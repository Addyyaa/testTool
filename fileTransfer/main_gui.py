#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
现代化文件传输工具主程序

集成GUI界面、HTTP服务器、Telnet客户端和文件传输控制器
"""

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
import socket
import re

# 添加父目录到系统路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from telnetTool.telnetConnect import CustomTelnetClient
from fileTransfer.http_server import FileHTTPServer
from fileTransfer.file_transfer_controller import FileTransferController, TransferTask


class ModernFileTransferGUI:
    """现代化文件传输GUI主界面"""
    
    def __init__(self):
        """初始化GUI界面"""
        # 主题配色 - 优化按钮对比度
        self.colors = {
            'bg_primary': '#ffffff',
            'bg_secondary': '#f7f7f8',
            'bg_sidebar': '#f7f7f8',
            'bg_button': '#0f7b6c',         # 更深的绿色，增强对比度
            'bg_button_hover': '#0a5d52',   # 更深的悬停色
            'text_primary': '#2d333a',
            'text_secondary': '#6e7681',
            'text_button': '#ffffff',
            'border': '#e5e7eb',
            'accent': '#10a37f',
            'error': '#ef4444',
            'success': '#10b981',
            'warning': '#f59e0b'
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
            pass
        
        # 配置样式
        self._setup_styles()
        
        # 初始化组件
        self.telnet_client: Optional[CustomTelnetClient] = None
        self.http_server: Optional[FileHTTPServer] = None
        self.transfer_controller: Optional[FileTransferController] = None
        self.current_remote_path = "/"
        self.connection_config = {}
        self.is_connected = False
        self.file_path_mapping = {}  # 文件名到完整路径的映射
        
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
                           foreground='#ffffff',  # 明确设置为白色
                           borderwidth=2,
                           relief='raised',
                           focuscolor='none',
                           font=('Microsoft YaHei UI', 10, 'bold'),
                           padding=(8, 6))
        
        self.style.map('Modern.TButton',
                      background=[('active', self.colors['bg_button_hover']),
                                ('pressed', self.colors['bg_button_hover'])],
                      foreground=[('active', '#ffffff'),
                                ('pressed', '#ffffff')],
                      relief=[('pressed', 'sunken'),
                            ('active', 'raised')],
                      borderwidth=[('active', 2), ('pressed', 2)])
        
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
        self.username_entry.insert(0, "root")
        self.username_entry.pack(fill=tk.X, pady=(2, 10))
        
        # 密码
        ttk.Label(self.connection_frame, text="密码:", style='Modern.TLabel').pack(anchor='w')
        self.password_entry = ttk.Entry(self.connection_frame, style='Modern.TEntry', show='*')
        self.password_entry.insert(0, "ya!2dkwy7-934^")
        self.password_entry.pack(fill=tk.X, pady=(2, 10))
        
        # 连接按钮
        self.connect_button = tk.Button(self.connection_frame, text="连接设备", 
                                      command=self._on_connect_clicked,
                                      bg='#0f7b6c', fg='#ffffff',
                                      font=('Microsoft YaHei UI', 10, 'bold'),
                                      relief='raised', borderwidth=2,
                                      activebackground='#0a5d52', activeforeground='#ffffff',
                                      cursor='hand2', pady=8)
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
        self.directory_tree_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        # 创建Treeview和滚动条
        tree_container = ttk.Frame(self.directory_tree_frame, style='Sidebar.TFrame')
        tree_container.pack(fill=tk.BOTH, expand=True)
        
        self.directory_tree = ttk.Treeview(tree_container, style='Modern.Treeview', 
                                         columns=(), show='tree', height=8)
        self.directory_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        tree_scrollbar = ttk.Scrollbar(tree_container, orient='vertical', command=self.directory_tree.yview)
        tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.directory_tree.configure(yscrollcommand=tree_scrollbar.set)
        
        # 工具按钮
        self.directory_buttons_frame = ttk.Frame(self.directory_tree_frame, style='Sidebar.TFrame')
        self.directory_buttons_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.refresh_button = tk.Button(self.directory_buttons_frame, text="刷新", 
                                       command=self._refresh_directory,
                                       bg='#0f7b6c', fg='#ffffff',
                                       font=('Microsoft YaHei UI', 9, 'bold'),
                                       relief='raised', borderwidth=2,
                                       activebackground='#0a5d52', activeforeground='#ffffff',
                                       cursor='hand2', pady=6)
        self.refresh_button.pack(side=tk.LEFT, padx=(0, 8), fill=tk.X, expand=True)
        
        self.parent_button = tk.Button(self.directory_buttons_frame, text="上级", 
                                     command=self._go_parent_directory,
                                     bg='#0f7b6c', fg='#ffffff',
                                     font=('Microsoft YaHei UI', 9, 'bold'),
                                     relief='raised', borderwidth=2,
                                     activebackground='#0a5d52', activeforeground='#ffffff',
                                     cursor='hand2', pady=6)
        self.parent_button.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 添加传输按钮
        self.quick_transfer_button = tk.Button(self.directory_buttons_frame, text="传输", 
                                             command=self._quick_start_transfer,
                                             bg='#dc2626', fg='#ffffff',
                                             font=('Microsoft YaHei UI', 9, 'bold'),
                                             relief='raised', borderwidth=2,
                                             activebackground='#b91c1c', activeforeground='#ffffff',
                                             cursor='hand2', pady=6)
        self.quick_transfer_button.pack(side=tk.LEFT, padx=(8, 0), fill=tk.X, expand=True)
        
        # 为传输按钮添加右键菜单（测试功能）
        self.transfer_context_menu = tk.Menu(self.root, tearoff=0)
        self.transfer_context_menu.add_command(label="🔧 测试传输设置", command=self._test_transfer_setup)
        self.transfer_context_menu.add_separator()
        self.transfer_context_menu.add_command(label="📊 显示传输状态", command=self._show_transfer_status)
        
        def show_transfer_menu(event):
            try:
                self.transfer_context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                self.transfer_context_menu.grab_release()
        
        self.quick_transfer_button.bind("<Button-3>", show_transfer_menu)  # 右键
    
    def _create_transfer_queue_panel(self):
        """创建传输队列面板"""
        # 传输队列标题
        queue_title_frame = ttk.Frame(self.sidebar_frame, style='Sidebar.TFrame')
        queue_title_frame.pack(fill=tk.X, padx=20, pady=(20, 10))
        
        queue_title = ttk.Label(queue_title_frame, text="传输队列", style='Title.TLabel')
        queue_title.pack(side=tk.LEFT)
        
        self.queue_count_label = ttk.Label(queue_title_frame, text="(0个文件)", 
                                         style='Modern.TLabel', foreground='#6b7280')
        self.queue_count_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # 传输队列列表
        self.queue_frame = ttk.Frame(self.sidebar_frame, style='Sidebar.TFrame')
        self.queue_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        # 队列列表
        self.queue_listbox = tk.Listbox(self.queue_frame, font=('Microsoft YaHei UI', 9),
                                      bg=self.colors['bg_primary'], 
                                      fg=self.colors['text_primary'],
                                      selectbackground=self.colors['accent'],
                                      borderwidth=1, relief='solid',
                                      height=6)
        self.queue_listbox.pack(fill=tk.X, pady=(0, 10))
        
        # 队列控制按钮
        self.queue_buttons_frame = ttk.Frame(self.queue_frame, style='Sidebar.TFrame')
        self.queue_buttons_frame.pack(fill=tk.X)
        
        self.clear_queue_button = tk.Button(self.queue_buttons_frame, text="清空队列", 
                                           command=self._clear_transfer_queue,
                                           bg='#6b7280', fg='#ffffff',
                                           font=('Microsoft YaHei UI', 9, 'bold'),
                                           relief='raised', borderwidth=2,
                                           activebackground='#4b5563', activeforeground='#ffffff',
                                           cursor='hand2', pady=8)
        self.clear_queue_button.pack(side=tk.LEFT, padx=(0, 8), fill=tk.X, expand=True)
        
        # 开始传输按钮 - 使用更醒目的颜色
        self.start_transfer_button = tk.Button(self.queue_buttons_frame, text="🚀 开始传输", 
                                             command=self._start_transfer,
                                             bg='#dc2626', fg='#ffffff',
                                             font=('Microsoft YaHei UI', 10, 'bold'),
                                             relief='raised', borderwidth=3,
                                             activebackground='#b91c1c', activeforeground='#ffffff',
                                             cursor='hand2', pady=8)
        self.start_transfer_button.pack(side=tk.LEFT, fill=tk.X, expand=True)
    
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
        
        # 为标签也添加拖拽支持
        self.drop_label.drop_target_register(tkdnd.DND_FILES)
        self.drop_label.dnd_bind('<<Drop>>', self._on_drop)
        self.drop_label.dnd_bind('<<DragEnter>>', self._on_drag_enter)
        self.drop_label.dnd_bind('<<DragLeave>>', self._on_drag_leave)
        
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
        
        self.clear_log_button = tk.Button(self.log_buttons_frame, text="清空日志", 
                                         command=self._clear_log,
                                         bg='#0f7b6c', fg='#ffffff',
                                         font=('Microsoft YaHei UI', 9, 'bold'),
                                         relief='raised', borderwidth=2,
                                         activebackground='#0a5d52', activeforeground='#ffffff',
                                         cursor='hand2', pady=6)
        self.clear_log_button.pack(side=tk.LEFT, padx=(0, 10), fill=tk.X, expand=True)
        
        self.save_log_button = tk.Button(self.log_buttons_frame, text="保存日志", 
                                        command=self._save_log,
                                        bg='#0f7b6c', fg='#ffffff',
                                        font=('Microsoft YaHei UI', 9, 'bold'),
                                        relief='raised', borderwidth=2,
                                        activebackground='#0a5d52', activeforeground='#ffffff',
                                        cursor='hand2', pady=6)
        self.save_log_button.pack(side=tk.LEFT, fill=tk.X, expand=True)
    
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
        self.logger.setLevel(logging.DEBUG)  # 设置为DEBUG级别以查看详细信息
        
        # 创建自定义日志处理器
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
    
    # 其他事件处理方法将在下一部分继续...
    
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
    
    # 简化的事件处理方法
    def _on_connect_clicked(self):
        """处理连接按钮点击"""
        if self.is_connected:
            self._disconnect_device()
        else:
            self._connect_device()
    
    def _connect_device(self):
        """连接设备"""
        try:
            host = self.host_entry.get().strip()
            port = int(self.port_entry.get().strip() or "23")
            username = self.username_entry.get().strip()
            password = self.password_entry.get()
            
            if not all([host, username, password]):
                messagebox.showerror("输入错误", "请填写完整的连接信息")
                return
            
            self.connection_config = {
                'host': host, 'port': port,
                'username': username, 'password': password
            }
            
            self.connect_button.configure(state='disabled', text='连接中...')
            threading.Thread(target=self._connect_async, daemon=True).start()
            
        except ValueError:
            messagebox.showerror("输入错误", "端口号必须是数字")
        except Exception as e:
            messagebox.showerror("连接错误", f"连接失败: {str(e)}")
    
    def _connect_async(self):
        """异步连接"""
        try:
            from telnetTool.telnetConnect import CustomTelnetClient
            self.telnet_client = CustomTelnetClient(
                host=self.connection_config['host'],
                port=self.connection_config['port'],
                timeout=30.0
            )
            
            future = self._run_async(self._do_connect())
            if future:
                result = future.result(timeout=15)
                if result:
                    self.root.after(0, self._on_connect_success)
                else:
                    self.root.after(0, self._on_connect_failed, "连接失败")
            else:
                self.root.after(0, self._on_connect_failed, "无法启动异步任务")
        except Exception as e:
            self.root.after(0, self._on_connect_failed, str(e))
    
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
        self.is_connected = True
        self.connect_button.configure(state='normal', text='断开连接')
        
        # 更新状态指示器
        self.status_indicator.delete('all')
        self.status_indicator.create_oval(2, 2, 10, 10, fill=self.colors['success'], outline='')
        self.connection_status_label.configure(text=f"已连接 ({self.connection_config['host']})")
        
        self._update_status(f"成功连接到 {self.connection_config['host']}")
        
        # 启动HTTP服务器
        self._start_http_server()
        
        # 刷新目录
        self._refresh_directory()
    
    def _on_connect_failed(self, error_msg):
        """连接失败"""
        self.connect_button.configure(state='normal', text='连接设备')
        self._update_status(f"连接失败: {error_msg}")
        messagebox.showerror("连接失败", f"无法连接到设备:\n{error_msg}")
    
    def _disconnect_device(self):
        """断开连接"""
        try:
            self.is_connected = False
            self.connect_button.configure(state='disabled', text='断开中...')
            
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
            
            # 更新UI
            self.connect_button.configure(state='normal', text='连接设备')
            self.status_indicator.delete('all')
            self.status_indicator.create_oval(2, 2, 10, 10, fill=self.colors['error'], outline='')
            self.connection_status_label.configure(text="未连接")
            self.directory_tree.delete(*self.directory_tree.get_children())
            self.current_path_var.set("/")
            self.http_status_var.set("HTTP服务: 未启动")
            
            self._update_status("已断开连接")
            
        except Exception as e:
            self.logger.error(f"断开连接失败: {str(e)}")
            self.connect_button.configure(state='normal', text='连接设备')
    
    def _start_http_server(self):
        """启动HTTP服务器"""
        try:
            if not self.http_server:
                self.http_server = FileHTTPServer(port=88)
                self.http_server.start()
                
                # 获取本机IP地址
                local_ip = self._get_local_ip()
                temp_dir = self.http_server.temp_dir
                
                self.http_status_var.set(f"HTTP服务: 运行中 (端口88)")
                self.logger.info(f"HTTP服务器已启动")
                self.logger.info(f"本机IP地址: {local_ip}")
                self.logger.info(f"HTTP服务器临时目录: {temp_dir}")
                self.logger.info(f"访问地址: http://{local_ip}:88/")
                
                # 在状态栏显示服务器信息
                self._update_status(f"HTTP服务器已启动 - IP: {local_ip}:88")
                
        except Exception as e:
            self.logger.error(f"启动HTTP服务器失败: {str(e)}")
            import traceback
            self.logger.error(f"详细错误: {traceback.format_exc()}")
            messagebox.showerror("服务器错误", f"无法启动HTTP服务器:\n{str(e)}")
    
    def _refresh_directory(self):
        """刷新目录"""
        if not self.is_connected:
            return
        threading.Thread(target=self._refresh_directory_async, daemon=True).start()
    
    def _refresh_directory_async(self):
        """异步刷新目录"""
        try:
            self.logger.debug(f"开始异步刷新目录: {self.current_remote_path}")
            future = self._run_async(self._get_directory_listing(self.current_remote_path))
            if future:
                items = future.result(timeout=10)
                self.logger.debug(f"异步操作完成，获得 {len(items)} 个项目")
                # 使用after确保在主线程中更新GUI
                self.root.after(0, lambda: self._update_directory_tree(items))
            else:
                self.logger.error("无法创建异步任务")
        except Exception as e:
            self.logger.error(f"刷新目录失败: {str(e)}")
            import traceback
            self.logger.error(f"完整错误信息: {traceback.format_exc()}")
    
    def _clean_ansi_codes(self, text):
        """清理ANSI转义序列和颜色代码"""
        # 移除ANSI转义序列
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        cleaned = ansi_escape.sub('', text)
        
        # 移除其他控制字符，但保留换行符(\n, \r)和制表符(\t)
        control_chars = re.compile(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]')
        cleaned = control_chars.sub('', cleaned)
        
        return cleaned.strip()
    
    async def _get_directory_listing(self, path):
        """获取目录列表"""
        try:
            # 首先尝试使用不带颜色的ls命令
            result = await self.telnet_client.execute_command(f'ls -la --color=never "{path}"')
            
            # 记录原始输出用于调试
            self.logger.debug(f"原始ls输出（前100字符）: {repr(result[:100])}")
            
            # 清理ANSI转义序列
            cleaned_result = self._clean_ansi_codes(result)
            self.logger.debug(f"清理后输出（前100字符）: {repr(cleaned_result[:100])}")
            
            items = []
            lines = cleaned_result.strip().split('\n')
            
            # 跳过第一行（通常是"total xxx"）
            for i, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue
                
                # 跳过总计行
                if i == 0 and line.startswith('total'):
                    continue
                
                # 解析ls -la的输出格式
                parts = line.split()
                if len(parts) >= 9:
                    permissions = parts[0]
                    name = ' '.join(parts[8:])
                    
                    # 跳过当前目录和父目录的引用
                    if name in ['.', '..']:
                        continue
                    
                    # 清理文件名中可能存在的控制字符
                    name = self._clean_ansi_codes(name)
                    
                    if name:  # 确保文件名不为空
                        is_directory = permissions.startswith('d')
                        items.append({
                            'name': name,
                            'is_directory': is_directory,
                            'full_path': os.path.join(path, name)
                        })
                        self.logger.debug(f"解析到项目: {name} ({'目录' if is_directory else '文件'})")
            
            self.logger.info(f"成功解析到 {len(items)} 个项目")
            return items
            
        except Exception as e:
            self.logger.warning(f"--color=never不支持: {str(e)}")
            # 如果--color=never不支持，尝试普通ls命令
            try:
                result = await self.telnet_client.execute_command(f'ls -la "{path}"')
                self.logger.debug(f"普通ls原始输出（前100字符）: {repr(result[:100])}")
                
                cleaned_result = self._clean_ansi_codes(result)
                self.logger.debug(f"普通ls清理后输出（前100字符）: {repr(cleaned_result[:100])}")
                
                items = []
                lines = cleaned_result.strip().split('\n')
                
                for i, line in enumerate(lines):
                    line = line.strip()
                    if not line:
                        continue
                    
                    # 跳过总计行
                    if i == 0 and line.startswith('total'):
                        continue
                    
                    parts = line.split()
                    if len(parts) >= 9:
                        permissions = parts[0]
                        name = ' '.join(parts[8:])
                        
                        if name in ['.', '..']:
                            continue
                        
                        name = self._clean_ansi_codes(name)
                        
                        if name:
                            is_directory = permissions.startswith('d')
                            items.append({
                                'name': name,
                                'is_directory': is_directory,
                                'full_path': os.path.join(path, name)
                            })
                            self.logger.debug(f"解析到项目: {name} ({'目录' if is_directory else '文件'})")
                
                self.logger.info(f"备用方法成功解析到 {len(items)} 个项目")
                return items
                
            except Exception as e2:
                self.logger.error(f"所有方法都失败: {str(e2)}")
                return []
    
    def _update_directory_tree(self, items):
        """更新目录树"""
        try:
            self.logger.debug(f"开始更新目录树，收到 {len(items)} 个项目")
            
            # 清空现有项目
            self.directory_tree.delete(*self.directory_tree.get_children())
            
            # 添加新项目
            for i, item in enumerate(items):
                try:
                    # 简化显示，先不使用emoji图标
                    prefix = "[DIR]" if item['is_directory'] else "[FILE]"
                    display_name = f"{prefix} {item['name']}"
                    
                    # 插入到树中
                    tree_item = self.directory_tree.insert('', 'end', text=display_name, 
                                                         values=(item['full_path'], item['is_directory']))
                    
                    self.logger.debug(f"成功添加项目 {i+1}: {display_name} -> {tree_item}")
                except Exception as item_error:
                    self.logger.error(f"添加项目失败 {item}: {str(item_error)}")
                    # 尝试简化版本
                    try:
                        simple_name = item['name']
                        tree_item = self.directory_tree.insert('', 'end', text=simple_name, 
                                                             values=(item['full_path'], item['is_directory']))
                        self.logger.debug(f"简化版本成功添加: {simple_name}")
                    except Exception as simple_error:
                        self.logger.error(f"简化版本也失败: {str(simple_error)}")
            
            # 检查最终结果
            children_count = len(self.directory_tree.get_children())
            self.logger.info(f"目录树更新完成，显示 {children_count} 个项目")
            
            if children_count == 0 and len(items) > 0:
                self.logger.warning("警告：有项目但目录树为空，可能存在显示问题")
                
        except Exception as e:
            self.logger.error(f"更新目录树失败: {str(e)}")
            import traceback
            self.logger.error(f"完整错误信息: {traceback.format_exc()}")
    
    def _on_directory_double_click(self, event):
        """目录双击事件"""
        selection = self.directory_tree.selection()
        if selection:
            item = self.directory_tree.item(selection[0])
            full_path, is_directory = item['values']
            if is_directory:
                self.current_remote_path = full_path
                self.current_path_var.set(full_path)
                self._refresh_directory()
    
    def _on_directory_select(self, event):
        """目录选择事件"""
        selection = self.directory_tree.selection()
        if selection:
            item = self.directory_tree.item(selection[0])
            full_path, is_directory = item['values']
            if is_directory:
                self.current_remote_path = full_path
                self.current_path_var.set(full_path)
    
    def _go_parent_directory(self):
        """上级目录"""
        if self.current_remote_path != '/':
            parent_path = os.path.dirname(self.current_remote_path)
            if not parent_path:
                parent_path = '/'
            self.current_remote_path = parent_path
            self.current_path_var.set(parent_path)
            self._refresh_directory()
    
    def _quick_start_transfer(self):
        """快速开始传输"""
        if not self.is_connected:
            messagebox.showerror("未连接", "请先连接设备")
            return
        
        if self.queue_listbox.size() == 0:
            messagebox.showinfo("队列为空", "请先拖拽文件到传输区域添加到队列")
            return
        
        # 直接调用开始传输
        self._start_transfer()
    
    def _test_transfer_setup(self):
        """测试传输设置"""
        self.logger.info("🔧 开始测试传输设置")
        
        # 1. 检查连接状态
        if not self.is_connected:
            self.logger.error("❌ 设备未连接")
            messagebox.showerror("测试失败", "请先连接设备")
            return
        
        # 2. 检查HTTP服务器
        if not self.http_server:
            self.logger.error("❌ HTTP服务器未启动")
            return
        
        # 3. 获取并显示网络信息
        local_ip = self._get_local_ip()
        temp_dir = self.http_server.temp_dir
        
        self.logger.info(f"✅ 连接状态: 已连接到 {self.connection_config.get('host', 'Unknown')}")
        self.logger.info(f"✅ HTTP服务器: 运行中 (端口88)")
        self.logger.info(f"✅ 本机IP地址: {local_ip}")
        self.logger.info(f"✅ 临时目录: {temp_dir}")
        self.logger.info(f"✅ 当前远程路径: {self.current_remote_path}")
        
        # 4. 测试网络连通性
        threading.Thread(target=self._test_network_connectivity, args=(local_ip,), daemon=True).start()
        
        messagebox.showinfo("传输设置检查", 
                          f"传输设置检查完成\n\n"
                          f"本机IP: {local_ip}\n"
                          f"HTTP端口: 88\n"
                          f"临时目录: {temp_dir}\n"
                          f"远程路径: {self.current_remote_path}\n\n"
                          f"详细信息请查看日志")
    
    def _show_transfer_status(self):
        """显示传输状态"""
        queue_count = self.queue_listbox.size()
        if queue_count == 0:
            status_msg = "传输队列为空"
        else:
            files = []
            for i in range(queue_count):
                files.append(self.queue_listbox.get(i))
            status_msg = f"队列中有 {queue_count} 个文件:\n\n" + "\n".join(files)
        
        messagebox.showinfo("传输状态", status_msg)
    
    def _test_network_connectivity(self, local_ip):
        """测试网络连通性"""
        try:
            self.logger.info("🔍 测试网络连通性...")
            
            # 通过telnet测试能否ping本机
            future = self._run_async(self._test_ping_from_remote(local_ip))
            if future:
                result = future.result(timeout=10)
                if result:
                    self.logger.info("✅ 远程设备可以访问本机")
                else:
                    self.logger.warning("⚠️ 远程设备可能无法访问本机")
            
        except Exception as e:
            self.logger.error(f"❌ 网络连通性测试失败: {str(e)}")
    
    async def _test_ping_from_remote(self, local_ip):
        """从远程设备ping本机"""
        try:
            ping_cmd = f"ping -c 1 {local_ip}"
            result = await self.telnet_client.execute_command(ping_cmd, timeout=10)
            self.logger.info(f"Ping结果: {result}")
            
            # 检查ping是否成功
            success_indicators = ['1 packets transmitted, 1 received', '1 received', '0% packet loss']
            return any(indicator in result for indicator in success_indicators)
            
        except Exception as e:
            self.logger.error(f"Ping测试失败: {str(e)}")
            return False
    
    def _on_drop(self, event):
        """文件拖拽事件"""
        try:
            self.logger.info(f"收到拖拽事件，数据: {repr(event.data)}")
            files = self._parse_drop_files(event.data)
            self.logger.info(f"解析到 {len(files)} 个文件: {files}")
            if files:
                self._add_files_to_queue(files)
            else:
                self.logger.warning("没有解析到有效文件")
            self._reset_drop_zone_style()
        except Exception as e:
            self.logger.error(f"处理拖拽失败: {str(e)}")
            import traceback
            self.logger.error(f"完整错误信息: {traceback.format_exc()}")
    
    def _on_drag_enter(self, event):
        """拖拽进入"""
        self.drop_zone.configure(bg=self.colors['accent'])
        self.drop_label.configure(bg=self.colors['accent'], fg=self.colors['text_button'])
        self.drop_label.configure(text="释放文件进行上传")
    
    def _on_drag_leave(self, event):
        """拖拽离开"""
        self._reset_drop_zone_style()
    
    def _reset_drop_zone_style(self):
        """重置拖拽区域样式"""
        self.drop_zone.configure(bg=self.colors['bg_secondary'])
        self.drop_label.configure(bg=self.colors['bg_secondary'], fg=self.colors['text_secondary'])
        self.drop_label.configure(text="将文件拖拽到此处进行上传\n\n支持多文件同时上传\n点击此处选择文件")
    
    def _on_select_files(self, event):
        """选择文件"""
        try:
            self.logger.info("打开文件选择对话框")
            files = filedialog.askopenfilenames(title="选择文件")
            self.logger.info(f"用户选择了 {len(files)} 个文件: {files}")
            if files:
                self._add_files_to_queue(list(files))
            else:
                self.logger.info("用户取消了文件选择")
        except Exception as e:
            self.logger.error(f"选择文件失败: {str(e)}")
            import traceback
            self.logger.error(f"完整错误信息: {traceback.format_exc()}")
    
    def _parse_drop_files(self, data):
        """解析拖拽文件"""
        files = []
        try:
            if isinstance(data, str):
                file_paths = data.replace('\\', '/').split()
                for path in file_paths:
                    path = path.strip('{}').strip()
                    if os.path.exists(path):
                        files.append(path)
        except Exception as e:
            self.logger.error(f"解析文件失败: {str(e)}")
        return files
    
    def _add_files_to_queue(self, files):
        """添加文件到队列"""
        self.logger.info(f"开始添加 {len(files)} 个文件到队列")
        
        if not self.is_connected:
            self.logger.warning("设备未连接，无法添加文件")
            messagebox.showwarning("未连接", "请先连接到设备")
            return
        
        added_count = 0
        for file_path in files:
            self.logger.debug(f"检查文件: {file_path}")
            if os.path.isfile(file_path):
                filename = os.path.basename(file_path)
                display_text = f"{filename} -> {self.current_remote_path}"
                self.queue_listbox.insert(tk.END, display_text)
                self.file_path_mapping[filename] = file_path
                added_count += 1
                self.logger.info(f"已添加文件: {filename}")
            else:
                self.logger.warning(f"文件不存在或不是文件: {file_path}")
        
        if added_count > 0:
            self.logger.info(f"成功添加 {added_count} 个文件到队列")
            self._update_status(f"已添加 {added_count} 个文件到队列")
            self._update_queue_count()
        else:
            self.logger.warning("没有有效文件被添加到队列")
    
    def _clear_transfer_queue(self):
        """清空队列"""
        self.queue_listbox.delete(0, tk.END)
        self.file_path_mapping.clear()
        self._update_status("队列已清空")
        self._update_queue_count()
    
    def _update_queue_count(self):
        """更新队列计数显示"""
        count = self.queue_listbox.size()
        self.queue_count_label.configure(text=f"({count}个文件)")
    
    def _start_transfer(self):
        """开始传输"""
        if not self.is_connected:
            messagebox.showwarning("未连接", "请先连接到设备")
            return
        
        if self.queue_listbox.size() == 0:
            messagebox.showinfo("无文件", "队列为空")
            return
        
        # 检查HTTP服务器状态
        if not self.http_server:
            self.logger.error("HTTP服务器未启动")
            messagebox.showerror("错误", "HTTP服务器未启动，请重新连接设备")
            return
        
        self.logger.info(f"开始传输 {self.queue_listbox.size()} 个文件")
        self.start_transfer_button.configure(state='disabled', text='传输中...')
        threading.Thread(target=self._transfer_files_async, daemon=True).start()
    
    def _transfer_files_async(self):
        """异步传输文件"""
        try:
            success_count = 0
            total_count = self.queue_listbox.size()
            
            for i in range(total_count):
                item_text = self.queue_listbox.get(i)
                parts = item_text.split(" -> ")
                if len(parts) == 2:
                    filename = parts[0]
                    remote_path = parts[1]
                    
                    if filename in self.file_path_mapping:
                        local_file = self.file_path_mapping[filename]
                        if self._transfer_single_file(local_file, remote_path, filename):
                            success_count += 1
            
            self.root.after(0, self._on_transfer_complete, success_count, total_count)
            
        except Exception as e:
            self.logger.error(f"文件传输异常: {str(e)}")
            self.root.after(0, self._on_transfer_error, str(e))
    
    def _transfer_single_file(self, local_file, remote_path, filename):
        """传输单个文件"""
        self.logger.info(f"开始传输文件: {filename} -> {remote_path}")
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
            
            # 获取下载URL
            host_ip = self._get_local_ip()
            download_url = f"http://{host_ip}:88/{filename}"
            self.logger.info(f"生成下载URL: {download_url}")
            
            # 通过telnet下载
            self.logger.info(f"开始通过telnet执行下载命令")
            future = self._run_async(self._download_via_telnet(download_url, remote_path, filename))
            if future:
                result = future.result(timeout=30)
                # 清理临时文件
                self.http_server.remove_file(filename)
                if result:
                    self.logger.info(f"文件传输成功: {filename}")
                else:
                    self.logger.error(f"文件传输失败: {filename}")
                return result
            else:
                self.logger.error("无法创建异步任务")
            
            return False
            
        except Exception as e:
            self.logger.error(f"传输文件失败: {str(e)}")
            import traceback
            self.logger.error(f"详细错误: {traceback.format_exc()}")
            return False
    
    async def _download_via_telnet(self, download_url, remote_path, filename):
        """通过telnet下载"""
        try:
            self.logger.info(f"切换到远程目录: {remote_path}")
            cd_result = await self.telnet_client.execute_command(f'cd "{remote_path}"')
            self.logger.debug(f"cd命令结果: {cd_result}")
            
            wget_cmd = f'wget -O "{filename}" "{download_url}"'
            self.logger.info(f"执行wget命令: {wget_cmd}")
            result = await self.telnet_client.execute_command(wget_cmd, timeout=30)
            self.logger.info(f"wget命令输出: {result}")
            
            # 检查下载结果
            success_keywords = ['100%', 'saved', 'complete', 'downloaded']
            if any(keyword in result.lower() for keyword in success_keywords):
                self.logger.info(f"文件下载成功判断通过: {filename}")
                return True
            else:
                # 尝试检查文件是否确实存在
                check_cmd = f'ls -la "{filename}"'
                check_result = await self.telnet_client.execute_command(check_cmd)
                self.logger.info(f"文件存在性检查: {check_result}")
                
                if filename in check_result and "-rw" in check_result:
                    self.logger.info(f"文件确实存在，下载成功: {filename}")
                    return True
                else:
                    self.logger.error(f"wget失败，文件不存在: {result}")
                    return False
                
        except Exception as e:
            self.logger.error(f"telnet下载失败: {str(e)}")
            import traceback
            self.logger.error(f"详细错误: {traceback.format_exc()}")
            return False
    
    def _get_local_ip(self):
        """获取本机IP"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except Exception:
            return "127.0.0.1"
    
    def _on_transfer_complete(self, success_count, total_count):
        """传输完成"""
        self.start_transfer_button.configure(state='normal', text='开始传输')
        
        if success_count == total_count:
            messagebox.showinfo("传输完成", f"成功传输 {success_count} 个文件")
        else:
            messagebox.showwarning("传输完成", f"成功: {success_count}, 失败: {total_count - success_count}")
        
        self._clear_transfer_queue()
    
    def _on_transfer_error(self, error_msg):
        """传输错误"""
        self.start_transfer_button.configure(state='normal', text='开始传输')
        messagebox.showerror("传输错误", f"传输时出错:\n{error_msg}")
    
    def _clear_log(self):
        """清空日志"""
        self.log_text.delete(1.0, tk.END)
    
    def _save_log(self):
        """保存日志"""
        try:
            content = self.log_text.get(1.0, tk.END)
            if not content.strip():
                messagebox.showinfo("无内容", "日志为空")
                return
            
            file_path = filedialog.asksaveasfilename(
                title="保存日志",
                defaultextension=".txt",
                filetypes=[("文本文件", "*.txt")]
            )
            
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                messagebox.showinfo("保存成功", f"日志已保存到:\n{file_path}")
                
        except Exception as e:
            messagebox.showerror("保存失败", f"保存日志失败:\n{str(e)}")
    
    def _append_log(self, message):
        """添加日志"""
        try:
            self.log_text.insert(tk.END, message + '\n')
            self.log_text.see(tk.END)
            
            # 限制日志行数
            lines = int(self.log_text.index('end-1c').split('.')[0])
            if lines > 1000:
                self.log_text.delete(1.0, '100.0')
        except Exception:
            pass
    
    def _update_status(self, message):
        """更新状态"""
        try:
            self.status_var.set(message)
            self.root.update_idletasks()
        except Exception:
            pass
    
    def _on_closing(self):
        """窗口关闭"""
        if messagebox.askokcancel("退出", "确定要退出吗？"):
            self._cleanup()
            self.root.destroy()


if __name__ == "__main__":
    # 检查依赖
    try:
        app = ModernFileTransferGUI()
        app.run()
    except ImportError as e:
        print(f"缺少依赖模块: {e}")
        print("请安装必要的依赖:")
        print("pip install tkinterdnd2 telnetlib3")
    except Exception as e:
        print(f"程序启动失败: {e}")
        import traceback  
        traceback.print_exc() 