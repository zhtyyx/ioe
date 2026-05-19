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
    MemberTransaction,
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

    def _sale_post_data(self, *, payment_method='cash', quantity='1', price='10.00'):
        return {
            'payment_method': payment_method,
            'member': self.member.id,
            'products[0][id]': self.product.id,
            'products[0][quantity]': quantity,
            'products[0][price]': price,
            'total_amount': str(Decimal(price) * Decimal(quantity)),
            'discount_amount': '0.00',
            'final_amount': str(Decimal(price) * Decimal(quantity)),
        }
    
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
        sale_data = self._sale_post_data(payment_method='cash')
        
        response = self.client.post(reverse('sale_create'), sale_data)
        
        # 验证创建销售单
        self.assertTrue(Sale.objects.filter(member=self.member).exists())
        sale = Sale.objects.filter(member=self.member).first()
        
        # 验证重定向到销售详情页面
        self.assertRedirects(response, reverse('sale_detail', args=[sale.id]))

    def test_sale_create_account_payment_deducts_member_balance(self):
        """主收银台选择余额支付时必须扣减会员余额"""
        self.client.login(username='testuser', password='12345')

        response = self.client.post(
            reverse('sale_create'),
            self._sale_post_data(payment_method='account')
        )

        sale = Sale.objects.get(member=self.member)
        self.assertRedirects(response, reverse('sale_detail', args=[sale.id]))

        sale.refresh_from_db()
        self.member.refresh_from_db()
        self.inventory.refresh_from_db()

        self.assertEqual(sale.payment_method, 'balance')
        self.assertEqual(sale.final_amount, Decimal('9.50'))
        self.assertEqual(sale.balance_paid, Decimal('9.50'))
        self.assertEqual(self.member.balance, Decimal('90.50'))
        self.assertEqual(self.inventory.quantity, 99)
        self.assertTrue(
            MemberTransaction.objects.filter(
                member=self.member,
                transaction_type='PURCHASE',
                balance_change=Decimal('-9.50'),
                related_object_id=sale.id,
                related_object_type='Sale'
            ).exists()
        )

    def test_sale_create_balance_payment_rolls_back_when_balance_insufficient(self):
        """余额不足时不得落销售单、销售项或库存扣减"""
        self.client.login(username='testuser', password='12345')
        self.member.balance = Decimal('1.00')
        self.member.save(update_fields=['balance'])

        response = self.client.post(
            reverse('sale_create'),
            self._sale_post_data(payment_method='account')
        )

        self.assertRedirects(response, reverse('sale_create'))
        self.assertFalse(Sale.objects.filter(member=self.member).exists())
        self.assertFalse(SaleItem.objects.exists())
        self.member.refresh_from_db()
        self.inventory.refresh_from_db()
        self.assertEqual(self.member.balance, Decimal('1.00'))
        self.assertEqual(self.inventory.quantity, 100)

    def test_sale_complete_balance_payment_deducts_member_balance(self):
        """旧完成销售路径同样使用原子余额扣减"""
        self.client.login(username='testuser', password='12345')
        sale = Sale.objects.create(
            member=self.member,
            total_amount=Decimal('10.00'),
            discount_amount=Decimal('0.00'),
            final_amount=Decimal('10.00'),
            operator=self.user
        )
        SaleItem.objects.create(
            sale=sale,
            product=self.product,
            quantity=1,
            price=Decimal('10.00'),
            actual_price=Decimal('10.00'),
            subtotal=Decimal('10.00')
        )

        response = self.client.post(
            reverse('sale_complete', args=[sale.id]),
            {
                'payment_method': 'balance',
                'remark': '余额支付'
            }
        )

        self.assertRedirects(response, reverse('sale_detail', args=[sale.id]))
        sale.refresh_from_db()
        self.member.refresh_from_db()

        self.assertEqual(sale.payment_method, 'balance')
        self.assertEqual(sale.final_amount, Decimal('9.50'))
        self.assertEqual(sale.balance_paid, Decimal('9.50'))
        self.assertEqual(self.member.balance, Decimal('90.50'))


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
