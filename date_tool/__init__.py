"""
时间转换工具包
提供时间戳转换为各种时间单位的功能

主要功能：
- 时间戳转换为时间单位分解
- 时间持续时间格式化
- 支持自定义时间单位
- 多种输出格式支持
"""

# 导入数据类型
from .types import TimeUnit, TimeUnitType

# 导入核心转换器
from .converter import DateTimeConverter

# 导入便捷函数
from .utils import convert_timestamp_to_time, format_time_duration

# 版本信息
__version__ = "1.0.0"
__author__ = "Addyya"
__email__ = "addyyaaa@gmail.com"

# 包的主要导出
__all__ = [
    # 数据类型
    'TimeUnit',
    'TimeUnitType',
    
    # 核心类
    'DateTimeConverter',
    
    # 便捷函数
    'convert_timestamp_to_time',
    'format_time_duration',
    
    # 版本信息
    '__version__',
]

# 包级别的便捷访问
def get_version():
    """获取包版本信息"""
    return __version__

def get_supported_units():
    """获取支持的时间单位"""
    converter = DateTimeConverter()
    return converter.get_supported_time_units()

# 示例用法（仅在直接运行时显示）
if __name__ == "__main__":
    print(f"时间转换工具包 v{__version__}")
    print("=" * 40)
    
    # 基本示例
    timestamp = 283822
    print(f"时间戳: {timestamp} 秒")
    
    # 使用便捷函数
    result = convert_timestamp_to_time(timestamp, "MO", "S")
    print(f"转换结果: {result}")
    
    # 格式化字符串
    formatted = format_time_duration(timestamp, "MO", "S")
    print(f"格式化: {formatted}")
    
    # 支持的单位
    units = get_supported_units()
    print(f"支持的时间单位: {units}")
