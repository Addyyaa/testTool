#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
连接管理面板组件

负责设备连接、IP历史记录管理、连接状态显示等功能
"""

import tkinter as tk
from tkinter import messagebox
from typing import Optional, Callable, Dict, Any
import threading
import sys
import os

# 添加父目录到系统路径以支持导入
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from ip_history_manager import IPHistoryManager


class ConnectionPanel:
    """连接管理面板组件"""
    
    def __init__(self, parent_frame, theme, logger):
        """初始化连接面板"""
        self.parent = parent_frame
        self.theme = theme
        self.logger = logger
        
        # 连接状态
        self.is_connected = False
        self.connection_config = {}
        self.current_device_id = None
        
        # IP历史管理器
        self.ip_history_manager = IPHistoryManager("ip_history.json")
        
        # 回调函数
        self.on_connect_callback: Optional[Callable] = None
        self.on_disconnect_callback: Optional[Callable] = None
        
        # 创建面板
        self._create_panel()
        
        # 加载最后使用的IP
        self._load_last_ip()
    
    def _create_panel(self):
        """创建连接配置面板 - 占侧边栏35%高度"""
        # 连接配置容器 - 使用卡片样式
        self.connection_container = tk.Frame(self.parent, bg=self.theme.colors['bg_sidebar'])
        self.connection_container.place(relx=0.02, rely=0.02, relwidth=0.96, relheight=0.35)
        
        # 卡片背景
        self.connection_card = tk.Frame(self.connection_container, 
                                       bg=self.theme.colors['bg_card'], 
                                       relief='flat', bd=0)
        self.connection_card.place(relx=0, rely=0, relwidth=1.0, relheight=1.0)
        
        # 连接配置标题 - 占容器8%高度
        connection_title = tk.Label(self.connection_card, text="🔗 设备连接", 
                                  bg=self.theme.colors['bg_card'], fg=self.theme.colors['text_primary'],
                                  font=('Microsoft YaHei UI', 11, 'bold'))
        connection_title.place(relx=0.04, rely=0.02, relwidth=0.92, relheight=0.08)
        
        # 连接配置框架 - 占容器88%高度
        self.connection_frame = tk.Frame(self.connection_card, bg=self.theme.colors['bg_card'])
        self.connection_frame.place(relx=0.04, rely=0.12, relwidth=0.92, relheight=0.86)
        
        # 主机地址 - 占框架13%高度
        tk.Label(self.connection_frame, text="主机地址:", 
                bg=self.theme.colors['bg_card'], fg=self.theme.colors['text_secondary'],
                font=('Microsoft YaHei UI', 9)).place(relx=0, rely=0, relwidth=1.0, relheight=0.10)
        
        # IP输入框和历史按钮容器 - 扩展到100%宽度
        ip_container = tk.Frame(self.connection_frame, bg=self.theme.colors['bg_card'])
        ip_container.place(relx=0, rely=0.11, relwidth=1.0, relheight=0.12)
        
        # IP输入框（可编辑）- 占40%宽度
        self.host_var = tk.StringVar(value="192.168.1.100")
        self.host_entry = tk.Entry(ip_container, textvariable=self.host_var,
                                 font=('Microsoft YaHei UI', 9),
                                 bg=self.theme.colors['bg_primary'], fg=self.theme.colors['text_primary'],
                                 relief='solid', bd=1, highlightthickness=1,
                                 highlightcolor=self.theme.colors['border_focus'])
        self.host_entry.place(relx=0, rely=0, relwidth=0.4, relheight=1.0)
        
        # 屏幕ID显示（只读）- 占40%宽度
        self.device_id_var = tk.StringVar(value="--")
        self.device_id_display = tk.Entry(ip_container, textvariable=self.device_id_var,
                                        font=('Microsoft YaHei UI', 9), state='readonly',
                                        readonlybackground=self.theme.colors['bg_secondary'], 
                                        fg=self.theme.colors['text_secondary'],
                                        relief='flat', justify='center')
        self.device_id_display.place(relx=0.4, rely=0, relwidth=0.4, relheight=1.0)
        
        # 历史记录按钮 - 占10%宽度
        self.history_button = tk.Button(ip_container, text="📋", 
                                      command=self._show_ip_history,
                                      bg=self.theme.colors['bg_accent'], fg=self.theme.colors['text_button'],
                                      font=('Microsoft YaHei UI', 9),
                                      relief='flat', borderwidth=0,
                                      activebackground=self.theme.colors['bg_accent'],
                                      cursor='hand2')
        self.history_button.place(relx=0.8, rely=0, relwidth=0.1, relheight=1.0)
        
        # 清除历史按钮 - 占10%宽度
        self.clear_history_button = tk.Button(ip_container, text="🗑", 
                                            command=self._clear_ip_history,
                                            bg=self.theme.colors['error'], fg=self.theme.colors['text_button'],
                                            font=('Microsoft YaHei UI', 9),
                                            relief='flat', borderwidth=0,
                                            activebackground='#dc2626',
                                            cursor='hand2')
        self.clear_history_button.place(relx=0.9, rely=0, relwidth=0.1, relheight=1.0)
        
        # 端口 - 占框架13%高度
        tk.Label(self.connection_frame, text="端口:", 
                bg=self.theme.colors['bg_card'], fg=self.theme.colors['text_secondary'],
                font=('Microsoft YaHei UI', 9)).place(relx=0, rely=0.25, relwidth=1.0, relheight=0.10)
        self.port_entry = tk.Entry(self.connection_frame, font=('Microsoft YaHei UI', 9),
                                 bg=self.theme.colors['bg_primary'], fg=self.theme.colors['text_primary'],
                                 relief='solid', bd=1, highlightthickness=1,
                                 highlightcolor=self.theme.colors['border_focus'])
        self.port_entry.place(relx=0, rely=0.36, relwidth=1.0, relheight=0.12)
        self.port_entry.insert(0, "23")
        
        # 用户名和密码 - 并排布局
        tk.Label(self.connection_frame, text="用户名:", 
                bg=self.theme.colors['bg_card'], fg=self.theme.colors['text_secondary'],
                font=('Microsoft YaHei UI', 9)).place(relx=0, rely=0.50, relwidth=0.48, relheight=0.10)
        self.username_entry = tk.Entry(self.connection_frame, font=('Microsoft YaHei UI', 9),
                                     bg=self.theme.colors['bg_primary'], fg=self.theme.colors['text_primary'],
                                     relief='solid', bd=1, highlightthickness=1,
                                     highlightcolor=self.theme.colors['border_focus'])
        self.username_entry.place(relx=0, rely=0.61, relwidth=0.48, relheight=0.12)
        self.username_entry.insert(0, "root")
        
        tk.Label(self.connection_frame, text="密码:", 
                bg=self.theme.colors['bg_card'], fg=self.theme.colors['text_secondary'],
                font=('Microsoft YaHei UI', 9)).place(relx=0.52, rely=0.50, relwidth=0.48, relheight=0.10)
        self.password_entry = tk.Entry(self.connection_frame, font=('Microsoft YaHei UI', 9), show='*',
                                     bg=self.theme.colors['bg_primary'], fg=self.theme.colors['text_primary'],
                                     relief='solid', bd=1, highlightthickness=1,
                                     highlightcolor=self.theme.colors['border_focus'])
        self.password_entry.place(relx=0.52, rely=0.61, relwidth=0.48, relheight=0.12)
        self.password_entry.insert(0, "ya!2dkwy7-934^")
        
        # 连接按钮 - 现代化样式
        self.connect_button = tk.Button(self.connection_frame, text="🔗 连接设备", 
                                      command=self._on_connect_clicked,
                                      bg=self.theme.colors['bg_button'], fg='#ffffff',
                                      font=('Microsoft YaHei UI', 10, 'bold'),
                                      relief='flat', borderwidth=0,
                                      activebackground=self.theme.colors['bg_button_hover'], 
                                      activeforeground='#ffffff',
                                      cursor='hand2')
        self.connect_button.place(relx=0, rely=0.76, relwidth=1.0, relheight=0.12)
        
        # 连接状态指示器 - 重新设计布局
        self.connection_status_frame = tk.Frame(self.connection_frame, bg=self.theme.colors['bg_card'])
        self.connection_status_frame.place(relx=0, rely=0.90, relwidth=1.0, relheight=0.10)
        
        # 状态指示点
        self.status_indicator = tk.Canvas(self.connection_status_frame, width=10, height=10, 
                                        bg=self.theme.colors['bg_card'], highlightthickness=0)
        self.status_indicator.place(relx=0, rely=0.2, relwidth=0.08, relheight=0.6)
        self.status_indicator.create_oval(2, 2, 8, 8, fill=self.theme.colors['error'], outline='')
        
        # 状态文字
        self.connection_status_label = tk.Label(self.connection_status_frame, text="未连接", 
                                              bg=self.theme.colors['bg_card'], fg=self.theme.colors['text_muted'],
                                              font=('Microsoft YaHei UI', 8))
        self.connection_status_label.place(relx=0.12, rely=0, relwidth=0.88, relheight=1.0)
        
        # 绑定事件
        self._bind_events()
    
    def _bind_events(self):
        """绑定事件"""
        # 连接参数输入事件
        self.host_entry.bind('<Return>', lambda e: self._on_connect_clicked())
        self.port_entry.bind('<Return>', lambda e: self._on_connect_clicked())
        self.username_entry.bind('<Return>', lambda e: self._on_connect_clicked())
        self.password_entry.bind('<Return>', lambda e: self._on_connect_clicked())
        
        # 绑定输入内容变化以清空设备ID并调整宽度
        self.host_entry.bind('<KeyRelease>', lambda e: self._on_ip_input_change())
        self.host_entry.bind('<FocusOut>', lambda e: self._on_ip_input_change())
        self.host_entry.bind('<FocusIn>', lambda e: self._on_ip_input_change())
    
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
            
            # IP地址校验
            if not self._is_valid_ip(host):
                messagebox.showerror("输入错误", "请输入有效的IP地址")
                return
            
            self.connection_config = {
                'host': host, 'port': port,
                'username': username, 'password': password
            }
            
            self.connect_button.configure(state='disabled', text='连接中...')
            
            # 调用回调函数
            if self.on_connect_callback:
                threading.Thread(target=self.on_connect_callback, args=(self.connection_config,), daemon=True).start()
            
        except ValueError:
            messagebox.showerror("输入错误", "端口号必须是数字")
        except Exception as e:
            messagebox.showerror("连接错误", f"连接失败: {str(e)}")
    
    def _disconnect_device(self):
        """断开连接"""
        try:
            self.is_connected = False
            self.connect_button.configure(state='disabled', text='断开中...')
            
            # 调用回调函数
            if self.on_disconnect_callback:
                self.on_disconnect_callback()
                
        except Exception as e:
            self.logger.error(f"断开连接失败: {str(e)}")
    
    def update_connection_status(self, connected: bool, message: str = "", ip: str = ""):
        """更新连接状态"""
        self.is_connected = connected
        
        if connected:
            self.connect_button.configure(state='normal', text='断开连接')
            # 更新状态指示器为绿色
            self.status_indicator.delete('all')
            self.status_indicator.create_oval(2, 2, 10, 10, fill=self.theme.colors['success'], outline='')
            self.connection_status_label.configure(text=f"已连接 ({ip})", fg=self.theme.colors['success'])
            
            # 保存IP到历史记录
            if ip:
                try:
                    self.ip_history_manager.add_ip(ip, None)
                    self.logger.info(f"已保存IP到历史记录: {ip}")
                except Exception as e:
                    self.logger.debug(f"保存IP失败: {e}")
        else:
            self.connect_button.configure(state='normal', text='连接设备')
            # 更新状态指示器为红色
            self.status_indicator.delete('all')
            self.status_indicator.create_oval(2, 2, 10, 10, fill=self.theme.colors['error'], outline='')
            self.connection_status_label.configure(text=message or "未连接", fg=self.theme.colors['error'])
    
    def set_connect_callback(self, callback: Callable):
        """设置连接回调"""
        self.on_connect_callback = callback
    
    def set_disconnect_callback(self, callback: Callable):
        """设置断开连接回调"""
        self.on_disconnect_callback = callback
    
    def get_connection_config(self) -> Dict[str, Any]:
        """获取连接配置"""
        return self.connection_config.copy()
    
    def _load_last_ip(self):
        """加载最后使用的IP"""
        try:
            last_ip = self.ip_history_manager.get_last_used_ip()
            if last_ip:
                self.host_var.set(last_ip)
                self._sync_device_id_display(last_ip)
                self.logger.info(f"已加载最后使用的IP: {last_ip}")
            else:
                # 即使没有历史记录，也要初始化显示
                self._sync_device_id_display()
        except Exception as e:
            self.logger.debug(f"加载最后使用IP失败: {e}")
            # 确保显示初始化
            self._sync_device_id_display()
    
    def _show_ip_history(self):
        """显示IP历史记录选择窗口"""
        try:
            suggestions = self.ip_history_manager.get_ip_suggestions()
            if not suggestions:
                messagebox.showinfo("历史记录", "暂无历史记录")
                return
                
            # 创建历史记录窗口
            history_window = tk.Toplevel()
            history_window.title("IP历史记录")
            history_window.geometry("400x300")
            history_window.configure(bg=self.theme.colors['bg_primary'])
            history_window.transient(self.parent)
            history_window.grab_set()
            
            # 居中窗口
            self._center_window(history_window, 400, 300)
            
            # 标题
            title_label = tk.Label(history_window, text="选择历史IP地址", 
                                 bg=self.theme.colors['bg_primary'], fg=self.theme.colors['text_primary'],
                                 font=('Microsoft YaHei UI', 12, 'bold'))
            title_label.pack(pady=10)
            
            # 历史记录列表
            listbox_frame = tk.Frame(history_window, bg=self.theme.colors['bg_primary'])
            listbox_frame.pack(fill='both', expand=True, padx=20, pady=(0, 10))
            
            history_listbox = tk.Listbox(listbox_frame, 
                                       bg=self.theme.colors['bg_card'], fg=self.theme.colors['text_primary'],
                                       font=('Microsoft YaHei UI', 9),
                                       selectbackground=self.theme.colors['bg_accent_light'])
            history_listbox.pack(side='left', fill='both', expand=True)
            
            scrollbar = tk.Scrollbar(listbox_frame, orient='vertical', command=history_listbox.yview)
            scrollbar.pack(side='right', fill='y')
            history_listbox.configure(yscrollcommand=scrollbar.set)
            
            # 加载历史记录
            for suggestion in suggestions:
                history_listbox.insert(tk.END, suggestion['display_text'])
            
            # 按钮区域
            button_frame = tk.Frame(history_window, bg=self.theme.colors['bg_primary'])
            button_frame.pack(fill='x', padx=20, pady=(0, 20))
            
            def on_select():
                selection = history_listbox.curselection()
                if selection:
                    selected_suggestion = suggestions[selection[0]]
                    ip = selected_suggestion['ip']
                    device_id = selected_suggestion.get('device_id')
                    self.host_var.set(ip)
                    # 同步显示设备ID
                    self.device_id_var.set(device_id or "--")
                    self._adjust_ip_id_width()
                    history_window.destroy()
            
            def on_cancel():
                history_window.destroy()
            
            # 按钮
            select_button = tk.Button(button_frame, text="选择", 
                                    command=on_select,
                                    bg=self.theme.colors['bg_button'], fg=self.theme.colors['text_button'],
                                    font=('Microsoft YaHei UI', 9),
                                    relief='flat', borderwidth=0, cursor='hand2')
            select_button.pack(side='left', padx=(0, 10))
            
            cancel_button = tk.Button(button_frame, text="取消", 
                                    command=on_cancel,
                                    bg=self.theme.colors['text_muted'], fg=self.theme.colors['text_button'],
                                    font=('Microsoft YaHei UI', 9),
                                    relief='flat', borderwidth=0, cursor='hand2')
            cancel_button.pack(side='left')
            
            # 双击选择
            history_listbox.bind('<Double-Button-1>', lambda e: on_select())
                
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
                # 同步显示
                self._sync_device_id_display()
        except Exception as e:
            self.logger.error(f"清除IP历史记录失败: {str(e)}")
            messagebox.showerror("错误", f"清除历史记录失败:\n{str(e)}")
    
    def _sync_device_id_display(self, ip: str = None):
        """同步设备ID到显示框"""
        try:
            ip = ip or self.host_var.get()
            device_id = None
            for record in self.ip_history_manager.get_ip_suggestions():
                if record['ip'] == ip:
                    device_id = record.get('device_id')
                    break
            self.device_id_var.set(device_id or "--")
            self._adjust_ip_id_width()
        except Exception as e:
            self.logger.debug(f"同步设备ID显示失败: {e}")
    
    def _adjust_ip_id_width(self):
        """使用固定的宽度比例：IP(40%) + ScreenID(40%) + 按钮(20%)"""
        try:
            # 固定比例：40%:40%:10%:10%
            self.host_entry.place_configure(relx=0, relwidth=0.4)
            self.device_id_display.place_configure(relx=0.4, relwidth=0.4)
            self.history_button.place_configure(relx=0.8, relwidth=0.1)
            self.clear_history_button.place_configure(relx=0.9, relwidth=0.1)
        except Exception:
            pass
    
    def _center_window(self, window, width, height):
        """居中窗口"""
        try:
            # 获取父窗口位置和大小
            parent_x = self.parent.winfo_rootx()
            parent_y = self.parent.winfo_rooty()
            parent_width = self.parent.winfo_width()
            parent_height = self.parent.winfo_height()
            
            # 计算居中位置
            x = parent_x + (parent_width - width) // 2
            y = parent_y + (parent_height - height) // 2
            
            # 设置窗口位置
            window.geometry(f"{width}x{height}+{x}+{y}")
        except Exception:
            # 如果居中失败，使用默认位置
            window.geometry(f"{width}x{height}")
    
    def update_device_id(self, device_id: str):
        """更新设备ID显示"""
        self.current_device_id = device_id
        if device_id:
            self.device_id_var.set(device_id)
            # 更新历史记录中的设备ID
            current_ip = self.host_var.get()
            if current_ip:
                try:
                    self.ip_history_manager.add_ip(current_ip, device_id)
                    self.logger.info(f"已更新设备ID: {current_ip} -> {device_id}")
                except Exception as e:
                    self.logger.debug(f"更新设备ID失败: {e}")
        self._adjust_ip_id_width()
    
    def _on_ip_input_change(self):
        """处理IP输入变化"""
        try:
            current_ip = self.host_var.get().strip()
            
            # 先查找历史记录中的设备ID
            device_id = None
            if current_ip:  # 只有当IP不为空时才查找
                suggestions = self.ip_history_manager.get_ip_suggestions()
                for record in suggestions:
                    if record['ip'] == current_ip:
                        device_id = record.get('device_id')
                        self.logger.debug(f"找到历史记录中的设备ID: {current_ip} -> {device_id}")
                        break
            
            # 更新设备ID显示
            self.device_id_var.set(device_id or "--")
            
            # 调整布局
            self._adjust_ip_id_width()
            
        except Exception as e:
            self.logger.debug(f"处理IP输入变化失败: {e}")
            # 确保显示"--"
            self.device_id_var.set("--")
    
    def _is_valid_ip(self, ip: str) -> bool:
        """验证IP地址格式"""
        try:
            import re
            # IPv4地址正则表达式
            ipv4_pattern = r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
            return bool(re.match(ipv4_pattern, ip))
        except Exception:
            return False 