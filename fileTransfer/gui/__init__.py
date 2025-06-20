#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
现代化文件传输工具GUI组件包

模块化设计，按功能分离组件：
- main_window: 主窗口框架
- connection_panel: 连接管理面板
- directory_panel: 目录浏览面板  
- transfer_panel: 文件传输面板
- file_editor: 远程文件编辑器
- styles: 样式配置
"""

from .main_window import ModernFileTransferGUI

__all__ = ['ModernFileTransferGUI'] 