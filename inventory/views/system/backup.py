"""
系统备份和恢复相关视图
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.conf import settings
from django.urls import reverse
from django.contrib.admin.models import LogEntry
from django.core import management
from django.utils.text import slugify
import os
import json
import time
import shutil
import logging
import re
import zipfile
from datetime import datetime

from inventory.permissions.decorators import permission_required
from inventory.utils.logging import log_view_access
from inventory.services.backup_service import BackupService

# 获取logger
logger = logging.getLogger(__name__)

def get_dir_size_display(dir_path):
    """获取目录大小的友好显示"""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(dir_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if os.path.exists(fp):
                total_size += os.path.getsize(fp)
    
    # 转换为合适的单位
    size_bytes = total_size
    if size_bytes < 1024:
        return f"{size_bytes} bytes"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

@login_required
@permission_required('inventory.can_manage_backup')
def backup_list(request):
    """备份列表视图"""
    # 检查备份目录是否存在
    if not os.path.exists(settings.BACKUP_ROOT):
        os.makedirs(settings.BACKUP_ROOT, exist_ok=True)
    
    # 获取所有备份
    backups = []
    for backup_name in os.listdir(settings.BACKUP_ROOT):
        backup_dir = os.path.join(settings.BACKUP_ROOT, backup_name)
        if os.path.isdir(backup_dir):
            # 读取备份信息
            backup_info_file = os.path.join(backup_dir, 'backup_info.json')
            try:
                if os.path.exists(backup_info_file):
                    with open(backup_info_file, 'r', encoding='utf-8') as f:
                        backup_info = json.load(f)
                    
                    backups.append({
                        'name': backup_name,
                        'created_at': datetime.fromisoformat(backup_info.get('created_at', '')),
                        'created_by': backup_info.get('created_by', '未知'),
                        'size': get_dir_size_display(backup_dir),
                    })
            except Exception as e:
                logger.error(f"读取备份信息失败: {str(e)}")
    
    # 按创建时间排序
    backups.sort(key=lambda x: x['created_at'], reverse=True)
    
    return render(request, 'inventory/system/backup_list.html', {'backups': backups})

@login_required
@permission_required('inventory.can_manage_backup')
def create_backup(request):
    """创建备份视图"""
    # 生成建议的备份名称
    now = datetime.now()
    suggested_name = f"backup_{now.strftime('%Y%m%d_%H%M%S')}"
    
    if request.method == 'POST':
        # 获取表单数据
        backup_name = request.POST.get('backup_name', '').strip()
        if not backup_name:
            backup_name = suggested_name
        
        # 验证备份名称
        if not re.match(r'^[a-zA-Z0-9_\-]+$', backup_name):
            messages.error(request, "备份名称只能包含字母、数字、下划线和连字符")
            return render(request, 'inventory/system/create_backup.html', {'suggested_name': suggested_name})
        
        # 检查备份是否已存在
        backup_dir = os.path.join(settings.BACKUP_ROOT, backup_name)
        if os.path.exists(backup_dir):
            messages.error(request, f"备份 {backup_name} 已存在")
            return render(request, 'inventory/system/create_backup.html', {'suggested_name': suggested_name})
        
        # 创建备份目录
        os.makedirs(backup_dir, exist_ok=True)
        
        try:
            # 备份数据库
            db_file = os.path.join(backup_dir, 'db.json')
            management.call_command('dumpdata', '--exclude', 'auth.permission', '--exclude', 'contenttypes', 
                                  '--exclude', 'sessions.session', '--indent', '4', 
                                  '--output', db_file)
            
            # 备份媒体文件
            backup_media = request.POST.get('backup_media') == 'on'
            if backup_media and os.path.exists(settings.MEDIA_ROOT):
                media_dir = os.path.join(backup_dir, 'media')
                os.makedirs(media_dir, exist_ok=True)
                
                # 复制媒体文件
                for item in os.listdir(settings.MEDIA_ROOT):
                    src_path = os.path.join(settings.MEDIA_ROOT, item)
                    dst_path = os.path.join(media_dir, item)
                    if os.path.isdir(src_path):
                        shutil.copytree(src_path, dst_path)
                    else:
                        shutil.copy2(src_path, dst_path)
            
            # 备份描述
            backup_description = request.POST.get('backup_description', '').strip()
            
            # 保存备份信息
            backup_info = {
                'name': backup_name,
                'created_at': now.isoformat(),
                'created_by': request.user.username,
                'description': backup_description,
                'includes_media': backup_media,
            }
            
            backup_info_file = os.path.join(backup_dir, 'backup_info.json')
            with open(backup_info_file, 'w', encoding='utf-8') as f:
                json.dump(backup_info, f, indent=4, ensure_ascii=False)
            
            # 记录日志
            LogEntry.objects.create(
                user=request.user,
                action_flag=1,  # 添加
                content_type_id=0,  # 自定义内容类型
                object_id=backup_name,
                object_repr=f'备份: {backup_name}',
                change_message=f'创建了系统备份 {backup_name}' + (' 包含媒体文件' if backup_media else '')
            )
            
            messages.success(request, f"成功创建备份: {backup_name}")
            return redirect('backup_list')
            
        except Exception as e:
            # 备份失败，清理备份目录
            if os.path.exists(backup_dir):
                shutil.rmtree(backup_dir)
            
            messages.error(request, f"创建备份失败: {str(e)}")
            logger.error(f"创建备份失败: {str(e)}")
            return render(request, 'inventory/system/create_backup.html', {'suggested_name': suggested_name})
    
    return render(request, 'inventory/system/create_backup.html', {'suggested_name': suggested_name})

@login_required
@permission_required('inventory.can_manage_backup')
def restore_backup(request, backup_name):
    """恢复备份视图"""
    # 检查备份是否存在
    backup_dir = os.path.join(settings.BACKUP_ROOT, backup_name)
    if not os.path.exists(backup_dir):
        messages.error(request, f"备份 {backup_name} 不存在")
        return redirect('backup_list')
    
    # 获取备份信息
    backup_info_file = os.path.join(backup_dir, 'backup_info.json')
    backup_info = {}
    if os.path.exists(backup_info_file):
        with open(backup_info_file, 'r', encoding='utf-8') as f:
            backup_info = json.load(f)
    
    if request.method == 'POST':
        # 确认恢复
        confirmed = request.POST.get('confirm') == 'on'
        if not confirmed:
            messages.error(request, "请确认您要恢复备份")
            return render(request, 'inventory/system/restore_backup.html', {
                'backup_name': backup_name,
                'backup_info': backup_info
            })
        
        try:
            # 恢复数据库
            db_file = os.path.join(backup_dir, 'db.json')
            if not os.path.exists(db_file):
                messages.error(request, f"备份文件 {db_file} 不存在")
                return redirect('backup_list')
            
            # 执行恢复
            management.call_command('loaddata', db_file)
            
            # 恢复媒体文件
            restore_media = request.POST.get('restore_media') == 'on'
            if restore_media and backup_info.get('includes_media', False):
                media_dir = os.path.join(backup_dir, 'media')
                if os.path.exists(media_dir):
                    # 清空现有媒体目录
                    if os.path.exists(settings.MEDIA_ROOT):
                        for item in os.listdir(settings.MEDIA_ROOT):
                            item_path = os.path.join(settings.MEDIA_ROOT, item)
                            if os.path.isdir(item_path):
                                shutil.rmtree(item_path)
                            else:
                                os.remove(item_path)
                    
                    # 复制备份中的媒体文件
                    for item in os.listdir(media_dir):
                        src_path = os.path.join(media_dir, item)
                        dst_path = os.path.join(settings.MEDIA_ROOT, item)
                        if os.path.isdir(src_path):
                            if os.path.exists(dst_path):
                                shutil.rmtree(dst_path)
                            shutil.copytree(src_path, dst_path)
                        else:
                            if os.path.exists(dst_path):
                                os.remove(dst_path)
                            shutil.copy2(src_path, dst_path)
            
            # 记录日志
            LogEntry.objects.create(
                user=request.user,
                action_flag=2,  # 修改
                content_type_id=0,  # 自定义内容类型
                object_id=backup_name,
                object_repr=f'恢复备份: {backup_name}',
                change_message=f'恢复了系统备份 {backup_name}' + (' 包含媒体文件' if restore_media else '')
            )
            
            messages.success(request, f"成功恢复备份: {backup_name}")
            return redirect('system_settings')
            
        except Exception as e:
            messages.error(request, f"恢复备份失败: {str(e)}")
            logger.error(f"恢复备份失败: {str(e)}")
            return render(request, 'inventory/system/restore_backup.html', {
                'backup_name': backup_name,
                'backup_info': backup_info
            })
    
    return render(request, 'inventory/system/restore_backup.html', {
        'backup_name': backup_name,
        'backup_info': backup_info
    })

@login_required
@permission_required('inventory.can_manage_backup')
def delete_backup(request, backup_name):
    """删除备份视图"""
    # 检查备份是否存在
    backup_dir = os.path.join(settings.BACKUP_ROOT, backup_name)
    if not os.path.exists(backup_dir):
        messages.error(request, f"备份 {backup_name} 不存在")
        return redirect('backup_list')
    
    if request.method == 'POST':
        # 确认删除
        confirmed = request.POST.get('confirm') == 'on'
        if not confirmed:
            messages.error(request, "请确认您要删除备份")
            return render(request, 'inventory/system/delete_backup.html', {'backup_name': backup_name})
        
        try:
            # 删除备份目录
            shutil.rmtree(backup_dir)
            
            # 记录日志
            LogEntry.objects.create(
                user=request.user,
                action_flag=3,  # 删除
                content_type_id=0,  # 自定义内容类型
                object_id=backup_name,
                object_repr=f'删除备份: {backup_name}',
                change_message=f'删除了系统备份 {backup_name}'
            )
            
            messages.success(request, f"成功删除备份: {backup_name}")
            return redirect('backup_list')
            
        except Exception as e:
            messages.error(request, f"删除备份失败: {str(e)}")
            logger.error(f"删除备份失败: {str(e)}")
            return render(request, 'inventory/system/delete_backup.html', {'backup_name': backup_name})
    
    return render(request, 'inventory/system/delete_backup.html', {'backup_name': backup_name})

@login_required
@permission_required('inventory.can_manage_backup')
def download_backup(request, backup_name):
    """下载备份视图"""
    # 检查备份是否存在
    backup_dir = os.path.join(settings.BACKUP_ROOT, backup_name)
    if not os.path.exists(backup_dir):
        messages.error(request, f"备份 {backup_name} 不存在")
        return redirect('backup_list')
    
    # 创建临时ZIP文件
    temp_file = os.path.join(settings.TEMP_DIR, f"{backup_name}.zip")
    
    try:
        # 创建ZIP文件
        with zipfile.ZipFile(temp_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 添加备份文件
            for root, dirs, files in os.walk(backup_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    zipf.write(file_path, os.path.relpath(file_path, os.path.dirname(backup_dir)))
        
        # 打开文件供下载
        with open(temp_file, 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/zip')
            response['Content-Disposition'] = f'attachment; filename="{backup_name}.zip"'
            
            # 记录日志
            LogEntry.objects.create(
                user=request.user,
                action_flag=1,  # 添加
                content_type_id=0,  # 自定义内容类型
                object_id=backup_name,
                object_repr=f'下载备份: {backup_name}',
                change_message=f'下载了系统备份 {backup_name}'
            )
            
            return response
            
    except Exception as e:
        messages.error(request, f"下载备份失败: {str(e)}")
        logger.error(f"下载备份失败: {str(e)}")
        return redirect('backup_list')
    finally:
        # 清理临时文件
        if os.path.exists(temp_file):
            os.remove(temp_file)

@login_required
@log_view_access('OTHER')
@permission_required('is_superuser')
def manual_backup(request):
    """
    手动备份API
    """
    if request.method == 'POST':
        try:
            backup_name = f"manual_{timezone.now().strftime('%Y%m%d_%H%M%S')}"
            backup_path = BackupService.create_backup(backup_name=backup_name, user=request.user)
            return JsonResponse({
                'success': True,
                'backup_name': backup_name,
                'message': '备份创建成功'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'备份创建失败: {str(e)}'
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'message': '不支持的请求方法'
    }, status=405) 