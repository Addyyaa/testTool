#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件传输工具优化启动脚本

解决界面显示和远程目录解析问题的启动器
"""

import os
import sys
import subprocess

def check_and_install_dependencies():
    """检查并安装必要的依赖"""
    required_packages = {
        'tkinterdnd2': 'tkinterdnd2>=0.3.0',
        'telnetlib3': 'telnetlib3>=2.0.0'
    }
    
    missing_packages = []
    
    print("检查依赖包...")
    for package, version_spec in required_packages.items():
        try:
            __import__(package)
            print(f"✓ {package} 已安装")
        except ImportError:
            missing_packages.append(version_spec)
            print(f"✗ {package} 未安装")
    
    if missing_packages:
        print(f"\n需要安装 {len(missing_packages)} 个依赖包...")
        try:
            for package in missing_packages:
                print(f"正在安装 {package}...")
                subprocess.check_call([
                    sys.executable, '-m', 'pip', 'install', package, '--user'
                ], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                print(f"✓ {package} 安装成功")
        except subprocess.CalledProcessError as e:
            print(f"✗ 依赖安装失败")
            print("请手动运行以下命令安装依赖:")
            for package in missing_packages:
                print(f"  pip install {package}")
            return False
    
    return True

def setup_environment():
    """设置运行环境"""
    # 设置工作目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # 添加父目录到Python路径
    parent_dir = os.path.dirname(script_dir)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    
    # 设置环境变量
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    
    return True

def main():
    """主函数"""
    print("=" * 60)
    print("现代化文件传输工具 - 优化启动器")
    print("=" * 60)
    
    # 检查Python版本
    if sys.version_info < (3, 7):
        print("✗ 错误: 需要Python 3.7或更高版本")
        print(f"当前版本: {sys.version}")
        input("按回车键退出...")
        return 1
    
    print(f"✓ Python版本: {sys.version.split()[0]}")
    
    # 设置环境
    print("设置运行环境...")
    if not setup_environment():
        print("✗ 环境设置失败")
        input("按回车键退出...")
        return 1
    print("✓ 环境设置完成")
    
    # 检查依赖
    if not check_and_install_dependencies():
        input("按回车键退出...")
        return 1
    
    print("✓ 所有依赖检查完成")
    
    # 启动GUI程序
    print("\n正在启动文件传输工具...")
    try:
        # 导入并启动GUI
        from main_gui import ModernFileTransferGUI
        
        print("✓ 模块导入成功")
        print("✓ 正在启动GUI界面...")
        print("\n" + "=" * 60)
        print("程序启动成功！请查看GUI窗口。")
        print("如果遇到远程目录显示问题，请查看日志区域的调试信息。")
        print("=" * 60)
        
        app = ModernFileTransferGUI()
        app.run()
        
        return 0
        
    except ImportError as e:
        print(f"✗ 导入模块失败: {e}")
        print("请确保所有文件都在正确的位置")
        print("建议检查以下文件是否存在:")
        print("  - main_gui.py")
        print("  - http_server.py")
        print("  - file_transfer_controller.py")
        print("  - ../telnetTool/telnetConnect.py")
        input("按回车键退出...")
        return 1
    except KeyboardInterrupt:
        print("\n用户中断程序运行")
        return 0
    except Exception as e:
        print(f"✗ 程序启动失败: {e}")
        print("\n详细错误信息:")
        import traceback
        traceback.print_exc()
        print("\n可能的解决方案:")
        print("1. 检查是否所有依赖都正确安装")
        print("2. 确保telnetTool目录存在且包含telnetConnect.py")
        print("3. 检查Python环境是否支持tkinter")
        print("4. 尝试以管理员权限运行")
        input("按回车键退出...")
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n程序被用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"启动器异常: {e}")
        import traceback
        traceback.print_exc()
        input("按回车键退出...")
        sys.exit(1) 