"""
核心视图模块
包含首页和仪表盘等核心功能
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from datetime import timedelta

from inventory.models import (
    Product, Inventory, Sale, SaleItem, 
    Member, InventoryTransaction, OperationLog
)


@login_required
def index(request):
    """系统首页/仪表盘视图"""
    # 获取系统概览统计
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # 商品统计
    total_products = Product.objects.count()
    active_products = total_products
    low_stock_products = Inventory.objects.filter(quantity__lte=10).count()
    out_of_stock_products = Inventory.objects.filter(quantity=0).count()
    
    # 销售统计
    total_sales = Sale.objects.count()
    today_sales = Sale.objects.filter(created_at__date=today).count()
    today_sales_amount = Sale.objects.filter(created_at__date=today).aggregate(
        total=Sum('total_amount')
    )['total'] or 0
    
    yesterday_sales = Sale.objects.filter(created_at__date=yesterday).count()
    yesterday_sales_amount = Sale.objects.filter(created_at__date=yesterday).aggregate(
        total=Sum('total_amount')
    )['total'] or 0
    
    # 会员统计
    total_members = Member.objects.count()
    active_members = total_members
    new_members_month = Member.objects.filter(created_at__gte=month_ago).count()
    
    # 近期销售走势
    sales_trend = []
    for i in range(7):
        date = today - timedelta(days=i)
        daily_sales = Sale.objects.filter(created_at__date=date).aggregate(
            total=Sum('total_amount')
        )['total'] or 0
        sales_trend.append({
            'date': date.strftime('%m-%d'),
            'amount': float(daily_sales)
        })
    sales_trend.reverse()
    
    # 热销商品
    top_products = SaleItem.objects.filter(
        sale__created_at__gte=week_ago
    ).values(
        'product__name'
    ).annotate(
        total_qty=Sum('quantity'),
        total_amount=Sum('subtotal')
    ).order_by('-total_qty')[:5]
    
    # 最近操作日志
    recent_logs = OperationLog.objects.all().order_by('-timestamp')[:10]
    
    # 获取当月生日会员
    current_month = today.month
    birthday_members = Member.objects.filter(
        birthday__isnull=False,  # 确保生日字段不为空
        birthday__month=current_month,
        is_active=True
    ).order_by('birthday__day')[:10]
    
    context = {
        'total_products': total_products,
        'active_products': active_products,
        'low_stock_products': low_stock_products,
        'out_of_stock_products': out_of_stock_products,
        'total_sales': total_sales,
        'today_sales': today_sales,
        'today_sales_amount': today_sales_amount,
        'yesterday_sales': yesterday_sales,
        'yesterday_sales_amount': yesterday_sales_amount,
        'total_members': total_members,
        'active_members': active_members,
        'new_members_month': new_members_month,
        'sales_trend': sales_trend,
        'top_products': top_products,
        'recent_logs': recent_logs,
        'birthday_members': birthday_members,
        'current_month': current_month,
    }
    
    return render(request, 'inventory/index.html', context)


@login_required
def reports_index(request):
    """报表首页视图"""
    return render(request, 'inventory/reports/index.html') 