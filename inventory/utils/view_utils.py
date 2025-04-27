"""视图工具函数，用于减少视图中的重复代码"""
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

from inventory.models import OperationLog

def log_operation(user, operation_type, details, related_object=None):
    """
    记录操作日志的通用方法
    
    Args:
        user: 执行操作的用户
        operation_type: 操作类型
        details: 操作详情
        related_object: 相关对象
    """
    log_entry = OperationLog(
        operator=user,
        operation_type=operation_type,
        details=details
    )
    
    if related_object:
        content_type = ContentType.objects.get_for_model(related_object)
        log_entry.related_content_type = content_type
        log_entry.related_object_id = related_object.id
    
    log_entry.save()
    return log_entry

def handle_form_submission(request, form_class, template_name, success_url, 
                          success_message, instance=None, extra_context=None, 
                          pre_save_callback=None, post_save_callback=None):
    """
    处理表单提交的通用方法
    
    Args:
        request: HTTP请求
        form_class: 表单类
        template_name: 模板名称
        success_url: 成功后重定向的URL
        success_message: 成功消息
        instance: 编辑时的实例对象
        extra_context: 额外的上下文数据
        pre_save_callback: 保存前的回调函数
        post_save_callback: 保存后的回调函数
        
    Returns:
        HttpResponse: 响应对象
    """
    from django.shortcuts import render, redirect
    
    context = extra_context or {}
    
    if request.method == 'POST':
        form = form_class(request.POST, request.FILES, instance=instance) if instance else form_class(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)
            
            # 执行保存前回调
            if pre_save_callback:
                pre_save_callback(obj, form)
                
            obj.save()
            form.save_m2m()  # 保存多对多关系
            
            # 执行保存后回调
            if post_save_callback:
                post_save_callback(obj, form)
                
            messages.success(request, success_message)
            return redirect(success_url)
    else:
        form = form_class(instance=instance) if instance else form_class()
    
    context['form'] = form
    return render(request, template_name, context)

def get_object_with_check(model_class, object_id, user=None, permission=None):
    """
    获取对象并检查权限的通用方法
    
    Args:
        model_class: 模型类
        object_id: 对象ID
        user: 用户对象
        permission: 需要检查的权限
        
    Returns:
        Model: 获取的对象
    """
    obj = get_object_or_404(model_class, id=object_id)
    
    # 如果需要检查权限
    if user and permission and not user.has_perm(permission):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied()
        
    return obj

def search_objects(queryset, search_term, search_fields):
    """
    通用搜索方法
    
    Args:
        queryset: 初始查询集
        search_term: 搜索词
        search_fields: 搜索字段列表
        
    Returns:
        QuerySet: 过滤后的查询集
    """
    if not search_term:
        return queryset
        
    q_objects = Q()
    for field in search_fields:
        q_objects |= Q(**{f"{field}__icontains": search_term})
        
    return queryset.filter(q_objects)

def require_ajax(view_func):
    """
    装饰器：确保视图只能通过AJAX调用
    
    Args:
        view_func: 被装饰的视图函数
        
    Returns:
        包装后的视图函数
    """
    from django.http import HttpResponseBadRequest
    from functools import wraps
    
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return HttpResponseBadRequest('该接口只接受AJAX请求')
        return view_func(request, *args, **kwargs)
    return wrapped

def require_post(view_func):
    """
    装饰器：确保视图只能通过POST方法调用
    
    Args:
        view_func: 被装饰的视图函数
        
    Returns:
        包装后的视图函数
    """
    from django.http import HttpResponseNotAllowed
    from functools import wraps
    
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if request.method != 'POST':
            return HttpResponseNotAllowed(['POST'], '该接口只接受POST请求')
        return view_func(request, *args, **kwargs)
    return wrapped

def get_referer_url(request, default_url='/'):
    """
    获取请求的Referer URL，如果不存在则返回默认URL
    
    Args:
        request: HTTP请求对象
        default_url: 默认的返回URL
        
    Returns:
        str: Referer URL或默认URL
    """
    referer = request.META.get('HTTP_REFERER')
    return referer if referer else default_url

def get_int_param(request, param_name, default=None):
    """
    从请求中获取整数参数
    
    Args:
        request: HTTP请求对象
        param_name: 参数名称
        default: 默认值
        
    Returns:
        int/None: 转换后的整数值或默认值
    """
    value = request.GET.get(param_name) or request.POST.get(param_name)
    if value:
        try:
            return int(value)
        except (ValueError, TypeError):
            pass
    return default