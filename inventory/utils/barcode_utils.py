"""
条码生成工具函数
"""
import io
import os
from PIL import Image, ImageDraw, ImageFont
import qrcode
import barcode
from barcode.writer import ImageWriter
from decimal import Decimal


def generate_product_barcode(product, price=None, barcode_type='ean13'):
    """
    生成商品条码图片
    
    参数:
        product: 商品对象
        price: 显示的价格，如果为None则使用商品默认零售价
        barcode_type: 条码类型，支持'ean13'、'code128'等
        
    返回:
        PIL.Image: 条码图片对象
    """
    if not price:
        price = product.retail_price
    
    # 获取条码内容
    barcode_content = product.barcode
    if not barcode_content:
        # 如果商品没有条码，使用商品ID作为条码
        barcode_content = f"ID{product.id:08d}"
    
    # 确定条码类型
    if barcode_type == 'ean13' and len(barcode_content) != 13:
        # 如果需要EAN13但条码不是13位，改用CODE128
        barcode_type = 'code128'
    
    try:
        # 生成条码
        barcode_class = barcode.get_barcode_class(barcode_type)
        barcode_image = barcode_class(barcode_content, writer=ImageWriter())
        
        # 渲染条码
        barcode_img = barcode_image.render(
            writer_options={
                'module_width': 0.6,
                'module_height': 15.0,
                'font_size': 10,
                'text_distance': 1.0,
                'quiet_zone': 6.0
            }
        )
        
        # 创建包含商品信息的完整图片
        width, height = barcode_img.size
        new_height = height + 100  # 添加额外空间用于显示商品信息
        
        # 创建新图片
        complete_img = Image.new('RGB', (width, new_height), color='white')
        complete_img.paste(barcode_img, (0, 0))
        
        # 添加商品信息
        draw = ImageDraw.Draw(complete_img)
        
        # 尝试加载字体，如果失败则使用默认字体
        try:
            font_path = os.path.join('static', 'fonts', 'msyh.ttf')  # 微软雅黑字体
            title_font = ImageFont.truetype(font_path, 20)
            info_font = ImageFont.truetype(font_path, 16)
        except IOError:
            # 使用默认字体
            title_font = ImageFont.load_default()
            info_font = ImageFont.load_default()
        
        # 绘制商品名称
        product_name = product.name
        if len(product_name) > 20:
            product_name = product_name[:18] + '...'
        
        # 绘制信息
        draw.text((10, height + 10), product_name, fill='black', font=title_font)
        draw.text((10, height + 40), f"价格: ¥{price:.2f}", fill='black', font=info_font)
        draw.text((10, height + 70), f"规格: {product.specification or '标准'}", fill='black', font=info_font)
        
        return complete_img
        
    except (ValueError, AttributeError) as e:
        # 生成错误时的默认图片
        error_img = Image.new('RGB', (300, 150), color='white')
        draw = ImageDraw.Draw(error_img)
        draw.text((10, 10), f"条码生成错误: {str(e)}", fill='black')
        draw.text((10, 30), f"商品: {product.name}", fill='black')
        draw.text((10, 50), f"条码: {barcode_content}", fill='black')
        return error_img


def generate_batch_barcode(batch, barcode_type='code128'):
    """
    生成批次条码图片
    
    参数:
        batch: 批次对象
        barcode_type: 条码类型
        
    返回:
        PIL.Image: 条码图片对象
    """
    # 生成批次编号条码
    batch_code = f"B{batch.id:06d}"
    
    try:
        # 生成条码
        barcode_class = barcode.get_barcode_class(barcode_type)
        barcode_image = barcode_class(batch_code, writer=ImageWriter())
        
        # 渲染条码
        barcode_img = barcode_image.render(
            writer_options={
                'module_width': 0.6,
                'module_height': 15.0,
                'font_size': 10,
                'text_distance': 1.0,
                'quiet_zone': 6.0
            }
        )
        
        # 创建包含批次信息的完整图片
        width, height = barcode_img.size
        new_height = height + 100  # 添加额外空间用于显示批次信息
        
        # 创建新图片
        complete_img = Image.new('RGB', (width, new_height), color='white')
        complete_img.paste(barcode_img, (0, 0))
        
        # 添加批次信息
        draw = ImageDraw.Draw(complete_img)
        
        # 尝试加载字体，如果失败则使用默认字体
        try:
            font_path = os.path.join('static', 'fonts', 'msyh.ttf')  # 微软雅黑字体
            title_font = ImageFont.truetype(font_path, 20)
            info_font = ImageFont.truetype(font_path, 16)
        except IOError:
            # 使用默认字体
            title_font = ImageFont.load_default()
            info_font = ImageFont.load_default()
        
        # 绘制批次信息
        product_name = batch.product.name
        if len(product_name) > 20:
            product_name = product_name[:18] + '...'
        
        # 绘制信息
        draw.text((10, height + 10), product_name, fill='black', font=title_font)
        draw.text((10, height + 40), f"批次: {batch.batch_number}", fill='black', font=info_font)
        draw.text((10, height + 70), f"生产日期: {batch.production_date.strftime('%Y-%m-%d')}", fill='black', font=info_font)
        
        return complete_img
        
    except (ValueError, AttributeError) as e:
        # 生成错误时的默认图片
        error_img = Image.new('RGB', (300, 150), color='white')
        draw = ImageDraw.Draw(error_img)
        draw.text((10, 10), f"条码生成错误: {str(e)}", fill='black')
        draw.text((10, 30), f"批次: {batch.batch_number}", fill='black')
        draw.text((10, 50), f"商品: {batch.product.name}", fill='black')
        return error_img


def generate_qrcode(content, size=10, box_size=10, border=4):
    """
    生成二维码
    
    参数:
        content: 二维码内容
        size: 二维码大小
        box_size: 每个点的像素大小
        border: 边框宽度
        
    返回:
        PIL.Image: 二维码图片对象
    """
    qr = qrcode.QRCode(
        version=size,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=box_size,
        border=border,
    )
    
    qr.add_data(content)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    return img 