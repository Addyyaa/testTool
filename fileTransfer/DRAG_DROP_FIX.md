# 拖拽文件解析功能修复

## 问题描述

用户反映拖拽文件到上传区域时，日志显示：
```
收到拖拽事件，数据: '{F:/WeChat/WeChat Files/wxid_6san4t5kmim222/FileStorage/File/2025-06/mymqtt(1)}'
解析到 0 个文件: []
没有解析到有效文件
```

## 问题原因

原来的文件解析逻辑过于简单，只能处理用空格分隔的简单路径：

```python
# 旧逻辑：只按空格分割
file_paths = data.replace('\\', '/').split()
for path in file_paths:
    path = path.strip('{}').strip()
    if os.path.exists(path):
        files.append(path)
```

这种方法有以下问题：
1. 无法正确处理包含空格的路径
2. 无法处理大括号格式的拖拽数据
3. 不支持目录拖拽（只查找文件）
4. 缺少详细的调试信息

## 解决方案

### 1. 支持大括号格式解析

新增对 `{path}` 格式的支持，这是Windows拖拽操作的常见格式：

```python
if '{' in data and '}' in data:
    # 使用正则表达式匹配大括号内的路径
    paths = re.findall(r'\{([^}]+)\}', data)
```

### 2. 支持目录拖拽

当拖拽的是目录时，自动列出目录中的所有文件：

```python
elif os.path.isdir(path):
    # 如果是目录，列出其中的文件
    for item in os.listdir(path):
        item_path = os.path.join(path, item)
        if os.path.isfile(item_path):
            files.append(item_path)
```

### 3. 增强错误处理和调试

添加详细的调试日志，帮助诊断问题：

```python
self.logger.debug(f"原始拖拽数据: {repr(data)}")
self.logger.debug(f"从大括号格式解析到路径: {paths}")
self.logger.debug(f"检查路径: {path}")
self.logger.debug(f"添加文件: {path}")
```

### 4. 双重解析策略

支持两种拖拽数据格式：
- **大括号格式**: `{path1} {path2}` - 支持包含空格的路径
- **简单格式**: `path1 path2` - 兼容不包含空格的路径

## 修复后的完整逻辑

```python
def _parse_drop_files(self, data):
    """解析拖拽文件"""
    files = []
    try:
        if isinstance(data, str):
            self.logger.debug(f"原始拖拽数据: {repr(data)}")
            
            # 处理不同的拖拽数据格式
            if '{' in data and '}' in data:
                # 大括号格式: {path1} {path2} ...
                paths = re.findall(r'\{([^}]+)\}', data)
                self.logger.debug(f"从大括号格式解析到路径: {paths}")
                
                for path in paths:
                    path = path.strip().replace('\\', '/')
                    if os.path.exists(path):
                        if os.path.isfile(path):
                            files.append(path)
                        elif os.path.isdir(path):
                            # 目录处理：列出所有文件
                            for item in os.listdir(path):
                                item_path = os.path.join(path, item)
                                if os.path.isfile(item_path):
                                    files.append(item_path)
            else:
                # 简单格式：按空格分割
                file_paths = data.replace('\\', '/').split()
                for path in file_paths:
                    path = path.strip('{}').strip()
                    # 同样的文件/目录处理逻辑
            
            self.logger.info(f"最终解析到 {len(files)} 个文件")
            
    except Exception as e:
        self.logger.error(f"解析文件失败: {str(e)}")
    return files
```

## 使用效果

### 修复前：
- 拖拽WeChat文件：解析到 0 个文件 ❌
- 拖拽包含空格的路径：解析失败 ❌
- 拖拽目录：不支持 ❌

### 修复后：
- 拖拽WeChat文件：正确解析文件 ✅
- 拖拽包含空格的路径：正确处理 ✅
- 拖拽目录：自动列出目录中的文件 ✅
- 详细的调试日志：便于问题诊断 ✅

## 支持的拖拽格式

1. **单个文件（大括号）**: `{C:/path/to/file.txt}`
2. **多个文件（大括号）**: `{C:/file1.txt} {C:/file2.txt}`
3. **包含空格的路径**: `{C:/Program Files/app/file.txt}`
4. **目录拖拽**: `{C:/some/directory}` - 自动添加目录中的所有文件
5. **简单路径**: `C:/file.txt` - 兼容旧格式

## 技术细节

- 使用正则表达式 `r'\{([^}]+)\}'` 匹配大括号内容
- 自动转换Windows路径分隔符 `\` 为 `/`
- 递归处理目录内容（仅一级，不递归子目录）
- 详细的错误处理和日志记录
- 保持向后兼容性

这个修复确保了文件传输工具能够正确处理各种拖拽操作，特别是来自WeChat等应用的文件拖拽。 