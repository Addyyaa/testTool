#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件传输工具启动脚本

用于便捷启动现代化文件传输工具
"""

import os
import sys
import subprocess

def check_dependencies():
    """检查依赖是否已安装"""
    required_packages = [
        'tkinterdnd2',
        'telnetlib3', 
        'requests',
        'pywin32',
        'PIL'  # Pillow库导入时使用PIL名称
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            if package == 'pywin32':
                try:
                    import win32clipboard
                except ImportError:
                    missing_packages.append(package)
            elif package == 'PIL':
                # PIL是Pillow的导入名，但安装时使用Pillow
                missing_packages.append('Pillow')
            else:
                missing_packages.append(package)
    
    return missing_packages

def install_dependencies(packages):
    """安装缺失的依赖"""
    print("正在安装缺失的依赖包...")
    for package in packages:
        print(f"安装 {package}...")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
            print(f"✅ {package} 安装成功")
        except subprocess.CalledProcessError:
            print(f"❌ {package} 安装失败")
            return False
    return True

def main():
    """主启动函数"""
    print("=" * 50)
    print("🚀 现代化文件传输工具启动器")
    print("=" * 50)
    
    # 检查依赖
    print("检查依赖包...")
    missing = check_dependencies()
    
    if missing:
        print(f"发现缺失的依赖包: {', '.join(missing)}")
        choice = input("是否自动安装？(y/n): ").lower().strip()
        
        if choice == 'y' or choice == 'yes':
            if not install_dependencies(missing):
                print("❌ 依赖安装失败，请手动安装")
                print("运行命令: pip install -r requirements.txt")
                return
        else:
            print("请手动安装依赖后再启动程序")
            print("运行命令: pip install -r requirements.txt")
            return
    else:
        print("✅ 所有依赖已安装")
    
    # 启动程序
    print("\n启动文件传输工具...")
    try:
        # 添加当前目录到Python路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        
        # 导入并启动GUI
        from fileTransfer.gui import ModernFileTransferGUI
        
        print("✅ 程序启动成功！")
        app = ModernFileTransferGUI()
        app.run()
        
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        print("请检查程序文件是否完整")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 