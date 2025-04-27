"""
Date and time utility functions.
"""
from datetime import datetime, time, timedelta, date
import calendar


def get_period_boundaries(date, period='day'):
    """
    Get the start and end datetime for a specific period.
    
    Args:
        date: The date to get boundaries for
        period: 'day', 'week', 'month' or 'year'
        
    Returns:
        tuple: (start_datetime, end_datetime)
    """
    if period == 'day':
        start_dt = datetime.combine(date, time.min)
        end_dt = datetime.combine(date, time.max)
    elif period == 'week':
        # Start of week (Monday)
        start_dt = datetime.combine(date - timedelta(days=date.weekday()), time.min)
        # End of week (Sunday)
        end_dt = datetime.combine(start_dt.date() + timedelta(days=6), time.max)
    elif period == 'month':
        # Start of month
        start_dt = datetime.combine(date.replace(day=1), time.min)
        # End of month - go to next month and go back one day
        if date.month == 12:
            next_month = date.replace(year=date.year+1, month=1, day=1)
        else:
            next_month = date.replace(month=date.month+1, day=1)
        end_dt = datetime.combine(next_month - timedelta(days=1), time.max)
    elif period == 'year':
        # Start of year
        start_dt = datetime.combine(date.replace(month=1, day=1), time.min)
        # End of year
        end_dt = datetime.combine(date.replace(month=12, day=31), time.max)
    else:
        # Default to day
        start_dt = datetime.combine(date, time.min)
        end_dt = datetime.combine(date, time.max)
        
    return (start_dt, end_dt)


def get_month_range(year, month):
    """
    获取指定年月的日期范围（开始日期和结束日期）
    
    参数:
        year: 年份，如2023
        month: 月份，如1表示一月
        
    返回:
        tuple: (start_date, end_date) 月份的开始日期和结束日期
    """
    # 确保输入合法
    year = int(year)
    month = int(month)
    
    if month < 1 or month > 12:
        raise ValueError("月份必须在1-12之间")
    
    # 月份第一天
    start_date = date(year, month, 1)
    
    # 月份最后一天（计算下个月第一天然后减去一天）
    if month == 12:
        end_date = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year, month + 1, 1) - timedelta(days=1)
    
    return (start_date, end_date)


def get_quarter_range(year, quarter):
    """
    获取指定年份和季度的日期范围
    
    参数:
        year: 年份，如2023
        quarter: 季度，1-4表示第一至第四季度
        
    返回:
        tuple: (start_date, end_date) 季度的开始日期和结束日期
    """
    # 确保输入合法
    year = int(year)
    quarter = int(quarter)
    
    if quarter < 1 or quarter > 4:
        raise ValueError("季度必须在1-4之间")
    
    # 确定季度对应的月份
    start_month = (quarter - 1) * 3 + 1  # 1, 4, 7, 10
    if quarter < 4:
        end_month = quarter * 3  # 3, 6, 9
    else:
        end_month = 12
    
    # 季度开始日期
    start_date = date(year, start_month, 1)
    
    # 季度结束日期（下个季度第一天减去一天）
    if end_month == 12:
        end_date = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year, end_month + 1, 1) - timedelta(days=1)
    
    return (start_date, end_date)


def get_year_range(year):
    """
    获取指定年份的日期范围
    
    参数:
        year: 年份，如2023
        
    返回:
        tuple: (start_date, end_date) 年份的开始日期和结束日期
    """
    # 确保输入合法
    year = int(year)
    
    # 年份开始日期（1月1日）
    start_date = date(year, 1, 1)
    
    # 年份结束日期（12月31日）
    end_date = date(year, 12, 31)
    
    return (start_date, end_date)


def get_date_format(period):
    """
    根据时间周期返回相应的日期格式
    
    参数:
        period: 时间周期，'day', 'week', 'month', 'quarter' 或 'year'
        
    返回:
        str: 日期格式字符串
    """
    formats = {
        'day': '%Y-%m-%d',
        'week': '%Y-%m-%d',
        'month': '%Y-%m',
        'quarter': '%Y-Q%q',
        'year': '%Y'
    }
    return formats.get(period, '%Y-%m-%d')


def get_date_range(start_date=None, end_date=None, period=None, days=None):
    """
    根据传入的参数获取日期范围，支持多种方式：
    1. 直接指定开始和结束日期
    2. 指定日期周期（如'today', 'yesterday', 'last_week', 'last_month'等）
    3. 指定天数（往前推N天）
    
    参数:
        start_date: 开始日期，datetime.date对象或者字符串（格式：YYYY-MM-DD）
        end_date: 结束日期，datetime.date对象或者字符串（格式：YYYY-MM-DD）
        period: 日期周期，可选值：'today', 'yesterday', 'this_week', 'last_week', 
                'this_month', 'last_month', 'this_quarter', 'last_quarter', 
                'this_year', 'last_year'
        days: 天数，往前推的天数
        
    返回:
        tuple: (start_date, end_date) 日期范围的开始和结束日期，都是datetime.date对象
    """
    today = date.today()
    
    # 处理字符串格式的日期
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # 如果直接指定了开始和结束日期，直接返回
    if start_date and end_date:
        return start_date, end_date
    
    # 根据周期计算日期范围
    if period:
        if period == 'today':
            return today, today
        elif period == 'yesterday':
            yesterday = today - timedelta(days=1)
            return yesterday, yesterday
        elif period == 'this_week':
            # 本周的周一
            monday = today - timedelta(days=today.weekday())
            return monday, today
        elif period == 'last_week':
            # 上周的周一和周日
            monday = today - timedelta(days=today.weekday() + 7)
            sunday = monday + timedelta(days=6)
            return monday, sunday
        elif period == 'this_month':
            # 本月的第一天
            first_day = date(today.year, today.month, 1)
            return first_day, today
        elif period == 'last_month':
            # 上个月的第一天和最后一天
            if today.month == 1:
                first_day = date(today.year - 1, 12, 1)
                last_day = date(today.year, 1, 1) - timedelta(days=1)
            else:
                first_day = date(today.year, today.month - 1, 1)
                last_day = date(today.year, today.month, 1) - timedelta(days=1)
            return first_day, last_day
        elif period == 'this_quarter':
            # 本季度的第一天
            quarter = (today.month - 1) // 3 + 1
            first_day = date(today.year, (quarter - 1) * 3 + 1, 1)
            return first_day, today
        elif period == 'last_quarter':
            # 上季度的第一天和最后一天
            quarter = (today.month - 1) // 3 + 1
            if quarter == 1:
                # 上一年第四季度
                first_day = date(today.year - 1, 10, 1)
                last_day = date(today.year, 1, 1) - timedelta(days=1)
            else:
                # 今年的上一季度
                first_day = date(today.year, (quarter - 2) * 3 + 1, 1)
                last_day = date(today.year, (quarter - 1) * 3 + 1, 1) - timedelta(days=1)
            return first_day, last_day
        elif period == 'this_year':
            # 今年的第一天
            first_day = date(today.year, 1, 1)
            return first_day, today
        elif period == 'last_year':
            # 去年的第一天和最后一天
            first_day = date(today.year - 1, 1, 1)
            last_day = date(today.year, 1, 1) - timedelta(days=1)
            return first_day, last_day
    
    # 根据往前推的天数计算
    if days:
        days = int(days)
        start_date = today - timedelta(days=days)
        return start_date, today
    
    # 默认返回今天
    return today, today 