from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from inventory.models import (
    Category,
    Inventory,
    Member,
    MemberLevel,
    MemberTransaction,
    Product,
    Sale,
)


class SaleCreateBalancePaymentTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='cashier', password='secret')
        self.client.force_login(self.user)
        self.category = Category.objects.create(name='测试分类')
        self.product = Product.objects.create(
            barcode='1234567890',
            name='测试商品',
            category=self.category,
            price=Decimal('10.00'),
            cost=Decimal('5.00'),
        )
        self.inventory = Inventory.objects.create(
            product=self.product,
            quantity=100,
            warning_level=10,
        )
        self.level = MemberLevel.objects.create(
            name='普通会员',
            discount=Decimal('1.00'),
            points_threshold=0,
            color='primary',
        )
        self.member = Member.objects.create(
            name='测试会员',
            phone='13800138000',
            level=self.level,
            balance=Decimal('100.00'),
        )

    def _sale_post_data(self, payment_method='account', quantity='2'):
        return {
            'member': str(self.member.pk),
            'payment_method': payment_method,
            'remark': '',
            'total_amount': '20.00',
            'discount_amount': '0.00',
            'final_amount': '20.00',
            'products[0][id]': str(self.product.pk),
            'products[0][quantity]': quantity,
            'products[0][price]': '10.00',
        }

    def test_account_payment_deducts_member_balance_in_sale_create(self):
        response = self.client.post(reverse('sale_create'), self._sale_post_data())

        sale = Sale.objects.get()
        self.assertRedirects(response, reverse('sale_detail', args=[sale.pk]))
        self.assertEqual(sale.payment_method, 'balance')
        self.assertEqual(sale.final_amount, Decimal('20.00'))
        self.assertEqual(sale.balance_paid, Decimal('20.00'))

        self.member.refresh_from_db()
        self.assertEqual(self.member.balance, Decimal('80.00'))
        self.assertEqual(self.member.total_spend, Decimal('20.00'))
        self.assertEqual(self.member.purchase_count, 1)
        self.assertEqual(self.member.points, 20)

        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 98)
        self.assertTrue(
            MemberTransaction.objects.filter(
                member=self.member,
                transaction_type='PURCHASE',
                balance_change=Decimal('-20.00'),
                related_object_id=sale.pk,
                related_object_type='Sale',
            ).exists()
        )

    def test_insufficient_balance_rolls_back_sale_and_inventory(self):
        self.member.balance = Decimal('15.00')
        self.member.save(update_fields=['balance'])

        response = self.client.post(reverse('sale_create'), self._sale_post_data())

        self.assertRedirects(response, reverse('sale_create'))
        self.assertFalse(Sale.objects.exists())
        self.assertFalse(MemberTransaction.objects.exists())

        self.member.refresh_from_db()
        self.assertEqual(self.member.balance, Decimal('15.00'))
        self.assertEqual(self.member.total_spend, Decimal('0.00'))
        self.assertEqual(self.member.purchase_count, 0)
        self.assertEqual(self.member.points, 0)

        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 100)
