#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IP历史记录管理模块

功能特点：
- IP地址历史记录
- 屏幕ID-IP关联记录
- 自动完成建议
- 历史记录清除
- 持久化存储

Author: AI Assistant
Date: 2024
Version: 1.0
"""

import json
import os
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from pathlib import Path


class IPHistoryManager:
    """IP历史记录管理器"""
    
    def __init__(self, history_file: str = "ip_history.json"):
        """
        初始化IP历史记录管理器
        
        Args:
            history_file (str): 历史记录文件路径
        """
        self.history_file = history_file
        self.history_data = {
            'ip_history': [],  # IP历史记录
            'device_history': {},  # 设备ID-IP关联记录
            'last_used': None,  # 最后使用的IP
            'created_time': datetime.now().isoformat(),
            'updated_time': datetime.now().isoformat()
        }
        
        # 配置日志
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 加载历史记录
        self._load_history()
    
    def _load_history(self):
        """加载历史记录"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                    
                # 合并数据，保持向后兼容
                if isinstance(loaded_data, dict):
                    self.history_data.update(loaded_data)
                elif isinstance(loaded_data, list):
                    # 兼容旧格式（只有IP列表）
                    self.history_data['ip_history'] = loaded_data
                
                self.logger.info(f"成功加载IP历史记录: {len(self.history_data.get('ip_history', []))} 条IP记录")
                self.logger.info(f"设备关联记录: {len(self.history_data.get('device_history', {}))} 个设备")
            else:
                self.logger.info("历史记录文件不存在，将创建新的记录")
                
        except Exception as e:
            self.logger.error(f"加载IP历史记录失败: {str(e)}")
            # 保持默认数据结构
    
    def _save_history(self):
        """保存历史记录"""
        try:
            self.history_data['updated_time'] = datetime.now().isoformat()
            
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history_data, f, ensure_ascii=False, indent=2)
                
            self.logger.debug("IP历史记录已保存")
            
        except Exception as e:
            self.logger.error(f"保存IP历史记录失败: {str(e)}")
    
    def add_ip(self, ip: str, device_id: Optional[str] = None) -> bool:
        """
        添加IP到历史记录
        
        Args:
            ip (str): IP地址
            device_id (str, optional): 设备ID
            
        Returns:
            bool: 是否成功添加
        """
        try:
            if not self._is_valid_ip(ip):
                self.logger.warning(f"无效的IP地址: {ip}")
                return False
            
            # 创建IP记录
            ip_record = {
                'ip': ip,
                'first_used': datetime.now().isoformat(),
                'last_used': datetime.now().isoformat(),
                'use_count': 1,
                'device_id': device_id
            }
            
            # 检查是否已存在
            existing_index = None
            for i, record in enumerate(self.history_data['ip_history']):
                if record['ip'] == ip:
                    existing_index = i
                    break
            
            if existing_index is not None:
                # 更新现有记录
                existing_record = self.history_data['ip_history'][existing_index]
                existing_record['last_used'] = datetime.now().isoformat()
                existing_record['use_count'] = existing_record.get('use_count', 0) + 1
                
                # 更新设备ID（如果提供）
                if device_id:
                    existing_record['device_id'] = device_id
                
                # 移动到列表前面（最近使用）
                self.history_data['ip_history'].pop(existing_index)
                self.history_data['ip_history'].insert(0, existing_record)
            else:
                # 添加新记录到前面
                self.history_data['ip_history'].insert(0, ip_record)
            
            # 限制历史记录数量
            max_history = 50
            if len(self.history_data['ip_history']) > max_history:
                self.history_data['ip_history'] = self.history_data['ip_history'][:max_history]
            
            # 更新设备关联记录
            if device_id:
                if device_id not in self.history_data['device_history']:
                    self.history_data['device_history'][device_id] = {
                        'device_id': device_id,
                        'ip_list': [],
                        'first_seen': datetime.now().isoformat(),
                        'last_seen': datetime.now().isoformat()
                    }
                
                device_record = self.history_data['device_history'][device_id]
                device_record['last_seen'] = datetime.now().isoformat()
                
                # 更新IP列表
                if ip not in device_record['ip_list']:
                    device_record['ip_list'].insert(0, ip)
                else:
                    # 移动到前面
                    device_record['ip_list'].remove(ip)
                    device_record['ip_list'].insert(0, ip)
                
                # 限制每个设备的IP记录数量
                if len(device_record['ip_list']) > 10:
                    device_record['ip_list'] = device_record['ip_list'][:10]
            
            # 更新最后使用的IP
            self.history_data['last_used'] = ip
            
            # 保存到文件
            self._save_history()
            
            self.logger.info(f"IP地址已添加到历史记录: {ip}" + (f" (设备: {device_id})" if device_id else ""))
            return True
            
        except Exception as e:
            self.logger.error(f"添加IP历史记录失败: {str(e)}")
            return False
    
    def get_ip_suggestions(self, partial_ip: str = "") -> List[Dict]:
        """
        获取IP建议列表
        
        Args:
            partial_ip (str): 部分IP地址用于过滤
            
        Returns:
            List[Dict]: IP建议列表，包含IP、设备ID、使用次数等信息
        """
        try:
            suggestions = []
            
            for record in self.history_data['ip_history']:
                ip = record['ip']
                
                # 过滤匹配的IP
                if not partial_ip or ip.startswith(partial_ip):
                    suggestion = {
                        'ip': ip,
                        'device_id': record.get('device_id'),
                        'use_count': record.get('use_count', 1),
                        'last_used': record.get('last_used'),
                        'display_text': self._format_ip_display(record)
                    }
                    suggestions.append(suggestion)
            
            return suggestions
            
        except Exception as e:
            self.logger.error(f"获取IP建议失败: {str(e)}")
            return []
    
    def get_device_history(self) -> Dict[str, Dict]:
        """
        获取设备历史记录
        
        Returns:
            Dict[str, Dict]: 设备ID到设备信息的映射
        """
        return self.history_data.get('device_history', {}).copy()
    
    def get_last_used_ip(self) -> Optional[str]:
        """
        获取最后使用的IP
        
        Returns:
            str: 最后使用的IP地址，如果没有则返回None
        """
        return self.history_data.get('last_used')
    
    def clear_history(self, clear_devices: bool = False) -> bool:
        """
        清空历史记录
        
        Args:
            clear_devices (bool): 是否同时清空设备关联记录
            
        Returns:
            bool: 是否成功清空
        """
        try:
            self.history_data['ip_history'] = []
            self.history_data['last_used'] = None
            
            if clear_devices:
                self.history_data['device_history'] = {}
            
            self._save_history()
            
            self.logger.info("IP历史记录已清空" + (" (包括设备记录)" if clear_devices else ""))
            return True
            
        except Exception as e:
            self.logger.error(f"清空历史记录失败: {str(e)}")
            return False
    
    def remove_ip(self, ip: str) -> bool:
        """
        移除特定IP记录
        
        Args:
            ip (str): 要移除的IP地址
            
        Returns:
            bool: 是否成功移除
        """
        try:
            # 从IP历史中移除
            original_count = len(self.history_data['ip_history'])
            self.history_data['ip_history'] = [
                record for record in self.history_data['ip_history'] 
                if record['ip'] != ip
            ]
            
            # 从设备记录中移除
            for device_id, device_record in self.history_data['device_history'].items():
                if ip in device_record['ip_list']:
                    device_record['ip_list'].remove(ip)
            
            # 如果是最后使用的IP，清空记录
            if self.history_data.get('last_used') == ip:
                if self.history_data['ip_history']:
                    self.history_data['last_used'] = self.history_data['ip_history'][0]['ip']
                else:
                    self.history_data['last_used'] = None
            
            removed_count = original_count - len(self.history_data['ip_history'])
            if removed_count > 0:
                self._save_history()
                self.logger.info(f"已移除IP记录: {ip}")
                return True
            else:
                self.logger.warning(f"未找到要移除的IP记录: {ip}")
                return False
                
        except Exception as e:
            self.logger.error(f"移除IP记录失败: {str(e)}")
            return False
    
    def _is_valid_ip(self, ip: str) -> bool:
        """验证IP地址格式"""
        try:
            parts = ip.split('.')
            if len(parts) != 4:
                return False
            
            for part in parts:
                if not part.isdigit():
                    return False
                num = int(part)
                if num < 0 or num > 255:
                    return False
            
            return True
            
        except Exception:
            return False
    
    def _format_ip_display(self, record: Dict) -> str:
        """格式化IP显示文本"""
        ip = record['ip']
        device_id = record.get('device_id')
        use_count = record.get('use_count', 1)
        
        if device_id:
            return f"{device_id} - {ip} (使用{use_count}次)"
        else:
            return f"{ip} (使用{use_count}次)"
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        try:
            return {
                'total_ips': len(self.history_data['ip_history']),
                'total_devices': len(self.history_data['device_history']),
                'last_used_ip': self.history_data.get('last_used'),
                'created_time': self.history_data.get('created_time'),
                'updated_time': self.history_data.get('updated_time')
            }
        except Exception as e:
            self.logger.error(f"获取统计信息失败: {str(e)}")
            return {}


# 设备ID读取工具函数
async def read_device_id_from_remote(telnet_client) -> Optional[str]:
    """
    从远程设备读取屏幕ID
    
    Args:
        telnet_client: Telnet客户端实例
        
    Returns:
        str: 设备ID，如果读取失败返回None
    """
    try:
        logger = logging.getLogger("DeviceIDReader")
        
        # 尝试读取设备ID文件
        config_file = "/customer/screenId.ini"
        result = await telnet_client.execute_command(f'cat "{config_file}"')
        
        if "No such file" in result or "not found" in result:
            logger.warning(f"设备ID配置文件不存在: {config_file}")
            return None
        
        # 解析配置文件内容
        lines = result.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('deviceId='):
                device_id = line.split('=', 1)[1].strip()
                if device_id:
                    logger.info(f"成功读取设备ID: {device_id}")
                    return device_id
                else:
                    logger.warning("设备ID为空")
                    return None
        
        logger.warning("未找到deviceId配置项")
        return None
        
    except Exception as e:
        logger = logging.getLogger("DeviceIDReader")
        logger.error(f"读取设备ID失败: {str(e)}")
        return None


# 使用示例
if __name__ == "__main__":
    # 创建IP历史管理器
    ip_manager = IPHistoryManager()
    
    # 添加一些测试数据
    ip_manager.add_ip("192.168.1.100", "M1220401L000189")
    ip_manager.add_ip("192.168.1.101", "M1220401L000190")
    ip_manager.add_ip("10.0.0.100")
    
    # 获取建议
    suggestions = ip_manager.get_ip_suggestions("192.168")
    print("IP建议:")
    for suggestion in suggestions:
        print(f"  {suggestion['display_text']}")
    
    # 获取统计信息
    stats = ip_manager.get_statistics()
    print(f"\n统计信息: {stats}") 