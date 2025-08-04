#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
连接问题专项测试工具
用于快速定位和复现连接问题
"""

import sys
import time
import asyncio
import logging
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from telnet_connecter import Telnet_connector
from debug_connection_monitor import connection_monitor, log_timing, analyze_timing

logger = logging.getLogger(__name__)

class ConnectionTester:
    """连接测试器"""
    
    def __init__(self, host: str, screen_id: str):
        self.host = host
        self.screen_id = screen_id
        self.tn = Telnet_connector(host=host)
        self.test_commands = [
            "pidof mymqtt",
            "pidof pintura", 
            "pidof video_player",
            "echo test",
            "pwd",
            "date"
        ]
    
    async def test_single_connection(self):
        """测试单个连接的稳定性"""
        print(f"\n=== 测试单个连接: {self.screen_id} ({self.host}) ===")
        
        try:
            # 初始连接
            log_timing("开始初始连接", self.screen_id)
            await self.tn.connect()
            log_timing("初始连接完成", self.screen_id)
            
            # 记录连接状态
            connection_monitor.record_connection_state(self.screen_id, self.tn, "initial_connect")
            
            # 执行多个命令测试
            for i, cmd in enumerate(self.test_commands):
                log_timing(f"执行命令 {i+1}/{len(self.test_commands)}: {cmd}", self.screen_id)
                
                # 记录命令前状态
                connection_monitor.record_connection_state(self.screen_id, self.tn, f"before_{cmd}")
                
                try:
                    result = await self.tn.send_command(cmd)
                    print(f"  {cmd} -> {result.strip()[:50]}...")
                    
                    # 记录命令后状态
                    connection_monitor.record_connection_state(self.screen_id, self.tn, f"after_{cmd}")
                    
                except Exception as e:
                    print(f"  {cmd} -> ERROR: {e}")
                    connection_monitor.record_connection_state(self.screen_id, self.tn, f"error_{cmd}", str(e))
                
                # 短暂等待
                await asyncio.sleep(0.5)
            
            log_timing("所有命令执行完成", self.screen_id)
            
        except Exception as e:
            print(f"连接测试失败: {e}")
            log_timing(f"连接测试失败: {str(e)}", self.screen_id)
            connection_monitor.record_connection_state(self.screen_id, self.tn, "connection_test_failed", str(e))
    
    async def test_rapid_commands(self, count: int = 10):
        """测试快速连续命令"""
        print(f"\n=== 测试快速连续命令: {self.screen_id} ===")
        
        try:
            if not self.tn.writer:
                await self.tn.connect()
            
            log_timing(f"开始快速命令测试 ({count}次)", self.screen_id)
            
            for i in range(count):
                cmd = f"echo rapid_test_{i}"
                log_timing(f"快速命令 {i+1}/{count}", self.screen_id)
                
                connection_monitor.record_connection_state(self.screen_id, self.tn, f"rapid_{i}")
                
                try:
                    result = await self.tn.send_command(cmd)
                    print(f"  快速命令 {i+1}: OK")
                except Exception as e:
                    print(f"  快速命令 {i+1}: ERROR - {e}")
                    connection_monitor.record_connection_state(self.screen_id, self.tn, f"rapid_{i}_error", str(e))
                
                # 很短的等待时间
                await asyncio.sleep(0.1)
            
            log_timing("快速命令测试完成", self.screen_id)
            
        except Exception as e:
            print(f"快速命令测试失败: {e}")
            log_timing(f"快速命令测试失败: {str(e)}", self.screen_id)
    
    async def test_reconnection_cycle(self, cycles: int = 3):
        """测试重连循环"""
        print(f"\n=== 测试重连循环: {self.screen_id} ({cycles}次) ===")
        
        for cycle in range(cycles):
            log_timing(f"重连循环 {cycle+1}/{cycles} 开始", self.screen_id)
            
            try:
                # 断开连接
                log_timing("断开连接", self.screen_id)
                await self.tn.disconnect()
                connection_monitor.record_connection_state(self.screen_id, self.tn, "disconnect")
                
                await asyncio.sleep(1)
                
                # 重新连接
                log_timing("重新连接", self.screen_id)
                await self.tn.connect()
                connection_monitor.record_connection_state(self.screen_id, self.tn, "reconnect")
                
                # 测试连接
                result = await self.tn.send_command("echo reconnect_test")
                print(f"  重连循环 {cycle+1}: OK - {result.strip()}")
                
                log_timing(f"重连循环 {cycle+1}/{cycles} 完成", self.screen_id)
                
            except Exception as e:
                print(f"  重连循环 {cycle+1}: ERROR - {e}")
                connection_monitor.record_connection_state(self.screen_id, self.tn, f"reconnect_cycle_{cycle}_error", str(e))
                log_timing(f"重连循环 {cycle+1} 失败: {str(e)}", self.screen_id)
            
            await asyncio.sleep(2)
    
    async def test_concurrent_operations(self):
        """测试并发操作（模拟实际使用场景）"""
        print(f"\n=== 测试并发操作: {self.screen_id} ===")
        
        try:
            if not self.tn.writer:
                await self.tn.connect()
            
            log_timing("开始并发操作测试", self.screen_id)
            
            # 模拟应用重启检查 + 显示模式切换的并发场景
            tasks = []
            
            # 任务1: 连续的pidof命令（模拟应用重启检查）
            async def pidof_task():
                for cmd in ["pidof mymqtt", "pidof pintura", "pidof video_player"]:
                    try:
                        connection_monitor.record_connection_state(self.screen_id, self.tn, f"concurrent_{cmd}")
                        result = await self.tn.send_command(cmd)
                        print(f"  并发pidof: {cmd} -> OK")
                        await asyncio.sleep(0.5)
                    except Exception as e:
                        print(f"  并发pidof: {cmd} -> ERROR: {e}")
                        connection_monitor.record_connection_state(self.screen_id, self.tn, f"concurrent_{cmd}_error", str(e))
            
            # 任务2: 其他命令（模拟其他操作）
            async def other_task():
                for i in range(3):
                    try:
                        cmd = f"echo concurrent_test_{i}"
                        connection_monitor.record_connection_state(self.screen_id, self.tn, f"concurrent_other_{i}")
                        result = await self.tn.send_command(cmd)
                        print(f"  并发其他: {cmd} -> OK")
                        await asyncio.sleep(0.3)
                    except Exception as e:
                        print(f"  并发其他: {cmd} -> ERROR: {e}")
                        connection_monitor.record_connection_state(self.screen_id, self.tn, f"concurrent_other_{i}_error", str(e))
            
            # 注意：这里不是真正的并发，因为telnet连接不支持真正的并发
            # 但可以测试快速切换的场景
            await pidof_task()
            await other_task()
            
            log_timing("并发操作测试完成", self.screen_id)
            
        except Exception as e:
            print(f"并发操作测试失败: {e}")
            log_timing(f"并发操作测试失败: {str(e)}", self.screen_id)

async def run_comprehensive_test():
    """运行综合测试"""
    # 测试设备列表
    test_devices = [
        ("192.168.1.36", "PinturaV2test09529"),
        ("192.168.1.4", "PSd4117cL000289"),
        ("192.168.1.7", "PinturaTest174280")
    ]
    
    print("开始连接问题综合测试...")
    log_timing("综合测试开始", "ALL")
    
    for host, screen_id in test_devices:
        print(f"\n{'='*60}")
        print(f"测试设备: {screen_id} ({host})")
        print('='*60)
        
        tester = ConnectionTester(host, screen_id)
        
        # 基础连接测试
        await tester.test_single_connection()
        await asyncio.sleep(2)
        
        # 快速命令测试
        await tester.test_rapid_commands(5)
        await asyncio.sleep(2)
        
        # 重连测试
        await tester.test_reconnection_cycle(2)
        await asyncio.sleep(2)
        
        # 并发操作测试
        await tester.test_concurrent_operations()
        
        # 分析当前设备的连接状态
        print(f"\n--- {screen_id} 连接状态分析 ---")
        connection_monitor.print_analysis(screen_id)
        
        await asyncio.sleep(3)
    
    log_timing("综合测试完成", "ALL")
    
    # 最终分析
    print("\n" + "="*80)
    print("最终综合分析报告")
    print("="*80)
    
    # 时序分析
    analyze_timing()
    
    # 所有设备的连接分析
    connection_monitor.print_analysis()

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d ===> %(message)s'
    )
    
    print("连接问题专项测试工具")
    print("这个工具将帮助定位连接问题的根本原因")
    print("-" * 50)
    
    try:
        asyncio.run(run_comprehensive_test())
    except KeyboardInterrupt:
        print("\n测试被用户中断")
        print("正在生成分析报告...")
        
        # 即使中断也要显示分析结果
        analyze_timing()
        connection_monitor.print_analysis()
        
        sys.exit(0)