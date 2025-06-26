#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
字体服务器启动脚本
自动检测和安装依赖，然后启动字体服务器

作者: Assistant
日期: 2024
版本: 1.0.0
"""

import os
import sys
import subprocess
import importlib
from pathlib import Path


def check_and_install_requirements():
    """检查并安装依赖包"""
    requirements_file = Path(__file__).parent / "requirements.txt"
    
    if not requirements_file.exists():
        print("错误: requirements.txt 文件不存在")
        return False
    
    # 读取依赖列表
    with open(requirements_file, 'r', encoding='utf-8') as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    missing_packages = []
    
    # 检查每个依赖包
    for requirement in requirements:
        package_name = requirement.split('>=')[0].split('==')[0].strip()
        try:
            importlib.import_module(package_name.replace('-', '_'))
            print(f"✓ {package_name} 已安装")
        except ImportError:
            missing_packages.append(requirement)
            print(f"✗ {package_name} 未安装")
    
    # 安装缺失的包
    if missing_packages:
        print(f"\n需要安装 {len(missing_packages)} 个依赖包...")
        
        for package in missing_packages:
            print(f"正在安装 {package}...")
            try:
                subprocess.check_call([
                    sys.executable, "-m", "pip", "install", package
                ], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                print(f"✓ {package} 安装成功")
            except subprocess.CalledProcessError as e:
                print(f"✗ {package} 安装失败: {e}")
                return False
    
    print("所有依赖包已准备就绪！\n")
    return True


def create_fonts_directory():
    """创建字体目录和示例结构"""
    fonts_dir = Path(__file__).parent / "fonts"
    fonts_dir.mkdir(exist_ok=True)
    
    # 创建示例目录结构
    (fonts_dir / "chinese").mkdir(exist_ok=True)
    (fonts_dir / "english").mkdir(exist_ok=True)
    (fonts_dir / "symbols").mkdir(exist_ok=True)
    
    # 创建说明文件
    readme_content = """# 字体文件目录

请将字体文件放置在此目录或子目录中。

## 支持的字体格式
- TTF (TrueType Font)
- OTF (OpenType Font)
- WOFF (Web Open Font Format)
- WOFF2 (Web Open Font Format 2.0)

## 目录结构建议
- chinese/    中文字体
- english/    英文字体  
- symbols/    符号字体

## 使用说明
1. 将字体文件复制到对应目录
2. 启动字体服务器
3. 通过API接口请求字体子集

更多信息请参考 README.md
"""
    
    readme_file = fonts_dir / "README.md"
    if not readme_file.exists():
        with open(readme_file, 'w', encoding='utf-8') as f:
            f.write(readme_content)
    
    print(f"字体目录已创建: {fonts_dir}")


def main():
    """主函数"""
    print("=" * 60)
    print("            字体服务器启动程序")
    print("=" * 60)
    print()
    
    # 检查Python版本
    python_version = sys.version_info
    if python_version < (3, 7):
        print("错误: 需要Python 3.7或更高版本")
        print(f"当前版本: Python {python_version.major}.{python_version.minor}.{python_version.micro}")
        return False
    
    print(f"Python版本: {python_version.major}.{python_version.minor}.{python_version.micro} ✓")
    print()
    
    # 检查和安装依赖
    print("检查依赖包...")
    if not check_and_install_requirements():
        print("依赖包安装失败，无法启动服务器")
        return False
    
    # 创建字体目录
    create_fonts_directory()
    print()
    
    # 启动字体服务器
    print("正在启动字体服务器...")
    try:
        from font_server import main as start_server
        start_server()
    except KeyboardInterrupt:
        print("\n字体服务器已停止")
    except Exception as e:
        print(f"启动字体服务器失败: {e}")
        return False
    
    return True


if __name__ == '__main__':
    success = main()
    if not success:
        input("按回车键退出...")
        sys.exit(1) 