#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Treeview测试程序
"""
import tkinter as tk
from tkinter import ttk

def test_treeview():
    """测试Treeview功能"""
    root = tk.Tk()
    root.title("Treeview测试")
    root.geometry("400x300")
    
    # 创建Treeview
    tree = ttk.Treeview(root, columns=(), show='tree')
    tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # 添加测试数据
    test_items = [
        {'name': 'appconfigs', 'is_directory': True},
        {'name': 'bin', 'is_directory': True},
        {'name': 'config', 'is_directory': True},
        {'name': 'customer', 'is_directory': True},
        {'name': 'linuxrc', 'is_directory': False},
        {'name': 'etc', 'is_directory': True},
    ]
    
    print(f"准备添加 {len(test_items)} 个项目")
    
    for i, item in enumerate(test_items):
        icon = "📁" if item['is_directory'] else "📄"
        display_name = f"{icon} {item['name']}"
        
        tree_item = tree.insert('', 'end', text=display_name, 
                               values=(f"/path/{item['name']}", item['is_directory']))
        print(f"添加项目 {i+1}: {display_name} -> {tree_item}")
    
    # 检查结果
    children = tree.get_children()
    print(f"Treeview中有 {len(children)} 个项目")
    
    for child in children:
        item_data = tree.item(child)
        print(f"  - {item_data['text']}")
    
    root.mainloop()

if __name__ == "__main__":
    test_treeview() 