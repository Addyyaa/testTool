# 中文文件名编码修复说明

## 问题描述

在文件传输过程中，当文件名包含中文字符时，HTTP服务器无法正确处理wget请求，导致以下错误：

```
wget: server returned error: HTTP/1.0 400 Bad request syntax ('GET /\xe6\xaf\\x85\xe6\\x99\xaf\xe6\\xad\xa3\xe9\\x9d\xa2.png HTTP/1.1')
```

## 问题原因

1. **URL编码缺失**：HTTP服务器在生成下载URL时，没有对包含中文字符的文件名进行URL编码
2. **URL解码不完整**：服务器在处理GET请求时，没有正确解码URL中的中文字符
3. **多处URL生成不一致**：不同模块中存在直接字符串拼接生成URL的方式，没有统一使用编码方法

## 修复内容

### 1. HTTP服务器端修复 (`http_server.py`)

#### URL解码处理
```python
# 修复前
file_path = parsed_path.path.lstrip('/')

# 修复后
encoded_file_path = parsed_path.path.lstrip('/')
try:
    file_path = urllib.parse.unquote(encoded_file_path, encoding='utf-8')
except UnicodeDecodeError:
    try:
        file_path = urllib.parse.unquote(encoded_file_path, encoding='gbk')
    except UnicodeDecodeError:
        file_path = encoded_file_path
```

#### 文件列表HTML生成
```python
# 修复前
<a href="/{file_info['name']}" class="file-name">

# 修复后
encoded_filename = urllib.parse.quote(file_info['name'], safe='')
<a href="/{encoded_filename}" class="file-name">
```

#### URL生成方法
```python
# 修复前
return f"http://{host_ip}:{self.port}/{filename}"

# 修复后
encoded_filename = urllib.parse.quote(filename, safe='')
return f"http://{host_ip}:{self.port}/{encoded_filename}"
```

### 2. 主界面修复 (`main_gui.py`)

#### 统一使用HTTP服务器的URL生成方法
```python
# 修复前
download_url = f"http://{host_ip}:88/{filename}"

# 修复后
download_url = self.http_server.get_download_url(filename, host_ip)
```

### 3. 事件处理修复 (`file_transfer_gui_events.py`)

#### 同样统一URL生成方式
```python
# 修复前
download_url = f"http://{host_ip}:88/{os.path.basename(server_file_path)}"

# 修复后
download_url = self.http_server.get_download_url(os.path.basename(server_file_path), host_ip)
```

## 技术要点

### URL编码标准
- 使用 `urllib.parse.quote()` 进行URL编码，`safe=''` 确保所有特殊字符都被编码
- 使用 `urllib.parse.unquote()` 进行URL解码，优先使用UTF-8编码

### 编码兼容性
- 主要使用UTF-8编码处理中文字符
- 提供GBK编码作为备用方案，提高兼容性
- 解码失败时保持原始字符串，避免程序崩溃

### 统一性原则
- 所有URL生成都通过 `FileHTTPServer.get_download_url()` 方法
- 避免在多处重复实现URL拼接逻辑
- 确保编码处理的一致性

## 测试验证

创建了专门的测试脚本验证修复效果：

1. **中文文件名编码测试**：验证URL编码和解码的正确性
2. **服务器端处理测试**：验证HTTP服务器能正确处理编码后的URL
3. **端到端集成测试**：确保整个传输流程正常工作

测试结果：✅ 所有测试通过

## 影响范围

- ✅ 支持包含中文字符的文件名传输
- ✅ 兼容其他Unicode字符（日文、韩文等）
- ✅ 保持对英文文件名的完全兼容
- ✅ 提高系统的国际化支持

## 使用说明

修复后，用户可以正常传输包含中文字符的文件，无需额外操作：

1. 直接拖拽包含中文名的文件到传输区域
2. 点击"开始传输"按钮
3. 系统自动处理文件名编码，确保传输成功

## 注意事项

- 远程设备的文件系统需要支持UTF-8编码
- 确保远程设备的wget工具版本支持UTF-8 URL
- 建议在传输前测试网络连接和权限设置