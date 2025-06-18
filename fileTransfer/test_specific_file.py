#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试特定文件名的HTTP传输
"""

import os
import tempfile
import time
from http_server import FileHTTPServer

def test_heic_filename():
    """测试HEIC文件名的处理"""
    print("=== 测试HEIC文件名 ===")
    
    # 创建模拟的HEIC文件
    test_filename = "2020-10-16.HEIC"
    test_content = "这是一个模拟的HEIC文件内容".encode('utf-8')  # 二进制内容
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.HEIC') as f:
        f.write(test_content)
        temp_file_path = f.name
    
    print(f"创建测试文件: {temp_file_path}")
    print(f"目标文件名: {test_filename}")
    
    try:
        # 启动HTTP服务器
        server = FileHTTPServer(port=8089)
        server.start()
        
        print(f"HTTP服务器已启动，端口: 8089")
        print(f"临时目录: {server.temp_dir}")
        
        # 等待服务器启动
        time.sleep(1)
        
        # 添加文件到服务器，使用特定文件名
        print(f"\n添加文件到HTTP服务器，使用文件名: {test_filename}")
        server_file_path = server.add_file(temp_file_path, test_filename)
        
        if server_file_path:
            print(f"文件添加成功: {server_file_path}")
            print(f"实际文件名: {os.path.basename(server_file_path)}")
            print(f"文件存在: {os.path.exists(server_file_path)}")
            
            if os.path.exists(server_file_path):
                file_size = os.path.getsize(server_file_path)
                print(f"文件大小: {file_size} bytes")
        else:
            print("文件添加失败!")
            return
        
        # 列出服务器文件
        print(f"\n服务器文件列表:")
        files = server.list_files()
        for file_info in files:
            print(f"  - {file_info['name']} ({file_info['size']} bytes)")
        
        # 测试URL生成
        actual_filename = os.path.basename(server_file_path)
        download_url = server.get_download_url(actual_filename)
        print(f"\n下载URL: {download_url}")
        
        # 测试URL编码
        import urllib.parse
        encoded_filename = urllib.parse.quote(actual_filename, safe='')
        print(f"编码后的文件名: {encoded_filename}")
        
        # 手动构造URL测试
        manual_url = f"http://192.168.1.7:8089/{encoded_filename}"
        print(f"手动构造URL: {manual_url}")
        
        # 测试HTTP请求
        print(f"\n测试HTTP请求...")
        try:
            import requests
            response = requests.get(download_url, timeout=10)
            print(f"HTTP状态码: {response.status_code}")
            
            if response.status_code == 200:
                print(f"下载成功！内容长度: {len(response.content)} bytes")
            else:
                print(f"下载失败: {response.text}")
                
        except Exception as e:
            print(f"HTTP请求失败: {e}")
        
        # 停止服务器
        print(f"\n停止HTTP服务器...")
        server.stop()
        
    finally:
        # 清理测试文件
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            print(f"清理测试文件: {temp_file_path}")

if __name__ == "__main__":
    test_heic_filename() 