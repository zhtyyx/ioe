from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from decimal import Decimal

from inventory.models import (
    Category, 
    Product, 
    Inventory, 
    InventoryTransaction,
    Member,
    MemberLevel,
    Sale,
    SaleItem,
    InventoryCheck,
    InventoryCheckItem
)

class IntegrationTestCase(TestCase):
    """集成测试基类"""
    
    def setUp(self):
        # 创建测试用户
        self.user = User.objects.create_user(
            username='testuser', 
            password='12345',
            email='test@example.com'
        )
        
        # 创建客户端
        self.client = Client()
        self.client.login(username='testuser', password='12345')
        
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
            discount=95,  # 95%
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

class SaleProcessTest(IntegrationTestCase):
    """测试完整销售流程"""
    
    def test_complete_sale_process(self):
        """测试从创建销售单到添加销售项的完整流程"""
        # 1. 创建销售单
        sale_data = {
            'payment_method': 'cash',
            'member': self.member.id
        }
        
        response = self.client.post(reverse('sale_create'), sale_data)
        self.assertEqual(response.status_code, 302)  # 重定向状态码
        
        # 获取创建的销售单
        sale = Sale.objects.filter(member=self.member).first()
        self.assertIsNotNone(sale)
        
        # 2. 添加销售项
        sale_item_data = {
            'product': self.product.id,
            'quantity': 5,
            'price': self.product.price
        }
        
        response = self.client.post(
            reverse('sale_item_create', args=[sale.id]), 
            sale_item_data
        )
        self.assertEqual(response.status_code, 302)  # 重定向状态码
        
        # 验证销售项创建
        sale_item = SaleItem.objects.filter(sale=sale, product=self.product).first()
        self.assertIsNotNone(sale_item)
        self.assertEqual(sale_item.quantity, 5)
        
        # 验证库存减少
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 95)  # 100 - 5
        
        # 验证交易记录创建
        transaction = InventoryTransaction.objects.filter(
            product=self.product,
            transaction_type='OUT',
            quantity=5
        ).first()
        self.assertIsNotNone(transaction)
        
        # 验证销售单金额更新
        sale.refresh_from_db()
        expected_amount = Decimal('50.00')  # 5 * 10.00
        self.assertEqual(sale.total_amount, expected_amount)

class InventoryCheckProcessTest(IntegrationTestCase):
    """测试完整库存盘点流程"""
    
    def test_complete_inventory_check_process(self):
        """测试从创建盘点单到完成盘点的完整流程"""
        # 1. 创建盘点单
        check_data = {
            'name': '测试盘点',
            'description': '测试盘点描述'
        }
        
        response = self.client.post(reverse('inventory_check_create'), check_data)
        self.assertEqual(response.status_code, 302)  # 重定向状态码
        
        # 获取创建的盘点单
        inventory_check = InventoryCheck.objects.filter(name='测试盘点').first()
        self.assertIsNotNone(inventory_check)
        self.assertEqual(inventory_check.status, 'draft')
        
        # 验证盘点项创建
        check_item = InventoryCheckItem.objects.filter(
            inventory_check=inventory_check,
            product=self.product
        ).first()
        self.assertIsNotNone(check_item)
        self.assertEqual(check_item.system_quantity, 100)
        
        # 2. 开始盘点
        response = self.client.post(reverse('inventory_check_start', args=[inventory_check.id]))
        self.assertEqual(response.status_code, 302)  # 重定向状态码
        
        # 验证盘点单状态更新
        inventory_check.refresh_from_db()
        self.assertEqual(inventory_check.status, 'in_progress')
        
        # 3. 记录盘点结果
        item_data = {
            'actual_quantity': 95,  # 与系统数量不同
            'notes': '测试盘点记录'
        }
        
        response = self.client.post(
            reverse('inventory_check_item_update', args=[inventory_check.id, check_item.id]),
            item_data
        )
        self.assertEqual(response.status_code, 302)  # 重定向状态码
        
        # 验证盘点项更新
        check_item.refresh_from_db()
        self.assertEqual(check_item.actual_quantity, 95)
        self.assertEqual(check_item.notes, '测试盘点记录')
        
        # 4. 完成盘点
        response = self.client.post(reverse('inventory_check_complete', args=[inventory_check.id]))
        self.assertEqual(response.status_code, 302)  # 重定向状态码
        
        # 验证盘点单状态更新
        inventory_check.refresh_from_db()
        self.assertEqual(inventory_check.status, 'completed')
        
        # 5. 审核盘点并调整库存
        approve_data = {
            'adjust_inventory': True
        }
        
        response = self.client.post(
            reverse('inventory_check_approve', args=[inventory_check.id]),
            approve_data
        )
        self.assertEqual(response.status_code, 302)  # 重定向状态码
        
        # 验证盘点单状态更新
        inventory_check.refresh_from_db()
        self.assertEqual(inventory_check.status, 'approved')
        
        # 验证库存调整
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 95)  # 调整为实际盘点数量