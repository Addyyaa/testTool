 # 自定义Telnet客户端类

## 项目概述

基于 `telnetlib3` 库开发的自定义Telnet客户端类，提供了更简洁易用的异步API接口。该类重新封装了常用的telnet操作方法，支持自动连接、命令执行、响应解析等功能。

## 功能特性

### 🔧 核心功能
- **异步操作**: 基于 `asyncio` 和 `telnetlib3` 的异步实现
- **自动认证**: 支持用户名/密码自动登录
- **命令执行**: 便捷的命令执行和结果获取
- **连接管理**: 自动连接管理和资源清理
- **错误处理**: 完善的异常处理机制
- **日志记录**: 详细的操作日志记录

### 🛠 高级特性
- **上下文管理器**: 支持 `async with` 语法
- **超时控制**: 灵活的超时设置
- **原始数据**: 支持发送原始数据
- **提示符识别**: 智能提示符识别
- **批量操作**: 支持并发处理多个连接
- **编码支持**: 可配置字符编码

## 安装依赖

```bash
pip install telnetlib3
```

## 快速开始

### 1. 基本使用

```python
import asyncio
from telnetConnect import CustomTelnetClient

async def main():
    # 创建客户端实例
    client = CustomTelnetClient("192.168.1.100", 23)
    
    try:
        # 连接并认证
        await client.connect(username="admin", password="password")
        
        # 执行命令
        result = await client.execute_command("ls -la")
        print(result)
        
    finally:
        await client.disconnect()

# 运行
asyncio.run(main())
```

### 2. 使用上下文管理器

```python
async def main():
    async with CustomTelnetClient("192.168.1.100", 23) as client:
        await client.connect(username="admin", password="password")
        result = await client.execute_command("uptime")
        print(result)
```

### 3. 快速命令执行

```python
from telnetConnect import quick_telnet_command

async def main():
    result = await quick_telnet_command(
        host="192.168.1.100",
        command="whoami",
        username="admin",
        password="password"
    )
    print(result)
```

## API 文档

### CustomTelnetClient 类

#### 构造函数

```python
CustomTelnetClient(
    host: str = "localhost",
    port: int = 23,
    timeout: float = 30.0,
    encoding: str = "utf-8",
    connect_timeout: float = 10.0,
    log_level: str = "INFO"
)
```

**参数说明:**
- `host`: 目标主机地址
- `port`: 端口号（默认23）
- `timeout`: 操作超时时间（秒）
- `encoding`: 字符编码（默认utf-8）
- `connect_timeout`: 连接超时时间（秒）
- `log_level`: 日志级别

#### 主要方法

##### connect()
```python
async def connect(
    username: Optional[str] = None,
    password: Optional[str] = None,
    login_prompt: str = "login:",
    password_prompt: str = "Password:",
    shell_prompt: str = "$"
) -> bool
```

连接到Telnet服务器并进行认证。

##### execute_command()
```python
async def execute_command(
    command: str,
    timeout: Optional[float] = None,
    end_prompt: str = "$",
    strip_command: bool = True
) -> str
```

执行命令并返回结果。

##### send_raw_data()
```python
async def send_raw_data(data: Union[str, bytes]) -> None
```

发送原始数据到服务器。

##### read_until()
```python
async def read_until(
    expected: str,
    timeout: Optional[float] = None
) -> str
```

读取数据直到遇到指定字符串。

##### read_available()
```python
async def read_available(timeout: float = 1.0) -> str
```

读取当前可用的所有数据。

##### disconnect()
```python
async def disconnect() -> None
```

断开连接。

##### get_connection_info()
```python
def get_connection_info() -> Dict[str, Any]
```

获取连接信息。

### 便利函数

#### quick_telnet_command()
```python
async def quick_telnet_command(
    host: str,
    command: str,
    port: int = 23,
    username: Optional[str] = None,
    password: Optional[str] = None,
    timeout: float = 30.0
) -> str
```

快速执行单个Telnet命令的便利函数。

## 使用示例

### 批量服务器操作

```python
async def batch_example():
    servers = [
        {"host": "192.168.1.100", "user": "admin", "pass": "pass1"},
        {"host": "192.168.1.101", "user": "admin", "pass": "pass2"},
    ]
    
    async def process_server(server):
        async with CustomTelnetClient(server["host"]) as client:
            await client.connect(server["user"], server["pass"])
            return await client.execute_command("hostname")
    
    tasks = [process_server(srv) for srv in servers]
    results = await asyncio.gather(*tasks)
    return results
```

### 错误处理

```python
async def error_handling_example():
    try:
        async with CustomTelnetClient("192.168.1.100") as client:
            await client.connect("admin", "password")
            result = await client.execute_command("some_command", timeout=10.0)
            
    except ConnectionError as e:
        print(f"连接失败: {e}")
    except TimeoutError as e:
        print(f"操作超时: {e}")
    except Exception as e:
        print(f"其他错误: {e}")
```

### 高级配置

```python
client = CustomTelnetClient(
    host="192.168.1.100",
    port=2323,              # 自定义端口
    timeout=60.0,           # 60秒超时
    encoding="gb2312",      # 中文编码
    connect_timeout=15.0,   # 连接超时
    log_level="DEBUG"       # 调试日志
)
```

## 配置说明

### 提示符配置

根据目标系统调整提示符：

```python
# Linux/Unix 系统
await client.connect(
    username="user",
    password="pass",
    login_prompt="login:",
    password_prompt="Password:",
    shell_prompt="$ "  # 或 "# " 对于root用户
)

# Windows 系统
await client.connect(
    username="user",
    password="pass",
    login_prompt="login:",
    password_prompt="password:",
    shell_prompt="C:\\>"
)
```

### 编码配置

针对不同系统设置适当的编码：

```python
# 中文系统
client = CustomTelnetClient(host="...", encoding="gb2312")

# 日文系统
client = CustomTelnetClient(host="...", encoding="shift_jis")

# 通用UTF-8
client = CustomTelnetClient(host="...", encoding="utf-8")
```

## 最佳实践

### 1. 连接管理
- 优先使用异步上下文管理器（`async with`）
- 确保连接及时关闭释放资源
- 设置合适的超时时间

### 2. 错误处理
- 捕获并处理连接异常
- 设置合理的重试机制
- 记录详细的错误日志

### 3. 安全考虑
- 避免在代码中硬编码密码
- 使用环境变量或配置文件存储敏感信息
- 生产环境建议使用SSH替代Telnet

### 4. 性能优化
- 批量操作时使用并发处理
- 合理设置缓冲区大小
- 避免频繁的连接建立和断开

## 故障排除

### 常见问题

1. **连接超时**
   - 检查网络连通性
   - 确认目标端口开放
   - 调整 `connect_timeout` 参数

2. **认证失败**
   - 验证用户名和密码
   - 检查提示符设置
   - 查看日志获取详细信息

3. **命令执行超时**
   - 增加 `timeout` 参数值
   - 检查命令是否需要交互输入
   - 使用 `read_available()` 获取部分输出

4. **编码问题**
   - 根据目标系统设置正确编码
   - 尝试不同的编码格式
   - 使用 `force_binary` 选项

## 开发指南

### 扩展功能

如需扩展功能，可以继承 `CustomTelnetClient` 类：

```python
class MyTelnetClient(CustomTelnetClient):
    async def custom_login(self):
        # 自定义登录逻辑
        pass
    
    async def execute_script(self, script_path):
        # 执行脚本文件
        with open(script_path, 'r') as f:
            commands = f.readlines()
        
        results = []
        for cmd in commands:
            if cmd.strip():
                result = await self.execute_command(cmd.strip())
                results.append(result)
        
        return results
```

### 调试技巧

1. 启用DEBUG日志：
```python
client = CustomTelnetClient(host="...", log_level="DEBUG")
```

2. 使用原始数据调试：
```python
await client.send_raw_data("debug command\n")
response = await client.read_available(timeout=5.0)
print(f"Raw response: {repr(response)}")
```

## 版本历史

- **v1.0.0**: 初始版本
  - 基本的异步Telnet客户端功能
  - 支持认证和命令执行
  - 完善的错误处理和日志记录

## 许可证

本项目采用 MIT 许可证，详见 LICENSE 文件。

## 贡献

欢迎提交问题报告和功能请求。在提交代码前，请确保：

1. 代码符合PEP 8规范
2. 添加适当的测试用例
3. 更新相关文档
4. 通过现有测试
