from django import forms
from django.utils.translation import gettext as _

from inventory.models import InventoryTransaction, Product


class InventoryTransactionForm(forms.ModelForm):
    class Meta:
        model = InventoryTransaction
        fields = ['product', 'quantity', 'notes']
        widgets = {
            'product': forms.Select(attrs={
                'class': 'form-control form-select',
                'aria-label': '商品',
                'style': 'height: 48px; font-size: 16px;'
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'step': '1',
                'placeholder': '数量',
                'inputmode': 'numeric',  # 在移动设备上显示数字键盘
                'aria-label': '数量',
                'autocomplete': 'off',  # 防止自动填充
                'pattern': '[0-9]*',  # HTML5验证，只允许数字
                'style': 'height: 48px; font-size: 16px;'
            }),
            'notes': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control',
                'placeholder': '备注信息',
                'aria-label': '备注'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 使用select_related优化查询
        self.fields['product'].queryset = Product.objects.all().select_related('category')
        
        self.fields['product'].empty_label = _('请选择商品')
        labels = {'product': '商品', 'quantity': '数量', 'notes': '备注', 'adjustment_action': '调整方式'}
        for name, field in self.fields.items():
            field.label = _(labels.get(name, field.label or name))
            field.widget.attrs.pop('style', None)
            for attr in ('placeholder', 'aria-label'):
                if attr in field.widget.attrs:
                    field.widget.attrs[attr] = _(field.widget.attrs[attr])

    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity is not None and quantity <= 0:
            raise forms.ValidationError(_('数量必须大于0'))
        return quantity

class InventoryAdjustmentForm(InventoryTransactionForm):
    adjustment_action = forms.ChoiceField(choices=[
        ('set', '设置为指定数量'), ('add', '增加指定数量'), ('subtract', '减少指定数量'),
    ], widget=forms.HiddenInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['quantity'].widget.attrs['min'] = '0'

    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity is not None and quantity < 0:
            raise forms.ValidationError('数量不能为负数')
        return quantity

    def clean(self):
        data = super().clean()
        if data.get('adjustment_action') in ('add', 'subtract') and data.get('quantity') == 0:
            self.add_error('quantity', '增加或减少的数量必须大于0')
        return data
