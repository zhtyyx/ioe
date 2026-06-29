from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from inventory.models import (
    Category,
    Inventory,
    Member,
    MemberLevel,
    MemberTransaction,
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

    def test_cannot_cancel_cancelled_sale_twice(self):
        sale = self._make_sale(status='DRAFT')

        first_response = self.client.post(
            reverse('sale_cancel', args=[sale.id]), {'reason': '顾客取消'}
        )
        self.assertRedirects(first_response, reverse('sale_list'))
        self.inventory.refresh_from_db()
        restored_quantity = self.inventory.quantity

        second_response = self.client.post(
            reverse('sale_cancel', args=[sale.id]), {'reason': '重复提交'}
        )

        self.assertRedirects(second_response, reverse('sale_detail', args=[sale.id]))
        sale.refresh_from_db()
        self.assertEqual(sale.status, 'CANCELLED')
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, restored_quantity)

    def test_cannot_add_item_to_completed_sale(self):
        sale = self._make_sale(status='COMPLETED')
        self.inventory.refresh_from_db()
        before = self.inventory.quantity

        response = self.client.post(
            reverse('sale_item_create', args=[sale.id]),
            {
                'product': self.product.id,
                'quantity': '1',
                'price': '10.00',
                'actual_price': '10.00',
            },
        )

        self.assertRedirects(response, reverse('sale_detail', args=[sale.id]))
        self.assertEqual(sale.items.count(), 1)
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, before)

    def test_cannot_delete_item_from_cancelled_sale(self):
        sale = self._make_sale(status='DRAFT')
        item = sale.items.get()
        self.client.post(reverse('sale_cancel', args=[sale.id]), {'reason': '顾客取消'})
        self.inventory.refresh_from_db()
        restored_quantity = self.inventory.quantity

        response = self.client.post(reverse('sale_item_delete', args=[sale.id, item.id]))

        self.assertRedirects(response, reverse('sale_detail', args=[sale.id]))
        self.assertTrue(SaleItem.objects.filter(pk=item.pk).exists())
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, restored_quantity)

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

    def test_sale_complete_page_renders_for_draft_sale(self):
        sale = self._make_sale(status='DRAFT')

        response = self.client.get(reverse('sale_complete', args=[sale.id]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventory/sale_complete.html')

    def test_sale_complete_insufficient_balance_does_not_credit_member(self):
        level = MemberLevel.objects.create(
            name='无折扣会员',
            discount=Decimal('1.00'),
            points_threshold=0,
            color='primary',
        )
        member = Member.objects.create(
            name='余额不足会员',
            phone='13900000001',
            level=level,
            balance=Decimal('5.00'),
        )
        sale = self._make_sale(status='DRAFT')
        sale.member = member
        sale.save()

        response = self.client.post(
            reverse('sale_complete', args=[sale.id]),
            {
                'payment_method': 'balance',
                'remark': '余额支付',
            },
        )

        self.assertRedirects(response, reverse('sale_complete', args=[sale.id]))
        sale.refresh_from_db()
        self.assertEqual(sale.status, 'DRAFT')
        self.assertEqual(sale.balance_paid, Decimal('0.00'))
        member.refresh_from_db()
        self.assertEqual(member.balance, Decimal('5.00'))
        self.assertEqual(member.points, 0)
        self.assertEqual(member.purchase_count, 0)
        self.assertEqual(member.total_spend, Decimal('0.00'))
        self.assertFalse(MemberTransaction.objects.filter(member=member).exists())

    def test_sale_complete_rejects_unsupported_credit_payment(self):
        sale = self._make_sale(status='DRAFT')

        response = self.client.post(
            reverse('sale_complete', args=[sale.id]),
            {
                'payment_method': 'credit',
                'remark': 'unsupported credit settlement',
            },
        )

        self.assertRedirects(response, reverse('sale_complete', args=[sale.id]))
        sale.refresh_from_db()
        self.assertEqual(sale.status, 'DRAFT')
        self.assertEqual(sale.payment_method, 'cash')
        self.assertEqual(sale.balance_paid, Decimal('0.00'))

    def test_sale_detail_does_not_rewrite_persisted_amounts(self):
        sale = self._make_sale(status='COMPLETED')
        Sale.objects.filter(pk=sale.pk).update(
            total_amount=Decimal('1.00'),
            discount_amount=Decimal('0.00'),
            final_amount=Decimal('1.00'),
        )

        response = self.client.get(reverse('sale_detail', args=[sale.id]))

        self.assertEqual(response.status_code, 200)
        sale.refresh_from_db()
        self.assertEqual(sale.total_amount, Decimal('1.00'))
        self.assertEqual(sale.final_amount, Decimal('1.00'))
