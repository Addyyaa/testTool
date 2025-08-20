# 礼物测试工具

## 概述
这是一个用于测试礼物功能的Python工具，支持文件上传和礼物添加功能。

## 功能特性
- **文件上传功能**：支持图片和视频文件的批量上传
- **智能文件转换**：自动将不支持的格式转换为支持的格式
  - 图片转换为JPG格式
  - 视频转换为MP4格式
- **多进程处理**：使用多进程提高文件处理效率
- **异步上传**：使用异步HTTP请求提高上传效率
- **礼物添加功能**：支持添加礼物信息到服务器

## 安装依赖
```bash
pip install -r requirements.txt
```

## 使用方法

### 方法1：使用启动脚本（推荐）
```bash
python run_test.py
```

### 方法2：直接运行主文件
```bash
python test_for_gift.py
```

## 文件结构
```
test_for_gift/
├── test_for_gift.py     # 主要功能模块
├── run_test.py          # 启动脚本
├── requirements.txt     # 依赖管理
├── README.md           # 说明文档
└── tmp/                # 临时文件目录（自动创建）
```

## 主要类说明

### addGift类
用于添加礼物信息到服务器。

**参数：**
- `timezone`: 时区设置
- `media_list`: 媒体文件列表
- `greetingContent`: 祝福内容
- `greentingTitile`: 祝福标题
- `greetingImg`: 祝福图片
- `receiver_name`: 接收者姓名
- `sender_name`: 发送者姓名

### file_uploader_to_fileServer类
用于文件上传和格式转换。

**主要方法：**
- `start()`: 开始文件上传流程
- `read_local_file()`: 选择本地文件
- `judge_file_type()`: 判断文件类型
- `convert_file_to_support_format()`: 转换文件格式
- `upload_file()`: 上传文件到服务器

## 支持的文件格式

### 图片格式
- **输入支持**：JPG, PNG, JPEG, WEBP, GIF, BMP
- **输出格式**：JPG（统一转换）

### 视频格式
- **输入支持**：MP4, AVI, MOV, WMV, FLV, MKV, WEBM
- **输出格式**：MP4（统一转换）

## 配置说明

### 服务器配置
```python
protocol = "http"
host = "139.224.192.36"
port = "8082"
```

### 用户认证
```python
user = "test2@tester.com"
passwd = "sf123123"
```

## 注意事项

1. **FFmpeg依赖**：视频转换需要安装FFmpeg
2. **文件大小限制**：根据服务器配置调整
3. **网络连接**：确保能够访问目标服务器
4. **权限设置**：确保有读写临时目录的权限

## 错误处理

工具包含完善的错误处理机制：
- 文件类型检查
- 网络连接重试
- 异常日志记录
- 资源清理

## 日志记录

程序会生成详细的日志记录：
- 控制台输出：实时显示处理状态
- 文件日志：保存到`test_for_gift.log`

## 开发说明

### 代码规范
- 遵循PEP 8代码规范
- 使用中文注释
- 完善的异常处理
- 详细的日志记录

### 设计模式
- 单一职责原则
- 函数式编程
- 异步编程模式
- 多进程处理

## 故障排除

### 常见问题
1. **模块导入错误**：确保Python路径正确
2. **依赖缺失**：运行`pip install -r requirements.txt`
3. **FFmpeg未安装**：安装FFmpeg并添加到PATH
4. **网络连接问题**：检查服务器地址和端口

### 调试模式
修改日志级别为DEBUG获取更详细信息：
```python
logging.basicConfig(level=logging.DEBUG)
```

## 更新日志

### v1.0.0
- 初始版本发布
- 支持文件上传和礼物添加功能
- 完善的错误处理和日志记录 