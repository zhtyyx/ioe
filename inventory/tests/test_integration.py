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
            discount=Decimal('0.95'),
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
        response = self.client.post(reverse('sale_create'), {
            'payment_method': 'cash',
            'member': self.member.pk,
            'products[0][id]': self.product.pk,
            'products[0][quantity]': '5',
            'products[0][price]': '10.00',
            'total_amount': '1.00',
            'discount_amount': '0.00',
            'final_amount': '1.00',
        })

        sale = Sale.objects.get(member=self.member)
        self.assertRedirects(response, reverse('sale_detail', args=[sale.pk]))
        self.assertEqual(sale.operator, self.user)
        self.assertEqual(sale.total_amount, Decimal('50.00'))
        self.assertEqual(sale.discount_amount, Decimal('2.50'))
        self.assertEqual(sale.final_amount, Decimal('47.50'))
        item = SaleItem.objects.get(sale=sale)
        self.assertEqual(item.product, self.product)
        self.assertEqual(item.quantity, 5)
        self.assertEqual(item.price, Decimal('10.00'))
        self.assertEqual(item.subtotal, Decimal('50.00'))

        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 95)
        movement = InventoryTransaction.objects.get(product=self.product)
        self.assertEqual(movement.transaction_type, 'OUT')
        self.assertEqual(movement.quantity, 5)
        self.assertEqual(movement.operator, self.user)
        self.member.refresh_from_db()
        self.assertEqual(self.member.balance, Decimal('100.00'))
        self.assertEqual(self.member.total_spend, Decimal('47.50'))
        self.assertEqual(self.member.purchase_count, 1)
        self.assertEqual(self.member.points, sale.points_earned)


class InventoryCheckProcessTest(IntegrationTestCase):
    """测试完整库存盘点流程"""
    
    def setUp(self):
        super().setUp()
        self.user.is_superuser = True
        self.user.save(update_fields=['is_superuser'])

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
        approve_data = {'adjust_inventory': 'on'}
        response = self.client.post(
            reverse('inventory_check_approve', args=[inventory_check.pk]), approve_data,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('confirm', response.context['form'].errors)
        inventory_check.refresh_from_db()
        self.inventory.refresh_from_db()
        self.assertEqual(inventory_check.status, 'completed')
        self.assertEqual(self.inventory.quantity, 100)
        self.assertFalse(InventoryTransaction.objects.exists())
        approve_data['confirm'] = 'on'
        
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
        self.assertEqual(self.inventory.quantity, 95)
        self.assertEqual(inventory_check.approved_by, self.user)
        self.assertIsNotNone(inventory_check.approved_at)
        movement = InventoryTransaction.objects.get(product=self.product)
        self.assertEqual(movement.transaction_type, 'ADJUST')
        self.assertEqual(movement.operator, self.user)
