from decimal import Decimal

from django.contrib.auth.models import User
from django.db import models
from django.test import Client, TestCase
from django.urls import reverse

from inventory.models import (
    Category,
    Inventory,
    InventoryTransaction,
    Member,
    MemberLevel,
    MemberTransaction,
    Product,
    Sale,
    SaleItem,
)


class SalesCriticalRegressionTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='cashier', password='pass')
        self.client.force_login(self.user)

        self.category = Category.objects.create(name='测试分类')
        self.product = Product.objects.create(
            barcode='critical-001',
            name='关键商品',
            category=self.category,
            price=Decimal('10.00'),
            cost=Decimal('5.00'),
        )
        self.inventory = Inventory.objects.create(
            product=self.product,
            quantity=10,
            warning_level=1,
        )
        self.member_level = MemberLevel.objects.create(
            name='无折扣会员',
            discount=Decimal('1.00'),
            points_threshold=0,
            color='primary',
        )
        self.member = Member.objects.create(
            name='余额会员',
            phone='13900000000',
            level=self.member_level,
            balance=Decimal('100.00'),
        )

    def _sale_create_payload(self, payment_method='cash', member=None):
        payload = {
            'payment_method': payment_method,
            'products[0][id]': str(self.product.id),
            'products[0][quantity]': '1',
            'products[0][price]': '10.00',
            'total_amount': '10.00',
            'discount_amount': '0.00',
            'final_amount': '10.00',
        }
        if member:
            payload['member'] = str(member.id)
        return payload

    def _create_sale_with_item(self, member=None):
        sale = Sale.objects.create(
            member=member,
            total_amount=Decimal('10.00'),
            discount_amount=Decimal('0.00'),
            final_amount=Decimal('10.00'),
            operator=self.user,
        )
        sale_item = SaleItem(
            sale=sale,
            product=self.product,
            quantity=1,
            price=Decimal('10.00'),
            actual_price=Decimal('10.00'),
            subtotal=Decimal('10.00'),
        )
        models.Model.save(sale_item)
        return sale

    def test_sale_create_account_payment_deducts_member_balance(self):
        response = self.client.post(
            reverse('sale_create'),
            self._sale_create_payload(payment_method='account', member=self.member),
        )

        sale = Sale.objects.get()
        self.assertRedirects(response, reverse('sale_detail', args=[sale.id]))

        self.member.refresh_from_db()
        self.inventory.refresh_from_db()
        sale.refresh_from_db()

        self.assertEqual(sale.payment_method, 'balance')
        self.assertEqual(sale.balance_paid, Decimal('10.00'))
        self.assertEqual(self.member.balance, Decimal('90.00'))
        self.assertEqual(self.inventory.quantity, 9)
        self.assertEqual(
            MemberTransaction.objects.get(member=self.member).balance_change,
            Decimal('-10.00'),
        )

    def test_sale_create_insufficient_balance_rolls_back_sale_and_inventory(self):
        self.member.balance = Decimal('5.00')
        self.member.save(update_fields=['balance'])

        response = self.client.post(
            reverse('sale_create'),
            self._sale_create_payload(payment_method='account', member=self.member),
        )

        self.assertRedirects(response, reverse('sale_create'))
        self.assertFalse(Sale.objects.exists())
        self.assertFalse(SaleItem.objects.exists())
        self.assertFalse(MemberTransaction.objects.exists())

        self.member.refresh_from_db()
        self.inventory.refresh_from_db()
        self.assertEqual(self.member.balance, Decimal('5.00'))
        self.assertEqual(self.inventory.quantity, 10)

    def test_sale_item_create_deducts_inventory_once(self):
        sale = Sale.objects.create(
            total_amount=Decimal('0.00'),
            discount_amount=Decimal('0.00'),
            final_amount=Decimal('0.00'),
            operator=self.user,
        )

        response = self.client.post(
            reverse('sale_item_create', args=[sale.id]),
            {
                'product': str(self.product.id),
                'quantity': '3',
                'price': '10.00',
                'actual_price': '10.00',
            },
        )

        self.assertRedirects(response, reverse('sale_item_create', args=[sale.id]))
        self.inventory.refresh_from_db()
        sale.refresh_from_db()

        self.assertEqual(self.inventory.quantity, 7)
        self.assertEqual(InventoryTransaction.objects.filter(product=self.product).count(), 1)
        self.assertEqual(SaleItem.objects.get(sale=sale).subtotal, Decimal('30.00'))
        self.assertEqual(sale.total_amount, Decimal('30.00'))

    def test_sale_complete_insufficient_balance_does_not_credit_member(self):
        sale = self._create_sale_with_item(member=self.member)
        self.member.balance = Decimal('5.00')
        self.member.save(update_fields=['balance'])

        response = self.client.post(
            reverse('sale_complete', args=[sale.id]),
            {
                'payment_method': 'balance',
                'remark': '余额不足',
            },
        )

        self.assertRedirects(response, reverse('sale_complete', args=[sale.id]))

        self.member.refresh_from_db()
        sale.refresh_from_db()

        self.assertEqual(self.member.balance, Decimal('5.00'))
        self.assertEqual(self.member.points, 0)
        self.assertEqual(self.member.purchase_count, 0)
        self.assertEqual(self.member.total_spend, Decimal('0.00'))
        self.assertEqual(sale.balance_paid, Decimal('0.00'))
        self.assertFalse(MemberTransaction.objects.filter(member=self.member).exists())
