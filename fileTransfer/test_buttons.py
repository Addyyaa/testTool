#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk

def test_buttons():
    """测试按钮显示"""
    root = tk.Tk()
    root.title("按钮测试")
    root.geometry("400x300")
    
    # 主容器
    main_frame = tk.Frame(root, bg='lightgray')
    main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # 标题
    title = tk.Label(main_frame, text="按钮测试", font=('Microsoft YaHei UI', 14, 'bold'), bg='lightgray')
    title.pack(pady=(10, 20))
    
    # 模拟目录树
    tree_frame = tk.Frame(main_frame, bg='white', height=150)
    tree_frame.pack(fill=tk.X, pady=(0, 10))
    tree_frame.pack_propagate(False)
    
    tree_label = tk.Label(tree_frame, text="这里是目录树区域", bg='white')
    tree_label.pack(expand=True)
    
    # 按钮区域
    buttons_container = tk.Frame(main_frame, bg='#ffcccc', height=80)
    buttons_container.pack(fill=tk.X)
    buttons_container.pack_propagate(False)
    
    # 第一行按钮
    buttons_row1 = tk.Frame(buttons_container, bg='#ccffcc', height=35)
    buttons_row1.pack(fill=tk.X, pady=(0, 5))
    buttons_row1.pack_propagate(False)
    
    refresh_button = tk.Button(buttons_row1, text="刷新", 
                              bg='#0f7b6c', fg='#ffffff',
                              font=('Microsoft YaHei UI', 9, 'bold'),
                              relief='raised', borderwidth=2)
    refresh_button.pack(side=tk.LEFT, padx=(5, 2), fill=tk.X, expand=True)
    
    parent_button = tk.Button(buttons_row1, text="上级", 
                             bg='#0f7b6c', fg='#ffffff',
                             font=('Microsoft YaHei UI', 9, 'bold'),
                             relief='raised', borderwidth=2)
    parent_button.pack(side=tk.LEFT, padx=(2, 5), fill=tk.X, expand=True)
    
    # 第二行按钮
    buttons_row2 = tk.Frame(buttons_container, bg='#ccccff', height=35)
    buttons_row2.pack(fill=tk.X)
    buttons_row2.pack_propagate(False)
    
    transfer_button = tk.Button(buttons_row2, text="🚀 快速传输", 
                               bg='#dc2626', fg='#ffffff',
                               font=('Microsoft YaHei UI', 9, 'bold'),
                               relief='raised', borderwidth=2)
    transfer_button.pack(fill=tk.X, padx=5)
    
    # 状态信息
    status_label = tk.Label(main_frame, text="如果您能看到上面的彩色按钮区域，说明布局正常", 
                           bg='lightgray', font=('Microsoft YaHei UI', 10))
    status_label.pack(pady=10)
    
    root.mainloop()

if __name__ == "__main__":
    test_buttons() 