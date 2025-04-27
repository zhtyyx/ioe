from django import template

register = template.Library()

@register.filter
def multiply(value, arg):
    """将数值乘以参数"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return value 