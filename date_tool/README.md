# 时间转换工具包 (date_tool)

一个优雅且易扩展的Python时间转换工具包，用于将时间戳转换为各种时间单位。

## 📋 功能特性

- ✅ **时间戳转换**: 将时间戳（秒）转换为年、月、日、时、分、秒等单位
- ✅ **多种输出格式**: 支持中文和英文键名输出
- ✅ **灵活的时间范围**: 自定义最大和最小时间单位
- ✅ **零值过滤**: 可选择过滤值为0的时间单位
- ✅ **格式化输出**: 将时间转换为易读的字符串格式
- ✅ **自定义时间单位**: 支持添加自定义时间单位（如周、季度等）
- ✅ **类型安全**: 完整的类型提示支持
- ✅ **易于扩展**: 模块化设计，易于添加新功能

## 📁 包结构

```
date_tool/
├── __init__.py          # 包初始化文件，导出主要接口
├── types.py             # 数据类型定义（TimeUnit, TimeUnitType）
├── converter.py         # 核心转换器（DateTimeConverter）
├── utils.py             # 便捷函数
└── README.md            # 使用说明
```

## 🚀 快速开始

### 基本用法

```python
from date_tool import convert_timestamp_to_time, format_time_duration

# 基本转换
timestamp = 283822  # 3天6小时57分2秒
result = convert_timestamp_to_time(timestamp, "MO", "S")
print(result)  # {'月': 0, '日': 3, '时': 6, '分': 57, '秒': 2}

# 格式化输出
formatted = format_time_duration(timestamp, "MO", "S")
print(formatted)  # "3日 6时 57分 2秒"
```

### 使用转换器类

```python
from date_tool import DateTimeConverter

# 创建转换器实例
converter = DateTimeConverter()

# 转换时间戳
result = converter.convert_timestamp_to_time(283822, "D", "M")
print(result)  # {'日': 3, '时': 6, '分': 57}

# 过滤零值
result_filtered = converter.convert_timestamp_to_time(283822, "Y", "S", filter_zero=True)
print(result_filtered)  # {'日': 3, '时': 6, '分': 57, '秒': 2}

# 英文键名格式
result_en = converter.convert_timestamp_to_time(283822, "D", "S", return_format="en")
print(result_en)  # {'D': 3, 'H': 6, 'M': 57, 'S': 2}
```

## 📚 详细使用说明

### 1. 时间单位说明

| 单位键名 | 中文名 | 英文名 | 对应秒数 |
|----------|--------|--------|----------|
| Y        | 年     | Year   | 31,536,000 |
| MO       | 月     | Month  | 2,592,000  |
| D        | 日     | Day    | 86,400     |
| H        | 时     | Hour   | 3,600      |
| M        | 分     | Minute | 60         |
| S        | 秒     | Second | 1          |

### 2. 参数说明

#### `convert_timestamp_to_time()` 参数

```python
convert_timestamp_to_time(
    timestamp: int,      # 时间戳（秒）
    max_unit: str = "Y", # 最大时间单位
    min_unit: str = "S", # 最小时间单位
    filter_zero: bool = False,    # 是否过滤零值
    return_format: str = "zh"     # 返回格式（'zh'中文/'en'英文）
)
```

#### `format_time_duration()` 参数

```python
format_time_duration(
    timestamp: int,      # 时间戳（秒）
    max_unit: str = "Y", # 最大时间单位
    min_unit: str = "S", # 最小时间单位
    separator: str = " ", # 分隔符
    filter_zero: bool = True      # 是否过滤零值
)
```

### 3. 高级功能

#### 自定义时间单位

```python
from date_tool import DateTimeConverter

converter = DateTimeConverter()

# 添加周单位
converter.add_custom_time_unit("W", "周", 7 * 24 * 60 * 60, 4)

# 添加季度单位
converter.add_custom_time_unit("Q", "季度", 90 * 24 * 60 * 60, 5)

# 使用自定义单位
result = converter.convert_timestamp_to_time(283822, "Q", "S")
print(result)  # {'季度': 0, '月': 0, '周': 0, '日': 3, '时': 6, '分': 57, '秒': 2}
```

#### 查看支持的时间单位

```python
from date_tool import get_supported_units

# 查看默认支持的时间单位
units = get_supported_units()
print(units)  # {'Y': '年', 'MO': '月', 'D': '日', 'H': '时', 'M': '分', 'S': '秒'}

# 或者使用转换器实例
converter = DateTimeConverter()
units = converter.get_supported_time_units()
```

#### 移除时间单位

```python
converter = DateTimeConverter()

# 移除月单位
success = converter.remove_time_unit("MO")
print(success)  # True

# 现在转换时不会包含月单位
result = converter.convert_timestamp_to_time(283822, "Y", "S")
```

## 🔧 示例代码

### 示例1: 不同时间范围的转换

```python
from date_tool import format_time_duration

timestamp = 283822

# 不同的时间范围
print("年到秒:", format_time_duration(timestamp, "Y", "S"))
print("日到分:", format_time_duration(timestamp, "D", "M"))
print("时到秒:", format_time_duration(timestamp, "H", "S"))
print("分到秒:", format_time_duration(timestamp, "M", "S"))
```

### 示例2: 自定义分隔符

```python
from date_tool import format_time_duration

timestamp = 283822

# 不同的分隔符
print("默认分隔符:", format_time_duration(timestamp, "D", "M"))
print("逗号分隔:", format_time_duration(timestamp, "D", "M", separator=", "))
print("换行分隔:", format_time_duration(timestamp, "D", "M", separator="\n"))
```

### 示例3: 批量转换

```python
from date_tool import convert_timestamp_to_time

# 批量转换不同时间戳
timestamps = [60, 3600, 86400, 283822]
names = ["1分钟", "1小时", "1天", "复合时间"]

for timestamp, name in zip(timestamps, names):
    result = convert_timestamp_to_time(timestamp, "D", "S", filter_zero=True)
    print(f"{name}: {result}")
```

## ⚠️ 异常处理

```python
from date_tool import convert_timestamp_to_time

try:
    # 负数时间戳
    result = convert_timestamp_to_time(-100, "Y", "S")
except ValueError as e:
    print(f"错误: {e}")

try:
    # 无效的时间单位
    result = convert_timestamp_to_time(1000, "INVALID", "S")
except ValueError as e:
    print(f"错误: {e}")

try:
    # 单位层级错误
    result = convert_timestamp_to_time(1000, "S", "Y")
except ValueError as e:
    print(f"错误: {e}")
```

## 🎯 设计原则

1. **单一职责原则**: 每个模块只负责一个特定功能
2. **开放封闭原则**: 对扩展开放，对修改封闭
3. **依赖倒置原则**: 高层模块不依赖低层模块
4. **接口隔离原则**: 提供最小且必要的接口

## 📈 性能特点

- 高效的时间计算算法
- 最小化内存使用
- 支持大量并发转换
- 类型安全的实现

## 🔄 版本信息

- 当前版本: 1.0.0
- Python版本要求: >= 3.7
- 依赖: 无第三方依赖

## 📄 许可证

本项目采用MIT许可证，详情请参考LICENSE文件。

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📞 联系方式

如有问题或建议，请联系开发者。 