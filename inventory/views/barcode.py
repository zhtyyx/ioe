from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

# 显式导入原始models
import inventory.models
from inventory.models.common import OperationLog 
from inventory.forms import ProductForm  # 直接从forms包导入需要的表单
from inventory.ali_barcode_service import AliBarcodeService
from inventory.services.product_service import search_products

# 外部条码服务API配置（示例用，实际应替换为自己的API密钥）
BARCODE_API_APP_KEY = "your_app_key"
BARCODE_API_APP_SECRET = "your_app_secret"
BARCODE_API_URL = "https://api.example.com/barcode"

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
                    'description': barcode_data.get('description', '')
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
                initial_data = {'barcode': barcode}
    
    # 处理表单提交
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            # 保存商品信息
            product = form.save()
            
            # 创建初始库存记录
            initial_stock = request.POST.get('initial_stock', 0)
            try:
                initial_stock = int(initial_stock)
                if initial_stock < 0:
                    initial_stock = 0
            except ValueError:
                initial_stock = 0
                
            # 检查是否已存在该商品的库存记录
            inventory, created = inventory.models.Inventory.objects.get_or_create(
                product=product,
                defaults={'quantity': initial_stock}
            )
            
            # 如果已存在库存记录，则更新数量
            if not created:
                inventory.quantity += initial_stock
                inventory.save()
            
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
        form = ProductForm(initial=initial_data)
    
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
        # 获取库存信息
        try:
            inventory = inventory.models.Inventory.objects.get(product=product)
            stock = inventory.quantity
        except inventory.models.Inventory.DoesNotExist:
            stock = 0
            
        return JsonResponse({
            'success': True,
            'exists': True,
            'product_id': product.id,
            'name': product.name,
            'price': float(product.price),
            'stock': stock,
            'category': product.category.name if product.category else '',
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

@login_required
def barcode_scan(request):
    """条码扫描页面，用于测试条码功能"""
    return render(request, 'inventory/barcode/barcode_scan.html')

def product_by_barcode(request, barcode):
    """根据条码查询商品信息的API"""
    try:
        # 先尝试精确匹配条码
        product = inventory.models.Product.objects.get(barcode=barcode)
        # 获取库存信息
        try:
            inventory_obj = inventory.models.Inventory.objects.get(product=product)
            stock = inventory_obj.quantity
        except inventory.models.Inventory.DoesNotExist:
            stock = 0
            
        return JsonResponse({
            'success': True,
            'multiple_matches': False,
            'product_id': product.id,
            'name': product.name,
            'price': float(product.price),
            'stock': stock,
            'category': product.category.name if product.category else '',
            'specification': product.specification,
            'manufacturer': product.manufacturer
        })
    except inventory.models.Product.DoesNotExist:
        # 如果精确匹配失败，尝试模糊匹配条码或名称
        products = inventory.models.Product.objects.filter(
            Q(barcode__icontains=barcode) | 
            Q(name__icontains=barcode)
        ).order_by('name')[:5]  # 限制返回数量
        
        if products.exists():
            # 如果只有一个匹配结果
            if products.count() == 1:
                product = products.first()
                # 获取库存信息
                try:
                    inventory_obj = inventory.models.Inventory.objects.get(product=product)
                    stock = inventory_obj.quantity
                except inventory.models.Inventory.DoesNotExist:
                    stock = 0
                    
                return JsonResponse({
                    'success': True,
                    'multiple_matches': False,
                    'product_id': product.id,
                    'name': product.name,
                    'price': float(product.price),
                    'stock': stock,
                    'category': product.category.name if product.category else '',
                    'specification': product.specification,
                    'manufacturer': product.manufacturer
                })
            # 如果有多个匹配结果
            else:
                product_list = []
                for product in products:
                    try:
                        inventory_obj = inventory.models.Inventory.objects.get(product=product)
                        stock = inventory_obj.quantity
                    except inventory.models.Inventory.DoesNotExist:
                        stock = 0
                        
                    product_list.append({
                        'product_id': product.id,
                        'name': product.name,
                        'price': float(product.price),
                        'barcode': product.barcode,
                        'stock': stock,
                        'category': product.category.name if product.category else ''
                    })
                    
                return JsonResponse({
                    'success': True,
                    'multiple_matches': True,
                    'products': product_list
                })
        else:
            return JsonResponse({
                'success': False,
                'message': '未找到商品'
            })

@login_required
def scan_barcode(request):
    """条码扫描功能视图"""
    if request.method == 'POST':
        barcode_data = request.POST.get('barcode_data')
        
        if not barcode_data:
            return JsonResponse({'error': '未提供条码数据'}, status=400)
        
        # 尝试查找商品
        try:
            # 如果是商品条码（通常以商品ID开始）
            if barcode_data.startswith('P'):
                product_id = barcode_data.split('-')[0][1:]
                product = get_object_or_404(inventory.models.Product, pk=product_id)
                
                return JsonResponse({
                    'type': 'product',
                    'data': {
                        'id': product.id,
                        'name': product.name,
                        'retail_price': float(product.retail_price),
                        'wholesale_price': float(product.wholesale_price),
                        'inventory': product.current_inventory,
                        'barcode': product.barcode or barcode_data,
                    }
                })
            
            # 如果是批次条码（通常以B开始）
            elif barcode_data.startswith('B'):
                batch_id = barcode_data.split('-')[0][1:]
                batch = get_object_or_404(inventory.models.ProductBatch, pk=batch_id)
                
                return JsonResponse({
                    'type': 'batch',
                    'data': {
                        'id': batch.id,
                        'product': {
                            'id': batch.product.id,
                            'name': batch.product.name,
                            'retail_price': float(batch.product.retail_price),
                        },
                        'batch_number': batch.batch_number,
                        'manufacturing_date': batch.manufacturing_date.strftime('%Y-%m-%d') if batch.manufacturing_date else None,
                        'expiry_date': batch.expiry_date.strftime('%Y-%m-%d') if batch.expiry_date else None,
                        'remaining_quantity': batch.remaining_quantity,
                    }
                })
            
            # 否则尝试通过商品条形码查找
            else:
                product = get_object_or_404(inventory.models.Product, barcode=barcode_data)
                
                return JsonResponse({
                    'type': 'product',
                    'data': {
                        'id': product.id,
                        'name': product.name,
                        'retail_price': float(product.retail_price),
                        'wholesale_price': float(product.wholesale_price),
                        'inventory': product.current_inventory,
                        'barcode': product.barcode,
                    }
                })
        
        except Exception as e:
            return JsonResponse({'error': f'找不到条码对应的商品或批次: {str(e)}'}, status=404)
    
    # GET请求
    return render(request, 'inventory/barcode/scan_barcode.html')

@login_required
def get_product_batches(request):
    """获取商品批次的API视图"""
    product_id = request.GET.get('product_id')
    if not product_id:
        return JsonResponse({'error': 'Missing product_id'}, status=400)
    
    try:
        batches = inventory.models.ProductBatch.objects.filter(
            product_id=product_id, 
            is_active=True,
            remaining_quantity__gt=0
        ).values('id', 'batch_number', 'manufacturing_date', 'expiry_date', 'remaining_quantity')
        
        return JsonResponse(list(batches), safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# 以下为已停用的条码生成和打印功能
# 保留函数定义以维持API兼容性，但返回功能停用提示

@login_required
def generate_barcode_view(request, product_id=None):
    """生成商品条码视图 - 功能已停用"""
    messages.info(request, "条码生成功能已停用，因为您的商品已有条码。")
    return redirect('product_list')  # 重定向到商品列表页面

@login_required
def batch_barcode_view(request, batch_id=None):
    """生成批次条码视图 - 功能已停用"""
    messages.info(request, "批次条码生成功能已停用，因为您的商品已有条码。")
    return redirect('product_list')  # 重定向到商品列表页面

@login_required
def bulk_barcode_generation(request):
    """批量生成条码视图 - 功能已停用"""
    messages.info(request, "批量条码生成功能已停用，因为您的商品已有条码。")
    return redirect('product_list')  # 重定向到商品列表页面

@login_required
def barcode_template(request):
    """条码模板设置视图 - 功能已停用"""
    messages.info(request, "条码模板设置功能已停用，因为您的商品已有条码。")
    return redirect('product_list')  # 重定向到商品列表页面

def product_search_api(request):
    """通过名称或其他字段搜索商品API"""
    query = request.GET.get('query', '')
    if not query or len(query) < 2:  # 至少2个字符才进行搜索
        return JsonResponse({
            'success': False,
            'message': '请输入至少2个字符进行搜索'
        })
    
    # 使用service层搜索商品
    products = search_products(query, active_only=True)
    
    # 格式化返回数据
    result = []
    for product in products[:10]:  # 限制返回10条结果
        try:
            inventory_obj = inventory.models.Inventory.objects.get(product=product)
            stock = inventory_obj.quantity
        except inventory.models.Inventory.DoesNotExist:
            stock = 0
            
        result.append({
            'id': product.id,
            'name': product.name,
            'price': float(product.price),
            'stock': stock,
            'barcode': product.barcode,
            'spec': product.specification,
            'category': product.category.name if product.category else ''
        })
    
    return JsonResponse({
        'success': True,
        'products': result,
        'count': len(result)
    })