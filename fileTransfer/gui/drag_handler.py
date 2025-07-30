#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
拖拽处理组件

负责处理目录树中文件的拖拽事件，支持拖拽下载功能
"""

import tkinter as tk
from tkinter import messagebox
import os
import sys
from typing import List, Dict, Any, Optional, Callable

from fileTransfer.logger_utils import get_logger

# Windows拖拽支持
if sys.platform == "win32":
    try:
        import win32clipboard
        import win32con
        import win32gui
        import win32api
        WINDOWS_DRAG_AVAILABLE = True
    except ImportError:
        WINDOWS_DRAG_AVAILABLE = False
else:
    WINDOWS_DRAG_AVAILABLE = False


class DragHandler:
    """拖拽处理器"""
    
    def __init__(self, treeview, theme, logger=None):
        """初始化拖拽处理器
        
        Args:
            treeview: 目录树控件
            theme: 主题对象
            logger: 日志器
        """
        self.treeview = treeview
        self.theme = theme
        self.logger = logger or get_logger(self.__class__)
        
        # 拖拽状态
        self.drag_data = None
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.is_dragging = False
        
        # 回调函数
        self.drag_start_callback: Optional[Callable] = None
        self.drag_drop_callback: Optional[Callable] = None
        
        # 保存原有的双击事件处理器
        self.original_double_click_handler = None
        
        # 绑定拖拽事件
        self._bind_drag_events()
        
        self.logger.debug("拖拽处理器初始化完成")
    
    def _bind_drag_events(self):
        """绑定拖拽事件"""
        # 保存原有的双击事件处理器
        try:
            # 获取当前绑定的双击事件
            current_bindings = self.treeview.bind('<Double-1>')
            if current_bindings:
                self.original_double_click_handler = current_bindings
                self.logger.debug(f"保存原有双击事件处理器: {current_bindings}")
        except Exception as e:
            self.logger.debug(f"获取原有双击事件处理器失败: {e}")
        
        # 鼠标按下事件（只绑定拖拽相关事件）
        self.treeview.bind('<B1-Motion>', self._on_mouse_drag, add='+')
        self.treeview.bind('<ButtonRelease-1>', self._on_mouse_up, add='+')
        
        # 重新绑定双击事件，确保拖拽处理和原有功能都能工作
        self.treeview.bind('<Double-1>', self._on_double_click, add='+')
    
    def _prepare_drag_data(self, event):
        """准备拖拽数据"""
        # 记录起始位置
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        self.is_dragging = False
        
        # 获取当前选中的项目
        selection = self.treeview.selection()
        if selection:
            item = selection[0]
            
            # 获取项目数据
            item_data = self.treeview.item(item)
            if item_data and 'values' in item_data and item_data['values']:
                values = item_data['values']
                if len(values) >= 2:
                    file_path = values[0]
                    is_directory = values[1]
                    
                    # 只允许拖拽文件，不允许拖拽目录
                    if not self._is_directory_item(is_directory):
                        self.drag_data = {
                            'item': item,
                            'file_path': file_path,
                            'filename': os.path.basename(file_path),
                            'is_directory': False
                        }
                        self.logger.debug(f"准备拖拽文件: {file_path}")
                        return True
                    else:
                        self.drag_data = None
                        self.logger.debug("目录不支持拖拽下载")
                else:
                    self.drag_data = None
            else:
                self.drag_data = None
        else:
            self.drag_data = None
        
        return False
    
    def _on_mouse_drag(self, event):
        """鼠标拖拽事件"""
        # 如果还没有准备拖拽数据，先准备
        if self.drag_data is None:
            if not self._prepare_drag_data(event):
                return
        
        # 计算拖拽距离
        dx = abs(event.x - self.drag_start_x)
        dy = abs(event.y - self.drag_start_y)
        
        # 只有拖拽距离超过阈值才开始拖拽
        if dx > 5 or dy > 5:
            if not self.is_dragging:
                self.is_dragging = True
                self._start_drag()
            else:
                # 拖拽过程中实时更新鼠标样式
                self._update_drag_cursor(event)
    
    def _on_mouse_up(self, event):
        """鼠标释放事件"""
        if self.is_dragging:
            self._end_drag(event)
        
        # 重置拖拽状态
        self.is_dragging = False
        self.drag_data = None
    
    def _on_double_click(self, event):
        """双击事件处理"""
        # 双击时取消拖拽
        self.is_dragging = False
        self.drag_data = None
        
        # 如果有原有的双击处理器，也要调用它
        # 注意：由于我们使用add='+'绑定，原有的处理器会自动被调用
        # 这里只是确保拖拽状态被正确重置
    
    def _start_drag(self):
        """开始拖拽"""
        if self.drag_data is None:
            return
        
        self.logger.info(f"开始拖拽文件: {self.drag_data['filename']}")
        
        # 初始设置为拖拽样式
        self.treeview.configure(cursor="plus")
        
        # 调用拖拽开始回调
        if self.drag_start_callback:
            self.drag_start_callback(self.drag_data)
    
    def _update_drag_cursor(self, event):
        """更新拖拽过程中的鼠标样式"""
        try:
            # 检查当前鼠标位置是否在有效的拖拽目标上
            if self._is_outside_window(event):
                # 在窗口外部，检查目标是否有效
                target_dir = self._get_drop_target_directory(event)
                if target_dir:
                    # 有效目标，显示允许拖放的样式
                    self.treeview.configure(cursor="plus")
                else:
                    # 无效目标，显示禁止拖放的样式
                    self.treeview.configure(cursor="no")
            else:
                # 在窗口内部，显示默认拖拽样式
                self.treeview.configure(cursor="plus")
                
        except Exception as e:
            self.logger.debug(f"更新拖拽鼠标样式失败: {e}")
            # 出错时使用默认样式
            self.treeview.configure(cursor="plus")
    
    def _end_drag(self, event):
        """结束拖拽"""
        if self.drag_data is None:
            return
        
        # 恢复鼠标样式
        self.treeview.configure(cursor="")
        
        self.logger.info(f"结束拖拽文件: {self.drag_data['filename']}")
        
        # 检查是否拖拽到了窗口外部
        if self._is_outside_window(event):
            # 检查目标是否有效
            target_dir = self._get_drop_target_directory(event)
            if target_dir:
                self.logger.info(f"拖拽到有效目标: {target_dir}")
                self._handle_external_drop(event)
            else:
                self.logger.info("拖拽到无效目标，取消操作")
                # 可以在这里显示提示信息
                self._show_invalid_drop_hint()
        
        # 调用拖拽结束回调
        if self.drag_drop_callback:
            self.drag_drop_callback(self.drag_data, event)
    
    def _is_outside_window(self, event):
        """检查是否拖拽到了窗口外部"""
        # 获取窗口边界
        widget = self.treeview
        while widget.master:
            widget = widget.master
        
        # 获取鼠标在屏幕上的绝对位置
        abs_x = event.x_root
        abs_y = event.y_root
        
        # 获取窗口在屏幕上的位置和大小
        window_x = widget.winfo_rootx()
        window_y = widget.winfo_rooty()
        window_width = widget.winfo_width()
        window_height = widget.winfo_height()
        
        # 检查是否在窗口外部
        outside = (abs_x < window_x or abs_x > window_x + window_width or
                  abs_y < window_y or abs_y > window_y + window_height)
        
        self.logger.debug(f"拖拽位置检查: 鼠标({abs_x}, {abs_y}), 窗口({window_x}, {window_y}, {window_width}, {window_height}), 外部: {outside}")
        
        return outside
    
    def _handle_external_drop(self, event):
        """处理拖拽到外部的情况"""
        if self.drag_data is None:
            return
        
        self.logger.info(f"检测到拖拽到外部: {self.drag_data['filename']}")
        
        # 尝试获取鼠标释放位置的目录
        target_dir = self._get_drop_target_directory(event)
        
        if target_dir:
            self.logger.info(f"自动检测到目标目录: {target_dir}")
            
            # 触发下载
            if self.drag_drop_callback:
                # 创建一个模拟的事件对象，包含目标目录信息
                mock_event = type('MockEvent', (), {
                    'target_dir': target_dir,
                    'external_drop': True
                })()
                
                self.drag_drop_callback(self.drag_data, mock_event)
        else:
            # 如果无法自动检测到目标目录，显示文件夹选择对话框
            self.logger.info("无法自动检测目标目录，显示文件夹选择对话框")
            self._show_directory_dialog()
    
    def _get_drop_target_directory(self, event):
        """获取拖拽目标目录"""
        try:
            if WINDOWS_DRAG_AVAILABLE:
                # Windows系统下尝试获取鼠标位置的文件夹
                return self._get_windows_drop_target(event)
            else:
                # 其他系统回退到默认行为
                return None
        except Exception as e:
            self.logger.debug(f"获取拖拽目标目录失败: {e}")
            return None
    
    def _get_windows_drop_target(self, event):
        """Windows系统下获取拖拽目标"""
        try:
            # 获取鼠标在屏幕上的绝对位置
            abs_x = event.x_root
            abs_y = event.y_root
            
            self.logger.debug(f"检测拖拽目标位置: ({abs_x}, {abs_y})")
            
            # 尝试使用Windows API检测目标窗口和路径
            if WINDOWS_DRAG_AVAILABLE:
                target_path = self._detect_windows_target_path(abs_x, abs_y)
                if target_path:
                    self.logger.info(f"检测到Windows目标路径: {target_path}")
                    return target_path
            
            # 如果无法检测到具体路径，显示目录选择对话框
            self.logger.info("无法自动检测目标路径，将显示选择对话框")
            return None
            
        except Exception as e:
            self.logger.debug(f"Windows拖拽目标检测失败: {e}")
            return None
    
    def _detect_windows_target_path(self, x, y):
        """检测Windows系统下鼠标位置的目标路径"""
        try:
            self.logger.info(f"开始检测Windows目标路径，位置: ({x}, {y})")
            
            if not WINDOWS_DRAG_AVAILABLE:
                self.logger.warning("Windows API不可用")
                return None
            
            # 获取鼠标位置下的窗口句柄
            hwnd = win32gui.WindowFromPoint((x, y))
            if not hwnd:
                self.logger.warning("无法获取鼠标位置的窗口句柄")
                return None
            
            # 获取窗口类名和标题
            class_name = win32gui.GetClassName(hwnd)
            try:
                window_title = win32gui.GetWindowText(hwnd)
            except:
                window_title = "无法获取标题"
            
            self.logger.info(f"检测到窗口: 类名='{class_name}', 标题='{window_title}'")
            
            # 检测是否为文件资源管理器
            if self._is_explorer_window(class_name, hwnd):
                self.logger.info("识别为文件资源管理器窗口")
                path = self._get_explorer_path_advanced(hwnd)
                if path:
                    self.logger.info(f"成功获取资源管理器路径: {path}")
                    return path
                else:
                    self.logger.warning("资源管理器窗口但无法获取路径")
            
            # 检测是否为桌面
            elif self._is_desktop_window(class_name):
                self.logger.info("识别为桌面窗口")
                desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
                if os.path.exists(desktop_path):
                    self.logger.info(f"返回桌面路径: {desktop_path}")
                    return desktop_path
                else:
                    self.logger.warning("桌面路径不存在")
            
            # 检测其他可能的目标窗口
            elif self._is_folder_window(class_name):
                self.logger.info("识别为文件夹窗口")
                path = self._get_folder_window_path(hwnd)
                if path:
                    self.logger.info(f"成功获取文件夹路径: {path}")
                    return path
                else:
                    self.logger.warning("文件夹窗口但无法获取路径")
            
            else:
                self.logger.warning(f"未识别的窗口类型: 类名='{class_name}', 标题='{window_title}'")
                # 对于未识别的窗口类型，尝试智能推断目标路径
                smart_path = self._smart_detect_target_path(class_name, window_title, hwnd)
                if smart_path:
                    self.logger.info(f"智能检测到目标路径: {smart_path}")
                    return smart_path
            
            return None
            
        except Exception as e:
            self.logger.error(f"检测Windows目标路径失败: {e}")
            import traceback
            self.logger.debug(f"详细错误: {traceback.format_exc()}")
            return None
    
    def _is_explorer_window(self, class_name, hwnd):
        """检测是否为文件资源管理器窗口"""
        explorer_classes = [
            'CabinetWClass',     # Windows文件资源管理器
            'ExploreWClass',     # 旧版资源管理器
            'Progman',           # 桌面
            '#32770',            # 对话框（可能是文件夹选择）
            'SHELLDLL_DefView'   # Shell默认视图（Windows 11常见）
        ]
        
        if class_name in explorer_classes:
            return True
        
        # 检查窗口标题是否包含文件夹路径
        try:
            window_title = win32gui.GetWindowText(hwnd)
            if any(keyword in window_title.lower() for keyword in ['文件夹', 'folder', ':\\', 'explorer']):
                return True
        except:
            pass
        
        return False
    
    def _is_desktop_window(self, class_name):
        """检测是否为桌面窗口"""
        desktop_classes = ['Progman', 'WorkerW', 'SysListView32']
        return class_name in desktop_classes
    
    def _is_folder_window(self, class_name):
        """检测是否为文件夹窗口"""
        folder_classes = ['#32770', 'DirectUIHWND', 'ToolbarWindow32', 'ReBarWindow32']
        return class_name in folder_classes
    
    def _get_explorer_path_advanced(self, hwnd):
        """获取文件资源管理器路径 - 增强版，支持复杂的窗口层次结构"""
        try:
            class_name = win32gui.GetClassName(hwnd)
            self.logger.info(f"获取资源管理器路径，窗口类名: {class_name}")
            
            # Windows 11特殊处理：SHELLDLL_DefView和DirectUIHWND
            if class_name in ['SHELLDLL_DefView', 'DirectUIHWND']:
                self.logger.info(f"{class_name}窗口，使用增强检测方法")
                
                # 构建窗口层次结构路径
                window_hierarchy = self._build_window_hierarchy(hwnd)
                self.logger.debug(f"窗口层次结构: {window_hierarchy}")
                
                # 在层次结构中查找资源管理器主窗口
                for level, (level_hwnd, level_class, level_title) in enumerate(window_hierarchy):
                    if level_class == 'CabinetWClass':
                        self.logger.info(f"在层次结构第{level}层找到CabinetWClass窗口")
                        # 使用主窗口的HWND进行COM查询
                        path = self._get_path_via_com(level_hwnd)
                        if path:
                            return path
                        
                        # 尝试从标题获取路径
                        path = self._extract_path_from_title(level_title)
                        if path:
                            return path
                
                # 如果没有找到CabinetWClass，尝试其他可能的父窗口
                for level, (level_hwnd, level_class, level_title) in enumerate(window_hierarchy):
                    if level_class in ['ExploreWClass', 'ShellTabWindowClass']:
                        self.logger.info(f"在层次结构第{level}层找到{level_class}窗口")
                        path = self._get_path_via_com(level_hwnd)
                        if path:
                            return path
            
            # 标准处理流程
            # 方法1: COM接口查询
            path = self._get_path_via_com(hwnd)
            if path:
                return path
            
            # 方法2: 窗口标题解析
            window_title = win32gui.GetWindowText(hwnd)
            self.logger.info(f"尝试从窗口标题获取路径: '{window_title}'")
            path = self._extract_path_from_title(window_title)
            if path:
                return path
            
            # 方法3: 使用Shell.Application的高级方法
            path = self._get_path_via_shell_application_advanced(hwnd)
            if path:
                return path
            
            # 方法4: 回退到智能推断
            path = self._fallback_path_detection(hwnd, class_name)
            if path:
                return path
            
            self.logger.error("所有方法都失败，无法获取资源管理器路径")
            return None
            
        except Exception as e:
            self.logger.error(f"获取资源管理器路径失败: {e}")
            import traceback
            self.logger.debug(f"详细错误: {traceback.format_exc()}")
            return None
    
    def _build_window_hierarchy(self, hwnd, max_levels=5):
        """构建窗口层次结构，用于分析复杂的嵌套关系"""
        hierarchy = []
        current_hwnd = hwnd
        
        for level in range(max_levels):
            if not current_hwnd:
                break
            
            try:
                class_name = win32gui.GetClassName(current_hwnd)
                window_title = win32gui.GetWindowText(current_hwnd)
                hierarchy.append((current_hwnd, class_name, window_title))
                
                # 获取父窗口
                parent_hwnd = win32gui.GetParent(current_hwnd)
                if parent_hwnd == current_hwnd:  # 避免无限循环
                    break
                current_hwnd = parent_hwnd
                
            except Exception as e:
                self.logger.debug(f"构建窗口层次结构时出错: {e}")
                break
        
        return hierarchy
    
    def _get_path_via_shell_application_advanced(self, hwnd):
        """使用Shell.Application的高级方法获取路径"""
        try:
            import win32com.client
            shell = win32com.client.Dispatch("Shell.Application")
            
            # 获取所有打开的资源管理器窗口
            windows = shell.Windows()
            
            # 创建一个窗口映射，包括所有相关的HWND
            window_map = {}
            for window in windows:
                try:
                    main_hwnd = window.HWND
                    location = window.LocationURL
                    
                    # 获取窗口的所有子窗口
                    child_hwnds = []
                    def enum_child_proc(child_hwnd, lParam):
                        child_hwnds.append(child_hwnd)
                        return True
                    
                    win32gui.EnumChildWindows(main_hwnd, enum_child_proc, 0)
                    
                    # 将主窗口和所有子窗口都映射到同一个位置
                    for related_hwnd in [main_hwnd] + child_hwnds:
                        window_map[related_hwnd] = location
                        
                except Exception:
                    continue
            
            # 查找目标窗口
            if hwnd in window_map:
                location = window_map[hwnd]
                return self._convert_location_to_path(location)
            
            # 查找父窗口
            parent_hwnd = win32gui.GetParent(hwnd)
            if parent_hwnd and parent_hwnd in window_map:
                location = window_map[parent_hwnd]
                return self._convert_location_to_path(location)
            
            # 查找祖父窗口
            if parent_hwnd:
                grandparent_hwnd = win32gui.GetParent(parent_hwnd)
                if grandparent_hwnd and grandparent_hwnd in window_map:
                    location = window_map[grandparent_hwnd]
                    return self._convert_location_to_path(location)
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Shell.Application高级方法失败: {e}")
            return None
    
    def _convert_location_to_path(self, location):
        """将位置URL转换为文件系统路径"""
        if not location:
            return None
        
        try:
            if location.startswith('file:///'):
                import urllib.parse
                path = urllib.parse.unquote(location[8:])
                path = path.replace('/', '\\')
                if os.path.exists(path):
                    return path
            
            # 尝试使用Windows API
            try:
                import ctypes
                from ctypes import wintypes
                
                # 调用PathCreateFromUrl
                shlwapi = ctypes.windll.shlwapi
                path_buffer = ctypes.create_unicode_buffer(260)
                path_size = wintypes.DWORD(260)
                
                result = shlwapi.PathCreateFromUrlW(
                    location,
                    path_buffer,
                    ctypes.byref(path_size),
                    0
                )
                
                if result == 0:  # S_OK
                    path = path_buffer.value
                    if os.path.exists(path):
                        return path
            except Exception as e:
                self.logger.debug(f"PathCreateFromUrl调用失败: {e}")
            
            return None
            
        except Exception as e:
            self.logger.debug(f"转换位置URL失败: {e}")
            return None
    
    def _fallback_path_detection(self, hwnd, class_name):
        """回退路径检测方法"""
        try:
            self.logger.info("使用回退路径检测方法")
            
            # 获取进程信息
            try:
                thread_id, process_id = win32gui.GetWindowThreadProcessId(hwnd)
                if process_id:
                    import psutil
                    process = psutil.Process(process_id)
                    
                    # 检查是否是explorer.exe进程
                    if 'explorer.exe' in process.name().lower():
                        self.logger.info("检测到explorer.exe进程")
                        
                        # 尝试获取进程的工作目录
                        try:
                            cwd = process.cwd()
                            if cwd and os.path.exists(cwd):
                                self.logger.info(f"使用进程工作目录: {cwd}")
                                return cwd
                        except Exception:
                            pass
                        
                        # 使用常用的资源管理器目录
                        common_explorer_dirs = [
                            os.path.join(os.path.expanduser("~"), "Documents"),
                            os.path.join(os.path.expanduser("~"), "Downloads"),
                            os.path.join(os.path.expanduser("~"), "Pictures"),
                            os.path.join(os.path.expanduser("~"), "Desktop"),
                            "C:\\",
                            os.path.expanduser("~")
                        ]
                        
                        for dir_path in common_explorer_dirs:
                            if os.path.exists(dir_path):
                                self.logger.info(f"使用常用目录: {dir_path}")
                                return dir_path
            except Exception as e:
                self.logger.debug(f"进程信息获取失败: {e}")
            
            # 最后的回退选项
            fallback_dirs = [
                os.path.join(os.path.expanduser("~"), "Downloads"),
                os.path.join(os.path.expanduser("~"), "Documents"),
                os.path.join(os.path.expanduser("~"), "Desktop"),
                os.path.expanduser("~")
            ]
            
            for dir_path in fallback_dirs:
                if os.path.exists(dir_path):
                    self.logger.info(f"使用最终回退目录: {dir_path}")
                    return dir_path
            
            return None
            
        except Exception as e:
            self.logger.debug(f"回退路径检测失败: {e}")
            return None
    
    def _get_path_via_com(self, hwnd):
        """通过COM接口获取路径 - 增强版，支持Windows 10/11"""
        try:
            self.logger.info(f"尝试通过COM接口获取路径，HWND: {hwnd}")
            import win32com.client
            
            # 创建Shell应用程序对象
            shell = win32com.client.Dispatch("Shell.Application")
            windows = shell.Windows()
            
            # 方法1: 直接匹配HWND
            for window in windows:
                try:
                    if window.HWND == hwnd:
                        self.logger.debug(f"找到匹配的COM窗口，HWND: {hwnd}")
                        return self._extract_path_from_com_window(window)
                except Exception:
                    continue
            
            # 方法2: 查找父窗口的HWND（用于处理子窗口）
            parent_hwnd = win32gui.GetParent(hwnd)
            if parent_hwnd:
                self.logger.debug(f"尝试父窗口HWND: {parent_hwnd}")
                for window in windows:
                    try:
                        if window.HWND == parent_hwnd:
                            self.logger.debug(f"通过父窗口找到COM窗口")
                            return self._extract_path_from_com_window(window)
                    except Exception:
                        continue
            
            # 方法3: 查找祖父窗口的HWND（用于处理Windows 11的深层嵌套）
            if parent_hwnd:
                grandparent_hwnd = win32gui.GetParent(parent_hwnd)
                if grandparent_hwnd:
                    self.logger.debug(f"尝试祖父窗口HWND: {grandparent_hwnd}")
                    for window in windows:
                        try:
                            if window.HWND == grandparent_hwnd:
                                self.logger.debug(f"通过祖父窗口找到COM窗口")
                                return self._extract_path_from_com_window(window)
                        except Exception:
                            continue
            
            # 方法4: 基于窗口位置的智能匹配（用于DirectUIHWND等复杂情况）
            try:
                target_rect = win32gui.GetWindowRect(hwnd)
                target_center_x = (target_rect[0] + target_rect[2]) // 2
                target_center_y = (target_rect[1] + target_rect[3]) // 2
                
                for window in windows:
                    try:
                        window_hwnd = window.HWND
                        window_rect = win32gui.GetWindowRect(window_hwnd)
                        
                        # 检查目标窗口是否在当前资源管理器窗口内
                        if (window_rect[0] <= target_center_x <= window_rect[2] and 
                            window_rect[1] <= target_center_y <= window_rect[3]):
                            self.logger.debug(f"通过位置匹配找到COM窗口: {window_hwnd}")
                            path = self._extract_path_from_com_window(window)
                            if path:
                                return path
                    except Exception:
                        continue
            except Exception as e:
                self.logger.debug(f"位置匹配失败: {e}")
            
            self.logger.warning(f"在COM接口中未找到HWND {hwnd}对应的窗口")
            return None
                
        except Exception as com_error:
            self.logger.warning(f"COM接口获取路径失败: {com_error}")
            return None
    
    def _extract_path_from_com_window(self, window):
        """从COM窗口对象中提取路径"""
        try:
            location = window.LocationURL
            self.logger.debug(f"COM窗口位置URL: {location}")
            
            if not location:
                self.logger.debug("COM窗口位置URL为空")
                return None
            
            # 处理file:///格式的URL
            if location.startswith('file:///'):
                import urllib.parse
                path = urllib.parse.unquote(location[8:])  # 移除 'file:///' 前缀
                path = path.replace('/', '\\')
                self.logger.debug(f"解析后的路径: {path}")
                
                if os.path.exists(path):
                    self.logger.info(f"通过COM接口获取到路径: {path}")
                    return path
                else:
                    self.logger.warning(f"COM解析的路径不存在: {path}")
            
            # 处理其他格式的URL（如网络位置等）
            elif ':\\' in location:
                # 直接包含驱动器路径
                import re
                path_match = re.search(r'[A-Za-z]:\\[^<>:"|?*\n\r]*', location)
                if path_match:
                    path = path_match.group(0)
                    if os.path.exists(path):
                        self.logger.info(f"从COM URL中提取到路径: {path}")
                        return path
            
            # 使用Windows API进行URL到路径的转换
            try:
                import win32api
                path = win32api.PathCreateFromUrl(location)
                if path and os.path.exists(path):
                    self.logger.info(f"通过Windows API转换URL到路径: {path}")
                    return path
            except Exception as e:
                self.logger.debug(f"Windows API转换URL失败: {e}")
            
            self.logger.debug(f"无法从COM位置URL获取有效路径: {location}")
            return None
            
        except Exception as e:
            self.logger.debug(f"从COM窗口提取路径失败: {e}")
            return None
    
    def _extract_path_from_title(self, window_title):
        """从窗口标题中提取路径"""
        try:
            if not window_title or ':\\' not in window_title:
                return None
            
            self.logger.debug(f"窗口标题包含驱动器路径: '{window_title}'")
            
            # 方法1: 直接包含完整路径的情况
            for part in window_title.split(' '):
                if ':\\' in part:
                    self.logger.debug(f"检查路径片段: '{part}'")
                    # 清理路径片段（移除可能的前后缀）
                    clean_part = part.strip('()[]{}"\'-.,;:')
                    if os.path.exists(clean_part) and os.path.isdir(clean_part):
                        self.logger.info(f"从窗口标题提取到路径: {clean_part}")
                        return clean_part
            
            # 方法2: 使用正则表达式提取路径模式
            import re
            # 匹配标准的Windows路径格式
            path_patterns = [
                r'[A-Za-z]:\\[^<>:"|?*\n\r\t]+',  # 标准路径
                r'[A-Za-z]:\\[^\s<>:"|?*\n\r\t]+',  # 不包含空格的路径
                r'[A-Za-z]:\\[^,\s<>:"|?*\n\r\t]+',  # 不包含逗号和空格的路径
            ]
            
            for pattern in path_patterns:
                matches = re.findall(pattern, window_title)
                for match in matches:
                    # 清理匹配结果
                    clean_match = match.rstrip('\\').rstrip('.,;:')
                    if os.path.exists(clean_match) and os.path.isdir(clean_match):
                        self.logger.info(f"通过正则表达式从标题提取到路径: {clean_match}")
                        return clean_match
            
            # 方法3: 特殊处理Windows 11的标题格式
            # 例如: "Documents - File Explorer" 或 "文档 - 文件资源管理器"
            title_lower = window_title.lower()
            folder_mappings = {
                'documents': os.path.join(os.path.expanduser("~"), "Documents"),
                'downloads': os.path.join(os.path.expanduser("~"), "Downloads"),
                'pictures': os.path.join(os.path.expanduser("~"), "Pictures"),
                'music': os.path.join(os.path.expanduser("~"), "Music"),
                'videos': os.path.join(os.path.expanduser("~"), "Videos"),
                'desktop': os.path.join(os.path.expanduser("~"), "Desktop"),
                '文档': os.path.join(os.path.expanduser("~"), "Documents"),
                '下载': os.path.join(os.path.expanduser("~"), "Downloads"),
                '图片': os.path.join(os.path.expanduser("~"), "Pictures"),
                '音乐': os.path.join(os.path.expanduser("~"), "Music"),
                '视频': os.path.join(os.path.expanduser("~"), "Videos"),
                '桌面': os.path.join(os.path.expanduser("~"), "Desktop"),
            }
            
            for folder_name, folder_path in folder_mappings.items():
                if folder_name in title_lower and os.path.exists(folder_path):
                    self.logger.info(f"通过文件夹名称映射提取到路径: {folder_path}")
                    return folder_path
            
            self.logger.warning("窗口标题包含路径指示符但无法提取有效路径")
            return None
            
        except Exception as e:
            self.logger.debug(f"从窗口标题提取路径失败: {e}")
            return None
    
    def _get_folder_window_path(self, hwnd):
        """获取文件夹窗口的路径"""
        try:
            # 尝试获取窗口标题
            window_title = win32gui.GetWindowText(hwnd)
            self.logger.info(f"文件夹窗口标题: '{window_title}'")
            
            # 如果标题包含路径信息
            if ':\\' in window_title:
                for part in window_title.split(' '):
                    if ':\\' in part and os.path.exists(part):
                        self.logger.info(f"从文件夹窗口标题获取路径: {part}")
                        return part
            
            # 对于DirectUIHWND类型的窗口，尝试获取父窗口信息
            if win32gui.GetClassName(hwnd) == 'DirectUIHWND':
                self.logger.info("DirectUIHWND窗口，尝试获取父窗口信息")
                parent_hwnd = win32gui.GetParent(hwnd)
                if parent_hwnd:
                    parent_class = win32gui.GetClassName(parent_hwnd)
                    parent_title = win32gui.GetWindowText(parent_hwnd)
                    self.logger.info(f"父窗口: 类名='{parent_class}', 标题='{parent_title}'")
                    
                    # 如果父窗口是资源管理器
                    if self._is_explorer_window(parent_class, parent_hwnd):
                        path = self._get_explorer_path_advanced(parent_hwnd)
                        if path:
                            self.logger.info(f"从父窗口获取到路径: {path}")
                            return path
                    
                    # 尝试从父窗口标题获取路径
                    if ':\\' in parent_title:
                        for part in parent_title.split(' '):
                            if ':\\' in part and os.path.exists(part):
                                self.logger.info(f"从父窗口标题获取路径: {part}")
                                return part
            
            self.logger.warning("无法从文件夹窗口获取路径")
            return None
            
        except Exception as e:
            self.logger.error(f"获取文件夹窗口路径失败: {e}")
            import traceback
            self.logger.debug(f"详细错误: {traceback.format_exc()}")
            return None
    
    def _smart_detect_target_path(self, class_name, window_title, hwnd):
        """智能检测目标路径（用于未识别的窗口类型）"""
        try:
            self.logger.info(f"开始智能检测目标路径: 类名='{class_name}', 标题='{window_title}'")
            
            # 1. 特殊处理DirectUIHWND窗口（Windows 11文件管理器常见）
            if class_name == 'DirectUIHWND':
                self.logger.info("DirectUIHWND窗口，尝试特殊处理")
                # 尝试通过COM接口获取所有资源管理器窗口
                try:
                    import win32com.client
                    shell = win32com.client.Dispatch("Shell.Application")
                    
                    # 获取鼠标位置附近的资源管理器窗口
                    for window in shell.Windows():
                        try:
                            window_hwnd = window.HWND
                            # 检查窗口位置是否接近鼠标位置
                            window_rect = win32gui.GetWindowRect(window_hwnd)
                            if (window_rect[0] <= hwnd <= window_rect[2] and 
                                window_rect[1] <= hwnd <= window_rect[3]):
                                location = window.LocationURL
                                if location and location.startswith('file:///'):
                                    import urllib.parse
                                    path = urllib.parse.unquote(location[8:])
                                    path = path.replace('/', '\\')
                                    if os.path.exists(path):
                                        self.logger.info(f"DirectUIHWND通过COM获取路径: {path}")
                                        return path
                        except Exception:
                            continue
                except Exception as e:
                    self.logger.debug(f"DirectUIHWND特殊处理失败: {e}")
            
            # 2. 检查是否是常见的应用程序，如果是则使用Downloads目录
            common_app_classes = [
                'Chrome_RenderWidgetHostHWND',  # Chrome浏览器
                'MozillaWindowClass',           # Firefox浏览器
                'MSEdgeWebView2',               # Edge浏览器
                'Notepad',                      # 记事本
                'WordPadClass',                 # 写字板
                'XLMAIN',                       # Excel
                'OpusApp',                      # Word
                'PPTFrameClass',                # PowerPoint
                'WinRAR',                       # WinRAR
                '7zFMClass',                    # 7-Zip
                'VLC DirectX video output',     # VLC播放器
                'PotPlayer',                    # PotPlayer
                'QWidget',                      # Qt应用程序
                'SunAwtFrame',                  # Java应用程序
                'ConsoleWindowClass',           # 控制台窗口
                'CASCADIA_HOSTING_WINDOW_CLASS' # Windows Terminal
            ]
            
            if any(app_class in class_name for app_class in common_app_classes):
                self.logger.info(f"识别为常见应用程序: {class_name}")
                # 对于常见应用程序，默认下载到Downloads目录
                downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
                if os.path.exists(downloads_path):
                    self.logger.info(f"使用Downloads目录: {downloads_path}")
                    return downloads_path
            
            # 3. 检查窗口标题是否包含路径信息
            if ':\\' in window_title:
                self.logger.info("窗口标题包含路径信息，尝试提取")
                # 尝试从标题中提取路径
                import re
                path_pattern = r'[A-Za-z]:\\[^<>:"|?*\n\r]*'
                paths = re.findall(path_pattern, window_title)
                
                for path in paths:
                    path = path.strip()
                    if os.path.exists(path) and os.path.isdir(path):
                        self.logger.info(f"从窗口标题提取到有效路径: {path}")
                        return path
            
            # 4. 尝试获取应用程序的工作目录
            try:
                import psutil
                # 获取窗口对应的进程ID
                thread_id, process_id = win32gui.GetWindowThreadProcessId(hwnd)
                if process_id:
                    process = psutil.Process(process_id)
                    cwd = process.cwd()
                    if cwd and os.path.exists(cwd) and os.path.isdir(cwd):
                        self.logger.info(f"使用进程工作目录: {cwd}")
                        return cwd
            except Exception as e:
                self.logger.debug(f"获取进程工作目录失败: {e}")
            
            # 5. 检查是否是特殊的系统窗口
            system_window_classes = [
                'Shell_TrayWnd',     # 任务栏
                'Button',            # 按钮
                'Static',            # 静态文本
                'Edit',              # 编辑框
                'ComboBox',          # 组合框
                'ListBox',           # 列表框
                'SysTabControl32',   # 标签页控件
                'SysListView32',     # 列表视图
                'SysTreeView32',     # 树形视图
            ]
            
            if class_name in system_window_classes:
                self.logger.info(f"识别为系统控件: {class_name}，使用桌面作为目标")
                desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
                if os.path.exists(desktop_path):
                    return desktop_path
            
            # 6. 最后的回退策略：使用最常用的目录
            self.logger.info("使用回退策略，返回最常用的目录")
            fallback_dirs = [
                os.path.join(os.path.expanduser("~"), "Downloads"),  # 优先Downloads
                os.path.join(os.path.expanduser("~"), "Documents"),  # 其次Documents
                os.path.join(os.path.expanduser("~"), "Desktop"),    # 然后Desktop
                os.path.expanduser("~")                              # 最后用户主目录
            ]
            
            for dir_path in fallback_dirs:
                if os.path.exists(dir_path):
                    self.logger.info(f"使用回退目录: {dir_path}")
                    return dir_path
            
            self.logger.warning("所有智能检测方法都失败")
            return None
            
        except Exception as e:
            self.logger.error(f"智能检测目标路径失败: {e}")
            import traceback
            self.logger.debug(f"详细错误: {traceback.format_exc()}")
            return None
    
    def _show_directory_dialog(self):
        """显示目录选择对话框"""
        from tkinter import filedialog
        
        target_dir = filedialog.askdirectory(
            title=f"选择下载位置 - {self.drag_data['filename']}",
            initialdir=os.path.expanduser("~/Downloads")
        )
        
        if target_dir:
            self.logger.info(f"用户选择下载目录: {target_dir}")
            
            # 触发下载
            if self.drag_drop_callback:
                # 创建一个模拟的事件对象，包含目标目录信息
                mock_event = type('MockEvent', (), {
                    'target_dir': target_dir,
                    'external_drop': True
                })()
                
                self.drag_drop_callback(self.drag_data, mock_event)
        else:
            self.logger.info("用户取消了下载")
    
    def _show_invalid_drop_hint(self):
        """显示无效拖放的提示"""
        try:
            # 可以在这里添加视觉提示，比如闪烁效果或者提示音
            # 目前只记录日志
            self.logger.info(f"无法拖放文件 {self.drag_data['filename']} 到此位置")
            
            # 可选：显示简短的提示消息
            # 注意：不要使用messagebox，因为会阻塞UI
            # 可以考虑使用toast通知或者状态栏提示
            
        except Exception as e:
            self.logger.debug(f"显示无效拖放提示失败: {e}")
    
    def _is_directory_item(self, is_directory_value) -> bool:
        """判断是否为目录项目"""
        if isinstance(is_directory_value, bool):
            return is_directory_value
        elif isinstance(is_directory_value, str):
            return is_directory_value.lower() in ['true', '1', 'yes']
        else:
            return bool(is_directory_value)
    
    def set_drag_start_callback(self, callback: Callable):
        """设置拖拽开始回调函数
        
        Args:
            callback: 回调函数，接收 drag_data 参数
        """
        self.drag_start_callback = callback
    
    def set_drag_drop_callback(self, callback: Callable):
        """设置拖拽结束回调函数
        
        Args:
            callback: 回调函数，接收 (drag_data, event) 参数
        """
        self.drag_drop_callback = callback
    
    def enable_drag(self):
        """启用拖拽功能"""
        self._bind_drag_events()
        self.logger.debug("拖拽功能已启用")
    
    def disable_drag(self):
        """禁用拖拽功能"""
        # 只解绑拖拽相关的事件，不要影响双击事件
        try:
            self.treeview.unbind('<B1-Motion>')
            self.treeview.unbind('<ButtonRelease-1>')
            
            # 如果有原有的双击处理器，恢复它
            if self.original_double_click_handler:
                self.treeview.bind('<Double-1>', self.original_double_click_handler)
                self.logger.debug("已恢复原有双击事件处理器")
            
        except Exception as e:
            self.logger.error(f"禁用拖拽功能时出错: {e}")
        
        # 重置状态
        self.is_dragging = False
        self.drag_data = None
        
        self.logger.debug("拖拽功能已禁用")


class DragDropIndicator:
    """拖拽指示器"""
    
    def __init__(self, parent, theme):
        """初始化拖拽指示器
        
        Args:
            parent: 父窗口
            theme: 主题对象
        """
        self.parent = parent
        self.theme = theme
        self.indicator_window = None
        
    def show_indicator(self, x, y, filename):
        """显示拖拽指示器
        
        Args:
            x: X坐标
            y: Y坐标
            filename: 文件名
        """
        if self.indicator_window:
            self.hide_indicator()
        
        # 创建指示器窗口
        self.indicator_window = tk.Toplevel(self.parent)
        self.indicator_window.wm_overrideredirect(True)
        self.indicator_window.configure(bg=self.theme.colors['bg_card'])
        
        # 创建指示器内容
        label = tk.Label(
            self.indicator_window,
            text=f"📄 {filename}",
            bg=self.theme.colors['bg_card'],
            fg=self.theme.colors['text_primary'],
            font=('Microsoft YaHei UI', 9),
            padx=10,
            pady=5
        )
        label.pack()
        
        # 设置位置
        self.indicator_window.geometry(f"+{x+10}+{y+10}")
        self.indicator_window.lift()
    
    def hide_indicator(self):
        """隐藏拖拽指示器"""
        if self.indicator_window:
            self.indicator_window.destroy()
            self.indicator_window = None
    
    def update_position(self, x, y):
        """更新指示器位置
        
        Args:
            x: X坐标
            y: Y坐标
        """
        if self.indicator_window:
            self.indicator_window.geometry(f"+{x+10}+{y+10}") 