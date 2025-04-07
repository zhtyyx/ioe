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
from . import views
from . import views_barcode
from . import views_category
from . import views_inventory_check
from . import views_report
from . import views_system

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),
    path('products/', views.product_list, name='product_list'),
    path('inventory/', views.inventory_list, name='inventory_list'),
    path('sales/', views.sale_list, name='sale_list'),
    path('products/create/', views.product_create, name='product_create'),
    path('products/<int:product_id>/edit/', views.product_edit, name='product_edit'),
    path('products/barcode/', views_barcode.barcode_product_create, name='barcode_product_create'),
    path('api/barcode/lookup/', views_barcode.barcode_lookup, name='barcode_lookup'),
    path('inventory/create/', views.inventory_transaction_create, name='inventory_create'),
    path('sales/create/', views.sale_create, name='sale_create'),
    path('sales/<int:sale_id>/items/create/', views.sale_item_create, name='sale_item_create'),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
    path('members/', views.member_list, name='member_list'),
    path('members/create/', views.member_create, name='member_create'),
    path('members/<int:member_id>/edit/', views.member_edit, name='member_edit'),
    path('members/<int:member_id>/details/', views.member_details, name='member_details'),
    path('members/<int:member_id>/recharge/', views.member_recharge, name='member_recharge'),
    path('members/add-ajax/', views.member_add_ajax, name='member_add_ajax'),
    path('members/purchases/', views.member_purchases, name='member_purchases'),
    path('members/<int:member_id>/recharge-records/', views.member_recharge_records, name='member_recharge_records'),
    path('member-levels/', views.member_level_list, name='member_level_list'),
    path('member-levels/create/', views.member_level_create, name='member_level_create'),
    path('member-levels/<int:level_id>/edit/', views.member_level_edit, name='member_level_edit'),
    path('api/product/barcode/<str:barcode>/', views.product_by_barcode, name='product_by_barcode'),
    path('api/member/search/<str:phone>/', views.member_search_by_phone, name='member_search_by_phone'),
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
    path('reports/', views.reports_index, name='reports_index'),
    path('reports/index/', views_report.report_index, name='report_index'),
    path('reports/sales-trend/', views_report.sales_trend_report, name='sales_trend_report'),
    path('reports/top-products/', views_report.top_products_report, name='top_products_report'),
    path('reports/inventory-turnover/', views_report.inventory_turnover_report, name='inventory_turnover_report'),
    path('reports/profit/', views_report.profit_report, name='profit_report'),
    path('reports/member-analysis/', views_report.member_analysis_report, name='member_analysis_report'),
    path('reports/birthday-members/', views.birthday_members_report, name='birthday_members_report'),
    path('reports/recharge/', views_report.recharge_report, name='recharge_report'),
    path('reports/operation-logs/', views_report.operation_log_report, name='operation_log_report'),
    
    # 销售明细路径
    path('sales/<int:sale_id>/', views.sale_detail, name='sale_detail'),

    # 备份相关
    path('system/backup/', views_system.backup_list, name='backup_list'),
    path('system/backup/create/', views_system.create_backup, name='create_backup'),
    path('system/backup/restore/<str:backup_name>/', views_system.restore_backup, name='restore_backup'),
    path('system/backup/delete/<str:backup_name>/', views_system.delete_backup, name='delete_backup'),
    path('system/backup/download/<str:backup_name>/', views_system.download_backup, name='download_backup'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
