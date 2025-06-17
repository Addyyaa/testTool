# -*- coding: utf-8 -*-

import asyncio
import os
import shutil
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter.scrolledtext import ScrolledText
import tkinterdnd2 as tkdnd
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import json
import logging

# 添加父目录到系统路径，以便导入telnet工具
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from telnetTool.telnetConnect import CustomTelnetClient
from fileTransfer.http_server import FileHTTPServer
from fileTransfer.file_transfer_controller import FileTransferController


class ModernFileTransferGUI:
    """
    现代化文件传输GUI主界面
    
    提供类似ChatGPT桌面版的现代化界面，支持：
    - Telnet设备连接管理
    - 文件拖拽上传
    - 远程目录浏览
    - 传输进度监控
    - 异常处理和日志记录
    """
    
    def __init__(self):
        """初始化GUI界面"""
        # 主题配色 - 参考ChatGPT桌面版
        self.colors = {
            'bg_primary': '#ffffff',        # 主背景色
            'bg_secondary': '#f7f7f8',      # 次要背景色
            'bg_sidebar': '#f7f7f8',        # 侧边栏背景
            'bg_button': '#10a37f',         # 按钮背景
            'bg_button_hover': '#0d8a6b',   # 按钮悬停
            'text_primary': '#2d333a',      # 主文本色
            'text_secondary': '#6e7681',    # 次要文本色
            'text_button': '#ffffff',       # 按钮文本色
            'border': '#e5e7eb',            # 边框色
            'accent': '#10a37f',            # 强调色
            'error': '#ef4444',             # 错误色
            'success': '#10b981',           # 成功色
            'warning': '#f59e0b'            # 警告色
        }
        
        # 创建主窗口
        self.root = tkdnd.Tk()
        self.root.title("现代化文件传输工具")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 600)
        self.root.configure(bg=self.colors['bg_primary'])
        
        # 设置图标
        try:
            icon_path = os.path.join(os.path.dirname(__file__), '..', 'resource', 'logo', 'log.ico')
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception:
            pass  # 图标加载失败不影响主要功能
        
        # 配置样式
        self._setup_styles()
        
        # 初始化组件
        self.telnet_client: Optional[CustomTelnetClient] = None
        self.http_server: Optional[FileHTTPServer] = None
        self.transfer_controller: Optional[FileTransferController] = None
        self.current_remote_path = "/"
        self.connection_config = {}
        self.is_connected = False
        
        # 创建界面元素
        self._create_widgets()
        
        # 绑定事件
        self._bind_events()
        
        # 配置日志
        self._setup_logging()
        
        # 设置异步事件循环
        self.loop = None
        self.loop_thread = None
        self._start_event_loop()
        
        self.logger.info("GUI界面初始化完成")
    
    def _setup_styles(self):
        """设置现代化样式"""
        self.style = ttk.Style()
        
        # 配置通用样式
        self.style.configure('Modern.TFrame', 
                           background=self.colors['bg_primary'],
                           relief='flat')
        
        self.style.configure('Sidebar.TFrame',
                           background=self.colors['bg_sidebar'],
                           relief='flat')
        
        self.style.configure('Modern.TLabel',
                           background=self.colors['bg_primary'],
                           foreground=self.colors['text_primary'],
                           font=('Microsoft YaHei UI', 10))
        
        self.style.configure('Title.TLabel',
                           background=self.colors['bg_primary'],
                           foreground=self.colors['text_primary'],
                           font=('Microsoft YaHei UI', 14, 'bold'))
        
        self.style.configure('Modern.TButton',
                           background=self.colors['bg_button'],
                           foreground=self.colors['text_button'],
                           borderwidth=0,
                           focuscolor='none',
                           font=('Microsoft YaHei UI', 10))
        
        self.style.map('Modern.TButton',
                      background=[('active', self.colors['bg_button_hover'])])
        
        self.style.configure('Modern.TEntry',
                           fieldbackground=self.colors['bg_primary'],
                           borderwidth=1,
                           insertcolor=self.colors['text_primary'],
                           font=('Microsoft YaHei UI', 10))
        
        self.style.configure('Modern.Treeview',
                           background=self.colors['bg_primary'],
                           foreground=self.colors['text_primary'],
                           borderwidth=1,
                           font=('Microsoft YaHei UI', 9))
        
        self.style.configure('Modern.Treeview.Heading',
                           background=self.colors['bg_secondary'],
                           foreground=self.colors['text_primary'],
                           font=('Microsoft YaHei UI', 10, 'bold'))
    
    def _create_widgets(self):
        """创建界面组件"""
        # 主容器
        self.main_frame = ttk.Frame(self.root, style='Modern.TFrame')
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        
        # 创建侧边栏
        self._create_sidebar()
        
        # 创建主内容区域
        self._create_main_content()
        
        # 创建状态栏
        self._create_status_bar()
    
    def _create_sidebar(self):
        """创建侧边栏"""
        # 侧边栏容器
        self.sidebar_frame = ttk.Frame(self.main_frame, style='Sidebar.TFrame', width=300)
        self.sidebar_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 1))
        self.sidebar_frame.pack_propagate(False)
        
        # 连接配置区域
        self._create_connection_panel()
        
        # 远程目录浏览区域
        self._create_directory_panel()
        
        # 传输队列区域
        self._create_transfer_queue_panel()
    
    def _create_connection_panel(self):
        """创建连接配置面板"""
        # 连接配置标题
        connection_title = ttk.Label(self.sidebar_frame, text="设备连接", style='Title.TLabel')
        connection_title.pack(pady=(20, 10), padx=20, anchor='w')
        
        # 连接配置框架
        self.connection_frame = ttk.Frame(self.sidebar_frame, style='Sidebar.TFrame')
        self.connection_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        # 主机地址
        ttk.Label(self.connection_frame, text="主机地址:", style='Modern.TLabel').pack(anchor='w')
        self.host_entry = ttk.Entry(self.connection_frame, style='Modern.TEntry')
        self.host_entry.pack(fill=tk.X, pady=(2, 10))
        self.host_entry.insert(0, "192.168.1.100")
        
        # 端口
        ttk.Label(self.connection_frame, text="端口:", style='Modern.TLabel').pack(anchor='w')
        self.port_entry = ttk.Entry(self.connection_frame, style='Modern.TEntry')
        self.port_entry.pack(fill=tk.X, pady=(2, 10))
        self.port_entry.insert(0, "23")
        
        # 用户名
        ttk.Label(self.connection_frame, text="用户名:", style='Modern.TLabel').pack(anchor='w')
        self.username_entry = ttk.Entry(self.connection_frame, style='Modern.TEntry')
        self.username_entry.pack(fill=tk.X, pady=(2, 10))
        
        # 密码
        ttk.Label(self.connection_frame, text="密码:", style='Modern.TLabel').pack(anchor='w')
        self.password_entry = ttk.Entry(self.connection_frame, style='Modern.TEntry', show='*')
        self.password_entry.pack(fill=tk.X, pady=(2, 10))
        
        # 连接按钮
        self.connect_button = ttk.Button(self.connection_frame, text="连接设备", 
                                       style='Modern.TButton', command=self._on_connect_clicked)
        self.connect_button.pack(fill=tk.X, pady=(10, 0))
        
        # 连接状态指示器
        self.connection_status_frame = ttk.Frame(self.connection_frame, style='Sidebar.TFrame')
        self.connection_status_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.status_indicator = tk.Canvas(self.connection_status_frame, width=12, height=12, 
                                        bg=self.colors['bg_sidebar'], highlightthickness=0)
        self.status_indicator.pack(side=tk.LEFT)
        self.status_indicator.create_oval(2, 2, 10, 10, fill=self.colors['error'], outline='')
        
        self.connection_status_label = ttk.Label(self.connection_status_frame, text="未连接", 
                                               style='Modern.TLabel')
        self.connection_status_label.pack(side=tk.LEFT, padx=(8, 0))
    
    def _create_directory_panel(self):
        """创建远程目录浏览面板"""
        # 目录浏览标题
        directory_title = ttk.Label(self.sidebar_frame, text="远程目录", style='Title.TLabel')
        directory_title.pack(pady=(20, 10), padx=20, anchor='w')
        
        # 当前路径显示
        self.current_path_frame = ttk.Frame(self.sidebar_frame, style='Sidebar.TFrame')
        self.current_path_frame.pack(fill=tk.X, padx=20, pady=(0, 10))
        
        self.current_path_label = ttk.Label(self.current_path_frame, text="当前路径:", style='Modern.TLabel')
        self.current_path_label.pack(anchor='w')
        
        self.current_path_var = tk.StringVar(value="/")
        self.current_path_entry = ttk.Entry(self.current_path_frame, textvariable=self.current_path_var,
                                          style='Modern.TEntry', state='readonly')
        self.current_path_entry.pack(fill=tk.X, pady=(2, 0))
        
        # 目录树视图
        self.directory_tree_frame = ttk.Frame(self.sidebar_frame, style='Sidebar.TFrame')
        self.directory_tree_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        # 创建Treeview和滚动条
        tree_container = ttk.Frame(self.directory_tree_frame, style='Sidebar.TFrame')
        tree_container.pack(fill=tk.BOTH, expand=True)
        
        self.directory_tree = ttk.Treeview(tree_container, style='Modern.Treeview', 
                                         columns=(), show='tree')
        self.directory_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        tree_scrollbar = ttk.Scrollbar(tree_container, orient='vertical', command=self.directory_tree.yview)
        tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.directory_tree.configure(yscrollcommand=tree_scrollbar.set)
        
        # 工具按钮
        self.directory_buttons_frame = ttk.Frame(self.directory_tree_frame, style='Sidebar.TFrame')
        self.directory_buttons_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.refresh_button = ttk.Button(self.directory_buttons_frame, text="刷新", 
                                       style='Modern.TButton', command=self._refresh_directory)
        self.refresh_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.parent_button = ttk.Button(self.directory_buttons_frame, text="上级", 
                                      style='Modern.TButton', command=self._go_parent_directory)
        self.parent_button.pack(side=tk.LEFT)
    
    def _create_transfer_queue_panel(self):
        """创建传输队列面板"""
        # 传输队列标题
        queue_title = ttk.Label(self.sidebar_frame, text="传输队列", style='Title.TLabel')
        queue_title.pack(pady=(20, 10), padx=20, anchor='w')
        
        # 传输队列列表
        self.queue_frame = ttk.Frame(self.sidebar_frame, style='Sidebar.TFrame')
        self.queue_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        # 队列列表
        self.queue_listbox = tk.Listbox(self.queue_frame, font=('Microsoft YaHei UI', 9),
                                      bg=self.colors['bg_primary'], 
                                      fg=self.colors['text_primary'],
                                      selectbackground=self.colors['accent'],
                                      borderwidth=1, relief='solid')
        self.queue_listbox.pack(fill=tk.BOTH, expand=True)
        
        # 队列控制按钮
        self.queue_buttons_frame = ttk.Frame(self.queue_frame, style='Sidebar.TFrame')
        self.queue_buttons_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.clear_queue_button = ttk.Button(self.queue_buttons_frame, text="清空队列", 
                                           style='Modern.TButton', command=self._clear_transfer_queue)
        self.clear_queue_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.start_transfer_button = ttk.Button(self.queue_buttons_frame, text="开始传输", 
                                              style='Modern.TButton', command=self._start_transfer)
        self.start_transfer_button.pack(side=tk.LEFT)
    
    def _create_main_content(self):
        """创建主内容区域"""
        # 主内容容器
        self.content_frame = ttk.Frame(self.main_frame, style='Modern.TFrame')
        self.content_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # 创建拖拽上传区域
        self._create_drop_zone()
        
        # 创建日志区域
        self._create_log_area()
    
    def _create_drop_zone(self):
        """创建文件拖拽上传区域"""
        # 拖拽区域标题
        drop_title = ttk.Label(self.content_frame, text="文件传输区域", style='Title.TLabel')
        drop_title.pack(pady=(20, 10), padx=20, anchor='w')
        
        # 拖拽区域容器
        self.drop_zone_container = ttk.Frame(self.content_frame, style='Modern.TFrame')
        self.drop_zone_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 10))
        
        # 拖拽区域
        self.drop_zone = tk.Frame(self.drop_zone_container, 
                                bg=self.colors['bg_secondary'],
                                relief='solid', borderwidth=2,
                                bd=2)
        self.drop_zone.pack(fill=tk.BOTH, expand=True)
        
        # 拖拽提示标签
        self.drop_label = tk.Label(self.drop_zone,
                                 text="将文件拖拽到此处进行上传\n\n支持多文件同时上传\n点击此处选择文件",
                                 font=('Microsoft YaHei UI', 14),
                                 fg=self.colors['text_secondary'],
                                 bg=self.colors['bg_secondary'],
                                 justify='center')
        self.drop_label.pack(expand=True)
        
        # 配置拖拽功能
        self.drop_zone.drop_target_register(tkdnd.DND_FILES)
        self.drop_zone.dnd_bind('<<Drop>>', self._on_drop)
        self.drop_zone.dnd_bind('<<DragEnter>>', self._on_drag_enter)
        self.drop_zone.dnd_bind('<<DragLeave>>', self._on_drag_leave)
        
        # 点击选择文件
        self.drop_label.bind('<Button-1>', self._on_select_files)
        self.drop_zone.bind('<Button-1>', self._on_select_files)
    
    def _create_log_area(self):
        """创建日志显示区域"""
        # 日志区域标题
        log_title = ttk.Label(self.content_frame, text="操作日志", style='Title.TLabel')
        log_title.pack(pady=(10, 10), padx=20, anchor='w')
        
        # 日志文本区域
        self.log_frame = ttk.Frame(self.content_frame, style='Modern.TFrame')
        self.log_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        self.log_text = ScrolledText(self.log_frame,
                                   font=('Consolas', 9),
                                   bg=self.colors['bg_primary'],
                                   fg=self.colors['text_primary'],
                                   insertbackground=self.colors['text_primary'],
                                   selectbackground=self.colors['accent'],
                                   wrap=tk.WORD,
                                   height=8)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 日志控制按钮
        self.log_buttons_frame = ttk.Frame(self.log_frame, style='Modern.TFrame')
        self.log_buttons_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.clear_log_button = ttk.Button(self.log_buttons_frame, text="清空日志", 
                                         style='Modern.TButton', command=self._clear_log)
        self.clear_log_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.save_log_button = ttk.Button(self.log_buttons_frame, text="保存日志", 
                                        style='Modern.TButton', command=self._save_log)
        self.save_log_button.pack(side=tk.LEFT)
    
    def _create_status_bar(self):
        """创建状态栏"""
        self.status_bar = ttk.Frame(self.main_frame, style='Modern.TFrame', relief='sunken', borderwidth=1)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 状态信息
        self.status_var = tk.StringVar(value="就绪")
        self.status_label = ttk.Label(self.status_bar, textvariable=self.status_var, style='Modern.TLabel')
        self.status_label.pack(side=tk.LEFT, padx=10)
        
        # HTTP服务器状态
        self.http_status_var = tk.StringVar(value="HTTP服务: 未启动")
        self.http_status_label = ttk.Label(self.status_bar, textvariable=self.http_status_var, style='Modern.TLabel')
        self.http_status_label.pack(side=tk.RIGHT, padx=10)
    
    def _bind_events(self):
        """绑定界面事件"""
        # 目录树选择事件
        self.directory_tree.bind('<<TreeviewSelect>>', self._on_directory_select)
        self.directory_tree.bind('<Double-1>', self._on_directory_double_click)
        
        # 连接参数输入事件
        self.host_entry.bind('<Return>', lambda e: self._on_connect_clicked())
        self.port_entry.bind('<Return>', lambda e: self._on_connect_clicked())
        self.username_entry.bind('<Return>', lambda e: self._on_connect_clicked())
        self.password_entry.bind('<Return>', lambda e: self._on_connect_clicked())
        
        # 窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _setup_logging(self):
        """配置日志系统"""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.INFO)
        
        # 创建自定义日志处理器，将日志输出到GUI
        class GUILogHandler(logging.Handler):
            def __init__(self, gui_instance):
                super().__init__()
                self.gui = gui_instance
                
            def emit(self, record):
                try:
                    msg = self.format(record)
                    self.gui._append_log(msg)
                except Exception:
                    pass
        
        if not self.logger.handlers:
            gui_handler = GUILogHandler(self)
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            gui_handler.setFormatter(formatter)
            self.logger.addHandler(gui_handler)
    
    def _start_event_loop(self):
        """启动异步事件循环"""
        def run_loop():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_forever()
        
        self.loop_thread = threading.Thread(target=run_loop, daemon=True)
        self.loop_thread.start()
        
        # 等待事件循环启动
        while self.loop is None:
            time.sleep(0.01)
    
    def _run_async(self, coro):
        """在事件循环中运行异步任务"""
        if self.loop and not self.loop.is_closed():
            future = asyncio.run_coroutine_threadsafe(coro, self.loop)
            return future
        return None
    
    # 事件处理方法将在下一部分继续...
    
    def run(self):
        """启动GUI主循环"""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.logger.info("用户中断程序运行")
        finally:
            self._cleanup()
    
    def _cleanup(self):
        """清理资源"""
        try:
            if self.http_server:
                self.http_server.stop()
            if self.telnet_client:
                if self.loop and not self.loop.is_closed():
                    asyncio.run_coroutine_threadsafe(self.telnet_client.disconnect(), self.loop)
            if self.loop and not self.loop.is_closed():
                self.loop.call_soon_threadsafe(self.loop.stop)
        except Exception as e:
            print(f"清理资源时出错: {e}")