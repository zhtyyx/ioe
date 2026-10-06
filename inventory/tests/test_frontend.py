from decimal import Decimal

from django.contrib.auth.models import Permission, User
from django.test import TestCase, override_settings
from django.urls import reverse

from inventory.models import Category, Inventory, InventoryTransaction, Product


@override_settings(ALLOWED_HOSTS=['testserver'])
class InventoryFrontendTest(TestCase):
    """The restored inventory pages must render errors and submit real movements."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='stock-clerk', password='test-password')
        cls.user.user_permissions.add(Permission.objects.get(
            content_type__app_label='inventory', codename='change_inventory',
        ))
        cls.product = Product.objects.create(
            name='Test product', barcode='frontend-product',
            category=Category.objects.create(name='Test category'),
            price=Decimal('10.00'), cost=Decimal('5.00'),
        )
        cls.stock = Inventory.objects.create(product=cls.product, quantity=10)

    def setUp(self):
        self.client.force_login(self.user)

    def test_inventory_pages_render(self):
        for route in ('inventory_in', 'inventory_out', 'inventory_adjust', 'inventory_transaction_list'):
            with self.subTest(route=route):
                self.assertEqual(self.client.get(reverse(route)).status_code, 200)

    def test_invalid_stock_movement_keeps_form_and_stock(self):
        response = self.client.post(reverse('inventory_in'), {
            'product': self.product.pk, 'quantity': '-1', 'notes': 'Invalid receipt',
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 10)
        self.assertFalse(InventoryTransaction.objects.exists())

    def test_stock_receipt_and_adjustment_use_existing_handlers(self):
        response = self.client.post(reverse('inventory_in'), {
            'product': self.product.pk, 'quantity': '3', 'notes': 'Receipt',
        })
        self.assertRedirects(response, reverse('inventory_list'))
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 13)
        response = self.client.post(reverse('inventory_adjust'), {
            'product': self.product.pk, 'quantity': '2',
            'adjustment_action': 'subtract', 'notes': 'Adjustment',
        })
        self.assertRedirects(response, reverse('inventory_list'))
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 11)
        self.assertEqual(InventoryTransaction.objects.count(), 2)

    def test_settings_has_working_management_destinations(self):
        self.user.is_superuser = True
        self.user.is_staff = True
        self.user.save()
        response = self.client.get(reverse('system_settings'))
        self.assertEqual(response.status_code, 200)
        for route in ('user_list', 'backup_list', 'log_list'):
            self.assertContains(response, f'href="{reverse(route)}"')


@override_settings(ALLOWED_HOSTS=['testserver'])
class UIPageRegressionTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        from inventory.models import Member, MemberLevel, Sale
        cls.user = User.objects.create_superuser(username='ui-reviewer', password='test-password')
        cls.product = Product.objects.create(
            name='UI product', barcode='ui-product',
            category=Category.objects.create(name='UI category'), price=10, cost=5,
        )
        level = MemberLevel.objects.create(name='UI level', discount=1, points_threshold=0)
        cls.member = Member.objects.create(name='UI member', phone='13900000000', level=level)
        cls.sale = Sale.objects.create(member=cls.member, operator=cls.user, total_amount=10, final_amount=10)
        Sale.objects.create(member=cls.member, operator=cls.user, total_amount=30, final_amount=30)

    def setUp(self):
        self.client.force_login(self.user)

    def test_detail_and_deactivation_pages_render_without_mutating_records(self):
        for route, pk in (
            ('product_detail', self.product.pk), ('product_delete', self.product.pk),
            ('member_delete', self.member.pk),
        ):
            with self.subTest(route=route):
                self.assertEqual(self.client.get(reverse(route, args=[pk])).status_code, 200)
        self.product.refresh_from_db()
        self.member.refresh_from_db()
        self.assertTrue(self.product.is_active)
        self.assertTrue(self.member.is_active)

    def test_member_purchase_summary_and_search(self):
        response = self.client.get(reverse('member_purchases'))
        self.assertEqual(response.status_code, 200)
        stats = list(response.context['member_stats'])
        self.assertEqual(len(stats), 1)
        self.assertEqual(stats[0]['purchase_total'], Decimal('40.00'))
        self.assertEqual(stats[0]['avg_amount'], Decimal('20.00'))
        self.assertContains(response, 'UI member')
        self.assertContains(response, '?member_id=')
        response = self.client.get(reverse('member_purchases'), {'search': '13900000000'})
        self.assertContains(response, 'UI member')
        response = self.client.get(reverse('member_purchases'), {'search': 'no matching member'})
        self.assertEqual(list(response.context['member_stats']), [])

    def test_member_purchase_details_render_orders(self):
        response = self.client.get(reverse('member_purchases'), {'member_id': self.member.pk})
        self.assertContains(response, 'UI member')
        self.assertContains(response, reverse('sale_detail', args=[self.sale.pk]))
        self.assertEqual(response.context['total_amount'], Decimal('40.00'))

    def test_system_maintenance_get_renders_existing_operations(self):
        response = self.client.get(reverse('system_maintenance'))
        self.assertEqual(response.status_code, 200)
        for operation in ('clear_sessions', 'clear_logs', 'optimize_db'):
            self.assertContains(response, f'value="{operation}"')

    def test_backup_confirmation_renders_metadata_and_rejects_unconfirmed_post(self):
        import json
        from pathlib import Path
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as directory, override_settings(BACKUP_ROOT=directory):
            backup = Path(directory) / 'ui_fixture'
            backup.mkdir()
            (backup / 'backup_info.json').write_text(json.dumps({
                'created_at': '2026-10-06T10:00:00', 'created_by': 'ui-reviewer',
                'description': 'Display metadata only', 'includes_media': False,
            }))
            url = reverse('restore_backup', args=['ui_fixture'])
            response = self.client.get(url)
            self.assertContains(response, f'action="{url}"')
            self.assertContains(response, 'name="confirm"')
            self.assertContains(response, '2026-10-06 10:00:00')
            response = self.client.post(url, {})
            self.assertContains(response, '请确认您要恢复备份')
            self.assertTrue(User.objects.filter(pk=self.user.pk).exists())

    def test_product_form_saves_uploaded_image_on_create_and_edit(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from tempfile import TemporaryDirectory
        image_bytes = (
            b'GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff'
            b'!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00'
            b'\x00\x02\x02D\x01\x00;'
        )
        with TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            data = {
                'name': 'Image upload', 'barcode': 'ui-upload-product',
                'category': self.product.category_id, 'price': '10', 'cost': '5',
                'image': SimpleUploadedFile('created.gif', image_bytes, content_type='image/gif'),
                'is_active': 'on',
            }
            response = self.client.post(reverse('product_create'), data)
            self.assertEqual(response.status_code, 302)
            product = Product.objects.get(barcode='ui-upload-product')
            self.assertTrue(product.image.name.endswith('created.gif'))
            data['image'] = SimpleUploadedFile('edited.gif', image_bytes, content_type='image/gif')
            response = self.client.post(reverse('product_edit', args=[product.pk]), data)
            self.assertEqual(response.status_code, 302)
            product.refresh_from_db()
            self.assertTrue(product.image.name.endswith('edited.gif'))

    def test_report_charts_load_library_and_report_names_remain_visible(self):
        for route in ('sales_trend_report', 'top_products_report', 'inventory_turnover_report',
                      'profit_report', 'recharge_report', 'operation_log_report'):
            with self.subTest(route=route):
                response = self.client.get(reverse(route))
                self.assertContains(response, 'inventory/vendor/chart.umd.js')
                self.assertContains(response, 'class="report-chart"')
        response = self.client.get(reverse('reports_index'))
        self.assertContains(response, 'class="card__title"', count=8)
        self.assertNotContains(response, '<h2 class="page-title visually-hidden">')

    def test_report_dates_are_iso_in_chinese_locale(self):
        from django.utils import translation
        from inventory.forms import DateRangeForm
        with translation.override('zh-hans'):
            form = DateRangeForm()
            for name in ('start_date', 'end_date'):
                self.assertRegex(str(form[name]), r'value="\d{4}-\d{2}-\d{2}"')

    def test_dashboard_counts_sales_after_local_midnight(self):
        from datetime import datetime, timezone as datetime_timezone
        from unittest.mock import patch
        from django.utils import timezone
        from inventory.models import Sale

        instant = datetime(2026, 10, 6, 17, 0, tzinfo=datetime_timezone.utc)
        with timezone.override('Asia/Shanghai'), patch('django.utils.timezone.now', return_value=instant):
            Sale.objects.create(operator=self.user, status='COMPLETED', total_amount=12, final_amount=12)
            Sale.objects.create(operator=self.user, status='CANCELLED', total_amount=99, final_amount=99)
            response = self.client.get(reverse('index'))
        self.assertEqual(response.context['today_sales_amount'], Decimal('12.00'))
        self.assertEqual(response.context['today_sales'], 1)
