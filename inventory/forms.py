from django import forms
from .models import Product, Inventory, Sale, SaleItem, InventoryTransaction, Member, Category, InventoryCheck, InventoryCheckItem, MemberLevel, RechargeRecord
from django.utils import timezone
from datetime import timedelta

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['barcode', 'name', 'category', 'color', 'size', 'description', 'price', 'cost', 'image', 'specification', 'manufacturer']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class InventoryTransactionForm(forms.ModelForm):
    class Meta:
        model = InventoryTransaction
        fields = ['product', 'quantity', 'notes']

class SaleForm(forms.ModelForm):
    class Meta:
        model = Sale
        fields = ['remark']

class SaleItemForm(forms.ModelForm):
    actual_price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        label='实际售价',
        required=False,
        widget=forms.NumberInput(attrs={'class': 'price-input'})
    )

    class Meta:
        model = SaleItem
        fields = ['product', 'quantity', 'price', 'actual_price']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['actual_price'].widget.attrs['readonly'] = True

class MemberForm(forms.ModelForm):
    birthday = forms.DateField(
        label='生日',
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        help_text='用于会员生日提醒和年龄统计'
    )
    
    class Meta:
        model = Member
        fields = ['name', 'phone', 'level', 'gender', 'birthday']

class MemberLevelForm(forms.ModelForm):
    class Meta:
        model = MemberLevel
        fields = ['name', 'discount', 'points_threshold']
        widgets = {
            'discount': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'max': '1'}),
        }
        
    def clean_discount(self):
        discount = self.cleaned_data['discount']
        if discount < 0 or discount > 1:
            raise forms.ValidationError('折扣率必须在0到1之间')
        return discount

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description']

# 新增库存盘点相关表单
class InventoryCheckForm(forms.ModelForm):
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        label='商品分类',
        help_text='可选，仅对选定分类的商品进行盘点'
    )
    
    class Meta:
        model = InventoryCheck
        fields = ['name', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class InventoryCheckItemForm(forms.ModelForm):
    class Meta:
        model = InventoryCheckItem
        fields = ['actual_quantity', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 2}),
        }

class InventoryCheckApproveForm(forms.Form):
    adjust_inventory = forms.BooleanField(
        required=False,
        label='调整库存',
        help_text='选中此项将自动调整库存数量以匹配实际盘点数量'
    )
    
    confirm = forms.BooleanField(
        required=True,
        label='确认审核',
        help_text='我已检查所有盘点数据并确认其准确性'
    )

# 报表相关表单
class DateRangeForm(forms.Form):
    PERIOD_CHOICES = [
        ('day', '按日'),
        ('week', '按周'),
        ('month', '按月'),
    ]
    
    start_date = forms.DateField(
        label='开始日期',
        widget=forms.DateInput(attrs={'type': 'date'}),
        initial=timezone.now().date() - timedelta(days=30)
    )
    
    end_date = forms.DateField(
        label='结束日期',
        widget=forms.DateInput(attrs={'type': 'date'}),
        initial=timezone.now().date()
    )
    
    period = forms.ChoiceField(
        label='时间周期',
        choices=PERIOD_CHOICES,
        initial='day',
        required=False
    )
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError('开始日期不能晚于结束日期')
            
        return cleaned_data

class TopProductsForm(DateRangeForm):
    """用于热销商品报表的表单"""
    limit = forms.IntegerField(
        label='显示数量',
        min_value=5,
        max_value=50,
        initial=10,
        help_text='显示前N个热销商品'
    )

class InventoryTurnoverForm(DateRangeForm):
    """用于库存周转报表的表单"""
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        label='商品分类',
        help_text='可选，筛选特定分类的商品'
    )

class RechargeRecordForm(forms.ModelForm):
    actual_amount = forms.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        label='实收金额',
        required=True
    )
    
    class Meta:
        model = RechargeRecord
        fields = ['amount', 'actual_amount', 'payment_method', 'remark']
        widgets = {
            'remark': forms.Textarea(attrs={'rows': 3}),
        }