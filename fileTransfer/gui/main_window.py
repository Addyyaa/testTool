#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
现代化文件传输工具主窗口

集成各个组件模块，提供统一的GUI界面
"""

import asyncio
import os
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
import tkinterdnd2 as tkdnd
from typing import Dict, List, Optional, Any
import logging
import socket
import re

# 添加父目录到系统路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from telnetTool.telnetConnect import CustomTelnetClient

# 修复相对导入
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from http_server import FileHTTPServer
from file_transfer_controller import RemoteFileEditor
from ip_history_manager import IPHistoryManager
from logger_utils import get_logger

# 导入组件模块
from .styles import ModernTheme
from .connection_panel import ConnectionPanel
from .directory_panel import DirectoryPanel
from .transfer_panel import TransferPanel
from .file_editor import RemoteFileEditorGUI
from ..drag_download_manager import DragDownloadManager


class ModernFileTransferGUI:
    """现代化文件传输GUI主界面"""
    
    def __init__(self):
        """初始化GUI界面"""
        # 初始化主题
        self.theme = ModernTheme()
        
        # 创建主窗口
        self.root = tkdnd.Tk()
        self.root.title("202文件传输工具")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 600)
        self.root.configure(bg=self.theme.colors['bg_primary'])
        
        # 设置图标
        self._set_window_icon()
        
        # 配置样式
        self.style = ttk.Style()
        self.theme.setup_styles(self.style)
        
        # 初始化组件
        self.telnet_client: Optional[CustomTelnetClient] = None
        self.http_server: Optional[FileHTTPServer] = None
        self.current_remote_path = "/"
        self.connection_config = {}
        self.is_connected = False
        
        # 添加刷新状态控制
        self.is_refreshing = False
        self.refresh_pending = False
        self.last_refresh_time = 0
        
        # 初始化拖拽下载管理器
        self.drag_download_manager = DragDownloadManager()
        self.drag_download_manager.set_progress_callback(self._on_drag_download_progress)
        self.drag_download_manager.set_completion_callback(self._on_drag_download_complete)
        self.drag_download_manager.set_error_callback(self._on_drag_download_error)
        
        # 配置日志
        self._setup_logging()
        
        # 创建界面元素
        self._create_widgets()
        
        # 绑定事件
        self._bind_events()
        
        # 初始化响应式布局
        self._setup_responsive_layout()
        
        # 设置异步事件循环
        self.loop = None
        self.loop_thread = None
        self.telnet_lock = None
        self._start_event_loop()
        
        self.logger.info("GUI界面初始化完成")
    
    def _set_window_icon(self):
        """设置窗口图标"""
        try:
            icon_path = os.path.join(os.path.dirname(__file__), '..', '..', 'resource', 'logo', 'log.ico')
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception:
            pass
    
    def _setup_logging(self):
        """配置日志系统"""
        self.logger = get_logger(self.__class__)
        # 日志等级现在由统一配置管理，无需手动设置
        
        # 创建自定义日志处理器
        class GUILogHandler(logging.Handler):
            def __init__(self, gui_instance):
                super().__init__()
                self.gui = gui_instance
                
            def emit(self, record):
                try:
                    msg = self.format(record)
                    if hasattr(self.gui, 'transfer_panel'):
                        self.gui.transfer_panel.append_log(msg)
                except Exception:
                    pass
        
        if not self.logger.handlers:
            gui_handler = GUILogHandler(self)
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s:%(lineno)d - %(message)s')
            gui_handler.setFormatter(formatter)
            self.logger.addHandler(gui_handler)
    
    def _create_widgets(self):
        """创建界面组件"""
        # 创建状态栏（先创建，在底部）
        self._create_status_bar()
        
        # 主容器（占用除状态栏外的所有空间）
        self.main_frame = tk.Frame(self.root, bg=self.theme.colors['bg_primary'])
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        
        # 创建侧边栏
        self._create_sidebar()
        
        # 创建主内容区域
        self._create_main_content()
    
    def _create_sidebar(self):
        """创建现代化侧边栏"""
        # 侧边栏容器 - 占窗口宽度的28%
        self.sidebar_frame = tk.Frame(self.main_frame, bg=self.theme.colors['bg_sidebar'])
        self.sidebar_frame.place(x=0, y=0, relwidth=0.28, relheight=1.0)
        
        # 创建连接面板
        self.connection_panel = ConnectionPanel(self.sidebar_frame, self.theme, self.logger)
        self.connection_panel.set_connect_callback(self._on_connect_request)
        self.connection_panel.set_disconnect_callback(self._on_disconnect_request)
        
        # 创建目录面板
        self.directory_panel = DirectoryPanel(self.sidebar_frame, self.theme, self.logger)
        self.directory_panel.set_refresh_callback(self._on_directory_refresh)
        self.directory_panel.set_path_change_callback(self._on_path_change)
        self.directory_panel.set_file_select_callback(self._on_file_select)
        self.directory_panel.set_file_delete_callback(self._on_file_delete)
        self.directory_panel.set_file_edit_callback(self._on_file_edit)
        self.directory_panel.set_drag_download_callback(self._on_drag_download_request)
    
    def _create_main_content(self):
        """创建现代化主内容区域"""
        # 主内容容器
        self.content_frame = tk.Frame(self.main_frame, bg=self.theme.colors['bg_primary'])
        self.content_frame.place(relx=0.28, rely=0, relwidth=0.72, relheight=1.0)
        
        # 创建传输面板（包含拖拽区域和日志）
        self.transfer_panel = TransferPanel(self.content_frame, self.theme, self.logger)
        self.transfer_panel.set_start_transfer_callback(self._start_transfer)
        self.transfer_panel.set_clear_queue_callback(self._clear_transfer_queue)
        self.transfer_panel.set_files_added_callback(self._on_files_added)
    
    def _create_status_bar(self):
        """创建状态栏"""
        self.status_bar = tk.Frame(self.root, bg=self.theme.colors['bg_secondary'], relief='sunken', borderwidth=1, height=25)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_bar.pack_propagate(False)  # 固定高度
        
        # 状态信息
        self.status_var = tk.StringVar(value="就绪")
        self.status_label = tk.Label(self.status_bar, textvariable=self.status_var, 
                                   bg=self.theme.colors['bg_secondary'], fg=self.theme.colors['text_primary'],
                                   font=('Microsoft YaHei UI', 9))
        self.status_label.pack(side=tk.LEFT, padx=10, pady=2)
        
        # HTTP服务器状态
        self.http_status_var = tk.StringVar(value="HTTP服务: 未启动")
        self.http_status_label = tk.Label(self.status_bar, textvariable=self.http_status_var,
                                        bg=self.theme.colors['bg_secondary'], fg=self.theme.colors['text_secondary'],
                                        font=('Microsoft YaHei UI', 9))
        self.http_status_label.pack(side=tk.RIGHT, padx=10, pady=2)
    
    def _bind_events(self):
        """绑定界面事件"""
        # 窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _setup_responsive_layout(self):
        """设置响应式布局"""
        # 记录初始窗口尺寸
        self.root.update_idletasks()
        self.initial_width = self.root.winfo_width()
        self.initial_height = self.root.winfo_height()
        
        # 绑定窗口大小变化事件
        self.root.bind('<Configure>', self._on_window_resize)
        
        # 应用初始布局
        self._apply_responsive_layout()
    
    def _on_window_resize(self, event):
        """窗口大小变化事件处理"""
        # 只处理主窗口的大小变化事件
        if event.widget == self.root:
            self.root.after_idle(self._apply_responsive_layout)
    
    def _apply_responsive_layout(self):
        """应用响应式布局"""
        try:
            window_width = self.root.winfo_width()
            window_height = self.root.winfo_height()
            
            if window_width <= 1 or window_height <= 1:
                return  # 窗口还没有完全初始化
            
            # 计算侧边栏宽度（窗口宽度的25%，最小280px，最大400px）
            sidebar_width = max(280, min(400, int(window_width * 0.25)))
            
            # 重新配置侧边栏
            if hasattr(self, 'sidebar_frame'):
                self.sidebar_frame.configure(width=sidebar_width)
                
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.debug(f"布局调整出错: {e}")
    
    def _start_event_loop(self):
        """启动异步事件循环"""
        def run_loop():
            try:
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)
                
                # 在事件循环中创建telnet锁
                async def create_lock():
                    self.telnet_lock = asyncio.Lock()
                    self.logger.info("异步事件循环和telnet锁已创建")
                
                # 创建锁并运行事件循环
                self.loop.run_until_complete(create_lock())
                self.logger.info("异步事件循环已启动")
                self.loop.run_forever()
            except Exception as e:
                self.logger.error(f"异步事件循环启动失败: {e}")
        
        self.loop_thread = threading.Thread(target=run_loop, daemon=True)
        self.loop_thread.start()
        
        # 等待事件循环启动
        wait_count = 0
        max_wait = 50
        while (self.loop is None or self.telnet_lock is None) and wait_count < max_wait:
            time.sleep(0.01)
            wait_count += 1
        
        if wait_count >= max_wait:
            self.logger.error("异步事件循环启动超时")
        else:
            self.logger.info(f"异步事件循环启动完成，等待了 {wait_count * 10}ms")
    
    def _run_async(self, coro):
        """在事件循环中运行异步任务"""
        try:
            if self.loop and not self.loop.is_closed():
                future = asyncio.run_coroutine_threadsafe(coro, self.loop)
                return future
            else:
                self.logger.error("事件循环不可用")
                return None
        except Exception as e:
            self.logger.error(f"创建异步任务失败: {e}")
            return None
    
    # 连接相关回调方法
    def _on_connect_request(self, config: Dict[str, Any]):
        """处理连接请求"""
        try:
            self.logger.info(f"开始连接到 {config['host']}")
            self.connection_config = config
            
            from telnetTool.telnetConnect import CustomTelnetClient
            self.telnet_client = CustomTelnetClient(
                host=config['host'],
                port=config['port'],
                timeout=30.0
            )
            
            # 使用回调方式避免阻塞UI线程
            future = self._run_async(self._do_connect())
            if future:
                future.add_done_callback(self._on_connect_result)
            else:
                self._on_connect_failed("无法启动异步任务")
        except Exception as e:
            self._on_connect_failed(str(e))
    
    def _on_connect_result(self, future):
        """处理连接结果回调"""
        try:
            result = future.result()
            if result:
                self.root.after(0, self._on_connect_success)
            else:
                self.root.after(0, lambda: self._on_connect_failed("连接失败"))
        except Exception as e:
            self.root.after(0, lambda: self._on_connect_failed(str(e)))
    
    async def _do_connect(self):
        """执行连接"""
        try:
            success = await self.telnet_client.connect(
                username=self.connection_config['username'],
                password=self.connection_config['password'],
                shell_prompt='#'
            )
            if success:
                await self.telnet_client.execute_command('pwd')
                return True
            return False
        except Exception as e:
            self.logger.error(f"连接失败: {str(e)}")
            return False
    
    def _on_connect_success(self):
        """连接成功"""
        try:
            self.is_connected = True
            current_ip = self.connection_config['host']
            
            # 更新连接面板状态
            self.connection_panel.update_connection_status(True, ip=current_ip)
            
            # 启动HTTP服务器
            if not self.http_server:
                self._start_http_server_delayed()
            else:
                # 如果HTTP服务器已启动，更新其telnet客户端引用以支持二进制文件自动chmod
                self.logger.info("更新HTTP服务器的telnet客户端引用，启用二进制文件自动chmod功能")
                self.http_server.telnet_client = self.telnet_client
            
            # 更新拖拽下载管理器的客户端
            self.drag_download_manager.set_clients(self.telnet_client, self.http_server, self.loop, self.telnet_lock)
            
            # 启用拖拽下载功能
            self.directory_panel.enable_drag_download()
            
            # 更新状态
            self._update_status(f"成功连接到 {current_ip}")
            
            # 创建文件编辑器
            self.file_editor = RemoteFileEditorGUI(
                self.root, self.theme, self.logger,
                self.telnet_client, self.http_server, self.loop, self.telnet_lock
            )
            
            # 自动刷新目录
            self.root.after(200, self._auto_refresh_directory)
            
            self.logger.info("连接成功处理完成！")
            
        except Exception as e:
            self.logger.error(f"连接成功处理过程中出错: {e}")
    
    def _on_connect_failed(self, error_msg: str):
        """连接失败"""
        self.connection_panel.update_connection_status(False, f"连接失败: {error_msg}")
        self._update_status(f"连接失败: {error_msg}")
        messagebox.showerror("连接失败", f"无法连接到设备:\n{error_msg}")
    
    def _on_disconnect_request(self):
        """处理断开连接请求"""
        try:
            self.is_connected = False
            
            # 重置刷新状态
            self.is_refreshing = False
            self.refresh_pending = False
            
            # 禁用拖拽下载功能
            self.directory_panel.disable_drag_download()
            
            # 清理拖拽下载管理器
            self.drag_download_manager.cancel_all_downloads()
            
            # 停止HTTP服务器
            if self.http_server:
                self.http_server.stop()
                self.http_server = None
            
            # 断开telnet
            if self.telnet_client:
                future = self._run_async(self.telnet_client.disconnect())
                if future:
                    future.result(timeout=5)
                self.telnet_client = None
            
            # 重置状态
            self.connection_panel.update_connection_status(False, "已断开连接")
            self.directory_panel.update_directory_tree([])
            self.directory_panel.set_current_path("/")
            self.directory_panel.set_refresh_status(False)  # 重置刷新按钮状态
            self.http_status_var.set("HTTP服务: 未启动")
            
            self._update_status("已断开连接")
            
        except Exception as e:
            self.logger.error(f"断开连接失败: {str(e)}")
    
    def _start_http_server_delayed(self):
        """延迟启动HTTP服务器"""
        try:
            self.logger.info("开始启动HTTP服务器...")
            threading.Thread(target=self._start_http_server_background, daemon=True).start()
        except Exception as e:
            self.logger.error(f"延迟启动HTTP服务器失败: {e}")
    
    def _start_http_server_background(self):
        """在后台线程中启动HTTP服务器"""
        try:
            if not self.http_server:
                # 传递telnet客户端以支持二进制文件自动chmod功能
                self.http_server = FileHTTPServer(port=88, telnet_client=self.telnet_client)
                self.http_server.start()
                
                # 在主线程中更新UI
                self.root.after(0, lambda: self.http_status_var.set(f"HTTP服务: 运行中 (端口88)"))
                self.root.after(0, lambda: self.logger.info(f"HTTP服务器已启动，已启用二进制文件自动chmod功能"))
                
        except Exception as e:
            self.logger.error(f"后台启动HTTP服务器失败: {str(e)}")
            self.root.after(0, lambda: messagebox.showerror("服务器错误", f"无法启动HTTP服务器:\n{str(e)}"))
    
    # 目录相关回调方法
    def _auto_refresh_directory(self):
        """自动刷新目录"""
        try:
            self.logger.info("开始自动刷新目录...")
            self.current_remote_path = "/"
            self.directory_panel.set_current_path(self.current_remote_path)
            self._refresh_directory()
        except Exception as e:
            self.logger.error(f"自动刷新目录失败: {e}")
    
    def _on_directory_refresh(self, path: str):
        """处理目录刷新请求"""
        if not self.is_connected:
            self._update_status("未连接，无法刷新目录")
            messagebox.showwarning("提示", "请先连接到设备")
            return
        
        import time
        current_time = time.time()
        
        # 防抖动：如果距离上次刷新不到300ms，忽略
        if current_time - self.last_refresh_time < 0.3:
            self.logger.debug("刷新请求过于频繁，忽略")
            return
        
        # 如果正在刷新，标记为待刷新
        if self.is_refreshing:
            self.logger.info("正在刷新中，标记为待刷新")
            self.refresh_pending = True
            return
        
        self.logger.info("用户手动触发目录刷新")
        self.last_refresh_time = current_time
        self._update_status("正在刷新目录...")
        self._refresh_directory()
    
    def _refresh_directory(self):
        """刷新目录"""
        if not self.is_connected:
            return
        
        if self.is_refreshing:
            self.logger.warning("已有刷新任务在进行中")
            # 检查是否超时，如果超时则重置状态
            if hasattr(self, '_refresh_start_time'):
                if time.time() - self._refresh_start_time > 30:  # 30秒超时
                    self.logger.warning("刷新任务超时，重置状态")
                    self.is_refreshing = False
                    self.root.after(0, lambda: self.directory_panel.set_refresh_status(False))
                else:
                    return
            else:
                return
            
        threading.Thread(target=self._refresh_directory_async, daemon=True).start()
    
    def _refresh_directory_async(self):
        """异步刷新目录"""
        try:
            # 设置刷新状态和开始时间
            self.is_refreshing = True
            self._refresh_start_time = time.time()
            self.refresh_pending = False
            
            # 更新UI状态
            self.root.after(0, lambda: self.directory_panel.set_refresh_status(True))
            
            self.logger.info(f"开始异步刷新目录: {self.current_remote_path}")
            
            if not self.loop or self.loop.is_closed():
                self.logger.error("异步事件循环不可用")
                self.is_refreshing = False
                self.root.after(0, lambda: self.directory_panel.set_refresh_status(False))
                return
            
            if not self.telnet_client:
                self.logger.error("Telnet客户端不存在")
                self.is_refreshing = False
                self.root.after(0, lambda: self.directory_panel.set_refresh_status(False))
                return
            
            future = self._run_async(self._get_directory_listing(self.current_remote_path))
            if future:
                future.add_done_callback(self._on_directory_result)
            else:
                self.logger.error("无法创建异步任务")
                self.is_refreshing = False
                self.root.after(0, lambda: self.directory_panel.set_refresh_status(False))
                
        except Exception as e:
            self.logger.error(f"刷新目录失败: {str(e)}")
            self.is_refreshing = False
            self.root.after(0, lambda: self.directory_panel.set_refresh_status(False))
    
    def _on_directory_result(self, future):
        """处理目录刷新结果回调"""
        try:
            items = future.result()
            self.logger.info(f"异步操作完成，获得 {len(items)} 个项目")
            self.root.after(0, lambda: self.directory_panel.update_directory_tree(items))
            
            # 更新状态信息
            if len(items) == 0:
                self.root.after(0, lambda: self._update_status(f"目录 {self.current_remote_path} 为空或已自动创建"))
            else:
                self.root.after(0, lambda: self._update_status(f"刷新完成，找到 {len(items)} 个项目"))
            
            # 如果是根目录刷新成功，尝试获取设备ID
            if self.current_remote_path == "/" and self.is_connected:
                self.root.after(100, self._try_get_device_id)
                
        except Exception as e:
            self.logger.error(f"目录刷新结果处理失败: {e}")
            self.root.after(0, lambda: self._update_status(f"目录刷新失败: {str(e)}"))
        finally:
            # 重置刷新状态
            self.is_refreshing = False
            if hasattr(self, '_refresh_start_time'):
                del self._refresh_start_time
            
            # 更新UI状态
            self.root.after(0, lambda: self.directory_panel.set_refresh_status(False))
            
            # 如果有待刷新请求，在短暂延迟后执行
            if self.refresh_pending:
                self.logger.info("检测到待刷新请求，将在500ms后执行")
                self.root.after(500, self._execute_pending_refresh)
    
    def _execute_pending_refresh(self):
        """执行待刷新请求"""
        if self.refresh_pending and not self.is_refreshing:
            self.logger.info("执行待刷新请求")
            self.refresh_pending = False
            self._refresh_directory()
    
    async def _get_directory_listing(self, path):
        """获取目录列表"""
        try:
            normalized_path = self._normalize_unix_path(path)
            self.logger.info(f"获取目录列表: '{path}' -> '{normalized_path}'")
            
            if not self.telnet_client:
                self.logger.error("Telnet客户端不存在")
                return []
            
            # 使用锁保护telnet连接
            async with self.telnet_lock:
                # 检查路径是否存在
                exist_result = await self.telnet_client.execute_command(f'test -e "{normalized_path}" && echo "EXISTS" || echo "NOT_EXISTS"')
                
                if "NOT_EXISTS" in exist_result:
                    self.logger.warning(f"路径 {normalized_path} 不存在")
                    # 尝试创建目录
                    self.logger.info(f"尝试创建目录: {normalized_path}")
                    mkdir_result = await self.telnet_client.execute_command(f'mkdir -p "{normalized_path}"')
                    
                    # 再次检查是否创建成功
                    exist_check = await self.telnet_client.execute_command(f'test -d "{normalized_path}" && echo "CREATED" || echo "CREATE_FAILED"')
                    if "CREATE_FAILED" in exist_check:
                        self.logger.error(f"无法创建目录: {normalized_path}")
                        return []
                    else:
                        self.logger.info(f"成功创建目录: {normalized_path}")
                
                # 检查路径是否是目录
                test_result = await self.telnet_client.execute_command(f'test -d "{normalized_path}" && echo "IS_DIR" || echo "NOT_DIR"')
                
                if "NOT_DIR" in test_result:
                    self.logger.warning(f"路径 {normalized_path} 存在但不是目录")
                    return []
                
                # 尝试使用带颜色的ls命令
                ls_cmd = f'ls -la --color=always "{normalized_path}"'
                self.logger.debug(f"执行ls命令: {ls_cmd}")
                result = await self.telnet_client.execute_command(ls_cmd)
                self.logger.debug(f"ls命令原始输出: {repr(result)}")
            
            # 解析目录内容
            items = self._parse_directory_output(result, path)
            self.logger.debug(f"解析得到 {len(items)} 个项目")
            return items
            
        except Exception as e:
            self.logger.error(f"获取目录列表失败: {str(e)}")
            return []
    
    def _parse_directory_output(self, output: str, base_path: str) -> List[Dict[str, Any]]:
        """解析目录输出"""
        items = []
        try:
            # 清理ANSI转义序列
            cleaned_result = self._clean_ansi_codes(output)
            lines = cleaned_result.strip().split('\n')
            self.logger.debug(f"清理后的输出行数: {len(lines)}")
            
            for i, line in enumerate(lines):
                line = line.strip()
                self.logger.debug(f"处理第{i}行: {repr(line)}")
                
                if not line or (i == 0 and line.startswith('total')):
                    self.logger.debug(f"跳过第{i}行: 空行或total行")
                    continue
                
                parts = line.split()
                self.logger.debug(f"第{i}行分割后: {len(parts)} 个部分: {parts}")
                
                if len(parts) >= 9:
                    permissions = parts[0]
                    name = ' '.join(parts[8:])
                    
                    if name in ['.', '..']:
                        self.logger.debug(f"跳过目录项: {name}")
                        continue
                    
                    name = self._clean_ansi_codes(name)
                    
                    if name:
                        is_directory = permissions.startswith('d')
                        is_executable = 'x' in permissions[1:4] and not is_directory
                        is_link = permissions.startswith('l')
                        
                        file_type = self._determine_file_type(permissions, name)
                        
                        item = {
                            'name': name,
                            'is_directory': is_directory,
                            'is_executable': is_executable,
                            'is_link': is_link,
                            'file_type': file_type,
                            'permissions': permissions,
                            'full_path': self._join_unix_path(base_path, name)
                        }
                        items.append(item)
                        self.logger.debug(f"添加项目: {name} (权限: {permissions})")
                else:
                    self.logger.debug(f"第{i}行部分不足9个，跳过: {parts}")
            
            self.logger.debug(f"最终解析得到 {len(items)} 个项目")
            return items
            
        except Exception as e:
            self.logger.error(f"解析目录输出失败: {str(e)}")
            return []
    
    def _on_path_change(self, new_path: str):
        """处理路径变化"""
        self.current_remote_path = new_path
        self.transfer_panel.set_target_path(new_path)
        self._refresh_directory()
    
    def _on_file_select(self, file_path: str, is_dir: bool, is_exec: bool):
        """处理文件选择"""
        self.logger.debug(f"选择了文件: {file_path}, 是否目录: {is_dir}")
    
    def _on_file_delete(self, file_path: str, filename: str):
        """处理文件删除"""
        try:
            self.logger.info(f"开始删除文件: {file_path}")
            self._update_status(f"正在删除文件: {filename}")
            threading.Thread(target=self._delete_file_async, args=(file_path, filename), daemon=True).start()
        except Exception as e:
            self.logger.error(f"删除文件失败: {e}")
    
    def _delete_file_async(self, file_path: str, filename: str):
        """异步删除文件"""
        try:
            future = self._run_async(self._delete_file_via_telnet(file_path, filename))
            if future:
                future.add_done_callback(lambda f: self._on_delete_result(f, filename))
            else:
                self.root.after(0, lambda: self._update_status("无法创建删除任务"))
        except Exception as e:
            self.logger.error(f"异步删除文件失败: {e}")
    
    def _on_delete_result(self, future, filename: str):
        """处理删除结果回调"""
        try:
            success = future.result()
            if success:
                self.root.after(0, lambda: self._on_delete_success(filename))
            else:
                self.root.after(0, lambda: self._on_delete_failed(filename))
        except Exception as e:
            self.logger.error(f"删除结果处理失败: {e}")
    
    def _on_delete_success(self, filename: str):
        """删除成功"""
        self.logger.info(f"文件删除成功: {filename}")
        self._update_status(f"文件删除成功: {filename}")
        self._refresh_directory()
    
    def _on_delete_failed(self, filename: str):
        """删除失败"""
        self.logger.error(f"文件删除失败: {filename}")
        self._update_status(f"文件删除失败: {filename}")
        messagebox.showerror("删除失败", f"无法删除文件: {filename}")
    
    async def _delete_file_via_telnet(self, file_path: str, filename: str):
        """通过telnet删除文件"""
        try:
            async with self.telnet_lock:
                delete_cmd = f'rm "{file_path}"'
                self.logger.info(f"执行删除命令: {delete_cmd}")
                result = await self.telnet_client.execute_command(delete_cmd, timeout=10)
                
                # 检查删除是否成功
                check_cmd = f'ls "{file_path}" 2>/dev/null || echo "FILE_NOT_FOUND"'
                check_result = await self.telnet_client.execute_command(check_cmd, timeout=5)
                
                return "FILE_NOT_FOUND" in check_result or "No such file" in check_result
        except Exception as e:
            self.logger.error(f"telnet删除文件失败: {str(e)}")
            return False
    
    def _on_file_edit(self, file_path: str, mode: str = 'edit'):
        """处理文件编辑"""
        if hasattr(self, 'file_editor'):
            # 如果没有指定模式，根据文件类型自动判断
            if mode == 'edit':
                filename_lower = os.path.basename(file_path).lower()
                # 检测图片文件
                if any(filename_lower.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg"]):
                    self.logger.info(f"检测到图片文件，切换到预览模式: {file_path}")
                    mode = 'preview'
            
            if mode == 'preview':
                self.file_editor.open_image_preview(file_path)
            else:
                self.file_editor.open_file_editor(file_path)
    
    def _on_drag_download_request(self, file_path: str, target_dir: str, filename: str):
        """处理拖拽下载请求"""
        try:
            self.logger.info(f"收到拖拽下载请求: {filename} -> {target_dir}")
            
            # 检查连接状态
            if not self.is_connected:
                messagebox.showwarning("未连接", "请先连接到设备")
                return
            
            # 确保拖拽下载管理器有最新的客户端实例
            if hasattr(self, 'telnet_client') and hasattr(self, 'http_server'):
                self.drag_download_manager.set_clients(
                    self.telnet_client, self.http_server, self.loop, self.telnet_lock
                )
            
            # 添加下载任务
            task = self.drag_download_manager.add_download_task(file_path, target_dir)
            
            # 开始下载
            self.drag_download_manager.start_downloads()
            
            # 更新状态
            self._update_status(f"开始下载: {filename}")
            
        except Exception as e:
            self.logger.error(f"处理拖拽下载请求失败: {e}")
            messagebox.showerror("下载失败", f"无法开始下载:\n{str(e)}")
    
    def _on_drag_download_progress(self, task, progress):
        """处理拖拽下载进度"""
        try:
            self._update_status(f"下载中: {task.filename} ({progress:.1f}%)")
        except Exception as e:
            self.logger.error(f"更新下载进度失败: {e}")
    
    def _on_drag_download_complete(self, task, success):
        """处理拖拽下载完成"""
        try:
            if success:
                self.logger.info(f"文件下载完成: {task.filename}")
                self._update_status(f"下载完成: {task.filename}")
                messagebox.showinfo("下载完成", f"文件已成功下载到:\n{task.local_target_path}")
            else:
                self.logger.error(f"文件下载失败: {task.filename}")
                self._update_status(f"下载失败: {task.filename}")
        except Exception as e:
            self.logger.error(f"处理下载完成回调失败: {e}")
    
    def _on_drag_download_error(self, task, error_message):
        """处理拖拽下载错误"""
        try:
            self.logger.error(f"下载出错: {task.filename} - {error_message}")
            self._update_status(f"下载失败: {task.filename}")
            messagebox.showerror("下载失败", f"下载文件时出错:\n{task.filename}\n\n错误信息:\n{error_message}")
        except Exception as e:
            self.logger.error(f"处理下载错误回调失败: {e}")
    
    # 传输相关回调方法
    def _on_files_added(self, count: int):
        """处理文件添加"""
        self._update_status(f"已添加 {count} 个文件到队列 (将传输到当前目录)")
    
    def _clear_transfer_queue(self):
        """清空传输队列"""
        self._update_status("队列已清空")
    
    def _start_transfer(self):
        """开始传输"""
        if not self.is_connected:
            messagebox.showwarning("未连接", "请先连接到设备")
            return
        
        transfer_tasks = self.transfer_panel.get_transfer_tasks()
        if not transfer_tasks:
            messagebox.showinfo("无文件", "队列为空")
            return
        
        # 检查HTTP服务器状态
        if not self.http_server or not self.http_server.is_running:
            self.logger.error("HTTP服务器未运行")
            messagebox.showerror("错误", "HTTP服务器未启动，无法进行文件传输")
            return
        
        self.logger.info(f"开始传输 {len(transfer_tasks)} 个文件")
        self.transfer_panel.update_transfer_button_state(False, '传输中...')
        threading.Thread(target=self._transfer_files_async, args=(transfer_tasks,), daemon=True).start()
    
    def _transfer_files_async(self, transfer_tasks: List[tuple]):
        """异步传输文件"""
        try:
            future = self._run_async(self._execute_transfers_sequentially(transfer_tasks))
            if future:
                future.add_done_callback(lambda f: self._on_transfer_result(f, len(transfer_tasks)))
            else:
                self.root.after(0, lambda: self._on_transfer_error("无法创建异步传输任务"))
        except Exception as e:
            self.logger.error(f"文件传输异常: {str(e)}")
            self.root.after(0, lambda: self._on_transfer_error(str(e)))
    
    def _on_transfer_result(self, future, total_count: int):
        """处理传输结果回调"""
        try:
            success_count = future.result()
            self.root.after(0, lambda: self._on_transfer_complete(success_count, total_count))
        except Exception as e:
            self.logger.error(f"传输结果处理失败: {e}")
            self.root.after(0, lambda: self._on_transfer_error(str(e)))
    
    async def _execute_transfers_sequentially(self, transfer_tasks: List[tuple]):
        """串行执行传输任务"""
        success_count = 0
        
        for i, (local_file, remote_path, filename) in enumerate(transfer_tasks, 1):
            self.logger.info(f"开始传输文件 {i}/{len(transfer_tasks)}: {filename}")
            
            try:
                async with self.telnet_lock:
                    if await self._transfer_single_file_async(local_file, remote_path, filename):
                        success_count += 1
                        self.logger.info(f"文件传输成功: {filename}")
                    else:
                        self.logger.error(f"文件传输失败: {filename}")
            except Exception as e:
                self.logger.error(f"传输文件 {filename} 时出错: {str(e)}")
        
        return success_count
    
    async def _transfer_single_file_async(self, local_file: str, remote_path: str, filename: str):
        """异步传输单个文件"""
        try:
            if not self.http_server:
                self.logger.error("HTTP服务器未启动")
                return False
            
            # 添加到HTTP服务器
            self.logger.info(f"将文件添加到HTTP服务器: {local_file}")
            server_file_path = self.http_server.add_file(local_file, filename)
            if not server_file_path:
                self.logger.error("无法添加文件到HTTP服务器")
                return False
            
            # 获取实际的文件名
            actual_filename = os.path.basename(server_file_path)
            
            # 获取下载URL
            host_ip = self._get_local_ip()
            download_url = self.http_server.get_download_url(actual_filename, host_ip)
            self.logger.info(f"生成下载URL: {download_url}")
            
            # 通过telnet下载
            result = await self._download_via_telnet(download_url, remote_path, actual_filename)
            
            # 延迟清理临时文件，避免Windows文件占用问题
            def delayed_cleanup():
                import time
                time.sleep(2)  # 等待2秒确保文件不再被占用
                try:
                    self.http_server.remove_file(actual_filename)
                except Exception as cleanup_error:
                    self.logger.warning(f"延迟清理临时文件失败: {cleanup_error}")
            
            threading.Thread(target=delayed_cleanup, daemon=True).start()
            
            return result
            
        except Exception as e:
            self.logger.error(f"异步传输文件失败: {str(e)}")
            return False
    
    async def _download_via_telnet(self, download_url: str, remote_path: str, filename: str):
        """通过telnet下载"""
        try:
            self.logger.info(f"切换到远程目录: {remote_path}")
            cd_result = await self.telnet_client.execute_command(f'cd "{remote_path}"')
            
            wget_cmd = f'wget -O "{filename}" "{download_url}"'
            self.logger.info(f"执行wget命令: {wget_cmd}")
            result = await self.telnet_client.execute_command(wget_cmd, timeout=30)
            
            # 检查下载结果
            success_keywords = ['100%', 'saved', 'complete', 'downloaded']
            download_success = False
            
            if any(keyword in result.lower() for keyword in success_keywords):
                download_success = True
            else:
                # 检查文件是否确实存在
                check_cmd = f'ls -la "{filename}"'
                check_result = await self.telnet_client.execute_command(check_cmd)
                download_success = filename in check_result and "-rw" in check_result
            
            # 如果下载成功，检查是否需要添加可执行权限
            if download_success:
                await self._check_and_set_executable_permission(filename, remote_path)
            
            return download_success
                
        except Exception as e:
            self.logger.error(f"telnet下载失败: {str(e)}")
            return False
    
    async def _check_and_set_executable_permission(self, filename: str, remote_path: str):
        """检查并设置二进制文件的可执行权限"""
        try:
            # 检测是否为需要可执行权限的二进制文件
            if self._is_executable_binary_file(filename):
                # 构建完整的远程文件路径
                remote_file_path = f"{remote_path.rstrip('/')}/{filename}"
                
                # 添加可执行权限
                chmod_cmd = f'chmod +x "{remote_file_path}"'
                self.logger.info(f"为二进制文件添加可执行权限: {chmod_cmd}")
                
                await self.telnet_client.execute_command(chmod_cmd, timeout=10)
                
                # 验证权限是否添加成功
                verify_cmd = f'ls -l "{remote_file_path}"'
                verify_result = await self.telnet_client.execute_command(verify_cmd, timeout=5)
                
                self.logger.info(f"权限验证结果: {verify_result.strip()}")
                
                if 'x' in verify_result:
                    self.logger.info(f"✅ 成功为二进制文件添加可执行权限: {filename}")
                else:
                    self.logger.warning(f"⚠️ 可执行权限可能未成功添加: {filename}")
                    
        except Exception as e:
            self.logger.error(f"❌ 添加可执行权限失败: {filename} - {e}")
    
    def _is_executable_binary_file(self, filename: str) -> bool:
        """检测文件是否为需要可执行权限的二进制文件"""
        try:
            # 只有这些扩展名的文件才需要可执行权限
            executable_extensions = {
                '.exe', '.bin', '.so', '.dll', '.dylib', '.a', '.o', '.obj',
                '.deb', '.rpm', '.apk', '.ipa'
            }
            
            file_ext = os.path.splitext(filename)[1].lower()
            if file_ext in executable_extensions:
                return True
            
            # 对于没有扩展名的文件，如果文件名包含常见的可执行文件特征
            if not file_ext:
                # 常见的可执行文件名模式
                executable_patterns = ['bin', 'exec', 'run', 'start', 'launch']
                filename_lower = filename.lower()
                if any(pattern in filename_lower for pattern in executable_patterns):
                    return True
            
            return False
            
        except Exception as e:
            self.logger.warning(f"检测可执行文件类型失败: {e}")
            return False
    
    def _on_transfer_complete(self, success_count: int, total_count: int):
        """传输完成"""
        self.transfer_panel.update_transfer_button_state(True, '▶️ 开始')
        
        if success_count == total_count:
            messagebox.showinfo("传输完成", f"成功传输 {success_count} 个文件")
        else:
            messagebox.showwarning("传输完成", f"成功: {success_count}, 失败: {total_count - success_count}")
        
        self._clear_transfer_queue()
    
    def _on_transfer_error(self, error_msg: str):
        """传输错误"""
        self.transfer_panel.update_transfer_button_state(True, '▶️ 开始')
        messagebox.showerror("传输错误", f"传输时出错:\n{error_msg}")
    
    # 工具方法
    def _update_status(self, message: str):
        """更新状态"""
        try:
            self.status_var.set(message)
            self.root.update_idletasks()
        except Exception:
            pass
    
    def _get_local_ip(self) -> str:
        """获取本机IP"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except Exception:
            return "127.0.0.1"
    
    def _clean_ansi_codes(self, text: str) -> str:
        """清理ANSI转义序列和颜色代码"""
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        cleaned = ansi_escape.sub('', text)
        control_chars = re.compile(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]')
        cleaned = control_chars.sub('', cleaned)
        return cleaned.strip()
    
    def _determine_file_type(self, permissions: str, name: str) -> str:
        """根据权限和文件名判断文件类型"""
        if permissions.startswith('d'):
            return 'directory'
        if permissions.startswith('l'):
            return 'link'
        if 'x' in permissions[1:4]:
            return 'executable'
        
        name_lower = name.lower()
        if any(name_lower.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg']):
            return 'image'
        if any(name_lower.endswith(ext) for ext in ['.txt', '.doc', '.docx', '.pdf', '.md']):
            return 'document'
        if any(name_lower.endswith(ext) for ext in ['.zip', '.tar', '.gz', '.bz2', '.rar', '.7z']):
            return 'archive'
        if any(name_lower.endswith(ext) for ext in ['.conf', '.cfg', '.ini', '.yaml', '.yml', '.json']):
            return 'config'
        if any(name_lower.endswith(ext) for ext in ['.sh', '.py', '.pl', '.rb', '.js']):
            return 'script'
        
        return 'file'
    
    def _join_unix_path(self, base_path: str, name: str) -> str:
        """连接Unix风格路径"""
        base_path = base_path.replace('\\', '/').rstrip('/')
        name = name.replace('\\', '/')
        
        if base_path == '':
            base_path = '/'
        
        if base_path == '/':
            return f'/{name}'
        else:
            return f'{base_path}/{name}'
    
    def _normalize_unix_path(self, path: str) -> str:
        """规范化Unix路径"""
        if not path:
            return '/'
        
        path = path.replace('\\', '/')
        
        if not path.startswith('/'):
            path = '/' + path
        
        while '//' in path:
            path = path.replace('//', '/')
        
        if path != '/' and path.endswith('/'):
            path = path.rstrip('/')
        
        return path
    
    def _on_closing(self):
        """窗口关闭"""
        if messagebox.askokcancel("退出", "确定要退出吗？"):
            self._cleanup()
            self.root.destroy()
    
    def _cleanup(self):
        """清理资源"""
        try:
            # 清理拖拽下载管理器
            if hasattr(self, 'drag_download_manager'):
                self.drag_download_manager.cleanup()
            
            if self.http_server:
                self.http_server.stop()
            if self.telnet_client:
                if self.loop and not self.loop.is_closed():
                    asyncio.run_coroutine_threadsafe(self.telnet_client.disconnect(), self.loop)
            if self.loop and not self.loop.is_closed():
                self.loop.call_soon_threadsafe(self.loop.stop)
        except Exception as e:
            print(f"清理资源时出错: {e}")
    
    def _try_get_device_id(self):
        """尝试获取设备ID"""
        try:
            if not self.is_connected or not self.telnet_client:
                return
                
            self.logger.info("尝试获取设备ID...")
            threading.Thread(target=self._get_device_id_async, daemon=True).start()
            
        except Exception as e:
            self.logger.debug(f"获取设备ID失败: {e}")
    
    def _get_device_id_async(self):
        """异步获取设备ID"""
        try:
            future = self._run_async(self._read_device_id_from_remote())
            if future:
                future.add_done_callback(self._on_device_id_result)
        except Exception as e:
            self.logger.debug(f"异步获取设备ID失败: {e}")
    
    def _on_device_id_result(self, future):
        """处理设备ID获取结果"""
        try:
            device_id = future.result()
            if device_id:
                self.logger.info(f"成功获取设备ID: {device_id}")
                self.root.after(0, lambda: self.connection_panel.update_device_id(device_id))
            else:
                self.logger.debug("未能获取到设备ID")
        except Exception as e:
            self.logger.debug(f"设备ID结果处理失败: {e}")
    
    async def _read_device_id_from_remote(self) -> Optional[str]:
        """从远程设备读取设备ID"""
        try:
            async with self.telnet_lock:
                # 检查文件是否存在
                check_cmd = 'test -f /customer/screenId.ini && echo "EXISTS" || echo "NOT_EXISTS"'
                check_result = await self.telnet_client.execute_command(check_cmd, timeout=5)
                
                if "NOT_EXISTS" in check_result:
                    self.logger.debug("设备ID文件不存在: /customer/screenId.ini")
                    return None
                
                # 读取文件内容
                read_cmd = 'cat /customer/screenId.ini'
                content = await self.telnet_client.execute_command(read_cmd, timeout=5)
                
                if not content:
                    self.logger.debug("设备ID文件为空")
                    return None
                
                # 解析deviceId
                lines = content.strip().split('\n')
                for line in lines:
                    line = line.strip()
                    if line.startswith('deviceId='):
                        device_id = line.split('=', 1)[1].strip()
                        if device_id:
                            return device_id
                
                self.logger.debug("未在文件中找到有效的deviceId")
                return None
                
        except Exception as e:
            self.logger.debug(f"读取设备ID失败: {str(e)}")
            return None

    def run(self):
        """启动GUI主循环"""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.logger.info("用户中断程序运行")
        finally:
            self._cleanup() 