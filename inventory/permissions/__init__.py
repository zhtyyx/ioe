"""
Permission handling module for the inventory system.
"""

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import models

# 导入装饰器
from .decorators import (
    permission_required, 
    group_required, 
    superuser_required, 
    owner_or_permission_required,
    system_admin_required
)

# 导出装饰器
__all__ = [
    'permission_required', 
    'group_required', 
    'superuser_required', 
    'owner_or_permission_required',
    'system_admin_required',
    'setup_permissions',
]

# Define common permission codenames
PERMISSIONS = {
    # Inventory permissions
    'view_inventory': '查看库存',
    'change_inventory': '修改库存',
    'add_inventory': '添加库存',
    
    # Product permissions
    'view_product': '查看商品',
    'add_product': '添加商品',
    'change_product': '修改商品',
    'delete_product': '删除商品',
    
    # Sales permissions
    'view_sale': '查看销售',
    'add_sale': '添加销售',
    'void_sale': '作废销售',
    
    # Member permissions
    'view_member': '查看会员',
    'add_member': '添加会员',
    'change_member': '修改会员',
    
    # Report permissions
    'view_reports': '查看报表',
    'export_reports': '导出报表',
    
    # Inventory checking permissions
    'perform_inventory_check': '执行库存盘点',
    'approve_inventory_check': '审批库存盘点',
}

# Define role-permission mappings
ROLES = {
    'admin': {
        'name': '系统管理员',
        'permissions': list(PERMISSIONS.keys()),
    },
    'manager': {
        'name': '店长',
        'permissions': [
            'view_inventory', 'change_inventory', 'add_inventory',
            'view_product', 'add_product', 'change_product',
            'view_sale', 'add_sale', 'void_sale',
            'view_member', 'add_member', 'change_member',
            'view_reports', 'export_reports',
            'perform_inventory_check', 'approve_inventory_check',
        ],
    },
    'sales': {
        'name': '销售员',
        'permissions': [
            'view_inventory',
            'view_product',
            'view_sale', 'add_sale',
            'view_member', 'add_member',
        ],
    },
    'inventory': {
        'name': '库存管理员',
        'permissions': [
            'view_inventory', 'change_inventory', 'add_inventory',
            'view_product', 'add_product', 'change_product',
            'perform_inventory_check',
        ],
    },
}

def setup_permissions():
    """Set up all permissions and groups."""
    # Create all custom permissions
    for model in [
        'inventory', 'product', 'sale', 'member', 'report', 'inventorycheck'
    ]:
        content_type = ContentType.objects.get_for_model(models.Model)
        
        for codename, name in PERMISSIONS.items():
            if codename.split('_')[1] == model:
                Permission.objects.get_or_create(
                    codename=codename,
                    name=name,
                    content_type=content_type,
                )
    
    # Create groups and assign permissions
    for role_key, role_info in ROLES.items():
        group, created = Group.objects.get_or_create(name=role_info['name'])
        
        # Get all permissions for this role
        permissions = Permission.objects.filter(codename__in=role_info['permissions'])
        
        # Assign permissions to group
        group.permissions.set(permissions) 