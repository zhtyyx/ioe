import re
from django import forms
from django.forms import inlineformset_factory
from inventory.models import Product, Category, ProductImage, ProductBatch, Supplier


class ProductForm(forms.ModelForm):
    barcode = forms.CharField(
        max_length=100,
        label='商品条码',
        help_text='支持EAN-13、UPC、ISBN等标准条码格式',
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': '请输入商品条码',
            'autocomplete': 'off',  # 防止自动填充
            'inputmode': 'numeric',  # 在移动设备上显示数字键盘
            'pattern': '[A-Za-z0-9-]+',  # HTML5验证模式，修复转义序列
            'aria-label': '商品条码'
        })
    )
    
    # 添加库存预警级别字段
    warning_level = forms.IntegerField(
        label='预警库存',
        help_text='库存低于此数量时将发出预警',
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '0',
            'step': '1',
            'placeholder': '预警数量',
            'aria-label': '预警库存'
        })
    )
    
    class Meta:
        model = Product
        fields = ['barcode', 'name', 'category', 'color', 'size', 'description', 'price', 'cost', 'image', 'specification', 'manufacturer', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '请输入商品名称', 'aria-label': '商品名称'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '售价', 'inputmode': 'decimal', 'aria-label': '售价'}),
            'cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '成本价', 'inputmode': 'decimal', 'aria-label': '成本价'}),
            'specification': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '规格', 'aria-label': '规格'}),
            'manufacturer': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '制造商', 'aria-label': '制造商'}),
            'category': forms.Select(attrs={'class': 'form-control form-select', 'aria-label': '商品分类'}),
            'color': forms.Select(attrs={'class': 'form-control form-select', 'aria-label': '颜色'}),
            'size': forms.Select(attrs={'class': 'form-control form-select', 'aria-label': '尺码'}),
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*', 'aria-label': '商品图片'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input', 'aria-label': '是否启用'}),
        }
        
    def clean_barcode(self):
        barcode = self.cleaned_data.get('barcode')
        if barcode:
            # 移除空格和其他不可见字符
            barcode = re.sub(r'\s', '', barcode).strip()
            
            # 检查是否只包含数字、字母和连字符
            if not all(c.isalnum() or c == '-' for c in barcode):
                raise forms.ValidationError('条码只能包含数字、字母和连字符')
            
            # 检查条码是否已存在（排除当前实例）
            existing = Product.objects.filter(barcode=barcode)
            if self.instance and self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
                
            if existing.exists():
                raise forms.ValidationError('该条码已存在，请勿重复添加')
                
            # 检查常见条码格式
            # 标准条码格式
            # EAN-13: 13位数字
            # EAN-8: 8位数字
            # UPC-A: 12位数字
            # UPC-E: 8位数字，以0开头
            # ISBN-13: 13位数字，通常以978或979开头
            # ISBN-10: 10位数字或数字+X
            # JAN: 日本商品编码，13位数字，以45或49开头
            # ITF-14: 14位数字，通常用于物流包装
            # GTIN-14: 14位数字，全球贸易项目代码
            # Code-39: 可变长度，字母数字和特定符号
            # Code-128: 可变长度，所有ASCII字符
            ean13_pattern = re.compile(r'^\d{13}$')
            ean8_pattern = re.compile(r'^\d{8}$')
            upc_pattern = re.compile(r'^\d{12}$')
            upc_e_pattern = re.compile(r'^0\d{7}$')
            isbn13_pattern = re.compile(r'^(978|979)\d{10}$')
            isbn10_pattern = re.compile(r'^\d{9}[\dX]$')
            jan_pattern = re.compile(r'^(45|49)\d{11}$')
            itf14_pattern = re.compile(r'^\d{14}$')
            gtin14_pattern = re.compile(r'^\d{14}$')
            
            # 如果不符合任何标准格式，添加警告（但不阻止保存）
            is_standard_format = (
                ean13_pattern.match(barcode) or
                ean8_pattern.match(barcode) or
                upc_pattern.match(barcode) or
                upc_e_pattern.match(barcode) or
                isbn13_pattern.match(barcode) or
                isbn10_pattern.match(barcode) or
                jan_pattern.match(barcode) or
                itf14_pattern.match(barcode) or
                gtin14_pattern.match(barcode)
            )
            
            if not is_standard_format:
                # 添加警告，但不阻止保存
                self.add_warning = '条码格式不符合常见标准格式，请确认无误'
                
        return barcode
        
    def clean(self):
        cleaned_data = super().clean()
        price = cleaned_data.get('price')
        cost = cleaned_data.get('cost')
        
        if price is not None and cost is not None and price < cost:
            self.add_warning = '当前售价低于成本价，请确认无误'
            
        return cleaned_data


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '分类名称',
                'aria-label': '分类名称',
                'style': 'height: 48px; font-size: 16px;',
                'autocomplete': 'off',  # 防止自动填充
                'autofocus': True  # 自动获取焦点
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': '分类描述',
                'rows': 3,
                'aria-label': '分类描述',
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
    
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            # 移除多余的空格
            name = name.strip()
            
            # 检查名称长度
            if len(name) < 2:
                raise forms.ValidationError('分类名称至少需要2个字符')
                
            # 检查是否已存在相同名称的分类（排除当前实例）
            existing = Category.objects.filter(name=name)
            if self.instance and self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
                
            if existing.exists():
                raise forms.ValidationError('该分类名称已存在，请使用其他名称')
                
        return name 


class ProductBatchForm(forms.ModelForm):
    """商品批次表单"""
    class Meta:
        model = ProductBatch
        fields = ['batch_number', 'production_date', 'expiry_date', 'quantity', 'cost_price', 'supplier', 'remarks']
        widgets = {
            'batch_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '批次号',
                'aria-label': '批次号'
            }),
            'production_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'aria-label': '生产日期'
            }),
            'expiry_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'aria-label': '过期日期'
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'step': '1',
                'placeholder': '数量',
                'aria-label': '数量'
            }),
            'cost_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': '成本价',
                'aria-label': '成本价'
            }),
            'supplier': forms.Select(attrs={
                'class': 'form-control form-select',
                'aria-label': '供应商'
            }),
            'remarks': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': '备注',
                'aria-label': '备注'
            }),
        }

    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity is not None and quantity < 0:
            raise forms.ValidationError('数量不能为负数')
        return quantity

    def clean_cost_price(self):
        cost_price = self.cleaned_data.get('cost_price')
        if cost_price is not None and cost_price < 0:
            raise forms.ValidationError('成本价不能为负数')
        return cost_price


# 创建商品图片的内联表单集
ProductImageFormSet = inlineformset_factory(
    Product, 
    ProductImage,
    fields=('image', 'alt_text', 'order', 'is_primary'),
    extra=3,  # 默认显示3个空表单
    can_delete=True,  # 允许删除
    widgets={
        'image': forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*',
            'aria-label': '图片'
        }),
        'alt_text': forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '图片描述',
            'aria-label': '图片描述'
        }),
        'order': forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '0',
            'step': '1',
            'placeholder': '排序',
            'aria-label': '排序'
        }),
        'is_primary': forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'aria-label': '是否主图'
        }),
    }
)


class ProductBulkForm(forms.Form):
    """批量创建商品表单"""
    category = forms.ModelChoiceField(
        queryset=Category.objects.filter(is_active=True),
        label='商品分类',
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-control form-select',
            'aria-label': '商品分类'
        })
    )
    name_prefix = forms.CharField(
        max_length=100,
        label='商品名称前缀',
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '例如：测试商品',
            'aria-label': '商品名称前缀'
        })
    )
    name_suffix_start = forms.IntegerField(
        label='编号起始值',
        initial=1,
        required=True,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
            'step': '1',
            'placeholder': '1',
            'aria-label': '编号起始值'
        })
    )
    name_suffix_end = forms.IntegerField(
        label='编号结束值',
        initial=10,
        required=True,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
            'step': '1',
            'placeholder': '10',
            'aria-label': '编号结束值'
        })
    )
    retail_price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        label='零售价',
        required=True,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': '零售价',
            'aria-label': '零售价'
        })
    )
    wholesale_price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        label='批发价',
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': '批发价（可选）',
            'aria-label': '批发价'
        })
    )
    cost_price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        label='成本价',
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': '成本价（可选）',
            'aria-label': '成本价'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        suffix_start = cleaned_data.get('name_suffix_start')
        suffix_end = cleaned_data.get('name_suffix_end')
        
        if suffix_start and suffix_end and suffix_start > suffix_end:
            raise forms.ValidationError('编号起始值不能大于结束值')
        
        # 限制批量创建数量不超过100
        if suffix_start and suffix_end and (suffix_end - suffix_start + 1) > 100:
            raise forms.ValidationError('批量创建商品数量不能超过100个')
        
        return cleaned_data


class ProductImportForm(forms.Form):
    """商品导入表单"""
    csv_file = forms.FileField(
        label='CSV文件',
        required=True,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.csv',
            'aria-label': 'CSV文件'
        })
    )
    
    def clean_csv_file(self):
        csv_file = self.cleaned_data.get('csv_file')
        if csv_file:
            # 检查文件类型
            if not csv_file.name.endswith('.csv'):
                raise forms.ValidationError('请上传CSV格式的文件')
            
            # 检查文件大小，限制为5MB
            if csv_file.size > 5 * 1024 * 1024:
                raise forms.ValidationError('文件大小不能超过5MB')
        
        return csv_file 