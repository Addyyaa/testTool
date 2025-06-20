#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
现代化主题样式配置

提供统一的颜色主题和UI样式配置
"""

from tkinter import ttk
from typing import Dict


class ModernTheme:
    """现代化主题配置类"""
    
    def __init__(self):
        """初始化主题配置"""
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
    
    def setup_styles(self, style: ttk.Style):
        """设置现代化样式"""
        # 配置通用样式
        style.configure('Modern.TFrame', 
                       background=self.colors['bg_primary'],
                       relief='flat')
        
        style.configure('Sidebar.TFrame',
                       background=self.colors['bg_sidebar'],
                       relief='flat')
        
        style.configure('Modern.TLabel',
                       background=self.colors['bg_primary'],
                       foreground=self.colors['text_primary'],
                       font=('Microsoft YaHei UI', 10))
        
        style.configure('Title.TLabel',
                       background=self.colors['bg_primary'],
                       foreground=self.colors['text_primary'],
                       font=('Microsoft YaHei UI', 14, 'bold'))
        
        style.configure('Modern.TButton',
                       background=self.colors['bg_button'],
                       foreground='#ffffff',  # 明确设置为白色
                       borderwidth=2,
                       relief='raised',
                       focuscolor='none',
                       font=('Microsoft YaHei UI', 10, 'bold'),
                       padding=(8, 6))
        
        style.map('Modern.TButton',
                  background=[('active', self.colors['bg_button_hover']),
                            ('pressed', self.colors['bg_button_hover'])],
                  foreground=[('active', '#ffffff'),
                            ('pressed', '#ffffff')],
                  relief=[('pressed', 'sunken'),
                        ('active', 'raised')],
                  borderwidth=[('active', 2), ('pressed', 2)])
        
        style.configure('Modern.TEntry',
                       fieldbackground=self.colors['bg_primary'],
                       borderwidth=1,
                       insertcolor=self.colors['text_primary'],
                       font=('Microsoft YaHei UI', 10))
        
        style.configure('Modern.Treeview',
                       background=self.colors['bg_primary'],
                       foreground=self.colors['text_primary'],
                       borderwidth=1,
                       font=('Microsoft YaHei UI', 9))
        
        style.configure('Modern.Treeview.Heading',
                       background=self.colors['bg_secondary'],
                       foreground=self.colors['text_primary'],
                       font=('Microsoft YaHei UI', 10, 'bold'))
    
    def get_file_type_colors(self) -> Dict[str, str]:
        """获取文件类型颜色映射"""
        return {
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
    
    def get_file_type_icons(self) -> Dict[str, str]:
        """获取文件类型图标映射"""
        return {
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