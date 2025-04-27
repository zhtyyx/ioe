from django import forms
from django.core.validators import FileExtensionValidator
from inventory.models import Product, Category, Inventory
import csv
import io

class BatchProductImportForm(forms.Form):
    """
    批量导入商品表单
    """
    file = forms.FileField(
        label='CSV文件',
        validators=[FileExtensionValidator(allowed_extensions=['csv'])],
        help_text='请上传CSV格式文件，包含商品信息',
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )
    
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        label='默认分类',
        required=False,
        help_text='如果CSV中未指定分类，将使用此分类',
        widget=forms.Select(attrs={'class': 'form-control form-select'})
    )
    
    update_existing = forms.BooleanField(
        label='更新已存在商品',
        required=False,
        initial=False,
        help_text='如果勾选，将更新已存在的商品信息',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            # 检查CSV文件格式
            try:
                # 读取CSV文件
                csv_file = file.read().decode('utf-8')
                csv_data = csv.reader(io.StringIO(csv_file))
                
                # 获取表头
                headers = next(csv_data)
                
                # 检查必要的列是否存在
                required_columns = ['barcode', 'name', 'price', 'cost']
                missing_columns = [col for col in required_columns if col not in headers]
                
                if missing_columns:
                    raise forms.ValidationError(f"CSV文件缺少必要的列: {', '.join(missing_columns)}")
                
                # 重置文件指针
                file.seek(0)
                
            except Exception as e:
                raise forms.ValidationError(f"CSV文件格式错误: {str(e)}")
        
        return file

class BatchInventoryUpdateForm(forms.Form):
    """
    批量调整库存表单
    """
    file = forms.FileField(
        label='CSV文件',
        validators=[FileExtensionValidator(allowed_extensions=['csv'])],
        help_text='请上传CSV格式文件，包含商品条码和库存数量',
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )
    
    adjustment_type = forms.ChoiceField(
        label='调整类型',
        choices=[
            ('set', '设置为指定数量'),
            ('add', '增加指定数量'),
            ('subtract', '减少指定数量'),
        ],
        initial='set',
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    
    notes = forms.CharField(
        label='备注',
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        help_text='批量调整的原因或说明'
    )
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            try:
                # 读取CSV文件
                csv_file = file.read().decode('utf-8')
                csv_data = csv.reader(io.StringIO(csv_file))
                
                # 获取表头
                headers = next(csv_data)
                
                # 检查必要的列是否存在
                required_columns = ['barcode', 'quantity']
                missing_columns = [col for col in required_columns if col not in headers]
                
                if missing_columns:
                    raise forms.ValidationError(f"CSV文件缺少必要的列: {', '.join(missing_columns)}")
                
                # 检查数据有效性
                row_number = 1  # 表头是第1行
                errors = []
                
                for row in csv_data:
                    row_number += 1
                    if len(row) != len(headers):
                        errors.append(f"第{row_number}行: 列数不匹配")
                        continue
                    
                    # 创建行数据字典
                    row_data = dict(zip(headers, row))
                    
                    # 检查条码是否存在
                    barcode = row_data.get('barcode', '').strip()
                    if not barcode:
                        errors.append(f"第{row_number}行: 条码不能为空")
                    
                    # 检查数量是否为有效数字
                    quantity = row_data.get('quantity', '').strip()
                    try:
                        quantity = int(quantity)
                        if quantity < 0 and self.cleaned_data.get('adjustment_type') == 'set':
                            errors.append(f"第{row_number}行: 设置库存时数量不能为负数")
                    except ValueError:
                        errors.append(f"第{row_number}行: 数量必须是整数")
                
                if errors:
                    raise forms.ValidationError(errors)
                
                # 重置文件指针
                file.seek(0)
                
            except Exception as e:
                if not isinstance(e, forms.ValidationError):
                    raise forms.ValidationError(f"CSV文件处理错误: {str(e)}")
                raise
        
        return file

class ProductBatchDeleteForm(forms.Form):
    """
    批量删除商品表单
    """
    product_ids = forms.CharField(
        widget=forms.HiddenInput(),
        required=True
    )
    
    confirm = forms.BooleanField(
        label='确认删除',
        required=True,
        help_text='我已了解此操作不可逆，并确认要删除选中的商品'
    )
    
    def clean_product_ids(self):
        product_ids_str = self.cleaned_data.get('product_ids')
        if not product_ids_str:
            raise forms.ValidationError('未选择任何商品')
        
        try:
            product_ids = [int(id.strip()) for id in product_ids_str.split(',') if id.strip()]
            if not product_ids:
                raise forms.ValidationError('未选择任何商品')
            return product_ids
        except ValueError:
            raise forms.ValidationError('商品ID格式错误')