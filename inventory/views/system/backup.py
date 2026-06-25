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
from django.contrib.auth import get_user_model
from django.core import management
from django.db import transaction
from django.utils.text import slugify
import os
import json
import time
import shutil
import logging
import re
import zipfile
import tempfile
from datetime import datetime

from inventory.permissions.decorators import permission_required
from inventory.utils.logging import log_view_access
from inventory.services.backup_service import BackupService

# 获取logger
logger = logging.getLogger(__name__)

BACKUP_NAME_RE = re.compile(r'^[a-zA-Z0-9_\-]+$')


def get_safe_backup_dir(backup_name):
    """Return a backup path guaranteed to stay within BACKUP_ROOT."""
    if not BACKUP_NAME_RE.fullmatch(backup_name or ''):
        raise ValueError("无效的备份名称")

    backup_root = os.path.realpath(settings.BACKUP_ROOT)
    backup_dir = os.path.realpath(os.path.join(backup_root, backup_name))
    if os.path.commonpath([backup_root, backup_dir]) != backup_root:
        raise ValueError("无效的备份路径")
    return backup_dir


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


def get_restore_context(backup_name, backup_info, backup_dir):
    """Build the restore template context from the on-disk backup metadata."""
    created_at = backup_info.get('created_at')
    try:
        created_at = datetime.fromisoformat(created_at) if created_at else None
    except (TypeError, ValueError):
        created_at = None

    return {
        'backup_name': backup_name,
        'backup_info': backup_info,
        'backup': {
            'name': backup_name,
            'created_at': created_at,
            'created_by': backup_info.get('created_by', '未知'),
            'size': get_dir_size_display(backup_dir),
            'includes_media': backup_info.get('includes_media', False),
        },
    }


def remove_media_root(media_root):
    if not os.path.exists(media_root):
        return
    if os.path.isdir(media_root):
        shutil.rmtree(media_root)
    else:
        os.remove(media_root)


def restore_previous_media_root(media_root, current_media_backup, current_media_backup_parent):
    """Best-effort rollback for media replacement after a failed restore."""
    if current_media_backup and os.path.exists(current_media_backup):
        remove_media_root(media_root)
        shutil.move(current_media_backup, media_root)
    elif os.path.exists(media_root):
        remove_media_root(media_root)

    if current_media_backup_parent and os.path.exists(current_media_backup_parent):
        shutil.rmtree(current_media_backup_parent, ignore_errors=True)

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
        if not BACKUP_NAME_RE.fullmatch(backup_name):
            messages.error(request, "备份名称只能包含字母、数字、下划线和连字符")
            return render(request, 'inventory/system/create_backup.html', {'suggested_name': suggested_name})
        
        # 检查备份是否已存在
        backup_dir = get_safe_backup_dir(backup_name)
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
                content_type_id=None,  # 自定义日志，无关联内容类型（id=0 会违反外键约束）
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
    try:
        backup_dir = get_safe_backup_dir(backup_name)
    except ValueError:
        messages.error(request, "无效的备份名称")
        return redirect('backup_list')

    if not os.path.exists(backup_dir):
        messages.error(request, f"备份 {backup_name} 不存在")
        return redirect('backup_list')
    
    # 获取备份信息
    backup_info_file = os.path.join(backup_dir, 'backup_info.json')
    backup_info = {}
    if os.path.exists(backup_info_file):
        with open(backup_info_file, 'r', encoding='utf-8') as f:
            backup_info = json.load(f)
    restore_context = get_restore_context(backup_name, backup_info, backup_dir)
    
    if request.method == 'POST':
        # 确认恢复
        confirmed = request.POST.get('confirm') == 'on' or request.POST.get('confirm_restore') == 'on'
        if not confirmed:
            messages.error(request, "请确认您要恢复备份")
            return render(request, 'inventory/system/restore_backup.html', restore_context)
        
        restore_temp_dir = None
        current_media_backup = None
        current_media_backup_parent = None
        media_replaced = False
        media_replacement_started = False
        try:
            # 恢复数据库
            db_file = os.path.join(backup_dir, 'db.json')
            if not os.path.exists(db_file):
                messages.error(request, f"备份文件 {db_file} 不存在")
                return redirect('backup_list')

            restore_media = request.POST.get('restore_media') == 'on'
            staged_media_dir = None
            if restore_media and backup_info.get('includes_media', False):
                media_dir = os.path.join(backup_dir, 'media')
                if os.path.exists(media_dir):
                    restore_temp_dir = tempfile.mkdtemp(prefix='restore-media-', dir=settings.TEMP_DIR)
                    staged_media_dir = os.path.join(restore_temp_dir, 'media')
                    shutil.copytree(media_dir, staged_media_dir)
            
            # 先清空数据库再加载快照；loaddata 只会 upsert，不能删除备份后新增的数据。
            # 媒体替换也放在事务块中，替换失败时让数据库恢复一起回滚。
            with transaction.atomic():
                management.call_command('flush', '--noinput', verbosity=0)
                management.call_command('loaddata', db_file, verbosity=0)

                # 恢复媒体文件
                if staged_media_dir:
                    os.makedirs(os.path.dirname(settings.MEDIA_ROOT), exist_ok=True)
                    if os.path.exists(settings.MEDIA_ROOT):
                        current_media_backup_parent = tempfile.mkdtemp(prefix='current-media-', dir=settings.TEMP_DIR)
                        current_media_backup = os.path.join(current_media_backup_parent, 'media')
                        shutil.move(settings.MEDIA_ROOT, current_media_backup)
                    media_replacement_started = True
                    shutil.copytree(staged_media_dir, settings.MEDIA_ROOT)
                    media_replaced = True

                # 恢复快照后，执行恢复的用户可能已不存在于当前数据库。
                restored_user = get_user_model().objects.filter(pk=request.user.pk).first()
                if restored_user:
                    LogEntry.objects.create(
                        user=restored_user,
                        action_flag=2,  # 修改
                        content_type_id=None,  # 自定义日志，无关联内容类型（id=0 会违反外键约束）
                        object_id=backup_name,
                        object_repr=f'恢复备份: {backup_name}',
                        change_message=f'恢复了系统备份 {backup_name}' + (' 包含媒体文件' if restore_media else '')
                    )
                else:
                    logger.warning("恢复备份后执行用户不存在，跳过管理日志记录: %s", backup_name)

            if current_media_backup_parent and os.path.exists(current_media_backup_parent):
                shutil.rmtree(current_media_backup_parent, ignore_errors=True)
            
            messages.success(request, f"成功恢复备份: {backup_name}")
            return redirect('system_settings')
            
        except Exception as e:
            if current_media_backup or media_replacement_started or media_replaced:
                try:
                    restore_previous_media_root(
                        settings.MEDIA_ROOT,
                        current_media_backup,
                        current_media_backup_parent,
                    )
                except Exception as rollback_error:
                    logger.error(f"恢复媒体文件回滚失败: {str(rollback_error)}")
            messages.error(request, f"恢复备份失败: {str(e)}")
            logger.error(f"恢复备份失败: {str(e)}")
            return render(request, 'inventory/system/restore_backup.html', restore_context)
        finally:
            if restore_temp_dir and os.path.exists(restore_temp_dir):
                shutil.rmtree(restore_temp_dir, ignore_errors=True)
    
    return render(request, 'inventory/system/restore_backup.html', restore_context)

@login_required
@permission_required('inventory.can_manage_backup')
def delete_backup(request, backup_name):
    """删除备份视图"""
    # 检查备份是否存在
    try:
        backup_dir = get_safe_backup_dir(backup_name)
    except ValueError:
        messages.error(request, "无效的备份名称")
        return redirect('backup_list')

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
                content_type_id=None,  # 自定义日志，无关联内容类型（id=0 会违反外键约束）
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
    try:
        backup_dir = get_safe_backup_dir(backup_name)
    except ValueError:
        messages.error(request, "无效的备份名称")
        return redirect('backup_list')

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
                content_type_id=None,  # 自定义日志，无关联内容类型（id=0 会违反外键约束）
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