from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from inventory.models import (
    Category,
    Inventory,
    Product,
    Sale,
    SaleItem,
)


class SaleStatusTest(TestCase):
    """覆盖销售单状态字段救活后的取消 / 删商品流程（此前因引用不存在的字段会 AttributeError）。"""

    def setUp(self):
        self.user = User.objects.create_user(username='cashier', password='secret')
        self.client = Client()
        self.client.login(username='cashier', password='secret')

        self.category = Category.objects.create(name='测试分类')
        self.product = Product.objects.create(
            barcode='status-test-product',
            name='状态测试商品',
            category=self.category,
            price=Decimal('10.00'),
            cost=Decimal('5.00'),
        )
        self.inventory = Inventory.objects.create(
            product=self.product,
            quantity=8,  # 已卖出 2 件
            warning_level=1,
        )

    def _make_sale(self, status='DRAFT'):
        sale = Sale.objects.create(
            total_amount=Decimal('20.00'),
            discount_amount=Decimal('0.00'),
            final_amount=Decimal('20.00'),
            payment_method='cash',
            operator=self.user,
            status=status,
        )
        SaleItem.objects.create(
            sale=sale,
            product=self.product,
            quantity=2,
            price=Decimal('10.00'),
            actual_price=Decimal('10.00'),
            subtotal=Decimal('20.00'),
        )
        return sale

    def test_cancel_draft_sale_restores_inventory_and_sets_status(self):
        sale = self._make_sale(status='DRAFT')
        self.inventory.refresh_from_db()
        before = self.inventory.quantity  # 创建明细已自动扣减库存

        response = self.client.post(
            reverse('sale_cancel', args=[sale.id]), {'reason': '顾客取消'}
        )

        self.assertRedirects(response, reverse('sale_list'))
        sale.refresh_from_db()
        self.assertEqual(sale.status, 'CANCELLED')
        self.assertIn('取消原因: 顾客取消', sale.remark)

        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, before + 2)  # 取消后库存已恢复

    def test_cannot_cancel_completed_sale(self):
        sale = self._make_sale(status='COMPLETED')
        self.inventory.refresh_from_db()
        before = self.inventory.quantity

        response = self.client.get(reverse('sale_cancel', args=[sale.id]))

        self.assertRedirects(response, reverse('sale_detail', args=[sale.id]))
        sale.refresh_from_db()
        self.assertEqual(sale.status, 'COMPLETED')
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, before)  # 库存未变动

    def test_delete_item_persists_recalculated_total(self):
        sale = self._make_sale(status='DRAFT')
        extra = SaleItem.objects.create(
            sale=sale,
            product=self.product,
            quantity=1,
            price=Decimal('10.00'),
            actual_price=Decimal('10.00'),
            subtotal=Decimal('10.00'),
        )

        response = self.client.post(
            reverse('sale_item_delete', args=[sale.id, extra.id])
        )

        self.assertRedirects(response, reverse('sale_item_create', args=[sale.id]))
        sale.refresh_from_db()
        self.assertEqual(sale.total_amount, Decimal('20.00'))  # 删除后总额已落库
