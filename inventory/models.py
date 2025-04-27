# 这是一个过渡文件，用于确保向后兼容性
# 模型现在已经重构到inventory/models/目录下的各个文件中

# 从重构后的模型结构中导入所有模型
from inventory.models.product import (
    Product, Category, Color, Size, Store
)

from inventory.models.inventory import (
    Inventory, InventoryTransaction, 
    check_inventory, update_inventory, StockAlert
)

from inventory.models.inventory_check import (
    InventoryCheck, InventoryCheckItem
)

from inventory.models.member import (
    Member, MemberLevel, RechargeRecord
)

from inventory.models.sales import (
    Sale, SaleItem
)

from inventory.models.common import (
    OperationLog
)

# 警告：这个文件将在重构完成后删除
# 请直接从inventory.models导入模型，例如:
# from inventory.models import Product