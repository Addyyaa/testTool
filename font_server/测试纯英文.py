#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试纯英文字体子集
"""

import requests
from fontTools.ttLib import TTFont

def test_english_subset():
    """测试纯英文字体子集"""
    print("🔍 测试纯英文字体子集")
    print("=" * 50)
    
    server_url = "http://localhost:8889"
    
    # 1. 准备测试文字（只包含英文）
    test_text = "Hello World 123"
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
        with open('english_subset.ttf', 'wb') as f:
            f.write(response.content)
        
        print(f"✅ 字体子集创建成功")
        print(f"文件大小: {len(response.content) / 1024:.2f}KB")
        
        # 4. 分析生成的字体文件包含的字符
        try:
            font = TTFont('english_subset.ttf')
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
            
            print(f"\n📋 实际包含的字符:")
            for char in sorted(actual_chars):
                unicode_val = ord(char)
                char_name = repr(char)
                in_expected = "✅" if char in expected_chars else "❌"
                print(f"  {in_expected} {char_name} (U+{unicode_val:04X})")
            
            if extra_chars:
                print(f"\n⚠️  包含额外字符 ({len(extra_chars)} 个):")
                for char in sorted(extra_chars):
                    unicode_val = ord(char)
                    char_name = repr(char)
                    print(f"  ❌ {char_name} (U+{unicode_val:04X})")
            
            if missing_chars:
                print(f"\n❌ 缺少字符 ({len(missing_chars)} 个):")
                for char in sorted(missing_chars):
                    unicode_val = ord(char)
                    char_name = repr(char)
                    print(f"  ❌ {char_name} (U+{unicode_val:04X})")
            
            if not extra_chars and not missing_chars:
                print(f"\n🎉 完美！字体只包含期望的字符")
            
            font.close()
            
        except Exception as e:
            print(f"❌ 分析字体文件失败: {e}")
    
    else:
        print(f"❌ 字体子集创建失败: {response.status_code}")
        print(f"错误: {response.text}")

if __name__ == '__main__':
    test_english_subset() 