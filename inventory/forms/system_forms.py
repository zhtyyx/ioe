from django import forms
from django.conf import settings
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Div

from inventory.models import SystemConfig


class SystemConfigForm(forms.ModelForm):
    """系统配置表单"""
    class Meta:
        model = SystemConfig
        fields = [
            'company_name', 'company_address', 'company_phone', 
            'company_email', 'company_website', 'company_logo',
            'barcode_width', 'barcode_height', 'barcode_font_size',
            'barcode_show_price', 'barcode_show_name', 'barcode_show_company',
            'receipt_header', 'receipt_footer',
            'enable_low_stock_alert', 'default_tax_rate', 'currency_symbol',
            'timezone'
        ]
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'form-control'}),
            'company_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'company_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'company_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'company_website': forms.URLInput(attrs={'class': 'form-control'}),
            'company_logo': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'barcode_width': forms.NumberInput(attrs={'class': 'form-control', 'min': 100, 'max': 1000}),
            'barcode_height': forms.NumberInput(attrs={'class': 'form-control', 'min': 50, 'max': 500}),
            'barcode_font_size': forms.NumberInput(attrs={'class': 'form-control', 'min': 8, 'max': 24}),
            'barcode_show_price': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'barcode_show_name': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'barcode_show_company': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'receipt_header': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'receipt_footer': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'enable_low_stock_alert': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'default_tax_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': 0, 'max': 1}),
            'currency_symbol': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 5}),
            'timezone': forms.Select(attrs={'class': 'form-control form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_enctype = 'multipart/form-data'
        
        # 添加时区选项
        timezone_choices = [(tz, tz) for tz in settings.TIME_ZONE_CHOICES] if hasattr(settings, 'TIME_ZONE_CHOICES') else [
            ('Asia/Shanghai', '中国标准时间 (UTC+8)'),
            ('Asia/Hong_Kong', '香港时间 (UTC+8)'),
            ('Asia/Tokyo', '东京时间 (UTC+9)'),
            ('Asia/Singapore', '新加坡时间 (UTC+8)'),
            ('Europe/London', '伦敦时间 (UTC+0/+1)'),
            ('America/New_York', '纽约时间 (UTC-5/-4)'),
            ('America/Los_Angeles', '洛杉矶时间 (UTC-8/-7)'),
            ('UTC', '协调世界时 (UTC)'),
        ]
        self.fields['timezone'].choices = timezone_choices
        
        # 设置表单布局
        self.helper.layout = Layout(
            Div(
                Div('company_name', css_class='col-md-12'),
                Div('company_address', css_class='col-md-12'),
                Div('company_phone', css_class='col-md-6'),
                Div('company_email', css_class='col-md-6'),
                Div('company_website', css_class='col-md-6'),
                Div('company_logo', css_class='col-md-6'),
                css_class='row mb-4'
            ),
            Div(
                Div('barcode_width', css_class='col-md-4'),
                Div('barcode_height', css_class='col-md-4'),
                Div('barcode_font_size', css_class='col-md-4'),
                Div('barcode_show_price', css_class='col-md-4'),
                Div('barcode_show_name', css_class='col-md-4'),
                Div('barcode_show_company', css_class='col-md-4'),
                css_class='row mb-4'
            ),
            Div(
                Div('receipt_header', css_class='col-md-6'),
                Div('receipt_footer', css_class='col-md-6'),
                css_class='row mb-4'
            ),
            Div(
                Div('enable_low_stock_alert', css_class='col-md-4'),
                Div('default_tax_rate', css_class='col-md-3'),
                Div('currency_symbol', css_class='col-md-2'),
                Div('timezone', css_class='col-md-3'),
                css_class='row mb-4'
            ),
            Submit('submit', '保存设置', css_class='btn btn-primary')
        )


class StoreForm(forms.ModelForm):
    """商店表单"""
    class Meta:
        model = None  # 将在forms/__init__.py中设置正确的model
        fields = ['name', 'address', 'phone', 'email', 'manager', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'manager': forms.Select(attrs={'class': 'form-control form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        
        # 设置表单布局
        self.helper.layout = Layout(
            Row(
                Column('name', css_class='form-group col-md-6 mb-0'),
                Column('phone', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            'address',
            Row(
                Column('email', css_class='form-group col-md-6 mb-0'),
                Column('manager', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            'is_active',
            Submit('submit', '保存', css_class='btn btn-primary')
        ) 