import json
import os
import tempfile
from decimal import Decimal
from unittest.mock import call, patch

from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import User
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


class CriticalSaleRegressionTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('cashier', password='pass')
        self.client = Client()
        self.client.login(username='cashier', password='pass')

        category = Category.objects.create(name='测试分类')
        self.product = Product.objects.create(
            barcode='critical-001',
            name='关键商品',
            category=category,
            price=Decimal('50.00'),
            cost=Decimal('10.00'),
        )
        self.inventory = Inventory.objects.create(product=self.product, quantity=10)
        self.level = MemberLevel.objects.create(
            name='无折扣会员',
            discount=Decimal('1.00'),
            points_threshold=0,
        )
        self.member = Member.objects.create(
            name='余额会员',
            phone='13900000000',
            level=self.level,
            balance=Decimal('100.00'),
        )

    def _post_sale_create(self, payment_method='account', member=None, quantity='1'):
        return self.client.post(reverse('sale_create'), {
            'member': member.pk if member else '',
            'payment_method': payment_method,
            'products[0][id]': self.product.pk,
            'products[0][quantity]': quantity,
            'products[0][price]': '50.00',
            'total_amount': '50.00',
            'discount_amount': '0.00',
            'final_amount': '50.00',
            'remark': '',
        })

    def test_sale_create_account_payment_deducts_member_balance(self):
        response = self._post_sale_create(member=self.member)

        sale = Sale.objects.get()
        self.assertRedirects(response, reverse('sale_detail', args=[sale.pk]))

        self.member.refresh_from_db()
        self.inventory.refresh_from_db()
        self.assertEqual(sale.payment_method, 'balance')
        self.assertEqual(sale.balance_paid, Decimal('50.00'))
        self.assertEqual(self.member.balance, Decimal('50.00'))
        self.assertEqual(self.member.purchase_count, 1)
        self.assertEqual(self.member.total_spend, Decimal('50.00'))
        self.assertEqual(self.inventory.quantity, 9)

        transaction = MemberTransaction.objects.get(member=self.member)
        self.assertEqual(transaction.transaction_type, 'PURCHASE')
        self.assertEqual(transaction.balance_change, Decimal('-50.00'))

    def test_sale_create_insufficient_balance_rolls_back_sale_and_inventory(self):
        self.member.balance = Decimal('20.00')
        self.member.save(update_fields=['balance'])

        response = self._post_sale_create(member=self.member)

        self.assertRedirects(response, reverse('sale_create'))
        self.assertFalse(Sale.objects.exists())
        self.assertFalse(SaleItem.objects.exists())
        self.assertFalse(MemberTransaction.objects.exists())

        self.member.refresh_from_db()
        self.inventory.refresh_from_db()
        self.assertEqual(self.member.balance, Decimal('20.00'))
        self.assertEqual(self.member.purchase_count, 0)
        self.assertEqual(self.member.total_spend, Decimal('0.00'))
        self.assertEqual(self.inventory.quantity, 10)

    def test_sale_item_create_deducts_inventory_once(self):
        sale = Sale.objects.create(
            total_amount=Decimal('0.00'),
            discount_amount=Decimal('0.00'),
            final_amount=Decimal('0.00'),
            operator=self.user,
        )

        response = self.client.post(reverse('sale_item_create', args=[sale.pk]), {
            'product': self.product.pk,
            'quantity': '3',
            'price': '50.00',
            'actual_price': '50.00',
        })

        self.assertRedirects(response, reverse('sale_item_create', args=[sale.pk]))
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 7)
        self.assertEqual(InventoryTransaction.objects.filter(product=self.product, transaction_type='OUT').count(), 1)


class CriticalBackupRegressionTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_superuser(
            username='backup-admin',
            password='backup-pass',
            email='backup@example.com',
        )
        self.client.force_login(self.user)

        self.temp_parent = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_parent.cleanup)
        self.backup_root = os.path.join(self.temp_parent.name, 'backups')
        self.temp_dir = os.path.join(self.temp_parent.name, 'temp')
        os.makedirs(self.backup_root, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)

    def _write_backup(self, name='backup_critical'):
        backup_dir = os.path.join(self.backup_root, name)
        os.makedirs(backup_dir, exist_ok=True)
        with open(os.path.join(backup_dir, 'backup_info.json'), 'w', encoding='utf-8') as info_file:
            json.dump({
                'name': name,
                'created_at': '2026-05-28T11:00:00',
                'created_by': self.user.username,
                'includes_media': False,
            }, info_file)
        with open(os.path.join(backup_dir, 'db.json'), 'w', encoding='utf-8') as db_file:
            db_file.write('[]')
        return name, backup_dir

    def test_create_backup_logs_with_valid_content_type(self):
        with self.settings(BACKUP_ROOT=self.backup_root, TEMP_DIR=self.temp_dir):
            response = self.client.post(reverse('create_backup'), {
                'backup_name': 'backup_create_log',
                'backup_description': 'critical regression',
            })

        self.assertRedirects(response, reverse('backup_list'))
        self.assertTrue(os.path.isdir(os.path.join(self.backup_root, 'backup_create_log')))
        log = LogEntry.objects.get(object_id='backup_create_log')
        self.assertIsNotNone(log.content_type_id)

    def test_restore_backup_flushes_before_loading_fixture(self):
        backup_name, _backup_dir = self._write_backup()

        with self.settings(BACKUP_ROOT=self.backup_root, TEMP_DIR=self.temp_dir):
            with patch('inventory.views.system.backup.management.call_command') as call_command:
                response = self.client.post(reverse('restore_backup', args=[backup_name]), {
                    'confirm': 'on',
                })

        self.assertRedirects(response, reverse('system_settings'))
        self.assertEqual(call_command.call_args_list[0], call('flush', interactive=False, verbosity=0))
        self.assertEqual(call_command.call_args_list[1][0][0], 'loaddata')
        self.assertTrue(call_command.call_args_list[1][0][1].endswith(os.path.join(backup_name, 'db.json')))
