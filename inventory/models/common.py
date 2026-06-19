from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType


class OperationLog(models.Model):
    """
    通用操作日志模型，记录系统中所有类型的操作，支持关联到不同的对象
    """
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
    related_content_type = models.ForeignKey(ContentType, on_delete=models.PROTECT, verbose_name='关联类型')

    class Meta:
        verbose_name = '操作日志'
        verbose_name_plural = '操作日志'
        ordering = ['-timestamp']

    def __str__(self):
        return f'{self.operator.username} - {self.get_operation_type_display()} - {self.timestamp}'


class SystemConfig(models.Model):
    """系统配置模型"""
    company_name = models.CharField(max_length=100, verbose_name="公司名称", default="我的商店")
    company_address = models.TextField(verbose_name="公司地址", blank=True, null=True)
    company_phone = models.CharField(max_length=20, verbose_name="联系电话", blank=True, null=True)
    company_email = models.EmailField(verbose_name="电子邮箱", blank=True, null=True)
    company_website = models.URLField(verbose_name="网站", blank=True, null=True)
    company_logo = models.ImageField(upload_to='logos/', verbose_name="公司标志", blank=True, null=True)
    
    # 条码设置
    barcode_width = models.IntegerField(verbose_name="条码宽度", default=300)
    barcode_height = models.IntegerField(verbose_name="条码高度", default=100)
    barcode_font_size = models.IntegerField(verbose_name="条码字体大小", default=12)
    barcode_show_price = models.BooleanField(verbose_name="显示价格", default=True)
    barcode_show_name = models.BooleanField(verbose_name="显示商品名称", default=True)
    barcode_show_company = models.BooleanField(verbose_name="显示公司名称", default=True)
    
    # 打印设置
    receipt_header = models.TextField(verbose_name="小票页眉", blank=True, null=True)
    receipt_footer = models.TextField(verbose_name="小票页脚", blank=True, null=True)
    
    # 系统设置
    enable_low_stock_alert = models.BooleanField(verbose_name="启用低库存提醒", default=True)
    default_tax_rate = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="默认税率", default=0)
    currency_symbol = models.CharField(max_length=10, verbose_name="货币符号", default="¥")
    timezone = models.CharField(max_length=50, verbose_name="时区", default="Asia/Shanghai")
    
    class Meta:
        verbose_name = '系统配置'
        verbose_name_plural = '系统配置'
    
    def __str__(self):
        return self.company_name 