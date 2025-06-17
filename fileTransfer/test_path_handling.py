#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
路径处理测试脚本

测试Unix路径处理函数的正确性
"""

def normalize_unix_path(path):
    """规范化Unix路径"""
    if not path:
        return '/'
    
    # 替换反斜杠为正斜杠
    path = path.replace('\\', '/')
    
    # 确保以/开头
    if not path.startswith('/'):
        path = '/' + path
    
    # 移除重复的斜杠
    while '//' in path:
        path = path.replace('//', '/')
    
    # 移除末尾斜杠（除非是根目录）
    if path != '/' and path.endswith('/'):
        path = path.rstrip('/')
    
    return path

def get_unix_parent_path(path):
    """获取Unix风格的父路径"""
    if path == '/':
        return '/'
    
    # 确保使用正斜杠
    path = path.replace('\\', '/')
    
    # 移除末尾的斜杠
    path = path.rstrip('/')
    
    # 如果是根目录
    if not path:
        return '/'
    
    # 找到最后一个斜杠
    last_slash = path.rfind('/')
    if last_slash == -1:
        return '/'
    elif last_slash == 0:
        return '/'
    else:
        return path[:last_slash]

def join_unix_path(base_path, name):
    """连接Unix风格路径"""
    # 确保使用正斜杠
    base_path = base_path.replace('\\', '/')
    name = name.replace('\\', '/')
    
    # 移除末尾斜杠
    base_path = base_path.rstrip('/')
    
    # 如果是根目录
    if base_path == '':
        base_path = '/'
    
    # 连接路径
    if base_path == '/':
        return f'/{name}'
    else:
        return f'{base_path}/{name}'

def test_path_functions():
    """测试路径处理函数"""
    print("🧪 测试路径处理函数")
    print("=" * 50)
    
    # 测试路径规范化
    test_cases = [
        ("/customer\\config", "/customer/config"),
        ("customer\\config", "/customer/config"),
        ("//customer//config", "/customer/config"),
        ("/customer/config/", "/customer/config"),
        ("", "/"),
        ("/", "/"),
        ("\\", "/"),
        ("customer/config\\test", "/customer/config/test"),
    ]
    
    print("📁 测试路径规范化:")
    for input_path, expected in test_cases:
        result = normalize_unix_path(input_path)
        status = "✅" if result == expected else "❌"
        print(f"{status} '{input_path}' -> '{result}' (期望: '{expected}')")
    
    print("\n📂 测试父路径获取:")
    parent_cases = [
        ("/customer/config", "/customer"),
        ("/customer", "/"),
        ("/", "/"),
        ("/customer/config/test", "/customer/config"),
    ]
    
    for input_path, expected in parent_cases:
        result = get_unix_parent_path(input_path)
        status = "✅" if result == expected else "❌"
        print(f"{status} '{input_path}' -> '{result}' (期望: '{expected}')")
    
    print("\n🔗 测试路径连接:")
    join_cases = [
        ("/customer", "config", "/customer/config"),
        ("/", "customer", "/customer"),
        ("/customer/", "config", "/customer/config"),
        ("", "customer", "/customer"),
    ]
    
    for base, name, expected in join_cases:
        result = join_unix_path(base, name)
        status = "✅" if result == expected else "❌"
        print(f"{status} '{base}' + '{name}' -> '{result}' (期望: '{expected}')")

if __name__ == "__main__":
    test_path_functions()
    print("\n" + "=" * 50)
    print("✅ 路径处理测试完成！") 