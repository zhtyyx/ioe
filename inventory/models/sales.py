from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.contrib.auth.models import User

from .product import Product
from .member import Member


class Sale(models.Model):
    """
    销售单模型
    """
    STATUS_CHOICES = [
        ('DRAFT', '未完成'),
        ('COMPLETED', '已完成'),
        ('CANCELLED', '已取消'),
    ]

    PAYMENT_METHODS = [
        ('cash', '现金'),
        ('wechat', '微信'),
        ('alipay', '支付宝'),
        ('card', '银行卡'),
        ('balance', '账户余额'),
        ('mixed', '混合支付'),
        ('other', '其他')
    ]

    member = models.ForeignKey(Member, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='会员')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='总金额')
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='折扣金额')
    final_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='实付金额')
    points_earned = models.IntegerField(default=0, verbose_name='获得积分')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='cash', verbose_name='支付方式')
    balance_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='余额支付')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT', verbose_name='状态')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    operator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='操作员')
    remark = models.TextField(blank=True, verbose_name='备注')

    @property
    def total_quantity(self):
        return sum(item.quantity for item in self.items.all())

    def update_total_amount(self):
        self.total_amount = sum(item.subtotal for item in self.items.all())
        return self.total_amount
    
    def save(self, *args, **kwargs):
        # 确保total_amount不为None且为有效值
        if self.total_amount is None:
            self.total_amount = 0
        
        if self.total_amount < self.discount_amount:
            self.discount_amount = self.total_amount
        
        self.final_amount = self.total_amount - self.discount_amount
        super().save(*args, **kwargs)
        
    class Meta:
        verbose_name = '销售单'
        verbose_name_plural = '销售单'

    def __str__(self):
        return f'销售单 #{self.id} - {self.created_at.strftime("%Y-%m-%d %H:%M")}'


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.PROTECT, related_name='items', verbose_name='销售单')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, verbose_name='商品')
    quantity = models.IntegerField(verbose_name='数量')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='标准售价')
    actual_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='实际售价')
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='小计')
    
    def clean(self):
        from django.core.exceptions import ValidationError
        if self.quantity <= 0:
            raise ValidationError('数量必须大于0')
    
    def save(self, *args, **kwargs):
        update_fields = kwargs.get('update_fields')
        if update_fields is not None and not update_fields:
            return
        with transaction.atomic():
            sale = Sale.objects.select_for_update().get(pk=self.sale_id)
            previous = type(self).objects.select_for_update().filter(pk=self.pk).first() if self.pk else None
            if previous and (previous.sale_id != self.sale_id or previous.product_id != self.product_id):
                raise ValidationError('已保存的销售明细不能更换销售单或商品')
            if previous and update_fields is not None:
                # Unselected fields on the instance must not change persisted stock or totals.
                for field in ('quantity', 'price', 'actual_price'):
                    if field not in update_fields:
                        setattr(self, field, getattr(previous, field))
            if self.quantity <= 0:
                raise ValidationError('数量必须大于0')
            if self.actual_price is None:
                self.actual_price = self.price
            self.subtotal = self.quantity * self.actual_price
            if update_fields is not None:
                kwargs['update_fields'] = set(update_fields) | {'subtotal'}
            delta = self.quantity - (previous.quantity if previous else 0)
            super().save(*args, **kwargs)
            if delta:
                from .inventory import update_inventory
                success, _, error = update_inventory(
                    product=self.product, quantity=-delta,
                    transaction_type='OUT' if delta > 0 else 'IN',
                    operator=sale.operator, notes=f'销售单 #{sale.id}',
                )
                if not success:
                    raise ValidationError(error or '库存更新失败')
            sale.update_total_amount()
            sale.save()
            self.sale = sale

    class Meta:
        verbose_name = '销售明细'
        verbose_name_plural = '销售明细'
    
    def __str__(self):
        return f'{self.product.name} x {self.quantity}' 