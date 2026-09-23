from decimal import Decimal

from django.contrib.auth.models import Permission, User
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from inventory.models import (
    Category, Inventory, Product, ProductBatch, ProductImage, Sale, SaleItem,
)


class ProductDetailTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='detail-viewer')
        cls.product = Product.objects.create(
            name='详情测试商品', barcode='DETAIL-001',
            category=Category.objects.create(name='详情测试分类'),
            price=Decimal('19.90'), cost=Decimal('8.50'),
            description='<script>alert(1)</script>\n商品说明',
            color='blue', size='M',
        )

    def setUp(self):
        self.client.force_login(self.user)
        self.url = reverse('product_detail', args=[self.product.pk])

    def test_empty_product_renders_without_creating_stock(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventory/product/product_detail.html')
        for text in ('详情测试商品', 'DETAIL-001', '详情测试分类', '19.90',
                     '8.50', '蓝色', '暂无库存记录', '暂无商品图片',
                     '暂无商品批次', '暂无销售记录'):
            self.assertContains(response, text)
        self.assertContains(response, '&lt;script&gt;alert(1)&lt;/script&gt;')
        self.assertNotContains(response, '<script>alert(1)</script>')
        self.assertFalse(Inventory.objects.filter(product=self.product).exists())
        self.assertNotContains(response, reverse('inventory_in') + '?product_id=')
        self.assertContains(response, reverse('product_list'))
        self.assertContains(response, reverse('product_edit', args=[self.product.pk]))

    def test_populated_product_shows_related_records_without_writes(self):
        self.user.user_permissions.add(Permission.objects.get(codename='change_inventory'))
        Inventory.objects.create(product=self.product, quantity=5, warning_level=10)
        self.product.image = 'products/detail-main.jpg'
        self.product.save(update_fields=['image'])
        photo = ProductImage.objects.create(
            product=self.product, image='products/detail-side.jpg', alt_text='商品侧面',
        )
        ProductBatch.objects.create(product=self.product, batch_number='DETAIL-BATCH', quantity=5)
        sale = Sale.objects.create(operator=self.user, total_amount=0, status='COMPLETED')
        SaleItem.objects.create(
            product=self.product, sale=sale, quantity=2,
            price=Decimal('19.90'), actual_price=Decimal('18.00'),
        )
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        for text in ('库存不足，请及时补货', 'DETAIL-BATCH', '商品侧面', '36.00', '已完成'):
            self.assertContains(response, text)
        self.assertContains(response, self.product.image.url)
        self.assertContains(response, photo.image.url)
        self.assertContains(response, reverse('sale_detail', args=[sale.pk]))
        for route in ('inventory_in', 'inventory_out', 'inventory_adjust'):
            self.assertContains(response, reverse(route) + f'?product_id={self.product.pk}')
        self.assertFalse([
            query['sql'] for query in queries
            if query['sql'].lstrip().upper().startswith(('INSERT ', 'UPDATE ', 'DELETE '))
        ])
        self.assertEqual(Inventory.objects.get(product=self.product).quantity, 3)

    def test_recent_sales_are_limited_to_ten_for_this_product(self):
        Inventory.objects.create(product=self.product, quantity=20)
        sales = []
        for _ in range(11):
            sale = Sale.objects.create(operator=self.user, total_amount=0)
            SaleItem.objects.create(
                product=self.product, sale=sale, quantity=1,
                price=self.product.price, actual_price=self.product.price,
            )
            sales.append(sale)
        other = Product.objects.create(
            name='另一商品', barcode='DETAIL-OTHER', category=self.product.category,
            price=1, cost=0,
        )
        Inventory.objects.create(product=other, quantity=1)
        other_sale = Sale.objects.create(operator=self.user, total_amount=0)
        SaleItem.objects.create(product=other, sale=other_sale, quantity=1, price=1, actual_price=1)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item.sale_id for item in response.context['sales_history']],
            [sale.pk for sale in reversed(sales[1:])],
        )
        self.assertNotContains(response, f'href="{reverse("sale_detail", args=[other_sale.pk])}"')

    def test_english_empty_state_and_inactive_status(self):
        self.product.is_active = False
        self.product.save(update_fields=['is_active'])
        Inventory.objects.create(product=self.product, quantity=0)

        response = self.client.get(self.url, HTTP_ACCEPT_LANGUAGE='en')

        for text in ('Product Details', 'Inactive', 'Current Stock', 'Low stock',
                     'No product images yet', 'No sales records yet'):
            self.assertContains(response, text)
        self.assertNotContains(response, 'No inventory record yet')

    def test_missing_product_returns_404(self):
        self.assertEqual(self.client.get(reverse('product_detail', args=[999999])).status_code, 404)

    def test_anonymous_user_must_login(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('next=' + self.url, response.url)
