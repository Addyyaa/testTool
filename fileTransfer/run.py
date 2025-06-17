#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件传输工具启动脚本

简单的启动入口，自动检查依赖并启动GUI程序
"""

import os
import sys
import subprocess

def check_dependencies():
    """检查必要的依赖"""
    required_packages = [
        'tkinterdnd2',
        'telnetlib3'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✓ {package} 已安装")
        except ImportError:
            missing_packages.append(package)
            print(f"✗ {package} 未安装")
    
    if missing_packages:
        print("\n缺少必要的依赖包，正在尝试安装...")
        try:
            for package in missing_packages:
                print(f"正在安装 {package}...")
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
                print(f"✓ {package} 安装成功")
        except subprocess.CalledProcessError as e:
            print(f"✗ 依赖安装失败: {e}")
            print("请手动运行以下命令安装依赖:")
            for package in missing_packages:
                print(f"  pip install {package}")
            return False
    
    return True

def main():
    """主函数"""
    print("=" * 50)
    print("现代化文件传输工具启动器")
    print("=" * 50)
    
    # 检查Python版本
    if sys.version_info < (3, 7):
        print("✗ 错误: 需要Python 3.7或更高版本")
        print(f"当前版本: {sys.version}")
        return 1
    
    print(f"✓ Python版本: {sys.version.split()[0]}")
    
    # 检查依赖
    print("\n检查依赖包...")
    if not check_dependencies():
        return 1
    
    # 启动GUI程序
    print("\n启动文件传输工具...")
    try:
        from main_gui import ModernFileTransferGUI
        
        print("✓ 所有依赖检查完成")
        print("✓ 正在启动GUI界面...")
        
        app = ModernFileTransferGUI()
        app.run()
        
    except ImportError as e:
        print(f"✗ 导入模块失败: {e}")
        print("请确保所有文件都在正确的位置")
        return 1
    except KeyboardInterrupt:
        print("\n用户中断程序运行")
        return 0
    except Exception as e:
        print(f"✗ 程序启动失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 