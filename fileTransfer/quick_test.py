#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速测试脚本

用于快速测试HTTP服务器和网络配置
"""

import os
import socket
import time
import requests
from http_server import FileHTTPServer


def get_local_ip():
    """获取本机IP"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception as e:
        print(f"获取IP失败: {e}")
        return "127.0.0.1"


def test_http_server():
    """测试HTTP服务器"""
    print("🔧 开始测试HTTP服务器...")
    
    # 1. 启动HTTP服务器
    server = FileHTTPServer(port=88)
    try:
        server.start()
        print("✅ HTTP服务器启动成功")
        
        local_ip = get_local_ip()
        print(f"✅ 本机IP地址: {local_ip}")
        print(f"✅ 临时目录: {server.temp_dir}")
        print(f"✅ 访问地址: http://{local_ip}:88/")
        
        # 2. 创建测试文件
        test_content = "这是一个测试文件\n用于验证HTTP服务器功能"
        test_file_path = "test_file.txt"
        
        with open(test_file_path, 'w', encoding='utf-8') as f:
            f.write(test_content)
        print(f"✅ 创建测试文件: {test_file_path}")
        
        # 3. 添加文件到服务器
        server_file_path = server.add_file(test_file_path, "test_file.txt")
        if server_file_path:
            print(f"✅ 文件已添加到服务器: {server_file_path}")
        else:
            print("❌ 文件添加失败")
            return False
        
        # 4. 测试下载
        download_url = f"http://{local_ip}:88/test_file.txt"
        print(f"🔍 测试下载URL: {download_url}")
        
        try:
            response = requests.get(download_url, timeout=5)
            if response.status_code == 200:
                print("✅ HTTP下载测试成功")
                print(f"✅ 下载内容: {response.text[:50]}...")
            else:
                print(f"❌ HTTP下载失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ HTTP下载异常: {e}")
            return False
        
        # 5. 清理
        server.remove_file("test_file.txt")
        print("✅ 临时文件已清理")
        
        return True
        
    except Exception as e:
        print(f"❌ HTTP服务器测试失败: {e}")
        return False
    
    finally:
        # 停止服务器
        try:
            server.stop()
            print("✅ HTTP服务器已停止")
        except Exception as e:
            print(f"⚠️ 停止服务器时出错: {e}")
        
        # 清理测试文件
        if os.path.exists(test_file_path):
            os.remove(test_file_path)
            print("✅ 测试文件已删除")


def main():
    """主函数"""
    print("=" * 50)
    print("🚀 文件传输工具 - 快速测试")
    print("=" * 50)
    
    # 测试HTTP服务器
    if test_http_server():
        print("\n🎉 所有测试通过!")
        print("\n📋 下一步操作:")
        print("1. 确保远程设备可以访问本机IP")
        print("2. 确保远程设备安装了wget工具")
        print("3. 在GUI中点击'测试传输'按钮进行完整测试")
    else:
        print("\n❌ 测试失败，请检查错误信息")
    
    print("\n" + "=" * 50)


if __name__ == "__main__":
    main() 