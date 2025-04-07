"""数据库查询优化工具"""
from django.db.models import QuerySet

def optimize_product_query(queryset):
    """
    优化商品查询，预加载分类信息
    
    Args:
        queryset: 商品查询集
        
    Returns:
        QuerySet: 优化后的查询集
    """
    if not isinstance(queryset, QuerySet):
        return queryset
        
    return queryset.select_related('category')

def optimize_inventory_query(queryset):
    """
    优化库存查询，预加载商品和分类信息
    
    Args:
        queryset: 库存查询集
        
    Returns:
        QuerySet: 优化后的查询集
    """
    if not isinstance(queryset, QuerySet):
        return queryset
        
    return queryset.select_related('product', 'product__category')

def optimize_sale_query(queryset):
    """
    优化销售查询，预加载会员信息
    
    Args:
        queryset: 销售查询集
        
    Returns:
        QuerySet: 优化后的查询集
    """
    if not isinstance(queryset, QuerySet):
        return queryset
        
    return queryset.select_related('member', 'member__level')

def optimize_sale_item_query(queryset):
    """
    优化销售项查询，预加载销售单和商品信息
    
    Args:
        queryset: 销售项查询集
        
    Returns:
        QuerySet: 优化后的查询集
    """
    if not isinstance(queryset, QuerySet):
        return queryset
        
    return queryset.select_related('sale', 'product')

def optimize_member_query(queryset):
    """
    优化会员查询，预加载会员等级信息
    
    Args:
        queryset: 会员查询集
        
    Returns:
        QuerySet: 优化后的查询集
    """
    if not isinstance(queryset, QuerySet):
        return queryset
        
    return queryset.select_related('level')

def optimize_inventory_check_query(queryset):
    """
    优化库存盘点查询，预加载创建者信息
    
    Args:
        queryset: 库存盘点查询集
        
    Returns:
        QuerySet: 优化后的查询集
    """
    if not isinstance(queryset, QuerySet):
        return queryset
        
    return queryset.select_related('created_by')

def optimize_inventory_check_item_query(queryset):
    """
    优化库存盘点项查询，预加载盘点单和商品信息
    
    Args:
        queryset: 库存盘点项查询集
        
    Returns:
        QuerySet: 优化后的查询集
    """
    if not isinstance(queryset, QuerySet):
        return queryset
        
    return queryset.select_related('inventory_check', 'product', 'checked_by')

def optimize_recharge_record_query(queryset):
    """
    优化充值记录查询，预加载会员信息
    
    Args:
        queryset: 充值记录查询集
        
    Returns:
        QuerySet: 优化后的查询集
    """
    if not isinstance(queryset, QuerySet):
        return queryset
        
    return queryset.select_related('member', 'member__level', 'operator')