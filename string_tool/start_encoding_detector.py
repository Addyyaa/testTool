#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
编码检测工具启动脚本
自动检查依赖并启动程序

Author: Assistant
Date: 2024
"""

import sys
import subprocess
import os
import importlib


def check_and_install_dependencies():
    """检查并安装依赖包"""
    print("正在检查依赖...")
    
    required_packages = {
        'chardet': 'chardet>=5.0.0'
    }
    
    missing_packages = []
    
    for package, pip_name in required_packages.items():
        try:
            importlib.import_module(package)
            print(f"✓ {package} 已安装")
        except ImportError:
            print(f"✗ {package} 未安装")
            missing_packages.append(pip_name)
    
    if missing_packages:
        print(f"\n正在安装缺失的依赖包: {', '.join(missing_packages)}")
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", "--upgrade"
            ] + missing_packages)
            print("✓ 依赖安装完成")
        except subprocess.CalledProcessError as e:
            print(f"✗ 依赖安装失败: {e}")
            print("请手动安装依赖:")
            print(f"pip install {' '.join(missing_packages)}")
            return False
    
    return True


def main():
    """主函数"""
    print("=" * 50)
    print("编码格式检测工具启动器")
    print("=" * 50)
    
    # 检查Python版本
    if sys.version_info < (3, 6):
        print("错误: 需要Python 3.6或更高版本")
        input("按回车键退出...")
        return
    
    print(f"Python版本: {sys.version}")
    
    # 检查并安装依赖
    if not check_and_install_dependencies():
        input("按回车键退出...")
        return
    
    print("\n正在启动编码检测工具...")
    
    try:
        # 导入并启动主程序
        from codeing_format import main as run_app
        run_app()
    except Exception as e:
        print(f"启动失败: {e}")
        import traceback
        traceback.print_exc()
        input("按回车键退出...")


if __name__ == "__main__":
    main() 