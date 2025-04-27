from django import forms
from django.utils import timezone
from datetime import timedelta, datetime, date

from inventory.models import Category, Store


class DateRangeForm(forms.Form):
    """通用日期范围表单，用于所有报表"""
    
    PERIOD_CHOICES = [
        ('day', '按日'),
        ('week', '按周'),
        ('month', '按月'),
        ('quarter', '按季度'),
        ('year', '按年'),
        ('hour', '按小时'),  # 新增按小时统计选项
        ('minute', '按分钟'),  # 新增按分钟统计选项，适用于实时监控
    ]
    
    CACHE_PRESETS = [
        (5, '5分钟'),  # 新增更短的缓存时间
        (15, '15分钟'),
        (30, '30分钟'),
        (60, '1小时'),
        (180, '3小时'),
        (360, '6小时'),
        (720, '12小时'),
        (1440, '24小时'),
        (2880, '2天'),  # 新增更长的缓存时间
        (10080, '7天'),  # 新增周缓存
        (0, '不缓存'),  # 新增不缓存选项
    ]
    
    # 预设时间范围选项
    DATE_RANGE_PRESETS = [
        ('today', '今天'),
        ('yesterday', '昨天'),
        ('this_week', '本周'),
        ('last_week', '上周'),
        ('this_month', '本月'),
        ('last_month', '上月'),
        ('this_quarter', '本季度'),
        ('last_quarter', '上季度'),
        ('this_year', '今年'),
        ('last_year', '去年'),
        ('last_3_days', '最近3天'),  # 新增更短的时间范围
        ('last_7_days', '最近7天'),
        ('last_14_days', '最近14天'),  # 新增两周选项
        ('last_30_days', '最近30天'),
        ('last_60_days', '最近60天'),  # 新增更多选项
        ('last_90_days', '最近90天'),
        ('last_180_days', '最近半年'),  # 新增半年选项
        ('last_365_days', '最近一年'),
        ('current_week_to_date', '本周至今'),  # 新增至今选项
        ('current_month_to_date', '本月至今'),
        ('current_quarter_to_date', '本季度至今'),
        ('current_year_to_date', '今年至今'),
        ('custom', '自定义范围'),
    ]
    
    date_range_preset = forms.ChoiceField(
        label='预设时间范围',
        choices=DATE_RANGE_PRESETS,
        initial='last_30_days',
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control form-select',
            'aria-label': '预设时间范围',
            'style': 'height: 48px; font-size: 16px;'  # 增大触摸区域和字体
        }),
        help_text='选择预设时间范围可快速设置开始和结束日期'
    )
    
    start_date = forms.DateField(
        label='开始日期',
        widget=forms.DateInput(attrs={
            'type': 'date', 
            'class': 'form-control',
            'aria-label': '开始日期',
            'style': 'height: 48px; font-size: 16px;',  # 增大触摸区域和字体
            'data-bs-toggle': 'tooltip',
            'title': '报表开始日期'
        }),
        initial=timezone.now().date() - timedelta(days=30)
    )
    
    end_date = forms.DateField(
        label='结束日期',
        widget=forms.DateInput(attrs={
            'type': 'date', 
            'class': 'form-control',
            'aria-label': '结束日期',
            'style': 'height: 48px; font-size: 16px;',  # 增大触摸区域和字体
            'data-bs-toggle': 'tooltip',
            'title': '报表结束日期'
        }),
        initial=timezone.now().date()
    )
    
    period = forms.ChoiceField(
        label='时间周期',
        choices=PERIOD_CHOICES,
        initial='day',
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control form-select',
            'aria-label': '时间周期'
        })
    )
    
    use_cache = forms.BooleanField(
        label='使用缓存',
        required=False,
        initial=True,
        help_text='使用缓存可以提高报表生成速度，但可能不会显示最新数据',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'aria-label': '使用缓存',
            'data-bs-toggle': 'tooltip',
            'title': '启用缓存可显著提高报表加载速度',
            'style': 'width: 20px; height: 20px;'  # 增大触摸区域
        })
    )
    
    cache_timeout = forms.IntegerField(
        label='缓存时间(分钟)',
        required=False,
        initial=60,
        min_value=0,  # 允许设置为0表示不缓存
        max_value=10080,  # 7天
        help_text='缓存数据的有效时间，0表示不缓存',
        widget=forms.NumberInput(attrs={
            'class': 'form-control', 
            'step': '5',
            'aria-label': '缓存时间',
            'inputmode': 'numeric',  # 在移动设备上显示数字键盘
            'data-bs-toggle': 'tooltip',
            'title': '设置报表数据缓存的有效时间（分钟）',
            'style': 'height: 48px; font-size: 16px;'  # 增大触摸区域和字体
        })
    )
    
    cache_preset = forms.ChoiceField(
        label='预设缓存时间',
        choices=CACHE_PRESETS,
        required=False,
        initial=60,
        widget=forms.Select(attrs={
            'class': 'form-control form-select',
            'aria-label': '预设缓存时间',
            'data-bs-toggle': 'tooltip',
            'title': '选择预设的缓存时间',
            'style': 'height: 48px; font-size: 16px;'  # 增大触摸区域和字体
        })
    )
    
    force_refresh = forms.BooleanField(
        label='强制刷新',
        required=False,
        initial=False,
        help_text='强制重新生成报表数据，忽略缓存',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'aria-label': '强制刷新',
            'data-bs-toggle': 'tooltip',
            'title': '强制重新生成报表数据，忽略缓存',
            'style': 'width: 20px; height: 20px;'  # 增大触摸区域
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 添加响应式布局的辅助类
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': field.widget.attrs.get('class', '') + ' mb-2',  # 添加下边距
            })
    
    def _get_date_range_from_preset(self, preset):
        """根据预设值获取日期范围"""
        today = timezone.now().date()
        
        # 计算本周的开始日期（周一）
        def get_week_start(d):
            return d - timedelta(days=d.weekday())
        
        # 计算本月的开始日期
        def get_month_start(d):
            return date(d.year, d.month, 1)
        
        # 计算本季度的开始日期
        def get_quarter_start(d):
            quarter = (d.month - 1) // 3 + 1
            return date(d.year, 3 * quarter - 2, 1)
        
        # 计算本年的开始日期
        def get_year_start(d):
            return date(d.year, 1, 1)
            
        if preset == 'today':
            return today, today
        elif preset == 'yesterday':
            yesterday = today - timedelta(days=1)
            return yesterday, yesterday
        elif preset == 'this_week':
            week_start = get_week_start(today)
            return week_start, today
        elif preset == 'last_week':
            this_week_start = get_week_start(today)
            last_week_start = this_week_start - timedelta(days=7)
            last_week_end = this_week_start - timedelta(days=1)
            return last_week_start, last_week_end
        elif preset == 'this_month':
            month_start = get_month_start(today)
            return month_start, today
        elif preset == 'last_month':
            this_month_start = get_month_start(today)
            last_month_end = this_month_start - timedelta(days=1)
            last_month_start = get_month_start(last_month_end)
            return last_month_start, last_month_end
        elif preset == 'this_quarter':
            quarter_start = get_quarter_start(today)
            return quarter_start, today
        elif preset == 'last_quarter':
            this_quarter_start = get_quarter_start(today)
            last_quarter_end = this_quarter_start - timedelta(days=1)
            # 寻找上季度的开始
            if this_quarter_start.month == 1:  # 如果是第一季度
                last_quarter_start = date(this_quarter_start.year - 1, 10, 1)
            else:
                last_quarter_start = date(this_quarter_start.year, this_quarter_start.month - 3, 1)
            return last_quarter_start, last_quarter_end
        elif preset == 'this_year':
            year_start = get_year_start(today)
            return year_start, today
        elif preset == 'last_year':
            this_year_start = get_year_start(today)
            last_year_end = this_year_start - timedelta(days=1)
            last_year_start = date(last_year_end.year, 1, 1)
            return last_year_start, last_year_end
        elif preset == 'last_3_days':
            return today - timedelta(days=2), today
        elif preset == 'last_7_days':
            return today - timedelta(days=6), today
        elif preset == 'last_14_days':
            return today - timedelta(days=13), today
        elif preset == 'last_30_days':
            return today - timedelta(days=29), today
        elif preset == 'last_60_days':
            return today - timedelta(days=59), today
        elif preset == 'last_90_days':
            return today - timedelta(days=89), today
        elif preset == 'last_180_days':
            return today - timedelta(days=179), today
        elif preset == 'last_365_days':
            return today - timedelta(days=364), today
        elif preset == 'current_week_to_date':
            return get_week_start(today), today
        elif preset == 'current_month_to_date':
            return get_month_start(today), today
        elif preset == 'current_quarter_to_date':
            return get_quarter_start(today), today
        elif preset == 'current_year_to_date':
            return get_year_start(today), today
            
        # 如果没有匹配的预设或选择了自定义，返回None
        return None, None
    
    def clean(self):
        cleaned_data = super().clean()
        preset = cleaned_data.get('date_range_preset')
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        # 如果选择了预设日期范围（不是自定义），计算对应的开始和结束日期
        if preset and preset != 'custom':
            start_date, end_date = self._get_date_range_from_preset(preset)
            if start_date and end_date:
                cleaned_data['start_date'] = start_date
                cleaned_data['end_date'] = end_date
                
        # 确保开始日期不大于结束日期
        if start_date and end_date and start_date > end_date:
            self.add_error('start_date', '开始日期不能晚于结束日期')
            
        # 如果设置了预设缓存时间，更新缓存超时
        cache_preset = cleaned_data.get('cache_preset')
        if cache_preset:
            try:
                cleaned_data['cache_timeout'] = int(cache_preset)
            except (ValueError, TypeError):
                pass  # 如果转换失败，保持原样
                
        # 如果强制刷新，禁用缓存
        if cleaned_data.get('force_refresh'):
            cleaned_data['use_cache'] = False
            cleaned_data['cache_timeout'] = 0
            
        # 给小的日期范围选择更小的缓存时间，除非用户明确选择
        if not cache_preset and preset in ('today', 'yesterday', 'last_3_days'):
            cleaned_data['cache_timeout'] = min(cleaned_data.get('cache_timeout', 60), 30)  # 最多30分钟
            
        return cleaned_data
    
    def get_date_range_display(self):
        """获取日期范围的显示文本，用于报表标题等"""
        preset = self.cleaned_data.get('date_range_preset')
        
        # 如果选择了预设，返回预设显示名
        if preset and preset != 'custom':
            for value, label in self.DATE_RANGE_PRESETS:
                if value == preset:
                    return label
                    
        # 如果是自定义范围，显示实际日期区间
        start_date = self.cleaned_data.get('start_date')
        end_date = self.cleaned_data.get('end_date')
        if start_date and end_date:
            if start_date == end_date:
                return f"{start_date.strftime('%Y-%m-%d')}"
            return f"{start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}"
            
        # 默认情况
        return '自定义日期范围'


class TopProductsForm(DateRangeForm):
    """用于热销商品报表的表单"""
    limit = forms.IntegerField(
        label='显示数量',
        initial=10,
        min_value=1,
        max_value=100,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )


class InventoryTurnoverForm(DateRangeForm):
    """用于库存周转报表的表单"""
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        empty_label="所有分类",
        widget=forms.Select(attrs={'class': 'form-control form-select'})
    )


# 添加缺失的表单类
class ReportFilterForm(DateRangeForm):
    """通用报表筛选表单，继承DateRangeForm并添加分类和门店筛选"""
    category = forms.ModelChoiceField(
        queryset=Category.objects.filter(is_active=True),
        required=False,
        empty_label="所有分类",
        widget=forms.Select(attrs={
            'class': 'form-control form-select',
            'aria-label': '商品分类',
            'data-bs-toggle': 'tooltip',
            'title': '按商品分类筛选报表数据',
            'style': 'height: 48px; font-size: 16px;'  # 增大触摸区域和字体
        })
    )
    
    store = forms.ModelChoiceField(
        queryset=Store.objects.filter(is_active=True),  # 恢复is_active过滤，只显示活跃的门店
        required=False,
        empty_label="所有门店",
        widget=forms.Select(attrs={
            'class': 'form-control form-select',
            'aria-label': '门店',
            'data-bs-toggle': 'tooltip',
            'title': '按门店筛选报表数据',
            'style': 'height: 48px; font-size: 16px;'  # 增大触摸区域和字体
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 处理门店为空的情况
        if Store.objects.count() == 0:
            self.fields.pop('store', None)


class SalesReportForm(ReportFilterForm):
    """销售报表专用表单，继承ReportFilterForm并添加销售相关筛选"""
    SALES_TYPE_CHOICES = [
        ('all', '所有销售'),
        ('retail', '零售销售'),
        ('wholesale', '批发销售'),
        ('member', '会员销售'),
        ('online', '线上销售'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('all', '所有支付方式'),
        ('cash', '现金'),
        ('card', '刷卡'),
        ('alipay', '支付宝'),
        ('wechat', '微信支付'),
        ('other', '其他方式'),
    ]
    
    SORT_CHOICES = [
        ('date', '按日期'),
        ('amount', '按金额'),
        ('profit', '按利润'),
        ('quantity', '按数量'),
    ]
    
    sales_type = forms.ChoiceField(
        label='销售类型',
        choices=SALES_TYPE_CHOICES,
        required=False,
        initial='all',
        widget=forms.Select(attrs={
            'class': 'form-control form-select',
            'aria-label': '销售类型',
            'data-bs-toggle': 'tooltip',
            'title': '按销售类型筛选',
            'style': 'height: 48px; font-size: 16px;'  # 增大触摸区域和字体
        })
    )
    
    payment_method = forms.ChoiceField(
        label='支付方式',
        choices=PAYMENT_METHOD_CHOICES,
        required=False,
        initial='all',
        widget=forms.Select(attrs={
            'class': 'form-control form-select',
            'aria-label': '支付方式',
            'data-bs-toggle': 'tooltip',
            'title': '按支付方式筛选',
            'style': 'height: 48px; font-size: 16px;'  # 增大触摸区域和字体
        })
    )
    
    min_amount = forms.DecimalField(
        label='最小金额',
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'aria-label': '最小金额',
            'placeholder': '最小销售金额',
            'inputmode': 'decimal',  # 在移动设备上显示数字键盘
            'style': 'height: 48px; font-size: 16px;'  # 增大触摸区域和字体
        })
    )
    
    max_amount = forms.DecimalField(
        label='最大金额',
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'aria-label': '最大金额',
            'placeholder': '最大销售金额',
            'inputmode': 'decimal',  # 在移动设备上显示数字键盘
            'style': 'height: 48px; font-size: 16px;'  # 增大触摸区域和字体
        })
    )
    
    sort_by = forms.ChoiceField(
        label='排序方式',
        choices=SORT_CHOICES,
        required=False,
        initial='date',
        widget=forms.Select(attrs={
            'class': 'form-control form-select',
            'aria-label': '排序方式',
            'data-bs-toggle': 'tooltip',
            'title': '选择报表数据的排序方式',
            'style': 'height: 48px; font-size: 16px;'  # 增大触摸区域和字体
        })
    )
    
    include_tax = forms.BooleanField(
        label='包含税费',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'aria-label': '包含税费',
            'data-bs-toggle': 'tooltip',
            'title': '是否在报表中包含税费',
            'style': 'width: 20px; height: 20px;'  # 增大触摸区域
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        min_amount = cleaned_data.get('min_amount')
        max_amount = cleaned_data.get('max_amount')
        
        # 验证最小金额不大于最大金额
        if min_amount and max_amount and min_amount > max_amount:
            self.add_error('min_amount', '最小金额不能大于最大金额')
            
        return cleaned_data 