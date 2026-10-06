from django import template

register = template.Library()

@register.filter
def multiply(value, arg):
    """将数值乘以参数"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return value


@register.filter
def activity_summary(details, language='zh-hans'):
    """Show a short activity label instead of a request's internal diagnostics."""
    text = str(details or '')
    if not text.startswith('Accessed '):
        return text
    view = text.removeprefix('Accessed ').split(':', 1)[0]
    names = {
        'system_settings': ('系统设置', 'settings'),
        'log_list': ('系统日志', 'system logs'),
        'backup_list': ('数据备份', 'backups'),
        'user_list': ('用户管理', 'users'),
        'sales_trend_report': ('销售趋势', 'sales trends'),
        'top_products_report': ('热销商品', 'bestsellers'),
        'inventory_turnover_report': ('库存周转', 'inventory turnover'),
        'profit_report': ('利润报表', 'profit reports'),
        'member_analysis_report': ('会员分析', 'member analysis'),
        'recharge_report': ('会员充值记录', 'member recharges'),
        'operation_log_report': ('操作记录', 'operation history'),
    }
    zh, en = names.get(view, ('页面', 'a page'))
    return f'Viewed {en}' if language == 'en' else f'查看{zh}'
