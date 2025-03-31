"""
Date and time utility functions.
"""
from datetime import datetime, time, timedelta


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