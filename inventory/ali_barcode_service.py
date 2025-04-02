import urllib3
import json
from django.conf import settings

class AliBarcodeService:
    """
    阿里云条形码查询API服务类
    使用APPCODE认证方式
    """
    BASE_URL = "https://ali-barcode.showapi.com/barcode"
    
    @classmethod
    def search_barcode(cls, barcode):
        """
        根据条码查询商品信息
        
        Args:
            barcode: 商品条码
            
        Returns:
            dict: 包含商品信息的字典，如果未找到则返回None
        """
        try:
            # 获取阿里云API的APPCODE
            appcode = getattr(settings, 'ALI_BARCODE_APPCODE', '')
            
            if not appcode:
                print("未配置阿里云条形码API的APPCODE")
                return None
                
            # 设置请求头，添加APPCODE认证
            headers = {
                "Authorization": f"APPCODE {appcode}"
            }
            
            # 构建查询URL
            url = f"{cls.BASE_URL}?code={barcode}"
            
            # 创建连接池管理器并发送请求
            http = urllib3.PoolManager()
            response = http.request(
                'GET',
                url,
                headers=headers,
                timeout=5.0
            )
            
            # 检查响应状态码
            if response.status == 200:
                # 解析JSON响应
                data = json.loads(response.data.decode('utf-8'))
                # 检查API返回结果
                if data.get('showapi_res_code') == 0:
                    # 获取商品信息
                    res_body = data.get('showapi_res_body', {})
                    
                    # 检查是否查询成功
                    # 注意：API返回的flag可能是字符串'true'或布尔值True
                    if res_body.get('flag') == 'true' or res_body.get('flag') is True:
                        # 将价格字符串转换为浮点数，如果转换失败则默认为0
                        price = 0
                        try:
                            if res_body.get('price'):
                                price = float(res_body.get('price'))
                        except (ValueError, TypeError):
                            pass
                            
                        return {
                            'name': res_body.get('goodsName', ''),
                            'specification': res_body.get('spec', ''),
                            'manufacturer': res_body.get('manuName', ''),
                            'category': res_body.get('goodsType', ''),
                            'suggested_price': price,
                            'image_url': res_body.get('img', ''),
                            'description': res_body.get('note', ''),
                            'trademark': res_body.get('trademark', ''),
                            'origin': res_body.get('ycg', ''),
                            'barcode_image': res_body.get('sptmImg', ''),
                            'barcode': res_body.get('code', ''),
                            'english_name': res_body.get('engName', '')
                        }
                    else:
                        print(f"条码查询失败: {res_body.get('remark')}")
                        print(f"完整响应体: {res_body}")
                else:
                    print(f"API调用失败: {data.get('showapi_res_error')}")
                    print(f"完整响应: {data}")
            else:
                print(f"HTTP请求失败，状态码: {response.status}")
                print(f"响应内容: {response.data.decode('utf-8', errors='replace')}")
                
            return None
        except Exception as e:
            print(f"条码查询出错: {e}")
            import traceback
            print(f"详细错误信息: {traceback.format_exc()}")
            return None