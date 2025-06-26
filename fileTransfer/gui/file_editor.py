#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
远程文件编辑器组件

提供远程文件编辑和图片预览功能
增强功能：搜索（支持正则表达式）、日志等级高亮、时间过滤、自动换行
"""

import tkinter as tk
from tkinter import messagebox
from tkinter.scrolledtext import ScrolledText
import os
import sys
import asyncio
import re

# 添加父目录到系统路径以支持导入
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from fileTransfer.file_transfer_controller import RemoteFileEditor


class AdvancedTextEditor:
    """增强文本编辑器，支持搜索、高亮、过滤等功能"""
    
    def __init__(self, parent_window, theme, logger):
        """初始化增强文本编辑器"""
        self.parent = parent_window
        self.theme = theme
        self.logger = logger
        
        # 文本内容相关
        self.original_content = ""
        self.filtered_content = ""
        self.search_results = []
        self.current_search_index = 0
        
        # 日志等级颜色配置
        self.log_level_colors = {
            'ERROR': '#FF4444',    # 红色
            'WARN': '#FF8800',     # 橙色  
            'INFO': '#0088FF',     # 蓝色
            'DEBUG': '#888888',    # 灰色
            'TRACE': '#666666',    # 深灰色
            'FATAL': '#AA0000',    # 深红色
            'CRITICAL': '#CC0000', # 暗红色
        }
        
        # 时间戳正则表达式
        self.timestamp_patterns = [
            r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}',  # YYYY-MM-DD HH:MM:SS
            r'\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2}',  # YYYY/MM/DD HH:MM:SS
            r'\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}',        # MM-DD HH:MM:SS
            r'\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2}',        # MM/DD HH:MM:SS
        ]
    
    def is_window_valid(self):
        """检查窗口是否仍然有效"""
        try:
            return hasattr(self, 'editor_win') and self.editor_win.winfo_exists()
        except tk.TclError:
            return False
    
    def create_editor_window(self, title: str, content: str, save_callback=None):
        """创建增强编辑器窗口"""
        self.original_content = content
        self.filtered_content = content
        
        # 创建编辑窗口
        self.editor_win = tk.Toplevel(self.parent)
        self.editor_win.title(title)
        self.editor_win.geometry("1000x700")
        self.editor_win.configure(bg=self.theme.colors['bg_primary'])
        
        # 改为transient而不是topmost，避免总是置顶
        self.editor_win.transient(self.parent)
        self._center_window(self.editor_win, 1000, 700)
        
        # 绑定窗口关闭事件
        self.editor_win.protocol("WM_DELETE_WINDOW", self._on_window_close)
        
        # 创建主框架
        main_frame = tk.Frame(self.editor_win, bg=self.theme.colors['bg_primary'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建工具栏
        self._create_toolbar(main_frame, save_callback)
        
        # 创建文本区域
        self._create_text_area(main_frame)
        
        # 创建状态栏
        self._create_status_bar(main_frame)
        
        # 插入内容并应用高亮
        self._insert_content_with_highlight()
        
        # 绑定事件
        self._bind_events()
        
        return self.editor_win
    
    def _on_window_close(self):
        """窗口关闭事件处理"""
        try:
            # 取消所有定时器
            if hasattr(self, '_search_timer'):
                self.editor_win.after_cancel(self._search_timer)
            
            # 清理资源
            if hasattr(self, 'text_area'):
                self.text_area = None
            
            # 销毁窗口
            self.editor_win.destroy()
        except Exception as e:
            self.logger.error(f"关闭编辑器窗口时出错: {e}")
    
    def _show_topmost_message(self, title: str, message: str, msg_type: str = "info"):
        """显示置顶消息框"""
        try:
            # 创建临时的根窗口用于置顶显示
            temp_root = tk.Tk()
            temp_root.withdraw()  # 隐藏主窗口
            temp_root.attributes('-topmost', True)  # 设置置顶
            
            # 显示消息
            if msg_type == "info":
                messagebox.showinfo(title, message, parent=temp_root)
            elif msg_type == "error":
                messagebox.showerror(title, message, parent=temp_root)
            elif msg_type == "warning":
                messagebox.showwarning(title, message, parent=temp_root)
            
            # 销毁临时窗口
            temp_root.destroy()
        except Exception as e:
            self.logger.error(f"显示置顶消息失败: {e}")
            # 回退到普通消息框
            if msg_type == "info":
                messagebox.showinfo(title, message)
            elif msg_type == "error":
                messagebox.showerror(title, message)
            elif msg_type == "warning":
                messagebox.showwarning(title, message)
    
    def _create_toolbar(self, parent, save_callback):
        """创建工具栏"""
        toolbar_frame = tk.Frame(parent, bg=self.theme.colors['bg_primary'])
        toolbar_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 左侧工具栏
        left_frame = tk.Frame(toolbar_frame, bg=self.theme.colors['bg_primary'])
        left_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 搜索框
        search_frame = tk.Frame(left_frame, bg=self.theme.colors['bg_primary'])
        search_frame.pack(side=tk.LEFT, padx=(0, 10))
        
        tk.Label(search_frame, text="搜索:", bg=self.theme.colors['bg_primary'], 
                fg=self.theme.colors['text_primary']).pack(side=tk.LEFT)
        
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(search_frame, textvariable=self.search_var, width=25)
        self.search_entry.pack(side=tk.LEFT, padx=(5, 5))
        
        # 添加占位符文本效果
        self._setup_placeholder(self.search_entry, "支持正则: \\d+错误|INFO.*成功")
        
        # 搜索选项
        self.regex_var = tk.BooleanVar(value=True)
        self.case_var = tk.BooleanVar(value=False)
        self.realtime_var = tk.BooleanVar(value=False)  # 默认关闭实时搜索
        
        tk.Checkbutton(search_frame, text="正则", variable=self.regex_var,
                      bg=self.theme.colors['bg_primary'], fg=self.theme.colors['text_primary'],
                      selectcolor=self.theme.colors['bg_card']).pack(side=tk.LEFT, padx=2)
        
        tk.Checkbutton(search_frame, text="大小写", variable=self.case_var,
                      bg=self.theme.colors['bg_primary'], fg=self.theme.colors['text_primary'],
                      selectcolor=self.theme.colors['bg_card']).pack(side=tk.LEFT, padx=2)
        
        tk.Checkbutton(search_frame, text="实时", variable=self.realtime_var,
                      bg=self.theme.colors['bg_primary'], fg=self.theme.colors['text_primary'],
                      selectcolor=self.theme.colors['bg_card']).pack(side=tk.LEFT, padx=2)
        
        # 搜索按钮
        btn_search = tk.Button(search_frame, text="🔍", command=self._search_text,
                              bg=self.theme.colors['bg_button'], fg='white', width=3)
        btn_search.pack(side=tk.LEFT, padx=2)
        
        btn_prev = tk.Button(search_frame, text="↑", command=self._search_prev,
                            bg=self.theme.colors['bg_button'], fg='white', width=3)
        btn_prev.pack(side=tk.LEFT, padx=1)
        
        btn_next = tk.Button(search_frame, text="↓", command=self._search_next,
                            bg=self.theme.colors['bg_button'], fg='white', width=3)
        btn_next.pack(side=tk.LEFT, padx=1)
        
        # 时间过滤框
        filter_frame = tk.Frame(left_frame, bg=self.theme.colors['bg_primary'])
        filter_frame.pack(side=tk.LEFT, padx=(20, 10))
        
        tk.Label(filter_frame, text="时间过滤:", bg=self.theme.colors['bg_primary'],
                fg=self.theme.colors['text_primary']).pack(side=tk.LEFT)
        
        self.time_start_var = tk.StringVar()
        self.time_end_var = tk.StringVar()
        
        start_entry = tk.Entry(filter_frame, textvariable=self.time_start_var, width=12)
        start_entry.pack(side=tk.LEFT, padx=(5, 2))
        self._setup_placeholder(start_entry, "10:00:00")
        
        tk.Label(filter_frame, text="至", bg=self.theme.colors['bg_primary'],
                fg=self.theme.colors['text_primary']).pack(side=tk.LEFT, padx=2)
        
        end_entry = tk.Entry(filter_frame, textvariable=self.time_end_var, width=12)
        end_entry.pack(side=tk.LEFT, padx=(2, 5))
        self._setup_placeholder(end_entry, "18:00:00")
        
        btn_filter = tk.Button(filter_frame, text="过滤", command=self._filter_by_time,
                              bg=self.theme.colors['bg_button'], fg='white')
        btn_filter.pack(side=tk.LEFT, padx=2)
        
        btn_reset = tk.Button(filter_frame, text="重置", command=self._reset_filter,
                             bg=self.theme.colors['bg_secondary'], fg='black')
        btn_reset.pack(side=tk.LEFT, padx=2)
        
        # 右侧工具栏
        right_frame = tk.Frame(toolbar_frame, bg=self.theme.colors['bg_primary'])
        right_frame.pack(side=tk.RIGHT)
        
        # 自动换行选项
        self.wrap_var = tk.BooleanVar(value=False)
        tk.Checkbutton(right_frame, text="自动换行", variable=self.wrap_var,
                      command=self._toggle_wrap, bg=self.theme.colors['bg_primary'],
                      fg=self.theme.colors['text_primary'],
                      selectcolor=self.theme.colors['bg_card']).pack(side=tk.LEFT, padx=10)
        
        # 保存按钮
        if save_callback:
            btn_save = tk.Button(right_frame, text="💾 保存", command=save_callback,
                               bg=self.theme.colors['bg_button'], fg='white')
            btn_save.pack(side=tk.LEFT, padx=5)
    
    def _create_text_area(self, parent):
        """创建文本区域"""
        text_frame = tk.Frame(parent, bg=self.theme.colors['bg_primary'])
        text_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 创建文本区域（默认不换行）
        self.text_area = ScrolledText(text_frame, font=('Consolas', 11), 
                                     wrap=tk.NONE, undo=True, maxundo=50,
                                     bg='white', fg='black', insertbackground='black')
        self.text_area.pack(fill=tk.BOTH, expand=True)
        
        # 配置文本标签样式
        self._configure_text_tags()
    
    def _create_status_bar(self, parent):
        """创建状态栏"""
        status_frame = tk.Frame(parent, bg=self.theme.colors['bg_primary'])
        status_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.status_var = tk.StringVar(value="已加载，Ctrl+S 保存，Ctrl+F 搜索，回车执行搜索")
        status_label = tk.Label(status_frame, textvariable=self.status_var,
                               bg=self.theme.colors['bg_primary'], 
                               fg=self.theme.colors['text_secondary'])
        status_label.pack(side=tk.LEFT)
        
        # 行列信息
        self.position_var = tk.StringVar(value="行: 1, 列: 1")
        position_label = tk.Label(status_frame, textvariable=self.position_var,
                                 bg=self.theme.colors['bg_primary'],
                                 fg=self.theme.colors['text_secondary'])
        position_label.pack(side=tk.RIGHT)
    
    def _configure_text_tags(self):
        """配置文本标签样式"""
        # 搜索高亮
        self.text_area.tag_configure("search_highlight", background="#FFFF00", foreground="#000000")
        self.text_area.tag_configure("current_search", background="#FF8800", foreground="#FFFFFF")
        
        # 日志等级高亮
        for level, color in self.log_level_colors.items():
            self.text_area.tag_configure(f"level_{level}", foreground=color, font=('Consolas', 11, 'bold'))
        
        # 时间戳高亮
        self.text_area.tag_configure("timestamp", foreground="#008800", font=('Consolas', 11, 'bold'))
    
    def _insert_content_with_highlight(self):
        """插入内容并应用高亮"""
        self.text_area.delete('1.0', tk.END)
        self.text_area.insert(tk.END, self.filtered_content)
        
        # 应用日志等级和时间戳高亮
        self._apply_log_highlighting()
    
    def _apply_log_highlighting(self):
        """应用日志等级和时间戳高亮"""
        content = self.text_area.get('1.0', tk.END)
        lines = content.split('\n')
        
        for line_idx, line in enumerate(lines):
            line_start = f"{line_idx + 1}.0"
            
            # 高亮日志等级
            for level in self.log_level_colors.keys():
                # 匹配各种格式的日志等级
                pattern = rf'\b{level}\b'
                for match in re.finditer(pattern, line, re.IGNORECASE):
                    start_pos = f"{line_idx + 1}.{match.start()}"
                    end_pos = f"{line_idx + 1}.{match.end()}"
                    self.text_area.tag_add(f"level_{level}", start_pos, end_pos)
            
            # 高亮时间戳
            for pattern in self.timestamp_patterns:
                for match in re.finditer(pattern, line):
                    start_pos = f"{line_idx + 1}.{match.start()}"
                    end_pos = f"{line_idx + 1}.{match.end()}"
                    self.text_area.tag_add("timestamp", start_pos, end_pos)
    
    def _bind_events(self):
        """绑定事件"""
        # 快捷键绑定
        self.editor_win.bind('<Control-f>', lambda e: (self.search_entry.focus(), 'break'))
        self.editor_win.bind('<F3>', lambda e: self._search_next())
        self.editor_win.bind('<Shift-F3>', lambda e: self._search_prev())
        self.search_entry.bind('<Return>', lambda e: self._search_text())
        self.search_entry.bind('<KeyRelease>', lambda e: self._search_text_realtime())
        
        # 光标位置更新
        self.text_area.bind('<KeyRelease>', self._update_cursor_position)
        self.text_area.bind('<Button-1>', self._update_cursor_position)
    
    def _search_text(self):
        """搜索文本"""
        if not self.is_window_valid():
            return
            
        try:
            search_term = self.search_var.get().strip()
            if not search_term:
                self._clear_search_highlights()
                return
            
            self._clear_search_highlights()
            self.search_results = []
            
            content = self.text_area.get('1.0', tk.END)
            
            if self.regex_var.get():
                # 正则表达式搜索
                flags = 0 if self.case_var.get() else re.IGNORECASE
                try:
                    pattern = re.compile(search_term, flags)
                    for match in pattern.finditer(content):
                        start_line = content[:match.start()].count('\n') + 1
                        start_char = match.start() - content[:match.start()].rfind('\n') - 1
                        if start_char < 0:
                            start_char = match.start()
                        
                        end_line = content[:match.end()].count('\n') + 1
                        end_char = match.end() - content[:match.end()].rfind('\n') - 1
                        if end_char < 0:
                            end_char = match.end()
                        
                        self.search_results.append((f"{start_line}.{start_char}", f"{end_line}.{end_char}"))
                except re.error as e:
                    if self.is_window_valid():
                        self.status_var.set(f"正则表达式错误: {e}")
                    return
            else:
                # 普通文本搜索
                if not self.case_var.get():
                    search_term = search_term.lower()
                    content = content.lower()
                
                start_pos = 0
                while True:
                    pos = content.find(search_term, start_pos)
                    if pos == -1:
                        break
                    
                    start_line = content[:pos].count('\n') + 1
                    start_char = pos - content[:pos].rfind('\n') - 1
                    if start_char < 0:
                        start_char = pos
                    
                    end_pos = pos + len(search_term)
                    end_line = content[:end_pos].count('\n') + 1
                    end_char = end_pos - content[:end_pos].rfind('\n') - 1
                    if end_char < 0:
                        end_char = end_pos
                    
                    self.search_results.append((f"{start_line}.{start_char}", f"{end_line}.{end_char}"))
                    start_pos = pos + 1
            
            if self.search_results:
                self.current_search_index = 0
                self._highlight_search_results()
                self._jump_to_current_search()
                if self.is_window_valid():
                    self.status_var.set(f"找到 {len(self.search_results)} 个匹配项")
            else:
                if self.is_window_valid():
                    self.status_var.set("未找到匹配项")
        except Exception as e:
            self.logger.error(f"搜索文本时出错: {e}")
            if self.is_window_valid():
                self.status_var.set(f"搜索出错: {e}")
    
    def _search_text_realtime(self):
        """实时搜索文本"""
        if not self.is_window_valid():
            return
            
        if not self.realtime_var.get():
            return
        
        try:
            # 取消上一个定时器
            if hasattr(self, '_search_timer'):
                self.editor_win.after_cancel(self._search_timer)
            
            # 设置新的定时器，避免过于频繁的搜索
            self._search_timer = self.editor_win.after(300, self._search_text)
        except Exception as e:
            self.logger.error(f"实时搜索出错: {e}")
    
    def _highlight_search_results(self):
        """高亮搜索结果"""
        self._clear_search_highlights()
        
        for start_pos, end_pos in self.search_results:
            self.text_area.tag_add("search_highlight", start_pos, end_pos)
    
    def _clear_search_highlights(self):
        """清除搜索高亮"""
        self.text_area.tag_remove("search_highlight", '1.0', tk.END)
        self.text_area.tag_remove("current_search", '1.0', tk.END)
    
    def _jump_to_current_search(self):
        """跳转到当前搜索结果"""
        if not self.is_window_valid() or not self.search_results:
            return
        
        try:
            # 清除当前高亮
            self.text_area.tag_remove("current_search", '1.0', tk.END)
            
            # 高亮当前结果
            start_pos, end_pos = self.search_results[self.current_search_index]
            self.text_area.tag_add("current_search", start_pos, end_pos)
            
            # 滚动到当前位置
            self.text_area.see(start_pos)
            
            # 更新状态
            if self.is_window_valid():
                self.status_var.set(f"第 {self.current_search_index + 1}/{len(self.search_results)} 个结果")
        except tk.TclError as e:
            self.logger.error(f"跳转搜索结果失败: {e}")
        except Exception as e:
            self.logger.error(f"跳转到搜索结果时出错: {e}")
    
    def _search_next(self):
        """下一个搜索结果"""
        if not self.search_results:
            return
        
        self.current_search_index = (self.current_search_index + 1) % len(self.search_results)
        self._jump_to_current_search()
    
    def _search_prev(self):
        """上一个搜索结果"""
        if not self.search_results:
            return
        
        self.current_search_index = (self.current_search_index - 1) % len(self.search_results)
        self._jump_to_current_search()
    
    def _filter_by_time(self):
        """按时间过滤日志"""
        if not self.is_window_valid():
            return
            
        start_time = self.time_start_var.get().strip()
        end_time = self.time_end_var.get().strip()
        
        # 检查是否为占位符文本
        if start_time == "10:00:00":
            start_time = ""
        if end_time == "18:00:00":
            end_time = ""
        
        if not start_time and not end_time:
            messagebox.showwarning("时间过滤", "请输入开始时间或结束时间")
            return
        
        try:
            filtered_lines = []
            lines = self.original_content.split('\n')
            
            for line in lines:
                # 提取时间戳
                timestamp = None
                for pattern in self.timestamp_patterns:
                    match = re.search(pattern, line)
                    if match:
                        timestamp = match.group()
                        break
                
                if timestamp:
                    # 提取时间部分（HH:MM:SS）
                    time_match = re.search(r'(\d{2}:\d{2}:\d{2})', timestamp)
                    if time_match:
                        line_time = time_match.group(1)
                        
                        # 检查是否在时间范围内
                        in_range = True
                        if start_time and line_time < start_time:
                            in_range = False
                        if end_time and line_time > end_time:
                            in_range = False
                        
                        if in_range:
                            filtered_lines.append(line)
                else:
                    # 没有时间戳的行也保留（可能是多行日志的一部分）
                    filtered_lines.append(line)
            
            self.filtered_content = '\n'.join(filtered_lines)
            self._insert_content_with_highlight()
            
            if self.is_window_valid():
                self.status_var.set(f"时间过滤完成，显示 {len(filtered_lines)} 行")
            
        except Exception as e:
            self.logger.error(f"时间过滤失败: {e}")
            messagebox.showerror("过滤失败", f"时间过滤过程中出现错误: {e}")
    
    def _reset_filter(self):
        """重置过滤器"""
        if not self.is_window_valid():
            return
            
        self.filtered_content = self.original_content
        self.time_start_var.set("")
        self.time_end_var.set("")
        self._insert_content_with_highlight()
        if self.is_window_valid():
            self.status_var.set("已重置过滤器")
    
    def _toggle_wrap(self):
        """切换自动换行"""
        if self.wrap_var.get():
            self.text_area.configure(wrap=tk.WORD)
        else:
            self.text_area.configure(wrap=tk.NONE)
    
    def _update_cursor_position(self, event=None):
        """更新光标位置显示"""
        try:
            cursor_pos = self.text_area.index(tk.INSERT)
            line, col = cursor_pos.split('.')
            self.position_var.set(f"行: {line}, 列: {int(col) + 1}")
        except:
            pass
    
    def _setup_placeholder(self, entry_widget, placeholder_text):
        """为Entry组件设置占位符文本"""
        def on_focus_in(event):
            if entry_widget.get() == placeholder_text:
                entry_widget.delete(0, tk.END)
                entry_widget.config(fg='black')
        
        def on_focus_out(event):
            if not entry_widget.get():
                entry_widget.insert(0, placeholder_text)
                entry_widget.config(fg='gray')
        
        # 初始设置占位符
        entry_widget.insert(0, placeholder_text)
        entry_widget.config(fg='gray')
        
        # 绑定事件
        entry_widget.bind('<FocusIn>', on_focus_in)
        entry_widget.bind('<FocusOut>', on_focus_out)
    
    def _center_window(self, win: tk.Toplevel, min_w: int = 400, min_h: int = 300):
        """将Toplevel窗口居中并设置最小尺寸"""
        self.parent.update_idletasks()
        w = max(min_w, win.winfo_reqwidth())
        h = max(min_h, win.winfo_reqheight())
        root_x = self.parent.winfo_x()
        root_y = self.parent.winfo_y()
        root_w = self.parent.winfo_width()
        root_h = self.parent.winfo_height()
        x = root_x + (root_w - w) // 2
        y = root_y + (root_h - h) // 2
        win.geometry(f"{w}x{h}+{x}+{y}")
    
    def get_text_content(self):
        """获取文本内容"""
        if not self.is_window_valid():
            return ""
        try:
            content = self.text_area.get('1.0', tk.END)
            # 移除Tkinter自动添加的末尾换行符
            if content.endswith('\n'):
                content = content[:-1]
            return content
        except tk.TclError:
            return ""


class RemoteFileEditorGUI:
    """远程文件编辑器GUI组件"""
    
    def __init__(self, parent_window, theme, logger, telnet_client, http_server, event_loop, telnet_lock):
        """初始化远程文件编辑器"""
        self.parent = parent_window
        self.theme = theme
        self.logger = logger
        self.event_loop = event_loop
        
        # 远程文件编辑器实例
        self.remote_file_editor = RemoteFileEditor(
            telnet_client=telnet_client,
            http_server=http_server,
            event_loop=event_loop,
            telnet_lock=telnet_lock,
            logger=logger
        )
    
    def _run_async(self, coro):
        """在事件循环中运行异步任务"""
        try:
            if self.event_loop and not self.event_loop.is_closed():
                future = asyncio.run_coroutine_threadsafe(coro, self.event_loop)
                return future
            else:
                self.logger.error("事件循环不可用")
                return None
        except Exception as e:
            self.logger.error(f"创建异步任务失败: {e}")
            return None
    
    def open_file_editor(self, remote_path: str):
        """打开远程文件编辑窗口"""
        try:
            self.logger.info(f"打开文件编辑器: {remote_path}")
            
            # 使用远程文件编辑器加载内容
            def load_and_edit():
                try:
                    # 异步加载文件内容
                    future = self._run_async(self.remote_file_editor.read_file_async(remote_path))
                    if future:
                        future.add_done_callback(lambda f: self._show_enhanced_editor_window(remote_path, f))
                    else:
                        messagebox.showerror("错误", "无法加载文件内容")
                except Exception as e:
                    self.logger.error(f"加载文件失败: {e}")
                    messagebox.showerror("错误", f"加载文件失败: {e}")
            
            load_and_edit()
            
        except Exception as e:
            self.logger.error(f"打开文件编辑器失败: {e}")
            messagebox.showerror("错误", f"打开文件编辑器失败: {e}")
    
    def _show_enhanced_editor_window(self, remote_path: str, future):
        """显示增强编辑器窗口"""
        try:
            content = future.result()
            
            # 创建增强文本编辑器
            advanced_editor = AdvancedTextEditor(self.parent, self.theme, self.logger)
            
            # 定义保存回调函数
            def save_callback():
                try:
                    new_text = advanced_editor.get_text_content()
                    if advanced_editor.is_window_valid():
                        advanced_editor.status_var.set("保存中...")
                    
                    # 异步保存文件
                    future = self._run_async(self.remote_file_editor.write_file_async(remote_path, new_text))
                    if future:
                        future.add_done_callback(lambda f: self._on_save_result(f, advanced_editor))
                    else:
                        if advanced_editor.is_window_valid():
                            advanced_editor.status_var.set("保存失败")
                        messagebox.showerror("错误", "无法保存文件")
                except Exception as e:
                    self.logger.error(f"保存文件失败: {e}")
                    if advanced_editor.is_window_valid():
                        advanced_editor.status_var.set("保存失败")
                    messagebox.showerror("错误", f"保存文件失败: {e}")
            
            # 创建编辑器窗口
            editor_win = advanced_editor.create_editor_window(
                title=f"编辑: {os.path.basename(remote_path)}",
                content=content,
                save_callback=save_callback
            )
            
            # 绑定保存快捷键
            editor_win.bind('<Control-s>', lambda e: (save_callback(), 'break'))
            
        except Exception as e:
            self.logger.error(f"显示编辑器窗口失败: {e}")
            messagebox.showerror("错误", f"显示编辑器窗口失败: {e}")
    
    def _on_save_result(self, future, advanced_editor):
        """处理保存结果"""
        try:
            success = future.result()
            if success:
                if advanced_editor.is_window_valid():
                    advanced_editor.status_var.set("保存成功")
                # 使用置顶消息显示保存成功
                advanced_editor._show_topmost_message("成功", "文件保存成功", "info")
            else:
                if advanced_editor.is_window_valid():
                    advanced_editor.status_var.set("保存失败")
                messagebox.showerror("错误", "文件保存失败")
        except Exception as e:
            self.logger.error(f"保存结果处理失败: {e}")
            if advanced_editor.is_window_valid():
                advanced_editor.status_var.set("保存失败")
            messagebox.showerror("错误", f"保存失败: {e}")
    
    def open_image_preview(self, remote_path: str):
        """通过HTTP下载图片并弹窗预览"""
        try:
            self.logger.info(f"打开图片预览: {remote_path}")
            
            win = tk.Toplevel(self.parent)
            win.title(os.path.basename(remote_path))
            win.geometry("800x600")
            # 改为transient而不是topmost
            win.transient(self.parent)
            
            # 居中窗口
            self._center_window(win, 800, 600)
            
            canvas = tk.Canvas(win, bg=self.theme.colors['bg_primary'], highlightthickness=0)
            canvas.pack(fill=tk.BOTH, expand=True)
            
            status_var = tk.StringVar(value="加载中...")
            status_label = tk.Label(win, textvariable=status_var, bg=self.theme.colors['bg_primary'])
            status_label.place(relx=0.5, rely=0.98, anchor='s')
            
            def _display_image(img_bytes: bytes):
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
                        try:
                            if not win.winfo_exists():
                                return
                            max_w = win.winfo_width() or 800
                            max_h = win.winfo_height() or 600
                            w, h = pil_img_original.size
                            scale = min(max_w / w, max_h / h, 1)
                            new_size = (int(w * scale), int(h * scale))
                            # Pillow兼容滤镜
                            if hasattr(Image, 'Resampling'):
                                resample_filter = Image.Resampling.LANCZOS
                            else:
                                resample_filter = Image.ANTIALIAS  # type: ignore
                            pil_img = pil_img_original.resize(new_size, resample_filter)
                            photo = ImageTk.PhotoImage(pil_img)
                            canvas.delete('all')
                            canvas.create_image(max_w / 2, max_h / 2, image=photo, anchor='center')
                            canvas.image = photo
                            status_var.set(f"{w}x{h} → {new_size[0]}x{new_size[1]}")
                        except Exception as e:
                            self.logger.error(f"渲染图片失败: {e}")
                    
                    render()
                    
                    # 绑定窗口尺寸变化重新渲染
                    win.bind('<Configure>', lambda e: render())
                    
                except Exception as e:
                    messagebox.showerror("错误", f"无法显示图片: {e}")
                    win.destroy()
            
            # 异步获取图片数据
            def load_image():
                try:
                    future = self._run_async(self.remote_file_editor.download_file_async(remote_path))
                    if future:
                        future.add_done_callback(lambda f: self._on_image_loaded(f, _display_image, status_var, win))
                    else:
                        status_var.set("加载失败")
                        messagebox.showerror("错误", "无法加载图片")
                except Exception as e:
                    self.logger.error(f"加载图片失败: {e}")
                    status_var.set("加载失败")
                    messagebox.showerror("错误", f"加载图片失败: {e}")
            
            load_image()
            
        except Exception as e:
            self.logger.error(f"打开图片预览失败: {e}")
            messagebox.showerror("错误", f"打开图片预览失败: {e}")
    
    def _on_image_loaded(self, future, display_callback, status_var, win):
        """处理图片加载结果"""
        try:
            img_data = future.result()
            if img_data:
                display_callback(img_data)
            else:
                status_var.set("加载失败")
                messagebox.showerror("错误", "无法获取图片数据")
        except Exception as e:
            self.logger.error(f"图片加载结果处理失败: {e}")
            status_var.set("加载失败")
            messagebox.showerror("错误", f"图片加载失败: {e}")
    
    def _center_window(self, win: tk.Toplevel, min_w: int = 400, min_h: int = 300):
        """将Toplevel窗口居中并设置最小尺寸"""
        self.parent.update_idletasks()
        w = max(min_w, win.winfo_reqwidth())
        h = max(min_h, win.winfo_reqheight())
        root_x = self.parent.winfo_x()
        root_y = self.parent.winfo_y()
        root_w = self.parent.winfo_width()
        root_h = self.parent.winfo_height()
        x = root_x + (root_w - w) // 2
        y = root_y + (root_h - h) // 2
        win.geometry(f"{w}x{h}+{x}+{y}") 