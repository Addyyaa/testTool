#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
字体文件检查脚本
检查fonts目录中的字体文件状态
"""

import os
from pathlib import Path
from fontTools.ttLib import TTFont

def check_fonts():
    """检查字体文件"""
    fonts_dir = Path("fonts")
    
    if not fonts_dir.exists():
        print("❌ fonts目录不存在")
        return
    
    print("🔍 检查字体文件...")
    print("=" * 50)
    
    total_files = 0
    valid_fonts = 0
    
    for font_file in fonts_dir.rglob("*"):
        if font_file.is_file() and font_file.suffix.lower() in ['.ttf', '.otf', '.ttc', '.woff', '.woff2']:
            total_files += 1
            print(f"\n📄 {font_file.relative_to(fonts_dir)}")
            print(f"   大小: {font_file.stat().st_size / (1024*1024):.2f} MB")
            
            # 验证字体文件
            try:
                font = TTFont(str(font_file))
                
                # 获取字体名称
                name_table = font['name']
                family_name = "Unknown"
                for record in name_table.names:
                    if record.nameID == 1:  # Family name
                        try:
                            family_name = record.toUnicode()
                            break
                        except:
                            continue
                
                # 获取字符数量
                cmap = font.getBestCmap()
                char_count = len(cmap) if cmap else 0
                
                print(f"   名称: {family_name}")
                print(f"   字符数: {char_count}")
                print(f"   状态: ✅ 有效")
                
                font.close()
                valid_fonts += 1
                
            except Exception as e:
                print(f"   状态: ❌ 无效 ({e})")
    
    print("\n" + "=" * 50)
    print(f"📊 总结:")
    print(f"   总文件数: {total_files}")
    print(f"   有效字体: {valid_fonts}")
    print(f"   无效字体: {total_files - valid_fonts}")
    
    if valid_fonts == 0:
        print("\n💡 建议:")
        print("   1. 确保fonts目录中有字体文件")
        print("   2. 支持的格式: .ttf, .otf, .ttc, .woff, .woff2")
        print("   3. 可以从C:\\Windows\\Fonts\\复制系统字体")

if __name__ == '__main__':
    check_fonts() 