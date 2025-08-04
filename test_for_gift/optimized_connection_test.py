#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化后的连接测试工具
验证telnet_connecter.py的优化效果
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

class OptimizedConnectionTester:
    """优化的连接测试器"""
    
    def __init__(self, host: str, screen_id: str):
        self.host = host
        self.screen_id = screen_id
        self.tn = Telnet_connector(host=host)
        self.test_commands = [
            "pidof mymqtt",
            "pidof pintura", 
            "pidof video_player"
        ]
    
    async def test_optimized_connection(self):
        """测试优化后的连接性能"""
        print(f"\n=== 测试优化连接: {self.screen_id} ({self.host}) ===")
        
        try:
            # 测试1: 预热连接
            log_timing("开始预热连接", self.screen_id)
            await self.tn.connect_and_warmup()
            log_timing("预热连接完成", self.screen_id)
            
            # 测试2: 健康检查
            log_timing("开始健康检查", self.screen_id)
            is_healthy = await self.tn.health_check()
            print(f"  健康检查结果: {'✓ 健康' if is_healthy else '✗ 不健康'}")
            log_timing(f"健康检查完成: {is_healthy}", self.screen_id)
            
            # 测试3: 快速命令执行
            log_timing("开始快速命令测试", self.screen_id)
            for i, cmd in enumerate(self.test_commands):
                start_time = time.time()
                result = await self.tn.send_command(cmd)
                duration = time.time() - start_time
                print(f"  {cmd} -> 耗时: {duration:.3f}s, 结果: {result.strip()[:20]}...")
                log_timing(f"命令 {cmd} 完成 ({duration:.3f}s)", self.screen_id)
            
            log_timing("快速命令测试完成", self.screen_id)
            
        except Exception as e:
            print(f"优化连接测试失败: {e}")
            log_timing(f"连接测试失败: {str(e)}", self.screen_id)
    
    async def test_connection_persistence(self, duration_minutes=2):
        """测试连接持久性（模拟长时间使用）"""
        print(f"\n=== 测试连接持久性: {self.screen_id} ({duration_minutes}分钟) ===")
        
        if not await self.tn.health_check():
            await self.tn.connect_and_warmup()
        
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        command_count = 0
        error_count = 0
        
        log_timing(f"开始持久性测试 ({duration_minutes}分钟)", self.screen_id)
        
        while time.time() < end_time:
            try:
                # 每10秒执行一次命令
                cmd = self.test_commands[command_count % len(self.test_commands)]
                
                # 先检查连接健康度
                if not await self.tn.health_check():
                    print(f"  连接不健康，正在重连...")
                    log_timing("检测到连接不健康，重连", self.screen_id)
                    await self.tn.ensure_connection()
                
                result = await self.tn.send_command(cmd)
                command_count += 1
                
                if command_count % 5 == 0:  # 每5个命令报告一次
                    elapsed = time.time() - start_time
                    print(f"  已执行 {command_count} 个命令，耗时 {elapsed:.1f}s，错误 {error_count} 次")
                
            except Exception as e:
                error_count += 1
                print(f"  命令执行失败: {e}")
                log_timing(f"命令失败: {str(e)}", self.screen_id)
            
            await asyncio.sleep(10)  # 10秒间隔
        
        total_time = time.time() - start_time
        success_rate = ((command_count - error_count) / command_count * 100) if command_count > 0 else 0
        
        print(f"  持久性测试完成:")
        print(f"    总时间: {total_time:.1f}s")
        print(f"    总命令: {command_count}")
        print(f"    成功率: {success_rate:.1f}%")
        print(f"    平均命令间隔: {total_time/command_count:.1f}s" if command_count > 0 else "")
        
        log_timing(f"持久性测试完成 (成功率: {success_rate:.1f}%)", self.screen_id)
    
    async def test_rapid_reconnection(self, cycles=5):
        """测试快速重连性能"""
        print(f"\n=== 测试快速重连: {self.screen_id} ({cycles}次) ===")
        
        reconnect_times = []
        
        for cycle in range(cycles):
            log_timing(f"重连测试 {cycle+1}/{cycles} 开始", self.screen_id)
            
            try:
                # 断开连接
                start_disconnect = time.time()
                await self.tn.disconnect()
                disconnect_time = time.time() - start_disconnect
                
                # 重新连接
                start_connect = time.time()
                await self.tn.connect_and_warmup()
                connect_time = time.time() - start_connect
                
                total_time = disconnect_time + connect_time
                reconnect_times.append(total_time)
                
                print(f"  重连 {cycle+1}: 断开 {disconnect_time:.3f}s + 连接 {connect_time:.3f}s = 总计 {total_time:.3f}s")
                log_timing(f"重连 {cycle+1} 完成 ({total_time:.3f}s)", self.screen_id)
                
                # 验证连接
                result = await self.tn.send_command("echo test")
                if "test" not in result:
                    print(f"  ⚠️ 重连 {cycle+1} 验证失败")
                
            except Exception as e:
                print(f"  ❌ 重连 {cycle+1} 失败: {e}")
                log_timing(f"重连 {cycle+1} 失败: {str(e)}", self.screen_id)
            
            if cycle < cycles - 1:
                await asyncio.sleep(1)  # 间隔1秒
        
        if reconnect_times:
            avg_time = sum(reconnect_times) / len(reconnect_times)
            min_time = min(reconnect_times)
            max_time = max(reconnect_times)
            
            print(f"  重连性能统计:")
            print(f"    平均时间: {avg_time:.3f}s")
            print(f"    最快时间: {min_time:.3f}s")
            print(f"    最慢时间: {max_time:.3f}s")
            print(f"    改进效果: {'✓ 优秀' if avg_time < 5 else '⚠️ 一般' if avg_time < 8 else '❌ 需要改进'}")

async def run_optimized_test():
    """运行优化测试"""
    test_devices = [
        ("192.168.1.36", "PinturaV2test09529"),
        ("192.168.1.4", "PSd4117cL000289"),
        ("192.168.1.7", "PinturaTest174280")
    ]
    
    print("🚀 开始优化后的连接性能测试...")
    log_timing("优化测试开始", "ALL")
    
    for host, screen_id in test_devices:
        print(f"\n{'='*60}")
        print(f"测试设备: {screen_id} ({host})")
        print('='*60)
        
        tester = OptimizedConnectionTester(host, screen_id)
        
        # 基础优化连接测试
        await tester.test_optimized_connection()
        await asyncio.sleep(2)
        
        # 快速重连测试
        await tester.test_rapid_reconnection(3)
        await asyncio.sleep(2)
        
        # 连接持久性测试（1分钟）
        await tester.test_connection_persistence(1)
        
        # 分析当前设备的连接状态
        print(f"\n--- {screen_id} 优化效果分析 ---")
        connection_monitor.print_analysis(screen_id)
        
        await asyncio.sleep(3)
    
    log_timing("优化测试完成", "ALL")
    
    # 最终分析
    print("\n" + "="*80)
    print("🎯 优化效果分析报告")
    print("="*80)
    
    # 时序分析
    analyze_timing()
    
    # 连接状态分析
    connection_monitor.print_analysis()
    
    print("\n📊 优化总结:")
    print("1. 连接建立时间: 目标 < 3秒")
    print("2. 重连时间: 目标 < 5秒") 
    print("3. 命令执行: 目标 < 2秒")
    print("4. 连接稳定性: 目标 > 95%")

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d ===> %(message)s'
    )
    
    print("🔧 优化后的连接测试工具")
    print("验证 telnet_connecter.py 的性能改进")
    print("-" * 50)
    
    try:
        asyncio.run(run_optimized_test())
    except KeyboardInterrupt:
        print("\n⏹️ 测试被用户中断")
        print("正在生成分析报告...")
        
        # 即使中断也要显示分析结果
        analyze_timing()
        connection_monitor.print_analysis()
        
        sys.exit(0)