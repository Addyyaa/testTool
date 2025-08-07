# 字体服务器 (Font Server)

一个专为终端设备设计的字体子集化服务器，通过动态生成字体子集来解决存储空间有限但需要国际化支持的问题。

## 功能特性

### 🎯 核心功能
- **动态字体子集化**: 根据客户端需求的字符集动态生成最小字体文件
- **多格式支持**: 支持 TTF、OTF、WOFF、WOFF2 等主流字体格式
- **智能缓存**: 内置缓存机制，提高响应速度，减少重复计算
- **RESTful API**: 简洁易用的HTTP API接口
- **多线程处理**: 支持并发请求，高性能处理

### 🌍 适用场景
- **嵌入式终端设备**: 存储空间有限的IoT设备、POS机、工业控制器等
- **国际化应用**: 需要支持多语言但不想包含完整字体文件的应用
- **Web字体优化**: 为网页提供定制化字体子集，减少加载时间
- **移动应用**: 减少应用包大小，按需下载字体资源

## 安装与使用

### 环境要求
- Python 3.7+
- 支持的操作系统: Windows、Linux、macOS

### 快速开始

1. **克隆项目并进入目录**
   ```bash
   cd font_server
   ```

2. **运行启动脚本（推荐）**
   ```bash
   python start_font_server.py
   ```
   启动脚本会自动：
   - 检查Python版本
   - 安装所需依赖包
   - 创建字体目录结构
   - 启动字体服务器

3. **手动安装依赖（可选）**
   ```bash
   pip install -r requirements.txt
   ```

4. **添加字体文件**
   将字体文件复制到 `fonts/` 目录中：
   ```
   fonts/
   ├── chinese/
   │   ├── NotoSansSC-Regular.ttf
   │   └── SourceHanSans-Regular.otf
   ├── english/
   │   ├── Arial.ttf
   │   └── Times-Roman.ttf
   └── symbols/
       └── FontAwesome.ttf
   ```

5. **启动服务器**
   ```bash
   python font_server.py
   ```

### 命令行参数

```bash
python font_server.py [选项]

选项:
  --fonts-dir DIR     字体文件目录 (默认: fonts)
  --cache-dir DIR     缓存目录 (默认: cache)
  --host HOST         服务器主机地址 (默认: 0.0.0.0)
  --port PORT         服务器端口 (默认: 8889)
  --log-level LEVEL   日志级别 (DEBUG/INFO/WARNING/ERROR, 默认: INFO)
  --debug             启用调试模式
  --help              显示帮助信息
```

示例：
```bash
# 自定义端口和字体目录
python font_server.py --port 9000 --fonts-dir /path/to/fonts

# 启用调试模式
python font_server.py --debug --log-level DEBUG
```

## API 接口文档

服务器启动后，默认运行在 `http://localhost:8889`

### 1. 健康检查
```http
GET /health
```

**响应示例:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00.000000",
  "version": "1.0.0"
}
```

### 2. 获取字体列表
```http
GET /api/fonts
```

**响应示例:**
```json
{
  "success": true,
  "fonts": {
    "chinese/NotoSansSC-Regular.ttf": {
      "path": "chinese/NotoSansSC-Regular.ttf",
      "size": 15728640,
      "modified": 1704067200,
      "family_name": "Noto Sans SC"
    }
  },
  "count": 1
}
```

### 3. 获取字体字符
```http
GET /api/font/characters/{font_name}
```

**响应示例:**
```json
{
  "success": true,
  "font": "chinese/NotoSansSC-Regular.ttf",
  "characters": ["a", "b", "c", "你", "好", "世", "界"],
  "count": 65536
}
```

### 4. 创建字体子集
```http
POST /api/font/subset/{font_name}
Content-Type: application/json
```

**请求参数:**
```json
{
  "text": "你好世界Hello",
  "format": "ttf"
}
```

**或者使用字符数组（兼容旧版本）:**
```json
{
  "characters": ["你", "好", "世", "界", "H", "e", "l", "l", "o"],
  "format": "ttf"
}
```

**响应:** 返回字体文件的二进制数据，自动下载

**支持的格式:**
- `ttf` - TrueType Font
- `otf` - OpenType Font  
- `woff` - Web Open Font Format
- `woff2` - Web Open Font Format 2.0

### 5. 获取服务器统计
```http
GET /api/stats
```

**响应示例:**
```json
{
  "success": true,
  "stats": {
    "fonts_count": 5,
    "fonts_dir": "/path/to/fonts",
    "cache": {
      "cache_count": 12,
      "total_size": 2048576,
      "max_cache_size": 100,
      "cache_ttl": 3600
    },
    "server": {
      "host": "0.0.0.0",
      "port": 8889
    }
  }
}
```

### 6. 清理缓存
```http
POST /api/cache/clear
```

**响应示例:**
```json
{
  "success": true,
  "message": "缓存已清理"
}
```

## 客户端使用示例

### 🎯 正确的使用方式

**重要说明：**
- 客户端只需要发送要显示的文字内容
- 服务器负责分析字符、创建字体子集
- 客户端无需了解字体内部结构

### Python 客户端
```python
import requests

# 1. 获取可用字体
response = requests.get('http://localhost:8889/api/fonts')
fonts = response.json()
font_name = list(fonts['fonts'].keys())[0]  # 选择第一个字体

# 2. 客户端只需要发送要显示的文字内容
# 不需要获取字体的所有字符（避免接收3000+个无用字符）
text_to_display = "收银台 金额:¥123.45 找零:¥6.55"

# 3. 服务器自动创建包含所需字符的字体子集
response = requests.post(f'http://localhost:8889/api/font/subset/{font_name}', 
    json={
        'text': text_to_display,  # 只需要这个！
        'format': 'ttf'
    }
)

if response.status_code == 200:
    with open('pos_font.ttf', 'wb') as f:
        f.write(response.content)
    
    # 原字体可能15MB，定制字体可能只有5KB
    size_kb = len(response.content) / 1024
    print(f"定制字体创建成功！大小: {size_kb:.2f}KB")
```

### 实际应用场景
```python
# 不同客户端的使用场景
scenarios = [
    {"client": "POS收银机", "text": "收银台 金额:¥123.45 找零:¥6.55"},
    {"client": "IoT温度显示", "text": "Temperature: 25.6°C 湿度:68%"},
    {"client": "多语言标签", "text": "Hello 你好 こんにちは 안녕하세요"},
    {"client": "数字时钟", "text": "2024-01-15 14:30:25"}
]

for scenario in scenarios:
    # 每个客户端只需要发送自己的文字内容
    response = requests.post(f'http://localhost:8889/api/font/subset/{font_name}',
        json={'text': scenario['text'], 'format': 'ttf'})
    
    if response.status_code == 200:
        filename = f"{scenario['client']}_font.ttf"
        with open(filename, 'wb') as f:
            f.write(response.content)
        print(f"{scenario['client']} 定制字体已创建: {filename}")
```

### JavaScript/Node.js 客户端
```javascript
const fs = require('fs');
const axios = require('axios');

async function createFontSubset() {
    try {
        const response = await axios.post(
            'http://localhost:8889/api/font/subset/chinese/NotoSansSC-Regular.ttf',
            {
                text: '你好世界！欢迎使用字体服务器。',
                format: 'woff2'
            },
            { responseType: 'arraybuffer' }
        );
        
        fs.writeFileSync('subset.woff2', Buffer.from(response.data));
        console.log('字体子集创建成功！');
    } catch (error) {
        console.error('创建失败:', error.message);
    }
}

createFontSubset();
```

### curl 命令行
```bash
# 获取字体列表
curl http://localhost:8889/api/fonts

# 创建字体子集
curl -X POST http://localhost:8889/api/font/subset/chinese/NotoSansSC-Regular.ttf \
  -H "Content-Type: application/json" \
  -d '{"text":"你好世界！欢迎使用字体服务器。", "format":"ttf"}' \
  --output subset.ttf
```

## 配置与优化

### 缓存配置
- **缓存目录**: 默认 `cache/`，可通过 `--cache-dir` 参数修改
- **缓存大小**: 默认最多100个缓存文件
- **过期时间**: 默认1小时（3600秒）
- **清理机制**: 自动清理过期缓存，支持手动清理

### 性能优化建议
1. **字体文件组织**: 按语言或用途分目录存放字体文件
2. **合理设置缓存参数**: 根据服务器资源调整缓存大小和过期时间
3. **使用适当格式**: WOFF2 提供最佳的压缩比
4. **批量处理**: 一次请求包含多个相关字符，减少网络请求

### 目录结构建议
```
fonts/
├── chinese/          # 中文字体
│   ├── sans/         # 无衬线字体
│   └── serif/        # 衬线字体
├── english/          # 英文字体
├── japanese/         # 日文字体
├── korean/           # 韩文字体
├── arabic/           # 阿拉伯文字体
└── symbols/          # 符号字体
    ├── icons/        # 图标字体
    └── emoji/        # 表情符号
```

## 最佳实践

### 1. 文字内容优化
```python
# 推荐：一次传递完整的文字内容
text = "你好世界！欢迎使用字体服务器，这是一个测试文本。"

# 不推荐：频繁的小批次请求
# text = "你好"  # 然后又请求 "世界"
# 这样会产生很多小缓存文件，效率低下
```

### 2. 格式选择
- **TTF**: 兼容性最好，适合桌面应用
- **WOFF2**: 压缩比最高，适合Web应用
- **OTF**: 支持高级排版特性
- **WOFF**: WOFF2不兼容时的备选方案

### 3. 缓存策略
- 相同字符集的请求会命中缓存
- 定期清理缓存避免磁盘空间不足
- 监控缓存命中率优化字符集分组

### 4. 错误处理
```python
def safe_create_subset(font_name, text, format_type='ttf'):
    try:
        response = requests.post(f'{server_url}/api/font/subset/{font_name}',
            json={'text': text, 'format': format_type},
            timeout=30  # 设置超时
        )
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
        return None
```

## 故障排除

### 常见问题

**1. 服务器启动失败**
- 检查端口是否被占用: `netstat -an | grep 8889`
- 检查Python版本: `python --version`
- 查看错误日志: `font_server.log`

**2. 字体文件无法识别**
- 确认字体文件格式正确
- 检查文件权限
- 查看服务器日志中的错误信息

**3. 子集创建失败**
- 确认请求的字符在字体中存在
- 检查JSON格式是否正确
- 验证字体文件没有损坏

**4. 性能问题**
- 增加缓存大小和过期时间
- 检查磁盘空间是否充足
- 监控服务器资源使用情况

### 日志分析
```bash
# 查看实时日志
tail -f font_server.log

# 过滤错误日志
grep "ERROR" font_server.log

# 查看缓存相关日志
grep "缓存" font_server.log
```

## 开发与扩展

### 项目结构
```
font_server/
├── font_server.py          # 主服务器文件
├── start_font_server.py    # 启动脚本
├── client_example.py       # 客户端示例
├── requirements.txt        # 依赖列表
├── README.md              # 说明文档
├── fonts/                 # 字体文件目录
├── cache/                 # 缓存目录
└── font_server.log        # 日志文件
```

### 扩展建议
1. **Web管理界面**: 添加字体管理和监控面板
2. **用户认证**: 添加API密钥或JWT认证
3. **限流机制**: 防止滥用API接口
4. **字体预览**: 提供字体样式预览功能
5. **批量处理**: 支持批量字体操作
6. **Docker支持**: 容器化部署

## 许可证

本项目采用 MIT 许可证，详见 LICENSE 文件。

## 贡献

欢迎提交 Issue 和 Pull Request 来改进项目！

## 更新日志

### v1.0.0 (2024-01-01)
- 首次发布
- 实现基本的字体子集化功能
- 支持多种字体格式
- 添加缓存机制
- 提供完整的REST API
- 包含客户端使用示例 