#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试字体子集包含的字符
"""

import requests
from fontTools.ttLib import TTFont

def debug_font_subset():
    """调试字体子集包含的字符"""
    print("🔍 调试字体子集字符")
    print("=" * 50)
    
    server_url = "http://localhost:8889"
    
    # 1. 准备测试文字
    test_text = "这是一个文字测试 This is a test"
    expected_chars = set(test_text)
    
    print(f"请求文字: {test_text}")
    print(f"期望字符: {sorted(list(expected_chars))}")
    print(f"期望字符数: {len(expected_chars)}")
    
    # 2. 获取字体
    response = requests.get(f"{server_url}/api/fonts")
    fonts = response.json()['fonts']
    font_name = list(fonts.keys())[0]
    
    print(f"\n使用字体: {font_name}")
    
    # 3. 创建字体子集
    response = requests.post(
        f"{server_url}/api/font/subset/{font_name}",
        json={'text': test_text, 'format': 'ttf'},
        timeout=30
    )
    
    if response.status_code == 200:
        # 保存字体文件
        with open('debug_subset.ttf', 'wb') as f:
            f.write(response.content)
        
        print(f"✅ 字体子集创建成功")
        print(f"文件大小: {len(response.content) / 1024:.2f}KB")
        
        # 4. 分析生成的字体文件包含的字符
        try:
            font = TTFont('debug_subset.ttf')
            cmap = font.getBestCmap()
            
            actual_chars = set()
            for unicode_value in cmap.keys():
                try:
                    char = chr(unicode_value)
                    actual_chars.add(char)
                except ValueError:
                    continue
            
            print(f"\n📊 字符分析:")
            print(f"实际包含字符数: {len(actual_chars)}")
            print(f"期望字符数: {len(expected_chars)}")
            
            # 检查是否只包含期望的字符
            extra_chars = actual_chars - expected_chars
            missing_chars = expected_chars - actual_chars
            
            if extra_chars:
                print(f"\n⚠️  包含额外字符 ({len(extra_chars)} 个):")
                extra_list = sorted(list(extra_chars))
                print(f"前20个额外字符: {extra_list[:20]}")
                if len(extra_list) > 20:
                    print(f"... 还有 {len(extra_list) - 20} 个额外字符")
            
            if missing_chars:
                print(f"\n❌ 缺少字符 ({len(missing_chars)} 个):")
                print(f"缺少字符: {sorted(list(missing_chars))}")
            
            if not extra_chars and not missing_chars:
                print(f"\n✅ 完美！字体只包含期望的字符")
            
            # 显示所有字符的详细信息
            print(f"\n📋 期望字符详情:")
            for char in sorted(expected_chars):
                unicode_val = ord(char)
                char_name = repr(char)
                print(f"  {char_name} (U+{unicode_val:04X})")
            
            font.close()
            
        except Exception as e:
            print(f"❌ 分析字体文件失败: {e}")
    
    else:
        print(f"❌ 字体子集创建失败: {response.status_code}")
        print(f"错误: {response.text}")

if __name__ == '__main__':
    debug_font_subset() 