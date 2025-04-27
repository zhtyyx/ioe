"""
库存管理视图
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.db.models import Q, Sum, F
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator

from inventory.models import (
    Product, Inventory, InventoryTransaction, 
    OperationLog, StockAlert, check_inventory,
    update_inventory, Category
)
from inventory.forms import InventoryTransactionForm


@login_required
def inventory_list(request):
    """库存列表视图"""
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
def inventory_transaction_list(request):
    """库存交易记录列表，显示所有入库、出库和调整记录"""
    # 获取筛选参数
    transaction_type = request.GET.get('type', '')
    product_id = request.GET.get('product_id', '')
    search_query = request.GET.get('search', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # 基础查询
    transactions = InventoryTransaction.objects.select_related('product', 'operator').all()
    
    # 应用筛选条件
    if transaction_type:
        transactions = transactions.filter(transaction_type=transaction_type)
    
    if product_id:
        transactions = transactions.filter(product_id=product_id)
    
    if search_query:
        transactions = transactions.filter(
            Q(product__name__icontains=search_query) | 
            Q(product__barcode__icontains=search_query) |
            Q(notes__icontains=search_query)
        )
    
    if date_from:
        from datetime import datetime
        try:
            date_from = datetime.strptime(date_from, '%Y-%m-%d')
            transactions = transactions.filter(created_at__gte=date_from)
        except (ValueError, TypeError):
            pass
    
    if date_to:
        from datetime import datetime, timedelta
        try:
            date_to = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)  # 加一天以包含整天
            transactions = transactions.filter(created_at__lt=date_to)
        except (ValueError, TypeError):
            pass
    
    # 排序
    transactions = transactions.order_by('-created_at')
    
    # 分页
    paginator = Paginator(transactions, 20)  # 每页20条记录
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'inventory/inventory_transaction_list.html', {
        'page_obj': page_obj,
        'transaction_type': transaction_type,
        'product_id': product_id,
        'search_query': search_query,
        'date_from': date_from,
        'date_to': date_to,
        'transaction_types': dict(InventoryTransaction.TRANSACTION_TYPES)
    })


@login_required
def inventory_in(request):
    """入库视图"""
    if request.method == 'POST':
        form = InventoryTransactionForm(request.POST)
        if form.is_valid():
            product = form.cleaned_data['product']
            quantity = form.cleaned_data['quantity']
            notes = form.cleaned_data['notes']
            
            # 使用工具函数更新库存
            success, inventory, result = update_inventory(
                product=product,
                quantity=quantity,  # 正数表示入库
                transaction_type='IN',
                operator=request.user,
                notes=notes
            )
            
            if success:
                # 记录操作日志
                OperationLog.objects.create(
                    operator=request.user,
                    operation_type='INVENTORY',
                    details=f'入库: {product.name} x {quantity}',
                    related_object_id=inventory.id,
                    related_content_type=ContentType.objects.get_for_model(inventory)
                )
                
                messages.success(request, f'{product.name} 入库成功，当前库存: {inventory.quantity}')
                return redirect('inventory_list')
            else:
                messages.error(request, f'入库失败: {result}')
    else:
        form = InventoryTransactionForm()
    
    return render(request, 'inventory/inventory_transaction_form.html', {
        'form': form,
        'form_title': '商品入库',
        'submit_text': '确认入库',
        'transaction_type': 'IN'
    })


@login_required
def inventory_out(request):
    """出库视图"""
    if request.method == 'POST':
        form = InventoryTransactionForm(request.POST)
        if form.is_valid():
            product = form.cleaned_data['product']
            quantity = form.cleaned_data['quantity']
            notes = form.cleaned_data['notes']
            
            # 先检查库存是否足够
            if not check_inventory(product, quantity):
                messages.error(request, f'出库失败: {product.name} 当前库存不足')
                return render(request, 'inventory/inventory_transaction_form.html', {
                    'form': form,
                    'form_title': '商品出库',
                    'submit_text': '确认出库',
                    'transaction_type': 'OUT'
                })
            
            # 使用工具函数更新库存
            success, inventory, result = update_inventory(
                product=product,
                quantity=-quantity,  # 负数表示出库
                transaction_type='OUT',
                operator=request.user,
                notes=notes
            )
            
            if success:
                # 记录操作日志
                OperationLog.objects.create(
                    operator=request.user,
                    operation_type='INVENTORY',
                    details=f'出库: {product.name} x {quantity}',
                    related_object_id=inventory.id,
                    related_content_type=ContentType.objects.get_for_model(inventory)
                )
                
                messages.success(request, f'{product.name} 出库成功，当前库存: {inventory.quantity}')
                return redirect('inventory_list')
            else:
                messages.error(request, f'出库失败: {result}')
    else:
        form = InventoryTransactionForm()
    
    return render(request, 'inventory/inventory_transaction_form.html', {
        'form': form,
        'form_title': '商品出库',
        'submit_text': '确认出库',
        'transaction_type': 'OUT'
    })


@login_required
def inventory_adjust(request):
    """库存调整视图"""
    if request.method == 'POST':
        form = InventoryTransactionForm(request.POST)
        if form.is_valid():
            product = form.cleaned_data['product']
            quantity = form.cleaned_data['quantity']
            notes = form.cleaned_data['notes']
            
            # 获取当前库存
            try:
                inventory = Inventory.objects.get(product=product)
                current_quantity = inventory.quantity
            except Inventory.DoesNotExist:
                current_quantity = 0
            
            # 计算调整值
            adjustment_action = request.POST.get('adjustment_action')
            if adjustment_action == 'set':
                # 设置为指定数量
                if quantity < 0:
                    messages.error(request, '库存数量不能为负数')
                    return render(request, 'inventory/inventory_adjust_form.html', {
                        'form': form,
                        'current_quantity': current_quantity
                    })
                
                adjustment_value = quantity - current_quantity
            elif adjustment_action == 'add':
                # 增加指定数量
                adjustment_value = quantity
            elif adjustment_action == 'subtract':
                # 减少指定数量
                if quantity > current_quantity:
                    messages.error(request, f'减少的数量({quantity})超过了当前库存({current_quantity})')
                    return render(request, 'inventory/inventory_adjust_form.html', {
                        'form': form,
                        'current_quantity': current_quantity
                    })
                
                adjustment_value = -quantity
            else:
                messages.error(request, '请选择有效的调整方式')
                return render(request, 'inventory/inventory_adjust_form.html', {
                    'form': form,
                    'current_quantity': current_quantity
                })
            
            # 使用工具函数更新库存
            success, inventory, result = update_inventory(
                product=product,
                quantity=adjustment_value,
                transaction_type='ADJUST',
                operator=request.user,
                notes=f"{notes} (调整前: {current_quantity})"
            )
            
            if success:
                # 记录操作日志
                OperationLog.objects.create(
                    operator=request.user,
                    operation_type='INVENTORY',
                    details=f'库存调整: {product.name} 从 {current_quantity} 到 {inventory.quantity}',
                    related_object_id=inventory.id,
                    related_content_type=ContentType.objects.get_for_model(inventory)
                )
                
                messages.success(request, f'{product.name} 库存调整成功，当前库存: {inventory.quantity}')
                return redirect('inventory_list')
            else:
                messages.error(request, f'库存调整失败: {result}')
    else:
        form = InventoryTransactionForm()
        product_id = request.GET.get('product_id')
        if product_id:
            try:
                product = Product.objects.get(id=product_id)
                form.fields['product'].initial = product
            except Product.DoesNotExist:
                pass
    
    # 获取当前库存（如果已选择商品）
    current_quantity = 0
    if form.initial.get('product'):
        try:
            inventory = Inventory.objects.get(product=form.initial['product'])
            current_quantity = inventory.quantity
        except Inventory.DoesNotExist:
            pass
    
    return render(request, 'inventory/inventory_adjust_form.html', {
        'form': form,
        'current_quantity': current_quantity
    })


@login_required
def inventory_transaction_create(request):
    """创建入库交易视图"""
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
            
            # 记录操作日志
            OperationLog.objects.create(
                operator=request.user,
                operation_type='INVENTORY',
                details=f'入库操作: {transaction.product.name}, 数量: {transaction.quantity}',
                related_object_id=transaction.id,
                related_content_type=ContentType.objects.get_for_model(InventoryTransaction)
            )
            
            messages.success(request, '入库操作成功')
            return redirect('inventory_list')
    else:
        form = InventoryTransactionForm()
    
    return render(request, 'inventory/inventory_form.html', {'form': form}) 