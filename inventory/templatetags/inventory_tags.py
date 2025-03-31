from django import template
import json

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