from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.db.models import Q, Count, Sum
from django.core.paginator import Paginator
from django.urls import reverse
from django.utils import timezone

import csv
import io
import base64
import uuid
import os
from PIL import Image
from datetime import datetime

from inventory.models import (
    Product, Category, ProductImage, ProductBatch,
    Inventory, Supplier
)
from inventory.forms import (
    ProductForm, CategoryForm, ProductBatchForm,
    ProductImageFormSet, ProductBulkForm, ProductImportForm
)
from inventory.utils import generate_thumbnail, validate_csv
from inventory.services import product_service


def product_by_barcode(request, barcode):
    """根据条码查询商品信息的API"""
    try:
        # 先尝试精确匹配条码
        product = Product.objects.get(barcode=barcode)
        # 获取库存信息
        try:
            inventory_obj = Inventory.objects.get(product=product)
            stock = inventory_obj.quantity
        except Inventory.DoesNotExist:
            stock = 0
            
        return JsonResponse({
            'success': True,
            'product_id': product.id,
            'name': product.name,
            'price': float(product.price),
            'stock': stock,
            'category': product.category.name if product.category else '',
            'specification': product.specification,
            'manufacturer': product.manufacturer
        })
    except Product.DoesNotExist:
        # 如果精确匹配失败，尝试模糊匹配条码
        try:
            products = Product.objects.filter(barcode__icontains=barcode).order_by('barcode')[:5]
            
            if products.exists():
                # 返回匹配的多个商品
                product_list = []
                for product in products:
                    try:
                        inventory_obj = Inventory.objects.get(product=product)
                        stock = inventory_obj.quantity
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
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'查询时发生错误: {str(e)}'})


@login_required
def product_list(request):
    """商品列表视图"""
    # 获取筛选参数
    search_query = request.GET.get('search', '')
    category_id = request.GET.get('category', '')
    status = request.GET.get('status', 'active')  # 默认显示活跃商品
    sort_by = request.GET.get('sort', 'updated')  # 修改默认排序为更新时间
    
    print(f"DEBUG: 列表筛选参数 - 搜索: {search_query}, 分类: {category_id}, 状态: {status}, 排序: {sort_by}")
    
    # 基本查询集
    products = Product.objects.select_related('category').all()
    print(f"DEBUG: 初始查询集数量: {products.count()}")
    
    # 应用筛选
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) | 
            Q(barcode__icontains=search_query) |
            Q(specification__icontains=search_query)
        )
    
    if category_id:
        products = products.filter(category_id=category_id)
    
    # 状态筛选
    if status == 'active':
        products = products.filter(is_active=True)
        print(f"DEBUG: 应用活跃状态筛选后的数量: {products.count()}")
    elif status == 'inactive':
        products = products.filter(is_active=False)
    
    # 排序
    if sort_by == 'name':
        products = products.order_by('name')
    elif sort_by == 'price':
        products = products.order_by('price')
    elif sort_by == 'category':
        products = products.order_by('category__name', 'name')
    elif sort_by == 'created':
        products = products.order_by('-created_at')
    elif sort_by == 'updated':  # 添加按更新时间排序
        products = products.order_by('-updated_at')
    else:  # 默认按更新时间降序
        products = products.order_by('-updated_at')
    
    # 分页
    paginator = Paginator(products, 15)  # 每页15个商品
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # 获取分类列表用于筛选
    categories = Category.objects.all().order_by('name')
    
    # 计算统计数据
    total_products = Product.objects.count()
    active_products = Product.objects.filter(is_active=True).count()
    
    print(f"DEBUG: 总商品数: {total_products}, 活跃商品数: {active_products}, 当前页面商品数: {len(page_obj)}")
    
    context = {
        'page_obj': page_obj,
        'categories': categories,
        'search_query': search_query,
        'selected_category': category_id,
        'selected_status': status,
        'sort_by': sort_by,
        'total_products': total_products,
        'active_products': active_products,
        'products': page_obj,
    }
    
    return render(request, 'inventory/product_list.html', context)


@login_required
def product_detail(request, pk):
    """商品详情视图"""
    product = get_object_or_404(Product, pk=pk)
    
    # 获取商品库存信息
    try:
        inventory = Inventory.objects.get(product=product)
    except Inventory.DoesNotExist:
        inventory = None
    
    # 获取商品批次信息
    batches = ProductBatch.objects.filter(product=product).order_by('-created_at')
    
    # 获取商品图片
    images = ProductImage.objects.filter(product=product).order_by('order')
    
    # 获取销售记录
    from inventory.models import SaleItem
    sales_history = SaleItem.objects.filter(product=product).order_by('-sale__created_at')[:10]
    
    context = {
        'product': product,
        'inventory': inventory,
        'batches': batches,
        'images': images,
        'sales_history': sales_history,
    }
    
    return render(request, 'inventory/product/product_detail.html', context)


@login_required
def product_create(request):
    """创建商品视图"""
    if request.method == 'POST':
        form = ProductForm(request.POST)
        image_formset = ProductImageFormSet(request.POST, request.FILES, prefix='images')
        
        # 修改验证逻辑，只检查表单是否有效，不强制检查图片表单集
        if form.is_valid():
            # 保存商品数据
            product = form.save(commit=False)
            product.created_by = request.user
            product.is_active = True  # 确保商品默认为活跃状态
            product.save()
            
            # 只有当图片表单集有效时才处理图片
            if image_formset.is_valid():
                # 保存商品图片
                for image_form in image_formset:
                    if image_form.cleaned_data and not image_form.cleaned_data.get('DELETE'):
                        image = image_form.save(commit=False)
                        image.product = product
                        
                        # 处理图片文件
                        if image.image:
                            # 生成缩略图
                            thumbnail = generate_thumbnail(image.image, (300, 300))
                            
                            # 保存缩略图
                            thumb_name = f'thumb_{uuid.uuid4()}.jpg'
                            thumb_path = f'products/thumbnails/{thumb_name}'
                            thumb_file = io.BytesIO()
                            thumbnail.save(thumb_file, format='JPEG')
                            
                            # 设置缩略图路径
                            image.thumbnail = thumb_path
                        
                        image.save()
            
            # 创建初始库存记录
            warning_level = 10  # 设置一个默认的预警值
            if 'warning_level' in form.cleaned_data and form.cleaned_data['warning_level'] is not None:
                warning_level = form.cleaned_data['warning_level']
                
            Inventory.objects.create(
                product=product,
                quantity=0,
                warning_level=warning_level
            )
            
            messages.success(request, f'商品 {product.name} 创建成功')
            
            # 如果是从批量页面过来，返回批量页面
            if 'next' in request.POST and request.POST['next'] == 'bulk':
                return redirect('product_bulk_create')
            
            # 修改重定向，解决模板不存在的问题
            return redirect('product_list')
    else:
        form = ProductForm()
        image_formset = ProductImageFormSet(prefix='images')
        
        # 如果有传入的分类参数，设置初始值
        category_id = request.GET.get('category')
        if category_id:
            try:
                form.fields['category'].initial = int(category_id)
            except (ValueError, TypeError):
                pass
    
    context = {
        'form': form,
        'image_formset': image_formset,
        'title': '创建商品',
        'submit_text': '保存商品',
        'next': request.GET.get('next', '')
    }
    
    return render(request, 'inventory/product/product_form.html', context)


@login_required
def product_update(request, pk):
    """更新商品视图"""
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        image_formset = ProductImageFormSet(request.POST, request.FILES, prefix='images', instance=product)
        
        # 修改验证逻辑，只检查表单是否有效，不强制检查图片表单集
        if form.is_valid():
            # 保存商品数据
            product = form.save(commit=False)
            product.updated_at = timezone.now()
            product.updated_by = request.user
            product.save()
            
            # 只有当图片表单集有效时才处理图片
            if image_formset.is_valid():
                # 保存商品图片
                for image_form in image_formset:
                    if image_form.cleaned_data:
                        if image_form.cleaned_data.get('DELETE'):
                            if image_form.instance.pk:
                                image_form.instance.delete()
                        else:
                            image = image_form.save(commit=False)
                            image.product = product
                            
                            # 处理图片文件
                            if image.image and not image.thumbnail:
                                # 生成缩略图
                                thumbnail = generate_thumbnail(image.image, (300, 300))
                                
                                # 保存缩略图
                                thumb_name = f'thumb_{uuid.uuid4()}.jpg'
                                thumb_path = f'products/thumbnails/{thumb_name}'
                                thumb_file = io.BytesIO()
                                thumbnail.save(thumb_file, format='JPEG')
                                
                                # 设置缩略图路径
                                image.thumbnail = thumb_path
                            
                            image.save()
            
            # 更新库存预警级别
            warning_level = 10  # 设置一个默认的预警值
            if 'warning_level' in form.cleaned_data and form.cleaned_data['warning_level'] is not None:
                warning_level = form.cleaned_data['warning_level']
                
            try:
                inventory = Inventory.objects.get(product=product)
                inventory.warning_level = warning_level
                inventory.save()
            except Inventory.DoesNotExist:
                Inventory.objects.create(
                    product=product,
                    quantity=0,
                    warning_level=warning_level
                )
            
            messages.success(request, f'商品 {product.name} 更新成功')
            # 修改重定向，解决模板不存在的问题
            return redirect('product_list')
    else:
        form = ProductForm(instance=product)
        # 设置库存预警级别
        try:
            inventory = Inventory.objects.get(product=product)
            form.fields['warning_level'].initial = inventory.warning_level
        except Inventory.DoesNotExist:
            pass
        
        image_formset = ProductImageFormSet(prefix='images', instance=product)
    
    context = {
        'form': form,
        'image_formset': image_formset,
        'product': product,
        'title': f'编辑商品: {product.name}',
        'submit_text': '更新商品'
    }
    
    return render(request, 'inventory/product/product_form.html', context)


@login_required
def product_delete(request, pk):
    """删除商品视图"""
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        product_name = product.name
        
        # 标记为不活跃而不是真的删除
        product.is_active = False
        product.updated_at = timezone.now()
        product.updated_by = request.user
        product.save()
        
        messages.success(request, f'商品 {product_name} 已标记为不活跃')
        return redirect('product_list')
    
    return render(request, 'inventory/product/product_confirm_delete.html', {
        'product': product
    })


@login_required
def product_category_list(request):
    """商品分类列表视图"""
    # 获取筛选参数
    search_query = request.GET.get('search', '')
    status = request.GET.get('status', '')
    
    # 基本查询集
    categories = Category.objects.all()
    
    # 应用筛选
    if search_query:
        categories = categories.filter(name__icontains=search_query)
    
    if status == 'active':
        categories = categories.filter(is_active=True)
    elif status == 'inactive':
        categories = categories.filter(is_active=False)
    
    # 添加商品计数
    categories = categories.annotate(product_count=Count('product'))
    
    # 排序
    categories = categories.order_by('name')
    
    # 计算统计数据
    total_categories = Category.objects.count()
    active_categories = Category.objects.filter(is_active=True).count()
    
    context = {
        'categories': categories,
        'search_query': search_query,
        'selected_status': status,
        'total_categories': total_categories,
        'active_categories': active_categories,
    }
    
    return render(request, 'inventory/product/category_list.html', context)


@login_required
def product_category_create(request):
    """创建商品分类视图"""
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'分类 {category.name} 创建成功')
            return redirect('product_category_list')
    else:
        form = CategoryForm()
    
    context = {
        'form': form,
        'title': '创建商品分类',
        'submit_text': '保存分类'
    }
    
    return render(request, 'inventory/product/category_form.html', context)


@login_required
def product_category_update(request, pk):
    """更新商品分类视图"""
    category = get_object_or_404(Category, pk=pk)
    
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'分类 {category.name} 更新成功')
            return redirect('product_category_list')
    else:
        form = CategoryForm(instance=category)
    
    context = {
        'form': form,
        'category': category,
        'title': f'编辑分类: {category.name}',
        'submit_text': '更新分类'
    }
    
    return render(request, 'inventory/product/category_form.html', context)


@login_required
def product_category_delete(request, pk):
    """删除商品分类视图"""
    category = get_object_or_404(Category, pk=pk)
    
    # 检查该分类是否有关联的商品
    product_count = Product.objects.filter(category=category).count()
    
    if request.method == 'POST':
        if product_count > 0 and not request.POST.get('force_delete'):
            messages.error(request, f'分类 {category.name} 下有 {product_count} 个商品，无法删除')
            return redirect('product_category_list')
        
        category_name = category.name
        
        if product_count > 0:
            # 将关联的商品分类设为空
            Product.objects.filter(category=category).update(category=None)
        
        # 标记为不活跃而不是真的删除
        category.is_active = False
        category.save()
        
        messages.success(request, f'分类 {category_name} 已标记为不活跃')
        return redirect('product_category_list')
    
    context = {
        'category': category,
        'product_count': product_count
    }
    
    return render(request, 'inventory/product/category_confirm_delete.html', context)


@login_required
def product_batch_create(request, product_id):
    """创建商品批次视图"""
    product = get_object_or_404(Product, pk=product_id)
    
    if request.method == 'POST':
        form = ProductBatchForm(request.POST)
        if form.is_valid():
            batch = form.save(commit=False)
            batch.product = product
            batch.created_by = request.user
            batch.save()
            
            messages.success(request, f'批次 {batch.batch_number} 创建成功')
            return redirect('product_detail', pk=product.id)
    else:
        # 生成一个默认的批次号
        current_date = datetime.now().strftime('%Y%m%d')
        next_batch_number = f'{product.id}-{current_date}'
        
        form = ProductBatchForm(initial={
            'batch_number': next_batch_number,
            'quantity': 0
        })
    
    context = {
        'form': form,
        'product': product,
        'title': f'为 {product.name} 创建批次',
        'submit_text': '保存批次'
    }
    
    return render(request, 'inventory/product/batch_form.html', context)


@login_required
def product_batch_update(request, pk):
    """更新商品批次视图"""
    batch = get_object_or_404(ProductBatch, pk=pk)
    product = batch.product
    
    if request.method == 'POST':
        form = ProductBatchForm(request.POST, instance=batch)
        if form.is_valid():
            batch = form.save()
            messages.success(request, f'批次 {batch.batch_number} 更新成功')
            return redirect('product_detail', pk=product.id)
    else:
        form = ProductBatchForm(instance=batch)
    
    context = {
        'form': form,
        'batch': batch,
        'product': product,
        'title': f'编辑批次: {batch.batch_number}',
        'submit_text': '更新批次'
    }
    
    return render(request, 'inventory/product/batch_form.html', context)


@login_required
def product_bulk_create(request):
    """批量创建商品视图"""
    if request.method == 'POST':
        form = ProductBulkForm(request.POST)
        if form.is_valid():
            category = form.cleaned_data['category']
            name_prefix = form.cleaned_data['name_prefix']
            name_suffix_start = form.cleaned_data.get('name_suffix_start', 1)
            name_suffix_end = form.cleaned_data.get('name_suffix_end', 10)
            retail_price = form.cleaned_data['retail_price']
            wholesale_price = form.cleaned_data.get('wholesale_price')
            cost_price = form.cleaned_data.get('cost_price')
            
            created_count = 0
            
            # 创建批量商品
            for i in range(name_suffix_start, name_suffix_end + 1):
                product_name = f"{name_prefix}{i}"
                
                # 检查商品是否已存在
                if Product.objects.filter(name=product_name).exists():
                    continue
                
                product = Product.objects.create(
                    name=product_name,
                    category=category,
                    retail_price=retail_price,
                    wholesale_price=wholesale_price or retail_price,
                    cost_price=cost_price or retail_price * 0.7,
                    created_by=request.user
                )
                
                # 创建库存记录
                Inventory.objects.create(
                    product=product,
                    quantity=0,
                    warning_level=5
                )
                
                created_count += 1
            
            messages.success(request, f'成功创建 {created_count} 个商品')
            return redirect('product_list')
    else:
        form = ProductBulkForm()
    
    context = {
        'form': form,
        'title': '批量创建商品',
        'submit_text': '创建商品'
    }
    
    return render(request, 'inventory/product/product_bulk_form.html', context)


@login_required
def product_import(request):
    """导入商品视图"""
    if request.method == 'POST':
        form = ProductImportForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            
            # 验证CSV文件
            validation_result = validate_csv(csv_file, 
                                            required_headers=['name', 'retail_price'],
                                            expected_headers=['name', 'category', 'retail_price', 
                                                            'wholesale_price', 'cost_price', 
                                                            'barcode', 'sku', 'specification'])
            
            if not validation_result['valid']:
                messages.error(request, f"CSV文件验证失败: {validation_result['errors']}")
                return render(request, 'inventory/product/product_import.html', {'form': form})
            
            # 处理CSV文件
            try:
                result = product_service.import_products_from_csv(csv_file, request.user)
                
                messages.success(request, f"成功导入 {result['success']} 个商品. {result['skipped']} 个被跳过, {result['failed']} 个失败.")
                
                if result['failed_rows']:
                    error_messages = []
                    for row_num, error in result['failed_rows']:
                        error_messages.append(f"行 {row_num}: {error}")
                    
                    # 将错误消息限制在合理范围内
                    if len(error_messages) > 5:
                        error_messages = error_messages[:5] + [f"... 及其他 {len(error_messages) - 5} 个错误."]
                    
                    for error in error_messages:
                        messages.warning(request, error)
                
                return redirect('product_list')
            
            except Exception as e:
                messages.error(request, f"导入过程中发生错误: {str(e)}")
                return render(request, 'inventory/product/product_import.html', {'form': form})
    else:
        form = ProductImportForm()
    
    # 生成样例CSV数据
    sample_data = [
        ['name', 'category', 'retail_price', 'wholesale_price', 'cost_price', 'barcode', 'sku', 'specification'],
        ['测试商品1', '水果', '10.00', '8.00', '6.00', '123456789', 'SKU001', '500g'],
        ['测试商品2', '蔬菜', '5.50', '4.50', '3.00', '987654321', 'SKU002', '1kg'],
    ]
    
    # 创建内存中的CSV
    sample_csv = io.StringIO()
    writer = csv.writer(sample_csv)
    for row in sample_data:
        writer.writerow(row)
    
    sample_csv_content = sample_csv.getvalue()
    
    context = {
        'form': form,
        'sample_csv': sample_csv_content,
    }
    
    return render(request, 'inventory/product/product_import.html', context)


@login_required
def product_export(request):
    """导出商品视图"""
    # 获取筛选参数
    category_id = request.GET.get('category', '')
    status = request.GET.get('status', '')
    
    # 基本查询集
    products = Product.objects.select_related('category').all()
    
    # 应用筛选
    if category_id:
        products = products.filter(category_id=category_id)
    
    if status == 'active':
        products = products.filter(is_active=True)
    elif status == 'inactive':
        products = products.filter(is_active=False)
    
    # 创建CSV响应
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="products_export.csv"'
    
    # 写入CSV
    writer = csv.writer(response)
    writer.writerow(['ID', '名称', '分类', '零售价', '批发价', '成本价', '条码', 'SKU', '规格', '状态'])
    
    for product in products:
        writer.writerow([
            product.id,
            product.name,
            product.category.name if product.category else '',
            product.retail_price,
            product.wholesale_price,
            product.cost_price,
            product.barcode or '',
            product.sku or '',
            product.specification or '',
            '启用' if product.is_active else '禁用',
        ])
    
    return response

# 添加别名函数以兼容旧的导入
def product_edit(request, pk):
    """
    product_update的别名函数，用于保持向后兼容性
    """
    return product_update(request, pk) 