"""
Report generation and data analysis services.
"""
from datetime import datetime, timedelta
from decimal import Decimal
from django.db.models import Sum, Count, F, Q, Avg, ExpressionWrapper, FloatField, DecimalField
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
from django.utils import timezone

from inventory.models import Product, Inventory, Sale, SaleItem, InventoryTransaction, Member, MemberLevel, RechargeRecord, OperationLog
from inventory.utils.date_utils import get_period_boundaries

class ReportService:
    """Service for generating reports and analyzing data."""
    
    @staticmethod
    def get_sales_by_period(start_date=None, end_date=None, period='day'):
        """
        Get sales data grouped by the specified period.
        
        Args:
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering
            period: Grouping period - 'day', 'week', or 'month'
            
        Returns:
            QuerySet: Sales data grouped by period
        """
        if not start_date:
            start_date = timezone.now() - timedelta(days=30)
        if not end_date:
            end_date = timezone.now()
            
        # Truncate function based on period
        if period == 'day':
            trunc_func = TruncDay('created_at')
        elif period == 'week':
            trunc_func = TruncWeek('created_at')
        elif period == 'month':
            trunc_func = TruncMonth('created_at')
        else:
            trunc_func = TruncDay('created_at')
            
        # Query sales data
        sales_data = Sale.objects.filter(
            created_at__range=(start_date, end_date)
        ).annotate(
            period=trunc_func
        ).values(
            'period'
        ).annotate(
            total_sales=Sum('final_amount'),
            total_cost=Sum(F('items__quantity') * F('items__product__cost')),
            order_count=Count('id', distinct=True),
            item_count=Count('items')
        ).order_by('period')
        
        # Calculate profit
        for data in sales_data:
            data['profit'] = data['total_sales'] - (data['total_cost'] or 0)
            if data['total_cost'] and data['total_cost'] > 0:
                data['profit_margin'] = (data['profit'] / data['total_cost']) * 100
            else:
                data['profit_margin'] = 0
                
        return sales_data
    
    @staticmethod
    def get_top_selling_products(start_date=None, end_date=None, limit=10):
        """
        Get top selling products for the given period.
        
        Args:
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering
            limit: Number of products to return
            
        Returns:
            QuerySet: Top selling products
        """
        if not start_date:
            start_date = timezone.now() - timedelta(days=30)
        if not end_date:
            end_date = timezone.now()
            
        return SaleItem.objects.filter(
            sale__created_at__range=(start_date, end_date)
        ).values(
            'product__id',
            'product__name',
            'product__barcode',
            'product__category__name'
        ).annotate(
            total_quantity=Sum('quantity'),
            total_sales=Sum('subtotal'),
            total_cost=Sum(F('quantity') * F('product__cost'))
        ).annotate(
            profit=F('total_sales') - F('total_cost'),
            profit_margin=ExpressionWrapper(
                F('profit') * 100 / F('total_cost'),
                output_field=DecimalField()
            )
        ).order_by('-total_quantity')[:limit]
    
    @staticmethod
    def get_inventory_turnover_rate(start_date=None, end_date=None, category=None):
        """
        Calculate inventory turnover rate for products.
        
        Args:
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering
            category: Optional category for filtering products
            
        Returns:
            list: Inventory turnover rates for products
        """
        if not start_date:
            start_date = timezone.now() - timedelta(days=30)
        if not end_date:
            end_date = timezone.now()
        
        # Time period in days
        days = (end_date - start_date).days or 1  # Avoid division by zero
        
        # Get current inventory levels
        inventory_query = Inventory.objects.select_related('product').all()
        
        # Filter by category if specified
        if category:
            inventory_query = inventory_query.filter(product__category=category)
            
        inventory_data = inventory_query
        
        # Get sales within period
        sales_query = SaleItem.objects.filter(
            sale__created_at__range=(start_date, end_date)
        )
        
        # Apply category filter if needed
        if category:
            sales_query = sales_query.filter(product__category=category)
            
        sales_data = sales_query.values('product').annotate(
            total_quantity=Sum('quantity')
        )
        
        # Create a map for quick lookup
        sales_map = {item['product']: item['total_quantity'] for item in sales_data}
        
        # Calculate turnover for each product
        product_turnover = []
        for inv in inventory_data:
            sold_quantity = sales_map.get(inv.product.id, 0)
            current_quantity = inv.quantity
            
            # Calculate average inventory (simple approximation)
            # For better accuracy, we would need historical inventory records
            average_inventory = (current_quantity + sold_quantity) / 2
            
            # Calculate turnover rate (annualized)
            if average_inventory > 0:
                turnover_rate = (sold_quantity / average_inventory) * (365 / days)
                turnover_days = 365 / turnover_rate if turnover_rate > 0 else float('inf')
            else:
                turnover_rate = 0
                turnover_days = float('inf')
                
            product_turnover.append({
                'product_id': inv.product.id,
                'product_name': inv.product.name,
                'product_code': inv.product.barcode,
                'category': inv.product.category.name,
                'current_stock': current_quantity,
                'sold_quantity': sold_quantity,
                'avg_stock': average_inventory,
                'turnover_rate': turnover_rate,
                'turnover_days': turnover_days
            })
            
        # Sort by turnover rate (descending)
        product_turnover.sort(key=lambda x: x['turnover_rate'], reverse=True)
            
        return product_turnover
    
    @staticmethod
    def get_profit_report(start_date=None, end_date=None):
        """
        Generate a profit report for the given period.
        
        Args:
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering
            
        Returns:
            dict: Profit report data
        """
        if not start_date:
            start_date = timezone.now() - timedelta(days=30)
        if not end_date:
            end_date = timezone.now()
            
        # Sales data
        sales_data = Sale.objects.filter(
            created_at__range=(start_date, end_date)
        )
        
        # Total sales
        total_sales = sales_data.aggregate(
            total_amount=Sum('total_amount'),
            final_amount=Sum('final_amount'),
            discount_amount=Sum('discount_amount')
        )
        
        # Calculate costs
        sale_items = SaleItem.objects.filter(sale__in=sales_data)
        total_cost = sale_items.aggregate(
            cost=Sum(F('quantity') * F('product__cost'))
        )['cost'] or 0
        
        # Calculate profit
        gross_profit = (total_sales['final_amount'] or 0) - total_cost
        
        # Calculate by category
        category_data = sale_items.values(
            'product__category__name'
        ).annotate(
            sales=Sum('subtotal'),
            cost=Sum(F('quantity') * F('product__cost')),
            quantity=Sum('quantity')
        ).annotate(
            profit=F('sales') - F('cost'),
            profit_margin=ExpressionWrapper(
                F('profit') * 100 / F('cost'),
                output_field=DecimalField()
            )
        ).order_by('-profit')
        
        # Profit margin
        profit_margin = 0
        if total_cost > 0:
            profit_margin = (gross_profit / total_cost) * 100
            
        return {
            'start_date': start_date,
            'end_date': end_date,
            'total_sales': total_sales['final_amount'] or 0,
            'total_cost': total_cost,
            'gross_profit': gross_profit,
            'profit_margin': profit_margin,
            'discount_amount': total_sales['discount_amount'] or 0,
            'order_count': sales_data.count(),
            'item_count': sale_items.count(),
            'category_data': list(category_data)
        }

    @staticmethod
    def get_member_analysis(start_date=None, end_date=None):
        """
        获取会员分析数据
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            dict: 会员分析数据
        """
        if not start_date:
            start_date = timezone.now().date() - timedelta(days=30)
        if not end_date:
            end_date = timezone.now().date()
            
        # 调整日期范围，包含整天
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())
        
        # 获取会员等级分布
        level_distribution = (
            Member.objects
            .values('level__name')
            .annotate(count=Count('id'))
            .order_by('level__points_threshold')
        )
        
        # 会员消费排行
        top_members = (
            Member.objects
            .filter(sale__created_at__range=(start_datetime, end_datetime))
            .annotate(
                period_spend=Sum('sale__final_amount'),
                period_purchase_count=Count('sale')
            )
            .filter(period_spend__gt=0)
            .order_by('-period_spend')[:10]
        )
        
        # 获取新增会员数据
        new_members = (
            Member.objects
            .filter(created_at__range=(start_datetime, end_datetime))
            .count()
        )
        
        # 获取活跃会员数据（在指定时间段内有消费的会员）
        active_members = (
            Member.objects
            .filter(sale__created_at__range=(start_datetime, end_datetime))
            .distinct()
            .count()
        )
        
        # 会员总数
        total_members = Member.objects.count()
        
        # 会员消费统计
        member_sales = (
            Sale.objects
            .filter(created_at__range=(start_datetime, end_datetime))
            .filter(member__isnull=False)
            .aggregate(
                total_amount=Sum('final_amount'),
                total_count=Count('id')
            )
        )
        
        # 非会员消费统计
        non_member_sales = (
            Sale.objects
            .filter(created_at__range=(start_datetime, end_datetime))
            .filter(member__isnull=True)
            .aggregate(
                total_amount=Sum('final_amount'),
                total_count=Count('id')
            )
        )
        
        # 会员平均客单价
        member_avg_order = member_sales['total_amount'] / member_sales['total_count'] if member_sales['total_count'] else 0
        
        # 非会员平均客单价
        non_member_avg_order = non_member_sales['total_amount'] / non_member_sales['total_count'] if non_member_sales['total_count'] else 0
        
        # 计算会员活跃率
        activity_rate = (active_members / total_members * 100) if total_members > 0 else 0
        
        return {
            'level_distribution': level_distribution,
            'top_members': top_members,
            'new_members': new_members,
            'active_members': active_members,
            'total_members': total_members,
            'activity_rate': activity_rate,
            'member_sales': member_sales,
            'non_member_sales': non_member_sales,
            'member_avg_order': member_avg_order,
            'non_member_avg_order': non_member_avg_order,
        }

    @staticmethod
    def get_recharge_report(start_date=None, end_date=None):
        """
        Generate a recharge report for the given period.
        
        Args:
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering
            
        Returns:
            dict: Recharge report data
        """
        if not start_date:
            start_date = timezone.now() - timedelta(days=30)
        if not end_date:
            end_date = timezone.now()
            
        # 总体统计
        summary = {
            'total_recharge_amount': RechargeRecord.objects.filter(
                created_at__range=(start_date, end_date)
            ).aggregate(total=Sum('amount'))['total'] or 0,
            
            'total_recharge_count': RechargeRecord.objects.filter(
                created_at__range=(start_date, end_date)
            ).count(),
            
            'total_actual_amount': RechargeRecord.objects.filter(
                created_at__range=(start_date, end_date)
            ).aggregate(total=Sum('actual_amount'))['total'] or 0,
            
            'avg_recharge_amount': RechargeRecord.objects.filter(
                created_at__range=(start_date, end_date)
            ).aggregate(avg=Avg('amount'))['avg'] or 0,
            
            'recharged_member_count': RechargeRecord.objects.filter(
                created_at__range=(start_date, end_date)
            ).values('member').distinct().count()
        }
        
        # 按日期统计充值
        daily_recharge = RechargeRecord.objects.filter(
            created_at__range=(start_date, end_date)
        ).annotate(
            day=TruncDay('created_at')
        ).values('day').annotate(
            total_amount=Sum('amount'),
            actual_amount=Sum('actual_amount'),
            count=Count('id'),
            member_count=Count('member', distinct=True)
        ).order_by('day')
        
        # 按支付方式统计
        payment_stats = RechargeRecord.objects.filter(
            created_at__range=(start_date, end_date)
        ).values('payment_method').annotate(
            count=Count('id'),
            total_amount=Sum('amount'),
            actual_amount=Sum('actual_amount')
        ).order_by('-count')
        
        # 会员充值排行
        top_members = Member.objects.filter(
            recharge_records__created_at__range=(start_date, end_date)
        ).annotate(
            total_recharge=Sum('recharge_records__amount', 
                              filter=Q(recharge_records__created_at__range=(start_date, end_date))),
            recharge_count=Count('recharge_records', 
                                filter=Q(recharge_records__created_at__range=(start_date, end_date)))
        ).order_by('-total_recharge')[:10]
        
        return {
            'summary': summary,
            'daily_recharge': daily_recharge,
            'payment_stats': payment_stats,
            'top_members': top_members
        }
    
    @staticmethod
    def get_operation_logs(start_date=None, end_date=None):
        """
        Get operation logs for the given period.
        
        Args:
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering
            
        Returns:
            QuerySet: Operation logs
        """
        if not start_date:
            start_date = timezone.now() - timedelta(days=7)
        if not end_date:
            end_date = timezone.now()
        
        # 结束日期+1天以包含当天的记录
        end_date_inclusive = end_date + timedelta(days=1)
        
        # 获取日志记录
        logs = OperationLog.objects.filter(
            timestamp__range=(start_date, end_date_inclusive)
        ).select_related('operator', 'related_content_type').order_by('-timestamp')
        
        # 按操作类型统计
        operation_type_stats = OperationLog.objects.filter(
            timestamp__range=(start_date, end_date_inclusive)
        ).values('operation_type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # 按操作员统计
        operator_stats = OperationLog.objects.filter(
            timestamp__range=(start_date, end_date_inclusive)
        ).values('operator__username').annotate(
            count=Count('id')
        ).order_by('-count')
        
        return {
            'logs': logs,
            'operation_type_stats': operation_type_stats,
            'operator_stats': operator_stats
        } 