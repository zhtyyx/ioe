from django.db import models
from django.core.exceptions import ValidationError


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name='分类名称')
    description = models.TextField(blank=True, verbose_name='分类描述')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
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
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    
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


class Color(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name='颜色名称')
    code = models.CharField(max_length=20, blank=True, verbose_name='颜色代码')
    
    class Meta:
        verbose_name = '颜色'
        verbose_name_plural = '颜色'
    
    def __str__(self):
        return self.name


class Size(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name='尺码名称')
    
    class Meta:
        verbose_name = '尺码'
        verbose_name_plural = '尺码'
    
    def __str__(self):
        return self.name


class Store(models.Model):
    name = models.CharField(max_length=100, verbose_name='店铺名称')
    address = models.CharField(max_length=255, blank=True, verbose_name='地址')
    phone = models.CharField(max_length=20, blank=True, verbose_name='联系电话')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    
    class Meta:
        verbose_name = '店铺'
        verbose_name_plural = '店铺'
    
    def __str__(self):
        return self.name


class ProductImage(models.Model):
    """商品图片模型"""
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE, verbose_name='商品')
    image = models.ImageField(upload_to='products/', verbose_name='图片')
    thumbnail = models.CharField(max_length=255, blank=True, null=True, verbose_name='缩略图路径')
    alt_text = models.CharField(max_length=255, blank=True, verbose_name='替代文本')
    order = models.IntegerField(default=0, verbose_name='排序')
    is_primary = models.BooleanField(default=False, verbose_name='是否主图')
    
    class Meta:
        verbose_name = '商品图片'
        verbose_name_plural = '商品图片'
        ordering = ['order']
    
    def __str__(self):
        return f"{self.product.name} - 图片 {self.id}"
    
    def save(self, *args, **kwargs):
        # 如果标记为主图，确保其他图片不是主图
        if self.is_primary:
            ProductImage.objects.filter(product=self.product, is_primary=True).update(is_primary=False)
        super(ProductImage, self).save(*args, **kwargs)


class ProductBatch(models.Model):
    """商品批次模型"""
    product = models.ForeignKey(Product, related_name='batches', on_delete=models.CASCADE, verbose_name='商品')
    batch_number = models.CharField(max_length=100, verbose_name='批次号')
    production_date = models.DateField(null=True, blank=True, verbose_name='生产日期')
    expiry_date = models.DateField(null=True, blank=True, verbose_name='过期日期')
    quantity = models.IntegerField(default=0, verbose_name='数量')
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='成本价')
    supplier = models.ForeignKey('Supplier', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='供应商')
    remarks = models.TextField(blank=True, verbose_name='备注')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, related_name='created_batches', verbose_name='创建人')
    
    class Meta:
        verbose_name = '商品批次'
        verbose_name_plural = '商品批次'
        unique_together = ('product', 'batch_number')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.product.name} - {self.batch_number}"


class Supplier(models.Model):
    """供应商模型"""
    name = models.CharField(max_length=100, verbose_name='供应商名称')
    contact_person = models.CharField(max_length=50, blank=True, verbose_name='联系人')
    phone = models.CharField(max_length=20, blank=True, verbose_name='联系电话')
    email = models.EmailField(blank=True, verbose_name='电子邮件')
    address = models.TextField(blank=True, verbose_name='地址')
    remarks = models.TextField(blank=True, verbose_name='备注')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '供应商'
        verbose_name_plural = '供应商'
    
    def __str__(self):
        return self.name 