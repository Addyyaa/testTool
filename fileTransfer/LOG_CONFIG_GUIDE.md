# 日志配置统一管理指南

## 📋 概述

本项目现在使用统一的日志配置系统，所有日志等级和设置都集中在 `fileTransfer/log_config.py` 文件中管理。

## 🎯 主要功能

### 1. 统一日志等级设置
- **全局日志等级**: 影响所有模块的默认日志等级
- **模块特定日志等级**: 为特定模块设置不同的日志等级
- **动态日志等级调整**: 运行时可以动态修改日志等级

### 2. 灵活的日志输出
- **控制台日志**: 可控制是否输出到控制台及其等级
- **文件日志**: 可选的文件日志输出，支持日志轮转
- **格式化**: 统一的日志格式和时间格式

## 🔧 如何使用

### 修改全局日志等级

在 `fileTransfer/log_config.py` 中找到 `LOG_CONFIG` 字典，修改 `GLOBAL_LOG_LEVEL`：

```python
LOG_CONFIG = {
    # 主要日志等级设置 - 在这里统一修改所有模块的日志等级
    'GLOBAL_LOG_LEVEL': logging.DEBUG,  # 改为DEBUG可以看到更多调试信息
    # 'GLOBAL_LOG_LEVEL': logging.INFO,   # 改为INFO可以减少输出
    # 'GLOBAL_LOG_LEVEL': logging.WARNING, # 改为WARNING只显示警告和错误
}
```

### 为特定模块设置日志等级

在 `MODULE_LOG_LEVELS` 中添加或修改模块的日志等级：

```python
'MODULE_LOG_LEVELS': {
    'fileTransfer.gui.main_window': logging.DEBUG,      # GUI主窗口
    'fileTransfer.http_server': logging.INFO,           # HTTP服务器
    'fileTransfer.file_transfer_controller': logging.INFO, # 文件传输控制器
    'telnetTool.telnetConnect': logging.WARNING,        # Telnet连接
    
    # 添加新的模块配置
    'fileTransfer.gui.directory_panel': logging.DEBUG,  # 目录面板
},
```

### 启用文件日志

如果需要将日志保存到文件：

```python
'ENABLE_FILE_LOG': True,              # 启用文件日志
'LOG_FILE_PATH': 'logs/app.log',      # 日志文件路径
'FILE_LOG_LEVEL': logging.DEBUG,      # 文件日志等级
'MAX_FILE_SIZE': 10 * 1024 * 1024,    # 最大文件大小 (10MB)
'BACKUP_COUNT': 5,                    # 备份文件数量
```

### 运行时动态调整日志等级

```python
from fileTransfer.log_config import update_log_level, LogLevel

# 修改全局日志等级
update_log_level(LogLevel.DEBUG)

# 修改特定模块的日志等级
update_log_level(LogLevel.WARNING, 'fileTransfer.gui.main_window')
```

## 📊 日志等级说明

| 等级 | 数值 | 用途 | 建议使用场景 |
|------|------|------|-------------|
| `DEBUG` | 10 | 详细的调试信息 | 开发调试时使用 |
| `INFO` | 20 | 一般信息 | 正常运行时的关键信息 |
| `WARNING` | 30 | 警告信息 | 可能的问题，但不影响运行 |
| `ERROR` | 40 | 错误信息 | 发生错误，但程序可以继续 |
| `CRITICAL` | 50 | 严重错误 | 严重错误，程序可能无法继续 |

## 🎨 常用配置示例

### 开发环境配置
```python
LOG_CONFIG = {
    'GLOBAL_LOG_LEVEL': logging.DEBUG,
    'CONSOLE_LOG_LEVEL': logging.DEBUG,
    'ENABLE_FILE_LOG': True,
    'FILE_LOG_LEVEL': logging.DEBUG,
}
```

### 生产环境配置
```python
LOG_CONFIG = {
    'GLOBAL_LOG_LEVEL': logging.INFO,
    'CONSOLE_LOG_LEVEL': logging.WARNING,
    'ENABLE_FILE_LOG': True,
    'FILE_LOG_LEVEL': logging.INFO,
}
```

### 调试特定问题配置
```python
LOG_CONFIG = {
    'GLOBAL_LOG_LEVEL': logging.WARNING,
    'MODULE_LOG_LEVELS': {
        'fileTransfer.gui.main_window': logging.DEBUG,  # 只调试GUI主窗口
    },
}
```

## 🔍 模块名称参考

常用的模块名称：
- `fileTransfer.gui.main_window` - GUI主窗口
- `fileTransfer.gui.directory_panel` - 目录面板
- `fileTransfer.gui.connection_panel` - 连接面板
- `fileTransfer.gui.transfer_panel` - 传输面板
- `fileTransfer.http_server` - HTTP服务器
- `fileTransfer.file_transfer_controller` - 文件传输控制器
- `fileTransfer.ip_history_manager` - IP历史管理器
- `telnetTool.telnetConnect` - Telnet连接

## 💡 最佳实践

1. **开发时使用DEBUG等级**，可以看到详细的调试信息
2. **生产环境使用INFO或WARNING等级**，减少日志输出
3. **调试特定问题时**，只为相关模块设置DEBUG等级
4. **启用文件日志**，便于问题追踪和分析
5. **定期清理日志文件**，避免占用过多磁盘空间

## 🚀 快速开始

1. 打开 `fileTransfer/log_config.py`
2. 修改 `GLOBAL_LOG_LEVEL` 为你需要的等级
3. 如果需要调试特定模块，在 `MODULE_LOG_LEVELS` 中添加配置
4. 重启应用程序，新的日志配置即生效

## ❓ 常见问题

**Q: 为什么我修改了日志等级但没有生效？**
A: 确保重启了应用程序，日志配置在程序启动时加载。

**Q: 如何查看某个模块的具体名称？**
A: 查看日志输出中的模块名称，或者在代码中打印 `logger.name`。

**Q: 可以在运行时修改日志等级吗？**
A: 可以，使用 `update_log_level()` 函数动态修改。

**Q: 如何只看到错误信息？**
A: 将 `GLOBAL_LOG_LEVEL` 设置为 `logging.ERROR`。 