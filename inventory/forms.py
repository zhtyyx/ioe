# 这是一个过渡文件，用于确保向后兼容性
# 表单现在已经重构到inventory/forms/目录下的各个文件中

# 从重构后的表单结构中导入所有表单
from inventory.forms.product_forms import (
    ProductForm, CategoryForm
)

from inventory.forms.inventory_check_forms import (
    InventoryCheckForm, InventoryCheckItemForm, InventoryCheckApproveForm
)

from inventory.forms.member_forms import (
    MemberForm, MemberLevelForm, RechargeForm
)

from inventory.forms.inventory_forms import (
    InventoryTransactionForm
)

from inventory.forms.sales_forms import (
    SaleForm, SaleItemForm
)

from inventory.forms.report_forms import (
    DateRangeForm, TopProductsForm, InventoryTurnoverForm
)

from inventory.forms_batch import (
    BatchProductImportForm, BatchInventoryUpdateForm, ProductBatchDeleteForm
)

# 警告：这个文件将在重构完成后删除
# 请直接从inventory.forms导入表单，例如:
# from inventory.forms import ProductForm