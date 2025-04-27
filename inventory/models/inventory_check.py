from django.db import models
from django.contrib.auth.models import User

from .product import Product


class InventoryCheck(models.Model):
    """
    库存盘点模型，用于管理库存盘点任务
    """
    STATUS_CHOICES = [
        ('draft', '草稿'),
        ('in_progress', '盘点中'),
        ('completed', '已完成'),
        ('approved', '已审核'),
        ('cancelled', '已取消'),
    ]
    
    name = models.CharField(max_length=100, verbose_name='盘点名称')
    description = models.TextField(blank=True, verbose_name='盘点描述')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name='状态')
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='inventory_checks_created', verbose_name='创建人')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')
    approved_by = models.ForeignKey(
        User, on_delete=models.PROTECT, 
        related_name='inventory_checks_approved', 
        null=True, blank=True,
        verbose_name='审核人'
    )
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name='审核时间')
    
    class Meta:
        verbose_name = '库存盘点'
        verbose_name_plural = '库存盘点'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.name} - {self.get_status_display()}'


class InventoryCheckItem(models.Model):
    """
    库存盘点项目，记录每个商品的盘点结果
    """
    inventory_check = models.ForeignKey(InventoryCheck, on_delete=models.CASCADE, related_name='items', verbose_name='盘点单')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, verbose_name='商品')
    system_quantity = models.IntegerField(verbose_name='系统数量')
    actual_quantity = models.IntegerField(null=True, blank=True, verbose_name='实际数量')
    difference = models.IntegerField(null=True, blank=True, verbose_name='差异')
    notes = models.TextField(blank=True, verbose_name='备注')
    checked_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, verbose_name='盘点人')
    checked_at = models.DateTimeField(null=True, blank=True, verbose_name='盘点时间')
    
    class Meta:
        verbose_name = '盘点项目'
        verbose_name_plural = '盘点项目'
        unique_together = ('inventory_check', 'product')
    
    def __str__(self):
        return f'{self.product.name} - 系统:{self.system_quantity} 实际:{self.actual_quantity or "未盘点"}'
    
    def save(self, *args, **kwargs):
        # Calculate difference when actual quantity is set
        if self.actual_quantity is not None:
            self.difference = self.actual_quantity - self.system_quantity
        super().save(*args, **kwargs) 