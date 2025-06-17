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
        
        self.host_entry = tk.Entry(ip_container, font=('Microsoft YaHei UI', 9),
                                 bg=self.colors['bg_primary'], fg=self.colors['text_primary'],
                                 relief='solid', bd=1, highlightthickness=1,
                                 highlightcolor=self.colors['border_focus'])
        self.host_entry.place(relx=0, rely=0, relwidth=0.78, relheight=1.0)
        self.host_entry.insert(0, "192.168.1.100")
        
        # 历史记录按钮
        self.history_button = tk.Button(ip_container, text="📋", 
                                      command=self._show_ip_history,
                                      bg=self.colors['bg_accent'], fg=self.colors['text_button'],
                                      font=('Microsoft YaHei UI', 8),
                                      relief='flat', borderwidth=0,
                                      activebackground=self.colors['bg_accent'],
                                      cursor='hand2')
        self.history_button.place(relx=0.80, rely=0, relwidth=0.09, relheight=1.0)
        
        # 清除历史按钮
        self.clear_history_button = tk.Button(ip_container, text="🗑", 
                                            command=self._clear_ip_history,
                                            bg=self.colors['error'], fg=self.colors['text_button'],
                                            font=('Microsoft YaHei UI', 8),
                                            relief='flat', borderwidth=0,
                                            activebackground='#dc2626',
                                            cursor='hand2')
        self.clear_history_button.place(relx=0.91, rely=0, relwidth=0.09, relheight=1.0)
        
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
                                      bg=self.colors['bg_button'], fg=self.colors['text_button'],
                                      font=('Microsoft YaHei UI', 9, 'bold'),
                                      relief='flat', borderwidth=0,
                                      activebackground=self.colors['bg_button_hover'], 
                                      activeforeground=self.colors['text_button'],
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
                                       bg=self.colors['bg_button'], fg=self.colors['text_button'],
                                       font=('Microsoft YaHei UI', 8, 'bold'),
                                       relief='flat', borderwidth=0,
                                       activebackground=self.colors['bg_button_hover'], 
                                       activeforeground=self.colors['text_button'],
                                       cursor='hand2')
        self.refresh_button.place(relx=0, rely=0, relwidth=0.32, relheight=1.0)
        
        self.parent_button = tk.Button(buttons_container, text="⬆️ 上级", 
                                     command=self._go_parent_directory,
                                     bg=self.colors['bg_button'], fg=self.colors['text_button'],
                                     font=('Microsoft YaHei UI', 8, 'bold'),
                                     relief='flat', borderwidth=0,
                                     activebackground=self.colors['bg_button_hover'], 
                                     activeforeground=self.colors['text_button'],
                                     cursor='hand2')
        self.parent_button.place(relx=0.34, rely=0, relwidth=0.32, relheight=1.0)
        
        self.quick_transfer_button = tk.Button(buttons_container, text="⚡ 快传", 
                                             command=self._quick_start_transfer,
                                             bg=self.colors['error'], fg=self.colors['text_button'],
                                             font=('Microsoft YaHei UI', 8, 'bold'),
                                             relief='flat', borderwidth=0,
                                             activebackground='#b91c1c', activeforeground=self.colors['text_button'],
                                             cursor='hand2')
        self.quick_transfer_button.place(relx=0.68, rely=0, relwidth=0.32, relheight=1.0)
        
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
                                             bg=self.colors['error'], fg=self.colors['text_button'],
                                             font=('Microsoft YaHei UI', 8, 'bold'),
                                             relief='flat', borderwidth=0,
                                             activebackground='#b91c1c', activeforeground=self.colors['text_button'],
                                             cursor='hand2')
        self.start_transfer_button.place(relx=0.04, rely=0.32, relwidth=0.44, relheight=0.63)
        
        self.clear_queue_button = tk.Button(self.queue_card, text="🗑️ 清空", 
                                          command=self._clear_transfer_queue,
                                          bg=self.colors['text_muted'], fg=self.colors['text_button'],
                                          font=('Microsoft YaHei UI', 8, 'bold'),
                                          relief='flat', borderwidth=0,
                                          activebackground='#4b5563', activeforeground=self.colors['text_button'],
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
            try:
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)
                # 创建telnet锁
                self.telnet_lock = asyncio.Lock()
                self.logger.info("异步事件循环已启动")
                self.loop.run_forever()
            except Exception as e:
                self.logger.error(f"异步事件循环启动失败: {e}")
        
        self.loop_thread = threading.Thread(target=run_loop, daemon=True)
        self.loop_thread.start()
        
        # 等待事件循环启动，增加超时保护
        wait_count = 0
        max_wait = 100  # 最多等待1秒
        while (self.loop is None or self.telnet_lock is None) and wait_count < max_wait:
            time.sleep(0.01)
            wait_count += 1
        
        if wait_count >= max_wait:
            self.logger.error("异步事件循环启动超时")
        else:
            self.logger.info(f"异步事件循环启动完成，等待了 {wait_count * 10}ms")
    
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
        self.connection_status_label.configure(text=f"已连接 ({self.connection_config['host']})", 
                                             fg=self.colors['success'])
        
        # 保存IP到历史记录
        current_ip = self.connection_config['host']
        if current_ip:
            # 异步读取设备ID并保存
            self._run_async(self._save_ip_with_device_id(current_ip))
        
        self._update_status(f"成功连接到 {self.connection_config['host']}")
        
        # 启动HTTP服务器
        self._start_http_server()
        
        # 连接成功后不自动刷新目录，让用户手动点击刷新
        self.logger.info("连接成功！请点击'刷新'按钮来获取目录列表")
        self._update_status("连接成功！请点击刷新按钮获取目录")
    
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
        """异步刷新目录"""
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
                try:
                    # 使用较短的超时时间，避免界面冻结
                    items = future.result(timeout=5)
                    self.logger.info(f"异步操作完成，获得 {len(items)} 个项目")
                    # 使用after确保在主线程中更新GUI
                    self.root.after(0, lambda: self._update_directory_tree(items))
                except asyncio.TimeoutError:
                    self.logger.error("目录列表获取超时")
                    self.root.after(0, lambda: self._update_status("目录列表获取超时"))
                except Exception as result_error:
                    self.logger.error(f"获取异步结果失败: {result_error}")
                    self.root.after(0, lambda: self._update_status(f"获取结果失败: {result_error}"))
            else:
                self.logger.error("无法创建异步任务")
                self.root.after(0, lambda: self._update_status("无法创建异步任务"))
                
        except Exception as e:
            self.logger.error(f"刷新目录失败: {str(e)}")
            import traceback
            self.logger.error(f"完整错误信息: {traceback.format_exc()}")
            # 显示错误信息到状态栏
            self.root.after(0, lambda: self._update_status(f"刷新目录失败: {str(e)}"))
    
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
            # 目录 - 蓝色
            self.directory_tree.tag_configure('directory', foreground='#3b82f6')
            
            # 可执行文件 - 绿色
            self.directory_tree.tag_configure('executable', foreground='#10b981')
            
            # 符号链接 - 紫色
            self.directory_tree.tag_configure('link', foreground='#8b5cf6')
            
            # 图片文件 - 橙色
            self.directory_tree.tag_configure('image', foreground='#f59e0b')
            
            # 文档文件 - 灰色
            self.directory_tree.tag_configure('document', foreground='#6b7280')
            
            # 压缩文件 - 红色
            self.directory_tree.tag_configure('archive', foreground='#dc2626')
            
            # 配置文件 - 青色
            self.directory_tree.tag_configure('config', foreground='#0891b2')
            
            # 脚本文件 - 翠绿色
            self.directory_tree.tag_configure('script', foreground='#059669')
            
            # 普通文件 - 深灰色
            self.directory_tree.tag_configure('file', foreground='#374151')
            
        except Exception as e:
            self.logger.debug(f"配置treeview颜色失败: {e}")
    
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
                self.logger.info(f"执行命令: ls -la --color=always \"{normalized_path}\"")
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
        """更新目录树"""
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
            
            # 添加新项目
            added_count = 0
            for i, item in enumerate(items):
                try:
                    # 根据文件类型选择图标和颜色
                    icon, color = self._get_file_icon_and_color(item)
                    display_name = f"{icon} {item['name']}"
                    
                    # 插入到树中
                    tree_item = self.directory_tree.insert('', 'end', text=display_name, 
                                                         values=(item['full_path'], item['is_directory']))
                    
                    # 设置文本颜色（需要配置treeview的tag）
                    self.directory_tree.set(tree_item, '#0', display_name)
                    
                    # 为不同类型的项目设置标签
                    if item['is_directory']:
                        self.directory_tree.item(tree_item, tags=('directory',))
                    elif item.get('is_executable', False):
                        self.directory_tree.item(tree_item, tags=('executable',))
                    elif item.get('is_link', False):
                        self.directory_tree.item(tree_item, tags=('link',))
                    else:
                        file_type = item.get('file_type', 'file')
                        self.directory_tree.item(tree_item, tags=(file_type,))
                    
                    added_count += 1
                    self.logger.debug(f"成功添加项目 {i+1}: {display_name} -> {tree_item}")
                except Exception as item_error:
                    self.logger.error(f"添加项目失败 {item}: {str(item_error)}")
                    # 尝试简化版本
                    try:
                        simple_name = item['name']
                        tree_item = self.directory_tree.insert('', 'end', text=simple_name, 
                                                             values=(item['full_path'], item.get('is_directory', False)))
                        added_count += 1
                        self.logger.debug(f"简化版本成功添加: {simple_name}")
                    except Exception as simple_error:
                        self.logger.error(f"简化版本也失败: {str(simple_error)}")
            
            # 配置treeview的颜色标签
            try:
                self._configure_tree_colors()
            except Exception as color_error:
                self.logger.warning(f"配置颜色失败: {color_error}")
            
            # 检查最终结果
            try:
                children_count = len(self.directory_tree.get_children())
                self.logger.info(f"目录树更新完成，显示 {children_count} 个项目，成功添加 {added_count} 个")
                
                if children_count == 0 and len(items) > 0:
                    self.logger.warning("警告：有项目但目录树为空，可能存在显示问题")
                    # 尝试强制刷新界面
                    self.root.update_idletasks()
                
                # 更新状态栏
                self._update_status(f"目录刷新完成，显示 {children_count} 个项目")
                
            except Exception as check_error:
                self.logger.error(f"检查最终结果失败: {check_error}")
                
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
            full_path, is_directory = item['values']
            
            self.logger.debug(f"双击项目: {full_path}, 是否为目录: {is_directory}")
            
            if is_directory:
                self.current_remote_path = self._normalize_unix_path(full_path)
                self.current_path_var.set(self.current_remote_path)
                self._refresh_directory()
            else:
                self.logger.info(f"双击了文件: {full_path}，忽略操作")
    
    def _on_directory_select(self, event):
        """目录选择事件"""
        selection = self.directory_tree.selection()
        if selection:
            item = self.directory_tree.item(selection[0])
            full_path, is_directory = item['values']
            if is_directory:
                self.current_remote_path = self._normalize_unix_path(full_path)
                self.current_path_var.set(self.current_remote_path)
    
    def _go_parent_directory(self):
        """上级目录"""
        if self.current_remote_path != '/':
            parent_path = self._get_unix_parent_path(self.current_remote_path)
            self.current_remote_path = parent_path
            self.current_path_var.set(parent_path)
            self._refresh_directory()
    
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
        """异步传输文件 - 改为串行执行避免并发冲突"""
        try:
            # 收集所有要传输的文件信息
            transfer_tasks = []
            total_count = self.queue_listbox.size()
            
            for i in range(total_count):
                item_text = self.queue_listbox.get(i)
                parts = item_text.split(" -> ")
                if len(parts) == 2:
                    filename = parts[0]
                    remote_path = parts[1]
                    
                    if filename in self.file_path_mapping:
                        local_file = self.file_path_mapping[filename]
                        transfer_tasks.append((local_file, remote_path, filename))
            
            # 在异步环境中串行执行所有传输任务
            future = self._run_async(self._execute_transfers_sequentially(transfer_tasks))
            if future:
                success_count = future.result(timeout=300)  # 5分钟超时
                self.root.after(0, self._on_transfer_complete, success_count, len(transfer_tasks))
            else:
                self.root.after(0, self._on_transfer_error, "无法创建异步传输任务")
            
        except Exception as e:
            self.logger.error(f"文件传输异常: {str(e)}")
            import traceback
            self.logger.error(f"详细错误: {traceback.format_exc()}")
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
            
            # 获取下载URL（使用HTTP服务器的方法，确保正确编码）
            host_ip = self._get_local_ip()
            download_url = self.http_server.get_download_url(filename, host_ip)
            self.logger.info(f"生成下载URL: {download_url}")
            
            # 通过telnet下载
            self.logger.info(f"开始通过telnet执行下载命令")
            result = await self._download_via_telnet(download_url, remote_path, filename)
            
            # 清理临时文件
            self.http_server.remove_file(filename)
            
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
            else:
                self.logger.info(f"已保存IP历史记录: {ip} (无设备ID)")
                
        except Exception as e:
            self.logger.error(f"保存IP历史记录失败: {str(e)}")
    
    def _load_last_ip(self):
        """加载最后使用的IP"""
        try:
            last_ip = self.ip_history_manager.get_last_used_ip()
            if last_ip:
                self.host_entry.delete(0, tk.END)
                self.host_entry.insert(0, last_ip)
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
                    self.host_entry.delete(0, tk.END)
                    self.host_entry.insert(0, ip)
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