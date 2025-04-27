"""
图片处理工具函数
"""
from io import BytesIO
from PIL import Image, ImageOps
import os


def generate_thumbnail(image_file, size=(300, 300), format='JPEG', quality=85):
    """
    生成图片缩略图
    
    参数:
        image_file: 原始图片文件对象(Django UploadedFile或文件路径)
        size: 缩略图尺寸，格式为(宽, 高)
        format: 图片格式('JPEG', 'PNG'等)
        quality: 图片质量(1-100)
        
    返回:
        PIL.Image: 处理后的缩略图对象
    """
    # 如果是文件路径，打开文件
    if isinstance(image_file, str):
        img = Image.open(image_file)
    # 如果是Django的InMemoryUploadedFile或TemporaryUploadedFile
    elif hasattr(image_file, 'read'):
        if hasattr(image_file, 'seek'):
            image_file.seek(0)
        img = Image.open(image_file)
    else:
        # 已经是PIL.Image对象
        img = image_file
    
    # 转换为RGB模式（去除透明通道）
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    # 生成缩略图
    img.thumbnail(size, Image.Resampling.LANCZOS)
    
    # 确保缩略图是指定的尺寸（通过填充）
    thumb = ImageOps.fit(img, size, Image.Resampling.LANCZOS)
    
    return thumb


def save_thumbnail(image, path, format='JPEG', quality=85):
    """
    保存缩略图到指定路径
    
    参数:
        image: PIL.Image对象
        path: 保存路径
        format: 图片格式
        quality: 图片质量
        
    返回:
        str: 保存后的路径
    """
    # 确保目录存在
    directory = os.path.dirname(path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
    
    # 保存图片
    image.save(path, format=format, quality=quality)
    
    return path


def image_to_base64(image, format='JPEG', quality=85):
    """
    将图片转换为base64编码
    
    参数:
        image: PIL.Image对象
        format: 图片格式
        quality: 图片质量
        
    返回:
        str: base64编码的图片数据
    """
    import base64
    
    buffered = BytesIO()
    image.save(buffered, format=format, quality=quality)
    img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
    
    return f"data:image/{format.lower()};base64,{img_str}"


def resize_image(image_file, size, format='JPEG', quality=85):
    """
    调整图片大小
    
    参数:
        image_file: 原始图片文件对象或路径
        size: 新尺寸，格式为(宽, 高)
        format: 图片格式
        quality: 图片质量
        
    返回:
        PIL.Image: 调整大小后的图片
    """
    # 如果是文件路径，打开文件
    if isinstance(image_file, str):
        img = Image.open(image_file)
    # 如果是Django的InMemoryUploadedFile或TemporaryUploadedFile
    elif hasattr(image_file, 'read'):
        if hasattr(image_file, 'seek'):
            image_file.seek(0)
        img = Image.open(image_file)
    else:
        # 已经是PIL.Image对象
        img = image_file
    
    # 转换为RGB模式（去除透明通道）
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    # 调整大小
    resized_img = img.resize(size, Image.Resampling.LANCZOS)
    
    return resized_img


def get_image_dimensions(image_file):
    """
    获取图片尺寸
    
    参数:
        image_file: 图片文件对象或路径
        
    返回:
        tuple: (宽, 高)
    """
    # 如果是文件路径，打开文件
    if isinstance(image_file, str):
        img = Image.open(image_file)
    # 如果是Django的InMemoryUploadedFile或TemporaryUploadedFile
    elif hasattr(image_file, 'read'):
        if hasattr(image_file, 'seek'):
            image_file.seek(0)
        img = Image.open(image_file)
    else:
        # 已经是PIL.Image对象
        img = image_file
    
    return img.size 