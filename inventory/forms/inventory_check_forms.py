from django import forms
from django.utils import timezone
from inventory.models import Category, InventoryCheck, InventoryCheckItem


class InventoryCheckForm(forms.ModelForm):
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        label='商品分类',
        help_text='可选，仅对选定分类的商品进行盘点',
        widget=forms.Select(attrs={
            'class': 'form-control form-select',
            'aria-label': '商品分类',
            'style': 'height: 48px; font-size: 16px;',
            'data-bs-toggle': 'tooltip',
            'title': '选择要盘点的商品分类',
            'data-mobile-friendly': 'true'  # 标记为移动友好元素
        })
    )
    
    scheduled_date = forms.DateField(
        label='计划盘点日期',
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
            'aria-label': '计划盘点日期',
            'style': 'height: 48px; font-size: 16px;',
            'data-bs-toggle': 'tooltip',
            'title': '设置计划进行盘点的日期',
            'min': timezone.now().date().isoformat(),  # 设置最小日期为今天
            'data-mobile-friendly': 'true'  # 标记为移动友好元素
        }),
        help_text='可选，设置计划进行盘点的日期'
    )
    
    priority = forms.ChoiceField(
        choices=[
            ('low', '低优先级'),
            ('normal', '普通'),
            ('high', '高优先级'),
            ('urgent', '紧急')
        ],
        required=False,
        initial='normal',
        label='优先级',
        widget=forms.Select(attrs={
            'class': 'form-control form-select',
            'aria-label': '优先级',
            'style': 'height: 48px; font-size: 16px;',
            'data-mobile-friendly': 'true'  # 标记为移动友好元素
        }),
        help_text='设置盘点任务的优先级'
    )
    
    class Meta:
        model = InventoryCheck
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '盘点名称',
                'aria-label': '盘点名称',
                'style': 'height: 48px; font-size: 16px;',
                'autocomplete': 'off',  # 防止自动填充
                'autofocus': True,  # 自动获取焦点
                'minlength': '2',  # 最小长度验证
                'maxlength': '100',  # 最大长度验证
                'required': 'required',  # HTML5必填验证
                'data-mobile-friendly': 'true'  # 标记为移动友好元素
            }),
            'description': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control',
                'placeholder': '盘点描述',
                'aria-label': '盘点描述',
                'style': 'font-size: 16px;',  # 增大字体
                'maxlength': '500',  # 最大长度验证
                'data-mobile-friendly': 'true'  # 标记为移动友好元素
            }),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 使用select_related优化查询
        self.fields['category'].queryset = Category.objects.all().order_by('name')
        
        # 添加响应式布局的辅助类
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': field.widget.attrs.get('class', '') + ' mb-2',  # 添加下边距
                'autocapitalize': 'off',  # 防止自动大写首字母
            })
            
        # 为移动设备优化标签显示
        for field_name, field in self.fields.items():
            if not field.widget.attrs.get('placeholder'):
                field.widget.attrs['placeholder'] = field.label


class InventoryCheckItemForm(forms.ModelForm):
    barcode_scan = forms.CharField(
        max_length=100,
        label='扫描条码',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '扫描商品条码',
            'inputmode': 'numeric',  # 在移动设备上显示数字键盘
            'aria-label': '扫描条码',
            'autocomplete': 'off',  # 防止自动填充
            'autofocus': True,  # 自动获取焦点
            'style': 'height: 48px; font-size: 16px;'  # 增大触摸区域和字体
        }),
        help_text='扫描商品条码快速定位商品'
    )
    
    class Meta:
        model = InventoryCheckItem
        fields = ['actual_quantity', 'notes']
        widgets = {
            'actual_quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '实际数量',
                'inputmode': 'numeric',  # 在移动设备上显示数字键盘
                'aria-label': '实际数量',
                'autocomplete': 'off',  # 防止自动填充
                'pattern': '[0-9]*',  # HTML5验证，只允许数字
                'style': 'height: 48px; font-size: 16px;'  # 增大触摸区域和字体
            }),
            'notes': forms.Textarea(attrs={
                'rows': 2,
                'class': 'form-control',
                'placeholder': '备注',
                'aria-label': '备注',
                'style': 'font-size: 16px;'  # 增大字体
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 添加响应式布局的辅助类
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': field.widget.attrs.get('class', '') + ' mb-2',  # 添加下边距
                'autocapitalize': 'off',  # 防止自动大写首字母
            })
        
    def clean_actual_quantity(self):
        actual_quantity = self.cleaned_data.get('actual_quantity')
        if actual_quantity is not None and actual_quantity < 0:
            raise forms.ValidationError('实际数量不能为负数')
        return actual_quantity


class InventoryCheckApproveForm(forms.Form):
    adjust_inventory = forms.BooleanField(
        required=False,
        label='调整库存',
        help_text='选中此项将自动调整库存数量以匹配实际盘点数量',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'aria-label': '调整库存',
            'style': 'width: 20px; height: 20px;'  # 增大触摸区域
        })
    )
    
    confirm = forms.BooleanField(
        required=True,
        label='确认审核',
        help_text='我已检查所有盘点数据并确认其准确性',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'aria-label': '确认审核',
            'style': 'width: 20px; height: 20px;'  # 增大触摸区域
        })
    )
    
    notes = forms.CharField(
        required=False,
        label='审核备注',
        widget=forms.Textarea(attrs={
            'rows': 2,
            'class': 'form-control',
            'placeholder': '审核备注（可选）',
            'aria-label': '审核备注'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 添加响应式布局的辅助类
        for field in self.fields.values():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({
                    'class': field.widget.attrs.get('class', '') + ' mb-2',  # 添加下边距
                })
    
    def clean(self):
        cleaned_data = super().clean()
        confirm = cleaned_data.get('confirm')
        
        if not confirm:
            self.add_error('confirm', '必须确认审核才能继续')
            
        return cleaned_data 