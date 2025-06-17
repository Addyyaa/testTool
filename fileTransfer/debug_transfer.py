#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件传输调试脚本

用于测试和调试文件传输过程的各个步骤
"""

import sys
import os
import asyncio
import logging
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from http_server import FileHTTPServer
from telnet_connect import TelnetConnect


class TransferDebugger:
    """传输调试器"""
    
    def __init__(self):
        self.setup_logging()
        self.http_server = None
        self.telnet_client = None
        
    def setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('debug_transfer.log', encoding='utf-8')
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    async def test_connection(self, host, port, username, password):
        """测试telnet连接"""
        try:
            self.logger.info(f"测试连接到 {host}:{port}")
            self.telnet_client = TelnetConnect(host, port)
            
            success = await self.telnet_client.connect()
            if not success:
                self.logger.error("连接失败")
                return False
            
            login_success = await self.telnet_client.login(username, password)
            if not login_success:
                self.logger.error("登录失败")
                return False
            
            self.logger.info("连接和登录成功")
            return True
            
        except Exception as e:
            self.logger.error(f"连接测试失败: {e}")
            return False
    
    def test_http_server(self):
        """测试HTTP服务器"""
        try:
            self.logger.info("启动HTTP服务器测试")
            self.http_server = FileHTTPServer(port=88)
            self.http_server.start()
            self.logger.info("HTTP服务器启动成功")
            return True
            
        except Exception as e:
            self.logger.error(f"HTTP服务器测试失败: {e}")
            return False
    
    def test_file_add(self, test_file_path):
        """测试文件添加"""
        try:
            if not os.path.exists(test_file_path):
                self.logger.error(f"测试文件不存在: {test_file_path}")
                return False
            
            self.logger.info(f"测试添加文件: {test_file_path}")
            filename = os.path.basename(test_file_path)
            
            server_path = self.http_server.add_file(test_file_path, filename)
            if not server_path:
                self.logger.error("文件添加失败")
                return False
            
            self.logger.info(f"文件成功添加到服务器: {server_path}")
            
            # 测试下载URL
            download_url = self.http_server.get_download_url(filename)
            self.logger.info(f"下载URL: {download_url}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"文件添加测试失败: {e}")
            return False
    
    async def test_wget_download(self, download_url, remote_path, filename):
        """测试wget下载"""
        try:
            self.logger.info(f"测试wget下载: {download_url}")
            
            # 切换到目标目录
            cd_result = await self.telnet_client.execute_command(f'cd "{remote_path}"')
            self.logger.info(f"cd命令结果: {cd_result}")
            
            # 检查当前目录
            pwd_result = await self.telnet_client.execute_command('pwd')
            self.logger.info(f"当前目录: {pwd_result}")
            
            # 执行wget命令
            wget_cmd = f'wget -O "{filename}" "{download_url}"'
            self.logger.info(f"执行wget命令: {wget_cmd}")
            
            result = await self.telnet_client.execute_command(wget_cmd, timeout=30)
            self.logger.info(f"wget结果: {result}")
            
            # 检查文件是否下载成功
            ls_result = await self.telnet_client.execute_command(f'ls -la "{filename}"')
            self.logger.info(f"文件检查结果: {ls_result}")
            
            return filename in ls_result
            
        except Exception as e:
            self.logger.error(f"wget下载测试失败: {e}")
            return False
    
    async def run_full_test(self, host, port, username, password, test_file_path, remote_path):
        """运行完整测试"""
        self.logger.info("开始完整传输测试")
        
        # 1. 测试连接
        if not await self.test_connection(host, port, username, password):
            return False
        
        # 2. 测试HTTP服务器
        if not self.test_http_server():
            return False
        
        # 3. 测试文件添加
        if not self.test_file_add(test_file_path):
            return False
        
        # 4. 测试wget下载
        filename = os.path.basename(test_file_path)
        download_url = self.http_server.get_download_url(filename)
        
        if not await self.test_wget_download(download_url, remote_path, filename):
            return False
        
        self.logger.info("完整传输测试成功!")
        return True
    
    def cleanup(self):
        """清理资源"""
        if self.http_server:
            self.http_server.stop()
        if self.telnet_client:
            asyncio.create_task(self.telnet_client.disconnect())


async def main():
    """主函数"""
    debugger = TransferDebugger()
    
    try:
        # 配置信息（请根据实际情况修改）
        host = "192.168.1.100"
        port = 23
        username = "root"
        password = "ya!2dkwy7-934^"
        test_file_path = "test_file.txt"  # 请创建一个测试文件
        remote_path = "/"
        
        # 创建测试文件（如果不存在）
        if not os.path.exists(test_file_path):
            with open(test_file_path, 'w', encoding='utf-8') as f:
                f.write(f"测试文件内容\n创建时间: {os.path.getctime(test_file_path)}")
            debugger.logger.info(f"创建测试文件: {test_file_path}")
        
        # 运行测试
        success = await debugger.run_full_test(host, port, username, password, test_file_path, remote_path)
        
        if success:
            print("✅ 所有测试通过!")
        else:
            print("❌ 测试失败，请查看日志")
            
    except Exception as e:
        debugger.logger.error(f"测试过程中出现异常: {e}")
        print(f"❌ 测试异常: {e}")
        
    finally:
        debugger.cleanup()


if __name__ == "__main__":
    print("🔧 文件传输调试脚本")
    print("请根据实际情况修改脚本中的连接参数")
    print("=" * 50)
    asyncio.run(main()) 