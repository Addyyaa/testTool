# 自动登录检查功能说明

## 功能概述

CustomTelnetClient现在支持在执行命令前自动检查登录状态，如果检测到需要重新登录，会自动处理登录过程。这个功能特别适用于：

- 长时间连接可能超时的场景
- 网络不稳定导致连接中断的情况
- 需要确保每次命令执行前都处于正确登录状态的场景

## 主要特性

### 1. 自动登录检查
每次执行命令前，客户端会：
1. 发送一个回车符检查当前状态
2. 分析服务器响应，判断是否需要重新登录
3. 如果检测到登录提示符，自动执行登录流程
4. 确保处于shell状态后再执行实际命令

### 2. 认证信息存储
- 在首次连接时自动存储认证信息
- 支持手动设置认证信息
- 后续命令执行时自动使用存储的认证信息

### 3. 灵活的控制选项
- 可以为单个命令禁用自动登录检查
- 可以为单个命令提供特定的认证信息
- 支持自定义各种提示符

## 使用方法

### 基本使用

```python
import asyncio
from telnetConnect import CustomTelnetClient

async def main():
    client = CustomTelnetClient("192.168.1.45", 23)
    
    # 连接并登录（认证信息会被自动存储）
    await client.connect(username="root", password="password")
    
    # 执行命令（会自动检查登录状态）
    result1 = await client.execute_command("whoami")
    result2 = await client.execute_command("pwd")
    
    await client.disconnect()

asyncio.run(main())
```

### 高级使用

```python
# 禁用特定命令的自动登录检查
result = await client.execute_command("uptime", auto_login=False)

# 为特定命令提供认证信息
result = await client.execute_command(
    "ls -la", 
    username="admin", 
    password="admin_pass"
)

# 手动设置认证信息
client.set_auth_info("root", "new_password", "#")

# 检查是否存储了认证信息
info = client.get_connection_info()
print(f"已存储认证信息: {info['has_stored_auth']}")
```

## 工作原理

### 登录状态检查流程

```
执行命令请求
    ↓
发送回车符
    ↓
读取服务器响应
    ↓
分析响应内容
    ↓
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ 包含登录提示符  │    │ 包含shell提示符 │    │ 其他状态        │
│ 执行重新登录    │    │ 直接执行命令    │    │ 尝试等待提示符  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
    ↓                      ↓                      ↓
执行实际命令           执行实际命令           执行实际命令
```

### 错误处理

- 如果检测到需要登录但没有存储认证信息，会抛出ConnectionError
- 如果登录过程失败，会抛出相应的异常
- 如果状态检查过程出现错误，会记录警告但不影响命令执行

## 配置选项

### execute_command方法参数

- `auto_login` (bool): 是否启用自动登录检查，默认True
- `username` (str, optional): 特定命令的用户名
- `password` (str, optional): 特定命令的密码
- `end_prompt` (str): 命令结束提示符，默认"#"

### 提示符自定义

可以在connect方法中自定义各种提示符：

```python
await client.connect(
    username="root",
    password="password",
    login_prompt="Username:",      # 登录提示符
    password_prompt="Password:",   # 密码提示符
    shell_prompt="$ "             # Shell提示符
)
```

## 日志输出

启用DEBUG日志可以查看详细的登录检查过程：

```python
import logging
logging.basicConfig(level=logging.DEBUG)

client = CustomTelnetClient("host", 23, log_level="DEBUG")
```

典型的日志输出：
```
DEBUG - 检查登录状态...
DEBUG - 收到响应: '\r\n/ # '
DEBUG - 已经在shell中，无需登录
DEBUG - 执行命令: whoami
```

## 注意事项

1. **性能影响**: 每次命令执行前都会进行登录检查，会增加少量延迟
2. **网络稳定性**: 在网络不稳定的环境中，登录检查可能会超时
3. **提示符匹配**: 确保设置的提示符与实际服务器返回的提示符匹配
4. **认证信息安全**: 认证信息存储在内存中，程序结束后会自动清除

## 测试

运行测试脚本查看功能演示：

```bash
python telnetTool/test_auto_login.py
```

这个脚本会演示各种自动登录检查的场景和用法。 