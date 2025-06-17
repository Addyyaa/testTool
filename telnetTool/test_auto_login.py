#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试自动登录检查功能

这个脚本演示了CustomTelnetClient的自动登录检查功能，
包括在执行命令前自动检查登录状态并处理重新登录。
"""

import asyncio
import logging
from telnetConnect import CustomTelnetClient

# 设置日志级别为DEBUG以查看详细信息
logging.basicConfig(level=logging.DEBUG)

async def test_auto_login_feature():
    """测试自动登录检查功能"""
    print("=" * 60)
    print("测试自动登录检查功能")
    print("=" * 60)
    
    # 创建客户端
    client = CustomTelnetClient("192.168.1.45", 23, log_level="DEBUG")
    
    try:
        print("\n1. 连接到服务器并登录...")
        await client.connect(username="root", password="ya!2dkwy7-934^")
        
        print("\n2. 执行第一个命令（会自动检查登录状态）...")
        result1 = await client.execute_command("whoami")
        print(f"当前用户: {result1}")
        
        print("\n3. 执行第二个命令（会再次检查登录状态）...")
        result2 = await client.execute_command("pwd")
        print(f"当前目录: {result2}")
        
        print("\n4. 执行第三个命令（测试连续执行）...")
        result3 = await client.execute_command("date")
        print(f"当前时间: {result3}")
        
        print("\n5. 测试禁用自动登录检查...")
        result4 = await client.execute_command("uptime", auto_login=False)
        print(f"系统运行时间: {result4}")
        
        print("\n6. 获取连接信息...")
        info = client.get_connection_info()
        print(f"连接信息: {info}")
        
        print("\n7. 测试手动设置认证信息...")
        client.set_auth_info("root", "ya!2dkwy7-934^", "#")
        result5 = await client.execute_command("hostname")
        print(f"主机名: {result5}")
        
    except Exception as e:
        print(f"测试过程出现错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.disconnect()
        print("\n测试完成！")

async def test_login_recovery():
    """测试登录恢复功能（模拟连接中断后重新登录）"""
    print("\n" + "=" * 60)
    print("测试登录恢复功能")
    print("=" * 60)
    
    client = CustomTelnetClient("192.168.1.45", 23, log_level="DEBUG")
    
    try:
        print("\n1. 连接并登录...")
        await client.connect(username="root", password="ya!2dkwy7-934^")
        
        print("\n2. 正常执行命令...")
        result1 = await client.execute_command("whoami")
        print(f"用户: {result1}")
        
        # 注意：在实际场景中，如果连接中断，自动登录检查会检测到登录提示符
        # 并自动重新登录。这里我们只是演示API的使用
        
        print("\n3. 使用显式认证信息执行命令...")
        result2 = await client.execute_command(
            "ls /", 
            username="root", 
            password="ya!2dkwy7-934^"
        )
        print(f"根目录内容: {result2[:100]}...")  # 只显示前100个字符
        
    except Exception as e:
        print(f"测试过程出现错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.disconnect()
        print("\n登录恢复测试完成！")

if __name__ == "__main__":
    async def main():
        await test_auto_login_feature()
        await test_login_recovery()
    
    asyncio.run(main()) 