#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化的PyInstaller打包脚本
自动执行打包并进行文件大小优化
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(cmd, description=""):
    """执行命令并显示进度"""
    print(f"正在执行: {description}")
    print(f"命令: {cmd}")
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8')
    
    if result.returncode == 0:
        print(f"✅ {description} 成功完成")
        if result.stdout.strip():
            print(f"输出: {result.stdout}")
    else:
        print(f"❌ {description} 失败")
        print(f"错误: {result.stderr}")
        return False
    
    return True

def clean_build_dirs():
    """清理之前的构建目录"""
    dirs_to_clean = ['build', 'dist', '__pycache__']
    
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"正在清理目录: {dir_name}")
            shutil.rmtree(dir_name)
    
    # 清理.pyc文件
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.pyc'):
                os.remove(os.path.join(root, file))

def check_dependencies():
    """检查必要的依赖是否已安装"""
    required_packages = ['requests', 'Pillow', 'pyinstaller']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.lower().replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ 缺少必要的依赖包: {', '.join(missing_packages)}")
        print("请运行以下命令安装:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    print("✅ 所有必要依赖已安装")
    return True

def build_executable():
    """使用PyInstaller构建可执行文件"""
    spec_file = "upload_pic_size_test.spec"
    
    if not os.path.exists(spec_file):
        print(f"❌ 找不到spec文件: {spec_file}")
        return False
    
    # 构建命令
    cmd = f"pyinstaller --clean --noconfirm {spec_file}"
    
    return run_command(cmd, "PyInstaller打包")

def optimize_executable():
    """对生成的可执行文件进行额外优化"""
    exe_path = "dist/upload_pic_size_test.exe"
    
    if not os.path.exists(exe_path):
        print(f"❌ 找不到生成的可执行文件: {exe_path}")
        return False
    
    # 获取文件大小
    original_size = os.path.getsize(exe_path)
    print(f"原始文件大小: {original_size / (1024*1024):.2f} MB")
    
    # 如果安装了UPX，尝试进一步压缩
    if shutil.which('upx'):
        print("检测到UPX，尝试进一步压缩...")
        upx_cmd = f"upx --best --lzma {exe_path}"
        if run_command(upx_cmd, "UPX压缩"):
            compressed_size = os.path.getsize(exe_path)
            compression_ratio = (original_size - compressed_size) / original_size * 100
            print(f"压缩后文件大小: {compressed_size / (1024*1024):.2f} MB")
            print(f"压缩率: {compression_ratio:.1f}%")
    else:
        print("未检测到UPX，跳过额外压缩")
    
    return True

def create_readme():
    """创建使用说明文件"""
    readme_content = """# 图片大小测试工具

## 使用说明

1. 双击 upload_pic_size_test.exe 运行程序
2. 按提示输入用户名和密码
3. 选择要测试的功能：
   - 屏幕图片测试
   - 相册图片测试
4. 根据提示选择要检查的屏幕或相册
5. 程序将自动检查图片大小和分辨率是否符合要求

## 检查标准

### 屏幕图片
- Linux屏幕：图片大小不超过2MB，分辨率不超过屏幕分辨率
- Android屏幕：图片大小不超过6MB，短边分辨率不超过1920像素

### 相册图片
- 图片大小不超过2MB
- 短边分辨率不超过1920像素

## 系统要求

- Windows 7 或更高版本
- 网络连接（用于访问图片服务器）

## 注意事项

- 首次运行可能需要几秒钟加载
- 确保网络连接稳定
- 如遇到问题，请检查防火墙设置
"""
    
    with open("dist/使用说明.txt", "w", encoding="utf-8") as f:
        f.write(readme_content)
    
    print("✅ 创建使用说明文件")

def main():
    """主函数"""
    print("🚀 开始优化打包流程...")
    print("="*50)
    
    # 1. 检查依赖
    if not check_dependencies():
        sys.exit(1)
    
    # 2. 清理构建目录
    clean_build_dirs()
    
    # 3. 构建可执行文件
    if not build_executable():
        print("❌ 打包失败")
        sys.exit(1)
    
    # 4. 优化可执行文件
    optimize_executable()
    
    # 5. 创建使用说明
    create_readme()
    
    print("="*50)
    print("🎉 打包完成！")
    print("📁 输出目录: dist/")
    print("📄 可执行文件: dist/upload_pic_size_test.exe")
    print("📋 使用说明: dist/使用说明.txt")
    
    # 显示最终文件大小
    exe_path = "dist/upload_pic_size_test.exe"
    if os.path.exists(exe_path):
        final_size = os.path.getsize(exe_path)
        print(f"📊 最终文件大小: {final_size / (1024*1024):.2f} MB")

if __name__ == "__main__":
    main() 