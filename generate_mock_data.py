#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
生成模拟数据脚本
使用Django管理命令generate_sample_data来创建测试数据
"""

import os
import sys
import subprocess

def main():
    """
    使用Django管理命令来生成示例数据
    """
    print("正在调用Django管理命令生成示例数据...")
    
    try:
        # 使用subprocess调用Django管理命令
        cmd = [sys.executable, "manage.py", "generate_sample_data", 
               "--products", "100", 
               "--members", "50", 
               "--sales", "200", 
               "--clean"]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(result.stdout)
        
        print("示例数据生成完成！")
        print("你可以自行调整参数使用以下命令来生成不同规模的数据：")
        print("python manage.py generate_sample_data --products 数量 --members 数量 --sales 数量 --clean")
        
    except subprocess.CalledProcessError as e:
        print(f"生成示例数据时出错: {e}")
        print(f"错误信息: {e.stderr}")
    except Exception as e:
        print(f"发生未知错误: {e}")

if __name__ == "__main__":
    main() 