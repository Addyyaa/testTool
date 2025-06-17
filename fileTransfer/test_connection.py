#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的连接测试脚本
用于验证telnet连接是否正常工作，不涉及GUI
"""

import asyncio
import sys
import os

# 添加父目录到系统路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from telnetTool.telnetConnect import CustomTelnetClient

async def test_connection():
    """测试telnet连接"""
    try:
        print("开始测试连接...")
        
        # 创建telnet客户端
        client = CustomTelnetClient(
            host="192.168.1.45",  # 使用您的IP
            port=23,
            timeout=10.0
        )
        
        print("正在连接...")
        success = await client.connect(
            username="root",
            password="ya!2dkwy7-934^",
            shell_prompt='#'
        )
        
        if success:
            print("✅ 连接成功!")
            
            # 测试一个简单命令
            result = await client.execute_command('pwd')
            print(f"当前目录: {result.strip()}")
            
            # 测试ls命令
            result = await client.execute_command('ls -la /')
            print(f"根目录内容:\n{result[:200]}...")  # 只显示前200字符
            
            print("✅ 命令执行成功!")
            
            # 断开连接
            await client.disconnect()
            print("✅ 连接已断开")
            
        else:
            print("❌ 连接失败")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_connection()) 