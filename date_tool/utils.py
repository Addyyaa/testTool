"""
时间转换工具 - 便捷函数
提供无需实例化即可使用的便捷函数
"""

from typing import Dict, Any
from .converter import DateTimeConverter

def convert_timestamp_to_time(
    timestamp: int, 
    max_unit: str = "Y", 
    min_unit: str = "S",
    filter_zero: bool = False,
    return_format: str = "zh"
) -> Dict[str, Any]:
    """
    便捷函数：将时间戳转换为时间单位分解结果
    
    Args:
        timestamp: 时间戳（秒）
        max_unit: 最大时间单位（Y/MO/D/H/M/S）
        min_unit: 最小时间单位（Y/MO/D/H/M/S）
        filter_zero: 是否过滤值为0的时间单位
        return_format: 返回格式（'zh': 中文, 'en': 英文键名）
        
    Returns:
        Dict[str, Any]: 时间单位分解结果
        
    Examples:
        >>> convert_timestamp_to_time(283822, "MO", "S")
        {'月': 3, '日': 7, '时': 6, '分': 57, '秒': 2}
        
        >>> convert_timestamp_to_time(283822, "MO", "S", filter_zero=True)
        {'月': 3, '日': 7, '时': 6, '分': 57, '秒': 2}
    """
    converter = DateTimeConverter()
    return converter.convert_timestamp_to_time(timestamp, max_unit, min_unit, filter_zero, return_format)

def format_time_duration(
    timestamp: int, 
    max_unit: str = "Y", 
    min_unit: str = "S",
    separator: str = " ",
    filter_zero: bool = True
) -> str:
    """
    便捷函数：将时间戳格式化为可读的时间持续时间字符串
    
    Args:
        timestamp: 时间戳（秒）
        max_unit: 最大时间单位
        min_unit: 最小时间单位
        separator: 分隔符
        filter_zero: 是否过滤零值
        
    Returns:
        str: 格式化后的时间字符串
        
    Examples:
        >>> format_time_duration(283822, "MO", "S")
        "3月 7日 6时 57分 2秒"
        
        >>> format_time_duration(283822, "D", "M", separator=", ")
        "3日, 6时, 57分"
    """
    converter = DateTimeConverter()
    return converter.format_time_duration(timestamp, max_unit, min_unit, separator, filter_zero)

# 导出的函数
__all__ = [
    'convert_timestamp_to_time',
    'format_time_duration'
] 