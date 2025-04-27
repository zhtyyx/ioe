from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
import random
from faker import Faker
import datetime

from inventory.models.product import Product, Category, Store
from inventory.models.member import Member, MemberLevel
from inventory.models.sales import Sale, SaleItem
from inventory.models.inventory import Inventory

fake = Faker('zh_CN')

class Command(BaseCommand):
    help = '为库存管理系统生成示例数据'

    def add_arguments(self, parser):
        parser.add_argument('--categories', type=int, default=10, help='生成的商品分类数量')
        parser.add_argument('--products', type=int, default=100, help='生成的商品数量')
        parser.add_argument('--members', type=int, default=30, help='生成的会员数量')
        parser.add_argument('--sales', type=int, default=50, help='生成的销售记录数量')
        parser.add_argument('--clean', action='store_true', help='是否在生成前清除现有数据')

    def handle(self, *args, **options):
        num_categories = options['categories']
        num_products = options['products']
        num_members = options['members']
        num_sales = options['sales']
        clean = options['clean']

        if clean:
            self.clean_database()
            self.stdout.write(self.style.SUCCESS('已清除现有数据'))

        try:
            with transaction.atomic():
                # 确保有管理员用户
                admin_user, created = User.objects.get_or_create(
                    username='admin',
                    defaults={
                        'is_staff': True,
                        'is_superuser': True,
                        'email': 'admin@example.com',
                    }
                )
                if created:
                    admin_user.set_password('admin')
                    admin_user.save()
                    self.stdout.write(self.style.SUCCESS('已创建管理员用户'))

                # 创建会员等级
                levels = self.create_member_levels()
                self.stdout.write(self.style.SUCCESS(f'已创建 {len(levels)} 个会员等级'))

                # 创建商品分类
                categories = self.create_categories(num_categories)
                self.stdout.write(self.style.SUCCESS(f'已创建 {len(categories)} 个商品分类'))

                # 创建商品
                products = self.create_products(categories, num_products)
                self.stdout.write(self.style.SUCCESS(f'已创建 {len(products)} 个商品'))

                # 创建会员
                members = self.create_members(levels, num_members, admin_user)
                self.stdout.write(self.style.SUCCESS(f'已创建 {len(members)} 个会员'))

                # 创建销售记录
                sales = self.create_sales(products, members, num_sales, admin_user)
                self.stdout.write(self.style.SUCCESS(f'已创建 {len(sales)} 个销售记录'))

                self.stdout.write(self.style.SUCCESS('示例数据生成完成!'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'生成示例数据时出错: {e}'))

    def clean_database(self):
        """清除现有数据"""
        SaleItem.objects.all().delete()
        Sale.objects.all().delete()
        
        # 先删除所有会员记录，而不仅仅是测试会员
        Member.objects.all().delete()
        User.objects.filter(username__startswith='member_').delete()
        
        # 先删除引用Product的相关记录
        from inventory.models.inventory import InventoryTransaction
        from inventory.models.inventory_check import InventoryCheckItem
        InventoryTransaction.objects.all().delete()
        InventoryCheckItem.objects.all().delete()
        
        Inventory.objects.all().delete()
        Product.objects.all().delete()
        Category.objects.all().delete()
        MemberLevel.objects.all().delete()

    def create_member_levels(self):
        """创建会员等级"""
        levels_data = [
            {'name': '普通会员', 'discount': Decimal('0.95'), 'points_threshold': 0, 'color': '#808080', 'priority': 1, 'is_default': True},
            {'name': '银卡会员', 'discount': Decimal('0.90'), 'points_threshold': 1000, 'color': '#C0C0C0', 'priority': 2},
            {'name': '金卡会员', 'discount': Decimal('0.85'), 'points_threshold': 3000, 'color': '#FFD700', 'priority': 3},
            {'name': '钻石会员', 'discount': Decimal('0.80'), 'points_threshold': 10000, 'color': '#B9F2FF', 'priority': 4},
        ]
        
        levels = []
        for data in levels_data:
            level, created = MemberLevel.objects.get_or_create(
                name=data['name'],
                defaults=data
            )
            levels.append(level)
        return levels

    def create_categories(self, num_categories):
        """创建商品分类"""
        category_names = [
            '手机数码', '电脑办公', '家用电器', '食品饮料', 
            '服装鞋帽', '美妆护肤', '母婴用品', '家居家装',
            '玩具乐器', '运动户外', '图书音像', '珠宝首饰',
            '汽车用品', '医药保健', '宠物用品'
        ]
        
        categories = []
        for i in range(min(num_categories, len(category_names))):
            name = category_names[i]
            category, created = Category.objects.get_or_create(
                name=name,
                defaults={
                    'description': f'{name}分类商品',
                    'is_active': True,
                }
            )
            categories.append(category)
        return categories

    def create_products(self, categories, num_products):
        """创建商品"""
        products = []
        colors = ['红色', '蓝色', '黑色', '白色', '灰色', '绿色', '黄色', '紫色']
        sizes = ['S', 'M', 'L', 'XL', 'XXL', '均码', '35', '36', '37', '38', '39', '40', '41', '42']
        
        for i in range(num_products):
            category = random.choice(categories)
            price = Decimal(str(round(random.uniform(10, 2000), 2)))
            cost = price * Decimal(str(round(random.uniform(0.5, 0.8), 2)))
            
            barcode = f'69{random.randint(10000000, 99999999)}'
            
            # 根据不同分类生成不同类型的商品名称
            if category.name == '手机数码':
                name = f"{random.choice(['华为', '小米', '苹果', 'OPPO', 'vivo'])} {random.choice(['Pro', 'Max', 'Ultra', 'Lite'])} {random.randint(5, 20)}"
            elif category.name == '电脑办公':
                name = f"{random.choice(['联想', '戴尔', '惠普', '华硕', '苹果'])} {random.choice(['笔记本', '台式机', '平板', '打印机', '显示器'])}"
            elif category.name == '服装鞋帽':
                name = f"{random.choice(['潮流', '时尚', '休闲', '运动', '经典'])} {random.choice(['T恤', '衬衫', '外套', '裙子', '裤子', '鞋'])}"
            else:
                name = f"{category.name}商品{i+1}"
            
            color = random.choice(colors)
            size = random.choice(sizes)
            
            product, created = Product.objects.get_or_create(
                barcode=barcode,
                defaults={
                    'name': name,
                    'category': category,
                    'description': f'{name}的详细描述',
                    'price': price,
                    'cost': cost,
                    'specification': f'{random.choice(["标准", "豪华", "经济", "高级"])}规格',
                    'manufacturer': fake.company(),
                    'color': color,
                    'size': size,
                    'is_active': True,
                }
            )
            
            if created:
                # 创建库存
                inventory, _ = Inventory.objects.get_or_create(
                    product=product,
                    defaults={
                        'quantity': random.randint(10, 100),
                        'warning_level': random.randint(5, 15),
                    }
                )
                products.append(product)
        
        return products

    def create_members(self, levels, num_members, admin_user):
        """创建会员"""
        members = []
        gender_choices = ['M', 'F', 'O']
        
        for i in range(num_members):
            username = f'member_{i+1}'
            # 检查用户是否已存在
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': fake.email(),
                    'first_name': fake.first_name(),
                    'last_name': fake.last_name(),
                    'is_staff': False,
                    'is_active': True,
                }
            )
            
            if created:
                user.set_password('password')
                user.save()
            
            # 根据点数阈值选择合适的会员等级
            points = random.randint(0, 15000)
            suitable_level = levels[0]  # 默认为最低等级
            
            for level in levels:
                if points >= level.points_threshold:
                    if level.priority > suitable_level.priority:
                        suitable_level = level
            
            member, created = Member.objects.get_or_create(
                user=user,
                defaults={
                    'name': fake.name(),
                    'phone': fake.phone_number(),
                    'gender': random.choice(gender_choices),
                    'birthday': fake.date_of_birth(minimum_age=18, maximum_age=70),
                    'level': suitable_level,
                    'points': points,
                    'total_spend': Decimal(str(random.randint(0, 20000))),
                    'purchase_count': random.randint(0, 30),
                    'balance': Decimal(str(random.randint(0, 5000))),
                    'is_recharged': random.choice([True, False]),
                    'member_id': f'M{random.randint(100000, 999999)}',
                    'email': fake.email(),
                    'address': fake.address(),
                    'notes': '系统生成的会员',
                    'is_active': True,
                    'created_by': admin_user,
                    'updated_by': admin_user,
                }
            )
            
            if created:
                members.append(member)
        
        return members

    def create_sales(self, products, members, num_sales, admin_user):
        """创建销售记录"""
        sales = []
        payment_methods = ['cash', 'wechat', 'alipay', 'card', 'balance']
        
        # 生成过去6个月的销售数据
        end_date = timezone.now()
        start_date = end_date - datetime.timedelta(days=180)
        
        for i in range(num_sales):
            # 随机销售日期
            sale_date = start_date + datetime.timedelta(
                seconds=random.randint(0, int((end_date - start_date).total_seconds()))
            )
            
            # 随机选择会员或无会员
            member = random.choice([None] + members) if random.random() < 0.8 else None
            
            # 创建销售记录 - 使用当前模型字段
            sale = Sale.objects.create(
                member=member,
                total_amount=Decimal('0.00'),  # 后续更新
                discount_amount=Decimal('0.00'),  # 后续更新
                final_amount=Decimal('0.00'),  # 后续更新
                payment_method=random.choice(payment_methods),
                operator=admin_user,
                remark='系统生成的销售记录'
            )
            
            # 添加1到5个商品到销售记录
            num_items = random.randint(1, 5)
            sale_products = random.sample(products, min(num_items, len(products)))
            
            for product in sale_products:
                quantity = random.randint(1, 3)
                price = product.price
                
                # 应用会员折扣
                actual_price = price
                if member:
                    actual_price = price * member.level.discount
                
                # 创建销售项目
                SaleItem.objects.create(
                    sale=sale,
                    product=product,
                    quantity=quantity,
                    price=price,
                    actual_price=actual_price,
                )
            
            # 更新销售总额
            sale.update_total_amount()
            
            # 根据会员折扣计算折扣金额
            if member:
                discount_rate = 1 - member.level.discount
                sale.discount_amount = sale.total_amount * discount_rate
                sale.final_amount = sale.total_amount - sale.discount_amount
                sale.save()
                
                # 累加会员积分和消费信息
                points_earned = int(sale.final_amount)
                sale.points_earned = points_earned
                sale.save()
                
                member.points += points_earned
                member.total_spend += sale.final_amount
                member.purchase_count += 1
                
                # 检查是否需要升级会员等级
                current_level = member.level
                available_levels = MemberLevel.objects.filter(
                    points_threshold__lte=member.points
                ).order_by('-priority')
                
                if available_levels.exists() and available_levels.first().priority > current_level.priority:
                    member.level = available_levels.first()
                
                member.save()
            
            sales.append(sale)
        
        return sales 