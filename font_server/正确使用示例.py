#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
正确使用字体服务器的示例
客户端只需要发送需要的文字，服务器负责创建字体子集
"""

import requests
import json

def correct_usage_demo():
    """正确使用字体服务器的演示"""
    print("✨ 字体服务器正确使用演示")
    print("=" * 50)
    
    server_url = "http://localhost:8889"
    
    # 1. 检查服务器
    print("1. 检查服务器状态...")
    try:
        response = requests.get(f"{server_url}/health", timeout=5)
        if response.status_code == 200:
            print("✅ 服务器正常")
        else:
            print("❌ 服务器异常")
            return
    except:
        print("❌ 服务器未启动，请运行：python start_font_server.py")
        return
    
    # 2. 获取可用字体（只需要知道有哪些字体）
    print("\n2. 获取可用字体...")
    try:
        response = requests.get(f"{server_url}/api/fonts")
        fonts_data = response.json()
        
        if not fonts_data.get('success'):
            print("❌ 获取字体失败")
            return
            
        fonts = fonts_data.get('fonts', {})
        if not fonts:
            print("❌ 没有字体文件")
            return
            
        # 选择第一个字体
        font_name = list(fonts.keys())[0]
        font_info = fonts[font_name]
        
        print(f"✅ 使用字体: {font_name}")
        print(f"   原始大小: {font_info.get('size', 0) / (1024*1024):.2f}MB")
        
    except Exception as e:
        print(f"❌ 获取字体异常: {e}")
        return
    
    # 3. 客户端使用场景演示
    print("\n3. 客户端使用场景演示...")
    print("   客户端只需要发送需要显示的文字内容")
    print("   服务器自动创建包含这些字符的字体文件")
    
    # 模拟不同的客户端需求
    client_scenarios = [
        {
            "client": "POS收银机",
            "text": "收银台 金额:¥123.45 找零:¥6.55",
            "description": "收银系统需要显示中文、数字和货币符号"
        },
        {
            "client": "IoT温度显示器", 
            "text": "Temperature: 25.6°C 湿度:68%",
            "description": "温度显示器需要英文、数字和特殊符号"
        },
        {
            "client": "多语言标签",
            "text": "Hello 你好 こんにちは 안녕하세요",
            "description": "国际化应用需要多语言支持"
        },
        {
            "client": "数字时钟",
            "text": "2024-01-15 14:30:25",
            "description": "时钟显示需要数字和日期分隔符"
        }
    ]
    
    for i, scenario in enumerate(client_scenarios, 1):
        print(f"\n   场景 {i}: {scenario['client']}")
        print(f"   需求: {scenario['description']}")
        print(f"   文字: {scenario['text']}")
        
        # 统计需要的字符
        unique_chars = set(scenario['text'])
        print(f"   字符数: {len(unique_chars)} 个")
        
        try:
            # 客户端发送请求：只需要提供文字内容
            response = requests.post(
                f"{server_url}/api/font/subset/{font_name}",
                json={
                    'text': scenario['text'],  # 只需要这个！
                    'format': 'ttf'
                },
                timeout=30
            )
            
            if response.status_code == 200:
                # 服务器返回定制的字体文件
                font_data = response.content
                size_kb = len(font_data) / 1024
                
                # 计算节省的空间
                original_size = font_info.get('size', 0)
                saved_mb = (original_size - len(font_data)) / (1024*1024)
                compression_ratio = (len(font_data) / original_size) * 100
                
                print(f"   ✅ 成功获取定制字体")
                print(f"   📦 字体大小: {size_kb:.2f}KB (原始: {original_size/(1024*1024):.2f}MB)")
                print(f"   💾 节省空间: {saved_mb:.2f}MB ({100-compression_ratio:.1f}%)")
                
                # 保存字体文件
                filename = f"{scenario['client']}_定制字体.ttf"
                with open(filename, 'wb') as f:
                    f.write(font_data)
                print(f"   💾 保存为: {filename}")
                
            else:
                try:
                    error_info = response.json()
                    print(f"   ❌ 失败: {error_info.get('error', '未知错误')}")
                except:
                    print(f"   ❌ 失败: HTTP {response.status_code}")
                    
        except Exception as e:
            print(f"   ❌ 请求异常: {e}")
    
    # 4. 总结优势
    print(f"\n" + "=" * 50)
    print("🎯 字体服务器的优势:")
    print("   ✅ 客户端只需发送文字内容")
    print("   ✅ 服务器自动创建定制字体")
    print("   ✅ 大幅减少字体文件大小")
    print("   ✅ 节省终端设备存储空间")
    print("   ✅ 支持多种字体格式")
    print("   ✅ 智能缓存提高效率")
    
    print("\n💡 使用建议:")
    print("   - 客户端无需了解字体内部结构")
    print("   - 只需要知道要显示什么文字")
    print("   - 服务器负责所有字体处理工作")
    print("   - 适合存储空间有限的IoT设备")

if __name__ == '__main__':
    correct_usage_demo() 