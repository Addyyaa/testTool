"""
时间转换工具 - 数据类型定义
包含时间单位的数据类和枚举定义
"""

from dataclasses import dataclass
from enum import Enum

@dataclass
class TimeUnit:
    """时间单位配置类"""
    key: str
    zh_name: str
    seconds: int
    priority: int

class TimeUnitType(Enum):
    """时间单位类型枚举"""
    YEAR = TimeUnit("Y", "年", 365 * 24 * 60 * 60, 6)
    MONTH = TimeUnit("MO", "月", 30 * 24 * 60 * 60, 5)
    DAY = TimeUnit("D", "日", 24 * 60 * 60, 4)
    HOUR = TimeUnit("H", "时", 60 * 60, 3)
    MINUTE = TimeUnit("M", "分", 60, 2)
    SECOND = TimeUnit("S", "秒", 1, 1)

# 导出的类型
__all__ = [
    'TimeUnit',
    'TimeUnitType'
] 