from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.contenttypes.models import ContentType

# 显式导入原始models
import inventory.models
from .models.common import OperationLog 
from . import forms
from .ali_barcode_service import AliBarcodeService

@login_required
def barcode_product_create(request):
    """
    通过条码查询商品信息并创建商品的视图
    支持GET方式查询条码，POST方式保存商品
    先查询数据库，如果不存在再调用API
    """
    barcode = request.GET.get('barcode', '')
    barcode_data = None
    initial_data = {}
    
    # 如果提供了条码，尝试查询商品信息
    if barcode:
        # 首先检查数据库中是否已存在该条码的商品
        try:
            existing_product = inventory.models.Product.objects.get(barcode=barcode)
            messages.warning(request, f'条码 {barcode} 的商品已存在，请勿重复添加')
            return redirect('product_list')
        except inventory.models.Product.DoesNotExist:
            # 调用阿里云条码服务查询商品信息
            barcode_data = AliBarcodeService.search_barcode(barcode)
            
            if barcode_data:
                # 预填表单数据
                initial_data = {
                    'barcode': barcode,
                    'name': barcode_data.get('name', ''),
                    'specification': barcode_data.get('specification', ''),
                    'manufacturer': barcode_data.get('manufacturer', ''),
                    'price': barcode_data.get('suggested_price', 0),
                    'cost': barcode_data.get('suggested_price', 0) * 0.8 if barcode_data.get('suggested_price') else 0,  # 默认成本价为建议售价的80%
                    'description': barcode_data.get('description', ''),
                    'is_active': True  # 确保初始化时is_active为True
                }
                
                # 尝试从数据库中查找匹配的商品类别
                category_name = barcode_data.get('category', '')
                if category_name:
                    try:
                        category = inventory.models.Category.objects.filter(name__icontains=category_name).first()
                        if category:
                            initial_data['category'] = category.id
                    except Exception as e:
                        print(f"查找商品类别出错: {e}")
                        # 错误处理，但不影响表单的其他字段
                messages.success(request, '成功获取商品信息，请确认并完善商品详情')
            else:
                messages.info(request, f'未找到条码 {barcode} 的商品信息，请手动填写')
                initial_data = {'barcode': barcode, 'is_active': True}  # 确保初始化时is_active为True
    
    # 处理表单提交
    if request.method == 'POST':
        form = forms.ProductForm(request.POST, request.FILES)
        if form.is_valid():
            # 确保is_active为True
            product = form.save(commit=False)
            product.is_active = True
            product.save()
            
            # 创建初始库存记录
            initial_stock = request.POST.get('initial_stock', 0)
            try:
                initial_stock = int(initial_stock)
                if initial_stock < 0:
                    initial_stock = 0
            except ValueError:
                initial_stock = 0
                
            # 检查是否已存在该商品的库存记录
            inventory_record, created = inventory.models.Inventory.objects.get_or_create(
                product=product,
                defaults={'quantity': initial_stock}
            )
            
            # 如果已存在库存记录，则更新数量
            if not created:
                inventory_record.quantity += initial_stock
                inventory_record.save()
            
            # 记录操作日志
            OperationLog.objects.create(
                operator=request.user,
                operation_type='INVENTORY',
                details=f'添加新商品: {product.name} (条码: {product.barcode}), 初始库存: {initial_stock}',
                related_object_id=product.id,
                related_content_type=ContentType.objects.get_for_model(product)
            )
            
            messages.success(request, '商品添加成功')
            return redirect('product_list')
    else:
        form = forms.ProductForm(initial=initial_data)
    
    # 确保barcode_data不为None时为字典类型
    if barcode_data is None:
        barcode_data = {}
        
    # 渲染模板
    return render(request, 'inventory/barcode_product_form.html', {
        'form': form,
        'barcode': barcode,
        'barcode_data': barcode_data
    })

@login_required
def barcode_lookup(request):
    """
    AJAX接口，用于查询条码信息
    先查询数据库，如果不存在再调用API
    """
    barcode = request.GET.get('barcode', '')
    if not barcode:
        return JsonResponse({'success': False, 'message': '请提供条码'})
        
    # 首先检查数据库中是否已存在该条码的商品
    try:
        product = inventory.models.Product.objects.get(barcode=barcode)
        return JsonResponse({
            'success': True,
            'exists': True,
            'product_id': product.id,
            'name': product.name,
            'price': float(product.price),
            'specification': product.specification,
            'manufacturer': product.manufacturer,
            'description': product.description,
            'message': '商品已存在于系统中'
        })
    except inventory.models.Product.DoesNotExist:
        # 调用阿里云条码服务查询商品信息
        barcode_data = AliBarcodeService.search_barcode(barcode)
        
        if barcode_data:
            return JsonResponse({
                'success': True,
                'exists': False,
                'data': barcode_data,
                'message': '成功获取商品信息'
            })
        else:
            return JsonResponse({
                'success': False,
                'exists': False,
                'message': '未找到商品信息'
            })