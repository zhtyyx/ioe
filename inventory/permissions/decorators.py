"""
Permission decorators for views.
"""
import functools
from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse

from inventory.exceptions import AuthorizationError

def permission_required(perm):
    """
    Decorator for views that checks whether a user has a particular permission.
    If not, raises AuthorizationError.
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.has_perm(perm):
                error_message = f"您没有权限执行此操作: {perm}"
                raise AuthorizationError(error_message, code="permission_denied")
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

def group_required(group_name):
    """
    Decorator for views that checks if a user is in a particular group.
    If not, raises AuthorizationError.
    """
    def check_group(user):
        if user.is_superuser:
            return True
        if user.groups.filter(name=group_name).exists():
            return True
        return False
    
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not check_group(request.user):
                error_message = f"您不属于 {group_name} 组，无法执行此操作"
                raise AuthorizationError(error_message, code="group_required")
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

def superuser_required(view_func):
    """
    Decorator for views that checks if the user is a superuser.
    If not, raises AuthorizationError.
    """
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_superuser:
            error_message = "需要超级管理员权限才能执行此操作"
            raise AuthorizationError(error_message, code="superuser_required")
        return view_func(request, *args, **kwargs)
    return wrapper

def owner_or_permission_required(owner_field, permission):
    """
    Decorator for views that checks if the user is the owner of the object 
    or has the specified permission.
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Get the object from the view
            obj = view_func.__globals__['get_object_or_404'](
                view_func.__globals__[owner_field.split('__')[0]], 
                pk=kwargs.get('pk', kwargs.get(f'{owner_field.split("__")[0]}_id'))
            )
            
            # Check if user is the owner
            is_owner = False
            owner_chain = owner_field.split('__')
            owner = obj
            for attr in owner_chain:
                owner = getattr(owner, attr)
            
            is_owner = owner == request.user
            
            # If not owner, check permission
            if not is_owner and not request.user.has_perm(permission):
                error_message = f"您不是此资源的拥有者，也没有执行此操作的权限: {permission}"
                raise AuthorizationError(error_message, code="not_owner_or_perm_denied")
                
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

def system_admin_required(view_func):
    """
    装饰器，检查用户是否是系统管理员。
    如果不是，会重定向到首页或显示权限错误页面。
    """
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_superuser or (
            request.user.groups.filter(name='系统管理员').exists() or 
            request.user.groups.filter(name='admin').exists()
        ):
            return view_func(request, *args, **kwargs)
        else:
            # 重定向到首页并显示错误消息
            from django.contrib import messages
            messages.error(request, "您需要系统管理员权限才能访问此页面")
            return redirect('index')
    return wrapper 