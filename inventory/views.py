from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import F, Sum
from .models import Product, Category, Inventory, Sale, SaleItem, InventoryTransaction, Member, MemberLevel, RechargeRecord
from django.http import JsonResponse
from .models import OperationLog
from django.db.models import Q
from decimal import Decimal
from django.utils import timezone
import re


def product_by_barcode(request, barcode):
    try:
        # 先尝试精确匹配条码
        product = Product.objects.get(barcode=barcode)
        # 获取库存信息
        try:
            inventory = Inventory.objects.get(product=product)
            stock = inventory.quantity
        except Inventory.DoesNotExist:
            stock = 0
            
        return JsonResponse({
            'success': True,
            'product_id': product.id,
            'name': product.name,
            'price': product.price,
            'stock': stock,
            'category': product.category.name if product.category else '',
            'specification': product.specification,
            'manufacturer': product.manufacturer
        })
    except Product.DoesNotExist:
        # 如果精确匹配失败，尝试模糊匹配条码
        products = Product.objects.filter(barcode__icontains=barcode).order_by('barcode')[:5]
        if products.exists():
            # 返回匹配的多个商品
            product_list = []
            for product in products:
                try:
                    inventory = Inventory.objects.get(product=product)
                    stock = inventory.quantity
                except Inventory.DoesNotExist:
                    stock = 0
                    
                product_list.append({
                    'product_id': product.id,
                    'barcode': product.barcode,
                    'name': product.name,
                    'price': float(product.price),
                    'stock': stock
                })
                
            return JsonResponse({
                'success': True,
                'multiple_matches': True,
                'products': product_list
            })
        else:
            return JsonResponse({'success': False, 'message': '未找到商品'})

# 新增会员搜索API
def member_search_by_phone(request, phone):
    """
    根据手机号搜索会员的API
    支持精确匹配和模糊匹配，返回多个匹配结果
    """
    try:
        # 先尝试精确匹配手机号
        member = Member.objects.get(phone=phone)
        return JsonResponse({
            'success': True,
            'multiple_matches': False,
            'member_id': member.id,
            'member_name': member.name,
            'member_level': member.level.name,
            'member_balance': float(member.balance),
            'member_points': member.points,
            'member_gender': member.get_gender_display(),
            'member_birthday': member.birthday.strftime('%Y-%m-%d') if member.birthday else '',
            'member_total_spend': float(member.total_spend),
            'member_purchase_count': member.purchase_count
        })
    except Member.DoesNotExist:
        # 如果精确匹配失败，尝试模糊匹配手机号或姓名
        members = Member.objects.filter(
            models.Q(phone__icontains=phone) | 
            models.Q(name__icontains=phone)
        ).order_by('phone')[:5]  # 限制返回数量
        
        if members.exists():
            # 如果只有一个匹配结果
            if members.count() == 1:
                member = members.first()
                return JsonResponse({
                    'success': True,
                    'multiple_matches': False,
                    'member_id': member.id,
                    'member_name': member.name,
                    'member_level': member.level.name,
                    'member_balance': float(member.balance),
                    'member_points': member.points,
                    'member_gender': member.get_gender_display(),
                    'member_birthday': member.birthday.strftime('%Y-%m-%d') if member.birthday else '',
                    'member_total_spend': float(member.total_spend),
                    'member_purchase_count': member.purchase_count
                })
            # 如果有多个匹配结果
            else:
                member_list = []
                for member in members:
                    member_list.append({
                        'member_id': member.id,
                        'member_name': member.name,
                        'member_phone': member.phone,
                        'member_level': member.level.name,
                        'member_balance': float(member.balance),
                        'member_points': member.points
                    })
                return JsonResponse({
                    'success': True,
                    'multiple_matches': True,
                    'members': member_list
                })
        else:
            return JsonResponse({'success': False, 'message': '未找到会员'})
            
from .forms import ProductForm, InventoryTransactionForm, SaleForm, SaleItemForm, MemberForm

@login_required
def index(request):
    products = Product.objects.all()[:5]  # 获取最新的5个商品
    low_stock_items = Inventory.objects.filter(quantity__lte=F('warning_level'))[:5]  # 获取库存预警商品
    context = {
        'products': products,
        'low_stock_items': low_stock_items,
    }
    return render(request, 'inventory/index.html', context)

@login_required
def product_list(request):
    products = Product.objects.all()
    categories = Category.objects.all()
    return render(request, 'inventory/product_list.html', {'products': products, 'categories': categories})

@login_required
def inventory_list(request):
    # 获取筛选参数
    category_id = request.GET.get('category', '')
    color = request.GET.get('color', '')
    size = request.GET.get('size', '')
    search_query = request.GET.get('search', '')
    
    # 基础查询
    inventory_items = Inventory.objects.select_related('product', 'product__category').all()
    
    # 应用筛选条件
    if category_id:
        inventory_items = inventory_items.filter(product__category_id=category_id)
    
    if color:
        inventory_items = inventory_items.filter(product__color=color)
    
    if size:
        inventory_items = inventory_items.filter(product__size=size)
    
    if search_query:
        inventory_items = inventory_items.filter(
            Q(product__name__icontains=search_query) | 
            Q(product__barcode__icontains=search_query)
        )
    
    # 获取所有分类
    categories = Category.objects.all()
    
    # 获取所有可用的颜色和尺码
    colors = Product.COLOR_CHOICES
    sizes = Product.SIZE_CHOICES
    
    context = {
        'inventory_items': inventory_items,
        'categories': categories,
        'colors': colors,
        'sizes': sizes,
        'selected_category': category_id,
        'selected_color': color,
        'selected_size': size,
        'search_query': search_query,
    }
    
    return render(request, 'inventory/inventory_list.html', context)

@login_required
def sale_list(request):
    sales = Sale.objects.all().order_by('-created_at')
    return render(request, 'inventory/sale_list.html', {'sales': sales})

@login_required
def sale_detail(request, sale_id):
    """销售单详情视图"""
    sale = get_object_or_404(Sale, pk=sale_id)
    items = sale.items.all()
    
    context = {
        'sale': sale,
        'items': items,
    }
    
    return render(request, 'inventory/sale_detail.html', context)

@login_required
def product_create(request):
    initial_data = {}
    
    # 如果是从条码API跳转过来的，预填表单
    if request.method == 'GET' and 'barcode' in request.GET:
        initial_data = {
            'barcode': request.GET.get('barcode', ''),
            'name': request.GET.get('name', ''),
            'price': request.GET.get('price', 0),
            'specification': request.GET.get('specification', ''),
            'manufacturer': request.GET.get('manufacturer', ''),
            'description': request.GET.get('description', '')
        }
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()
            Inventory.objects.create(product=product)
            
            # 记录操作日志
            from django.contrib.contenttypes.models import ContentType
            OperationLog.objects.create(
                operator=request.user,
                operation_type='INVENTORY',
                details=f'添加新商品: {product.name} (条码: {product.barcode})',
                related_object_id=product.id,
                related_content_type=ContentType.objects.get_for_model(Product)
            )
            
            messages.success(request, '商品添加成功')
            return redirect('product_list')
    else:
        form = ProductForm(initial=initial_data)
    
    return render(request, 'inventory/product_form.html', {
        'form': form,
        'is_from_barcode_api': bool(initial_data)
    })

@login_required
def product_edit(request, product_id):
    """编辑商品信息"""
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            
            # 记录操作日志
            from django.contrib.contenttypes.models import ContentType
            OperationLog.objects.create(
                operator=request.user,
                operation_type='INVENTORY',
                details=f'编辑商品: {product.name} (条码: {product.barcode})',
                related_object_id=product.id,
                related_content_type=ContentType.objects.get_for_model(Product)
            )
            
            messages.success(request, '商品信息更新成功')
            return redirect('product_list')
    else:
        form = ProductForm(instance=product)
    
    return render(request, 'inventory/product_form.html', {
        'form': form,
        'product': product,
        'is_edit': True
    })

@login_required
def inventory_transaction_create(request):
    if request.method == 'POST':
        form = InventoryTransactionForm(request.POST)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.transaction_type = 'IN'
            transaction.operator = request.user
            transaction.save()
            
            inventory = Inventory.objects.get(product=transaction.product)
            inventory.quantity += transaction.quantity
            inventory.save()
            
            messages.success(request, '入库操作成功')
            return redirect('inventory_list')
    else:
        form = InventoryTransactionForm()
    return render(request, 'inventory/inventory_form.html', {'form': form})

@login_required
def sale_create(request):
    if request.method == 'POST':
        form = SaleForm(request.POST)
        if form.is_valid():
            sale = form.save(commit=False)
            sale.operator = request.user
            
            # 添加会员关联
            member_id = request.POST.get('member')
            if member_id:
                try:
                    member = Member.objects.get(id=member_id)
                    sale.member = member
                except Member.DoesNotExist:
                    pass
                
            sale.save()
            messages.success(request, '销售单创建成功')
            return redirect('sale_item_create', sale_id=sale.id)
    else:
        form = SaleForm()
    
    # 获取会员等级列表，用于添加会员模态框
    member_levels = MemberLevel.objects.all()
    
    return render(request, 'inventory/sale_form.html', {
        'form': form,
        'member_levels': member_levels
    })

@login_required
def sale_item_create(request, sale_id):
    sale = get_object_or_404(Sale, id=sale_id)
    if request.method == 'POST':
        form = SaleItemForm(request.POST)
        if form.is_valid():
            sale_item = form.save(commit=False)
            sale_item.sale = sale
            
            inventory = Inventory.objects.get(product=sale_item.product)
            if inventory.quantity >= sale_item.quantity:
                inventory.quantity -= sale_item.quantity
                inventory.save()
                
                sale_item.save()
                sale.update_total_amount()
                
                transaction = InventoryTransaction.objects.create(
                    product=sale_item.product,
                    transaction_type='OUT',
                    quantity=sale_item.quantity,
                    operator=request.user,
                    notes=f'销售单号：{sale.id}'
                )
                
                messages.success(request, '商品添加成功')
                
                # 记录操作日志
                from django.contrib.contenttypes.models import ContentType
                OperationLog.objects.create(
                    operator=request.user,
                    operation_type='SALE',
                    details=f'销售商品 {sale_item.product.name} 数量 {sale_item.quantity}',
                    related_object_id=sale.id,
                    related_content_type=ContentType.objects.get_for_model(Sale)
                )
                return redirect('sale_item_create', sale_id=sale.id)
            else:
                messages.error(request, '库存不足')
    else:
        form = SaleItemForm()
    
    sale_items = sale.items.all()
    return render(request, 'inventory/sale_item_form.html', {
        'form': form,
        'sale': sale,
        'sale_items': sale_items
    })

@login_required
def member_list(request):
    sort_by = request.GET.get('sort', 'name')
    
    # 根据排序参数查询会员
    if sort_by == 'total_spend':
        members = Member.objects.all().order_by('-total_spend')
        sort_label = '累计消费'
    elif sort_by == 'purchase_count':
        members = Member.objects.all().order_by('-purchase_count')
        sort_label = '消费次数'
    else:
        members = Member.objects.all().order_by('name')
        sort_by = 'name'  # 防止注入
        sort_label = '姓名'
    
    member_levels = MemberLevel.objects.all()
    
    return render(request, 'inventory/member_list.html', {
        'members': members, 
        'member_levels': member_levels,
        'sort_by': sort_by,
        'sort_label': sort_label
    })

@login_required
def member_create(request):
    # 移除对当前用户是否已有会员记录的检查，允许管理员创建多个会员
    if request.method == 'POST':
        form = MemberForm(request.POST)
        if form.is_valid():
            member = form.save(commit=False)
            # 不再将会员与当前用户关联，允许创建独立的会员记录
            member.save()
            messages.success(request, '会员添加成功')
            return redirect('member_list')
    else:
        form = MemberForm()
    return render(request, 'inventory/member_form.html', {'form': form})

@login_required
def member_edit(request, member_id):
    member = get_object_or_404(Member, id=member_id)
    if request.method == 'POST':
        form = MemberForm(request.POST, instance=member)
        if form.is_valid():
            form.save()
            messages.success(request, '会员信息更新成功')
            return redirect('member_list')
    else:
        form = MemberForm(instance=member)
    return render(request, 'inventory/member_form.html', {'form': form})

@login_required
def member_purchases(request):
    """会员消费记录查询视图"""
    search_term = request.GET.get('search', '')
    
    if search_term:
        # 根据名称或手机号查询会员
        member = None
        sales = []
        
        try:
            # 先尝试按手机号查找
            member = Member.objects.get(phone=search_term)
            sales = Sale.objects.filter(member=member).order_by('-created_at')
        except Member.DoesNotExist:
            # 再尝试按名称模糊查找
            members = Member.objects.filter(name__icontains=search_term)
            if members.exists():
                # 如果找到多个会员，使用第一个
                member = members.first()
                sales = Sale.objects.filter(member=member).order_by('-created_at')
                
        return render(request, 'inventory/member_purchases.html', {
            'search_term': search_term,
            'member': member,
            'sales': sales
        })
    
    return render(request, 'inventory/member_purchases.html', {
        'search_term': '',
        'member': None,
        'sales': []
    })

@login_required
def member_level_list(request):
    """会员等级列表视图"""
    levels = MemberLevel.objects.all().order_by('points_threshold')
    return render(request, 'inventory/member_level_list.html', {'levels': levels})

@login_required
def member_level_create(request):
    """创建会员等级视图"""
    from .forms import MemberLevelForm
    
    if request.method == 'POST':
        form = MemberLevelForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '会员等级添加成功')
            return redirect('member_level_list')
    else:
        form = MemberLevelForm()
        
    return render(request, 'inventory/member_level_form.html', {'form': form})

@login_required
def member_level_edit(request, level_id):
    """编辑会员等级视图"""
    from .forms import MemberLevelForm
    
    level = get_object_or_404(MemberLevel, id=level_id)
    if request.method == 'POST':
        form = MemberLevelForm(request.POST, instance=level)
        if form.is_valid():
            form.save()
            messages.success(request, '会员等级更新成功')
            return redirect('member_level_list')
    else:
        form = MemberLevelForm(instance=level)
        
    return render(request, 'inventory/member_level_form.html', {'form': form, 'level': level})

@login_required
def member_recharge(request, member_id):
    """会员充值视图"""
    member = get_object_or_404(Member, id=member_id)
    
    if request.method == 'POST':
        amount = Decimal(request.POST.get('amount', '0'))
        actual_amount = Decimal(request.POST.get('actual_amount', '0'))
        payment_method = request.POST.get('payment_method', 'cash')
        remark = request.POST.get('remark', '')
        
        if amount <= 0:
            messages.error(request, '充值金额必须大于0')
            return redirect('member_recharge', member_id=member_id)
        
        # 创建充值记录
        recharge = RechargeRecord.objects.create(
            member=member,
            amount=amount,
            actual_amount=actual_amount,
            payment_method=payment_method,
            operator=request.user,
            remark=remark
        )
        
        # 更新会员余额和状态
        member.balance += amount
        member.is_recharged = True
        member.save()
        
        # 记录操作日志
        from django.contrib.contenttypes.models import ContentType
        OperationLog.objects.create(
            operator=request.user,
            operation_type='MEMBER',
            details=f'为会员 {member.name} 充值 {amount} 元',
            related_object_id=recharge.id,
            related_content_type=ContentType.objects.get_for_model(RechargeRecord)
        )
        
        messages.success(request, f'已成功为 {member.name} 充值 {amount} 元')
        return redirect('member_list')
    
    return render(request, 'inventory/member_recharge.html', {
        'member': member
    })

@login_required
def member_recharge_records(request, member_id):
    """会员充值记录视图"""
    member = get_object_or_404(Member, id=member_id)
    recharge_records = RechargeRecord.objects.filter(member=member).order_by('-created_at')
    
    return render(request, 'inventory/member_recharge_records.html', {
        'member': member,
        'recharge_records': recharge_records
    })

@login_required
def birthday_members_report(request):
    """当月生日会员报表"""
    # 获取当前月份
    current_month = timezone.now().month
    current_month_name = {
        1: '一月', 2: '二月', 3: '三月', 4: '四月', 5: '五月', 6: '六月',
        7: '七月', 8: '八月', 9: '九月', 10: '十月', 11: '十一月', 12: '十二月'
    }[current_month]
    
    # 获取当月生日的会员
    members = Member.objects.filter(birthday__month=current_month).order_by('id')
    
    # 统计会员等级分布
    level_counts = {}
    levels_data = []
    
    for member in members:
        if member.level:
            level_id = member.level.id
            if level_id not in level_counts:
                level_counts[level_id] = {
                    'id': level_id,
                    'name': member.level.name,
                    'color': member.level.color,
                    'color_code': f'#{member.level.color}' if member.level.color.startswith('gradient-') else member.level.color,
                    'count': 0
                }
            level_counts[level_id]['count'] += 1
    
    levels_data = list(level_counts.values())
    
    # 统计生日日期分布 (1-31日)
    days_distribution = [0] * 31
    for member in members:
        if member.birthday:
            day = member.birthday.day
            if 1 <= day <= 31:
                days_distribution[day - 1] += 1
    
    context = {
        'current_month_name': current_month_name,
        'members': members,
        'levels': levels_data,
        'days_distribution': days_distribution
    }
    
    return render(request, 'inventory/birthday_members_report.html', context)

@login_required
def member_details(request, member_id):
    """会员详细信息视图，包括消费记录和充值记录"""
    member = get_object_or_404(Member, id=member_id)
    
    # 获取会员的消费记录
    sales = Sale.objects.filter(member=member).order_by('-created_at')
    
    # 获取会员的充值记录
    recharge_records = RechargeRecord.objects.filter(member=member).order_by('-created_at')
    
    return render(request, 'inventory/member_details.html', {
        'member': member,
        'sales': sales,
        'recharge_records': recharge_records
    })

# 报表中心相关视图
@login_required
def reports_index(request):
    """报表中心首页，显示所有可用报表及其统计信息"""
    # 获取当月生日会员数量
    current_month = timezone.now().month
    birthday_members_count = Member.objects.filter(birthday__month=current_month).count()
    
    # 获取销售记录数量
    total_sales_count = Sale.objects.count()
    
    # 获取库存偏低的商品数量
    low_stock_count = Inventory.objects.filter(quantity__lt=F('warning_level')).count() or 0
    
    # 获取充值总金额
    total_recharge_amount = RechargeRecord.objects.aggregate(total=Sum('amount'))['total'] or 0
    
    # 获取本月销售额
    current_month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_sales_amount = Sale.objects.filter(
        created_at__gte=current_month_start
    ).aggregate(total=Sum('final_amount'))['total'] or 0
    
    # 获取今日操作日志数量
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_log_count = OperationLog.objects.filter(timestamp__gte=today_start).count()
    
    context = {
        'birthday_members_count': birthday_members_count,
        'total_sales_count': total_sales_count,
        'low_stock_count': low_stock_count,
        'total_recharge_amount': total_recharge_amount,
        'monthly_sales_amount': monthly_sales_amount,
        'today_log_count': today_log_count,
    }
    
    return render(request, 'inventory/reports_index.html', context)

@login_required
def member_add_ajax(request):
    """AJAX添加会员"""
    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            phone = request.POST.get('phone')
            level_id = request.POST.get('level')
            
            # 详细验证数据
            errors = {}
            if not name:
                errors['name'] = '会员姓名不能为空'
            if not phone:
                errors['phone'] = '手机号不能为空'
            elif not re.match(r'^\d{11}$', phone):
                errors['phone'] = '请输入11位手机号码'
            if not level_id:
                errors['level'] = '请选择会员等级'
            
            if errors:
                return JsonResponse({
                    'success': False, 
                    'message': '表单验证失败',
                    'errors': errors
                })
            
            # 检查手机号是否已存在
            if Member.objects.filter(phone=phone).exists():
                return JsonResponse({
                    'success': False, 
                    'message': '该手机号已注册为会员，请使用其他手机号'
                })
            
            # 获取会员等级
            try:
                level = MemberLevel.objects.get(id=level_id)
            except MemberLevel.DoesNotExist:
                return JsonResponse({
                    'success': False, 
                    'message': '所选会员等级不存在，请重新选择'
                })
            
            # 创建会员
            member = Member.objects.create(
                name=name,
                phone=phone,
                level=level,
                points=0,
                balance=0
            )
            
            # 记录操作日志
            from django.contrib.contenttypes.models import ContentType
            OperationLog.objects.create(
                operator=request.user,
                operation_type='MEMBER',
                details=f'添加会员: {name} (手机: {phone})',
                related_object_id=member.id,
                related_content_type=ContentType.objects.get_for_model(Member)
            )
            
            return JsonResponse({
                'success': True,
                'member_id': member.id,
                'member_name': member.name,
                'member_phone': member.phone,
                'member_level': member.level.name
            })
            
        except Exception as e:
            import traceback
            print(f"会员添加错误: {str(e)}")
            print(traceback.format_exc())
            return JsonResponse({
                'success': False, 
                'message': f'添加会员时发生错误: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': '不支持的请求方法'})