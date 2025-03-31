import os
import datetime
import shutil
import json
import glob
import logging
from pathlib import Path
from django.conf import settings
from django.core.management import call_command
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)

class BackupService:
    """数据库备份和恢复服务"""
    
    @staticmethod
    def get_backup_directory():
        """获取备份目录，如果不存在则创建"""
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        return backup_dir

    @staticmethod
    def create_backup(backup_name=None, user=None):
        """
        创建数据库备份
        :param backup_name: 备份名称，如果为None则使用当前日期时间
        :param user: 执行备份的用户
        :return: 备份文件路径
        """
        if not backup_name:
            now = datetime.datetime.now()
            backup_name = f"backup_{now.strftime('%Y%m%d_%H%M%S')}"
        
        # 创建备份目录
        backup_dir = BackupService.get_backup_directory()
        backup_path = os.path.join(backup_dir, backup_name)
        os.makedirs(backup_path, exist_ok=True)
        
        try:
            # 导出数据库为JSON fixtures
            fixtures_path = os.path.join(backup_path, 'db.json')
            with open(fixtures_path, 'w', encoding='utf-8') as f:
                call_command('dumpdata', '--exclude', 'contenttypes', '--exclude', 'auth.Permission',
                            '--exclude', 'sessions.session', '--indent', '2', stdout=f)
            
            # 备份媒体文件
            media_dir = os.path.join(settings.BASE_DIR, 'media')
            if os.path.exists(media_dir):
                media_backup_dir = os.path.join(backup_path, 'media')
                os.makedirs(media_backup_dir, exist_ok=True)
                for item in os.listdir(media_dir):
                    source = os.path.join(media_dir, item)
                    target = os.path.join(media_backup_dir, item)
                    if os.path.isdir(source):
                        shutil.copytree(source, target, dirs_exist_ok=True)
                    else:
                        shutil.copy2(source, target)
            
            # 记录备份元数据
            metadata = {
                'backup_name': backup_name,
                'created_at': datetime.datetime.now().isoformat(),
                'created_by': user.username if user else 'system',
                'django_version': settings.DJANGO_VERSION,
                'database_engine': settings.DATABASES['default']['ENGINE'],
            }
            
            with open(os.path.join(backup_path, 'metadata.json'), 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"备份创建成功: {backup_name}")
            return backup_path
        except Exception as e:
            # 如果备份失败，删除可能创建的部分备份
            if os.path.exists(backup_path):
                shutil.rmtree(backup_path)
            logger.error(f"备份创建失败: {str(e)}")
            raise

    @staticmethod
    def restore_backup(backup_name, user=None):
        """
        从备份恢复数据库
        :param backup_name: 备份名称
        :param user: 执行恢复的用户
        :return: 成功返回True，失败返回False
        """
        backup_dir = BackupService.get_backup_directory()
        backup_path = os.path.join(backup_dir, backup_name)
        
        if not os.path.exists(backup_path):
            logger.error(f"备份不存在: {backup_name}")
            return False
        
        try:
            # 恢复数据库
            fixtures_path = os.path.join(backup_path, 'db.json')
            if os.path.exists(fixtures_path):
                # 先清空数据库，但保留超级用户
                superusers = list(User.objects.filter(is_superuser=True).values_list('username', flat=True))
                call_command('flush', '--noinput')
                call_command('loaddata', fixtures_path)
                
                # 记录恢复操作
                with open(os.path.join(backup_path, 'restore_log.json'), 'w', encoding='utf-8') as f:
                    restore_log = {
                        'restored_at': datetime.datetime.now().isoformat(),
                        'restored_by': user.username if user else 'system',
                    }
                    json.dump(restore_log, f, indent=2)
                
                # 恢复媒体文件
                media_backup_dir = os.path.join(backup_path, 'media')
                if os.path.exists(media_backup_dir):
                    media_dir = os.path.join(settings.BASE_DIR, 'media')
                    if os.path.exists(media_dir):
                        # 先备份当前的媒体文件
                        media_backup = os.path.join(settings.BASE_DIR, f"media_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}")
                        shutil.move(media_dir, media_backup)
                    
                    # 复制备份的媒体文件
                    shutil.copytree(media_backup_dir, media_dir)
                
                logger.info(f"备份恢复成功: {backup_name}")
                return True
            else:
                logger.error(f"备份文件不完整，缺少db.json: {backup_name}")
                return False
        except Exception as e:
            logger.error(f"备份恢复失败: {str(e)}")
            return False
    
    @staticmethod
    def list_backups():
        """
        列出所有备份
        :return: 备份列表，格式为[{'name': name, 'created_at': datetime, 'size': size_in_mb, ...}, ...]
        """
        backup_dir = BackupService.get_backup_directory()
        if not os.path.exists(backup_dir):
            return []
        
        backups = []
        for backup_name in os.listdir(backup_dir):
            backup_path = os.path.join(backup_dir, backup_name)
            if os.path.isdir(backup_path):
                metadata_path = os.path.join(backup_path, 'metadata.json')
                if os.path.exists(metadata_path):
                    try:
                        with open(metadata_path, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                        
                        # 计算备份大小
                        size_bytes = sum(
                            os.path.getsize(os.path.join(dirpath, filename))
                            for dirpath, _, filenames in os.walk(backup_path)
                            for filename in filenames
                        )
                        size_mb = size_bytes / (1024 * 1024)
                        
                        backups.append({
                            'name': backup_name,
                            'created_at': datetime.datetime.fromisoformat(metadata['created_at']),
                            'created_by': metadata.get('created_by', 'unknown'),
                            'size': f"{size_mb:.2f} MB",
                            'size_bytes': size_bytes,
                            'metadata': metadata
                        })
                    except Exception as e:
                        logger.warning(f"读取备份元数据失败: {backup_name}, 错误: {str(e)}")
                        # 添加一个简单的备份记录，无元数据
                        backups.append({
                            'name': backup_name,
                            'created_at': datetime.datetime.fromtimestamp(os.path.getctime(backup_path)),
                            'created_by': 'unknown',
                            'size': '未知',
                            'size_bytes': 0,
                            'metadata': {}
                        })
        
        # 按创建时间排序，最新的在前面
        backups.sort(key=lambda x: x['created_at'], reverse=True)
        return backups
    
    @staticmethod
    def delete_backup(backup_name):
        """
        删除指定备份
        :param backup_name: 备份名称
        :return: 成功返回True，失败返回False
        """
        backup_dir = BackupService.get_backup_directory()
        backup_path = os.path.join(backup_dir, backup_name)
        
        if not os.path.exists(backup_path):
            logger.error(f"备份不存在: {backup_name}")
            return False
        
        try:
            shutil.rmtree(backup_path)
            logger.info(f"备份删除成功: {backup_name}")
            return True
        except Exception as e:
            logger.error(f"备份删除失败: {str(e)}")
            return False
    
    @staticmethod
    def auto_backup():
        """
        执行自动备份，并清理超过60天的旧备份
        """
        try:
            # 创建新备份
            backup_name = f"auto_backup_{datetime.datetime.now().strftime('%Y%m%d')}"
            BackupService.create_backup(backup_name=backup_name)
            
            # 计算60天前的日期
            days_to_keep = getattr(settings, 'BACKUP_DAYS_TO_KEEP', 60)
            cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days_to_keep)
            
            # 列出所有备份并删除旧的自动备份
            backups = BackupService.list_backups()
            for backup in backups:
                if backup['name'].startswith('auto_backup_') and backup['created_at'] < cutoff_date:
                    BackupService.delete_backup(backup['name'])
            
            return True
        except Exception as e:
            logger.error(f"自动备份失败: {str(e)}")
            return False 