import os
import tempfile

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User, Permission, Group
from decimal import Decimal

from inventory.models import (
    Category, 
    Product, 
    Inventory, 
    InventoryTransaction,
    Member,
    MemberLevel,
    Sale,
    SaleItem
)

class ViewTestCase(TestCase):
    """视图测试的基类"""
    
    def setUp(self):
        # 创建测试用户
        self.user = User.objects.create_user(
            username='testuser', 
            password='12345',
            email='test@example.com'
        )
        
        # 创建测试管理员
        self.admin = User.objects.create_user(
            username='admin', 
            password='admin123',
            email='admin@example.com',
            is_staff=True
        )
        
        # 创建客户端
        self.client = Client()
        
        # 创建测试分类
        self.category = Category.objects.create(
            name='测试分类',
            description='测试分类描述'
        )
        
        # 创建测试商品
        self.product = Product.objects.create(
            barcode='1234567890',
            name='测试商品',
            category=self.category,
            description='测试商品描述',
            price=Decimal('10.00'),
            cost=Decimal('5.00')
        )
        
        # 创建库存记录
        self.inventory = Inventory.objects.create(
            product=self.product,
            quantity=100,
            warning_level=10
        )
        
        # 创建会员等级
        self.member_level = MemberLevel.objects.create(
            name='普通会员',
            discount=Decimal('0.95'),  # 95%
            points_threshold=0,
            color='#FF5733'
        )
        
        # 创建会员
        self.member = Member.objects.create(
            name='测试会员',
            phone='13800138000',
            level=self.member_level,
            balance=Decimal('100.00'),
            points=0
        )

class ProductViewTest(ViewTestCase):
    """测试商品相关视图"""
    
    def test_product_list_view(self):
        """测试商品列表视图"""
        # 登录
        self.client.login(username='testuser', password='12345')
        
        # 访问商品列表页面
        response = self.client.get(reverse('product_list'))
        
        # 验证响应
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventory/product_list.html')
        self.assertContains(response, '测试商品')
        
    def test_product_create_view(self):
        """测试创建商品视图"""
        # 登录
        self.client.login(username='testuser', password='12345')
        
        # 访问创建商品页面
        response = self.client.get(reverse('product_create'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventory/product_form.html')
        
        # 提交创建商品表单
        product_data = {
            'barcode': '9876543210',
            'name': '新测试商品',
            'category': self.category.id,
            'description': '新测试商品描述',
            'price': '15.00',
            'cost': '7.50'
        }
        
        response = self.client.post(reverse('product_create'), product_data)
        
        # 验证重定向
        self.assertRedirects(response, reverse('product_list'))
        
        # 验证商品创建
        self.assertTrue(Product.objects.filter(barcode='9876543210').exists())

class InventoryViewTest(ViewTestCase):
    """测试库存相关视图"""
    
    def test_inventory_list_view(self):
        """测试库存列表视图"""
        # 登录
        self.client.login(username='testuser', password='12345')
        
        # 访问库存列表页面
        response = self.client.get(reverse('inventory_list'))
        
        # 验证响应
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventory/inventory_list.html')
        self.assertContains(response, '测试商品')
        
    def test_inventory_transaction_create_view(self):
        """测试创建库存交易视图"""
        # 登录
        self.client.login(username='testuser', password='12345')
        
        # 访问创建库存交易页面
        response = self.client.get(reverse('inventory_create'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventory/inventory_form.html')
        
        # 提交创建库存交易表单
        transaction_data = {
            'product': self.product.id,
            'quantity': '50',
            'notes': '测试入库'
        }
        
        response = self.client.post(reverse('inventory_create'), transaction_data)
        
        # 验证重定向
        self.assertRedirects(response, reverse('inventory_list'))
        
        # 验证库存交易创建和库存更新
        self.assertTrue(InventoryTransaction.objects.filter(product=self.product, quantity=50).exists())
        
        # 刷新库存对象
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 150)  # 100 + 50


class MemberApiViewTest(ViewTestCase):
    """测试会员相关 API 视图"""

    def test_member_search_requires_login(self):
        """未登录用户不能通过手机号查询会员隐私信息"""
        url = reverse('member_search_by_phone', args=[self.member.phone])

        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response['Location'])
        self.assertIn('next=', response['Location'])

    def test_member_search_returns_data_for_authenticated_user(self):
        """登录用户仍可使用会员搜索 API"""
        self.client.login(username='testuser', password='12345')
        url = reverse('member_search_by_phone', args=[self.member.phone])

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['member_id'], self.member.id)
        self.assertEqual(data['member_phone'], self.member.phone)


class SaleViewTest(ViewTestCase):
    """测试销售相关视图"""
    
    def test_sale_list_view(self):
        """测试销售列表视图"""
        # 登录
        self.client.login(username='testuser', password='12345')
        
        # 访问销售列表页面
        response = self.client.get(reverse('sale_list'))
        
        # 验证响应
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventory/sale_list.html')
        
    def test_sale_create_view(self):
        """测试创建销售视图"""
        # 登录
        self.client.login(username='testuser', password='12345')
        
        # 访问创建销售页面
        response = self.client.get(reverse('sale_create'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inventory/sale_form.html')
        
        # 提交创建销售表单
        sale_data = {
            'payment_method': 'cash',
            'member': self.member.id
        }
        
        response = self.client.post(reverse('sale_create'), sale_data)
        
        # 验证创建销售单
        self.assertTrue(Sale.objects.filter(member=self.member).exists())
        sale = Sale.objects.filter(member=self.member).first()
        
        # 验证重定向到销售项创建页面
        self.assertRedirects(response, reverse('sale_item_create', args=[sale.id]))

    def test_sale_item_create_decrements_inventory_once(self):
        """添加销售商品时库存只能扣减一次"""
        self.client.login(username='testuser', password='12345')
        sale = Sale.objects.create(
            member=self.member,
            total_amount=Decimal('0.00'),
            final_amount=Decimal('0.00'),
            operator=self.user
        )

        response = self.client.post(reverse('sale_item_create', args=[sale.id]), {
            'product': self.product.id,
            'quantity': '5',
            'price': '10.00',
            'actual_price': '10.00',
        })

        self.assertRedirects(response, reverse('sale_item_create', args=[sale.id]))
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 95)
        self.assertEqual(
            InventoryTransaction.objects.filter(
                product=self.product,
                transaction_type='OUT',
                quantity=5
            ).count(),
            1
        )

    def test_sale_delete_item_handles_sales_without_status(self):
        """删除销售商品不应因 Sale 缺少 status 字段而 500"""
        self.client.login(username='testuser', password='12345')
        sale = Sale.objects.create(
            member=self.member,
            total_amount=Decimal('0.00'),
            final_amount=Decimal('0.00'),
            operator=self.user
        )
        sale_item = SaleItem.objects.create(
            sale=sale,
            product=self.product,
            quantity=5,
            price=Decimal('10.00'),
            actual_price=Decimal('10.00'),
            subtotal=Decimal('50.00')
        )
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 95)

        response = self.client.get(reverse('sale_item_delete', args=[sale.id, sale_item.id]))

        self.assertRedirects(response, reverse('sale_item_create', args=[sale.id]))
        self.assertFalse(SaleItem.objects.filter(pk=sale_item.pk).exists())
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 100)
        sale.refresh_from_db()
        self.assertEqual(sale.total_amount, Decimal('0.00'))

    def test_sale_complete_insufficient_balance_does_not_record_purchase(self):
        """余额不足结算失败时不应增加会员消费统计"""
        self.client.login(username='testuser', password='12345')
        self.member_level.discount = Decimal('1.00')
        self.member_level.save()
        self.member.balance = Decimal('10.00')
        self.member.save()
        sale = Sale.objects.create(
            member=self.member,
            total_amount=Decimal('0.00'),
            final_amount=Decimal('0.00'),
            operator=self.user
        )
        SaleItem.objects.create(
            sale=sale,
            product=self.product,
            quantity=5,
            price=Decimal('10.00'),
            actual_price=Decimal('10.00'),
            subtotal=Decimal('50.00')
        )

        response = self.client.post(reverse('sale_complete', args=[sale.id]), {
            'payment_method': 'balance',
            'remark': '',
        })

        self.assertRedirects(response, reverse('sale_complete', args=[sale.id]))
        self.member.refresh_from_db()
        self.assertEqual(self.member.balance, Decimal('10.00'))
        self.assertEqual(self.member.purchase_count, 0)
        self.assertEqual(self.member.total_spend, Decimal('0.00'))

    def test_sale_complete_balance_payment_updates_balance_atomically(self):
        """余额支付应使用数据库增量扣款并记录余额支付金额"""
        self.client.login(username='testuser', password='12345')
        self.member_level.discount = Decimal('1.00')
        self.member_level.save()
        self.member.balance = Decimal('125.00')
        self.member.save()
        sale = Sale.objects.create(
            member=self.member,
            total_amount=Decimal('0.00'),
            final_amount=Decimal('0.00'),
            operator=self.user
        )
        SaleItem.objects.create(
            sale=sale,
            product=self.product,
            quantity=5,
            price=Decimal('10.00'),
            actual_price=Decimal('10.00'),
            subtotal=Decimal('50.00')
        )

        response = self.client.post(reverse('sale_complete', args=[sale.id]), {
            'payment_method': 'balance',
            'remark': '',
        })

        self.assertRedirects(response, reverse('sale_detail', args=[sale.id]))
        self.member.refresh_from_db()
        self.assertEqual(self.member.balance, Decimal('75.00'))
        self.assertEqual(self.member.purchase_count, 1)
        self.assertEqual(self.member.total_spend, Decimal('50.00'))
        sale.refresh_from_db()
        self.assertEqual(sale.balance_paid, Decimal('50.00'))

    def test_sale_cancel_without_status_does_not_restore_inventory(self):
        """当前 Sale 模型无状态字段时，取消入口不能部分回补库存"""
        self.client.login(username='testuser', password='12345')
        sale = Sale.objects.create(
            member=self.member,
            total_amount=Decimal('0.00'),
            final_amount=Decimal('0.00'),
            operator=self.user
        )
        SaleItem.objects.create(
            sale=sale,
            product=self.product,
            quantity=5,
            price=Decimal('10.00'),
            actual_price=Decimal('10.00'),
            subtotal=Decimal('50.00')
        )
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 95)

        response = self.client.post(reverse('sale_cancel', args=[sale.id]), {'reason': '测试取消'})

        self.assertRedirects(response, reverse('sale_detail', args=[sale.id]))
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 95)


class BackupViewSecurityTest(TestCase):
    """备份管理视图的安全回归测试"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_superuser(
            username='backup-admin',
            password='backup-pass',
            email='backup@example.com'
        )
        self.client.force_login(self.user)

        self.temp_parent = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_parent.cleanup)
        self.backup_root = os.path.join(self.temp_parent.name, 'backups')
        self.temp_dir = os.path.join(self.temp_parent.name, 'temp')
        os.makedirs(self.backup_root, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)

    def test_delete_backup_rejects_parent_directory_traversal(self):
        sentinel_path = os.path.join(self.temp_parent.name, 'keep.txt')
        with open(sentinel_path, 'w', encoding='utf-8') as sentinel:
            sentinel.write('do not delete')

        with self.settings(BACKUP_ROOT=self.backup_root, TEMP_DIR=self.temp_dir):
            response = self.client.post('/system/backup/delete/../', {'confirm': 'on'})

        self.assertRedirects(response, reverse('backup_list'))
        self.assertTrue(os.path.exists(sentinel_path))
        self.assertTrue(os.path.isdir(self.backup_root))
