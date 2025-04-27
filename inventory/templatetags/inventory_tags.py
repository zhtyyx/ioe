from django import template
import json
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter(name='jsonify')
def jsonify(obj):
    """将对象转换为JSON字符串"""
    return json.dumps(obj)

@register.filter(name='currency')
def currency(value):
    """格式化为货币"""
    if value is None:
        return '¥0.00'
    return f'¥{value:.2f}'

@register.filter(name='divisor')
def divisor(value, arg):
    """计算一个数除以另一个数的结果（主要用于计算百分比）"""
    try:
        value = float(value)
        arg = float(arg)
        if arg == 0:
            return 0
        return value / arg * 100
    except (ValueError, TypeError):
        return 0
        
@register.filter(name='div')
def div(value, arg):
    """计算一个数除以另一个数的结果（用于计算平均值）"""
    try:
        value = float(value)
        arg = float(arg)
        if arg == 0:
            return 0
        return value / arg
    except (ValueError, TypeError):
        return 0

@register.filter
def percentage(value, total):
    """将数值转换为百分比"""
    if total == 0:
        return 0
    return round((value / total) * 100)

@register.simple_tag
def level_badge(level):
    """为会员等级生成格式化的徽章"""
    if not level:
        return mark_safe('<span class="badge bg-secondary">无等级</span>')
    
    # 使用等级的颜色属性，默认为primary
    color = level.color if hasattr(level, 'color') and level.color else 'primary'
    
    # 构建徽章HTML
    badge = f'<span class="badge bg-{color}">{level.name}</span>'
    
    # 如果是默认等级，添加特殊标记
    if hasattr(level, 'is_default') and level.is_default:
        badge = f'<span class="badge bg-{color}">{level.name} <i class="bi bi-star-fill ms-1"></i></span>'
    
    return mark_safe(badge)

@register.inclusion_tag('inventory/member/tags/level_selector.html')
def level_selector(levels, selected_id=None):
    """渲染会员等级选择器"""
    return {
        'levels': levels,
        'selected_id': selected_id
    } 