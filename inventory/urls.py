"""
URL configuration for inventory project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

# 导入视图
from . import views
from . import views_barcode
from . import views_category
from . import views_inventory_check
from . import views_system
from . import views_report

# 导入重构后的视图模块
from .views import member as member_views
from .views import barcode as barcode_views
from .views import core as core_views
from .views import sales as sales_views
from .views import product as product_views
from .views import inventory as inventory_views
from .views import system as system_views  # 导入重构后的系统视图模块

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', core_views.index, name='index'),
    path('products/', product_views.product_list, name='product_list'),
    path('inventory/', inventory_views.inventory_list, name='inventory_list'),
    path('sales/', sales_views.sale_list, name='sale_list'),
    path('products/create/', product_views.product_create, name='product_create'),
    path('products/<int:pk>/edit/', product_views.product_update, name='product_edit'),
    path('products/<int:pk>/', product_views.product_detail, name='product_detail'),
    path('products/<int:pk>/delete/', product_views.product_delete, name='product_delete'),
    
    # 使用新的条码视图
    path('products/barcode/', views_barcode.barcode_product_create, name='barcode_product_create'),
    path('api/barcode/lookup/', barcode_views.barcode_lookup, name='barcode_lookup'),
    path('api/barcode/scan/', barcode_views.barcode_scan, name='barcode_scan'),
    path('api/product/barcode/<str:barcode>/', barcode_views.product_by_barcode, name='product_by_barcode'),
    path('api/product/search/barcode/<str:barcode>/', barcode_views.product_by_barcode, name='product_search_by_barcode'),
    path('api/product/search/', barcode_views.product_search_api, name='product_search_api'),
    
    path('inventory/create/', inventory_views.inventory_transaction_create, name='inventory_create'),
    path('inventory/in/', inventory_views.inventory_in, name='inventory_in'),
    path('inventory/out/', inventory_views.inventory_out, name='inventory_out'),
    path('inventory/adjust/', inventory_views.inventory_adjust, name='inventory_adjust'),
    path('inventory/transactions/', inventory_views.inventory_transaction_list, name='inventory_transaction_list'),
    path('sales/create/', sales_views.sale_create, name='sale_create'),
    path('sales/<int:sale_id>/items/create/', sales_views.sale_item_create, name='sale_item_create'),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(next_page='accounts/login/'), name='logout'),
    
    # 会员管理URL - 使用新的会员视图模块
    path('members/', member_views.member_list, name='member_list'),
    path('members/create/', member_views.member_create, name='member_create'),
    path('members/<int:pk>/edit/', member_views.member_update, name='member_edit'),
    path('members/<int:pk>/', member_views.member_detail, name='member_detail'),
    path('members/<int:pk>/delete/', member_views.member_delete, name='member_delete'),
    path('members/<int:pk>/recharge/', member_views.member_recharge, name='member_recharge'),
    path('members/<int:pk>/recharge-records/', member_views.member_recharge_records, name='member_recharge_records'),
    path('members/<int:pk>/points-adjust/', member_views.member_points_adjust, name='member_points_adjust'),
    path('members/<int:pk>/balance-adjust/', member_views.member_balance_adjust, name='member_balance_adjust'),
    path('members/import/', member_views.member_import, name='member_import'),
    path('members/export/', member_views.member_export, name='member_export'),
    path('members/add-ajax/', member_views.member_add_ajax, name='member_add_ajax'),
    path('members/purchases/', sales_views.member_purchases, name='member_purchases'),
    path('api/member/search/<str:phone>/', member_views.member_search_by_phone, name='member_search_by_phone'),
    
    # 会员等级管理URL - 使用新的会员视图模块
    path('member-levels/', member_views.member_level_list, name='member_level_list'),
    path('member-levels/create/', member_views.member_level_create, name='member_level_create'),
    path('member-levels/<int:pk>/edit/', member_views.member_level_update, name='member_level_edit'),
    path('member-levels/<int:pk>/delete/', member_views.member_level_delete, name='member_level_delete'),
    
    # 分类管理URL
    path('categories/', views_category.category_list, name='category_list'),
    path('categories/create/', views_category.category_create, name='category_create'),
    path('categories/<int:category_id>/edit/', views_category.category_edit, name='category_edit'),
    path('categories/<int:category_id>/delete/', views_category.category_delete, name='category_delete'),
    
    # 库存盘点URL
    path('inventory-checks/', views_inventory_check.inventory_check_list, name='inventory_check_list'),
    path('inventory-checks/create/', views_inventory_check.inventory_check_create, name='inventory_check_create'),
    path('inventory-checks/<int:check_id>/', views_inventory_check.inventory_check_detail, name='inventory_check_detail'),
    path('inventory-checks/<int:check_id>/start/', views_inventory_check.inventory_check_start, name='inventory_check_start'),
    path('inventory-checks/<int:check_id>/complete/', views_inventory_check.inventory_check_complete, name='inventory_check_complete'),
    path('inventory-checks/<int:check_id>/approve/', views_inventory_check.inventory_check_approve, name='inventory_check_approve'),
    path('inventory-checks/<int:check_id>/cancel/', views_inventory_check.inventory_check_cancel, name='inventory_check_cancel'),
    path('inventory-checks/<int:check_id>/items/<int:item_id>/', views_inventory_check.inventory_check_item_update, name='inventory_check_item_update'),
    
    # 报表URL
    path('reports/', core_views.reports_index, name='reports_index'),
    path('reports/index/', views_report.report_index, name='report_index'),
    path('reports/sales-trend/', views_report.sales_trend_report, name='sales_trend_report'),
    path('reports/top-products/', views_report.top_products_report, name='top_products_report'),
    path('reports/inventory-turnover/', views_report.inventory_turnover_report, name='inventory_turnover_report'),
    path('reports/profit/', views_report.profit_report, name='profit_report'),
    path('reports/member-analysis/', views_report.member_analysis_report, name='member_analysis_report'),
    path('reports/birthday-members/', sales_views.birthday_members_report, name='birthday_members_report'),
    path('reports/recharge/', views_report.recharge_report, name='recharge_report'),
    path('reports/operation-logs/', views_report.operation_log_report, name='operation_log_report'),
    
    # 销售明细路径
    path('sales/<int:sale_id>/', sales_views.sale_detail, name='sale_detail'),
    path('sales/<int:sale_id>/complete/', sales_views.sale_complete, name='sale_complete'),
    path('sales/<int:sale_id>/cancel/', sales_views.sale_cancel, name='sale_cancel'),
    path('sales/<int:sale_id>/items/<int:item_id>/delete/', sales_views.sale_delete_item, name='sale_item_delete'),

    # 系统管理 - 新增系统日志相关URL
    path('system/logs/', system_views.log_list, name='log_list'),
    path('system/logs/clear/', system_views.clear_logs, name='clear_logs'),
    path('system/logs/view/<str:file_name>/', system_views.view_log_file, name='view_log_file'),
    path('system/logs/download/<str:file_name>/', system_views.download_log_file, name='download_log_file'),
    path('system/logs/delete/<str:file_name>/', system_views.delete_log_file, name='delete_log_file'),
    path('system/settings/', system_views.system_settings, name='system_settings'),
    path('system/maintenance/', system_views.system_maintenance, name='system_maintenance'),
    
    # 备份相关 - 使用重构后的系统视图
    path('system/backup/', system_views.backup_list, name='backup_list'),
    path('system/backup/create/', system_views.create_backup, name='create_backup'),
    path('system/backup/restore/<str:backup_name>/', system_views.restore_backup, name='restore_backup'),
    path('system/backup/delete/<str:backup_name>/', system_views.delete_backup, name='delete_backup'),
    path('system/backup/download/<str:backup_name>/', system_views.download_backup, name='download_backup'),
    path('system/manual-backup/', system_views.manual_backup, name='manual_backup'),
    
    # 用户管理相关URL
    path('system/users/', system_views.user_list, name='user_list'),
    path('system/users/create/', system_views.user_create, name='user_create'),
    path('system/users/<int:pk>/', system_views.user_detail, name='user_detail'),
    path('system/users/<int:pk>/update/', system_views.user_update, name='user_update'),
    path('system/users/<int:pk>/delete/', system_views.user_delete, name='user_delete'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
