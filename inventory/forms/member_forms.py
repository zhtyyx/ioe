from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Div
from ..models.member import Member, MemberLevel, RechargeRecord


class MemberForm(forms.ModelForm):
    """会员表单"""
    class Meta:
        model = Member
        fields = ['name', 'phone', 'gender', 'birthday', 'level', 'email', 'member_id', 'address', 'notes', 'is_active']
        widgets = {
            'birthday': forms.DateInput(attrs={'type': 'date'})
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Row(
                Column('name', css_class='form-group col-md-6 mb-0'),
                Column('phone', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('gender', css_class='form-group col-md-4 mb-0'),
                Column('birthday', css_class='form-group col-md-4 mb-0'),
                Column('member_id', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('level', css_class='form-group col-md-6 mb-0'),
                Column('email', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            'address',
            'notes',
            'is_active',
            Submit('submit', '保存', css_class='btn btn-primary')
        )
    
    def clean_phone(self):
        """手机号验证"""
        phone = self.cleaned_data.get('phone')
        if not phone:
            raise forms.ValidationError('手机号不能为空')
        
        # 检查格式
        import re
        if not re.match(r'^\d{11}$', phone):
            raise forms.ValidationError('请输入11位手机号码')
        
        # 检查唯一性（排除当前实例）
        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            # 修改时检查
            if Member.objects.exclude(pk=instance.pk).filter(phone=phone).exists():
                raise forms.ValidationError('该手机号已被注册')
        else:
            # 新增时检查
            if Member.objects.filter(phone=phone).exists():
                raise forms.ValidationError('该手机号已被注册')
                
        return phone


class MemberLevelForm(forms.ModelForm):
    """会员等级表单"""
    class Meta:
        model = MemberLevel
        fields = ['name', 'discount', 'points_threshold', 'color', 'priority', 'is_default', 'is_active']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            'name',
            Row(
                Column('discount', css_class='form-group col-md-6 mb-0'),
                Column('points_threshold', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('color', css_class='form-group col-md-4 mb-0'),
                Column('priority', css_class='form-group col-md-4 mb-0'),
                Column('is_default', css_class='form-group col-md-2 mb-0'),
                Column('is_active', css_class='form-group col-md-2 mb-0'),
                css_class='form-row'
            ),
            Submit('submit', '保存', css_class='btn btn-primary')
        )
    
    def clean_discount(self):
        """折扣率验证"""
        discount = self.cleaned_data.get('discount')
        if discount < 0 or discount > 1:
            raise forms.ValidationError('折扣率必须在0到1之间')
        return discount
    
    def clean(self):
        """验证整个表单"""
        cleaned_data = super().clean()
        is_default = cleaned_data.get('is_default')
        
        # 如果设置为默认等级，检查是否有其他默认等级
        if is_default and not self.instance.pk:
            if MemberLevel.objects.filter(is_default=True).exists():
                self.add_error('is_default', '已存在默认等级，一次只能有一个默认等级')
        return cleaned_data


class RechargeForm(forms.ModelForm):
    """会员充值表单"""
    class Meta:
        model = RechargeRecord
        fields = ['amount', 'actual_amount', 'payment_method', 'remark']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Row(
                Column('amount', css_class='form-group col-md-6 mb-0'),
                Column('actual_amount', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            'payment_method',
            'remark',
            Submit('submit', '确认充值', css_class='btn btn-primary')
        )
        
        # 自动填充实收金额等于充值金额
        self.fields['actual_amount'].initial = self.fields['amount'].initial


class MemberImportForm(forms.Form):
    """会员批量导入表单"""
    csv_file = forms.FileField(
        label='CSV文件',
        help_text='请上传CSV格式的会员数据文件，必须包含姓名和手机号两个字段'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-8'
        self.helper.layout = Layout(
            'csv_file',
            Div(
                Submit('submit', '导入', css_class='btn btn-primary'),
                css_class='form-group'
            )
        )
        
    def clean_csv_file(self):
        """CSV文件格式验证"""
        csv_file = self.cleaned_data.get('csv_file')
        if not csv_file:
            raise forms.ValidationError('请选择文件')
        
        # 检查文件扩展名
        if not csv_file.name.endswith('.csv'):
            raise forms.ValidationError('请上传CSV格式的文件')
            
        # 文件大小限制（2MB）
        if csv_file.size > 2 * 1024 * 1024:
            raise forms.ValidationError('文件大小不能超过2MB')
            
        return csv_file 