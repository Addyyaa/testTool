#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试新的文字字符串API
"""

import requests
import json
from pathlib import Path

def test_font_server():
    """测试字体服务器的新API"""
    server_url = "http://localhost:8889"
    
    print("🧪 测试字体服务器文字字符串API")
    print("=" * 50)
    
    # 1. 健康检查
    print("1. 健康检查...")
    try:
        response = requests.get(f"{server_url}/health", timeout=5)
        if response.status_code == 200:
            print("✅ 服务器运行正常")
        else:
            print("❌ 服务器响应异常")
            return
    except:
        print("❌ 无法连接到服务器，请确保服务器正在运行")
        return
    
    # 2. 获取字体列表
    print("\n2. 获取字体列表...")
    try:
        response = requests.get(f"{server_url}/api/fonts")
        fonts_data = response.json()
        
        if fonts_data.get('success') and fonts_data.get('fonts'):
            print(f"✅ 找到 {fonts_data['count']} 个字体文件")
            font_name = list(fonts_data['fonts'].keys())[0]
            print(f"   使用字体: {font_name}")
        else:
            print("❌ 没有找到字体文件，请先添加字体文件到fonts目录")
            return
    except Exception as e:
        print(f"❌ 获取字体列表失败: {e}")
        return
    
    # 3. 测试新的文字字符串API
    print("\n3. 测试文字字符串API...")
    
    test_cases = [
        {
            "name": "中英文混合",
            "text": "Hello世界！欢迎使用字体服务器。",
            "format": "ttf"
        },
        {
            "name": "纯中文",
            "text": "你好世界！这是一个测试。",
            "format": "woff2"
        },
        {
            "name": "数字符号",
            "text": "123456789 !@#$%^&*()",
            "format": "ttf"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n   测试 {i}: {test_case['name']}")
        print(f"   文字内容: {test_case['text']}")
        
        try:
            # 使用新的text参数
            response = requests.post(
                f"{server_url}/api/font/subset/{font_name}",
                json={
                    'text': test_case['text'],
                    'format': test_case['format']
                },
                timeout=30
            )
            
            if response.status_code == 200:
                font_data = response.content
                size_kb = len(font_data) / 1024
                
                # 保存文件
                output_file = f"test_{i}_{test_case['name']}.{test_case['format']}"
                with open(output_file, 'wb') as f:
                    f.write(font_data)
                
                print(f"   ✅ 成功 - 大小: {size_kb:.2f}KB, 保存为: {output_file}")
                
                # 统计唯一字符数
                unique_chars = len(set(test_case['text']))
                print(f"   📊 唯一字符数: {unique_chars}")
                
            else:
                error_info = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
                print(f"   ❌ 失败 - {error_info}")
                
        except Exception as e:
            print(f"   ❌ 请求异常: {e}")
    
    # 4. 测试兼容性API（characters参数）
    print("\n4. 测试兼容性API（characters参数）...")
    try:
        response = requests.post(
            f"{server_url}/api/font/subset/{font_name}",
            json={
                'characters': ['A', 'B', 'C', '测', '试'],
                'format': 'ttf'
            },
            timeout=30
        )
        
        if response.status_code == 200:
            size_kb = len(response.content) / 1024
            print(f"   ✅ 兼容性API正常 - 大小: {size_kb:.2f}KB")
        else:
            print(f"   ❌ 兼容性API失败")
            
    except Exception as e:
        print(f"   ❌ 兼容性API异常: {e}")
    
    print("\n🎉 测试完成！")

if __name__ == '__main__':
    test_font_server() 