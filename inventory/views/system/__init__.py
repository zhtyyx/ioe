"""
系统管理相关视图
"""
from .base import (
    system_settings,
    system_info,
    store_settings, 
    store_list,
    delete_store,
    system_maintenance
)

from .log import (
    log_list,
    clear_logs,
    view_log_file,
    download_log_file,
    delete_log_file
)

from .backup import (
    backup_list,
    create_backup,
    restore_backup,
    delete_backup,
    download_backup,
    manual_backup
)

from .user import (
    user_list,
    user_create,
    user_update,
    user_delete,
    user_detail
)

__all__ = [
    # 基础系统设置
    'system_settings',
    'system_info',
    'store_settings',
    'store_list',
    'delete_store',
    'system_maintenance',
    
    # 日志管理
    'log_list',
    'clear_logs',
    'view_log_file',
    'download_log_file',
    'delete_log_file',
    
    # 备份管理
    'backup_list',
    'create_backup',
    'restore_backup',
    'delete_backup',
    'download_backup',
    'manual_backup',
    
    # 用户管理
    'user_list',
    'user_create',
    'user_update',
    'user_delete',
    'user_detail',
] 