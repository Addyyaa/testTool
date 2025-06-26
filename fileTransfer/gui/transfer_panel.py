#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
传输面板组件

负责文件传输队列管理、拖拽上传、传输状态监控等功能
"""

import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
import tkinterdnd2 as tkdnd
from typing import List, Dict, Any, Optional, Callable
import os
import re


class TransferPanel:
    """传输面板组件"""
    
    def __init__(self, parent_frame, theme, logger):
        """初始化传输面板"""
        self.parent = parent_frame
        self.theme = theme
        self.logger = logger
        
        # 传输队列和文件映射
        self.file_path_mapping = {}
        self.current_target_path = "/"
        
        # 回调函数
        self.on_start_transfer_callback: Optional[Callable] = None
        self.on_clear_queue_callback: Optional[Callable] = None
        self.on_files_added_callback: Optional[Callable] = None
        
        # 创建面板
        self._create_queue_panel()
        self._create_drop_zone()
        self._create_log_area()
    
    def _create_queue_panel(self):
        """创建现代化传输队列面板 - 占主内容区域底部"""
        # 传输队列容器 - 位于主内容区域底部，减少高度
        self.queue_container = tk.Frame(self.parent, bg=self.theme.colors['bg_primary'])
        self.queue_container.place(relx=0, rely=0.88, relwidth=1.0, relheight=0.12)
        
        # 队列标题区域
        title_frame = tk.Frame(self.queue_container, bg=self.theme.colors['bg_primary'])
        title_frame.place(relx=0, rely=0, relwidth=1.0, relheight=0.25)
        
        queue_title = tk.Label(title_frame, text="🚀 传输队列", 
                             bg=self.theme.colors['bg_primary'], fg=self.theme.colors['text_primary'],
                             font=('Microsoft YaHei UI', 12, 'bold'))
        queue_title.pack(side=tk.LEFT, padx=10)
        
        self.queue_count_label = tk.Label(title_frame, text="(0个文件)", 
                                        bg=self.theme.colors['bg_primary'], fg=self.theme.colors['text_muted'],
                                        font=('Microsoft YaHei UI', 10))
        self.queue_count_label.pack(side=tk.LEFT, padx=5)
        
        # 队列列表区域
        queue_frame = tk.Frame(self.queue_container, bg=self.theme.colors['bg_primary'])
        queue_frame.place(relx=0, rely=0.25, relwidth=0.75, relheight=0.75)
        
        self.queue_listbox = tk.Listbox(queue_frame,
                                      font=('Microsoft YaHei UI', 9),
                                      bg=self.theme.colors['bg_card'], 
                                      fg=self.theme.colors['text_primary'],
                                      selectbackground=self.theme.colors['accent'],
                                      relief='solid', bd=1)
        self.queue_listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 按钮区域
        button_frame = tk.Frame(self.queue_container, bg=self.theme.colors['bg_primary'])
        button_frame.place(relx=0.75, rely=0.25, relwidth=0.25, relheight=0.75)
        
        self.start_transfer_button = tk.Button(button_frame, text="▶️ 开始传输", 
                                             command=self._start_transfer,
                                             bg=self.theme.colors['bg_button'], fg='#ffffff',
                                             font=('Microsoft YaHei UI', 10, 'bold'),
                                             relief='flat', borderwidth=0,
                                             activebackground=self.theme.colors['bg_button_hover'], 
                                             activeforeground='#ffffff',
                                             cursor='hand2')
        self.start_transfer_button.pack(fill=tk.X, padx=10, pady=5)
        
        self.clear_queue_button = tk.Button(button_frame, text="🗑️ 清空队列", 
                                          command=self._clear_transfer_queue,
                                          bg=self.theme.colors['text_muted'], fg='#ffffff',
                                          font=('Microsoft YaHei UI', 10, 'bold'),
                                          relief='flat', borderwidth=0,
                                          activebackground='#4b5563', activeforeground='#ffffff',
                                          cursor='hand2')
        self.clear_queue_button.pack(fill=tk.X, padx=10, pady=5)
    
    def _create_drop_zone(self):
        """创建现代化文件拖拽区域 - 占主内容30%高度"""
        # 拖拽区域容器
        self.drop_zone_container = tk.Frame(self.parent, bg=self.theme.colors['bg_primary'])
        self.drop_zone_container.place(relx=0, rely=0.02, relwidth=1.0, relheight=0.30)
        
        # 拖拽区域标题 - 占容器12%高度
        drop_title = tk.Label(self.drop_zone_container, text="📤 文件传输", 
                            bg=self.theme.colors['bg_primary'], fg=self.theme.colors['text_primary'],
                            font=('Microsoft YaHei UI', 12, 'bold'))
        drop_title.place(relx=0, rely=0, relwidth=1.0, relheight=0.12)
        
        # 现代化拖拽区域 - 带圆角效果
        self.drop_zone = tk.Frame(self.drop_zone_container, 
                                bg=self.theme.colors['bg_accent_light'],
                                relief='solid', borderwidth=1)
        self.drop_zone.place(relx=0, rely=0.15, relwidth=1.0, relheight=0.82)
        
        # 现代化拖拽提示标签
        self.drop_label = tk.Label(self.drop_zone,
                                 text="📁 拖拽文件到此处\n或点击选择文件",
                                 font=('Microsoft YaHei UI', 11),
                                 fg=self.theme.colors['text_secondary'],
                                 bg=self.theme.colors['bg_accent_light'],
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
        """创建现代化日志显示区域 - 占主内容56%高度"""
        # 日志区域容器
        self.log_container = tk.Frame(self.parent, bg=self.theme.colors['bg_primary'])
        self.log_container.place(relx=0, rely=0.32, relwidth=1.0, relheight=0.56)
        
        # 日志区域标题 - 占容器8%高度
        log_title = tk.Label(self.log_container, text="📋 操作日志", 
                           bg=self.theme.colors['bg_primary'], fg=self.theme.colors['text_primary'],
                           font=('Microsoft YaHei UI', 12, 'bold'))
        log_title.place(relx=0, rely=0, relwidth=1.0, relheight=0.08)
        
        # 日志文本区域 - 占容器82%高度
        self.log_frame = tk.Frame(self.log_container, bg=self.theme.colors['bg_primary'])
        self.log_frame.place(relx=0, rely=0.10, relwidth=1.0, relheight=0.80)
        
        # 现代化日志文本控件 - 占日志框架90%高度
        self.log_text = ScrolledText(self.log_frame,
                                   font=('Consolas', 9),
                                   bg=self.theme.colors['bg_card'],
                                   fg=self.theme.colors['text_primary'],
                                   insertbackground=self.theme.colors['text_primary'],
                                   selectbackground=self.theme.colors['accent'],
                                   wrap=tk.WORD,
                                   relief='solid', bd=1)
        self.log_text.place(relx=0, rely=0, relwidth=1.0, relheight=0.90)
        
        # 现代化日志控制按钮 - 占日志框架10%高度
        self.clear_log_button = tk.Button(self.log_frame, text="🗑️ 清空", 
                                         command=self._clear_log,
                                         bg=self.theme.colors['bg_button'], fg=self.theme.colors['text_button'],
                                         font=('Microsoft YaHei UI', 9, 'bold'),
                                         relief='flat', borderwidth=0,
                                         activebackground=self.theme.colors['bg_button_hover'], 
                                         activeforeground=self.theme.colors['text_button'],
                                         cursor='hand2')
        self.clear_log_button.place(relx=0, rely=0.91, relwidth=0.48, relheight=0.09)
        
        self.save_log_button = tk.Button(self.log_frame, text="💾 保存", 
                                        command=self._save_log,
                                        bg=self.theme.colors['bg_button'], fg=self.theme.colors['text_button'],
                                        font=('Microsoft YaHei UI', 9, 'bold'),
                                        relief='flat', borderwidth=0,
                                        activebackground=self.theme.colors['bg_button_hover'], 
                                        activeforeground=self.theme.colors['text_button'],
                                        cursor='hand2')
        self.save_log_button.place(relx=0.52, rely=0.91, relwidth=0.48, relheight=0.09)
    
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
    
    def _on_drag_enter(self, event):
        """拖拽进入"""
        self.drop_zone.configure(bg=self.theme.colors['accent'])
        self.drop_label.configure(bg=self.theme.colors['accent'], fg=self.theme.colors['text_button'])
        self.drop_label.configure(text="释放文件进行上传")
    
    def _on_drag_leave(self, event):
        """拖拽离开"""
        self._reset_drop_zone_style()
    
    def _reset_drop_zone_style(self):
        """重置拖拽区域样式"""
        self.drop_zone.configure(bg=self.theme.colors['bg_accent_light'])
        self.drop_label.configure(bg=self.theme.colors['bg_accent_light'], fg=self.theme.colors['text_secondary'])
        self.drop_label.configure(text="📁 拖拽文件到此处\n或点击选择文件")
    
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
    
    def _parse_drop_files(self, data):
        """解析拖拽文件"""
        files = []
        try:
            if isinstance(data, str):
                self.logger.debug(f"原始拖拽数据: {repr(data)}")
                
                # 处理不同的拖拽数据格式
                if '{' in data and '}' in data:
                    # 格式: {path1} {path2} ...
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
                    # 简单格式，尝试按空格分割
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
        return files
    
    def _get_file_type_indicator(self, file_path):
        """获取文件类型标识"""
        try:
            # 1. 通过扩展名检测常见的二进制文件
            binary_extensions = {
                '.exe', '.bin', '.so', '.dll', '.dylib', '.a', '.o', '.obj',
                '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz',
                '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico', '.tiff',
                '.mp3', '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv',
                '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
                '.deb', '.rpm', '.apk', '.ipa', '.dmg', '.iso'
            }
            
            file_ext = os.path.splitext(file_path)[1].lower()
            if file_ext in binary_extensions:
                return "[二进制]"
            
            # 2. 通过文件内容检测
            with open(file_path, 'rb') as f:
                # 读取前1024字节进行检测
                chunk = f.read(1024)
                if not chunk:
                    return "[文本]"
                
                # 检测空字节（二进制文件的典型特征）
                if b'\x00' in chunk:
                    return "[二进制]"
                
                # 检测非ASCII字符的比例
                non_ascii_count = sum(1 for byte in chunk if byte > 127)
                non_ascii_ratio = non_ascii_count / len(chunk)
                
                # 如果非ASCII字符超过30%，认为是二进制文件
                if non_ascii_ratio > 0.3:
                    return "[二进制]"
                
                # 检测控制字符（除了常见的换行、制表符等）
                control_chars = sum(1 for byte in chunk if byte < 32 and byte not in (9, 10, 13))
                control_ratio = control_chars / len(chunk)
                
                # 如果控制字符超过5%，认为是二进制文件
                if control_ratio > 0.05:
                    return "[二进制]"
            
            return "[文本]"
            
        except Exception as e:
            self.logger.warning(f"检测文件类型失败: {e}")
            # 出错时默认为文本文件
            return "[文本]"
    
    def _add_files_to_queue(self, files: List[str]):
        """添加文件到队列"""
        self.logger.info(f"开始添加 {len(files)} 个文件到队列")
        
        added_count = 0
        for file_path in files:
            self.logger.debug(f"检查文件: {file_path}")
            if os.path.isfile(file_path):
                filename = os.path.basename(file_path)
                # 检测文件类型
                file_type_indicator = self._get_file_type_indicator(file_path)
                # 显示文件名和类型标识
                display_text = f"{filename} {file_type_indicator} -> (当前目录)"
                self.queue_listbox.insert(tk.END, display_text)
                self.file_path_mapping[filename] = file_path
                added_count += 1
                self.logger.info(f"已添加文件: {filename} {file_type_indicator}")
            else:
                self.logger.warning(f"文件不存在或不是文件: {file_path}")
        
        if added_count > 0:
            self.logger.info(f"成功添加 {added_count} 个文件到队列")
            self._update_queue_count()
            # 更新队列显示，显示当前路径
            self._update_queue_display()
            
            # 调用回调
            if self.on_files_added_callback:
                self.on_files_added_callback(added_count)
        else:
            self.logger.warning("没有有效文件被添加到队列")
    
    def _clear_transfer_queue(self):
        """清空队列"""
        self.queue_listbox.delete(0, tk.END)
        self.file_path_mapping.clear()
        self._update_queue_count()
        
        # 移除递归调用 - 回调应该由外部调用方决定是否执行
        # if self.on_clear_queue_callback:
        #     self.on_clear_queue_callback()
    
    def _start_transfer(self):
        """开始传输"""
        if self.on_start_transfer_callback:
            self.on_start_transfer_callback()
    
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
            
            # 获取所有文件名和类型标识
            file_items = []
            for i in range(queue_size):
                item_text = self.queue_listbox.get(i)
                # 提取文件名和类型标识（在 -> 之前的部分）
                if " -> " in item_text:
                    filename_with_type = item_text.split(" -> ")[0]
                    file_items.append(filename_with_type)
                else:
                    file_items.append(item_text)
            
            # 清空队列
            self.queue_listbox.delete(0, tk.END)
            
            # 重新添加，使用当前路径
            for filename_with_type in file_items:
                display_text = f"{filename_with_type} -> {self.current_target_path}"
                self.queue_listbox.insert(tk.END, display_text)
                
            self.logger.debug(f"队列显示已更新，当前目标路径: {self.current_target_path}")
            
        except Exception as e:
            self.logger.error(f"更新队列显示失败: {str(e)}")
    
    def set_target_path(self, path: str):
        """设置目标路径"""
        self.current_target_path = path
        self._update_queue_display()
    
    def get_transfer_tasks(self) -> List[tuple]:
        """获取传输任务列表"""
        transfer_tasks = []
        total_count = self.queue_listbox.size()
        
        for i in range(total_count):
            item_text = self.queue_listbox.get(i)
            parts = item_text.split(" -> ")
            if len(parts) >= 1:
                filename_with_type = parts[0]
                # 提取文件名（去掉类型标识）
                if "[文本]" in filename_with_type:
                    filename = filename_with_type.replace(" [文本]", "")
                elif "[二进制]" in filename_with_type:
                    filename = filename_with_type.replace(" [二进制]", "")
                else:
                    filename = filename_with_type
                
                if filename in self.file_path_mapping:
                    local_file = self.file_path_mapping[filename]
                    transfer_tasks.append((local_file, self.current_target_path, filename))
        
        return transfer_tasks
    
    def update_transfer_button_state(self, enabled: bool, text: str = None):
        """更新传输按钮状态"""
        state = 'normal' if enabled else 'disabled'
        self.start_transfer_button.configure(state=state)
        if text:
            self.start_transfer_button.configure(text=text)
    
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
    
    def append_log(self, message: str):
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
    
    def set_start_transfer_callback(self, callback: Callable):
        """设置开始传输回调"""
        self.on_start_transfer_callback = callback
    
    def set_clear_queue_callback(self, callback: Callable):
        """设置清空队列回调"""
        self.on_clear_queue_callback = callback
    
    def set_files_added_callback(self, callback: Callable):
        """设置文件添加回调"""
        self.on_files_added_callback = callback 