"""
商品相关业务服务
提供商品管理相关的业务逻辑处理
"""
import csv
import io
from django.utils import timezone
from django.db import transaction
from django.db.models import Q

from inventory.models import Product, Category, ProductImage, ProductBatch, Inventory


def import_products_from_csv(csv_file, user):
    """从CSV文件导入商品"""
    result = {
        'success': 0,
        'skipped': 0,
        'failed': 0,
        'failed_rows': []
    }
    
    # 读取CSV文件
    decoded_file = csv_file.read().decode('utf-8')
    csv_data = csv.reader(io.StringIO(decoded_file))
    headers = next(csv_data)  # 获取表头
    
    # 验证必要的表头
    required_headers = ['name', 'retail_price']
    missing_headers = [h for h in required_headers if h not in headers]
    if missing_headers:
        raise ValueError(f"CSV文件缺少必要的表头: {', '.join(missing_headers)}")
    
    # 获取各列索引
    headers_lower = [h.lower() for h in headers]
    name_idx = headers_lower.index('name')
    retail_price_idx = headers_lower.index('retail_price')
    
    # 可选列的索引
    category_idx = headers_lower.index('category') if 'category' in headers_lower else -1
    wholesale_price_idx = headers_lower.index('wholesale_price') if 'wholesale_price' in headers_lower else -1
    cost_price_idx = headers_lower.index('cost_price') if 'cost_price' in headers_lower else -1
    barcode_idx = headers_lower.index('barcode') if 'barcode' in headers_lower else -1
    sku_idx = headers_lower.index('sku') if 'sku' in headers_lower else -1
    specification_idx = headers_lower.index('specification') if 'specification' in headers_lower else -1
    
    # 处理每一行数据
    for row_num, row in enumerate(csv_data, start=2):  # 从2开始，因为1是表头
        try:
            if not row or len(row) < len(required_headers):
                result['skipped'] += 1
                continue
            
            # 解析基本信息
            name = row[name_idx].strip()
            if not name:
                result['failed'] += 1
                result['failed_rows'].append((row_num, "商品名称不能为空"))
                continue
            
            # 解析价格
            try:
                retail_price = float(row[retail_price_idx].replace(',', ''))
                if retail_price < 0:
                    result['failed'] += 1
                    result['failed_rows'].append((row_num, "零售价不能为负数"))
                    continue
            except (ValueError, IndexError):
                result['failed'] += 1
                result['failed_rows'].append((row_num, "零售价格式不正确"))
                continue
            
            # 检查商品是否已存在
            existing_product = None
            if barcode_idx >= 0 and row[barcode_idx]:
                barcode = row[barcode_idx].strip()
                existing_product = Product.objects.filter(barcode=barcode).first()
                if existing_product:
                    result['skipped'] += 1
                    result['failed_rows'].append((row_num, f"条码 {barcode} 已存在"))
                    continue
            
            # 解析分类
            category = None
            if category_idx >= 0 and row[category_idx]:
                category_name = row[category_idx].strip()
                category, _ = Category.objects.get_or_create(name=category_name)
            
            # 创建商品
            with transaction.atomic():
                product = Product.objects.create(
                    name=name,
                    category=category,
                    price=retail_price,
                    cost=float(row[cost_price_idx]) if cost_price_idx >= 0 and row[cost_price_idx] else retail_price * 0.7,
                    barcode=row[barcode_idx].strip() if barcode_idx >= 0 and row[barcode_idx] else None,
                    specification=row[specification_idx].strip() if specification_idx >= 0 and row[specification_idx] else "",
                    created_by=user
                )
                
                # 创建初始库存记录
                Inventory.objects.create(
                    product=product,
                    quantity=0,
                    warning_level=5
                )
                
                result['success'] += 1
                
        except Exception as e:
            result['failed'] += 1
            result['failed_rows'].append((row_num, str(e)))
            
    return result


def search_products(query, category_id=None, active_only=True):
    """搜索商品"""
    products = Product.objects.select_related('category').all()
    
    if query:
        products = products.filter(
            Q(name__icontains=query) | 
            Q(barcode__icontains=query) |
            Q(sku__icontains=query) |
            Q(specification__icontains=query)
        )
    
    if category_id:
        products = products.filter(category_id=category_id)
    
    if active_only:
        products = products.filter(is_active=True)
    
    return products.order_by('name')


def get_product_with_inventory(product_id):
    """获取商品及其库存信息"""
    try:
        product = Product.objects.get(id=product_id)
        inventory = Inventory.objects.get(product=product)
        return {
            'product': product,
            'inventory': inventory
        }
    except (Product.DoesNotExist, Inventory.DoesNotExist):
        return None 