"""
报表生成和导出相关视图
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponse, JsonResponse
from django.db.models import Sum, Count, F, Q, Avg
from django.utils import timezone
from django.contrib import messages

import csv
import datetime
import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import io

from inventory.models import (
    Product, Category, Inventory, InventoryTransaction,
    Sale, SaleItem, Member, MemberTransaction, Store
)
from inventory.services import report_service
from inventory.utils.date_utils import get_date_range
from inventory.forms.report_forms import ReportFilterForm, SalesReportForm


@login_required
@permission_required('inventory.view_reports', raise_exception=True)
def sales_report(request):
    """销售报表视图"""
    # 默认显示最近30天的销售数据
    end_date = timezone.now().date()
    start_date = end_date - datetime.timedelta(days=30)
    
    form = SalesReportForm(request.GET or None)
    
    if form.is_valid():
        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date']
        store_id = form.cleaned_data.get('store')
        category_id = form.cleaned_data.get('category')
        
        # 获取销售数据
        sales_data = report_service.get_sales_data(start_date, end_date, store_id, category_id)
        
        # 准备销售趋势数据
        sales_trend = report_service.get_sales_trend(start_date, end_date, store_id)
        
        # 准备按商品分类的销售数据
        category_sales = report_service.get_category_sales(start_date, end_date, store_id)
        
        # 如果请求导出
        if 'export' in request.GET:
            export_format = request.GET.get('export_format', 'excel')
            
            if export_format == 'excel':
                return report_service.export_sales_report_excel(sales_data, start_date, end_date)
            elif export_format == 'csv':
                return report_service.export_sales_report_csv(sales_data, start_date, end_date)
        
        # 渲染正常报表页面
        return render(request, 'inventory/reports/sales_report.html', {
            'form': form,
            'sales_data': sales_data,
            'total_sales': sum(item['total_amount'] for item in sales_data),
            'total_profit': sum(item['profit'] for item in sales_data),
            'sales_trend': sales_trend,
            'category_sales': category_sales,
            'start_date': start_date,
            'end_date': end_date,
        })
    
    # 首次访问或表单无效时
    return render(request, 'inventory/reports/sales_report.html', {
        'form': form,
        'start_date': start_date,
        'end_date': end_date,
    })


@login_required
@permission_required('inventory.view_reports', raise_exception=True)
def inventory_report(request):
    """库存报表视图"""
    form = ReportFilterForm(request.GET or None)
    
    filters = {}
    if form.is_valid():
        category_id = form.cleaned_data.get('category')
        if category_id:
            filters['category_id'] = category_id
        
        store_id = form.cleaned_data.get('store')
        if store_id:
            filters['store_id'] = store_id
    
    # 获取库存数据
    inventory_data = report_service.get_inventory_data(filters)
    
    # 获取库存警告数据
    warning_data = report_service.get_inventory_warnings()
    
    # 获取库存变动趋势
    inventory_trend = report_service.get_inventory_trend()
    
    # 如果请求导出
    if 'export' in request.GET:
        export_format = request.GET.get('export_format', 'excel')
        
        if export_format == 'excel':
            return report_service.export_inventory_report_excel(inventory_data)
        elif export_format == 'csv':
            return report_service.export_inventory_report_csv(inventory_data)
    
    # 渲染正常报表页面
    return render(request, 'inventory/reports/inventory_report.html', {
        'form': form,
        'inventory_data': inventory_data,
        'warning_data': warning_data,
        'inventory_trend': inventory_trend,
        'total_inventory_value': sum(item['inventory_value'] for item in inventory_data),
    })


@login_required
@permission_required('inventory.view_reports', raise_exception=True)
def member_report(request):
    """会员报表视图"""
    form = ReportFilterForm(request.GET or None)
    
    start_date = timezone.now().date() - datetime.timedelta(days=30)
    end_date = timezone.now().date()
    
    if form.is_valid():
        start_date = form.cleaned_data.get('start_date') or start_date
        end_date = form.cleaned_data.get('end_date') or end_date
    
    # 获取会员数据
    member_data = report_service.get_member_data(start_date, end_date)
    
    # 获取会员消费趋势
    member_trend = report_service.get_member_trend(start_date, end_date)
    
    # 获取会员等级分布
    level_distribution = report_service.get_member_level_distribution()
    
    # 如果请求导出
    if 'export' in request.GET:
        export_format = request.GET.get('export_format', 'excel')
        
        if export_format == 'excel':
            return report_service.export_member_report_excel(member_data, start_date, end_date)
        elif export_format == 'csv':
            return report_service.export_member_report_csv(member_data, start_date, end_date)
    
    # 渲染正常报表页面
    return render(request, 'inventory/reports/member_report.html', {
        'form': form,
        'member_data': member_data,
        'member_trend': member_trend,
        'level_distribution': level_distribution,
        'start_date': start_date,
        'end_date': end_date,
        'total_members': len(member_data),
        'total_consumption': sum(member['total_consumption'] for member in member_data),
    })


@login_required
@permission_required('inventory.view_reports', raise_exception=True)
def product_performance_report(request):
    """商品绩效报表视图"""
    form = ReportFilterForm(request.GET or None)
    
    start_date = timezone.now().date() - datetime.timedelta(days=30)
    end_date = timezone.now().date()
    filters = {}
    
    if form.is_valid():
        start_date = form.cleaned_data.get('start_date') or start_date
        end_date = form.cleaned_data.get('end_date') or end_date
        
        category_id = form.cleaned_data.get('category')
        if category_id:
            filters['category_id'] = category_id
        
        store_id = form.cleaned_data.get('store')
        if store_id:
            filters['store_id'] = store_id
    
    # 获取商品销售绩效数据
    performance_data = report_service.get_product_performance(start_date, end_date, filters)
    
    # 获取热销商品数据
    hot_products = report_service.get_hot_products(start_date, end_date, filters)
    
    # 获取滞销商品数据
    slow_moving = report_service.get_slow_moving_products(filters)
    
    # 如果请求导出
    if 'export' in request.GET:
        export_format = request.GET.get('export_format', 'excel')
        
        if export_format == 'excel':
            return report_service.export_product_performance_excel(performance_data, start_date, end_date)
        elif export_format == 'csv':
            return report_service.export_product_performance_csv(performance_data, start_date, end_date)
    
    # 渲染正常报表页面
    return render(request, 'inventory/reports/product_performance.html', {
        'form': form,
        'performance_data': performance_data,
        'hot_products': hot_products,
        'slow_moving': slow_moving,
        'start_date': start_date,
        'end_date': end_date,
    })


@login_required
@permission_required('inventory.view_reports', raise_exception=True)
def daily_summary_report(request):
    """每日汇总报表视图"""
    # 默认显示最近7天
    end_date = timezone.now().date()
    start_date = end_date - datetime.timedelta(days=6)
    
    form = ReportFilterForm(request.GET or None)
    
    if form.is_valid():
        start_date = form.cleaned_data.get('start_date') or start_date
        end_date = form.cleaned_data.get('end_date') or end_date
        store_id = form.cleaned_data.get('store')
    else:
        store_id = None
    
    # 获取日报数据
    daily_data = report_service.get_daily_summary(start_date, end_date, store_id)
    
    # 如果请求导出
    if 'export' in request.GET:
        export_format = request.GET.get('export_format', 'excel')
        
        if export_format == 'excel':
            return report_service.export_daily_summary_excel(daily_data, start_date, end_date)
        elif export_format == 'csv':
            return report_service.export_daily_summary_csv(daily_data, start_date, end_date)
    
    # 渲染正常报表页面
    return render(request, 'inventory/reports/daily_summary.html', {
        'form': form,
        'daily_data': daily_data,
        'start_date': start_date,
        'end_date': end_date,
        'total_sales': sum(day['total_sales'] for day in daily_data),
        'total_profit': sum(day['total_profit'] for day in daily_data),
        'total_transactions': sum(day['transaction_count'] for day in daily_data),
    })


@login_required
@permission_required('inventory.view_reports', raise_exception=True)
def custom_report(request):
    """自定义报表视图"""
    # 获取所有可用字段
    available_fields = report_service.get_available_report_fields()
    
    if request.method == 'POST':
        # 处理自定义报表生成请求
        report_type = request.POST.get('report_type')
        selected_fields = request.POST.getlist('selected_fields')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        filters = {}
        
        # 处理过滤条件
        for key, value in request.POST.items():
            if key.startswith('filter_') and value:
                filter_field = key.replace('filter_', '')
                filters[filter_field] = value
        
        if not selected_fields:
            messages.error(request, "请至少选择一个字段")
            return redirect('custom_report')
        
        # 生成报表数据
        try:
            report_data = report_service.generate_custom_report(
                report_type, 
                selected_fields, 
                start_date, 
                end_date, 
                filters
            )
            
            # 如果请求导出
            if 'export' in request.POST:
                export_format = request.POST.get('export_format', 'excel')
                
                if export_format == 'excel':
                    return report_service.export_custom_report_excel(
                        report_data, 
                        selected_fields, 
                        report_type
                    )
                elif export_format == 'csv':
                    return report_service.export_custom_report_csv(
                        report_data, 
                        selected_fields, 
                        report_type
                    )
            
            # 渲染报表结果页面
            return render(request, 'inventory/reports/custom_report_result.html', {
                'report_data': report_data,
                'selected_fields': selected_fields,
                'report_type': report_type,
                'start_date': start_date,
                'end_date': end_date,
                'filters': filters,
            })
            
        except Exception as e:
            messages.error(request, f"生成报表时发生错误: {str(e)}")
            return redirect('custom_report')
    
    # GET请求显示报表配置页面
    return render(request, 'inventory/reports/custom_report.html', {
        'available_fields': available_fields,
    })


@login_required
@permission_required('inventory.view_reports', raise_exception=True)
def profit_analysis(request):
    """利润分析报表视图"""
    form = ReportFilterForm(request.GET or None)
    
    start_date = timezone.now().date() - datetime.timedelta(days=30)
    end_date = timezone.now().date()
    filters = {}
    
    if form.is_valid():
        start_date = form.cleaned_data.get('start_date') or start_date
        end_date = form.cleaned_data.get('end_date') or end_date
        
        category_id = form.cleaned_data.get('category')
        if category_id:
            filters['category_id'] = category_id
        
        store_id = form.cleaned_data.get('store')
        if store_id:
            filters['store_id'] = store_id
    
    # 获取利润分析数据
    profit_data = report_service.get_profit_analysis(start_date, end_date, filters)
    
    # 获取利润趋势数据
    profit_trend = report_service.get_profit_trend(start_date, end_date, filters)
    
    # 获取按分类的利润分布
    category_profit = report_service.get_category_profit(start_date, end_date, filters)
    
    # 如果请求导出
    if 'export' in request.GET:
        export_format = request.GET.get('export_format', 'excel')
        
        if export_format == 'excel':
            return report_service.export_profit_analysis_excel(profit_data, start_date, end_date)
        elif export_format == 'csv':
            return report_service.export_profit_analysis_csv(profit_data, start_date, end_date)
    
    # 渲染正常报表页面
    return render(request, 'inventory/reports/profit_analysis.html', {
        'form': form,
        'profit_data': profit_data,
        'profit_trend': profit_trend,
        'category_profit': category_profit,
        'start_date': start_date,
        'end_date': end_date,
        'total_revenue': sum(item['total_revenue'] for item in profit_data),
        'total_cost': sum(item['total_cost'] for item in profit_data),
        'total_profit': sum(item['total_profit'] for item in profit_data),
        'average_margin': sum(item['profit_margin'] for item in profit_data) / len(profit_data) if profit_data else 0,
    })


@login_required
@permission_required('inventory.view_reports', raise_exception=True)
def inventory_batch_report(request):
    """库存批次报表视图"""
    form = ReportFilterForm(request.GET or None)
    
    filters = {}
    if form.is_valid():
        category_id = form.cleaned_data.get('category')
        if category_id:
            filters['product__category_id'] = category_id
        
        store_id = form.cleaned_data.get('store')
        if store_id:
            filters['store_id'] = store_id
        
        # 添加过期筛选
        expiry_filter = request.GET.get('expiry_filter')
        if expiry_filter == 'expired':
            filters['expiry_date__lt'] = timezone.now().date()
        elif expiry_filter == 'expiring_soon':
            filters['expiry_date__gte'] = timezone.now().date()
            filters['expiry_date__lte'] = timezone.now().date() + datetime.timedelta(days=30)
    
    # 获取批次数据
    batch_data = report_service.get_batch_report(filters)
    
    # 如果请求导出
    if 'export' in request.GET:
        export_format = request.GET.get('export_format', 'excel')
        
        if export_format == 'excel':
            return report_service.export_batch_report_excel(batch_data)
        elif export_format == 'csv':
            return report_service.export_batch_report_csv(batch_data)
    
    # 渲染正常报表页面
    return render(request, 'inventory/reports/inventory_batch_report.html', {
        'form': form,
        'batch_data': batch_data,
        'total_batches': len(batch_data),
        'total_quantity': sum(batch['remaining_quantity'] for batch in batch_data),
        'expired_count': sum(1 for batch in batch_data if batch['expiry_date'] and batch['expiry_date'] < timezone.now().date()),
    }) 