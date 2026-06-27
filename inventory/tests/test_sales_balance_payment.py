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
)


class SaleBalancePaymentTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='cashier', password='secret')
        self.client = Client()
        self.client.login(username='cashier', password='secret')

        self.category = Category.objects.create(name='测试分类')
        self.product = Product.objects.create(
            barcode='balance-test-product',
            name='余额支付商品',
            category=self.category,
            price=Decimal('10.00'),
            cost=Decimal('5.00'),
        )
        self.inventory = Inventory.objects.create(
            product=self.product,
            quantity=10,
            warning_level=1,
        )
        self.level = MemberLevel.objects.create(
            name='无折扣会员',
            discount=Decimal('1.00'),
            points_threshold=0,
            color='primary',
        )
        self.member = Member.objects.create(
            name='余额会员',
            phone='13900000000',
            level=self.level,
            balance=Decimal('100.00'),
        )

    def sale_post_data(self, payment_method='balance'):
        return {
            'member': str(self.member.id),
            'payment_method': payment_method,
            'products[0][id]': str(self.product.id),
            'products[0][quantity]': '2',
            'products[0][price]': '10.00',
            'total_amount': '20.00',
            'discount_amount': '0.00',
            'final_amount': '20.00',
        }

    def test_sale_create_balance_payment_deducts_member_balance(self):
        response = self.client.post(reverse('sale_create'), self.sale_post_data('account'))

        sale = Sale.objects.get()
        self.assertRedirects(response, reverse('sale_detail', args=[sale.id]))
        self.assertEqual(sale.payment_method, 'balance')
        self.assertEqual(sale.balance_paid, Decimal('20.00'))

        self.member.refresh_from_db()
        self.assertEqual(self.member.balance, Decimal('80.00'))
        self.assertEqual(self.member.total_spend, Decimal('20.00'))
        self.assertEqual(self.member.purchase_count, 1)

        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 8)
        self.assertTrue(
            MemberTransaction.objects.filter(
                member=self.member,
                transaction_type='PURCHASE',
                balance_change=Decimal('-20.00'),
                related_object_id=sale.id,
                related_object_type='Sale',
            ).exists()
        )

    def test_sale_create_balance_payment_rolls_back_when_balance_is_insufficient(self):
        self.member.balance = Decimal('5.00')
        self.member.save(update_fields=['balance'])

        response = self.client.post(reverse('sale_create'), self.sale_post_data('balance'))

        self.assertRedirects(response, reverse('sale_create'))
        self.assertFalse(Sale.objects.exists())

        self.member.refresh_from_db()
        self.assertEqual(self.member.balance, Decimal('5.00'))
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 10)

    def test_sale_create_rejects_unsupported_credit_payment(self):
        response = self.client.post(reverse('sale_create'), self.sale_post_data('credit'))

        self.assertRedirects(response, reverse('sale_create'))
        self.assertFalse(Sale.objects.exists())
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 10)
