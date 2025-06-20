#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
远程文件编辑器组件

提供远程文件编辑和图片预览功能
"""

import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from tkinter import messagebox
import os
import sys
import asyncio
from typing import Optional, Any

# 添加父目录到系统路径以支持导入
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from file_transfer_controller import RemoteFileEditor


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
                        future.add_done_callback(lambda f: self._show_editor_window(remote_path, f))
                    else:
                        messagebox.showerror("错误", "无法加载文件内容")
                except Exception as e:
                    self.logger.error(f"加载文件失败: {e}")
                    messagebox.showerror("错误", f"加载文件失败: {e}")
            
            load_and_edit()
            
        except Exception as e:
            self.logger.error(f"打开文件编辑器失败: {e}")
            messagebox.showerror("错误", f"打开文件编辑器失败: {e}")
    
    def _show_editor_window(self, remote_path: str, future):
        """显示编辑器窗口"""
        try:
            content = future.result()
            
            # 创建编辑窗口
            editor_win = tk.Toplevel(self.parent)
            editor_win.title(f"编辑: {os.path.basename(remote_path)}")
            editor_win.geometry("800x600")
            editor_win.configure(bg=self.theme.colors['bg_primary'])
            
            # 置顶并居中
            editor_win.attributes('-topmost', True)
            self._center_window(editor_win, 800, 600)
            
            # 文本区域
            text_area = ScrolledText(editor_win, font=('Consolas', 11), wrap=tk.NONE, undo=True)
            text_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # 插入内容
            text_area.delete('1.0', tk.END)
            text_area.insert(tk.END, content)
            
            status_var = tk.StringVar(value="已加载，Ctrl+S 保存")
            status_label = tk.Label(editor_win, textvariable=status_var, 
                                  bg=self.theme.colors['bg_primary'], fg=self.theme.colors['text_secondary'])
            status_label.pack(anchor='w', padx=12)
            
            def _save_content():
                try:
                    new_text = text_area.get('1.0', tk.END)
                    status_var.set("保存中...")
                    
                    # 异步保存文件
                    future = self._run_async(self.remote_file_editor.write_file_async(remote_path, new_text))
                    if future:
                        future.add_done_callback(lambda f: self._on_save_result(f, status_var, editor_win))
                    else:
                        status_var.set("保存失败")
                        messagebox.showerror("错误", "无法保存文件")
                except Exception as e:
                    self.logger.error(f"保存文件失败: {e}")
                    status_var.set("保存失败")
                    messagebox.showerror("错误", f"保存文件失败: {e}")
            
            # 保存按钮
            btn_frame = tk.Frame(editor_win, bg=self.theme.colors['bg_primary'])
            btn_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
            save_btn = tk.Button(btn_frame, text="💾 保存", command=_save_content, 
                               bg=self.theme.colors['bg_button'], fg='#ffffff', relief='flat')
            save_btn.pack(side=tk.LEFT)
            
            # 绑定快捷键
            editor_win.bind('<Control-s>', lambda e: (_save_content(), 'break'))
            
        except Exception as e:
            self.logger.error(f"显示编辑器窗口失败: {e}")
            messagebox.showerror("错误", f"显示编辑器窗口失败: {e}")
    
    def _on_save_result(self, future, status_var, editor_win):
        """处理保存结果"""
        try:
            success = future.result()
            if success:
                status_var.set("保存成功")
                messagebox.showinfo("成功", "文件保存成功")
            else:
                status_var.set("保存失败")
                messagebox.showerror("错误", "文件保存失败")
        except Exception as e:
            self.logger.error(f"保存结果处理失败: {e}")
            status_var.set("保存失败")
            messagebox.showerror("错误", f"保存失败: {e}")
    
    def open_image_preview(self, remote_path: str):
        """通过HTTP下载图片并弹窗预览"""
        try:
            self.logger.info(f"打开图片预览: {remote_path}")
            
            win = tk.Toplevel(self.parent)
            win.title(os.path.basename(remote_path))
            win.geometry("800x600")
            win.attributes('-topmost', True)
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
                            if not canvas.winfo_exists():
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