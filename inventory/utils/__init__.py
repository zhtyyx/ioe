"""工具函数包，提供各种辅助功能"""

from .date_utils import get_month_range, get_quarter_range, get_year_range, get_date_range
from .csv_utils import validate_csv, validate_csv_data
from .logging import log_operation
from .query_utils import get_paginated_queryset, build_filter_query
from .view_utils import require_ajax, require_post, get_referer_url, get_int_param
from .image_utils import generate_thumbnail, save_thumbnail, image_to_base64, resize_image, get_image_dimensions
import qrcode  # 添加qrcode导入

# 尝试导入barcode_utils中的函数，如果失败则使用barcode_api中的替代实现
try:
    from .barcode_utils import generate_product_barcode, generate_batch_barcode, generate_qrcode
except ImportError:
    from .barcode_api import generate_product_barcode_alt as generate_product_barcode
    from .barcode_api import generate_batch_barcode_alt as generate_batch_barcode
    # 使用qrcode库的基本功能作为替代
    def generate_qrcode(content, size=10, box_size=10, border=4):
        qr = qrcode.QRCode(
            version=size,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=box_size,
            border=border,
        )
        qr.add_data(content)
        qr.make(fit=True)
        return qr.make_image(fill_color="black", back_color="white")

__all__ = [
    # 日期工具
    'get_month_range', 'get_quarter_range', 'get_year_range', 'get_date_range',
    
    # CSV处理工具
    'validate_csv', 'validate_csv_data',
    
    # 日志工具
    'log_operation',
    
    # 查询工具
    'get_paginated_queryset', 'build_filter_query',
    
    # 视图工具
    'require_ajax', 'require_post', 'get_referer_url', 'get_int_param',
    
    # 图片处理工具
    'generate_thumbnail', 'save_thumbnail', 'image_to_base64', 'resize_image', 'get_image_dimensions',
    
    # 条码工具
    'generate_product_barcode', 'generate_batch_barcode', 'generate_qrcode',
] 