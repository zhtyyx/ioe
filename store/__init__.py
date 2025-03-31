from django.db import transaction
from django.core.exceptions import ValidationError
from inventory.models import Inventory, InventoryTransaction

def update_inventory(product, quantity, transaction_type, operator, notes=''):
    """
    更新商品库存
    :param product: 商品对象
    :param quantity: 数量（正数表示入库，负数表示出库）
    :param transaction_type: 交易类型（IN/OUT/ADJUST）
    :param operator: 操作员
    :param notes: 备注
    """
    with transaction.atomic():
        inventory, created = Inventory.objects.select_for_update().get_or_create(
            product=product,
            defaults={'quantity': 0}
        )

        # 检查库存是否足够（仅出库时）
        if quantity < 0 and inventory.quantity + quantity < 0:
            raise ValidationError('库存不足')

        # 更新库存
        inventory.quantity += quantity
        inventory.save()

        # 创建库存交易记录
        InventoryTransaction.objects.create(
            product=product,
            transaction_type=transaction_type,
            quantity=abs(quantity),  # 保存绝对值
            operator=operator,
            notes=notes
        )

def check_inventory(product, quantity):
    """
    检查商品库存是否足够
    :param product: 商品对象
    :param quantity: 需要的数量
    :return: bool
    """
    try:
        inventory = Inventory.objects.get(product=product)
        return inventory.quantity >= quantity
    except Inventory.DoesNotExist:
        return False