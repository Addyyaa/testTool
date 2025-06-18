#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
现代化文件传输工具主程序

集成GUI界面、HTTP服务器、Telnet客户端和文件传输控制器

修复说明：
- 已修复连接后UI卡死问题：使用回调方式替代阻塞的future.result()
- 已修复异步嵌套调用问题：简化连接成功后的处理逻辑
- 已修复事件循环锁创建问题：确保telnet锁在正确的上下文中创建
- 已修复传输和目录刷新的UI阻塞问题：全面采用回调方式处理异步结果
"""

import asyncio
import os
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter.scrolledtext import ScrolledText
import tkinterdnd2 as tkdnd
from typing import Dict, List, Optional, Any
import logging
import socket
import re

# 添加父目录到系统路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from telnetTool.telnetConnect import CustomTelnetClient
from fileTransfer.http_server import FileHTTPServer
from fileTransfer.file_transfer_controller import FileTransferController, TransferTask, RemoteFileEditor
from fileTransfer.ip_history_manager import IPHistoryManager, read_device_id_from_remote


class ModernFileTransferGUI:
    """现代化文件传输GUI主界面"""
    
    def __init__(self):
        """初始化GUI界面"""
        # 现代化主题配色 - 添加渐变和透明度支持
        self.colors = {
            'bg_primary': '#ffffff',
            'bg_secondary': '#f8fafc',
            'bg_sidebar': '#f1f5f9',
            'bg_card': '#ffffff',
            'bg_button': '#0f7b6c',
            'bg_button_hover': '#0a5d52',
            'bg_accent': '#10a37f',
            'bg_accent_light': '#d1fae5',
            'text_primary': '#1e293b',
            'text_secondary': '#64748b',
            'text_muted': '#94a3b8',
            'text_button': '#ffffff',
            'border': '#e2e8f0',
            'border_focus': '#10a37f',
            'accent': '#10a37f',
            'error': '#ef4444',
            'success': '#10b981',
            'warning': '#f59e0b',
            'shadow': '#00000010',
            'overlay': '#00000020'
        }
        
        # 创建主窗口
        self.root = tkdnd.Tk()
        self.root.title("202文件传输工具")
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
        
        # 初始化IP历史管理器
        self.ip_history_manager = IPHistoryManager("ip_history.json")
        self.current_device_id = None  # 当前连接设备的ID
        
        # 配置日志（需要在创建界面元素之前初始化）
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
        self.telnet_lock = None  # telnet连接锁，防止并发访问
        self._start_event_loop()
        
        self.logger.info("GUI界面初始化完成")
    
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
            # 获取当前窗口尺寸
            window_width = self.root.winfo_width()
            window_height = self.root.winfo_height()
            
            if window_width <= 1 or window_height <= 1:
                return  # 窗口还没有完全初始化
            
            # 计算侧边栏宽度（窗口宽度的25%，最小280px，最大400px）
            sidebar_width = max(280, min(400, int(window_width * 0.25)))
            
            # 重新配置侧边栏
            if hasattr(self, 'sidebar_frame'):
                self.sidebar_frame.configure(width=sidebar_width)
            
            # 动态调整组件高度
            self._adjust_component_heights(window_height)
            
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.debug(f"布局调整出错: {e}")
    
    def _adjust_component_heights(self, window_height):
        """根据窗口高度调整组件高度"""
        try:
            # 计算可用高度（减去标题栏、状态栏等固定高度）
            available_height = window_height - 100  # 预留100px给状态栏等
            
            # 连接面板固定高度约200px
            connection_height = 200
            
            # 传输队列面板高度（15%的可用高度，最小120px）
            queue_height = max(120, int(available_height * 0.15))
            
            # 目录面板高度（剩余高度）
            directory_height = available_height - connection_height - queue_height - 60  # 预留间距
            directory_height = max(200, directory_height)
            
            # 应用高度调整
            if hasattr(self, 'directory_tree'):
                # 计算目录树的行数（每行约20px）
                tree_rows = max(8, min(20, directory_height // 25))
                self.directory_tree.configure(height=tree_rows)
            
            if hasattr(self, 'queue_listbox'):
                # 计算队列列表的行数
                queue_rows = max(4, min(12, queue_height // 20))
                self.queue_listbox.configure(height=queue_rows)
            
            if hasattr(self, 'log_text'):
                # 计算日志区域的行数（主内容区域的40%）
                main_content_height = available_height
                log_rows = max(6, min(25, int(main_content_height * 0.4) // 20))
                self.log_text.configure(height=log_rows)
                
        except Exception as e:
            if hasattr(self, 'logger'):
                self.logger.debug(f"高度调整出错: {e}")
    
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
        """创建现代化侧边栏 - 响应式布局"""
        # 侧边栏容器 - 占窗口宽度的28%，增加一点宽度以容纳更多内容
        self.sidebar_frame = tk.Frame(self.main_frame, bg=self.colors['bg_sidebar'])
        self.sidebar_frame.place(x=0, y=0, relwidth=0.28, relheight=1.0)
        
        # 连接配置区域 - 占侧边栏高度的35%，增加高度
        self._create_connection_panel()
        
        # 远程目录浏览区域 - 占侧边栏高度的45%
        self._create_directory_panel()
        
        # 传输队列区域 - 占侧边栏高度的20%
        self._create_transfer_queue_panel()
    
    def _create_connection_panel(self):
        """创建现代化连接配置面板 - 占侧边栏35%高度"""
        # 连接配置容器 - 使用卡片样式
        self.connection_container = tk.Frame(self.sidebar_frame, bg=self.colors['bg_sidebar'])
        self.connection_container.place(relx=0.02, rely=0.02, relwidth=0.96, relheight=0.35)
        
        # 卡片背景
        self.connection_card = tk.Frame(self.connection_container, 
                                       bg=self.colors['bg_card'], 
                                       relief='flat', bd=0)
        self.connection_card.place(relx=0, rely=0, relwidth=1.0, relheight=1.0)
        
        # 连接配置标题 - 占容器8%高度
        connection_title = tk.Label(self.connection_card, text="🔗 设备连接", 
                                  bg=self.colors['bg_card'], fg=self.colors['text_primary'],
                                  font=('Microsoft YaHei UI', 11, 'bold'))
        connection_title.place(relx=0.04, rely=0.02, relwidth=0.92, relheight=0.08)
        
        # 连接配置框架 - 占容器88%高度
        self.connection_frame = tk.Frame(self.connection_card, bg=self.colors['bg_card'])
        self.connection_frame.place(relx=0.04, rely=0.12, relwidth=0.92, relheight=0.86)
        
        # 主机地址 - 占框架13%高度
        tk.Label(self.connection_frame, text="主机地址:", 
                bg=self.colors['bg_card'], fg=self.colors['text_secondary'],
                font=('Microsoft YaHei UI', 9)).place(relx=0, rely=0, relwidth=1.0, relheight=0.10)
        
        # IP输入框和历史按钮容器
        ip_container = tk.Frame(self.connection_frame, bg=self.colors['bg_card'])
        ip_container.place(relx=0, rely=0.11, relwidth=1.0, relheight=0.12)
        
        # IP输入框（可编辑）
        self.host_var = tk.StringVar(value="192.168.1.100")
        self.host_entry = tk.Entry(ip_container, textvariable=self.host_var,
                                 font=('Microsoft YaHei UI', 9),
                                 bg=self.colors['bg_primary'], fg=self.colors['text_primary'],
                                 relief='solid', bd=1, highlightthickness=1,
                                 highlightcolor=self.colors['border_focus'])
        # 注意: 初始宽度占比稍后会在 _adjust_ip_id_width 中根据内容调整
        self.host_entry.place(relx=0, rely=0, relwidth=0.58, relheight=1.0)
        
        # 屏幕ID显示（只读）
        self.device_id_var = tk.StringVar(value="--")
        self.device_id_display = tk.Entry(ip_container, textvariable=self.device_id_var,
                                        font=('Microsoft YaHei UI', 9), state='readonly',
                                        readonlybackground=self.colors['bg_secondary'], fg=self.colors['text_secondary'],
                                        relief='flat', justify='center')
        self.device_id_display.place(relx=0.60, rely=0, relwidth=0.22, relheight=1.0)
        
        # 历史记录按钮
        self.history_button = tk.Button(ip_container, text="📋", 
                                      command=self._show_ip_history,
                                      bg=self.colors['bg_accent'], fg=self.colors['text_button'],
                                      font=('Microsoft YaHei UI', 8),
                                      relief='flat', borderwidth=0,
                                      activebackground=self.colors['bg_accent'],
                                      cursor='hand2')
        self.history_button.place(relx=0.83, rely=0, relwidth=0.07, relheight=1.0)
        
        # 清除历史按钮
        self.clear_history_button = tk.Button(ip_container, text="🗑", 
                                            command=self._clear_ip_history,
                                            bg=self.colors['error'], fg=self.colors['text_button'],
                                            font=('Microsoft YaHei UI', 8),
                                            relief='flat', borderwidth=0,
                                            activebackground='#dc2626',
                                            cursor='hand2')
        self.clear_history_button.place(relx=0.91, rely=0, relwidth=0.07, relheight=1.0)
        
        # 端口 - 占框架13%高度
        tk.Label(self.connection_frame, text="端口:", 
                bg=self.colors['bg_card'], fg=self.colors['text_secondary'],
                font=('Microsoft YaHei UI', 9)).place(relx=0, rely=0.25, relwidth=1.0, relheight=0.10)
        self.port_entry = tk.Entry(self.connection_frame, font=('Microsoft YaHei UI', 9),
                                 bg=self.colors['bg_primary'], fg=self.colors['text_primary'],
                                 relief='solid', bd=1, highlightthickness=1,
                                 highlightcolor=self.colors['border_focus'])
        self.port_entry.place(relx=0, rely=0.36, relwidth=1.0, relheight=0.12)
        self.port_entry.insert(0, "23")
        
        # 用户名和密码 - 并排布局
        tk.Label(self.connection_frame, text="用户名:", 
                bg=self.colors['bg_card'], fg=self.colors['text_secondary'],
                font=('Microsoft YaHei UI', 9)).place(relx=0, rely=0.50, relwidth=0.48, relheight=0.10)
        self.username_entry = tk.Entry(self.connection_frame, font=('Microsoft YaHei UI', 9),
                                     bg=self.colors['bg_primary'], fg=self.colors['text_primary'],
                                     relief='solid', bd=1, highlightthickness=1,
                                     highlightcolor=self.colors['border_focus'])
        self.username_entry.place(relx=0, rely=0.61, relwidth=0.48, relheight=0.12)
        self.username_entry.insert(0, "root")
        
        tk.Label(self.connection_frame, text="密码:", 
                bg=self.colors['bg_card'], fg=self.colors['text_secondary'],
                font=('Microsoft YaHei UI', 9)).place(relx=0.52, rely=0.50, relwidth=0.48, relheight=0.10)
        self.password_entry = tk.Entry(self.connection_frame, font=('Microsoft YaHei UI', 9), show='*',
                                     bg=self.colors['bg_primary'], fg=self.colors['text_primary'],
                                     relief='solid', bd=1, highlightthickness=1,
                                     highlightcolor=self.colors['border_focus'])
        self.password_entry.place(relx=0.52, rely=0.61, relwidth=0.48, relheight=0.12)
        self.password_entry.insert(0, "ya!2dkwy7-934^")
        
        # 连接按钮 - 现代化样式
        self.connect_button = tk.Button(self.connection_frame, text="🔗 连接设备", 
                                      command=self._on_connect_clicked,
                                      bg=self.colors['bg_button'], fg='#ffffff',
                                      font=('Microsoft YaHei UI', 10, 'bold'),
                                      relief='flat', borderwidth=0,
                                      activebackground=self.colors['bg_button_hover'], 
                                      activeforeground='#ffffff',
                                      cursor='hand2')
        self.connect_button.place(relx=0, rely=0.76, relwidth=1.0, relheight=0.12)
        
        # 连接状态指示器 - 重新设计布局
        self.connection_status_frame = tk.Frame(self.connection_frame, bg=self.colors['bg_card'])
        self.connection_status_frame.place(relx=0, rely=0.90, relwidth=1.0, relheight=0.10)
        
        # 状态指示点
        self.status_indicator = tk.Canvas(self.connection_status_frame, width=10, height=10, 
                                        bg=self.colors['bg_card'], highlightthickness=0)
        self.status_indicator.place(relx=0, rely=0.2, relwidth=0.08, relheight=0.6)
        self.status_indicator.create_oval(2, 2, 8, 8, fill=self.colors['error'], outline='')
        
        # 状态文字
        self.connection_status_label = tk.Label(self.connection_status_frame, text="未连接", 
                                              bg=self.colors['bg_card'], fg=self.colors['text_muted'],
                                              font=('Microsoft YaHei UI', 8))
        self.connection_status_label.place(relx=0.12, rely=0, relwidth=0.88, relheight=1.0)
        
        # 加载最后使用的IP
        self._load_last_ip()
    
    def _create_directory_panel(self):
        """创建现代化远程目录浏览面板 - 占侧边栏45%高度"""
        # 目录浏览容器
        self.directory_container = tk.Frame(self.sidebar_frame, bg=self.colors['bg_sidebar'])
        self.directory_container.place(relx=0.02, rely=0.39, relwidth=0.96, relheight=0.45)
        
        # 卡片背景
        self.directory_card = tk.Frame(self.directory_container, 
                                     bg=self.colors['bg_card'], 
                                     relief='flat', bd=0)
        self.directory_card.place(relx=0, rely=0, relwidth=1.0, relheight=1.0)
        
        # 目录浏览标题 - 占容器7%高度
        directory_title = tk.Label(self.directory_card, text="📁 远程目录", 
                                 bg=self.colors['bg_card'], fg=self.colors['text_primary'],
                                 font=('Microsoft YaHei UI', 11, 'bold'))
        directory_title.place(relx=0.04, rely=0.02, relwidth=0.92, relheight=0.07)
        
        # 当前路径标签 - 占容器5%高度
        self.current_path_label = tk.Label(self.directory_card, text="当前路径:", 
                                         bg=self.colors['bg_card'], fg=self.colors['text_secondary'],
                                         font=('Microsoft YaHei UI', 8))
        self.current_path_label.place(relx=0.04, rely=0.10, relwidth=0.92, relheight=0.05)
        
        # 当前路径输入框 - 占容器7%高度
        self.current_path_var = tk.StringVar(value="/")
        self.current_path_entry = tk.Entry(self.directory_card, textvariable=self.current_path_var,
                                         font=('Microsoft YaHei UI', 8), state='readonly',
                                         bg=self.colors['bg_secondary'], fg=self.colors['text_primary'],
                                         relief='solid', bd=1)
        self.current_path_entry.place(relx=0.04, rely=0.16, relwidth=0.92, relheight=0.07)
        
        # 目录树 - 占容器60%高度
        self.directory_tree = ttk.Treeview(self.directory_card, style='Modern.Treeview', 
                                         columns=(), show='tree')
        self.directory_tree.place(relx=0.04, rely=0.25, relwidth=0.88, relheight=0.60)
        
        # 目录树滚动条
        tree_scrollbar = ttk.Scrollbar(self.directory_card, orient='vertical', command=self.directory_tree.yview)
        tree_scrollbar.place(relx=0.92, rely=0.25, relwidth=0.04, relheight=0.60)
        self.directory_tree.configure(yscrollcommand=tree_scrollbar.set)
        
        # 现代化按钮区域 - 占容器15%高度
        buttons_container = tk.Frame(self.directory_card, bg=self.colors['bg_card'])
        buttons_container.place(relx=0.04, rely=0.87, relwidth=0.92, relheight=0.11)
        
        # 现代化按钮 - 使用图标
        self.refresh_button = tk.Button(buttons_container, text="🔄 刷新", 
                                       command=self._safe_refresh_directory,
                                       bg=self.colors['bg_button'], fg='#ffffff',
                                       font=('Microsoft YaHei UI', 9, 'bold'),
                                       relief='flat', borderwidth=0,
                                       activebackground=self.colors['bg_button_hover'], 
                                       activeforeground='#ffffff',
                                       cursor='hand2')
        self.refresh_button.place(relx=0, rely=0, relwidth=0.32, relheight=1.0)
        
        self.parent_button = tk.Button(buttons_container, text="⬆️ 上级", 
                                     command=self._go_parent_directory,
                                     bg=self.colors['bg_button'], fg='#ffffff',
                                     font=('Microsoft YaHei UI', 9, 'bold'),
                                     relief='flat', borderwidth=0,
                                     activebackground=self.colors['bg_button_hover'], 
                                     activeforeground='#ffffff',
                                     cursor='hand2')
        self.parent_button.place(relx=0.34, rely=0, relwidth=0.32, relheight=1.0)
        
        self.delete_file_button = tk.Button(buttons_container, text="🗑️ 删除", 
                                           command=self._delete_selected_file,
                                           bg=self.colors['error'], fg='#ffffff',
                                           font=('Microsoft YaHei UI', 9, 'bold'),
                                           relief='flat', borderwidth=0,
                                           activebackground='#b91c1c', activeforeground='#ffffff',
                                           cursor='hand2', state='disabled')
        self.delete_file_button.place(relx=0.68, rely=0, relwidth=0.32, relheight=1.0)
        
        # 为删除按钮添加右键菜单（调试功能）
        self.delete_context_menu = tk.Menu(self.root, tearoff=0)
        self.delete_context_menu.add_command(label="🔍 调试选择状态", command=self._debug_selection_status)
        self.delete_context_menu.add_separator()
        self.delete_context_menu.add_command(label="🔧 测试传输设置", command=self._test_transfer_setup)
        self.delete_context_menu.add_command(label="📊 显示传输状态", command=self._show_transfer_status)
        
        def show_delete_menu(event):
            try:
                self.delete_context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                self.delete_context_menu.grab_release()
        
        # 为删除按钮绑定右键菜单（调试功能）
        self.delete_file_button.bind("<Button-3>", show_delete_menu)  # 右键
    
    def _create_transfer_queue_panel(self):
        """创建现代化传输队列面板 - 占侧边栏20%高度"""
        # 传输队列容器
        self.queue_container = tk.Frame(self.sidebar_frame, bg=self.colors['bg_sidebar'])
        self.queue_container.place(relx=0.02, rely=0.86, relwidth=0.96, relheight=0.12)
        
        # 创建一个虚拟的队列列表（用于兼容性）
        self.queue_listbox = tk.Listbox(self.queue_container, 
                                      font=('Microsoft YaHei UI', 1),
                                      bg=self.colors['bg_card'], fg=self.colors['text_primary'])
        # 不显示，仅用于数据存储
        
        # 卡片背景
        self.queue_card = tk.Frame(self.queue_container, 
                                 bg=self.colors['bg_card'], 
                                 relief='flat', bd=0)
        self.queue_card.place(relx=0, rely=0, relwidth=1.0, relheight=1.0)
        
        # 紧凑的传输队列标题和计数
        queue_title = tk.Label(self.queue_card, text="🚀 传输队列", 
                             bg=self.colors['bg_card'], fg=self.colors['text_primary'],
                             font=('Microsoft YaHei UI', 10, 'bold'))
        queue_title.place(relx=0.04, rely=0.05, relwidth=0.6, relheight=0.25)
        
        self.queue_count_label = tk.Label(self.queue_card, text="(0个文件)", 
                                        bg=self.colors['bg_card'], fg=self.colors['text_muted'],
                                        font=('Microsoft YaHei UI', 8))
        self.queue_count_label.place(relx=0.65, rely=0.05, relwidth=0.31, relheight=0.25)
        
        # 紧凑的控制按钮 - 占容器70%高度
        self.start_transfer_button = tk.Button(self.queue_card, text="▶️ 开始", 
                                             command=self._start_transfer,
                                             bg=self.colors['error'], fg='#ffffff',
                                             font=('Microsoft YaHei UI', 9, 'bold'),
                                             relief='flat', borderwidth=0,
                                             activebackground='#b91c1c', activeforeground='#ffffff',
                                             cursor='hand2')
        self.start_transfer_button.place(relx=0.04, rely=0.32, relwidth=0.44, relheight=0.63)
        
        self.clear_queue_button = tk.Button(self.queue_card, text="🗑️ 清空", 
                                          command=self._clear_transfer_queue,
                                          bg=self.colors['text_muted'], fg='#ffffff',
                                          font=('Microsoft YaHei UI', 9, 'bold'),
                                          relief='flat', borderwidth=0,
                                          activebackground='#4b5563', activeforeground='#ffffff',
                                          cursor='hand2')
        self.clear_queue_button.place(relx=0.52, rely=0.32, relwidth=0.44, relheight=0.63)
    
    def _create_main_content(self):
        """创建现代化主内容区域 - 占窗口宽度72%"""
        # 主内容容器
        self.content_frame = tk.Frame(self.main_frame, bg=self.colors['bg_primary'])
        self.content_frame.place(relx=0.28, rely=0, relwidth=0.72, relheight=1.0)
        
        # 创建拖拽上传区域 - 占主内容区域35%高度（减小）
        self._create_drop_zone()
        
        # 创建日志区域 - 占主内容区域65%高度（增大）
        self._create_log_area()
    
    def _create_drop_zone(self):
        """创建现代化文件拖拽区域 - 占主内容35%高度"""
        # 拖拽区域容器
        self.drop_zone_container = tk.Frame(self.content_frame, bg=self.colors['bg_primary'])
        self.drop_zone_container.place(relx=0.02, rely=0.02, relwidth=0.96, relheight=0.35)
        
        # 拖拽区域标题 - 占容器12%高度
        drop_title = tk.Label(self.drop_zone_container, text="📤 文件传输", 
                            bg=self.colors['bg_primary'], fg=self.colors['text_primary'],
                            font=('Microsoft YaHei UI', 12, 'bold'))
        drop_title.place(relx=0, rely=0, relwidth=1.0, relheight=0.12)
        
        # 现代化拖拽区域 - 带圆角效果
        self.drop_zone = tk.Frame(self.drop_zone_container, 
                                bg=self.colors['bg_accent_light'],
                                relief='solid', borderwidth=1)
        self.drop_zone.place(relx=0, rely=0.15, relwidth=1.0, relheight=0.82)
        
        # 现代化拖拽提示标签
        self.drop_label = tk.Label(self.drop_zone,
                                 text="📁 拖拽文件到此处\n或点击选择文件",
                                 font=('Microsoft YaHei UI', 11),
                                 fg=self.colors['text_secondary'],
                                 bg=self.colors['bg_accent_light'],
                                 justify='center')
        self.drop_label.place(relx=0.5, rely=0.5, anchor='center')
        
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
        """创建现代化日志显示区域 - 占主内容65%高度"""
        # 日志区域容器
        self.log_container = tk.Frame(self.content_frame, bg=self.colors['bg_primary'])
        self.log_container.place(relx=0.02, rely=0.39, relwidth=0.96, relheight=0.59)
        
        # 日志区域标题 - 占容器8%高度
        log_title = tk.Label(self.log_container, text="📋 操作日志", 
                           bg=self.colors['bg_primary'], fg=self.colors['text_primary'],
                           font=('Microsoft YaHei UI', 12, 'bold'))
        log_title.place(relx=0, rely=0, relwidth=1.0, relheight=0.08)
        
        # 日志文本区域 - 占容器82%高度
        self.log_frame = tk.Frame(self.log_container, bg=self.colors['bg_primary'])
        self.log_frame.place(relx=0, rely=0.10, relwidth=1.0, relheight=0.80)
        
        # 现代化日志文本控件 - 占日志框架90%高度
        self.log_text = ScrolledText(self.log_frame,
                                   font=('Consolas', 9),
                                   bg=self.colors['bg_card'],
                                   fg=self.colors['text_primary'],
                                   insertbackground=self.colors['text_primary'],
                                   selectbackground=self.colors['accent'],
                                   wrap=tk.WORD,
                                   relief='solid', bd=1)
        self.log_text.place(relx=0, rely=0, relwidth=1.0, relheight=0.90)
        
        # 现代化日志控制按钮 - 占日志框架10%高度
        self.clear_log_button = tk.Button(self.log_frame, text="🗑️ 清空", 
                                         command=self._clear_log,
                                         bg=self.colors['bg_button'], fg=self.colors['text_button'],
                                         font=('Microsoft YaHei UI', 9, 'bold'),
                                         relief='flat', borderwidth=0,
                                         activebackground=self.colors['bg_button_hover'], 
                                         activeforeground=self.colors['text_button'],
                                         cursor='hand2')
        self.clear_log_button.place(relx=0, rely=0.91, relwidth=0.48, relheight=0.09)
        
        self.save_log_button = tk.Button(self.log_frame, text="💾 保存", 
                                        command=self._save_log,
                                        bg=self.colors['bg_button'], fg=self.colors['text_button'],
                                        font=('Microsoft YaHei UI', 9, 'bold'),
                                        relief='flat', borderwidth=0,
                                        activebackground=self.colors['bg_button_hover'], 
                                        activeforeground=self.colors['text_button'],
                                        cursor='hand2')
        self.save_log_button.place(relx=0.52, rely=0.91, relwidth=0.48, relheight=0.09)
    
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
        
        # 绑定输入内容变化以清空设备ID并调整宽度
        self.host_entry.bind('<Key>', lambda e: (self.device_id_var.set("--"), self._adjust_ip_id_width()))
        
        # 窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _setup_logging(self):
        """配置日志系统"""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.INFO)  # 设置为DEBUG级别以查看详细信息
        
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
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s:%(lineno)d - %(message)s')
            gui_handler.setFormatter(formatter)
            self.logger.addHandler(gui_handler)
    
    def _start_event_loop(self):
        """启动异步事件循环 - 修复版本"""
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
                import traceback
                self.logger.error(f"详细错误: {traceback.format_exc()}")
        
        self.loop_thread = threading.Thread(target=run_loop, daemon=True)
        self.loop_thread.start()
        
        # 等待事件循环启动，增加超时保护
        wait_count = 0
        max_wait = 50  # 最多等待0.5秒
        while (self.loop is None or self.telnet_lock is None) and wait_count < max_wait:
            time.sleep(0.01)
            wait_count += 1
        
        if wait_count >= max_wait:
            self.logger.error("异步事件循环启动超时")
            # 即使超时也继续运行，但记录错误
        else:
            self.logger.info(f"异步事件循环启动完成，等待了 {wait_count * 10}ms")
    
    def _run_async(self, coro):
        """在事件循环中运行异步任务 - 修复版本"""
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
            host = self.host_var.get().strip()
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
        """异步连接 - 修复版本，避免UI阻塞"""
        try:
            from telnetTool.telnetConnect import CustomTelnetClient
            self.telnet_client = CustomTelnetClient(
                host=self.connection_config['host'],
                port=self.connection_config['port'],
                timeout=30.0
            )
            
            # 使用回调方式避免阻塞UI线程
            future = self._run_async(self._do_connect())
            if future:
                # 使用add_done_callback避免阻塞
                future.add_done_callback(self._on_connect_result)
            else:
                self.root.after(0, self._on_connect_failed, "无法启动异步任务")
        except Exception as e:
            self.root.after(0, self._on_connect_failed, str(e))
    
    def _on_connect_result(self, future):
        """处理连接结果回调"""
        try:
            result = future.result()
            if result:
                self.root.after(0, self._on_connect_success)
            else:
                self.root.after(0, self._on_connect_failed, "连接失败")
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
        """连接成功 - 添加自动刷新目录功能"""
        try:
            self.logger.info("开始处理连接成功...")
            
            self.is_connected = True
            self.connect_button.configure(state='normal', text='断开连接')
            
            # 更新状态指示器
            self.status_indicator.delete('all')
            self.status_indicator.create_oval(2, 2, 10, 10, fill=self.colors['success'], outline='')
            self.connection_status_label.configure(text=f"已连接 ({self.connection_config['host']})", 
                                                 fg=self.colors['success'])
            
            # 最简化的IP保存（先仅IP），随后后台读取设备ID并更新
            current_ip = self.connection_config['host']
            if current_ip:
                try:
                    self.ip_history_manager.add_ip(current_ip, None)
                    self.logger.info(f"已保存IP到历史记录: {current_ip}")
                except Exception as e:
                    self.logger.debug(f"保存IP失败: {e}")
            
            # 设备ID读取将在目录树成功首次刷新后触发
            self._pending_device_id_ip = current_ip
            
            # 启动HTTP服务器（确保在连接成功后立即启动）
            if not self.http_server:
                self.logger.info("连接成功，立即启动HTTP服务器...")
                self._start_http_server_delayed()
            
            # 更新状态
            self._update_status(f"成功连接到 {self.connection_config['host']}")
            
            # 连接成功提示
            self.logger.info("连接成功！正在自动获取目录列表...")
            self._update_status("连接成功！正在获取目录列表...")
            
            # 延迟自动刷新目录（避免与连接过程冲突）
            self.root.after(200, self._auto_refresh_directory)
            
            self.logger.info("连接成功处理完成！")
            
        except Exception as e:
            self.logger.error(f"连接成功处理过程中出错: {e}")
            import traceback
            self.logger.error(f"详细错误: {traceback.format_exc()}")
    
    def _auto_refresh_directory(self):
        """自动刷新目录（连接成功后调用）"""
        try:
            self.logger.info("开始自动刷新目录...")
            
            # 重置当前路径为根目录
            self.current_remote_path = "/"
            self.current_path_var.set(self.current_remote_path)
            
            # 调用目录刷新
            self._refresh_directory()
            
        except Exception as e:
            self.logger.error(f"自动刷新目录失败: {e}")
            # 如果自动刷新失败，提示用户手动刷新
            self._update_status("连接成功！请手动点击刷新按钮获取目录")
    
    def _start_http_server_delayed(self):
        """延迟启动HTTP服务器，避免阻塞UI"""
        try:
            self.logger.info("开始启动HTTP服务器...")
            threading.Thread(target=self._start_http_server_background, daemon=True).start()
        except Exception as e:
            self.logger.error(f"延迟启动HTTP服务器失败: {e}")
    
    def _start_http_server_background(self):
        """在后台线程中启动HTTP服务器"""
        try:
            if not self.http_server:
                self.http_server = FileHTTPServer(port=88)
                self.http_server.start()
                
                # 获取本机IP地址
                local_ip = self._get_local_ip()
                temp_dir = self.http_server.temp_dir
                
                # 在主线程中更新UI
                self.root.after(0, lambda: self.http_status_var.set(f"HTTP服务: 运行中 (端口88)"))
                self.root.after(0, lambda: self.logger.info(f"HTTP服务器已启动 - IP: {local_ip}:88"))
                
        except Exception as e:
            self.logger.error(f"后台启动HTTP服务器失败: {str(e)}")
            # 在主线程中显示错误
            self.root.after(0, lambda: messagebox.showerror("服务器错误", f"无法启动HTTP服务器:\n{str(e)}"))
    
    def _save_device_id_background(self, ip):
        """完全在后台保存设备ID，不影响UI"""
        try:
            self.logger.debug(f"开始后台获取设备ID: {ip}")
            # 这里不调用异步方法，避免任何可能的阻塞
            # 设备ID获取可以稍后实现，现在先确保连接稳定
        except Exception as e:
            self.logger.debug(f"后台保存设备ID失败: {e}")
    
    # 暂时注释掉可能导致问题的异步方法
    # def _save_device_id_async(self, ip):
    #     """异步保存设备ID到历史记录（后台操作）"""
    #     try:
    #         future = self._run_async(self._read_and_save_device_id(ip))
    #         if future:
    #             # 不等待结果，让它在后台执行
    #             future.add_done_callback(lambda f: self._on_device_id_saved(f, ip))
    #     except Exception as e:
    #         self.logger.debug(f"后台保存设备ID失败: {e}")
    # 
    # def _on_device_id_saved(self, future, ip):
    #     """设备ID保存完成回调"""
    #     try:
    #         device_id = future.result()
    #         if device_id:
    #             self.current_device_id = device_id
    #             self.logger.info(f"设备ID已更新: {ip} -> {device_id}")
    #     except Exception as e:
    #         self.logger.debug(f"设备ID保存回调失败: {e}")
    # 
    # async def _read_and_save_device_id(self, ip):
    #     """读取并保存设备ID"""
    #     try:
    #         # 使用锁保护telnet连接
    #         async with self.telnet_lock:
    #             device_id = await read_device_id_from_remote(self.telnet_client)
    #             if device_id:
    #                 # 更新历史记录中的设备ID
    #                 self.ip_history_manager.add_ip(ip, device_id)
    #                 return device_id
    #     except Exception as e:
    #         self.logger.debug(f"读取设备ID失败: {e}")
    #     return None
    
    def _on_connect_failed(self, error_msg):
        """连接失败"""
        self.connect_button.configure(state='normal', text='连接设备')
        
        # 更新状态指示器为红色
        self.status_indicator.delete('all')
        self.status_indicator.create_oval(2, 2, 10, 10, fill=self.colors['error'], outline='')
        self.connection_status_label.configure(text="连接失败", fg=self.colors['error'])
        
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
        """启动HTTP服务器 - 简化版本（备用）"""
        # 这个方法暂时不使用，避免阻塞
        pass
    
    def _safe_refresh_directory(self):
        """安全的刷新目录（用户手动触发）"""
        if not self.is_connected:
            self._update_status("未连接，无法刷新目录")
            messagebox.showwarning("提示", "请先连接到设备")
            return
        
        self.logger.info("用户手动触发目录刷新")
        self._update_status("正在刷新目录...")
        self._refresh_directory()
    
    def _refresh_directory(self):
        """刷新目录"""
        if not self.is_connected:
            return
        threading.Thread(target=self._refresh_directory_async, daemon=True).start()
    
    def _refresh_directory_async(self):
        """异步刷新目录 - 修复版本，避免UI阻塞"""
        try:
            self.logger.info(f"开始异步刷新目录: {self.current_remote_path}")
            
            # 检查异步循环是否可用
            if not self.loop or self.loop.is_closed():
                self.logger.error("异步事件循环不可用")
                self.root.after(0, lambda: self._update_status("异步事件循环不可用"))
                return
            
            # 检查telnet客户端是否存在
            if not self.telnet_client:
                self.logger.error("Telnet客户端不存在")
                self.root.after(0, lambda: self._update_status("Telnet客户端不存在"))
                return
            
            future = self._run_async(self._get_directory_listing(self.current_remote_path))
            if future:
                # 使用回调方式处理结果
                future.add_done_callback(self._on_directory_result)
            else:
                self.logger.error("无法创建异步任务")
                self.root.after(0, lambda: self._update_status("无法创建异步任务"))
                
        except Exception as e:
            self.logger.error(f"刷新目录失败: {str(e)}")
            import traceback
            self.logger.error(f"完整错误信息: {traceback.format_exc()}")
            # 显示错误信息到状态栏
            self.root.after(0, lambda: self._update_status(f"刷新目录失败: {str(e)}"))
    
    def _on_directory_result(self, future):
        """处理目录刷新结果回调"""
        try:
            items = future.result()
            self.logger.info(f"异步操作完成，获得 {len(items)} 个项目")
            # 使用after确保在主线程中更新GUI
            self.root.after(0, lambda: self._update_directory_tree(items))
            # 延迟启动HTTP服务器（如果还没启动）
            if not self.http_server:
                self.root.after(100, self._start_http_server_delayed)
        except Exception as e:
            self.logger.error(f"目录刷新结果处理失败: {e}")
            self.root.after(0, lambda: self._update_status(f"目录刷新失败: {str(e)}"))
    
    def _clean_ansi_codes(self, text):
        """清理ANSI转义序列和颜色代码"""
        # 移除ANSI转义序列
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        cleaned = ansi_escape.sub('', text)
        
        # 移除其他控制字符，但保留换行符(\n, \r)和制表符(\t)
        control_chars = re.compile(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]')
        cleaned = control_chars.sub('', cleaned)
        
        return cleaned.strip()
    
    def _determine_file_type(self, permissions, name):
        """根据权限和文件名判断文件类型"""
        # 目录
        if permissions.startswith('d'):
            return 'directory'
        
        # 符号链接
        if permissions.startswith('l'):
            return 'link'
        
        # 可执行文件
        if 'x' in permissions[1:4]:
            return 'executable'
        
        # 根据文件扩展名判断
        name_lower = name.lower()
        
        # 图片文件
        if any(name_lower.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg']):
            return 'image'
        
        # 文档文件
        if any(name_lower.endswith(ext) for ext in ['.txt', '.doc', '.docx', '.pdf', '.md']):
            return 'document'
        
        # 压缩文件
        if any(name_lower.endswith(ext) for ext in ['.zip', '.tar', '.gz', '.bz2', '.rar', '.7z']):
            return 'archive'
        
        # 配置文件
        if any(name_lower.endswith(ext) for ext in ['.conf', '.cfg', '.ini', '.yaml', '.yml', '.json']):
            return 'config'
        
        # 脚本文件
        if any(name_lower.endswith(ext) for ext in ['.sh', '.py', '.pl', '.rb', '.js']):
            return 'script'
        
        # 默认为普通文件
        return 'file'
    
    def _get_file_icon_and_color(self, item):
        """根据文件类型获取图标和颜色"""
        file_type = item.get('file_type', 'file')
        
        # 图标映射
        icons = {
            'directory': '📁',
            'executable': '⚙️',
            'link': '🔗',
            'image': '🖼️',
            'document': '📄',
            'archive': '📦',
            'config': '⚙️',
            'script': '📜',
            'file': '📄'
        }
        
        # 颜色映射
        colors = {
            'directory': '#3b82f6',      # 蓝色
            'executable': '#10b981',     # 绿色
            'link': '#8b5cf6',           # 紫色
            'image': '#f59e0b',          # 橙色
            'document': '#6b7280',       # 灰色
            'archive': '#dc2626',        # 红色
            'config': '#0891b2',         # 青色
            'script': '#059669',         # 翠绿色
            'file': '#374151'            # 深灰色
        }
        
        icon = icons.get(file_type, icons['file'])
        color = colors.get(file_type, colors['file'])
        
        return icon, color
    
    def _configure_tree_colors(self):
        """配置treeview的颜色标签"""
        try:
            self.logger.debug("开始配置目录树颜色...")
            
            # 目录 - 蓝色，加粗
            self.directory_tree.tag_configure('directory', 
                                            foreground='#1e40af', 
                                            font=('Microsoft YaHei UI', 9, 'bold'))
            
            # 可执行文件 - 绿色，加粗
            self.directory_tree.tag_configure('executable', 
                                            foreground='#059669', 
                                            font=('Microsoft YaHei UI', 9, 'bold'))
            
            # 符号链接 - 紫色，斜体
            self.directory_tree.tag_configure('link', 
                                            foreground='#7c3aed', 
                                            font=('Microsoft YaHei UI', 9, 'italic'))
            
            # 图片文件 - 橙色
            self.directory_tree.tag_configure('image', 
                                            foreground='#ea580c')
            
            # 文档文件 - 灰色
            self.directory_tree.tag_configure('document', 
                                            foreground='#4b5563')
            
            # 压缩文件 - 红色
            self.directory_tree.tag_configure('archive', 
                                            foreground='#dc2626')
            
            # 配置文件 - 青色
            self.directory_tree.tag_configure('config', 
                                            foreground='#0891b2')
            
            # 脚本文件 - 翠绿色
            self.directory_tree.tag_configure('script', 
                                            foreground='#059669')
            
            # 普通文件 - 深灰色
            self.directory_tree.tag_configure('file', 
                                            foreground='#374151')
            
            self.logger.debug("目录树颜色配置完成")
            
        except Exception as e:
            self.logger.error(f"配置treeview颜色失败: {e}")
            import traceback
            self.logger.error(f"详细错误: {traceback.format_exc()}")
    
    async def _get_directory_listing(self, path):
        """获取目录列表"""
        try:
            # 规范化路径
            normalized_path = self._normalize_unix_path(path)
            self.logger.info(f"获取目录列表: '{path}' -> '{normalized_path}'")
            
            # 检查telnet客户端是否存在
            if not self.telnet_client:
                self.logger.error("Telnet客户端不存在")
                return []
            
            # 使用锁保护telnet连接
            async with self.telnet_lock:
                # 首先检查路径是否是目录
                test_result = await self.telnet_client.execute_command(f'test -d "{normalized_path}" && echo "IS_DIR" || echo "NOT_DIR"')
                self.logger.info(f"目录检查结果: {test_result.strip()}")
                
                if "NOT_DIR" in test_result:
                    self.logger.warning(f"路径 {normalized_path} 不是目录，无法列出内容")
                    return []
                
                # 尝试使用带颜色的ls命令获取文件类型信息
                self.logger.info(f'执行命令: ls -la --color=always "{normalized_path}"')
                result = await self.telnet_client.execute_command(f'ls -la --color=always "{normalized_path}"')
            
            # 记录原始输出用于调试
            self.logger.info(f"命令输出长度: {len(result)} 字符")
            self.logger.debug(f"原始ls输出（前100字符）: {repr(result[:100])}")
            
            # 清理ANSI转义序列
            cleaned_result = self._clean_ansi_codes(result)
            self.logger.debug(f"清理后输出（前100字符）: {repr(cleaned_result[:100])}")
            
            items = []
            lines = cleaned_result.strip().split('\n')
            self.logger.info(f"解析出 {len(lines)} 行输出")
            
            # 跳过第一行（通常是"total xxx"）
            for i, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue
                
                # 跳过总计行
                if i == 0 and line.startswith('total'):
                    self.logger.debug(f"跳过总计行: {line}")
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
                        is_executable = 'x' in permissions[1:4] and not is_directory
                        is_link = permissions.startswith('l')
                        
                        # 根据权限和类型确定文件类型
                        file_type = self._determine_file_type(permissions, name)
                        
                        items.append({
                            'name': name,
                            'is_directory': is_directory,
                            'is_executable': is_executable,
                            'is_link': is_link,
                            'file_type': file_type,
                            'permissions': permissions,
                            'full_path': self._join_unix_path(path, name)
                        })
                        self.logger.debug(f"解析到项目: {name} ({'目录' if is_directory else file_type})")
                else:
                    self.logger.debug(f"跳过格式异常行: {repr(line)}")
            
            self.logger.info(f"成功解析到 {len(items)} 个项目")
            return items
            
        except Exception as e:
            self.logger.warning(f"--color=always失败: {str(e)}")
            # 如果--color=always不支持，尝试普通ls命令
            try:
                # 备用方法也需要锁保护
                async with self.telnet_lock:
                    self.logger.info(f"尝试普通ls命令: ls -la \"{normalized_path}\"")
                    result = await self.telnet_client.execute_command(f'ls -la "{normalized_path}"')
                self.logger.info(f"普通ls输出长度: {len(result)} 字符")
                self.logger.debug(f"普通ls原始输出（前100字符）: {repr(result[:100])}")
                
                cleaned_result = self._clean_ansi_codes(result)
                self.logger.debug(f"普通ls清理后输出（前100字符）: {repr(cleaned_result[:100])}")
                
                items = []
                lines = cleaned_result.strip().split('\n')
                self.logger.info(f"普通ls解析出 {len(lines)} 行")
                
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
                                'full_path': self._join_unix_path(normalized_path, name)
                            })
                            self.logger.debug(f"解析到项目: {name} ({'目录' if is_directory else '文件'})")
                
                self.logger.info(f"备用方法成功解析到 {len(items)} 个项目")
                return items
                
            except Exception as e2:
                self.logger.error(f"所有方法都失败: {str(e2)}")
                import traceback
                self.logger.error(f"详细错误: {traceback.format_exc()}")
                return []
    
    def _update_directory_tree(self, items):
        """更新目录树 - 修复重复显示和颜色问题"""
        try:
            self.logger.info(f"开始更新目录树，收到 {len(items)} 个项目")
            
            # 检查目录树组件是否存在
            if not hasattr(self, 'directory_tree') or not self.directory_tree:
                self.logger.error("目录树组件不存在")
                return
            
            # 清空现有项目
            try:
                current_children = self.directory_tree.get_children()
                self.logger.debug(f"清空现有的 {len(current_children)} 个项目")
                self.directory_tree.delete(*current_children)
            except Exception as clear_error:
                self.logger.error(f"清空目录树失败: {clear_error}")
                return
            
            # 先配置颜色标签
            self._configure_tree_colors()
            
            # 添加新项目 - 简化版本，避免重复
            added_count = 0
            for i, item in enumerate(items):
                try:
                    # 根据文件类型选择图标
                    icon, color = self._get_file_icon_and_color(item)
                    display_name = f"{icon} {item['name']}"
                    
                    # 确定标签类型
                    if item.get('is_directory', False):
                        tag = 'directory'
                    elif item.get('is_executable', False):
                        tag = 'executable'
                    elif item.get('is_link', False):
                        tag = 'link'
                    else:
                        file_type = item.get('file_type', 'file')
                        tag = file_type
                    
                    # 插入到树中，直接设置标签
                    # 确保 is_directory 是明确的布尔值
                    is_directory_value = bool(item.get('is_directory', False))
                    tree_item = self.directory_tree.insert('', 'end', 
                                                         text=display_name,
                                                         values=(item['full_path'], is_directory_value, item.get('is_executable', False)),
                                                         tags=(tag,))
                    
                    added_count += 1
                    self.logger.debug(f"成功添加项目: {display_name} (标签: {tag})")
                    
                except Exception as item_error:
                    self.logger.error(f"添加项目失败 {item['name']}: {str(item_error)}")
                    # 如果添加失败，尝试最简单的版本（不设置颜色）
                    try:
                        simple_name = item['name']
                        tree_item = self.directory_tree.insert('', 'end', 
                                                             text=simple_name,
                                                             values=(item['full_path'], item.get('is_directory', False)))
                        added_count += 1
                        self.logger.debug(f"简化版本成功添加: {simple_name}")
                    except Exception as simple_error:
                        self.logger.error(f"简化版本也失败: {str(simple_error)}")
            
            # 检查最终结果
            children_count = len(self.directory_tree.get_children())
            self.logger.info(f"目录树更新完成，显示 {children_count} 个项目，成功添加 {added_count} 个")
            
            # 更新状态栏
            if children_count > 0:
                self._update_status(f"目录刷新完成，显示 {children_count} 个项目 - 路径: {self.current_remote_path}")
            else:
                self._update_status(f"目录为空 - 路径: {self.current_remote_path}")
                
            # 首次目录刷新完毕后，触发设备ID读取任务
            if getattr(self, 'is_connected', False) and not getattr(self, 'device_id_task_started', False):
                if hasattr(self, '_pending_device_id_ip') and self._pending_device_id_ip and self.telnet_client:
                    self.device_id_task_started = True
                    def _start_read_id():
                        fut = self._run_async(self._save_ip_with_device_id(self._pending_device_id_ip))
                        if fut:
                            fut.add_done_callback(lambda f: self.logger.info("设备ID读取任务完成"))
                    # 短暂延迟 100ms 确保 UI 空闲
                    self.root.after(100, _start_read_id)
                
        except Exception as e:
            self.logger.error(f"更新目录树失败: {str(e)}")
            import traceback
            self.logger.error(f"完整错误信息: {traceback.format_exc()}")
            # 更新状态栏显示错误
            self._update_status(f"目录树更新失败: {str(e)}")
    
    def _on_directory_double_click(self, event):
        """目录双击事件"""
        selection = self.directory_tree.selection()
        if selection:
            item = self.directory_tree.item(selection[0])
            values = item['values']
            if len(values) >= 3:
                full_path, is_directory, is_exec = values[0], values[1], values[2]
            else:
                full_path, is_directory = values[0], values[1]
                is_exec = False
            
            self.logger.debug(f"双击项目: {full_path}, 是否为目录: {is_directory}")
            
            # 使用统一的判断逻辑
            is_dir = self._is_directory_item(is_directory)
            
            if is_dir:
                self.current_remote_path = self._normalize_unix_path(full_path)
                self.current_path_var.set(self.current_remote_path)
                self._refresh_directory()
                # 更新队列显示以反映新的目标路径
                self._update_queue_display()
            else:
                # 判断是否可编辑：非可执行文件 或 明确文本扩展名
                filename_lower = full_path.lower()
                editable_by_ext = any(filename_lower.endswith(ext) for ext in [".ini", ".txt", ".log", ".sh"]) or "log" in filename_lower or "ini" in filename_lower
                if (not is_exec) or editable_by_ext:
                    self._open_remote_file_editor(full_path)
                elif any(filename_lower.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".gif", ".bmp"]):
                    self._open_image_preview(full_path)
                else:
                    self.logger.info(f"双击了文件: {full_path}，非可编辑类型，忽略")
    
    def _on_directory_select(self, event):
        """目录选择事件"""
        selection = self.directory_tree.selection()
        if selection:
            item = self.directory_tree.item(selection[0])
            values = item['values']
            if len(values) >= 3:
                full_path, is_directory, is_exec = values[0], values[1], values[2]
            else:
                full_path, is_directory = values[0], values[1]
                is_exec = False
            
            # 添加调试日志
            self.logger.debug(f"选择项目: {full_path}, 是否为目录: {is_directory} (类型: {type(is_directory)})")
            self.logger.debug(f"原始值: {repr(is_directory)}")
            
            # 使用统一的判断方法
            is_dir = self._is_directory_item(is_directory)
            self.logger.debug(f"最终判断结果: is_dir = {is_dir}")
            
            if is_dir:
                # 选择的是目录，禁用删除按钮
                self.delete_file_button.configure(state='disabled')
                self.logger.debug("选择了目录，删除按钮已禁用")
                # 不要自动改变当前路径，让用户双击才进入
            else:
                # 选择的是文件，启用删除按钮
                self.delete_file_button.configure(state='normal')
                self.logger.debug("选择了文件，删除按钮已启用")
        else:
            # 没有选择任何项目，禁用删除按钮
            self.delete_file_button.configure(state='disabled')
            self.logger.debug("没有选择项目，删除按钮已禁用")
    
    def _go_parent_directory(self):
        """上级目录"""
        if self.current_remote_path != '/':
            parent_path = self._get_unix_parent_path(self.current_remote_path)
            self.current_remote_path = parent_path
            self.current_path_var.set(parent_path)
            self._refresh_directory()
            # 更新队列显示以反映新的目标路径
            self._update_queue_display()
    
    def _get_unix_parent_path(self, path):
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
    
    def _join_unix_path(self, base_path, name):
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
    
    def _normalize_unix_path(self, path):
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
    
    def _is_directory_item(self, is_directory_value):
        """统一的目录判断方法"""
        if isinstance(is_directory_value, bool):
            return is_directory_value
        elif isinstance(is_directory_value, str):
            return is_directory_value.lower() in ['true', '1', 'yes']
        elif isinstance(is_directory_value, (int, float)):
            return bool(is_directory_value)
        else:
            return False  # 默认为文件
    
    def _create_adaptive_dialog(self, title, icon="ℹ️", min_width=400, min_height=250):
        """创建自适应大小的对话框"""
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.configure(bg=self.colors['bg_primary'])
        dialog.resizable(False, False)
        
        # 设置对话框始终在最前面
        dialog.attributes('-topmost', True)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 创建内容容器
        content_frame = tk.Frame(dialog, bg=self.colors['bg_primary'])
        content_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # 图标
        icon_label = tk.Label(content_frame, text=icon, font=('Microsoft YaHei UI', 32),
                            bg=self.colors['bg_primary'], fg=self.colors['warning'])
        icon_label.pack(pady=(0, 15))
        
        # 返回内容框架和对话框，供调用者添加内容
        return dialog, content_frame
    
    def _finalize_adaptive_dialog(self, dialog, min_width=400, min_height=250):
        """完成自适应对话框的布局和定位"""
        # 让对话框根据内容自动调整大小
        dialog.update_idletasks()
        
        # 获取对话框的实际大小
        dialog_width = dialog.winfo_reqwidth()
        dialog_height = dialog.winfo_reqheight()
        
        # 设置最小尺寸
        dialog_width = max(dialog_width, min_width)
        dialog_height = max(dialog_height, min_height)
        
        # 获取主窗口位置和大小
        self.root.update_idletasks()
        main_x = self.root.winfo_x()
        main_y = self.root.winfo_y()
        main_width = self.root.winfo_width()
        main_height = self.root.winfo_height()
        
        # 计算居中位置
        x = main_x + (main_width - dialog_width) // 2
        y = main_y + (main_height - dialog_height) // 2
        
        # 确保对话框不会超出屏幕边界
        screen_width = dialog.winfo_screenwidth()
        screen_height = dialog.winfo_screenheight()
        x = max(0, min(x, screen_width - dialog_width))
        y = max(0, min(y, screen_height - dialog_height))
        
        # 设置对话框位置和大小
        dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
    
    def _show_adaptive_info_dialog(self, title, message, icon="ℹ️"):
        """显示自适应信息对话框"""
        dialog, content_frame = self._create_adaptive_dialog(title, icon)
        
        # 消息文本 - 使用wraplength自动换行
        message_label = tk.Label(content_frame, text=message, 
                               font=('Microsoft YaHei UI', 10),
                               bg=self.colors['bg_primary'], fg=self.colors['text_primary'],
                               justify='left', wraplength=450)
        message_label.pack(pady=(0, 20))
        
        # 确定按钮
        ok_button = tk.Button(content_frame, text="确定", 
                            command=dialog.destroy,
                            bg=self.colors['bg_button'], fg='#ffffff',
                            font=('Microsoft YaHei UI', 11, 'bold'),
                            relief='flat', borderwidth=0, cursor='hand2',
                            padx=30, pady=8)
        ok_button.pack()
        
        # 绑定ESC键关闭
        dialog.bind('<Escape>', lambda e: dialog.destroy())
        ok_button.focus_set()
        
        # 完成对话框布局
        self._finalize_adaptive_dialog(dialog)
        
        # 等待对话框关闭
        self.root.wait_window(dialog)
    
    def _delete_selected_file(self):
        """删除选中的文件"""
        if not self.is_connected:
            messagebox.showerror("未连接", "请先连接设备")
            return
        
        # 获取选中的项目
        selection = self.directory_tree.selection()
        if not selection:
            messagebox.showwarning("未选择", "请先选择要删除的文件")
            return
        
        item = self.directory_tree.item(selection[0])
        full_path, is_directory = item['values']
        filename = item['text']
        
        # 添加调试日志
        self.logger.debug(f"删除操作 - 选择项目: {full_path}, 是否为目录: {is_directory} (类型: {type(is_directory)})")
        
        # 使用统一的判断方法
        is_dir = self._is_directory_item(is_directory)
        self.logger.debug(f"删除操作 - 最终判断结果: is_dir = {is_dir}")
        
        # 确保选择的是文件而不是目录
        if is_dir:
            messagebox.showwarning("无法删除", "不能删除目录，只能删除文件")
            return
        
        # 移除图标，只显示文件名
        clean_filename = filename
        if ' ' in filename and any(icon in filename for icon in ['📄', '🖼️', '📦', '⚙️', '📜', '🔗']):
            clean_filename = filename.split(' ', 1)[1] if ' ' in filename else filename
        
        # 显示居中的确认对话框
        if self._show_centered_confirm_dialog("确认删除", 
                                            f"确定要删除文件吗？\n\n文件名: {clean_filename}\n路径: {full_path}\n\n此操作不可撤销！"):
            # 执行删除操作
            self._execute_file_deletion(full_path, clean_filename)
    
    def _show_centered_confirm_dialog(self, title, message):
        """显示居中的确认对话框 - 自适应布局"""
        # 创建自定义对话框
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.configure(bg=self.colors['bg_primary'])
        dialog.resizable(False, False)
        
        # 设置对话框始终在最前面
        dialog.attributes('-topmost', True)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 用户选择结果
        result = {'confirmed': False}
        
        # 创建内容容器
        content_frame = tk.Frame(dialog, bg=self.colors['bg_primary'])
        content_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # 图标
        icon_label = tk.Label(content_frame, text="⚠️", font=('Microsoft YaHei UI', 32),
                            bg=self.colors['bg_primary'], fg=self.colors['warning'])
        icon_label.pack(pady=(0, 15))
        
        # 消息文本 - 使用wraplength自动换行
        message_label = tk.Label(content_frame, text=message, 
                               font=('Microsoft YaHei UI', 11),
                               bg=self.colors['bg_primary'], fg=self.colors['text_primary'],
                               justify='center', wraplength=350)
        message_label.pack(pady=(0, 25))
        
        # 按钮区域
        button_frame = tk.Frame(content_frame, bg=self.colors['bg_primary'])
        button_frame.pack(pady=(0, 0))
        
        def on_confirm():
            result['confirmed'] = True
            dialog.destroy()
        
        def on_cancel():
            result['confirmed'] = False
            dialog.destroy()
        
        # 确认按钮
        confirm_btn = tk.Button(button_frame, text="确认删除", 
                               command=on_confirm,
                               bg=self.colors['error'], fg='#ffffff',
                               font=('Microsoft YaHei UI', 11, 'bold'),
                               relief='flat', borderwidth=0, cursor='hand2',
                               padx=25, pady=8)
        confirm_btn.pack(side=tk.LEFT, padx=(0, 15))
        
        # 取消按钮
        cancel_btn = tk.Button(button_frame, text="取消", 
                              command=on_cancel,
                              bg=self.colors['text_muted'], fg='#ffffff',
                              font=('Microsoft YaHei UI', 11),
                              relief='flat', borderwidth=0, cursor='hand2',
                              padx=25, pady=8)
        cancel_btn.pack(side=tk.LEFT)
        
        # 绑定ESC键取消
        dialog.bind('<Escape>', lambda e: on_cancel())
        
        # 设置默认焦点到取消按钮（安全起见）
        cancel_btn.focus_set()
        
        # 让对话框根据内容自动调整大小
        dialog.update_idletasks()
        
        # 获取对话框的实际大小
        dialog_width = dialog.winfo_reqwidth()
        dialog_height = dialog.winfo_reqheight()
        
        # 设置最小尺寸
        min_width = 400
        min_height = 250
        dialog_width = max(dialog_width, min_width)
        dialog_height = max(dialog_height, min_height)
        
        # 获取主窗口位置和大小
        self.root.update_idletasks()
        main_x = self.root.winfo_x()
        main_y = self.root.winfo_y()
        main_width = self.root.winfo_width()
        main_height = self.root.winfo_height()
        
        # 计算居中位置
        x = main_x + (main_width - dialog_width) // 2
        y = main_y + (main_height - dialog_height) // 2
        
        # 设置对话框位置和大小
        dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        
        # 等待对话框关闭
        self.root.wait_window(dialog)
        
        return result['confirmed']
    
    def _execute_file_deletion(self, file_path, filename):
        """执行文件删除操作"""
        try:
            self.logger.info(f"开始删除文件: {file_path}")
            self._update_status(f"正在删除文件: {filename}")
            
            # 在后台线程中执行删除
            threading.Thread(target=self._delete_file_async, args=(file_path, filename), daemon=True).start()
            
        except Exception as e:
            self.logger.error(f"删除文件失败: {e}")
            self._update_status(f"删除文件失败: {str(e)}")
    
    def _delete_file_async(self, file_path, filename):
        """异步删除文件"""
        try:
            future = self._run_async(self._delete_file_via_telnet(file_path, filename))
            if future:
                # 使用回调处理结果
                future.add_done_callback(lambda f: self._on_delete_result(f, filename))
            else:
                self.root.after(0, lambda: self._update_status("无法创建删除任务"))
                
        except Exception as e:
            self.logger.error(f"异步删除文件失败: {e}")
            self.root.after(0, lambda: self._update_status(f"删除失败: {str(e)}"))
    
    def _on_delete_result(self, future, filename):
        """处理删除结果回调"""
        try:
            success = future.result()
            if success:
                self.root.after(0, lambda: self._on_delete_success(filename))
            else:
                self.root.after(0, lambda: self._on_delete_failed(filename))
        except Exception as e:
            self.logger.error(f"删除结果处理失败: {e}")
            self.root.after(0, lambda: self._on_delete_failed(filename))
    
    def _on_delete_success(self, filename):
        """删除成功"""
        self.logger.info(f"文件删除成功: {filename}")
        self._update_status(f"文件删除成功: {filename}")
        
        # 自动刷新目录以更新显示
        self._refresh_directory()
        
        # 禁用删除按钮（因为选择会丢失）
        self.delete_file_button.configure(state='disabled')
    
    def _on_delete_failed(self, filename):
        """删除失败"""
        self.logger.error(f"文件删除失败: {filename}")
        self._update_status(f"文件删除失败: {filename}")
        messagebox.showerror("删除失败", f"无法删除文件: {filename}")
    
    async def _delete_file_via_telnet(self, file_path, filename):
        """通过telnet删除文件"""
        try:
            # 使用锁保护telnet连接
            async with self.telnet_lock:
                # 执行删除命令
                delete_cmd = f'rm "{file_path}"'
                self.logger.info(f"执行删除命令: {delete_cmd}")
                result = await self.telnet_client.execute_command(delete_cmd, timeout=10)
                self.logger.info(f"删除命令输出: {result}")
                
                # 检查删除是否成功（通过检查文件是否还存在）
                check_cmd = f'ls "{file_path}" 2>/dev/null || echo "FILE_NOT_FOUND"'
                check_result = await self.telnet_client.execute_command(check_cmd, timeout=5)
                self.logger.info(f"删除检查结果: {check_result}")
                
                # 如果文件不存在，说明删除成功
                if "FILE_NOT_FOUND" in check_result or "No such file" in check_result:
                    return True
                else:
                    return False
                    
        except Exception as e:
            self.logger.error(f"telnet删除文件失败: {str(e)}")
            return False
    
    def _debug_selection_status(self):
        """调试选择状态"""
        self.logger.info("🔍 开始调试选择状态")
        
        selection = self.directory_tree.selection()
        if selection:
            item = self.directory_tree.item(selection[0])
            full_path, is_directory = item['values']
            filename = item['text']
            
            # 详细输出调试信息
            self.logger.info(f"📁 选中项目详情:")
            self.logger.info(f"   - 显示名称: {filename}")
            self.logger.info(f"   - 完整路径: {full_path}")
            self.logger.info(f"   - 是否为目录: {is_directory} (类型: {type(is_directory)})")
            self.logger.info(f"   - 原始值: {repr(is_directory)}")
            
            # 判断逻辑测试
            is_dir = self._is_directory_item(is_directory)
            if isinstance(is_directory, bool):
                logic_used = "直接布尔值"
            elif isinstance(is_directory, str):
                logic_used = "字符串转换"
            elif isinstance(is_directory, (int, float)):
                logic_used = "数值转换"
            else:
                logic_used = "默认为文件"
            
            self.logger.info(f"   - 判断逻辑: {logic_used}")
            self.logger.info(f"   - 最终结果: {'目录' if is_dir else '文件'}")
            
            # 按钮状态
            button_state = self.delete_file_button['state']
            self.logger.info(f"   - 删除按钮状态: {button_state}")
            
            # 当前路径
            self.logger.info(f"   - 当前远程路径: {self.current_remote_path}")
            
            # 显示在自适应对话框中
            debug_info = f"""选中项目调试信息:

显示名称: {filename}
完整路径: {full_path}
是否为目录: {is_directory} ({type(is_directory).__name__})
判断逻辑: {logic_used}
最终结果: {'目录' if is_dir else '文件'}
删除按钮状态: {button_state}
当前远程路径: {self.current_remote_path}

详细信息请查看日志区域"""
            
            self._show_adaptive_info_dialog("选择状态调试", debug_info, "🔍")
        else:
            self.logger.info("❌ 没有选中任何项目")
            self._show_adaptive_info_dialog("选择状态调试", "没有选中任何项目", "❌")
    
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
            
            # 使用锁保护telnet连接
            async with self.telnet_lock:
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
                self.logger.debug(f"原始拖拽数据: {repr(data)}")
                
                # 处理不同的拖拽数据格式
                if '{' in data and '}' in data:
                    # 格式: {path1} {path2} ...
                    # 这种格式需要特殊处理，因为路径可能包含空格
                    import re
                    # 匹配被大括号包围的路径
                    paths = re.findall(r'\{([^}]+)\}', data)
                    self.logger.debug(f"从大括号格式解析到路径: {paths}")
                    
                    for path in paths:
                        path = path.strip().replace('\\', '/')
                        self.logger.debug(f"检查路径: {path}")
                        if os.path.exists(path):
                            if os.path.isfile(path):
                                files.append(path)
                                self.logger.debug(f"添加文件: {path}")
                            elif os.path.isdir(path):
                                self.logger.info(f"检测到目录: {path}，查找其中的文件")
                                # 如果是目录，列出其中的文件
                                try:
                                    for item in os.listdir(path):
                                        item_path = os.path.join(path, item)
                                        if os.path.isfile(item_path):
                                            files.append(item_path)
                                            self.logger.debug(f"从目录添加文件: {item_path}")
                                except Exception as dir_error:
                                    self.logger.error(f"读取目录失败: {dir_error}")
                        else:
                            self.logger.warning(f"路径不存在: {path}")
                else:
                    # 简单格式，尝试按空格分割（对于不包含空格的路径）
                    file_paths = data.replace('\\', '/').split()
                    self.logger.debug(f"按空格分割得到路径: {file_paths}")
                    
                    for path in file_paths:
                        path = path.strip('{}').strip()
                        self.logger.debug(f"检查路径: {path}")
                        if os.path.exists(path):
                            if os.path.isfile(path):
                                files.append(path)
                                self.logger.debug(f"添加文件: {path}")
                            elif os.path.isdir(path):
                                self.logger.info(f"检测到目录: {path}，查找其中的文件")
                                try:
                                    for item in os.listdir(path):
                                        item_path = os.path.join(path, item)
                                        if os.path.isfile(item_path):
                                            files.append(item_path)
                                            self.logger.debug(f"从目录添加文件: {item_path}")
                                except Exception as dir_error:
                                    self.logger.error(f"读取目录失败: {dir_error}")
                        else:
                            self.logger.warning(f"路径不存在: {path}")
                
                self.logger.info(f"最终解析到 {len(files)} 个文件")
                
        except Exception as e:
            self.logger.error(f"解析文件失败: {str(e)}")
            import traceback
            self.logger.error(f"详细错误: {traceback.format_exc()}")
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
                # 只显示文件名，不固定路径，传输时使用当前最新路径
                display_text = f"{filename} -> (当前目录)"
                self.queue_listbox.insert(tk.END, display_text)
                self.file_path_mapping[filename] = file_path
                added_count += 1
                self.logger.info(f"已添加文件: {filename}")
            else:
                self.logger.warning(f"文件不存在或不是文件: {file_path}")
        
        if added_count > 0:
            self.logger.info(f"成功添加 {added_count} 个文件到队列")
            self._update_status(f"已添加 {added_count} 个文件到队列 (将传输到当前目录)")
            self._update_queue_count()
            # 更新队列显示，显示当前路径
            self._update_queue_display()
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
    
    def _update_queue_display(self):
        """更新队列显示，显示最新的当前路径"""
        try:
            queue_size = self.queue_listbox.size()
            if queue_size == 0:
                return
            
            # 获取所有文件名
            filenames = []
            for i in range(queue_size):
                item_text = self.queue_listbox.get(i)
                # 提取文件名（在 -> 之前的部分）
                if " -> " in item_text:
                    filename = item_text.split(" -> ")[0]
                    filenames.append(filename)
                else:
                    filenames.append(item_text)
            
            # 清空队列
            self.queue_listbox.delete(0, tk.END)
            
            # 重新添加，使用当前路径
            for filename in filenames:
                display_text = f"{filename} -> {self.current_remote_path}"
                self.queue_listbox.insert(tk.END, display_text)
                
            self.logger.debug(f"队列显示已更新，当前目标路径: {self.current_remote_path}")
            
        except Exception as e:
            self.logger.error(f"更新队列显示失败: {str(e)}")
            # 如果更新失败，保持原有显示
    
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
            self.logger.error("HTTP服务器未启动，尝试启动...")
            self._start_http_server_delayed()
            # 等待一下服务器启动
            self.root.after(1000, self._retry_start_transfer)
            return
        
        # 验证HTTP服务器是否真的在运行
        if not self.http_server.is_running:
            self.logger.error("HTTP服务器未运行，尝试重新启动...")
            self._start_http_server_delayed()
            self.root.after(1000, self._retry_start_transfer)
            return
        
        self.logger.info(f"开始传输 {self.queue_listbox.size()} 个文件")
        self.logger.info(f"HTTP服务器状态: 运行中，端口 {self.http_server.port}")
        self.start_transfer_button.configure(state='disabled', text='传输中...')
        threading.Thread(target=self._transfer_files_async, daemon=True).start()
    
    def _retry_start_transfer(self):
        """重试开始传输（给HTTP服务器启动时间）"""
        try:
            if self.http_server and self.http_server.is_running:
                self.logger.info("HTTP服务器已启动，开始传输...")
                self._start_transfer()
            else:
                self.logger.error("HTTP服务器启动失败")
                messagebox.showerror("错误", "HTTP服务器启动失败，无法进行文件传输")
        except Exception as e:
            self.logger.error(f"重试传输失败: {e}")
            messagebox.showerror("错误", f"传输启动失败: {str(e)}")
    
    def _transfer_files_async(self):
        """异步传输文件 - 修复版本，避免UI阻塞"""
        try:
            # 收集所有要传输的文件信息
            transfer_tasks = []
            total_count = self.queue_listbox.size()
            
            # 使用当前最新的远程路径，而不是队列中显示的路径
            current_remote_path = self.current_remote_path
            self.logger.info(f"开始传输文件到当前路径: {current_remote_path}")
            
            for i in range(total_count):
                item_text = self.queue_listbox.get(i)
                parts = item_text.split(" -> ")
                if len(parts) >= 1:
                    filename = parts[0]
                    
                    if filename in self.file_path_mapping:
                        local_file = self.file_path_mapping[filename]
                        # 使用当前最新路径，而不是队列中存储的路径
                        transfer_tasks.append((local_file, current_remote_path, filename))
                        self.logger.debug(f"准备传输: {filename} -> {current_remote_path}")
            
            if not transfer_tasks:
                self.logger.warning("没有找到可传输的文件")
                self.root.after(0, self._on_transfer_error, "队列中没有可传输的文件")
                return
            
            # 使用回调方式避免阻塞UI
            future = self._run_async(self._execute_transfers_sequentially(transfer_tasks))
            if future:
                # 使用回调而不是阻塞等待
                future.add_done_callback(lambda f: self._on_transfer_result(f, len(transfer_tasks)))
            else:
                self.root.after(0, self._on_transfer_error, "无法创建异步传输任务")
            
        except Exception as e:
            self.logger.error(f"文件传输异常: {str(e)}")
            import traceback
            self.logger.error(f"详细错误: {traceback.format_exc()}")
            self.root.after(0, self._on_transfer_error, str(e))
    
    def _on_transfer_result(self, future, total_count):
        """处理传输结果回调"""
        try:
            success_count = future.result()
            self.root.after(0, self._on_transfer_complete, success_count, total_count)
        except Exception as e:
            self.logger.error(f"传输结果处理失败: {e}")
            self.root.after(0, self._on_transfer_error, str(e))
    
    async def _execute_transfers_sequentially(self, transfer_tasks):
        """串行执行传输任务，避免telnet连接冲突"""
        success_count = 0
        
        for i, (local_file, remote_path, filename) in enumerate(transfer_tasks, 1):
            self.logger.info(f"开始传输文件 {i}/{len(transfer_tasks)}: {filename}")
            
            try:
                # 使用锁确保telnet连接不会被并发访问
                async with self.telnet_lock:
                    if await self._transfer_single_file_async(local_file, remote_path, filename):
                        success_count += 1
                        self.logger.info(f"文件传输成功: {filename}")
                    else:
                        self.logger.error(f"文件传输失败: {filename}")
                        
            except Exception as e:
                self.logger.error(f"传输文件 {filename} 时出错: {str(e)}")
                import traceback
                self.logger.error(f"详细错误: {traceback.format_exc()}")
        
        return success_count
    
    async def _transfer_single_file_async(self, local_file, remote_path, filename):
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
            
            # 验证文件是否真的添加成功
            if not os.path.exists(server_file_path):
                self.logger.error(f"文件添加后不存在: {server_file_path}")
                return False
            
            # 获取实际的文件名（可能被重命名了）
            actual_filename = os.path.basename(server_file_path)
            self.logger.info(f"实际文件名: {actual_filename}")
            
            # 获取下载URL（使用实际文件名）
            host_ip = self._get_local_ip()
            download_url = self.http_server.get_download_url(actual_filename, host_ip)
            self.logger.info(f"生成下载URL: {download_url}")
            
            # 验证HTTP服务器能否访问该文件
            self._verify_http_server_file(actual_filename)
            
            # 测试HTTP服务器连通性
            await self._test_http_server_connectivity(download_url)
            
            # 通过telnet下载
            self.logger.info(f"开始通过telnet执行下载命令")
            result = await self._download_via_telnet(download_url, remote_path, actual_filename)
            
            # 清理临时文件
            self.http_server.remove_file(actual_filename)
            
            return result
            
        except Exception as e:
            self.logger.error(f"异步传输文件失败: {str(e)}")
            import traceback
            self.logger.error(f"详细错误: {traceback.format_exc()}")
            return False
    
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
            
            # 获取下载URL（使用HTTP服务器的方法，确保正确编码）
            host_ip = self._get_local_ip()
            download_url = self.http_server.get_download_url(filename, host_ip)
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
    
    def _verify_http_server_file(self, filename):
        """验证HTTP服务器上的文件"""
        try:
            # 检查临时目录中的文件
            temp_dir = self.http_server.temp_dir
            file_path = os.path.join(temp_dir, filename)
            
            self.logger.info(f"验证HTTP服务器文件:")
            self.logger.info(f"  - 临时目录: {temp_dir}")
            self.logger.info(f"  - 文件路径: {file_path}")
            self.logger.info(f"  - 文件存在: {os.path.exists(file_path)}")
            
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                self.logger.info(f"  - 文件大小: {file_size} bytes")
            
            # 列出临时目录中的所有文件
            try:
                files_in_temp = os.listdir(temp_dir)
                self.logger.info(f"  - 临时目录文件列表: {files_in_temp}")
            except Exception as e:
                self.logger.error(f"  - 无法列出临时目录: {e}")
                
        except Exception as e:
            self.logger.error(f"验证HTTP服务器文件失败: {e}")
    
    async def _test_http_server_connectivity(self, download_url):
        """测试HTTP服务器连通性"""
        try:
            self.logger.info(f"测试HTTP服务器连通性:")
            self.logger.info(f"  - 下载URL: {download_url}")
            self.logger.info(f"  - HTTP服务器运行状态: {self.http_server.is_running}")
            self.logger.info(f"  - HTTP服务器端口: {self.http_server.port}")
            
            # 检查端口是否被占用
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                result = s.connect_ex(('127.0.0.1', self.http_server.port))
                if result == 0:
                    self.logger.info(f"  - 端口 {self.http_server.port} 可连接")
                else:
                    self.logger.error(f"  - 端口 {self.http_server.port} 不可连接")
            
            # 尝试从远程设备ping本机
            local_ip = self._get_local_ip()
            self.logger.info(f"  - 本机IP: {local_ip}")
            
            ping_cmd = f"ping -c 1 {local_ip}"
            self.logger.info(f"  - 测试远程设备到本机连通性: {ping_cmd}")
            ping_result = await self.telnet_client.execute_command(ping_cmd, timeout=10)
            self.logger.info(f"  - Ping结果: {ping_result.strip()}")
            
            # 检查ping是否成功
            success_indicators = ['1 packets transmitted, 1 received', '1 received', '0% packet loss']
            ping_success = any(indicator in ping_result for indicator in success_indicators)
            self.logger.info(f"  - 网络连通性: {'正常' if ping_success else '异常'}")
            
        except Exception as e:
            self.logger.error(f"测试HTTP服务器连通性失败: {e}")
            import traceback
            self.logger.error(f"详细错误: {traceback.format_exc()}")
    
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
    
    async def _save_ip_with_device_id(self, ip):
        """保存IP地址和设备ID到历史记录"""
        try:
            # 读取设备ID
            device_id = await read_device_id_from_remote(self.telnet_client)
            self.current_device_id = device_id
            
            # 保存到历史记录
            self.ip_history_manager.add_ip(ip, device_id)
            
            if device_id:
                self.logger.info(f"已保存IP历史记录: {ip} (设备: {device_id})")
                try:
                    # 在主线程中更新显示
                    self.root.after(0, lambda: (self.device_id_var.set(device_id), self._adjust_ip_id_width()))
                except Exception:
                    pass
            else:
                self.logger.info(f"已保存IP历史记录: {ip} (无设备ID)")
                
        except Exception as e:
            self.logger.error(f"保存IP历史记录失败: {str(e)}")
    
    def _load_last_ip(self):
        """加载最后使用的IP"""
        try:
            last_ip = self.ip_history_manager.get_last_used_ip()
            if last_ip:
                self.host_var.set(last_ip)
                # 同步设备ID显示
                self._sync_device_id_display(last_ip)
                self.logger.info(f"已加载最后使用的IP: {last_ip}")
        except Exception as e:
            self.logger.debug(f"加载最后使用IP失败: {e}")
    
    def _show_ip_history(self):
        """显示IP历史记录选择窗口"""
        try:
            # 创建历史记录窗口
            history_window = tk.Toplevel(self.root)
            history_window.title("IP历史记录")
            history_window.geometry("400x300")
            history_window.configure(bg=self.colors['bg_primary'])
            history_window.transient(self.root)
            history_window.grab_set()
            
            # 居中窗口
            self._center_toplevel(history_window, 400, 300)
            
            # 标题
            title_label = tk.Label(history_window, text="选择历史IP地址", 
                                 bg=self.colors['bg_primary'], fg=self.colors['text_primary'],
                                 font=('Microsoft YaHei UI', 12, 'bold'))
            title_label.pack(pady=10)
            
            # 历史记录列表
            listbox_frame = tk.Frame(history_window, bg=self.colors['bg_primary'])
            listbox_frame.pack(fill='both', expand=True, padx=20, pady=(0, 10))
            
            history_listbox = tk.Listbox(listbox_frame, 
                                       bg=self.colors['bg_card'], fg=self.colors['text_primary'],
                                       font=('Microsoft YaHei UI', 9),
                                       selectbackground=self.colors['bg_accent_light'])
            history_listbox.pack(side='left', fill='both', expand=True)
            
            scrollbar = tk.Scrollbar(listbox_frame, orient='vertical', command=history_listbox.yview)
            scrollbar.pack(side='right', fill='y')
            history_listbox.configure(yscrollcommand=scrollbar.set)
            
            # 加载历史记录
            suggestions = self.ip_history_manager.get_ip_suggestions()
            for suggestion in suggestions:
                history_listbox.insert(tk.END, suggestion['display_text'])
            
            # 按钮区域
            button_frame = tk.Frame(history_window, bg=self.colors['bg_primary'])
            button_frame.pack(fill='x', padx=20, pady=(0, 20))
            
            def on_select():
                selection = history_listbox.curselection()
                if selection:
                    selected_suggestion = suggestions[selection[0]]
                    ip = selected_suggestion['ip']
                    self.host_var.set(ip)
                    history_window.destroy()
            
            def on_cancel():
                history_window.destroy()
            
            # 按钮
            select_button = tk.Button(button_frame, text="选择", 
                                    command=on_select,
                                    bg=self.colors['bg_button'], fg=self.colors['text_button'],
                                    font=('Microsoft YaHei UI', 9),
                                    relief='flat', borderwidth=0, cursor='hand2')
            select_button.pack(side='left', padx=(0, 10))
            
            cancel_button = tk.Button(button_frame, text="取消", 
                                    command=on_cancel,
                                    bg=self.colors['text_muted'], fg=self.colors['text_button'],
                                    font=('Microsoft YaHei UI', 9),
                                    relief='flat', borderwidth=0, cursor='hand2')
            cancel_button.pack(side='left')
            
            # 双击选择
            history_listbox.bind('<Double-Button-1>', lambda e: on_select())
            
            # 如果没有历史记录，显示提示
            if not suggestions:
                history_listbox.insert(tk.END, "暂无历史记录")
                select_button.configure(state='disabled')
                
        except Exception as e:
            self.logger.error(f"显示IP历史记录失败: {str(e)}")
            messagebox.showerror("错误", f"无法显示历史记录:\n{str(e)}")
    
    def _clear_ip_history(self):
        """清除IP历史记录"""
        try:
            if messagebox.askyesno("确认清除", "确定要清除所有IP历史记录吗？\n此操作不可撤销。"):
                self.ip_history_manager.clear_history(clear_devices=True)
                self.logger.info("IP历史记录已清除")
                messagebox.showinfo("清除完成", "IP历史记录已清除")
        except Exception as e:
            self.logger.error(f"清除IP历史记录失败: {str(e)}")
            messagebox.showerror("错误", f"清除历史记录失败:\n{str(e)}")
    
    def _on_closing(self):
        """窗口关闭"""
        if messagebox.askokcancel("退出", "确定要退出吗？"):
            self._cleanup()
            self.root.destroy()
    
    # ------------------------------------------------------------------
    # 远程文件编辑功能
    # ------------------------------------------------------------------
    def _open_remote_file_editor(self, remote_path: str):
        """打开远程文件编辑窗口"""
        if not self.is_connected:
            messagebox.showwarning("未连接", "请先连接设备")
            return

        # 确保 RemoteFileEditor 实例存在
        if not hasattr(self, 'remote_file_editor') or self.remote_file_editor is None:
            if self.telnet_client and self.http_server:
                self.remote_file_editor = RemoteFileEditor(
                    telnet_client=self.telnet_client,
                    http_server=self.http_server,
                    event_loop=self.loop,
                    telnet_lock=self.telnet_lock,
                    logger=self.logger
                )
            else:
                messagebox.showerror("错误", "HTTP 服务器未启动，无法编辑文件")
                return

        # 创建编辑窗口
        editor_win = tk.Toplevel(self.root)
        editor_win.title(f"编辑: {os.path.basename(remote_path)}")
        editor_win.geometry("800x600")
        editor_win.configure(bg=self.colors['bg_primary'])

        # 置顶并居中
        editor_win.attributes('-topmost', True)
        self._center_toplevel(editor_win, 800, 600)

        # 文本区域
        text_area = ScrolledText(editor_win, font=('Consolas', 11), wrap=tk.NONE, undo=True)
        text_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        status_var = tk.StringVar(value="正在加载...")
        status_label = tk.Label(editor_win, textvariable=status_var, bg=self.colors['bg_primary'], fg=self.colors['text_secondary'])
        status_label.pack(anchor='w', padx=12)

        def _load_content():
            # 先加载预览（前1000行），然后后台加载完整内容
            preview_future = self._run_async(self.remote_file_editor.read_file_preview(remote_path, 1000))
            if preview_future:
                def _on_preview_done(f):
                    try:
                        preview = f.result()
                    except Exception as e:
                        preview = f"读取文件失败: {str(e)}"
                    self.root.after(0, lambda: _populate_content(preview))

                    # 继续加载完整内容
                    full_future = self._run_async(self.remote_file_editor.read_file(remote_path))
                    if full_future:
                        def _on_full_done(ff):
                            try:
                                full_c = ff.result()
                            except Exception as ee:
                                self.logger.error(f"读取完整文件失败: {ee}")
                                return
                            if full_c != preview:
                                self.root.after(0, lambda: _populate_content(full_c))
                        full_future.add_done_callback(_on_full_done)

                preview_future.add_done_callback(_on_preview_done)

        def _populate_content(content:str):
            text_area.delete('1.0', tk.END)
            text_area.insert(tk.END, content)
            status_var.set("已加载，Ctrl+S 保存")

        def _save_content():
            new_text = text_area.get('1.0', tk.END)
            status_var.set("保存中...")
            save_future = self._run_async(self.remote_file_editor.write_file(remote_path, new_text))
            if save_future:
                def _on_save_done(f):
                    success = False
                    try:
                        success = f.result()
                    except Exception as e:
                        self.logger.error(f"保存失败: {e}")
                    self.root.after(0, lambda: status_var.set("保存成功" if success else "保存失败"))
                save_future.add_done_callback(_on_save_done)

        # 保存按钮
        btn_frame = tk.Frame(editor_win, bg=self.colors['bg_primary'])
        btn_frame.pack(fill=tk.X, padx=10, pady=(0,10))
        save_btn = tk.Button(btn_frame, text="💾 保存", command=_save_content, bg=self.colors['bg_button'], fg='#ffffff', relief='flat')
        save_btn.pack(side=tk.LEFT)

        # 绑定快捷键
        editor_win.bind('<Control-s>', lambda e: (_save_content(), 'break'))

        _load_content()

    def _open_image_preview(self, remote_path:str):
        """通过HTTP下载图片并弹窗预览"""
        if not self.is_connected:
            messagebox.showwarning("未连接", "请先连接设备")
            return

        if not hasattr(self, 'remote_file_editor') or self.remote_file_editor is None:
            if self.telnet_client and self.http_server:
                self.remote_file_editor = RemoteFileEditor(
                    telnet_client=self.telnet_client,
                    http_server=self.http_server,
                    event_loop=self.loop,
                    telnet_lock=self.telnet_lock,
                    logger=self.logger
                )
            else:
                messagebox.showerror("错误", "HTTP 服务器未启动，无法预览图片")
                return

        win = tk.Toplevel(self.root)
        win.title(os.path.basename(remote_path))
        win.geometry("800x600")
        win.attributes('-topmost', True)
        win.transient(self.root)

        # 居中窗口
        self._center_toplevel(win, 800, 600)

        canvas = tk.Canvas(win, bg=self.colors['bg_primary'], highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True)

        status_var = tk.StringVar(value="加载中...")
        status_label = tk.Label(win, textvariable=status_var, bg=self.colors['bg_primary'])
        status_label.place(relx=0.5, rely=0.98, anchor='s')

        async def fetch_bytes():
            return await self.remote_file_editor.get_file_bytes(remote_path)

        def _display_image(img_bytes:bytes):
            try:
                from PIL import Image, ImageTk  # 需要Pillow
            except ImportError:
                messagebox.showerror("缺少依赖", "预览图片需要 Pillow 库\n请运行: pip install pillow")
                win.destroy()
                return

            try:
                import io
                pil_img_original = Image.open(io.BytesIO(img_bytes))

                def render():
                    if not canvas.winfo_exists():
                        return
                    max_w = win.winfo_width() or 800
                    max_h = win.winfo_height() or 600
                    w, h = pil_img_original.size
                    scale = min(max_w / w, max_h / h, 1)
                    new_size = (int(w*scale), int(h*scale))
                    # Pillow兼容滤镜
                    if hasattr(Image, 'Resampling'):
                        resample_filter = Image.Resampling.LANCZOS
                    else:
                        resample_filter = Image.ANTIALIAS  # type: ignore
                    pil_img = pil_img_original.resize(new_size, resample_filter)
                    photo = ImageTk.PhotoImage(pil_img)
                    canvas.delete('all')
                    canvas.create_image(max_w/2, max_h/2, image=photo, anchor='center')
                    canvas.image = photo
                    status_var.set(f"{w}x{h} → {new_size[0]}x{new_size[1]}")

                render()

                # 绑定窗口尺寸变化重新渲染
                win.bind('<Configure>', lambda e: render())

            except Exception as e:
                messagebox.showerror("错误", f"无法显示图片: {e}")
                win.destroy()

        future = self._run_async(fetch_bytes())
        if future:
            def _on_img(f):
                try:
                    data = f.result()
                    if data:
                        self.root.after(0, lambda: _display_image(data))
                    else:
                        self.root.after(0, lambda: messagebox.showerror("错误", "下载图片失败"))
                except Exception as e:
                    self.root.after(0, lambda: messagebox.showerror("错误", f"下载图片异常: {e}"))
            future.add_done_callback(_on_img)

    def _center_toplevel(self, win:tk.Toplevel, min_w:int=400, min_h:int=300):
        """将Toplevel窗口居中并设置最小尺寸"""
        self.root.update_idletasks()
        w = max(min_w, win.winfo_reqwidth())
        h = max(min_h, win.winfo_reqheight())
        root_x = self.root.winfo_x()
        root_y = self.root.winfo_y()
        root_w = self.root.winfo_width()
        root_h = self.root.winfo_height()
        x = root_x + (root_w - w)//2
        y = root_y + (root_h - h)//2
        win.geometry(f"{w}x{h}+{x}+{y}")

    # ------------------------------------------------------------------
    # 辅助: 根据内容自动调整IP与设备ID输入框宽度
    # ------------------------------------------------------------------
    def _adjust_ip_id_width(self):
        """根据字符串长度动态调整两个Entry的宽度占比"""
        try:
            ip_len = max(len(self.host_var.get()), 1)
            dev_len = max(len(self.device_id_var.get()), 2)

            total = ip_len + dev_len
            # 预留给按钮 0.14 (历史+清除)
            host_ratio = max(0.40, min(0.75, ip_len / total * 0.86))
            dev_ratio = max(0.10, min(0.40, dev_len / total * 0.86))

            self.host_entry.place_configure(relwidth=host_ratio)
            self.device_id_display.place_configure(relx=host_ratio + 0.02, relwidth=dev_ratio)
            self.history_button.place_configure(relx=host_ratio + dev_ratio + 0.04)
            self.clear_history_button.place_configure(relx=host_ratio + dev_ratio + 0.11)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # 辅助: 根据历史记录同步设备ID到显示框
    # ------------------------------------------------------------------
    def _sync_device_id_display(self, ip:str=None):
        """根据IP历史记录设置device_id_var"""
        try:
            target_ip = ip or self.host_var.get().strip()
            device_id = None
            for rec in self.ip_history_manager.history_data.get('ip_history', []):
                if rec.get('ip') == target_ip:
                    device_id = rec.get('device_id')
                    break
            if device_id:
                self.device_id_var.set(device_id)
            else:
                self.device_id_var.set("--")
            self._adjust_ip_id_width()
        except Exception:
            pass


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