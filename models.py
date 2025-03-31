from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.db import transaction

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name='分类名称')
    description = models.TextField(blank=True, verbose_name='分类描述')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '商品分类'
        verbose_name_plural = '商品分类'
    
    def __str__(self):
        return self.name

class Product(models.Model):
    COLOR_CHOICES = [
        ('', '无颜色'),
        ('black', '黑色'),
        ('white', '白色'),
        ('red', '红色'),
        ('blue', '蓝色'),
        ('green', '绿色'),
        ('yellow', '黄色'),
        ('purple', '紫色'),
        ('grey', '灰色'),
        ('pink', '粉色'),
        ('orange', '橙色'),
        ('brown', '棕色'),
        ('other', '其他')
    ]
    
    SIZE_CHOICES = [
        ('', '无尺码'),
        ('XS', 'XS'),
        ('S', 'S'),
        ('M', 'M'),
        ('L', 'L'),
        ('XL', 'XL'),
        ('XXL', 'XXL'),
        ('XXXL', 'XXXL'),
        ('35', '35'),
        ('36', '36'),
        ('37', '37'),
        ('38', '38'),
        ('39', '39'),
        ('40', '40'),
        ('41', '41'),
        ('42', '42'),
        ('43', '43'),
        ('44', '44'),
        ('45', '45'),
        ('other', '其他')
    ]
    
    barcode = models.CharField(max_length=100, unique=True, verbose_name='商品条码')
    name = models.CharField(max_length=200, verbose_name='商品名称')
    category = models.ForeignKey(Category, on_delete=models.PROTECT, verbose_name='商品分类')
    description = models.TextField(blank=True, verbose_name='商品描述')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='售价')
    cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='成本价')
    image = models.ImageField(upload_to='products/', blank=True, null=True, verbose_name='商品图片')
    # 新增字段
    specification = models.CharField(max_length=200, blank=True, verbose_name='规格')
    manufacturer = models.CharField(max_length=200, blank=True, verbose_name='制造商')
    color = models.CharField(max_length=20, choices=COLOR_CHOICES, blank=True, default='', verbose_name='颜色')
    size = models.CharField(max_length=10, choices=SIZE_CHOICES, blank=True, default='', verbose_name='尺码')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    def clean(self):
        if self.price < 0:
            raise ValidationError('售价不能为负数')
        if self.cost < 0:
            raise ValidationError('成本价不能为负数')
    
    class Meta:
        verbose_name = '商品'
        verbose_name_plural = '商品'
    
    def __str__(self):
        return self.name

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

# 添加辅助函数
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

# 新增模型：库存盘点
class InventoryCheck(models.Model):
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

class MemberLevel(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name='等级名称')
    discount = models.DecimalField(
        max_digits=3, 
        decimal_places=2, 
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        verbose_name='折扣率'
    )
    points_threshold = models.IntegerField(verbose_name='升级所需积分')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '会员等级'
        verbose_name_plural = '会员等级'
        ordering = ['points_threshold']

    def __str__(self):
        return self.name

class Member(models.Model):
    GENDER_CHOICES = [
        ('M', '男'),
        ('F', '女'),
        ('O', '其他')
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name='用户', null=True, blank=True)
    level = models.ForeignKey(MemberLevel, on_delete=models.PROTECT, verbose_name='会员等级')
    name = models.CharField(max_length=100, verbose_name='姓名')
    phone = models.CharField(max_length=20, unique=True, verbose_name='手机号')
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, verbose_name='性别', default='O')
    birthday = models.DateField(null=True, blank=True, verbose_name='生日')
    points = models.IntegerField(default=0, verbose_name='积分')
    total_spend = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='累计消费')
    purchase_count = models.IntegerField(default=0, verbose_name='消费次数')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='注册时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='账户余额')
    is_recharged = models.BooleanField(default=False, verbose_name='是否充值会员')

    class Meta:
        verbose_name = '会员'
        verbose_name_plural = '会员'

    def __str__(self):
        return f"{self.name} ({self.phone})"

    @property
    def age(self):
        """计算会员年龄"""
        if not self.birthday:
            return None
        today = timezone.now().date()
        return today.year - self.birthday.year - ((today.month, today.day) < (self.birthday.month, self.birthday.day))

class RechargeRecord(models.Model):
    PAYMENT_METHODS = [
        ('cash', '现金'),
        ('wechat', '微信'),
        ('alipay', '支付宝'),
        ('card', '银行卡'),
        ('other', '其他')
    ]
    
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='recharge_records', verbose_name='会员')
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='充值金额')
    actual_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='实收金额')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, verbose_name='支付方式')
    operator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='操作员')
    remark = models.TextField(blank=True, verbose_name='备注')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='充值时间')
    
    class Meta:
        verbose_name = '充值记录'
        verbose_name_plural = '充值记录'
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.member.name} 充值 {self.amount}元"

class Sale(models.Model):
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
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    operator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='操作员')
    remark = models.TextField(blank=True, verbose_name='备注')

    def update_total_amount(self):
        self.total_amount = sum(item.subtotal for item in self.items.all())
        super().save(update_fields=['total_amount'])

    def save(self, *args, **kwargs):
        if not self.pk:
            super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)
            self.update_total_amount()

    class Meta:
        verbose_name = '销售单'
        verbose_name_plural = '销售单'

    def __str__(self):
        return f'销售单 #{self.id}'

class OperationLog(models.Model):
    OPERATION_TYPES = [
        ('SALE', '销售'),
        ('INVENTORY', '库存调整'),
        ('MEMBER', '会员管理'),
        ('INVENTORY_CHECK', '库存盘点'),
        ('OTHER', '其他')
    ]

    operator = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='操作员')
    operation_type = models.CharField(max_length=20, choices=OPERATION_TYPES, verbose_name='操作类型')
    details = models.TextField(verbose_name='操作详情')
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='操作时间')
    related_object_id = models.PositiveIntegerField(verbose_name='关联对象ID')
    related_content_type = models.ForeignKey('contenttypes.ContentType', on_delete=models.PROTECT, verbose_name='关联类型')

    class Meta:
        verbose_name = '操作日志'
        verbose_name_plural = '操作日志'
        ordering = ['-timestamp']

    def __str__(self):
        return f'{self.operator.username} - {self.get_operation_type_display()} - {self.timestamp}'

class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.PROTECT, related_name='items', verbose_name='销售单')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, verbose_name='商品')
    quantity = models.IntegerField(verbose_name='数量')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='标准售价')
    actual_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='实际售价')
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='小计')
    
    def clean(self):
        if self.quantity <= 0:
            raise ValidationError('销售数量必须大于0')
        if not check_inventory(self.product, self.quantity):
            raise ValidationError('库存不足')
    
    def save(self, *args, **kwargs):
        with transaction.atomic():
            self.price = self.product.price
            self.subtotal = self.price * self.quantity
            if not self.pk:  # 新建销售明细时更新库存
                update_inventory(
                    product=self.product,
                    quantity=-self.quantity,
                    transaction_type='OUT',
                    operator=self.sale.operator,
                    notes=f'销售单 #{self.sale.id}'
                )
            super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = '销售明细'
        verbose_name_plural = '销售明细'
    
    def __str__(self):
        return f'{self.product.name} x {self.quantity}'