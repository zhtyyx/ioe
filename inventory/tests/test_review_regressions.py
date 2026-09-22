from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier
from unittest.mock import patch

from django.contrib.auth.models import Group, Permission, User
from django.db import connection, connections, models
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse

from inventory.models import (
    Category, Inventory, InventoryTransaction, Member, MemberLevel,
    MemberTransaction, OperationLog, Product, RechargeRecord, Sale, SaleItem,
)
from inventory.models.inventory import update_inventory


def create_product():
    return Product.objects.create(
        name='回归测试商品', barcode='review-product',
        category=Category.objects.create(name='回归测试分类'),
        price=Decimal('10.00'), cost=Decimal('5.00'),
    )


class ReviewRegressionTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='operator', password='secret')
        cls.admin = User.objects.create_superuser(username='admin', password='secret')
        cls.product = create_product()
        cls.stock = Inventory.objects.create(product=cls.product, quantity=10)
        level = MemberLevel.objects.create(name='普通会员', discount=1, points_threshold=0)
        cls.member = Member.objects.create(
            name='测试会员', phone='5550000001', level=level, balance=100,
        )

    def setUp(self):
        self.user.user_permissions.add(*Permission.objects.filter(
            content_type__app_label='inventory',
            codename__in=['change_member', 'change_inventory'],
        ))
        self.client.force_login(self.user)

    def grant(self, *codenames):
        self.user.user_permissions.add(*Permission.objects.filter(
            content_type__app_label='auth', codename__in=codenames,
        ))

    def make_sale(self):
        sale = Sale.objects.create(
            total_amount=20, final_amount=20, operator=self.user, status='DRAFT',
        )
        item = SaleItem(
            sale=sale, product=self.product, quantity=2,
            price=10, actual_price=10, subtotal=20,
        )
        # 库存设为销售后的数量，避免模型 save() 再次扣库存。
        models.Model.save(item)
        Inventory.objects.filter(pk=self.stock.pk).update(quantity=8)
        return sale, item

    def test_recharge_updates_balance_and_records_once(self):
        response = self.client.post(reverse('member_recharge', args=[self.member.pk]), {
            'amount': '20.00', 'actual_amount': '18.00', 'payment_method': 'cash',
        })
        self.assertEqual(response.status_code, 302)
        self.member.refresh_from_db()
        self.assertEqual(self.member.balance, Decimal('120.00'))
        self.assertTrue(self.member.is_recharged)
        self.assertEqual(RechargeRecord.objects.get().amount, Decimal('20.00'))
        self.assertEqual(MemberTransaction.objects.get().balance_change, Decimal('20.00'))

    def test_balance_adjust_updates_balance_once(self):
        response = self.client.post(reverse('member_balance_adjust', args=[self.member.pk]), {
            'balance_change': '-15.50', 'description': '回归测试',
        })
        self.assertEqual(response.status_code, 302)
        self.member.refresh_from_db()
        self.assertEqual(self.member.balance, Decimal('84.50'))
        self.assertEqual(MemberTransaction.objects.get().balance_change, Decimal('-15.50'))

    def test_recharge_rolls_back_if_log_fails(self):
        with patch.object(OperationLog.objects, 'create', side_effect=RuntimeError('log failed')):
            with self.assertRaises(RuntimeError):
                self.client.post(reverse('member_recharge', args=[self.member.pk]), {'amount': '20'})
        self.member.refresh_from_db()
        self.assertEqual(self.member.balance, Decimal('100.00'))
        self.assertFalse(RechargeRecord.objects.exists())
        self.assertFalse(MemberTransaction.objects.exists())

    def test_user_list_renders_with_view_permission(self):
        self.grant('view_user')
        response = self.client.get(reverse('user_list'))
        self.assertContains(response, self.user.username)

    def test_delegated_manager_cannot_escalate_or_take_over_privileged_accounts(self):
        self.grant('add_user', 'change_user', 'delete_user')
        group = Group.objects.create(name='系统管理员')
        ordinary = User.objects.create_user(username='ordinary')
        for data in ({'is_superuser': 'on'}, {'is_staff': 'on'}, {'groups': [group.pk]}):
            with self.subTest(data=data):
                response = self.client.post(reverse('user_update', args=[ordinary.pk]), data)
                self.assertEqual(response.status_code, 403)
        for target in (self.user, self.admin):
            with self.subTest(target=target.username):
                response = self.client.post(reverse('user_update', args=[target.pk]), {
                    'is_active': 'on', 'is_superuser': 'on',
                    'new_password': 'takeover-password', 'new_password_confirm': 'takeover-password',
                })
                self.assertEqual(response.status_code, 403)
                response = self.client.post(reverse('user_delete', args=[target.pk]))
                self.assertEqual(response.status_code, 403)
        response = self.client.post(reverse('user_create'), {
            'username': 'escalated', 'password': 'secret123', 'password_confirm': 'secret123',
            'is_superuser': 'on',
        })
        self.assertEqual(response.status_code, 403)
        self.assertFalse(User.objects.filter(username='escalated').exists())
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_superuser)
        self.assertTrue(self.admin.check_password('secret'))
        ordinary.refresh_from_db()
        self.assertFalse(ordinary.is_staff)
        self.assertFalse(ordinary.is_superuser)
        self.assertFalse(ordinary.groups.exists())

    def test_delegated_manager_can_create_and_edit_ordinary_accounts(self):
        self.grant('add_user', 'change_user')
        response = self.client.post(reverse('user_create'), {
            'username': 'ordinary', 'password': 'secret123', 'password_confirm': 'secret123',
            'is_active': 'on',
        })
        self.assertEqual(response.status_code, 302)
        ordinary = User.objects.get(username='ordinary')
        response = self.client.post(reverse('user_update', args=[ordinary.pk]), {
            'email': 'updated@example.com', 'is_active': 'on',
        })
        self.assertEqual(response.status_code, 302)
        ordinary.refresh_from_db()
        self.assertEqual(ordinary.email, 'updated@example.com')
        self.assertFalse(ordinary.is_superuser)
        self.assertFalse(ordinary.is_staff)

    def test_admin_can_create_update_and_delete_users_with_audit_logs(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse('user_create'), {
            'username': 'created', 'password': 'secret123', 'password_confirm': 'secret123',
            'is_active': 'on', 'is_staff': 'on',
        })
        self.assertEqual(response.status_code, 302)
        target = User.objects.get(username='created')
        target_id = target.pk
        response = self.client.post(reverse('user_update', args=[target.pk]), {
            'email': 'changed@example.com', 'is_active': 'on', 'is_superuser': 'on',
        })
        self.assertEqual(response.status_code, 302)
        target.refresh_from_db()
        self.assertTrue(target.is_superuser)
        response = self.client.post(reverse('user_delete', args=[target.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(User.objects.filter(pk=target_id).exists())
        self.assertEqual(OperationLog.objects.filter(
            related_object_id=target_id, related_content_type__model='user',
        ).count(), 3)

    def test_user_update_rolls_back_if_logging_fails(self):
        self.client.force_login(self.admin)
        with patch.object(OperationLog.objects, 'create', side_effect=RuntimeError('log failed')):
            with self.assertRaises(RuntimeError):
                self.client.post(reverse('user_update', args=[self.user.pk]), {
                    'is_active': 'on', 'is_superuser': 'on',
                })
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_superuser)

    def test_delete_item_requires_post_and_csrf(self):
        sale, item = self.make_sale()
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        url = reverse('sale_item_delete', args=[sale.pk, item.pk])
        self.assertEqual(client.get(url).status_code, 405)
        self.assertEqual(client.post(url).status_code, 403)
        page = client.get(reverse('sale_item_create', args=[sale.pk]))
        self.assertContains(page, f'action="{url}"')
        response = client.post(url, {'csrfmiddlewaretoken': client.cookies['csrftoken'].value})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(SaleItem.objects.filter(pk=item.pk).exists())
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 10)
        sale.refresh_from_db()
        self.assertEqual(sale.total_amount, 0)
        self.assertEqual(client.post(url, {
            'csrfmiddlewaretoken': client.cookies['csrftoken'].value,
        }).status_code, 404)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 10)

    def test_delete_item_rolls_back_stock_item_and_total_if_log_fails(self):
        sale, item = self.make_sale()
        with patch.object(OperationLog.objects, 'create', side_effect=RuntimeError('log failed')):
            with self.assertRaises(RuntimeError):
                self.client.post(reverse('sale_item_delete', args=[sale.pk, item.pk]))
        self.stock.refresh_from_db()
        sale.refresh_from_db()
        self.assertEqual(self.stock.quantity, 8)
        self.assertTrue(SaleItem.objects.filter(pk=item.pk).exists())
        self.assertEqual(sale.total_amount, 20)
        self.assertFalse(InventoryTransaction.objects.exists())

    def test_stock_and_ledger_roll_back_together(self):
        with patch.object(InventoryTransaction.objects, 'create', side_effect=RuntimeError('ledger failed')):
            success, _, _ = update_inventory(self.product, -3, 'OUT', self.user)
        self.assertFalse(success)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 10)
        self.assertFalse(InventoryTransaction.objects.exists())

    def test_stock_rejects_insufficient_quantity_without_writes(self):
        success, _, _ = update_inventory(self.product, -11, 'OUT', self.user)
        self.assertFalse(success)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 10)
        self.assertFalse(InventoryTransaction.objects.exists())

    def test_stock_can_be_initialized_on_incoming_transaction(self):
        self.stock.delete()
        success, stock, record = update_inventory(self.product, 3, 'IN', self.user)
        self.assertTrue(success)
        self.assertEqual(stock.quantity, 3)
        self.assertEqual(record.quantity, 3)

    def test_inventory_create_initializes_stock_and_writes_one_ledger_entry(self):
        self.stock.delete()
        response = self.client.post(reverse('inventory_create'), {
            'product': self.product.pk, 'quantity': '3', 'notes': '首次入库',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Inventory.objects.get(product=self.product).quantity, 3)
        self.assertEqual(InventoryTransaction.objects.get().quantity, 3)
        self.assertEqual(OperationLog.objects.count(), 1)


class InventoryConcurrencyRegressionTest(TransactionTestCase):
    def setUp(self):
        database_name = str(connection.settings_dict['NAME'])
        if connection.vendor == 'sqlite' and (database_name == ':memory:' or 'mode=memory' in database_name):
            self.skipTest('并发测试需文件型 SQLite 测试库或 PostgreSQL，避免共享内存数据库的表锁')
        self.user = User.objects.create_user(username='operator')
        self.product = create_product()
        self.stock = Inventory.objects.create(product=self.product, quantity=10)

    def run_withdrawals(self):
        start = Barrier(2)

        def worker():
            try:
                start.wait(timeout=10)
                return update_inventory(self.product, -3, 'OUT', self.user)[0]
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            return list(pool.map(lambda _: worker(), range(2)))

    def test_two_withdrawals_cannot_overwrite_each_other(self):
        read_barrier = Barrier(2)
        original_get = Inventory.objects.get_or_create

        def synchronized_read(*args, **kwargs):
            result = original_get(*args, **kwargs)
            read_barrier.wait(timeout=10)
            return result

        # 旧实现两次读到相同库存，新实现先执行条件 UPDATE，不依赖旧快照。
        with patch.object(Inventory.objects, 'get_or_create', side_effect=synchronized_read):
            self.assertEqual(self.run_withdrawals(), [True, True])
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 4)
        self.assertEqual(InventoryTransaction.objects.count(), 2)

    def test_two_withdrawals_cannot_oversell(self):
        Inventory.objects.filter(pk=self.stock.pk).update(quantity=5)
        self.assertEqual(sorted(self.run_withdrawals()), [False, True])
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 2)
        self.assertEqual(InventoryTransaction.objects.count(), 1)
