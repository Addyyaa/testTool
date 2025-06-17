#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试并发冲突修复
"""

import asyncio
import logging
import sys
import os

# 添加telnetTool路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'telnetTool'))

from telnetConnect import CustomTelnetClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_concurrent_access():
    """测试并发访问telnet连接"""
    try:
        # 创建telnet客户端
        client = CustomTelnetClient(host='192.168.1.100', port=23)
        
        # 连接
        success = await client.connect(username='root', password='ya!2dkwy7-934^')
        if not success:
            logger.error("连接失败")
            return
        
        logger.info("连接成功，开始测试并发访问")
        
        # 创建锁
        telnet_lock = asyncio.Lock()
        
        async def execute_with_lock(command, task_id):
            """使用锁执行命令"""
            async with telnet_lock:
                logger.info(f"任务 {task_id} 开始执行: {command}")
                result = await client.execute_command(command)
                logger.info(f"任务 {task_id} 完成，结果长度: {len(result)}")
                return result
        
        # 并发执行多个命令
        tasks = []
        commands = [
            'ls -la /',
            'pwd',
            'whoami',
            'date',
            'ls -la /tmp'
        ]
        
        for i, cmd in enumerate(commands):
            task = execute_with_lock(cmd, i+1)
            tasks.append(task)
        
        # 等待所有任务完成
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 检查结果
        success_count = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"任务 {i+1} 失败: {result}")
            else:
                logger.info(f"任务 {i+1} 成功")
                success_count += 1
        
        logger.info(f"测试完成，成功: {success_count}/{len(tasks)}")
        
        # 断开连接
        await client.disconnect()
        
    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(test_concurrent_access()) 