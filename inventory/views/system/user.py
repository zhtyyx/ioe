from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User, Group, Permission
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from django.http import JsonResponse
from django.contrib.contenttypes.models import ContentType

from ...models.common import OperationLog


@login_required
@permission_required('auth.view_user', raise_exception=True)
def user_list(request):
    """用户列表视图"""
    # 获取筛选参数
    search_query = request.GET.get('search', '')
    is_active = request.GET.get('is_active', '')
    user_group = request.GET.get('group', '')
    
    # 基本查询集
    users = User.objects.select_related('profile').prefetch_related('groups').all()
    
    # 应用筛选
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) | 
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    if is_active:
        users = users.filter(is_active=(is_active == 'true'))
    
    if user_group:
        users = users.filter(groups__id=user_group)
    
    # 获取用户组
    groups = Group.objects.all()
    
    context = {
        'users': users,
        'groups': groups,
        'search_query': search_query,
        'is_active': is_active,
        'user_group': user_group
    }
    
    return render(request, 'inventory/system/user_list.html', context)


@login_required
@permission_required('auth.add_user', raise_exception=True)
def user_create(request):
    """创建用户视图"""
    groups = Group.objects.all()
    
    # 确保销售员组存在
    sales_group, created = Group.objects.get_or_create(name='销售员')
    
    # 如果是新创建的组，为其设置相应权限
    if created:
        # 销售相关权限
        content_types = ContentType.objects.filter(
            Q(app_label='inventory', model='sale') |
            Q(app_label='inventory', model='saleitem') |
            Q(app_label='inventory', model='member')
        )
        permissions = Permission.objects.filter(content_type__in=content_types)
        sales_group.permissions.add(*permissions)
        
        # 记录日志
        OperationLog.objects.create(
            operator=request.user,
            operation_type='ADD',
            details=f'创建销售员用户组并设置权限',
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        email = request.POST.get('email', '')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        is_active = request.POST.get('is_active') == 'on'
        is_staff = request.POST.get('is_staff') == 'on'
        is_superuser = request.POST.get('is_superuser') == 'on'
        group_ids = request.POST.getlist('groups')
        
        # 表单验证
        errors = []
        
        # 用户名验证
        if not username:
            errors.append('用户名不能为空')
        elif User.objects.filter(username=username).exists():
            errors.append('用户名已存在')
        
        # 密码验证
        if not password:
            errors.append('密码不能为空')
        elif len(password) < 8:
            errors.append('密码长度至少为8个字符')
        elif password != password_confirm:
            errors.append('两次输入的密码不一致')
        
        # 如果有错误，返回错误信息
        if errors:
            messages.error(request, '\n'.join(errors))
            return render(request, 'inventory/system/user_create.html', {
                'groups': groups,
                'form_data': request.POST
            })
        
        # 创建用户
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_active=is_active,
            is_staff=is_staff,
            is_superuser=is_superuser
        )
        
        # 分配用户组
        if group_ids:
            selected_groups = Group.objects.filter(id__in=group_ids)
            user.groups.add(*selected_groups)
        
        # 记录操作日志
        OperationLog.objects.create(
            operator=request.user,
            operation_type='ADD',
            details=f'创建用户: {username}',
            related_object_id=user.id,
            related_content_type=ContentType.objects.get_for_model(user),
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
        
        messages.success(request, f'用户 {username} 创建成功')
        return redirect('user_list')
    
    return render(request, 'inventory/system/user_create.html', {
        'groups': groups
    })


@login_required
@permission_required('auth.change_user', raise_exception=True)
def user_update(request, pk):
    """更新用户视图"""
    user = get_object_or_404(User, pk=pk)
    groups = Group.objects.all()
    
    if request.method == 'POST':
        email = request.POST.get('email', '')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        is_active = request.POST.get('is_active') == 'on'
        is_staff = request.POST.get('is_staff') == 'on'
        is_superuser = request.POST.get('is_superuser') == 'on'
        group_ids = request.POST.getlist('groups')
        new_password = request.POST.get('new_password', '')
        new_password_confirm = request.POST.get('new_password_confirm', '')
        
        # 表单验证
        errors = []
        
        # 密码验证
        if new_password:
            if len(new_password) < 8:
                errors.append('密码长度至少为8个字符')
            elif new_password != new_password_confirm:
                errors.append('两次输入的密码不一致')
        
        # 如果有错误，返回错误信息
        if errors:
            messages.error(request, '\n'.join(errors))
            return render(request, 'inventory/system/user_update.html', {
                'user': user,
                'groups': groups,
                'form_data': request.POST
            })
        
        # 更新用户信息
        user.email = email
        user.first_name = first_name
        user.last_name = last_name
        user.is_active = is_active
        user.is_staff = is_staff
        user.is_superuser = is_superuser
        
        # 如果提供了新密码，更新密码
        if new_password:
            user.set_password(new_password)
        
        user.save()
        
        # 更新用户组
        user.groups.clear()
        if group_ids:
            selected_groups = Group.objects.filter(id__in=group_ids)
            user.groups.add(*selected_groups)
        
        # 记录操作日志
        OperationLog.objects.create(
            operator=request.user,
            operation_type='CHANGE',
            details=f'更新用户: {user.username}',
            related_object_id=user.id,
            related_content_type=ContentType.objects.get_for_model(user),
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
        
        messages.success(request, f'用户 {user.username} 更新成功')
        return redirect('user_list')
    
    return render(request, 'inventory/system/user_update.html', {
        'user': user,
        'groups': groups
    })


@login_required
@permission_required('auth.delete_user', raise_exception=True)
def user_delete(request, pk):
    """删除用户视图"""
    user = get_object_or_404(User, pk=pk)
    
    # 防止删除自己
    if user == request.user:
        messages.error(request, '不能删除当前登录的用户')
        return redirect('user_list')
    
    if request.method == 'POST':
        username = user.username
        user.delete()
        
        # 记录操作日志
        OperationLog.objects.create(
            operator=request.user,
            operation_type='DELETE',
            details=f'删除用户: {username}',
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
        
        messages.success(request, f'用户 {username} 已删除')
        return redirect('user_list')
    
    return render(request, 'inventory/system/user_delete.html', {
        'user': user
    })


@login_required
@permission_required('auth.view_user', raise_exception=True)
def user_detail(request, pk):
    """用户详情视图"""
    user = get_object_or_404(User, pk=pk)
    
    # 获取用户最近的操作日志
    logs = OperationLog.objects.filter(operator=user).order_by('-timestamp')[:20]
    
    return render(request, 'inventory/system/user_detail.html', {
        'user': user,
        'logs': logs
    }) 