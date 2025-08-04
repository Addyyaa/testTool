#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
连接状态监控和调试工具
用于定位 switch_display_mode.py 中的连接问题
"""

import asyncio
import time
import logging
import threading
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class ConnectionState:
    """连接状态记录"""
    timestamp: float
    has_writer: bool
    has_reader: bool
    writer_closing: bool
    transport_valid: bool
    loop_running: bool
    proactor_valid: bool
    last_command: Optional[str] = None
    error_msg: Optional[str] = None

class ConnectionMonitor:
    """连接状态监控器"""
    
    def __init__(self):
        self.connection_states: Dict[str, list] = {}
        self.command_history: Dict[str, list] = {}
        self.error_count: Dict[str, int] = {}
        self.lock = threading.Lock()
        
    def record_connection_state(self, screen_id: str, tn_connector, command: str = None, error: str = None):
        """记录连接状态"""
        try:
            state = ConnectionState(
                timestamp=time.time(),
                has_writer=hasattr(tn_connector, 'writer') and tn_connector.writer is not None,
                has_reader=hasattr(tn_connector, 'reader') and tn_connector.reader is not None,
                writer_closing=self._check_writer_closing(tn_connector),
                transport_valid=self._check_transport_valid(tn_connector),
                loop_running=self._check_loop_running(tn_connector),
                proactor_valid=self._check_proactor_valid(tn_connector),
                last_command=command,
                error_msg=error
            )
            
            with self.lock:
                if screen_id not in self.connection_states:
                    self.connection_states[screen_id] = []
                    self.command_history[screen_id] = []
                    self.error_count[screen_id] = 0
                
                self.connection_states[screen_id].append(state)
                if command:
                    self.command_history[screen_id].append((time.time(), command))
                if error:
                    self.error_count[screen_id] += 1
                
                # 保持最近100条记录
                if len(self.connection_states[screen_id]) > 100:
                    self.connection_states[screen_id] = self.connection_states[screen_id][-100:]
                if len(self.command_history[screen_id]) > 100:
                    self.command_history[screen_id] = self.command_history[screen_id][-100:]
                    
        except Exception as e:
            logging.error(f"记录连接状态失败: {e}")
    
    def _check_writer_closing(self, tn_connector) -> bool:
        """检查writer是否正在关闭"""
        try:
            if hasattr(tn_connector, 'writer') and tn_connector.writer:
                return tn_connector.writer.is_closing()
        except:
            pass
        return False
    
    def _check_transport_valid(self, tn_connector) -> bool:
        """检查传输层是否有效"""
        try:
            if hasattr(tn_connector, 'writer') and tn_connector.writer:
                if hasattr(tn_connector.writer, '_transport'):
                    return tn_connector.writer._transport is not None
        except:
            pass
        return False
    
    def _check_loop_running(self, tn_connector) -> bool:
        """检查事件循环是否运行"""
        try:
            if hasattr(tn_connector, 'writer') and tn_connector.writer:
                if hasattr(tn_connector.writer, '_transport') and tn_connector.writer._transport:
                    if hasattr(tn_connector.writer._transport, '_loop'):
                        loop = tn_connector.writer._transport._loop
                        return loop is not None and loop.is_running()
        except:
            pass
        return False
    
    def _check_proactor_valid(self, tn_connector) -> bool:
        """检查proactor是否有效"""
        try:
            if hasattr(tn_connector, 'writer') and tn_connector.writer:
                if hasattr(tn_connector.writer, '_transport') and tn_connector.writer._transport:
                    if hasattr(tn_connector.writer._transport, '_loop'):
                        loop = tn_connector.writer._transport._loop
                        if loop and hasattr(loop, '_proactor'):
                            return loop._proactor is not None
        except:
            pass
        return False
    
    def analyze_connection_pattern(self, screen_id: str) -> Dict[str, Any]:
        """分析连接模式"""
        with self.lock:
            if screen_id not in self.connection_states:
                return {"error": "没有找到连接记录"}
            
            states = self.connection_states[screen_id]
            if not states:
                return {"error": "连接状态记录为空"}
            
            # 分析状态变化
            state_changes = []
            last_state = None
            
            for state in states:
                current_key = (state.has_writer, state.writer_closing, state.transport_valid, state.proactor_valid)
                if last_state != current_key:
                    state_changes.append({
                        "timestamp": datetime.fromtimestamp(state.timestamp).strftime("%H:%M:%S.%f")[:-3],
                        "has_writer": state.has_writer,
                        "writer_closing": state.writer_closing,
                        "transport_valid": state.transport_valid,
                        "proactor_valid": state.proactor_valid,
                        "command": state.last_command,
                        "error": state.error_msg
                    })
                    last_state = current_key
            
            # 统计信息
            total_states = len(states)
            error_states = len([s for s in states if s.error_msg])
            transport_invalid_count = len([s for s in states if not s.transport_valid])
            proactor_invalid_count = len([s for s in states if not s.proactor_valid])
            
            return {
                "screen_id": screen_id,
                "total_records": total_states,
                "error_count": self.error_count.get(screen_id, 0),
                "transport_invalid_count": transport_invalid_count,
                "proactor_invalid_count": proactor_invalid_count,
                "state_changes": state_changes[-10:],  # 最近10次状态变化
                "recent_commands": self.command_history.get(screen_id, [])[-5:],  # 最近5个命令
                "pattern_analysis": self._detect_patterns(states)
            }
    
    def _detect_patterns(self, states) -> Dict[str, Any]:
        """检测问题模式"""
        patterns = {
            "frequent_transport_failures": 0,
            "proactor_null_occurrences": 0,
            "rapid_state_changes": 0,
            "command_failure_rate": 0.0
        }
        
        # 检测传输层频繁失效
        transport_failures = 0
        for i in range(1, len(states)):
            if states[i-1].transport_valid and not states[i].transport_valid:
                transport_failures += 1
        patterns["frequent_transport_failures"] = transport_failures
        
        # 检测proactor为空的情况
        patterns["proactor_null_occurrences"] = len([s for s in states if not s.proactor_valid])
        
        # 检测快速状态变化（可能的竞态条件）
        rapid_changes = 0
        for i in range(1, len(states)):
            if states[i].timestamp - states[i-1].timestamp < 0.1:  # 100ms内的变化
                rapid_changes += 1
        patterns["rapid_state_changes"] = rapid_changes
        
        # 计算命令失败率
        error_states = len([s for s in states if s.error_msg])
        if states:
            patterns["command_failure_rate"] = error_states / len(states)
        
        return patterns
    
    def print_analysis(self, screen_id: str = None):
        """打印分析结果"""
        if screen_id:
            analysis = self.analyze_connection_pattern(screen_id)
            self._print_single_analysis(analysis)
        else:
            # 打印所有设备的分析
            with self.lock:
                for sid in self.connection_states.keys():
                    analysis = self.analyze_connection_pattern(sid)
                    self._print_single_analysis(analysis)
                    print("-" * 80)
    
    def _print_single_analysis(self, analysis):
        """打印单个设备的分析结果"""
        print(f"\n=== 连接分析报告: {analysis.get('screen_id', 'Unknown')} ===")
        print(f"总记录数: {analysis.get('total_records', 0)}")
        print(f"错误次数: {analysis.get('error_count', 0)}")
        print(f"传输层失效次数: {analysis.get('transport_invalid_count', 0)}")
        print(f"Proactor失效次数: {analysis.get('proactor_invalid_count', 0)}")
        
        patterns = analysis.get('pattern_analysis', {})
        print(f"\n模式分析:")
        print(f"  传输层频繁失效: {patterns.get('frequent_transport_failures', 0)} 次")
        print(f"  Proactor为空: {patterns.get('proactor_null_occurrences', 0)} 次")
        print(f"  快速状态变化: {patterns.get('rapid_state_changes', 0)} 次")
        print(f"  命令失败率: {patterns.get('command_failure_rate', 0):.2%}")
        
        print(f"\n最近状态变化:")
        for change in analysis.get('state_changes', []):
            print(f"  {change['timestamp']} - Writer:{change['has_writer']} "
                  f"Closing:{change['writer_closing']} Transport:{change['transport_valid']} "
                  f"Proactor:{change['proactor_valid']} Cmd:{change['command']} "
                  f"Error:{change['error']}")
        
        print(f"\n最近命令:")
        for ts, cmd in analysis.get('recent_commands', []):
            print(f"  {datetime.fromtimestamp(ts).strftime('%H:%M:%S.%f')[:-3]} - {cmd}")

# 全局监控实例
connection_monitor = ConnectionMonitor()

def monitor_connection_wrapper(original_send_command):
    """装饰器：监控send_command方法"""
    async def wrapper(self, command, *args, **kwargs):
        screen_id = getattr(self, 'host', 'unknown')
        
        # 记录命令发送前的状态
        connection_monitor.record_connection_state(screen_id, self, command)
        
        try:
            result = await original_send_command(command, *args, **kwargs)
            # 记录成功状态
            connection_monitor.record_connection_state(screen_id, self, command)
            return result
        except Exception as e:
            # 记录错误状态
            connection_monitor.record_connection_state(screen_id, self, command, str(e))
            raise
    
    return wrapper

def add_timing_analysis():
    """添加时序分析"""
    timing_log = []
    
    def log_timing(operation: str, screen_id: str = ""):
        """记录操作时间"""
        timestamp = time.time()
        timing_log.append({
            "timestamp": timestamp,
            "time_str": datetime.fromtimestamp(timestamp).strftime("%H:%M:%S.%f")[:-3],
            "operation": operation,
            "screen_id": screen_id
        })
        print(f"[TIMING] {datetime.fromtimestamp(timestamp).strftime('%H:%M:%S.%f')[:-3]} - {operation} ({screen_id})")
    
    def analyze_timing():
        """分析时序"""
        if len(timing_log) < 2:
            return
        
        print("\n=== 时序分析 ===")
        for i in range(1, len(timing_log)):
            prev = timing_log[i-1]
            curr = timing_log[i]
            interval = curr["timestamp"] - prev["timestamp"]
            print(f"{curr['time_str']} - {curr['operation']} (间隔: {interval:.3f}s)")
        
        # 检测异常间隔
        intervals = []
        for i in range(1, len(timing_log)):
            intervals.append(timing_log[i]["timestamp"] - timing_log[i-1]["timestamp"])
        
        if intervals:
            avg_interval = sum(intervals) / len(intervals)
            print(f"\n平均间隔: {avg_interval:.3f}s")
            
            abnormal_intervals = [(i, interval) for i, interval in enumerate(intervals) if abs(interval - avg_interval) > avg_interval * 0.5]
            if abnormal_intervals:
                print("异常间隔:")
                for i, interval in abnormal_intervals:
                    print(f"  位置 {i}: {interval:.3f}s (正常: {avg_interval:.3f}s)")
    
    return log_timing, analyze_timing

# 创建时序分析工具
log_timing, analyze_timing = add_timing_analysis()

if __name__ == "__main__":
    # 测试代码
    print("连接监控工具已加载")
    print("使用方法:")
    print("1. 在主程序中导入: from debug_connection_monitor import connection_monitor, log_timing")
    print("2. 在关键位置添加: connection_monitor.record_connection_state(screen_id, tn_connector, command)")
    print("3. 在关键操作添加: log_timing('操作描述', screen_id)")
    print("4. 分析结果: connection_monitor.print_analysis()")