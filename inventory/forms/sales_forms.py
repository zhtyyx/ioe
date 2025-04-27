from django import forms
from django.core.exceptions import ValidationError

from inventory.models import Sale, SaleItem, Product, Member
from inventory.models.inventory import check_inventory


class SaleForm(forms.ModelForm):
    # 添加会员搜索字段，用于快速查找会员
    member_search = forms.CharField(
        max_length=100,
        label='会员搜索',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '输入手机号或会员名称',
            'aria-label': '会员搜索',
            'autocomplete': 'off',  # 防止自动填充
            'style': 'height: 48px; font-size: 16px;',  # 增大触摸区域和字体
            'inputmode': 'search',  # 在移动设备上显示搜索键盘
            'data-bs-toggle': 'tooltip',  # 启用Bootstrap工具提示
            'title': '可以输入手机号或会员名称进行搜索'
        })
    )
    
    # 添加获取表单警告的方法
    def get_warnings(self):
        """获取表单验证过程中的警告信息（不阻止提交但需要提示用户的信息）"""
        return getattr(self, '_warnings', {})
    
    class Meta:
        model = Sale
        fields = ['remark']
        widgets = {
            'remark': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control',
                'placeholder': '销售备注（可选）',
                'aria-label': '备注'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 添加响应式布局的辅助类
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': field.widget.attrs.get('class', '') + ' mb-2',  # 添加下边距
            })


class SaleItemForm(forms.ModelForm):
    actual_price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        label='实际售价',
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'price-input form-control',
            'placeholder': '实际售价',
            'inputmode': 'decimal',  # 在移动设备上显示数字键盘，带小数点
            'aria-label': '实际售价',
            'autocomplete': 'off'  # 防止自动填充
        })
    )
    
    # 添加条码扫描字段，用于快速添加商品
    barcode = forms.CharField(
        max_length=100,
        label='扫描条码',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '扫描商品条码',
            'aria-label': '扫描条码',
            'autocomplete': 'off',  # 防止自动填充
            'autofocus': True,  # 自动获取焦点
            'style': 'height: 48px; font-size: 16px;'  # 增大触摸区域和字体
        })
    )
    
    class Meta:
        model = SaleItem
        fields = ['product', 'quantity', 'price', 'actual_price']
        widgets = {
            'product': forms.Select(attrs={
                'class': 'form-control form-select product-select',
                'aria-label': '商品',
                'style': 'height: 48px; font-size: 16px;'  # 增大触摸区域和字体
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'quantity-input form-control',
                'min': '1',
                'value': '1',
                'step': '1',
                'placeholder': '数量',
                'inputmode': 'numeric',  # 在移动设备上显示数字键盘
                'aria-label': '数量',
                'autocomplete': 'off',  # 防止自动填充
                'style': 'height: 48px; font-size: 16px;'  # 增大触摸区域和字体
            }),
            'price': forms.NumberInput(attrs={
                'class': 'price-input form-control',
                'step': '0.01',
                'placeholder': '标准售价',
                'inputmode': 'decimal',  # 在移动设备上显示数字键盘，带小数点
                'aria-label': '标准售价',
                'readonly': 'readonly',  # 标准价格不可编辑
                'style': 'height: 48px; font-size: 16px;'  # 增大触摸区域和字体
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 使用select_related优化查询
        self.fields['product'].queryset = Product.objects.all().select_related('category')
        
        # 添加响应式布局的辅助类
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': field.widget.attrs.get('class', '') + ' mb-2',  # 添加下边距
            })
            
        # 标记警告信息列表
        self._warnings = {}
        
        # 如果实例已存在，设置默认的实际价格
        if self.instance and self.instance.pk:
            self.initial['actual_price'] = self.instance.actual_price
            
            # 对于已有的销售项，不允许更改商品
            self.fields['product'].widget.attrs['readonly'] = 'readonly'
            self.fields['product'].widget.attrs['disabled'] = 'disabled'
    
    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity <= 0:
            raise ValidationError('销售数量必须大于0')
        return quantity
    
    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get('product')
        quantity = cleaned_data.get('quantity')
        
        if product and quantity:
            # 检查库存
            if not self.instance.pk:  # 只有新添加的销售项才检查库存
                if not check_inventory(product, quantity):
                    self._warnings['inventory'] = f'警告：商品 "{product.name}" 库存不足，当前销售数量可能导致库存不足。'
                
            # 如果未设置实际价格，使用标准价格
            if cleaned_data.get('actual_price') is None:
                cleaned_data['actual_price'] = product.price
                
            # 如果实际价格小于标准价格的一半，标记警告
            if cleaned_data.get('actual_price') < product.price * 0.5:
                self._warnings['low_price'] = f'警告：商品 "{product.name}" 的实际售价低于标准价格的50%，请确认是否正确。'
                
            # 如果实际价格大于标准价格的两倍，标记警告
            if cleaned_data.get('actual_price') > product.price * 2:
                self._warnings['high_price'] = f'警告：商品 "{product.name}" 的实际售价高于标准价格的200%，请确认是否正确。'
            
        return cleaned_data
    
    def get_warnings(self):
        """获取表单验证过程中的警告信息（不阻止提交但需要提示用户的信息）"""
        return self._warnings 