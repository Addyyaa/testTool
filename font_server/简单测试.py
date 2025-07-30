#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单测试字体服务器的字体子集化功能
"""

import requests
import os

def test_font_subsetting():
    """测试字体子集化功能"""
    print("🧪 测试字体服务器字体子集化功能")
    print("=" * 50)
    
    # 服务器地址
    server_url = "http://localhost:8889"
    
    # 1. 检查服务器状态
    try:
        response = requests.get(f"{server_url}/health", timeout=5)
        if response.status_code == 200:
            print("✅ 服务器运行正常")
        else:
            print("❌ 服务器状态异常")
            return
    except:
        print("❌ 无法连接服务器，请确保服务器正在运行")
        print("   启动命令: python start_font_server.py")
        return
    
    # 2. 获取可用字体
    try:
        response = requests.get(f"{server_url}/api/fonts")
        fonts_data = response.json()
        
        if not fonts_data.get('success') or not fonts_data.get('fonts'):
            print("❌ 没有找到字体文件")
            print("   请将字体文件放入 fonts/ 目录")
            print("   例如: copy \"C:\\Windows\\Fonts\\arial.ttf\" \"fonts\\english\\arial.ttf\"")
            return
        
        # 选择第一个字体进行测试
        font_name = list(fonts_data['fonts'].keys())[0]
        font_info = fonts_data['fonts'][font_name]
        original_size = font_info.get('size', 0)
        
        print(f"✅ 找到字体: {font_name}")
        print(f"   原始大小: {original_size / (1024*1024):.2f}MB")
        
    except Exception as e:
        print(f"❌ 获取字体列表失败: {e}")
        return
    
    # 3. 测试字体子集化
    test_text = "hello world! 你好，世界！"
    print(f"\n📝 测试文字: {test_text}")
    print(f"   包含字符: {len(set(test_text))} 个唯一字符")
    print(f"   字符列表: {list(set(test_text))}")
    
    try:
        # 发送请求创建字体子集
        response = requests.post(
            f"{server_url}/api/font/subset/{font_name}",
            json={
                'text': test_text,
                'format': 'ttf'
            },
            timeout=30
        )
        
        if response.status_code == 200:
            # 保存返回的字体文件
            font_data = response.content
            output_file = "子集字体.ttf"
            
            with open(output_file, 'wb') as f:
                f.write(font_data)
            
            # 计算压缩比
            subset_size = len(font_data)
            compression_ratio = (subset_size / original_size) * 100
            
            print(f"\n🎉 字体子集化成功！")
            print(f"   原始大小: {original_size / (1024*1024):.2f}MB")
            print(f"   子集大小: {subset_size / 1024:.2f}KB")
            print(f"   压缩比例: {compression_ratio:.2f}%")
            print(f"   节省空间: {(original_size - subset_size) / (1024*1024):.2f}MB")
            print(f"   保存文件: {output_file}")
            
            # 验证文件确实被创建
            if os.path.exists(output_file):
                print(f"✅ 文件创建成功，可以直接使用")
            else:
                print(f"❌ 文件创建失败")
        
        else:
            # 显示错误信息
            try:
                error_info = response.json()
                print(f"❌ 创建字体子集失败: {error_info.get('error', '未知错误')}")
            except:
                print(f"❌ 创建字体子集失败: HTTP {response.status_code}")
    
    except Exception as e:
        print(f"❌ 请求异常: {e}")
    
    print("\n" + "=" * 50)
    print("测试完成")

if __name__ == '__main__':
    test_font_subsetting() 