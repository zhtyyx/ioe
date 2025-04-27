from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator


class MemberLevel(models.Model):
    """会员等级模型，用于定义不同等级的会员及其折扣权益"""
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
    color = models.CharField(max_length=50, default='blue', verbose_name='颜色标识')
    priority = models.IntegerField(default=0, verbose_name='优先级')
    is_default = models.BooleanField(default=False, verbose_name='是否默认等级')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')

    class Meta:
        verbose_name = '会员等级'
        verbose_name_plural = '会员等级'
        ordering = ['priority', 'points_threshold']

    def __str__(self):
        return self.name


class Member(models.Model):
    """会员模型，存储会员基本信息和消费统计"""
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
    member_id = models.CharField(max_length=50, unique=True, null=True, blank=True, verbose_name='会员号')
    email = models.EmailField(max_length=100, null=True, blank=True, verbose_name='邮箱')
    address = models.CharField(max_length=200, null=True, blank=True, verbose_name='地址')
    notes = models.TextField(blank=True, null=True, verbose_name='备注')
    is_active = models.BooleanField(default=True, verbose_name='是否活跃')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_members', verbose_name='创建人')
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_members', verbose_name='更新人')

    class Meta:
        verbose_name = '会员'
        verbose_name_plural = '会员'

    def __str__(self):
        return self.name

    @property
    def age(self):
        """计算会员年龄"""
        if self.birthday:
            today = timezone.now().date()
            born = self.birthday
            return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
        return None


class RechargeRecord(models.Model):
    """会员充值记录"""
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
        return f'{self.member.name} - {self.amount}'


class MemberTransaction(models.Model):
    """会员交易记录，用于跟踪积分和余额的变动"""
    TRANSACTION_TYPES = [
        ('PURCHASE', '消费'),
        ('REFUND', '退款'),
        ('RECHARGE', '充值'),
        ('POINTS_EARN', '积分奖励'),
        ('POINTS_REDEEM', '积分兑换'),
        ('POINTS_ADJUST', '积分调整'),
        ('BALANCE_ADJUST', '余额调整'),
        ('LEVEL_UPGRADE', '等级升级'),
        ('LEVEL_DOWNGRADE', '等级降级'),
        ('OTHER', '其他')
    ]
    
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='transactions', verbose_name='会员')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES, verbose_name='交易类型')
    points_change = models.IntegerField(default=0, verbose_name='积分变动')
    balance_change = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='余额变动')
    description = models.CharField(max_length=255, verbose_name='描述', blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='交易时间')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='member_transactions', verbose_name='操作员')
    related_object_id = models.PositiveIntegerField(null=True, blank=True, verbose_name='关联对象ID')
    related_object_type = models.CharField(max_length=50, null=True, blank=True, verbose_name='关联对象类型')
    
    class Meta:
        verbose_name = '会员交易记录'
        verbose_name_plural = '会员交易记录'
        ordering = ['-created_at']
        
    def __str__(self):
        change_str = ""
        if self.points_change != 0:
            change_str += f"积分:{self.points_change:+d} "
        if self.balance_change != 0:
            change_str += f"余额:{self.balance_change:+.2f} "
        return f'{self.member.name} - {self.get_transaction_type_display()} {change_str}' 