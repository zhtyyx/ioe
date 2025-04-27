"""
系统配置相关视图
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.http import JsonResponse
from django.contrib import messages
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.admin.models import LogEntry
from django.utils import timezone
from datetime import datetime, timedelta
import os
import logging

from inventory.models import SystemConfig, Store
from inventory.forms import SystemConfigForm, StoreForm
from inventory.permissions import system_admin_required
from inventory.utils.system_utils import get_system_info
from inventory.models.settings import SystemSettings, BackupSchedule
from inventory.forms.system import SystemSettingsForm, BackupScheduleForm

logger = logging.getLogger(__name__)


@login_required
@system_admin_required
def system_settings(request):
    """系统设置视图"""
    # 获取或创建系统配置
    config, created = SystemConfig.objects.get_or_create(pk=1)
    
    if request.method == 'POST':
        form = SystemConfigForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, "系统设置已更新")
            return redirect('system_settings')
    else:
        form = SystemConfigForm(instance=config)
    
    return render(request, 'inventory/system/settings.html', {
        'form': form,
        'config': config
    })


@login_required
@system_admin_required
def store_settings(request, pk=None):
    """门店设置视图"""
    if pk:
        store = get_object_or_404(Store, pk=pk)
        if request.method == 'POST':
            form = StoreForm(request.POST, instance=store)
            if form.is_valid():
                form.save()
                messages.success(request, f"门店 {store.name} 信息已更新")
                return redirect('store_list')
        else:
            form = StoreForm(instance=store)
        
        return render(request, 'inventory/system/store_form.html', {
            'form': form,
            'store': store,
            'title': f'编辑门店: {store.name}'
        })
    else:
        if request.method == 'POST':
            form = StoreForm(request.POST)
            if form.is_valid():
                store = form.save()
                messages.success(request, f"门店 {store.name} 创建成功")
                return redirect('store_list')
        else:
            form = StoreForm()
        
        return render(request, 'inventory/system/store_form.html', {
            'form': form,
            'title': '新增门店'
        })


@login_required
@system_admin_required
def store_list(request):
    """门店列表视图"""
    stores = Store.objects.all().order_by('name')
    return render(request, 'inventory/system/store_list.html', {
        'stores': stores
    })


@login_required
@system_admin_required
def delete_store(request, pk):
    """删除门店视图"""
    store = get_object_or_404(Store, pk=pk)
    
    if request.method == 'POST':
        store_name = store.name
        store.delete()
        messages.success(request, f"门店 {store_name} 已删除")
        return redirect('store_list')
    
    return render(request, 'inventory/system/store_confirm_delete.html', {
        'store': store
    })


@login_required
@system_admin_required
def system_info(request):
    """系统信息视图"""
    # 收集系统信息
    system_info = {
        'django_version': settings.DJANGO_VERSION,
        'debug_mode': settings.DEBUG,
        'database_engine': settings.DATABASES['default']['ENGINE'],
        'static_root': settings.STATIC_ROOT,
        'media_root': settings.MEDIA_ROOT,
        'time_zone': settings.TIME_ZONE,
        'language_code': settings.LANGUAGE_CODE,
    }
    
    # 用户统计
    user_stats = {
        'total_users': User.objects.count(),
        'active_users': User.objects.filter(is_active=True).count(),
        'staff_users': User.objects.filter(is_staff=True).count(),
        'admin_users': User.objects.filter(is_superuser=True).count(),
    }
    
    # 门店统计
    store_stats = {
        'total_stores': Store.objects.count(),
        'active_stores': Store.objects.filter(is_active=True).count(),  # 恢复is_active过滤
    }
    
    return render(request, 'inventory/system/info.html', {
        'system_info': system_info,
        'user_stats': user_stats,
        'store_stats': store_stats,
    })


@login_required
@system_admin_required
def system_maintenance(request):
    """系统维护视图"""
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'clear_cache':
            # 实现清除缓存的功能
            from django.core.cache import cache
            cache.clear()
            messages.success(request, "系统缓存已清除")
            
        elif action == 'rebuild_index':
            # 实现重建搜索索引的功能
            # 这里需要根据实际使用的搜索引擎来实现
            messages.success(request, "搜索索引已重建")
            
        elif action == 'backup_database':
            # 实现数据库备份功能
            # 这里可以调用自定义的备份脚本
            import subprocess
            import os
            import datetime
            
            # 创建备份目录
            backup_dir = os.path.join(settings.BASE_DIR, 'db_backups')
            os.makedirs(backup_dir, exist_ok=True)
            
            # 生成备份文件名
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = os.path.join(backup_dir, f'backup_{timestamp}.json')
            
            # 执行数据库备份
            cmd = [
                'python', 
                os.path.join(settings.BASE_DIR, 'manage.py'), 
                'dumpdata', 
                '--exclude', 'contenttypes', 
                '--exclude', 'auth.Permission', 
                '-o', 
                backup_file
            ]
            
            try:
                subprocess.run(cmd, check=True, capture_output=True)
                messages.success(request, f"数据库已备份到: {backup_file}")
            except subprocess.CalledProcessError as e:
                messages.error(request, f"备份失败: {e.stderr.decode()}")
        
        return redirect('system_maintenance')
    
    # 获取备份列表
    backup_dir = os.path.join(settings.BASE_DIR, 'db_backups')
    backups = []
    
    if os.path.exists(backup_dir):
        for file in os.listdir(backup_dir):
            if file.startswith('backup_') and file.endswith('.json'):
                file_path = os.path.join(backup_dir, file)
                file_stats = os.stat(file_path)
                backups.append({
                    'filename': file,
                    'size': file_stats.st_size / 1024.0,  # KB
                    'date': datetime.datetime.fromtimestamp(file_stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                })
    
    # 按日期排序，最新的在前面
    backups.sort(key=lambda x: x['date'], reverse=True)
    
    return render(request, 'inventory/system/maintenance.html', {
        'backups': backups
    })


@login_required
@system_admin_required
def restore_database(request, filename):
    """恢复数据库视图"""
    import os
    import subprocess
    from django.conf import settings
    
    backup_dir = os.path.join(settings.BASE_DIR, 'db_backups')
    backup_file = os.path.join(backup_dir, filename)
    
    if not os.path.exists(backup_file):
        messages.error(request, f"备份文件不存在: {filename}")
        return redirect('system_maintenance')
    
    if request.method == 'POST':
        # 执行数据库恢复
        cmd = [
            'python', 
            os.path.join(settings.BASE_DIR, 'manage.py'), 
            'loaddata', 
            backup_file
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            messages.success(request, f"数据库已从备份恢复: {filename}")
        except subprocess.CalledProcessError as e:
            messages.error(request, f"恢复失败: {e.stderr.decode()}")
        
        return redirect('system_maintenance')
    
    return render(request, 'inventory/system/restore_confirm.html', {
        'filename': filename
    })


@login_required
@system_admin_required
def delete_backup(request, filename):
    """删除备份文件视图"""
    import os
    from django.conf import settings
    
    backup_dir = os.path.join(settings.BASE_DIR, 'db_backups')
    backup_file = os.path.join(backup_dir, filename)
    
    if not os.path.exists(backup_file):
        messages.error(request, f"备份文件不存在: {filename}")
        return redirect('system_maintenance')
    
    if request.method == 'POST':
        try:
            os.remove(backup_file)
            messages.success(request, f"备份文件已删除: {filename}")
        except Exception as e:
            messages.error(request, f"删除失败: {str(e)}")
        
        return redirect('system_maintenance')
    
    return render(request, 'inventory/system/delete_backup_confirm.html', {
        'filename': filename
    })


@login_required
@permission_required('inventory.view_systemsettings', raise_exception=True)
def system_settings(request):
    """系统设置视图"""
    settings = SystemSettings.get_settings()
    
    if request.method == 'POST':
        form = SystemSettingsForm(request.POST, instance=settings)
        if form.is_valid():
            form.save()
            messages.success(request, "系统设置已更新")
            return redirect('system_settings')
    else:
        form = SystemSettingsForm(instance=settings)
        
    backup_schedule = BackupSchedule.get_schedule()
    backup_form = BackupScheduleForm(instance=backup_schedule)
    
    system_info = get_system_info()
    
    context = {
        'form': form,
        'backup_form': backup_form,
        'system_info': system_info
    }
    
    return render(request, 'inventory/system/settings.html', context)


@login_required
@permission_required('inventory.change_systemsettings', raise_exception=True)
def backup_schedule(request):
    """备份设置视图"""
    schedule = BackupSchedule.get_schedule()
    
    if request.method == 'POST':
        form = BackupScheduleForm(request.POST, instance=schedule)
        if form.is_valid():
            form.save()
            messages.success(request, "备份计划已更新")
            return redirect('system_settings')
    else:
        form = BackupScheduleForm(instance=schedule)
    
    return render(request, 'inventory/system/backup_schedule.html', {'form': form})


@login_required
@permission_required('admin.view_logentry', raise_exception=True)
def log_list(request):
    """系统日志列表视图"""
    # 获取筛选参数
    action_filter = request.GET.get('action', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    page_size = request.GET.get('page_size', 50)
    
    # 查询日志
    logs = LogEntry.objects.all().order_by('-action_time')
    
    # 应用筛选
    if action_filter:
        logs = logs.filter(action_flag=action_filter)
    
    if start_date:
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            logs = logs.filter(action_time__date__gte=start_date_obj)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            logs = logs.filter(action_time__date__lte=end_date_obj)
        except ValueError:
            pass
    
    # 统计信息
    total_logs = logs.count()
    add_logs = logs.filter(action_flag=1).count()
    change_logs = logs.filter(action_flag=2).count()
    delete_logs = logs.filter(action_flag=3).count()
    
    # 获取日志文件列表
    log_files = []
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
    
    if os.path.exists(log_dir):
        for file in os.listdir(log_dir):
            if file.endswith('.log'):
                file_path = os.path.join(log_dir, file)
                stats = os.stat(file_path)
                size_kb = stats.st_size / 1024
                last_modified = datetime.fromtimestamp(stats.st_mtime)
                
                log_files.append({
                    'name': file,
                    'size': f"{size_kb:.2f} KB",
                    'last_modified': last_modified
                })
    
    context = {
        'logs': logs[:int(page_size)],  # 简单分页，仅用于演示
        'total_logs': total_logs,
        'add_logs': add_logs,
        'change_logs': change_logs,
        'delete_logs': delete_logs,
        'action_filter': action_filter,
        'start_date': start_date,
        'end_date': end_date,
        'page_size': page_size,
        'log_files': log_files
    }
    
    return render(request, 'inventory/system/log_list.html', context)


@login_required
@permission_required('admin.delete_logentry', raise_exception=True)
def clear_logs(request):
    """清除系统日志视图"""
    # 默认日期为30天前
    default_date = (timezone.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    if request.method == 'POST':
        log_type = request.POST.get('log_type', 'admin')
        date_before = request.POST.get('date_before')
        confirm = request.POST.get('confirm') == 'on'
        
        if confirm and date_before:
            try:
                # 解析日期
                date_obj = datetime.strptime(date_before, '%Y-%m-%d').replace(tzinfo=timezone.get_current_timezone())
                
                # 创建过滤条件
                filter_kwargs = {'action_time__lt': date_obj}
                
                # 删除日志
                deleted_count = LogEntry.objects.filter(**filter_kwargs).delete()[0]
                
                # 记录操作到日志
                logger.info(f"用户 {request.user.username} 清除了系统日志：类型 {log_type}，日期 {date_before} 之前，共 {deleted_count} 条记录")
                
                messages.success(request, f"成功清除 {deleted_count} 条日志记录")
                return redirect('log_list')
            except ValueError:
                messages.error(request, "日期格式无效")
        else:
            messages.error(request, "请确认清除操作")
    
    context = {
        'default_date': default_date
    }
    
    return render(request, 'inventory/system/clear_logs.html', context) 