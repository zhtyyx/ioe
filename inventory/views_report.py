"""
Report views.
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta

from .forms import DateRangeForm, TopProductsForm, InventoryTurnoverForm
from .services.report_service import ReportService
from .services.export_service import ExportService
from .utils.logging import log_view_access
from .permissions.decorators import permission_required

@login_required
@log_view_access('OTHER')
@permission_required('view_reports')
def report_index(request):
    """
    Report index view. Redirects to new reports_index.
    """
    return redirect('reports_index')

@login_required
@log_view_access('OTHER')
@permission_required('view_reports')
def sales_trend_report(request):
    """
    Sales trend report view.
    """
    if request.method == 'POST':
        form = DateRangeForm(request.POST)
        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            period = form.cleaned_data['period']
            
            # Get sales trend data
            sales_data = ReportService.get_sales_by_period(
                start_date=start_date,
                end_date=end_date,
                period=period
            )
            
            return render(request, 'inventory/reports/sales_trend.html', {
                'form': form,
                'sales_data': sales_data,
                'start_date': start_date,
                'end_date': end_date,
                'period': period
            })
    else:
        form = DateRangeForm()
        
        # Get default data for last 30 days
        start_date = timezone.now().date() - timedelta(days=30)
        end_date = timezone.now().date()
        
        # Get sales trend data
        sales_data = ReportService.get_sales_by_period(
            start_date=start_date,
            end_date=end_date,
            period='day'
        )
        
        return render(request, 'inventory/reports/sales_trend.html', {
            'form': form,
            'sales_data': sales_data,
            'start_date': start_date,
            'end_date': end_date,
            'period': 'day'
        })

@login_required
@log_view_access('OTHER')
@permission_required('view_reports')
def top_products_report(request):
    """
    Top selling products report view.
    """
    if request.method == 'POST':
        form = TopProductsForm(request.POST)
        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            limit = form.cleaned_data['limit']
            
            # Get top products data
            top_products = ReportService.get_top_selling_products(
                start_date=start_date,
                end_date=end_date,
                limit=limit
            )
            
            return render(request, 'inventory/reports/top_products.html', {
                'form': form,
                'top_products': top_products,
                'start_date': start_date,
                'end_date': end_date
            })
    else:
        form = TopProductsForm()
        
        # Get default data for last 30 days
        start_date = timezone.now().date() - timedelta(days=30)
        end_date = timezone.now().date()
        limit = 10  # 默认显示10个
        
        # Get top products data
        top_products = ReportService.get_top_selling_products(
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        
        return render(request, 'inventory/reports/top_products.html', {
            'form': form,
            'top_products': top_products,
            'start_date': start_date,
            'end_date': end_date
        })

@login_required
@log_view_access('OTHER')
@permission_required('view_reports')
def inventory_turnover_report(request):
    """
    Inventory turnover report view.
    """
    if request.method == 'POST':
        form = InventoryTurnoverForm(request.POST)
        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            category = form.cleaned_data['category']
            
            # Get inventory turnover data
            inventory_data = ReportService.get_inventory_turnover_rate(
                start_date=start_date,
                end_date=end_date,
                category=category
            )
            
            return render(request, 'inventory/reports/inventory_turnover.html', {
                'form': form,
                'inventory_data': inventory_data,
                'start_date': start_date,
                'end_date': end_date
            })
    else:
        form = InventoryTurnoverForm()
        
        # Get default data for last 30 days
        start_date = timezone.now().date() - timedelta(days=30)
        end_date = timezone.now().date()
        
        # Get inventory turnover data
        inventory_data = ReportService.get_inventory_turnover_rate(
            start_date=start_date,
            end_date=end_date
        )
        
        return render(request, 'inventory/reports/inventory_turnover.html', {
            'form': form,
            'inventory_data': inventory_data,
            'start_date': start_date,
            'end_date': end_date
        })

@login_required
@log_view_access('OTHER')
@permission_required('view_reports')
def profit_report(request):
    """
    Profit report view.
    """
    if request.method == 'POST':
        form = DateRangeForm(request.POST)
        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            
            # Get profit data
            profit_data = ReportService.get_profit_report(
                start_date=start_date,
                end_date=end_date
            )
            
            return render(request, 'inventory/reports/profit.html', {
                'form': form,
                'profit_data': profit_data,
                'start_date': start_date,
                'end_date': end_date
            })
    else:
        form = DateRangeForm()
        
        # Get default data for last 30 days
        start_date = timezone.now().date() - timedelta(days=30)
        end_date = timezone.now().date()
        
        # Get profit data
        profit_data = ReportService.get_profit_report(
            start_date=start_date,
            end_date=end_date
        )
        
        return render(request, 'inventory/reports/profit.html', {
            'form': form,
            'profit_data': profit_data,
            'start_date': start_date,
            'end_date': end_date
        })

@login_required
@log_view_access('OTHER')
@permission_required('view_reports')
def member_analysis_report(request):
    """
    Member analysis report view.
    """
    if request.method == 'POST':
        form = DateRangeForm(request.POST)
        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            
            # 处理导出Excel请求
            if 'export_excel' in request.POST:
                member_data = ReportService.get_member_analysis(
                    start_date=start_date,
                    end_date=end_date
                )
                return ExportService.export_member_analysis(member_data, start_date, end_date)
            
            # Get member analysis data
            member_data = ReportService.get_member_analysis(
                start_date=start_date,
                end_date=end_date
            )
            
            return render(request, 'inventory/reports/member_analysis.html', {
                'form': form,
                'member_data': member_data,
                'start_date': start_date,
                'end_date': end_date
            })
    else:
        form = DateRangeForm()
        
        # Get default data for last 30 days
        start_date = timezone.now().date() - timedelta(days=30)
        end_date = timezone.now().date()
        
        # Get member analysis data
        member_data = ReportService.get_member_analysis(
            start_date=start_date,
            end_date=end_date
        )
        
        return render(request, 'inventory/reports/member_analysis.html', {
            'form': form,
            'member_data': member_data,
            'start_date': start_date,
            'end_date': end_date
        })

@login_required
@log_view_access('OTHER')
@permission_required('view_reports')
def recharge_report(request):
    """
    Member recharge report view.
    """
    if request.method == 'POST':
        form = DateRangeForm(request.POST)
        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            
            # 获取会员充值数据
            recharge_data = ReportService.get_recharge_report(
                start_date=start_date,
                end_date=end_date
            )
            
            return render(request, 'inventory/reports/recharge_report.html', {
                'form': form,
                'recharge_data': recharge_data,
                'start_date': start_date,
                'end_date': end_date
            })
    else:
        form = DateRangeForm()
        
        # 默认显示最近30天的数据
        start_date = timezone.now().date() - timedelta(days=30)
        end_date = timezone.now().date()
        
        # 获取会员充值数据
        recharge_data = ReportService.get_recharge_report(
            start_date=start_date,
            end_date=end_date
        )
        
        return render(request, 'inventory/reports/recharge_report.html', {
            'form': form,
            'recharge_data': recharge_data,
            'start_date': start_date,
            'end_date': end_date
        })

@login_required
@log_view_access('OTHER')
@permission_required('view_reports')
def operation_log_report(request):
    """
    Operation log report view.
    """
    if request.method == 'POST':
        form = DateRangeForm(request.POST)
        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
            
            # 获取操作日志数据
            log_data = ReportService.get_operation_logs(
                start_date=start_date,
                end_date=end_date
            )
            
            return render(request, 'inventory/reports/operation_log.html', {
                'form': form,
                'log_data': log_data,
                'start_date': start_date,
                'end_date': end_date
            })
    else:
        form = DateRangeForm()
        
        # 默认显示最近7天的日志
        start_date = timezone.now().date() - timedelta(days=7)
        end_date = timezone.now().date()
        
        # 获取操作日志数据
        log_data = ReportService.get_operation_logs(
            start_date=start_date,
            end_date=end_date
        )
        
        return render(request, 'inventory/reports/operation_log.html', {
            'form': form,
            'log_data': log_data,
            'start_date': start_date,
            'end_date': end_date
        }) 