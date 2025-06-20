#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
目录浏览面板组件

负责远程目录浏览、文件类型识别、文件操作等功能
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Dict, Any, Optional, Callable
import os
import re


class DirectoryPanel:
    """目录浏览面板组件"""
    
    def __init__(self, parent_frame, theme, logger):
        """初始化目录面板"""
        self.parent = parent_frame
        self.theme = theme
        self.logger = logger
        
        # 当前路径
        self.current_remote_path = "/"
        
        # 回调函数
        self.on_refresh_callback: Optional[Callable] = None
        self.on_path_change_callback: Optional[Callable] = None
        self.on_file_select_callback: Optional[Callable] = None
        self.on_file_delete_callback: Optional[Callable] = None
        self.on_file_edit_callback: Optional[Callable] = None
        
        # 创建面板
        self._create_panel()
    
    def _create_panel(self):
        """创建现代化远程目录浏览面板 - 扩展到底部，充分利用空间"""
        # 目录浏览容器 - 扩展高度到58%，几乎到底部
        self.directory_container = tk.Frame(self.parent, bg=self.theme.colors['bg_sidebar'])
        self.directory_container.place(relx=0.02, rely=0.39, relwidth=0.96, relheight=0.58)
        
        # 卡片背景
        self.directory_card = tk.Frame(self.directory_container, 
                                     bg=self.theme.colors['bg_card'], 
                                     relief='flat', bd=0)
        self.directory_card.place(relx=0, rely=0, relwidth=1.0, relheight=1.0)
        
        # 目录浏览标题 - 占容器7%高度
        directory_title = tk.Label(self.directory_card, text="📁 远程目录", 
                                 bg=self.theme.colors['bg_card'], fg=self.theme.colors['text_primary'],
                                 font=('Microsoft YaHei UI', 11, 'bold'))
        directory_title.place(relx=0.04, rely=0.02, relwidth=0.92, relheight=0.07)
        
        # 当前路径标签 - 占容器5%高度
        self.current_path_label = tk.Label(self.directory_card, text="当前路径:", 
                                         bg=self.theme.colors['bg_card'], fg=self.theme.colors['text_secondary'],
                                         font=('Microsoft YaHei UI', 8))
        self.current_path_label.place(relx=0.04, rely=0.10, relwidth=0.92, relheight=0.05)
        
        # 当前路径输入框 - 占容器7%高度
        self.current_path_var = tk.StringVar(value="/")
        self.current_path_entry = tk.Entry(self.directory_card, textvariable=self.current_path_var,
                                         font=('Microsoft YaHei UI', 8), state='readonly',
                                         bg=self.theme.colors['bg_secondary'], fg=self.theme.colors['text_primary'],
                                         relief='solid', bd=1)
        self.current_path_entry.place(relx=0.04, rely=0.16, relwidth=0.92, relheight=0.07)
        
        # 目录树 - 占容器65%高度，为按钮留出足够空间
        self.directory_tree = ttk.Treeview(self.directory_card, columns=(), show='tree')
        self.directory_tree.place(relx=0.04, rely=0.25, relwidth=0.88, relheight=0.65)
        
        # 目录树滚动条
        tree_scrollbar = ttk.Scrollbar(self.directory_card, orient='vertical', command=self.directory_tree.yview)
        tree_scrollbar.place(relx=0.92, rely=0.25, relwidth=0.04, relheight=0.65)
        self.directory_tree.configure(yscrollcommand=tree_scrollbar.set)
        
        # 现代化按钮区域 - 占容器10%高度，位置在92%处，确保不重叠
        buttons_container = tk.Frame(self.directory_card, bg=self.theme.colors['bg_card'])
        buttons_container.place(relx=0.04, rely=0.92, relwidth=0.92, relheight=0.08)
        
        # 现代化按钮 - 使用图标
        self.refresh_button = tk.Button(buttons_container, text="🔄 刷新", 
                                       command=self._on_refresh_clicked,
                                       bg=self.theme.colors['bg_button'], fg='#ffffff',
                                       font=('Microsoft YaHei UI', 9, 'bold'),
                                       relief='flat', borderwidth=0,
                                       activebackground=self.theme.colors['bg_button_hover'], 
                                       activeforeground='#ffffff',
                                       cursor='hand2')
        self.refresh_button.place(relx=0, rely=0, relwidth=0.32, relheight=1.0)
        
        self.parent_button = tk.Button(buttons_container, text="⬆️ 上级", 
                                     command=self._go_parent_directory,
                                     bg=self.theme.colors['bg_button'], fg='#ffffff',
                                     font=('Microsoft YaHei UI', 9, 'bold'),
                                     relief='flat', borderwidth=0,
                                     activebackground=self.theme.colors['bg_button_hover'], 
                                     activeforeground='#ffffff',
                                     cursor='hand2')
        self.parent_button.place(relx=0.34, rely=0, relwidth=0.32, relheight=1.0)
        
        self.delete_file_button = tk.Button(buttons_container, text="🗑️ 删除", 
                                           command=self._delete_selected_file,
                                           bg=self.theme.colors['error'], fg='#ffffff',
                                           font=('Microsoft YaHei UI', 9, 'bold'),
                                           relief='flat', borderwidth=0,
                                           activebackground='#b91c1c', activeforeground='#ffffff',
                                           cursor='hand2', state='disabled')
        self.delete_file_button.place(relx=0.68, rely=0, relwidth=0.32, relheight=1.0)
        
        # 绑定事件
        self._bind_events()
        
        # 配置树颜色
        self._configure_tree_colors()
    
    def _bind_events(self):
        """绑定事件"""
        self.directory_tree.bind('<<TreeviewSelect>>', self._on_directory_select)
        self.directory_tree.bind('<Double-1>', self._on_directory_double_click)
    
    def _configure_tree_colors(self):
        """配置treeview的颜色标签"""
        try:
            colors = self.theme.get_file_type_colors()
            
            # 目录 - 蓝色，加粗
            self.directory_tree.tag_configure('directory', 
                                            foreground=colors['directory'], 
                                            font=('Microsoft YaHei UI', 9, 'bold'))
            
            # 可执行文件 - 绿色，加粗
            self.directory_tree.tag_configure('executable', 
                                            foreground=colors['executable'], 
                                            font=('Microsoft YaHei UI', 9, 'bold'))
            
            # 符号链接 - 紫色，斜体
            self.directory_tree.tag_configure('link', 
                                            foreground=colors['link'], 
                                            font=('Microsoft YaHei UI', 9, 'italic'))
            
            # 图片文件 - 橙色
            self.directory_tree.tag_configure('image', foreground=colors['image'])
            # 文档文件 - 灰色
            self.directory_tree.tag_configure('document', foreground=colors['document'])
            # 压缩文件 - 红色
            self.directory_tree.tag_configure('archive', foreground=colors['archive'])
            # 配置文件 - 青色
            self.directory_tree.tag_configure('config', foreground=colors['config'])
            # 脚本文件 - 翠绿色
            self.directory_tree.tag_configure('script', foreground=colors['script'])
            # 普通文件 - 深灰色
            self.directory_tree.tag_configure('file', foreground=colors['file'])
            
        except Exception as e:
            self.logger.error(f"配置treeview颜色失败: {e}")
    
    def _on_refresh_clicked(self):
        """刷新按钮点击"""
        if self.on_refresh_callback:
            self.on_refresh_callback(self.current_remote_path)
    
    def _go_parent_directory(self):
        """上级目录"""
        if self.current_remote_path != '/':
            parent_path = self._get_unix_parent_path(self.current_remote_path)
            self.set_current_path(parent_path)
            if self.on_path_change_callback:
                self.on_path_change_callback(parent_path)
    
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
            
            is_dir = self._is_directory_item(is_directory)
            
            if is_dir:
                self.delete_file_button.configure(state='disabled')
            else:
                self.delete_file_button.configure(state='normal')
            
            # 调用选择回调
            if self.on_file_select_callback:
                self.on_file_select_callback(full_path, is_dir, is_exec)
        else:
            self.delete_file_button.configure(state='disabled')
    
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
            
            is_dir = self._is_directory_item(is_directory)
            
            if is_dir:
                # 进入目录
                self.set_current_path(full_path)
                if self.on_path_change_callback:
                    self.on_path_change_callback(full_path)
            else:
                # 文件操作
                filename_lower = full_path.lower()
                editable_by_ext = any(filename_lower.endswith(ext) for ext in [".ini", ".txt", ".log", ".sh"]) or "log" in filename_lower or "ini" in filename_lower
                
                if (not is_exec) or editable_by_ext:
                    # 可编辑文件
                    if self.on_file_edit_callback:
                        self.on_file_edit_callback(full_path)
                elif any(filename_lower.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".gif", ".bmp"]):
                    # 图片预览
                    if self.on_file_edit_callback:
                        self.on_file_edit_callback(full_path, mode='preview')
    
    def _delete_selected_file(self):
        """删除选中的文件"""
        selection = self.directory_tree.selection()
        if not selection:
            messagebox.showwarning("未选择", "请先选择要删除的文件")
            return
        
        item = self.directory_tree.item(selection[0])
        full_path, is_directory, is_exec = item['values']
        filename = item['text']
        
        is_dir = self._is_directory_item(is_directory)
        
        if is_dir:
            messagebox.showwarning("无法删除", "不能删除目录，只能删除文件")
            return
        
        # 移除图标，只显示文件名
        clean_filename = filename
        if ' ' in filename and any(icon in filename for icon in ['📄', '🖼️', '📦', '⚙️', '📜', '🔗']):
            clean_filename = filename.split(' ', 1)[1] if ' ' in filename else filename
        
        # 显示确认对话框
        if messagebox.askyesno("确认删除", 
                              f"确定要删除文件吗？\n\n文件名: {clean_filename}\n路径: {full_path}\n\n此操作不可撤销！"):
            if self.on_file_delete_callback:
                self.on_file_delete_callback(full_path, clean_filename)
    
    def set_current_path(self, path: str):
        """设置当前路径"""
        self.current_remote_path = self._normalize_unix_path(path)
        self.current_path_var.set(self.current_remote_path)
    
    def get_current_path(self) -> str:
        """获取当前路径"""
        return self.current_remote_path
    
    def update_directory_tree(self, items: List[Dict[str, Any]]):
        """更新目录树"""
        try:
            self.logger.info(f"开始更新目录树，收到 {len(items)} 个项目")
            
            # 清空现有项目
            current_children = self.directory_tree.get_children()
            self.directory_tree.delete(*current_children)
            
            # 先配置颜色标签
            self._configure_tree_colors()
            
            # 添加新项目
            added_count = 0
            icons = self.theme.get_file_type_icons()
            
            for item in items:
                try:
                    # 根据文件类型选择图标
                    file_type = item.get('file_type', 'file')
                    icon = icons.get(file_type, icons['file'])
                    display_name = f"{icon} {item['name']}"
                    
                    # 确定标签类型
                    if item.get('is_directory', False):
                        tag = 'directory'
                    elif item.get('is_executable', False):
                        tag = 'executable'
                    elif item.get('is_link', False):
                        tag = 'link'
                    else:
                        tag = item.get('file_type', 'file')
                    
                    # 插入到树中
                    is_directory_value = bool(item.get('is_directory', False))
                    tree_item = self.directory_tree.insert('', 'end', 
                                                         text=display_name,
                                                         values=(item['full_path'], is_directory_value, item.get('is_executable', False)),
                                                         tags=(tag,))
                    
                    added_count += 1
                    
                except Exception as item_error:
                    self.logger.error(f"添加项目失败 {item['name']}: {str(item_error)}")
                    # 如果添加失败，尝试最简单的版本
                    try:
                        simple_name = item['name']
                        tree_item = self.directory_tree.insert('', 'end', 
                                                             text=simple_name,
                                                             values=(item['full_path'], item.get('is_directory', False)))
                        added_count += 1
                    except Exception:
                        pass
            
            # 检查最终结果
            children_count = len(self.directory_tree.get_children())
            self.logger.info(f"目录树更新完成，显示 {children_count} 个项目，成功添加 {added_count} 个")
                
        except Exception as e:
            self.logger.error(f"更新目录树失败: {str(e)}")
    
    def _determine_file_type(self, permissions: str, name: str) -> str:
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
    
    def _is_directory_item(self, is_directory_value) -> bool:
        """统一的目录判断方法"""
        if isinstance(is_directory_value, bool):
            return is_directory_value
        elif isinstance(is_directory_value, str):
            return is_directory_value.lower() in ['true', '1', 'yes']
        elif isinstance(is_directory_value, (int, float)):
            return bool(is_directory_value)
        else:
            return False
    
    def _get_unix_parent_path(self, path: str) -> str:
        """获取Unix风格的父路径"""
        if path == '/':
            return '/'
        
        path = path.replace('\\', '/')
        path = path.rstrip('/')
        
        if not path:
            return '/'
        
        last_slash = path.rfind('/')
        if last_slash == -1:
            return '/'
        elif last_slash == 0:
            return '/'
        else:
            return path[:last_slash]
    
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
    
    def set_refresh_callback(self, callback: Callable):
        """设置刷新回调"""
        self.on_refresh_callback = callback
    
    def set_path_change_callback(self, callback: Callable):
        """设置路径变化回调"""
        self.on_path_change_callback = callback
    
    def set_file_select_callback(self, callback: Callable):
        """设置文件选择回调"""
        self.on_file_select_callback = callback
    
    def set_file_delete_callback(self, callback: Callable):
        """设置文件删除回调"""
        self.on_file_delete_callback = callback
    
    def set_file_edit_callback(self, callback: Callable):
        """设置文件编辑回调"""
        self.on_file_edit_callback = callback
    
    def set_refresh_status(self, is_refreshing: bool):
        """设置刷新状态"""
        try:
            if is_refreshing:
                self.refresh_button.configure(
                    text="⏳ 刷新中...",
                    state='disabled',
                    bg=self.theme.colors['bg_secondary']
                )
            else:
                self.refresh_button.configure(
                    text="🔄 刷新",
                    state='normal',
                    bg=self.theme.colors['bg_button']
                )
        except Exception as e:
            self.logger.error(f"设置刷新状态失败: {e}") 