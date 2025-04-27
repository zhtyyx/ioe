from django.db.models import Prefetch, Q, Count, Sum, Avg, F, ExpressionWrapper, DecimalField
from django.utils import timezone
from datetime import timedelta
from functools import wraps
import time

def optimize_query(queryset, select_fields=None, prefetch_fields=None):
    """
    优化查询，减少数据库访问次数
    
    Args:
        queryset: 要优化的查询集
        select_fields: 要使用select_related的字段列表
        prefetch_fields: 要使用prefetch_related的字段列表或Prefetch对象列表
    
    Returns:
        优化后的查询集
    """
    if select_fields:
        queryset = queryset.select_related(*select_fields)
    
    if prefetch_fields:
        queryset = queryset.prefetch_related(*prefetch_fields)
    
    return queryset

def query_performance_logger(func):
    """
    装饰器：记录查询执行时间，用于性能分析
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        execution_time = time.time() - start_time
        print(f"查询 {func.__name__} 执行时间: {execution_time:.4f}秒")
        return result
    return wrapper

def paginate_queryset(queryset, page_number, items_per_page=20):
    """
    对查询集进行分页处理
    
    Args:
        queryset: 要分页的查询集
        page_number: 当前页码
        items_per_page: 每页显示的项目数
        
    Returns:
        分页后的查询集
    """
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    
    paginator = Paginator(queryset, items_per_page)
    
    try:
        paginated_queryset = paginator.page(page_number)
    except PageNotAnInteger:
        # 如果页码不是整数，返回第一页
        paginated_queryset = paginator.page(1)
    except EmptyPage:
        # 如果页码超出范围，返回最后一页
        paginated_queryset = paginator.page(paginator.num_pages)
    
    return paginated_queryset

def get_filtered_queryset(queryset, filter_params):
    """
    根据过滤参数过滤查询集
    
    Args:
        queryset: 要过滤的查询集
        filter_params: 过滤参数字典
        
    Returns:
        过滤后的查询集
    """
    # 移除空值
    valid_filters = {k: v for k, v in filter_params.items() if v}
    
    if valid_filters:
        queryset = queryset.filter(**valid_filters)
    
    return queryset

def get_date_range_filter(start_date, end_date, date_field='created_at'):
    """
    获取日期范围过滤条件
    
    Args:
        start_date: 开始日期
        end_date: 结束日期
        date_field: 日期字段名
        
    Returns:
        日期范围过滤条件字典
    """
    filter_kwargs = {}
    
    if start_date:
        filter_kwargs[f"{date_field}__gte"] = start_date
    
    if end_date:
        # 将结束日期调整为当天的最后一刻
        end_date = timezone.datetime.combine(
            end_date, 
            timezone.datetime.max.time()
        ).replace(tzinfo=timezone.get_current_timezone())
        filter_kwargs[f"{date_field}__lte"] = end_date
    
    return filter_kwargs

# 添加别名函数，保持向后兼容性
def get_paginated_queryset(queryset, page_number, items_per_page=20):
    """
    paginate_queryset的别名函数，保持向后兼容性
    
    Args:
        queryset: 要分页的查询集
        page_number: 当前页码
        items_per_page: 每页显示的项目数
        
    Returns:
        分页后的查询集
    """
    return paginate_queryset(queryset, page_number, items_per_page)

def build_filter_query(filter_dict):
    """
    构建过滤查询条件
    
    此函数从过滤字典创建Django ORM查询对象(Q)的组合
    
    Args:
        filter_dict: 包含字段和值的过滤字典，格式为 {field_name: value}
        
    Returns:
        Django Q对象的组合，可用于queryset.filter()
    """
    from django.db.models import Q
    
    # 移除空值
    valid_filters = {k: v for k, v in filter_dict.items() if v is not None and v != ''}
    
    # 初始化查询对象
    query = Q()
    
    # 为每个过滤条件创建查询子句并组合
    for field, value in valid_filters.items():
        # 支持列表值（用于in查询）
        if isinstance(value, list):
            if value:  # 只有当列表非空时才添加查询
                query &= Q(**{f"{field}__in": value})
        else:
            query &= Q(**{field: value})
    
    return query