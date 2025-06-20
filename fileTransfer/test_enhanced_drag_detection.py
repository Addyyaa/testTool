#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强的拖拽目标检测测试脚本
测试Windows 10/11兼容性和SHELLDLL_DefView/DirectUIHWND窗口支持
"""

import os
import sys
import time
import tkinter as tk
from tkinter import messagebox

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 导入拖拽处理器
from fileTransfer.gui.drag_handler import DragHandler
from fileTransfer.logger_utils import get_logger

def test_windows_api_availability():
    """测试Windows API可用性"""
    print("=== 测试Windows API可用性 ===")
    try:
        import win32gui
        import win32com.client
        print("✓ win32gui可用")
        print("✓ win32com.client可用")
        
        # 测试获取当前鼠标位置
        cursor_pos = win32gui.GetCursorPos()
        print(f"✓ 当前鼠标位置: {cursor_pos}")
        
        return True
    except ImportError as e:
        print(f"✗ Windows API不可用: {e}")
        return False

def test_shell_application_com():
    """测试Shell.Application COM接口"""
    print("\n=== 测试Shell.Application COM接口 ===")
    try:
        import win32com.client
        shell = win32com.client.Dispatch("Shell.Application")
        windows = shell.Windows()
        
        print(f"✓ Shell.Application对象创建成功")
        print(f"✓ 找到 {len(windows)} 个Shell窗口")
        
        # 列出所有资源管理器窗口
        explorer_windows = []
        for i, window in enumerate(windows):
            try:
                hwnd = window.HWND
                location = window.LocationURL
                print(f"  窗口 {i+1}: HWND={hwnd}, 位置={location}")
                explorer_windows.append((hwnd, location))
            except Exception as e:
                print(f"  窗口 {i+1}: 获取信息失败 - {e}")
        
        return explorer_windows
    except Exception as e:
        print(f"✗ Shell.Application COM接口测试失败: {e}")
        return []

def test_explorer_window_detection():
    """测试资源管理器窗口检测"""
    print("\n=== 测试资源管理器窗口检测 ===")
    try:
        import win32gui
        
        def enum_windows_proc(hwnd, windows):
            class_name = win32gui.GetClassName(hwnd)
            if class_name in ['CabinetWClass', 'ExploreWClass', 'SHELLDLL_DefView', 'DirectUIHWND']:
                try:
                    window_title = win32gui.GetWindowText(hwnd)
                    is_visible = win32gui.IsWindowVisible(hwnd)
                    windows.append((hwnd, class_name, window_title, is_visible))
                except:
                    pass
            return True
        
        windows = []
        win32gui.EnumWindows(enum_windows_proc, windows)
        
        print(f"找到 {len(windows)} 个相关窗口:")
        for hwnd, class_name, title, visible in windows:
            visibility = "可见" if visible else "隐藏"
            print(f"  HWND={hwnd}, 类名='{class_name}', 标题='{title}', {visibility}")
        
        return windows
    except Exception as e:
        print(f"✗ 资源管理器窗口检测失败: {e}")
        return []

def test_window_hierarchy_analysis():
    """测试窗口层次结构分析"""
    print("\n=== 测试窗口层次结构分析 ===")
    try:
        import win32gui
        
        # 获取当前鼠标位置的窗口
        cursor_pos = win32gui.GetCursorPos()
        hwnd = win32gui.WindowFromPoint(cursor_pos)
        
        if not hwnd:
            print("✗ 无法获取鼠标位置的窗口")
            return
        
        print(f"鼠标位置窗口: HWND={hwnd}")
        
        # 构建窗口层次结构
        hierarchy = []
        current_hwnd = hwnd
        
        for level in range(10):  # 最多10层
            if not current_hwnd:
                break
            
            try:
                class_name = win32gui.GetClassName(current_hwnd)
                window_title = win32gui.GetWindowText(current_hwnd)
                hierarchy.append((level, current_hwnd, class_name, window_title))
                
                parent_hwnd = win32gui.GetParent(current_hwnd)
                if parent_hwnd == current_hwnd:
                    break
                current_hwnd = parent_hwnd
                
            except Exception as e:
                print(f"  层次结构分析在第{level}层出错: {e}")
                break
        
        print("窗口层次结构:")
        for level, hwnd, class_name, title in hierarchy:
            indent = "  " * level
            print(f"{indent}第{level}层: HWND={hwnd}, 类名='{class_name}', 标题='{title}'")
        
        return hierarchy
    except Exception as e:
        print(f"✗ 窗口层次结构分析失败: {e}")
        return []

def test_enhanced_drag_detection():
    """测试增强的拖拽检测功能"""
    print("\n=== 测试增强的拖拽检测功能 ===")
    
    # 创建一个简单的测试GUI
    root = tk.Tk()
    root.title("拖拽检测测试")
    root.geometry("400x300")
    
    # 创建一个虚拟的treeview（用于测试）
    class MockTreeview:
        def __init__(self):
            self.master = root
        
        def configure(self, **kwargs):
            pass
        
        def bind(self, *args, **kwargs):
            pass
    
    # 创建logger
    logger = get_logger("drag_test")
    
    # 创建拖拽处理器
    mock_treeview = MockTreeview()
    drag_handler = DragHandler(mock_treeview, None, logger)
    
    # 测试函数
    def test_current_position():
        try:
            import win32gui
            cursor_pos = win32gui.GetCursorPos()
            x, y = cursor_pos
            
            print(f"\n当前鼠标位置: ({x}, {y})")
            
            # 测试目标路径检测
            target_path = drag_handler._detect_windows_target_path(x, y)
            
            if target_path:
                print(f"✓ 检测到目标路径: {target_path}")
                if os.path.exists(target_path):
                    print(f"✓ 路径存在且有效")
                else:
                    print(f"✗ 路径不存在: {target_path}")
            else:
                print("✗ 未能检测到目标路径")
            
            # 显示结果
            result_text = f"位置: ({x}, {y})\n目标路径: {target_path or '未检测到'}"
            messagebox.showinfo("检测结果", result_text)
            
        except Exception as e:
            error_msg = f"测试失败: {e}"
            print(f"✗ {error_msg}")
            messagebox.showerror("错误", error_msg)
    
    # 创建测试按钮
    test_button = tk.Button(
        root, 
        text="测试当前鼠标位置的拖拽目标检测", 
        command=test_current_position,
        font=("Microsoft YaHei", 12),
        bg="#4CAF50",
        fg="white",
        padx=20,
        pady=10
    )
    test_button.pack(pady=50)
    
    # 说明文本
    instruction = tk.Label(
        root,
        text="使用说明：\n1. 将鼠标移动到要测试的位置\n2. 点击测试按钮\n3. 查看检测结果",
        font=("Microsoft YaHei", 10),
        justify="left"
    )
    instruction.pack(pady=20)
    
    print("✓ 测试GUI已启动")
    print("请将鼠标移动到不同的窗口位置进行测试")
    
    return root

def main():
    """主测试函数"""
    print("开始增强的拖拽目标检测测试")
    print("=" * 50)
    
    # 1. 测试Windows API可用性
    if not test_windows_api_availability():
        print("Windows API不可用，无法继续测试")
        return
    
    # 2. 测试Shell.Application COM接口
    explorer_windows = test_shell_application_com()
    
    # 3. 测试资源管理器窗口检测
    detected_windows = test_explorer_window_detection()
    
    # 4. 测试窗口层次结构分析
    hierarchy = test_window_hierarchy_analysis()
    
    # 5. 启动交互式测试
    print("\n=== 启动交互式测试 ===")
    try:
        root = test_enhanced_drag_detection()
        if root:
            print("交互式测试界面已启动，请手动测试...")
            root.mainloop()
    except Exception as e:
        print(f"启动交互式测试失败: {e}")
    
    print("\n测试完成！")

if __name__ == "__main__":
    main() 