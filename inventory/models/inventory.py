from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from .product import Product


class Inventory(models.Model):
    product = models.OneToOneField(Product, on_delete=models.PROTECT, verbose_name='商品')
    quantity = models.IntegerField(default=0, verbose_name='库存数量')
    warning_level = models.IntegerField(default=10, verbose_name='预警数量')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    def clean(self):
        if self.quantity < 0:
            raise ValidationError('库存数量不能为负数')
        if self.warning_level < 0:
            raise ValidationError('预警数量不能为负数')
    
    @property
    def is_low_stock(self):
        return self.quantity <= self.warning_level
    
    class Meta:
        verbose_name = '库存'
        verbose_name_plural = '库存'
        permissions = (
            ("can_view_item", "可以查看物料"),
            ("can_add_item", "可以添加物料"),
            ("can_change_item", "可以修改物料"),
            ("can_delete_item", "可以删除物料"),
            ("can_export_item", "可以导出物料"),
            ("can_import_item", "可以导入物料"),
            ("can_allocate_item", "可以分配物料"),
            ("can_checkin_item", "可以入库物料"),
            ("can_checkout_item", "可以出库物料"),
            ("can_adjust_item", "可以调整物料库存"),
            ("can_return_item", "可以归还物料"),
            ("can_move_item", "可以移动物料"),
            ("can_manage_backup", "可以管理备份"),
        )
    
    def __str__(self):
        return f'{self.product.name} - {self.quantity}'


class InventoryTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('IN', '入库'),
        ('OUT', '出库'),
        ('ADJUST', '调整'),
    ]

    product = models.ForeignKey(Product, on_delete=models.PROTECT, verbose_name='商品')
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES, verbose_name='交易类型')
    quantity = models.IntegerField(verbose_name='数量')
    operator = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='操作员')
    notes = models.TextField(blank=True, verbose_name='备注')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        verbose_name = '库存交易记录'
        verbose_name_plural = '库存交易记录'
    
    def __str__(self):
        return f'{self.product.name} - {self.get_transaction_type_display()} - {self.quantity}'


# 添加库存工具函数
def check_inventory(product, quantity):
    """检查库存是否足够"""
    try:
        inventory = Inventory.objects.get(product=product)
        return inventory.quantity >= quantity
    except Inventory.DoesNotExist:
        return False


def update_inventory(product, quantity, transaction_type, operator, notes=''):
    """更新库存并记录交易"""
    try:
        # 获取或创建库存记录
        inventory, created = Inventory.objects.get_or_create(
            product=product,
            defaults={'quantity': 0}
        )
        
        # 更新库存数量
        old_quantity = inventory.quantity
        inventory.quantity += quantity
        
        # 确保库存不为负数
        if inventory.quantity < 0:
            raise ValidationError(f"库存不足: {product.name}, 当前库存: {old_quantity}, 请求数量: {abs(quantity)}")
        
        inventory.save()
        
        # 记录库存交易
        transaction = InventoryTransaction.objects.create(
            product=product,
            transaction_type=transaction_type,
            quantity=abs(quantity),  # 存储绝对值
            operator=operator,
            notes=notes
        )
        
        return True, inventory, transaction
    except Exception as e:
        return False, None, str(e)


class StockAlert(models.Model):
    """库存预警模型"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='商品')
    alert_type = models.CharField(
        max_length=20, 
        choices=[
            ('low_stock', '低库存'),
            ('expiring', '即将过期'),
            ('overstock', '库存过量')
        ],
        verbose_name='预警类型'
    )
    is_active = models.BooleanField(default=True, verbose_name='是否激活')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name='解决时间')
    
    class Meta:
        verbose_name = '库存预警'
        verbose_name_plural = '库存预警'
        
    def __str__(self):
        return f'{self.product.name} - {self.get_alert_type_display()}' 