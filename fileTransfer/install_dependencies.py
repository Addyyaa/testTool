#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件传输工具依赖安装脚本

自动检测和安装必要的依赖包
"""

import subprocess
import sys
import os

def check_and_install_dependencies():
    """检查并安装依赖包"""
    print("🔍 检查文件传输工具依赖...")
    
    # 必需的包
    required_packages = [
        'tkinterdnd2>=0.3.0',
        'telnetlib3>=2.0.0', 
        'requests>=2.25.0',
        'Pillow>=8.0.0'
    ]
    
    # Windows增强包
    windows_packages = [
        'send2trash>=1.8.0'
    ]
    
    missing_packages = []
    
    # 检查必需包
    for package in required_packages:
        package_name = package.split('>=')[0]
        try:
            __import__(package_name)
            print(f"✅ {package_name} 已安装")
        except ImportError:
            print(f"❌ {package_name} 未安装")
            missing_packages.append(package)
    
    # 检查Windows增强包
    if os.name == 'nt':  # Windows系统
        for package in windows_packages:
            package_name = package.split('>=')[0]
            try:
                __import__(package_name)
                print(f"✅ {package_name} 已安装")
            except ImportError:
                print(f"⚠️  {package_name} 未安装（推荐安装以改善文件删除性能）")
                missing_packages.append(package)
    
    # 安装缺失的包
    if missing_packages:
        print(f"\n📦 需要安装 {len(missing_packages)} 个依赖包...")
        
        for package in missing_packages:
            try:
                print(f"正在安装 {package}...")
                result = subprocess.run([
                    sys.executable, '-m', 'pip', 'install', package
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    print(f"✅ {package} 安装成功")
                else:
                    print(f"❌ {package} 安装失败: {result.stderr}")
                    
            except Exception as e:
                print(f"❌ 安装 {package} 时出错: {e}")
    else:
        print("\n🎉 所有依赖包都已安装！")
    
    print("\n" + "="*50)
    print("✨ 文件传输工具依赖检查完成")
    print("现在您可以运行：python main_gui.py")
    print("="*50)

if __name__ == "__main__":
    try:
        check_and_install_dependencies()
    except KeyboardInterrupt:
        print("\n\n⚠️ 安装被用户中断")
    except Exception as e:
        print(f"\n❌ 安装脚本执行失败: {e}")
        print("请手动运行: pip install -r requirements.txt") 