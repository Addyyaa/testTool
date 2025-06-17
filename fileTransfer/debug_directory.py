#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
目录解析调试脚本
"""
import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from telnetTool.telnetConnect import CustomTelnetClient

async def test_directory_listing():
    """测试目录列表功能"""
    try:
        # 连接参数
        host = "192.168.1.45"
        port = 23
        username = "root"
        password = "ya!2dkwy7-934^"
        
        print(f"连接到 {host}:{port}")
        
        # 创建telnet客户端
        client = CustomTelnetClient(host=host, port=port, timeout=30.0)
        
        # 连接
        success = await client.connect(username=username, password=password, shell_prompt='#')
        if not success:
            print("连接失败")
            return
        
        print("连接成功！")
        
        # 测试目录列表
        paths_to_test = ["/", "/bin", "/etc", "/tmp"]
        
        for path in paths_to_test:
            print(f"\n=== 测试路径: {path} ===")
            
            # 尝试ls命令
            result = await client.execute_command(f'ls -la "{path}"')
            print(f"原始输出长度: {len(result)}")
            print(f"原始输出前200字符: {repr(result[:200])}")
            
            # 解析输出
            lines = result.strip().split('\n')
            print(f"分割后行数: {len(lines)}")
            
            items = []
            for i, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue
                
                # 跳过总计行
                if i == 0 and line.startswith('total'):
                    continue
                
                # 解析ls -la的输出格式
                parts = line.split()
                if len(parts) >= 9:
                    permissions = parts[0]
                    name = ' '.join(parts[8:])
                    
                    # 跳过当前目录和父目录的引用
                    if name in ['.', '..']:
                        continue
                    
                    if name:  # 确保文件名不为空
                        is_directory = permissions.startswith('d')
                        items.append({
                            'name': name,
                            'is_directory': is_directory,
                            'permissions': permissions
                        })
                        print(f"  {'[DIR]' if is_directory else '[FILE]'} {name}")
            
            print(f"解析到 {len(items)} 个项目")
        
        # 断开连接
        await client.disconnect()
        print("\n测试完成")
        
    except Exception as e:
        print(f"测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_directory_listing()) 