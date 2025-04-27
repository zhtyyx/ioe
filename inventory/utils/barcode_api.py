"""
条码生成工具函数 - 不依赖于barcode库的替代实现
"""
import io
import os
import uuid
from PIL import Image, ImageDraw, ImageFont
import qrcode
from decimal import Decimal


def draw_code128_barcode(text, height=100, thickness=3, quiet_zone=10):
    """
    绘制Code 128条码的简单实现
    
    参数:
        text: 条码文本
        height: 条码高度
        thickness: 条码线条粗细
        quiet_zone: 条码两侧的空白区域
        
    返回:
        PIL.Image: 条码图片
    """
    # 由于没有barcode库，我们用黑色矩形模拟条码图案
    # 实际项目中应使用专业库或在这里实现完整的Code 128编码算法
    
    # 创建一个白色图片
    width = len(text) * 10 * thickness + 2 * quiet_zone
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    
    # 在空白区域中间处绘制交替的黑条
    x = quiet_zone
    for char in text:
        # 根据字符ASCII值计算条码宽度（模拟）
        stripe_width = (ord(char) % 3 + 1) * thickness
        
        # 绘制黑条
        draw.rectangle([(x, 0), (x + stripe_width, height)], fill='black')
        x += stripe_width + thickness  # 条之间的空白
    
    # 尝试加载字体
    try:
        font_path = os.path.join('static', 'fonts', 'msyh.ttf')
        font = ImageFont.truetype(font_path, 12)
    except IOError:
        font = ImageFont.load_default()
    
    # 在条码下方显示文本
    text_width = draw.textlength(text, font=font)
    draw.text(((width - text_width) / 2, height - 15), text, fill='black', font=font)
    
    return img


def generate_product_barcode_alt(product, price=None):
    """
    生成商品条码图片 (替代实现)
    
    参数:
        product: 商品对象
        price: 显示的价格
        
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
    
    try:
        # 生成条码
        barcode_img = draw_code128_barcode(barcode_content, height=80)
        
        # 创建包含商品信息的完整图片
        width, height = barcode_img.size
        new_height = height + 100  # 添加额外空间用于显示商品信息
        
        # 创建新图片
        complete_img = Image.new('RGB', (width, new_height), color='white')
        complete_img.paste(barcode_img, (0, 0))
        
        # 添加商品信息
        draw = ImageDraw.Draw(complete_img)
        
        # 尝试加载字体
        try:
            font_path = os.path.join('static', 'fonts', 'msyh.ttf')
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
        
    except Exception as e:
        # 生成错误时的默认图片
        error_img = Image.new('RGB', (300, 150), color='white')
        draw = ImageDraw.Draw(error_img)
        draw.text((10, 10), f"条码生成错误: {str(e)}", fill='black')
        draw.text((10, 30), f"商品: {product.name}", fill='black')
        draw.text((10, 50), f"条码: {barcode_content}", fill='black')
        return error_img


def generate_batch_barcode_alt(batch):
    """
    生成批次条码图片 (替代实现)
    
    参数:
        batch: 批次对象
        
    返回:
        PIL.Image: 条码图片对象
    """
    # 生成批次编号条码
    batch_code = f"B{batch.id:06d}"
    
    try:
        # 生成条码
        barcode_img = draw_code128_barcode(batch_code, height=80)
        
        # 创建包含批次信息的完整图片
        width, height = barcode_img.size
        new_height = height + 100  # 添加额外空间用于显示批次信息
        
        # 创建新图片
        complete_img = Image.new('RGB', (width, new_height), color='white')
        complete_img.paste(barcode_img, (0, 0))
        
        # 添加批次信息
        draw = ImageDraw.Draw(complete_img)
        
        # 尝试加载字体
        try:
            font_path = os.path.join('static', 'fonts', 'msyh.ttf')
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
        
    except Exception as e:
        # 生成错误时的默认图片
        error_img = Image.new('RGB', (300, 150), color='white')
        draw = ImageDraw.Draw(error_img)
        draw.text((10, 10), f"条码生成错误: {str(e)}", fill='black')
        draw.text((10, 30), f"批次: {batch.batch_number}", fill='black')
        draw.text((10, 50), f"商品: {batch.product.name}", fill='black')
        return error_img 