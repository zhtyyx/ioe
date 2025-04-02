from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, FileResponse
from django.utils import timezone
from django.conf import settings
from django.urls import reverse
import os
import json
import time
import shutil
import logging
import re
import zipfile
from datetime import datetime, timedelta
from django.contrib.admin.models import LogEntry
from django.core import management
from django.http import HttpResponse
from django.utils.text import slugify
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.db import connection
import io
import subprocess

from .permissions.decorators import permission_required
from .utils.logging import log_view_access
from .services.backup_service import BackupService

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
@user_passes_test(lambda u: u.is_superuser)
def system_settings(request):
    """
    系统设置视图 - 仅管理员可访问
    """
    if request.method == 'POST':
        # 处理系统设置更新
        pass
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
@permission_required('inventory.can_manage_backup')
def backup_list(request):
    """显示备份列表"""
    backups = []
    backup_dir = settings.BACKUP_ROOT
    
    if os.path.exists(backup_dir):
        for filename in os.listdir(backup_dir):
            if filename.endswith('.zip'):
                file_path = os.path.join(backup_dir, filename)
                file_stat = os.stat(file_path)
                backups.append({
                    'name': filename,
                    'size': file_stat.st_size,
                    'created_at': datetime.fromtimestamp(file_stat.st_ctime),
                    'path': file_path
                })
    
    # 按创建时间降序排序
    backups.sort(key=lambda x: x['created_at'], reverse=True)
    return render(request, 'inventory/system/backup_list.html', {'backups': backups})

@login_required
@permission_required('inventory.can_manage_backup')
def create_backup(request):
    """创建数据库备份"""
    try:
        # 创建备份文件名
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"{settings.BACKUP_PREFIX}{timestamp}.{settings.BACKUP_FORMAT}"
        backup_path = os.path.join(settings.BACKUP_ROOT, backup_name)
        
        # 确保备份目录存在
        os.makedirs(settings.BACKUP_ROOT, exist_ok=True)
        
        # 创建ZIP文件
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 导出数据库
            db_settings = settings.DATABASES['default']
            db_name = db_settings['NAME']
            db_user = db_settings['USER']
            db_host = db_settings['HOST']
            db_port = db_settings['PORT']
            
            # 使用pgpass文件存储密码
            pgpass_dir = os.path.expanduser('~/.pgpass')
            pgpass_path = os.path.join(pgpass_dir, 'pgpass')
            
            # 确保.pgpass目录存在
            os.makedirs(pgpass_dir, exist_ok=True)
            
            # 创建临时pgpass文件
            with open(pgpass_path, 'w') as f:
                f.write(f"{db_host}:{db_port}:*:{db_user}:{db_settings['PASSWORD']}\n")
            
            # 设置正确的权限
            os.chmod(pgpass_path, 0o600)
            
            try:
                # 使用pg_dump导出数据库
                dump_process = subprocess.Popen(
                    [
                        'pg_dump',
                        '-h', db_host,
                        '-p', str(db_port),
                        '-U', db_user,
                        '-d', db_name
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                dump_output, dump_error = dump_process.communicate()
                
                if dump_process.returncode == 0:
                    zipf.writestr('database.sql', dump_output)
                else:
                    raise Exception(f"数据库导出失败: {dump_error.decode()}")
            finally:
                # 清理临时pgpass文件
                if os.path.exists(pgpass_path):
                    os.remove(pgpass_path)
            
            # 导出媒体文件
            media_dir = settings.MEDIA_ROOT
            if os.path.exists(media_dir):
                for root, dirs, files in os.walk(media_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, media_dir)
                        zipf.write(file_path, f'media/{arcname}')
            
            # 导出配置文件（排除敏感信息）
            config = {
                'settings': {
                    'MEDIA_ROOT': settings.MEDIA_ROOT,
                    'STATIC_ROOT': settings.STATIC_ROOT,
                    'ALLOWED_HOSTS': settings.ALLOWED_HOSTS,
                }
            }
            zipf.writestr('config.json', json.dumps(config, indent=2))
        
        messages.success(request, f'备份创建成功: {backup_name}')
        logger.info(f"创建备份成功: {backup_name}")
    except Exception as e:
        messages.error(request, f'备份创建失败: {str(e)}')
        logger.error(f"创建备份失败: {str(e)}")
    
    return redirect('backup_list')

@login_required
@permission_required('inventory.can_manage_backup')
def restore_backup(request, backup_name):
    """从备份恢复数据库"""
    try:
        backup_path = os.path.join(settings.BACKUP_ROOT, backup_name)
        if not os.path.exists(backup_path):
            raise Exception('备份文件不存在')
        
        # 创建临时目录
        temp_dir = os.path.join(settings.BACKUP_ROOT, 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        
        # 解压备份文件
        with zipfile.ZipFile(backup_path, 'r') as zipf:
            zipf.extractall(temp_dir)
        
        # 恢复数据库
        db_settings = settings.DATABASES['default']
        db_name = db_settings['NAME']
        db_user = db_settings['USER']
        db_host = db_settings['HOST']
        db_port = db_settings['PORT']
        
        # 使用pgpass文件存储密码
        pgpass_dir = os.path.expanduser('~/.pgpass')
        pgpass_path = os.path.join(pgpass_dir, 'pgpass')
        
        # 确保.pgpass目录存在
        os.makedirs(pgpass_dir, exist_ok=True)
        
        # 创建临时pgpass文件
        with open(pgpass_path, 'w') as f:
            f.write(f"{db_host}:{db_port}:*:{db_user}:{db_settings['PASSWORD']}\n")
        
        # 设置正确的权限
        os.chmod(pgpass_path, 0o600)
        
        try:
            # 先删除现有数据库
            drop_process = subprocess.Popen(
                [
                    'dropdb',
                    '-h', db_host,
                    '-p', str(db_port),
                    '-U', db_user,
                    db_name
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            drop_output, drop_error = drop_process.communicate()
            
            # 创建新数据库
            create_process = subprocess.Popen(
                [
                    'createdb',
                    '-h', db_host,
                    '-p', str(db_port),
                    '-U', db_user,
                    db_name
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            create_output, create_error = create_process.communicate()
            
            # 恢复数据库
            restore_process = subprocess.Popen(
                [
                    'psql',
                    '-h', db_host,
                    '-p', str(db_port),
                    '-U', db_user,
                    '-d', db_name,
                    '-f', os.path.join(temp_dir, 'database.sql')
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            restore_output, restore_error = restore_process.communicate()
            
            if restore_process.returncode != 0:
                raise Exception(f"数据库恢复失败: {restore_error.decode()}")
        finally:
            # 清理临时pgpass文件
            if os.path.exists(pgpass_path):
                os.remove(pgpass_path)
        
        # 恢复媒体文件
        media_dir = os.path.join(temp_dir, 'media')
        if os.path.exists(media_dir):
            for root, dirs, files in os.walk(media_dir):
                for file in files:
                    src_path = os.path.join(root, file)
                    dst_path = os.path.join(settings.MEDIA_ROOT, os.path.relpath(src_path, media_dir))
                    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                    with open(src_path, 'rb') as src, open(dst_path, 'wb') as dst:
                        dst.write(src.read())
        
        # 清理临时文件
        shutil.rmtree(temp_dir)
        
        messages.success(request, '备份恢复成功')
        logger.info(f"恢复备份成功: {backup_name}")
    except Exception as e:
        messages.error(request, f'备份恢复失败: {str(e)}')
        logger.error(f"恢复备份失败: {str(e)}")
    
    return redirect('backup_list')

@login_required
@permission_required('inventory.can_manage_backup')
def delete_backup(request, backup_name):
    """删除备份文件"""
    try:
        backup_path = os.path.join(settings.BACKUP_ROOT, backup_name)
        if os.path.exists(backup_path):
            os.remove(backup_path)
            messages.success(request, f'备份删除成功: {backup_name}')
            logger.info(f"删除备份成功: {backup_name}")
        else:
            messages.warning(request, f'备份文件不存在: {backup_name}')
    except Exception as e:
        messages.error(request, f'备份删除失败: {str(e)}')
        logger.error(f"删除备份失败: {str(e)}")
    
    return redirect('backup_list')

@login_required
@permission_required('inventory.can_manage_backup')
def download_backup(request, backup_name):
    """下载备份文件"""
    try:
        backup_path = os.path.join(settings.BACKUP_ROOT, backup_name)
        if os.path.exists(backup_path):
            response = FileResponse(open(backup_path, 'rb'))
            response['Content-Type'] = 'application/zip'
            response['Content-Disposition'] = f'attachment; filename="{backup_name}"'
            return response
        else:
            messages.error(request, f'备份文件不存在: {backup_name}')
    except Exception as e:
        messages.error(request, f'下载失败: {str(e)}')
        logger.error(f"下载备份失败: {str(e)}")
    
    return redirect('backup_list')

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