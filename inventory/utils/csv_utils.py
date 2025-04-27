"""
CSV文件处理工具函数
"""
import csv
import io


def validate_csv(csv_file, required_headers=None, expected_headers=None, max_rows=1000):
    """
    验证CSV文件的格式和内容
    
    参数:
    - csv_file: 上传的CSV文件对象
    - required_headers: 必填的列标题列表
    - expected_headers: 预期可能存在的列标题列表
    - max_rows: 最大行数限制
    
    返回:
    - dict: 包含验证结果的字典
    """
    if required_headers is None:
        required_headers = []
    if expected_headers is None:
        expected_headers = []
    
    # 重置文件指针
    csv_file.seek(0)
    
    # 读取CSV文件
    try:
        csv_data = csv_file.read().decode('utf-8-sig')  # 处理带BOM的UTF-8文件
    except UnicodeDecodeError:
        try:
            # 尝试其他编码
            csv_file.seek(0)
            csv_data = csv_file.read().decode('gb18030')  # 中文Windows常用编码
        except UnicodeDecodeError:
            return {
                'valid': False,
                'errors': '无法解析CSV文件编码，请使用UTF-8或GB18030编码保存'
            }
    
    # 创建CSV读取器
    csv_reader = csv.reader(io.StringIO(csv_data))
    
    # 读取标题行
    try:
        headers = next(csv_reader)
    except StopIteration:
        return {
            'valid': False,
            'errors': 'CSV文件为空或格式错误'
        }
    
    # 验证必填的标题
    missing_headers = [header for header in required_headers if header not in headers]
    if missing_headers:
        return {
            'valid': False,
            'errors': f'缺少必填列: {", ".join(missing_headers)}'
        }
    
    # 验证行数
    row_count = 1  # 已经读取了标题行
    for _ in csv_reader:
        row_count += 1
        if row_count > max_rows:
            return {
                'valid': False,
                'errors': f'CSV文件行数超过限制 ({max_rows}行)'
            }
    
    # 重置文件指针供后续使用
    csv_file.seek(0)
    
    return {
        'valid': True,
        'headers': headers,
        'row_count': row_count
    }


def validate_csv_data(csv_file, validators=None, required_headers=None):
    """
    验证CSV文件中的数据是否符合要求
    
    参数:
    - csv_file: 上传的CSV文件对象
    - validators: 字段验证函数的字典，键为字段名，值为验证函数
    - required_headers: 必填的列标题列表
    
    返回:
    - dict: 包含验证结果的字典
    """
    if validators is None:
        validators = {}
    if required_headers is None:
        required_headers = []
    
    # 首先验证CSV基本格式
    basic_validation = validate_csv(csv_file, required_headers=required_headers)
    if not basic_validation['valid']:
        return basic_validation
    
    # 重置文件指针
    csv_file.seek(0)
    
    # 读取CSV内容
    csv_data = csv_file.read().decode('utf-8-sig')
    csv_reader = csv.DictReader(io.StringIO(csv_data))
    
    errors = []
    row_num = 2  # 从2开始（1是标题行）
    
    # 逐行验证数据
    for row in csv_reader:
        row_errors = []
        
        # 验证必填字段不为空
        for header in required_headers:
            if not row.get(header):
                row_errors.append(f'"{header}"列不能为空')
        
        # 应用自定义验证器
        for field, validator in validators.items():
            if field in row:
                try:
                    validator_result = validator(row[field])
                    if validator_result is not True:
                        row_errors.append(f'"{field}"列: {validator_result}')
                except Exception as e:
                    row_errors.append(f'"{field}"列验证错误: {str(e)}')
        
        if row_errors:
            errors.append((row_num, row_errors))
        
        row_num += 1
    
    # 重置文件指针供后续使用
    csv_file.seek(0)
    
    if errors:
        return {
            'valid': False,
            'errors': f'CSV数据验证失败，共有{len(errors)}行数据有问题',
            'detail_errors': errors
        }
    
    return {
        'valid': True,
        'row_count': row_num - 1  # 减去标题行
    } 