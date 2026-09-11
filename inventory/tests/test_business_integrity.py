from decimal import Decimal
from datetime import timedelta
from unittest import mock
import tempfile
import json
from pathlib import Path
from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils import timezone
from inventory.models import Sale, SaleItem, Inventory, InventoryTransaction, Product, InventoryCheck
from django.test import Client
from inventory.models import Category, Member, MemberLevel
from inventory.services.report_service import ReportService

class BusinessIntegrityTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='cashier', password='secret')
        self.client = Client()
        self.client.login(username='cashier', password='secret')
        self.category = Category.objects.create(name='测试分类')
        self.product = Product.objects.create(barcode='balance-test-product', name='余额支付商品', category=self.category, price=Decimal('10.00'), cost=Decimal('5.00'))
        self.inventory = Inventory.objects.create(product=self.product, quantity=10, warning_level=1)
        self.level = MemberLevel.objects.create(name='无折扣会员', discount=Decimal('1.00'), points_threshold=0, color='primary')
        self.member = Member.objects.create(name='余额会员', phone='13900000000', level=self.level, balance=Decimal('100.00'))

    def sale_post_data(self, payment_method='balance'):
        return {'member': str(self.member.id), 'payment_method': payment_method, 'products[0][id]': str(self.product.id), 'products[0][quantity]': '2', 'products[0][price]': '10.00', 'total_amount': '20.00', 'discount_amount': '0.00', 'final_amount': '20.00'}

    def test_unprivileged_account_cannot_adjust_balance(self):
        self.assertFalse(self.user.has_perm('inventory.change_member'))
        self.client.post(reverse('member_balance_adjust', args=[self.member.pk]), {'balance_change': '500', 'description': 'probe'})
        self.member.refresh_from_db()
        self.assertEqual(self.member.balance, Decimal('100'), 'Unprivileged account added 500 to member balance')

    def test_unprivileged_account_cannot_change_stock(self):
        self.assertFalse(self.user.has_perm('inventory.change_inventory'))
        self.client.post(reverse('inventory_in'), {'product': self.product.pk, 'quantity': 5, 'notes': 'probe'})
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 10, 'Unprivileged account added stock')

    def test_inventory_write_failure_rolls_back_quantity(self):
        self.user.is_superuser = True
        self.user.save()
        with mock.patch('inventory.models.inventory.InventoryTransaction.objects.create', side_effect=RuntimeError('simulated audit failure')):
            response = self.client.post(reverse('inventory_in'), {'product': self.product.pk, 'quantity': 5, 'notes': 'probe'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(InventoryTransaction.objects.exists())
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 10, 'Reported failure but inventory changed to 15')

    def test_inventory_adjust_allows_setting_zero(self):
        self.user.is_superuser = True
        self.user.save()
        self.client.post(reverse('inventory_adjust'), {'product': self.product.pk, 'quantity': 0, 'adjustment_action': 'set', 'notes': 'clear stock'})
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 0, 'Cannot set stock to zero')

    def test_model_item_price_edit_does_not_rededuct_stock(self):
        sale = Sale.objects.create(operator=self.user, total_amount=0, final_amount=0)
        item = SaleItem.objects.create(sale=sale, product=self.product, quantity=2, price=10, actual_price=10)
        self.inventory.refresh_from_db()
        before = self.inventory.quantity
        item.actual_price = Decimal('9')
        item.save()
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, before, 'Updating existing item price deducted quantity again')

    def test_home_sales_excludes_cancelled_orders(self):
        Sale.objects.create(operator=self.user, status='COMPLETED', total_amount=20, final_amount=20)
        Sale.objects.create(operator=self.user, status='CANCELLED', total_amount=100, final_amount=100)
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['today_sales_amount'], 20, 'Cancelled amount counted as sales')

    def test_sales_report_does_not_multiply_order_total(self):
        sale = Sale.objects.create(operator=self.user, status='COMPLETED', total_amount=0, final_amount=0)
        for _ in range(2):
            SaleItem.objects.create(sale=sale, product=self.product, quantity=1, price=10, actual_price=10)
        now = timezone.now()
        data = list(ReportService.get_sales_by_period(now - timedelta(days=1), now + timedelta(days=1)))
        self.assertEqual(sum((x['total_sales'] for x in data)), 20, 'Two item rows doubled a 20-yuan order to 40')

    def test_authorized_inventory_checker_can_open_page(self):
        ct = ContentType.objects.get_for_model(InventoryCheck)
        (permission, _) = Permission.objects.get_or_create(content_type=ct, codename='perform_inventory_check', defaults={'name': 'Perform check'})
        self.user.user_permissions.add(permission)
        self.assertTrue(User.objects.get(pk=self.user.pk).has_perm('inventory.perform_inventory_check'))
        response = self.client.get(reverse('inventory_check_list'))
        self.assertEqual(response.status_code, 200, 'Correctly authorized user rejected because permission name lacks app label')

    def test_recharge_rejects_negative_actual_received(self):
        self.user.is_superuser = True
        self.user.save()
        self.client.post(reverse('member_recharge', args=[self.member.pk]), {'amount': '100', 'actual_amount': '-50', 'payment_method': 'cash'})
        self.member.refresh_from_db()
        self.assertEqual(self.member.balance, Decimal('100'), 'Recharge accepted negative cash received and credited 100')

    def test_backup_restore_page_renders(self):
        self.user.is_superuser = True
        self.user.save()
        self.client.raise_request_exception = False
        with tempfile.TemporaryDirectory() as tmp:
            snapshot = Path(tmp) / 'snapshot'
            snapshot.mkdir()
            (snapshot / 'backup_info.json').write_text(json.dumps({'created_at': '2026-09-11T10:00:00', 'includes_media': False}))
            with self.settings(BACKUP_ROOT=tmp):
                response = self.client.get(reverse('restore_backup', args=['snapshot']))
            self.assertEqual(response.status_code, 200, 'Backup restore confirmation page crashes')

class LogDownloadIntegrityTests(TransactionTestCase):

    def test_log_download_works(self):
        from inventory.views.system import log
        user = User.objects.create_superuser('logscan', 'logscan@example.com', 'password')
        self.client.force_login(user)
        directory = Path(log.__file__).resolve().parents[3] / 'logs'
        directory.mkdir(exist_ok=True)
        path = directory / 'scan-review.log'
        path.write_text('test log')
        self.addCleanup(path.unlink, missing_ok=True)
        response = self.client.get(reverse('download_log_file', args=[path.name]))
        self.assertEqual(response.status_code, 200, 'Invalid content-type audit FK prevents log download')

class PaymentAndInventoryEdgeTests(TestCase):
    setUp = BusinessIntegrityTests.setUp
    sale_post_data = BusinessIntegrityTests.sale_post_data

    def test_named_member_permission_allows_recharge(self):
        self.user.user_permissions.add(Permission.objects.get(codename='change_member', content_type__app_label='inventory'))
        response = self.client.post(reverse('member_recharge', args=[self.member.pk]), {'amount': '50.00', 'actual_amount': '40.00', 'payment_method': 'cash'})
        self.assertEqual(response.status_code, 302)
        self.member.refresh_from_db()
        self.assertEqual(self.member.balance, Decimal('150.00'))

    def test_recharge_rejects_nonfinite_amounts_and_unknown_payment(self):
        self.user.is_superuser = True
        self.user.save()
        for (amount, actual, method) in [('NaN', '10', 'cash'), ('10', 'Infinity', 'cash'), ('10', '10', 'unknown'), ('10.001', '10', 'cash')]:
            with self.subTest(amount=amount, actual=actual, method=method):
                self.client.post(reverse('member_recharge', args=[self.member.pk]), {'amount': amount, 'actual_amount': actual, 'payment_method': method})
                self.member.refresh_from_db()
                self.assertEqual(self.member.balance, Decimal('100.00'))

    def test_quantity_changes_only_apply_delta_and_roll_back_on_shortage(self):
        from django.core.exceptions import ValidationError
        sale = Sale.objects.create(operator=self.user, total_amount=0, final_amount=0)
        item = SaleItem.objects.create(sale=sale, product=self.product, quantity=2, price=10, actual_price=10)
        item.quantity = 3
        item.save(update_fields=['quantity'])
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 7)
        item.quantity = 1
        item.save(update_fields=['quantity'])
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 9)
        item.quantity = 20
        with self.assertRaises(ValidationError):
            item.save()
        item.refresh_from_db()
        self.inventory.refresh_from_db()
        sale.refresh_from_db()
        self.assertEqual(item.quantity, 1)
        self.assertEqual(self.inventory.quantity, 9)
        self.assertEqual(sale.total_amount, Decimal('10'))

    def test_equal_value_orders_and_cancelled_orders_in_reports(self):
        for status in ['COMPLETED', 'COMPLETED', 'CANCELLED', 'DRAFT']:
            sale = Sale.objects.create(operator=self.user, status=status, total_amount=0, final_amount=0)
            for _ in range(2):
                SaleItem.objects.create(sale=sale, product=self.product, quantity=1, price=10, actual_price=10)
        now = timezone.now()
        data = list(ReportService.get_sales_by_period(now - timedelta(days=1), now + timedelta(days=1)))
        self.assertEqual(sum((row['total_sales'] for row in data)), Decimal('40'))
        self.assertEqual(sum((row['total_cost'] for row in data)), Decimal('20'))
        self.assertEqual(sum((row['item_count'] for row in data)), 4)
        self.assertEqual(sum((row['order_count'] for row in data)), 2)

    def test_quantity_not_in_update_fields_does_not_change_stock(self):
        sale = Sale.objects.create(operator=self.user, total_amount=0, final_amount=0)
        item = SaleItem.objects.create(sale=sale, product=self.product, quantity=2, price=10, actual_price=10)
        item.quantity = 5
        item.actual_price = Decimal('9')
        item.save(update_fields=['actual_price'])
        item.refresh_from_db()
        self.inventory.refresh_from_db()
        self.assertEqual(item.quantity, 2)
        self.assertEqual(item.subtotal, Decimal('18'))
        self.assertEqual(self.inventory.quantity, 8)

    def test_all_sensitive_write_routes_reject_unprivileged_account(self):
        member_data = {'amount': '10', 'actual_amount': '10', 'points_change': '10', 'balance_change': '10'}
        routes = [(name, [self.member.pk], member_data) for name in ('member_recharge', 'member_points_adjust', 'member_balance_adjust')]
        inventory_data = {'product': self.product.pk, 'quantity': 1, 'adjustment_action': 'add'}
        routes += [(name, [], inventory_data) for name in ('inventory_in', 'inventory_out', 'inventory_adjust', 'inventory_create')]
        for (name, args, data) in routes:
            with self.subTest(route=name):
                response = self.client.post(reverse(name, args=args), data)
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response['Location'], reverse('index'))
                self.member.refresh_from_db()
                self.inventory.refresh_from_db()
                self.assertEqual(self.member.balance, Decimal('100'))
                self.assertEqual(self.member.points, 0)
                self.assertEqual(self.inventory.quantity, 10)

    def test_operation_log_failure_rolls_back_inventory_and_ledger(self):
        self.user.user_permissions.add(Permission.objects.get(codename='change_inventory', content_type__app_label='inventory'))
        with mock.patch('inventory.views.inventory.OperationLog.objects.create', side_effect=RuntimeError('audit failure')):
            with self.assertRaises(RuntimeError):
                self.client.post(reverse('inventory_in'), {'product': self.product.pk, 'quantity': 5})
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 10)
        self.assertFalse(InventoryTransaction.objects.exists())

    def test_zero_delta_is_only_accepted_for_set(self):
        self.user.user_permissions.add(Permission.objects.get(codename='change_inventory', content_type__app_label='inventory'))
        for action in ['add', 'subtract']:
            with self.subTest(action=action):
                response = self.client.post(reverse('inventory_adjust'), {'product': self.product.pk, 'quantity': 0, 'adjustment_action': action})
                self.assertEqual(response.status_code, 200)
                self.assertIn('quantity', response.context['form'].errors)
                self.inventory.refresh_from_db()
                self.assertEqual(self.inventory.quantity, 10)
