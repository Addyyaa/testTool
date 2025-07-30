"""
时间转换工具 - 核心转换器
包含时间戳转换为各种时间单位的主要逻辑
"""

import logging
from typing import Dict, Any

from .types import TimeUnit, TimeUnitType

logger = logging.getLogger(__name__)

class DateTimeConverter:
    """时间转换器类"""
    
    def __init__(self):
        """初始化时间转换器"""
        # 时间单位映射表 - 便于查找和扩展
        self._time_units = {unit.value.key: unit.value for unit in TimeUnitType}
        
    def convert_timestamp_to_time(
        self, 
        timestamp: int, 
        max_unit: str = "Y", 
        min_unit: str = "S",
        filter_zero: bool = False,
        return_format: str = "zh"
    ) -> Dict[str, Any]:
        """
        将时间戳转换为时间单位分解结果
        
        Args:
            timestamp: 时间戳（秒）
            max_unit: 最大时间单位（Y/MO/D/H/M/S）
            min_unit: 最小时间单位（Y/MO/D/H/M/S）
            filter_zero: 是否过滤值为0的时间单位
            return_format: 返回格式（'zh': 中文, 'en': 英文键名）
            
        Returns:
            Dict[str, Any]: 时间单位分解结果
            
        Raises:
            ValueError: 当输入参数不合法时抛出
            
        Examples:
            >>> converter = DateTimeConverter()
            >>> converter.convert_timestamp_to_time(283822, "MO", "S")
            {'月': 3, '日': 7, '时': 6, '分': 57, '秒': 2}
            
            >>> converter.convert_timestamp_to_time(283822, "MO", "S", filter_zero=True)
            {'月': 3, '日': 7, '时': 6, '分': 57, '秒': 2}
            
            >>> converter.convert_timestamp_to_time(283822, "MO", "S", return_format="en")
            {'MO': 3, 'D': 7, 'H': 6, 'M': 57, 'S': 2}
        """
        # 参数验证和标准化
        max_unit = max_unit.upper()
        min_unit = min_unit.upper()
        
        # 验证时间单位是否存在
        if max_unit not in self._time_units:
            raise ValueError(f"不支持的时间单位: {max_unit}")
        if min_unit not in self._time_units:
            raise ValueError(f"不支持的时间单位: {min_unit}")
            
        # 验证时间戳
        if not isinstance(timestamp, int) or timestamp < 0:
            raise ValueError("时间戳必须为非负整数")
            
        # 验证单位层级关系
        max_priority = self._time_units[max_unit].priority
        min_priority = self._time_units[min_unit].priority
        
        if max_priority < min_priority:
            raise ValueError(f"最大单位 {max_unit} 不能小于最小单位 {min_unit}")
        
        # 计算时间分解
        result = {}
        remaining_timestamp = timestamp
        
        # 按优先级排序处理时间单位
        sorted_units = sorted(
            self._time_units.values(),
            key=lambda x: x.priority,
            reverse=True
        )
        
        for unit in sorted_units:
            # 检查是否在指定范围内
            if unit.priority > max_priority or unit.priority < min_priority:
                continue
                
            # 计算当前单位的值
            unit_value = remaining_timestamp // unit.seconds
            remaining_timestamp = remaining_timestamp % unit.seconds
            
            # 根据返回格式和过滤条件决定是否添加到结果
            if not filter_zero or unit_value > 0:
                key = unit.zh_name if return_format == "zh" else unit.key
                result[key] = unit_value
                
        return result
    
    def get_supported_time_units(self) -> Dict[str, str]:
        """
        获取支持的时间单位列表
        
        Returns:
            Dict[str, str]: 时间单位键名到中文名的映射
        """
        return {unit.key: unit.zh_name for unit in self._time_units.values()}
    
    def add_custom_time_unit(self, key: str, zh_name: str, seconds: int, priority: int) -> None:
        """
        添加自定义时间单位（扩展功能）
        
        Args:
            key: 时间单位键名
            zh_name: 中文名称
            seconds: 对应的秒数
            priority: 优先级（数字越大优先级越高）
        """
        if key in self._time_units:
            logger.warning(f"时间单位 {key} 已存在，将被覆盖")
            
        self._time_units[key] = TimeUnit(key, zh_name, seconds, priority)
        logger.info(f"添加自定义时间单位: {key} -> {zh_name}")
    
    def remove_time_unit(self, key: str) -> bool:
        """
        移除指定的时间单位
        
        Args:
            key: 时间单位键名
            
        Returns:
            bool: 是否成功移除
        """
        key = key.upper()
        if key in self._time_units:
            del self._time_units[key]
            logger.info(f"移除时间单位: {key}")
            return True
        else:
            logger.warning(f"时间单位 {key} 不存在")
            return False
    
    def format_time_duration(
        self, 
        timestamp: int, 
        max_unit: str = "Y", 
        min_unit: str = "S",
        separator: str = " ",
        filter_zero: bool = True
    ) -> str:
        """
        将时间戳格式化为可读的时间持续时间字符串
        
        Args:
            timestamp: 时间戳（秒）
            max_unit: 最大时间单位
            min_unit: 最小时间单位
            separator: 分隔符
            filter_zero: 是否过滤零值
            
        Returns:
            str: 格式化后的时间字符串
            
        Examples:
            >>> converter = DateTimeConverter()
            >>> converter.format_time_duration(283822, "MO", "S")
            "3月 7日 6时 57分 2秒"
        """
        time_dict = self.convert_timestamp_to_time(
            timestamp, max_unit, min_unit, filter_zero=filter_zero
        )
        
        if not time_dict:
            return "0秒"
            
        # 按优先级排序
        sorted_items = []
        for unit in sorted(self._time_units.values(), key=lambda x: x.priority, reverse=True):
            if unit.zh_name in time_dict:
                value = time_dict[unit.zh_name]
                if value > 0 or not filter_zero:
                    sorted_items.append(f"{value}{unit.zh_name}")
        
        return separator.join(sorted_items)

# 导出的类
__all__ = [
    'DateTimeConverter'
] 