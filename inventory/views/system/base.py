"""
系统设置和信息相关视图
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.utils import timezone
import os
import platform
import django
import psutil
import time
import logging

from inventory.permissions.decorators import permission_required
from inventory.utils.logging import log_view_access

# 获取logger
logger = logging.getLogger(__name__)

@login_required
@log_view_access('OTHER')
@permission_required('is_superuser')
def system_settings(request):
    """
    系统设置视图
    """
    context = {
        'settings': {
            'debug_mode': settings.DEBUG,
            'media_root': settings.MEDIA_ROOT,
            'timezone': settings.TIME_ZONE,
            'database_engine': settings.DATABASES['default']['ENGINE'],
            'version': getattr(settings, 'VERSION', '1.0.0'),
        }
    }
    return render(request, 'inventory/system/settings.html', context)

@login_required
@log_view_access('OTHER')
@permission_required('is_superuser')
def system_info(request):
    """
    系统信息视图，显示系统运行状态和环境信息
    """
    # 获取系统信息
    system_info = {
        'os': platform.system(),
        'os_version': platform.version(),
        'python_version': platform.python_version(),
        'django_version': django.__version__,
        'cpu_count': psutil.cpu_count(),
        'memory_total': round(psutil.virtual_memory().total / (1024 * 1024 * 1024), 2),  # GB
        'memory_available': round(psutil.virtual_memory().available / (1024 * 1024 * 1024), 2),  # GB
        'disk_total': round(psutil.disk_usage('/').total / (1024 * 1024 * 1024), 2),  # GB
        'disk_free': round(psutil.disk_usage('/').free / (1024 * 1024 * 1024), 2),  # GB
        'hostname': platform.node(),
        'server_time': timezone.now(),
        'uptime': round((time.time() - psutil.boot_time()) / 3600, 2),  # 小时
    }
    
    # 获取数据库统计信息
    from django.db import connection
    db_stats = {}
    
    # 各个主要表的记录数量
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM inventory_product")
        db_stats['product_count'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM inventory_category")
        db_stats['category_count'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM inventory_inventory")
        db_stats['inventory_count'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM inventory_sale")
        db_stats['sale_count'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM inventory_member")
        db_stats['member_count'] = cursor.fetchone()[0]
    
    # 目录和文件大小
    media_size = 0
    if os.path.exists(settings.MEDIA_ROOT):
        for dirpath, dirnames, filenames in os.walk(settings.MEDIA_ROOT):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                media_size += os.path.getsize(fp)
    
    # 转换为MB
    media_size_mb = round(media_size / (1024 * 1024), 2)
    
    # 系统日志统计
    log_file = os.path.join(settings.BASE_DIR, 'logs', 'inventory.log')
    log_size_mb = 0
    log_entries = 0
    if os.path.exists(log_file):
        log_size_mb = round(os.path.getsize(log_file) / (1024 * 1024), 2)
        # 统计日志条目数（简单近似）
        with open(log_file, 'r') as f:
            log_entries = sum(1 for _ in f)
    
    # 组合所有信息
    context = {
        'system_info': system_info,
        'db_stats': db_stats,
        'media_size_mb': media_size_mb,
        'log_size_mb': log_size_mb,
        'log_entries': log_entries,
    }
    
    return render(request, 'inventory/system/system_info.html', context)

@login_required
@log_view_access('OTHER')
@permission_required('is_superuser')
def store_settings(request):
    """
    商店设置视图
    """
    from inventory.models import Store
    
    # 获取当前的商店设置
    store = Store.objects.first()
    
    if request.method == 'POST':
        # 更新商店设置
        store_name = request.POST.get('store_name')
        address = request.POST.get('address')
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        website = request.POST.get('website')
        store_description = request.POST.get('store_description')
        logo = request.FILES.get('logo')
        
        if not store:
            store = Store()
        
        store.name = store_name
        store.address = address
        store.phone = phone
        store.email = email
        store.website = website
        store.description = store_description
        
        if logo:
            store.logo = logo
        
        store.save()
        messages.success(request, '商店设置已更新')
        return redirect('store_settings')
    
    return render(request, 'inventory/system/store_settings.html', {'store': store})

@login_required
@log_view_access('OTHER')
@permission_required('is_superuser')
def store_list(request):
    """
    商店列表视图
    """
    from inventory.models import Store
    
    stores = Store.objects.all()
    return render(request, 'inventory/system/store_list.html', {'stores': stores})

@login_required
@log_view_access('OTHER')
@permission_required('is_superuser')
def delete_store(request, store_id):
    """
    删除商店视图
    """
    from inventory.models import Store
    
    store = Store.objects.get(pk=store_id)
    store.delete()
    messages.success(request, f'商店"{store.name}"已删除')
    return redirect('store_list')

@login_required
@log_view_access('OTHER')
@permission_required('is_superuser')
def system_maintenance(request):
    """
    系统维护视图，提供系统清理和优化功能
    """
    # 执行维护操作
    if request.method == 'POST':
        operation = request.POST.get('operation')
        
        if operation == 'clear_sessions':
            from django.contrib.sessions.models import Session
            # 清理过期会话
            Session.objects.filter(expire_date__lt=timezone.now()).delete()
            messages.success(request, '过期会话已清理')
            
        elif operation == 'clear_logs':
            # 清理日志文件（保留最近的10000行）
            log_file = os.path.join(settings.BASE_DIR, 'logs', 'inventory.log')
            if os.path.exists(log_file):
                try:
                    # 读取最后10000行
                    with open(log_file, 'r') as f:
                        lines = f.readlines()
                        last_lines = lines[-10000:] if len(lines) > 10000 else lines
                    
                    # 重写日志文件
                    with open(log_file, 'w') as f:
                        f.writelines(last_lines)
                    
                    messages.success(request, '日志文件已清理')
                except Exception as e:
                    messages.error(request, f'清理日志文件失败: {str(e)}')
            
        elif operation == 'optimize_db':
            # 执行数据库优化
            try:
                from django.db import connection
                with connection.cursor() as cursor:
                    if 'sqlite' in connection.vendor:
                        cursor.execute("VACUUM")
                    elif 'postgresql' in connection.vendor:
                        cursor.execute("VACUUM ANALYZE")
                    elif 'mysql' in connection.vendor:
                        cursor.execute("OPTIMIZE TABLE")
                
                messages.success(request, '数据库已优化')
            except Exception as e:
                messages.error(request, f'数据库优化失败: {str(e)}')
        
        return redirect('system_maintenance')
    
    # 获取系统状态信息
    disk_usage = psutil.disk_usage('/')
    disk_usage_percent = disk_usage.percent
    memory_usage = psutil.virtual_memory()
    memory_usage_percent = memory_usage.percent
    
    # 日志文件大小
    log_file = os.path.join(settings.BASE_DIR, 'logs', 'inventory.log')
    log_size_mb = 0
    if os.path.exists(log_file):
        log_size_mb = round(os.path.getsize(log_file) / (1024 * 1024), 2)
    
    # 会话数量
    from django.contrib.sessions.models import Session
    active_sessions = Session.objects.filter(expire_date__gt=timezone.now()).count()
    expired_sessions = Session.objects.filter(expire_date__lt=timezone.now()).count()
    
    context = {
        'disk_usage_percent': disk_usage_percent,
        'memory_usage_percent': memory_usage_percent,
        'log_size_mb': log_size_mb,
        'active_sessions': active_sessions,
        'expired_sessions': expired_sessions,
    }
    
    return render(request, 'inventory/system/maintenance.html', context) 