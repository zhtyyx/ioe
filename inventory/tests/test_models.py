from django.test import TestCase
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
    RechargeRecord,
    InventoryCheck,
    InventoryCheckItem
)

class CategoryModelTest(TestCase):
    """测试商品分类模型"""
    
    def setUp(self):
        self.category = Category.objects.create(
            name='测试分类',
            description='测试分类描述'
        )
    
    def test_category_creation(self):
        """测试分类创建"""
        self.assertEqual(self.category.name, '测试分类')
        self.assertEqual(self.category.description, '测试分类描述')
        self.assertTrue(self.category.created_at)
        self.assertTrue(self.category.updated_at)
    
    def test_category_str(self):
        """测试分类字符串表示"""
        self.assertEqual(str(self.category), '测试分类')

class ProductModelTest(TestCase):
    """测试商品模型"""
    
    def setUp(self):
        self.category = Category.objects.create(name='测试分类')
        self.product = Product.objects.create(
            barcode='1234567890',
            name='测试商品',
            category=self.category,
            description='测试商品描述',
            price=Decimal('10.00'),
            cost=Decimal('5.00')
        )
    
    def test_product_creation(self):
        """测试商品创建"""
        self.assertEqual(self.product.barcode, '1234567890')
        self.assertEqual(self.product.name, '测试商品')
        self.assertEqual(self.product.category, self.category)
        self.assertEqual(self.product.description, '测试商品描述')
        self.assertEqual(self.product.price, Decimal('10.00'))
        self.assertEqual(self.product.cost, Decimal('5.00'))
        self.assertTrue(self.product.created_at)
        self.assertTrue(self.product.updated_at)
    
    def test_product_str(self):
        """测试商品字符串表示"""
        self.assertEqual(str(self.product), '测试商品')

class InventoryModelTest(TestCase):
    """测试库存模型"""
    
    def setUp(self):
        self.category = Category.objects.create(name='测试分类')
        self.product = Product.objects.create(
            barcode='1234567890',
            name='测试商品',
            category=self.category,
            price=Decimal('10.00'),
            cost=Decimal('5.00')
        )
        self.inventory = Inventory.objects.create(
            product=self.product,
            quantity=100,
            warning_level=10
        )
    
    def test_inventory_creation(self):
        """测试库存创建"""
        self.assertEqual(self.inventory.product, self.product)
        self.assertEqual(self.inventory.quantity, 100)
        self.assertEqual(self.inventory.warning_level, 10)
        self.assertTrue(self.inventory.created_at)
        self.assertTrue(self.inventory.updated_at)
    
    def test_inventory_str(self):
        """测试库存字符串表示"""
        self.assertEqual(str(self.inventory), f'{self.product.name} - 100')
    
    def test_is_low_stock(self):
        """测试库存预警属性"""
        self.assertFalse(self.inventory.is_low_stock)  # 100 > 10
        
        self.inventory.quantity = 10
        self.inventory.save()
        self.assertTrue(self.inventory.is_low_stock)  # 10 == 10
        
        self.inventory.quantity = 5
        self.inventory.save()
        self.assertTrue(self.inventory.is_low_stock)  # 5 < 10

class InventoryTransactionModelTest(TestCase):
    """测试库存交易记录模型"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.category = Category.objects.create(name='测试分类')
        self.product = Product.objects.create(
            barcode='1234567890',
            name='测试商品',
            category=self.category,
            price=Decimal('10.00'),
            cost=Decimal('5.00')
        )
        self.transaction = InventoryTransaction.objects.create(
            product=self.product,
            transaction_type='IN',
            quantity=50,
            operator=self.user,
            notes='测试入库'
        )
    
    def test_transaction_creation(self):
        """测试交易记录创建"""
        self.assertEqual(self.transaction.product, self.product)
        self.assertEqual(self.transaction.transaction_type, 'IN')
        self.assertEqual(self.transaction.quantity, 50)
        self.assertEqual(self.transaction.operator, self.user)
        self.assertEqual(self.transaction.notes, '测试入库')
        self.assertTrue(self.transaction.created_at)
    
    def test_transaction_str(self):
        """测试交易记录字符串表示"""
        self.assertEqual(str(self.transaction), f'{self.product.name} - 入库 - 50')