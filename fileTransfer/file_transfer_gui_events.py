#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI事件处理方法

包含ModernFileTransferGUI类的所有事件处理方法
"""

import asyncio
import os
import shutil
import threading
import tkinter as tk
from tkinter import messagebox, filedialog
from pathlib import Path
from typing import List, Optional
import re


class FileTransferGUIEvents:
    """GUI事件处理方法的Mixin类"""
    
    def _on_connect_clicked(self):
        """处理连接按钮点击事件"""
        if self.is_connected:
            # 如果已连接，则断开连接
            self._disconnect_device()
        else:
            # 如果未连接，则建立连接
            self._connect_device()
    
    def _connect_device(self):
        """连接到远程设备"""
        try:
            # 获取连接参数
            host = self.host_entry.get().strip()
            port = self.port_entry.get().strip()
            username = self.username_entry.get().strip()
            password = self.password_entry.get()
            
            # 验证输入参数
            if not host:
                messagebox.showerror("输入错误", "请输入主机地址")
                return
            
            try:
                port = int(port) if port else 23
            except ValueError:
                messagebox.showerror("输入错误", "端口号必须是数字")
                return
            
            if not username:
                messagebox.showerror("输入错误", "请输入用户名")
                return
            
            if not password:
                messagebox.showerror("输入错误", "请输入密码")
                return
            
            # 禁用连接按钮，防止重复点击
            self.connect_button.configure(state='disabled', text='连接中...')
            self._update_status("正在连接设备...")
            
            # 存储连接配置
            self.connection_config = {
                'host': host,
                'port': port,
                'username': username,
                'password': password
            }
            
            # 在新线程中执行连接操作
            threading.Thread(target=self._connect_async, daemon=True).start()
            
        except Exception as e:
            self.logger.error(f"连接设备时出错: {str(e)}")
            self._reset_connect_button()
            messagebox.showerror("连接错误", f"连接失败: {str(e)}")
    
    def _connect_async(self):
        """异步连接操作"""
        try:
            # 创建telnet客户端
            self.telnet_client = CustomTelnetClient(
                host=self.connection_config['host'],
                port=self.connection_config['port'],
                timeout=30.0,
                connect_timeout=10.0
            )
            
            # 运行异步连接
            future = self._run_async(self._do_connect())
            if future:
                result = future.result(timeout=15)  # 等待连接结果
                if result:
                    self.root.after(0, self._on_connect_success)
                else:
                    self.root.after(0, self._on_connect_failed, "连接失败")
            else:
                self.root.after(0, self._on_connect_failed, "无法启动异步任务")
                
        except Exception as e:
            self.logger.error(f"异步连接失败: {str(e)}")
            self.root.after(0, self._on_connect_failed, str(e))
    
    async def _do_connect(self):
        """执行实际的连接操作"""
        try:
            # 连接并认证
            success = await self.telnet_client.connect(
                username=self.connection_config['username'],
                password=self.connection_config['password'],
                shell_prompt='#'
            )
            
            if success:
                # 测试连接
                await self.telnet_client.execute_command('pwd')
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"Telnet连接失败: {str(e)}")
            return False
    
    def _on_connect_success(self):
        """连接成功回调"""
        self.is_connected = True
        self.connect_button.configure(state='normal', text='断开连接')
        
        # 更新状态指示器
        self.status_indicator.delete('all')
        self.status_indicator.create_oval(2, 2, 10, 10, fill=self.colors['success'], outline='')
        self.connection_status_label.configure(text=f"已连接 ({self.connection_config['host']})")
        
        self._update_status(f"成功连接到 {self.connection_config['host']}")
        self.logger.info(f"成功连接到设备 {self.connection_config['host']}:{self.connection_config['port']}")
        
        # 启动HTTP服务器
        self._start_http_server()
        
        # 刷新远程目录
        self._refresh_directory()
    
    def _on_connect_failed(self, error_msg):
        """连接失败回调"""
        self._reset_connect_button()
        self._update_status(f"连接失败: {error_msg}")
        self.logger.error(f"设备连接失败: {error_msg}")
        messagebox.showerror("连接失败", f"无法连接到设备:\n{error_msg}")
    
    def _disconnect_device(self):
        """断开设备连接"""
        try:
            self.is_connected = False
            self.connect_button.configure(state='disabled', text='断开中...')
            self._update_status("正在断开连接...")
            
            # 停止HTTP服务器
            self._stop_http_server()
            
            # 断开telnet连接
            if self.telnet_client:
                future = self._run_async(self.telnet_client.disconnect())
                if future:
                    future.result(timeout=5)
                self.telnet_client = None
            
            # 更新UI状态
            self._reset_connect_button()
            self.status_indicator.delete('all')
            self.status_indicator.create_oval(2, 2, 10, 10, fill=self.colors['error'], outline='')
            self.connection_status_label.configure(text="未连接")
            
            # 清空目录树
            self.directory_tree.delete(*self.directory_tree.get_children())
            self.current_path_var.set("/")
            
            self._update_status("已断开连接")
            self.logger.info("已断开设备连接")
            
        except Exception as e:
            self.logger.error(f"断开连接时出错: {str(e)}")
            self._reset_connect_button()
    
    def _reset_connect_button(self):
        """重置连接按钮状态"""
        self.connect_button.configure(state='normal', text='连接设备')
    
    def _start_http_server(self):
        """启动HTTP服务器"""
        try:
            if not self.http_server:
                from fileTransfer.http_server import FileHTTPServer
                self.http_server = FileHTTPServer(port=88)
                self.http_server.start()
                
                self.http_status_var.set("HTTP服务: 运行中 (端口88)")
                self.logger.info("HTTP文件服务器已启动，端口: 88")
            
        except Exception as e:
            self.logger.error(f"启动HTTP服务器失败: {str(e)}")
            messagebox.showerror("服务器错误", f"无法启动HTTP服务器:\n{str(e)}")
    
    def _stop_http_server(self):
        """停止HTTP服务器"""
        try:
            if self.http_server:
                self.http_server.stop()
                self.http_server = None
                self.http_status_var.set("HTTP服务: 未启动")
                self.logger.info("HTTP文件服务器已停止")
        except Exception as e:
            self.logger.error(f"停止HTTP服务器失败: {str(e)}")
    
    def _refresh_directory(self):
        """刷新远程目录"""
        if not self.is_connected or not self.telnet_client:
            messagebox.showwarning("未连接", "请先连接到设备")
            return
        
        self._update_status("正在刷新目录...")
        threading.Thread(target=self._refresh_directory_async, daemon=True).start()
    
    def _refresh_directory_async(self):
        """异步刷新目录"""
        try:
            future = self._run_async(self._get_directory_listing(self.current_remote_path))
            if future:
                directory_items = future.result(timeout=10)
                self.root.after(0, self._update_directory_tree, directory_items)
            else:
                self.root.after(0, self._on_directory_refresh_failed, "无法启动异步任务")
                
        except Exception as e:
            self.logger.error(f"刷新目录失败: {str(e)}")
            self.root.after(0, self._on_directory_refresh_failed, str(e))
    
    async def _get_directory_listing(self, path):
        """获取远程目录列表"""
        try:
            # 执行ls命令获取目录内容
            result = await self.telnet_client.execute_command(f'ls -la "{path}"')
            
            # 解析ls命令输出
            items = []
            lines = result.strip().split('\n')
            
            for line in lines[1:]:  # 跳过第一行（总计信息）
                if not line.strip():
                    continue
                
                # 解析ls -la的输出格式
                parts = line.split()
                if len(parts) >= 9:
                    permissions = parts[0]
                    name = ' '.join(parts[8:])
                    
                    # 跳过当前目录和父目录的引用
                    if name in ['.', '..']:
                        continue
                    
                    is_directory = permissions.startswith('d')
                    items.append({
                        'name': name,
                        'is_directory': is_directory,
                        'permissions': permissions,
                        'full_path': os.path.join(path, name)
                    })
            
            return items
            
        except Exception as e:
            self.logger.error(f"获取目录列表失败: {str(e)}")
            return []
    
    def _update_directory_tree(self, items):
        """更新目录树视图"""
        try:
            # 清空现有内容
            self.directory_tree.delete(*self.directory_tree.get_children())
            
            # 添加目录项
            for item in items:
                icon = "📁" if item['is_directory'] else "📄"
                display_name = f"{icon} {item['name']}"
                
                item_id = self.directory_tree.insert('', 'end', text=display_name, 
                                                   values=(item['full_path'], item['is_directory']))
            
            self._update_status("目录刷新完成")
            
        except Exception as e:
            self.logger.error(f"更新目录树失败: {str(e)}")
    
    def _on_directory_refresh_failed(self, error_msg):
        """目录刷新失败回调"""
        self._update_status(f"目录刷新失败: {error_msg}")
        messagebox.showerror("刷新失败", f"无法刷新目录:\n{error_msg}")
    
    def _on_directory_select(self, event):
        """处理目录选择事件"""
        selection = self.directory_tree.selection()
        if selection:
            item = self.directory_tree.item(selection[0])
            full_path, is_directory = item['values']
            
            if is_directory:
                self.current_remote_path = full_path
                self.current_path_var.set(full_path)
    
    def _on_directory_double_click(self, event):
        """处理目录双击事件"""
        selection = self.directory_tree.selection()
        if selection:
            item = self.directory_tree.item(selection[0])
            full_path, is_directory = item['values']
            
            if is_directory:
                self.current_remote_path = full_path
                self.current_path_var.set(full_path)
                self._refresh_directory()
    
    def _go_parent_directory(self):
        """进入上级目录"""
        if self.current_remote_path != '/':
            parent_path = os.path.dirname(self.current_remote_path)
            if not parent_path:
                parent_path = '/'
            self.current_remote_path = parent_path
            self.current_path_var.set(parent_path)
            self._refresh_directory()
    
    def _on_drop(self, event):
        """处理文件拖拽事件"""
        try:
            files = self._parse_drop_files(event.data)
            if files:
                self._add_files_to_queue(files)
            
            # 恢复拖拽区域样式
            self._reset_drop_zone_style()
            
        except Exception as e:
            self.logger.error(f"处理拖拽文件失败: {str(e)}")
            messagebox.showerror("拖拽错误", f"处理拖拽文件时出错:\n{str(e)}")
    
    def _on_drag_enter(self, event):
        """拖拽进入事件"""
        self.drop_zone.configure(bg=self.colors['accent'])
        self.drop_label.configure(bg=self.colors['accent'], fg=self.colors['text_button'])
        self.drop_label.configure(text="释放文件进行上传")
    
    def _on_drag_leave(self, event):
        """拖拽离开事件"""
        self._reset_drop_zone_style()
    
    def _reset_drop_zone_style(self):
        """重置拖拽区域样式"""
        self.drop_zone.configure(bg=self.colors['bg_secondary'])
        self.drop_label.configure(bg=self.colors['bg_secondary'], fg=self.colors['text_secondary'])
        self.drop_label.configure(text="将文件拖拽到此处进行上传\n\n支持多文件同时上传\n点击此处选择文件")
    
    def _on_select_files(self, event):
        """处理点击选择文件事件"""
        try:
            files = filedialog.askopenfilenames(
                title="选择要上传的文件",
                filetypes=[
                    ("所有文件", "*.*"),
                    ("文本文件", "*.txt"),
                    ("图片文件", "*.jpg;*.jpeg;*.png;*.gif;*.bmp"),
                    ("文档文件", "*.pdf;*.doc;*.docx"),
                    ("压缩文件", "*.zip;*.rar;*.7z;*.tar;*.gz")
                ]
            )
            
            if files:
                self._add_files_to_queue(list(files))
                
        except Exception as e:
            self.logger.error(f"选择文件失败: {str(e)}")
            messagebox.showerror("选择错误", f"选择文件时出错:\n{str(e)}")
    
    def _parse_drop_files(self, data):
        """解析拖拽的文件列表"""
        files = []
        try:
            # 处理不同格式的文件路径数据
            if isinstance(data, str):
                # 处理Windows和Unix路径分隔符
                file_paths = data.replace('\\', '/').split()
                for path in file_paths:
                    path = path.strip('{}').strip()
                    if os.path.exists(path):
                        files.append(path)
            else:
                # 尝试直接处理为文件路径
                if os.path.exists(str(data)):
                    files.append(str(data))
                    
        except Exception as e:
            self.logger.error(f"解析拖拽文件失败: {str(e)}")
        
        return files
    
    def _add_files_to_queue(self, files: List[str]):
        """将文件添加到传输队列"""
        try:
            if not self.is_connected:
                messagebox.showwarning("未连接", "请先连接到设备")
                return
            
            added_count = 0
            for file_path in files:
                if os.path.isfile(file_path):
                    # 添加到队列列表框
                    filename = os.path.basename(file_path)
                    display_text = f"{filename} -> {self.current_remote_path}"
                    self.queue_listbox.insert(tk.END, display_text)
                    added_count += 1
                    
                    self.logger.info(f"已添加文件到传输队列: {filename}")
            
            if added_count > 0:
                self._update_status(f"已添加 {added_count} 个文件到传输队列")
            else:
                messagebox.showinfo("无文件", "没有找到有效的文件")
                
        except Exception as e:
            self.logger.error(f"添加文件到队列失败: {str(e)}")
            messagebox.showerror("队列错误", f"添加文件到队列时出错:\n{str(e)}")
    
    def _clear_transfer_queue(self):
        """清空传输队列"""
        try:
            self.queue_listbox.delete(0, tk.END)
            self._update_status("传输队列已清空")
            self.logger.info("传输队列已清空")
        except Exception as e:
            self.logger.error(f"清空队列失败: {str(e)}")
    
    def _start_transfer(self):
        """开始文件传输"""
        if not self.is_connected:
            messagebox.showwarning("未连接", "请先连接到设备")
            return
        
        if self.queue_listbox.size() == 0:
            messagebox.showinfo("无文件", "传输队列为空")
            return
        
        # 禁用传输按钮
        self.start_transfer_button.configure(state='disabled', text='传输中...')
        self._update_status("开始文件传输...")
        
        # 在新线程中执行传输
        threading.Thread(target=self._transfer_files_async, daemon=True).start()
    
    def _transfer_files_async(self):
        """异步执行文件传输"""
        try:
            # 获取队列中的所有文件
            transfer_items = []
            for i in range(self.queue_listbox.size()):
                item_text = self.queue_listbox.get(i)
                # 解析显示文本获取文件信息
                parts = item_text.split(" -> ")
                if len(parts) == 2:
                    filename = parts[0]
                    remote_path = parts[1]
                    transfer_items.append((filename, remote_path))
            
            # 执行传输
            success_count = 0
            for filename, remote_path in transfer_items:
                try:
                    if self._transfer_single_file(filename, remote_path):
                        success_count += 1
                        self.root.after(0, lambda: self._update_status(f"已传输: {filename}"))
                    else:
                        self.root.after(0, lambda: self._update_status(f"传输失败: {filename}"))
                except Exception as e:
                    self.logger.error(f"传输文件 {filename} 失败: {str(e)}")
            
            # 传输完成
            self.root.after(0, self._on_transfer_complete, success_count, len(transfer_items))
            
        except Exception as e:
            self.logger.error(f"文件传输异常: {str(e)}")
            self.root.after(0, self._on_transfer_error, str(e))
    
    def _transfer_single_file(self, filename, remote_path):
        """传输单个文件"""
        try:
            if not self.http_server:
                return False
            
            # 复制文件到HTTP服务器目录
            local_file_path = self._find_local_file(filename)
            if not local_file_path:
                self.logger.error(f"未找到本地文件: {filename}")
                return False
            
            server_file_path = self.http_server.add_file(local_file_path)
            if not server_file_path:
                return False
            
            # 获取本机IP地址和下载URL（使用HTTP服务器的方法，确保正确编码）
            host_ip = self._get_local_ip()
            download_url = self.http_server.get_download_url(os.path.basename(server_file_path), host_ip)
            
            # 通过telnet执行wget下载命令
            future = self._run_async(self._download_file_via_telnet(download_url, remote_path, filename))
            if future:
                result = future.result(timeout=30)
                return result
            
            return False
            
        except Exception as e:
            self.logger.error(f"传输文件失败: {str(e)}")
            return False
    
    def _find_local_file(self, filename):
        """查找本地文件路径"""
        # 这里简化处理，实际应该维护一个文件路径映射
        # 暂时返回None，实际实现中需要改进
        return None
    
    def _get_local_ip(self):
        """获取本机IP地址"""
        import socket
        try:
            # 连接到一个不存在的地址，获取本机IP
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except Exception:
            return "127.0.0.1"
    
    async def _download_file_via_telnet(self, download_url, remote_path, filename):
        """通过telnet执行wget下载"""
        try:
            # 切换到目标目录
            await self.telnet_client.execute_command(f'cd "{remote_path}"')
            
            # 执行wget下载
            wget_cmd = f'wget -O "{filename}" "{download_url}"'
            result = await self.telnet_client.execute_command(wget_cmd, timeout=30)
            
            # 检查下载是否成功
            if "100%" in result or "saved" in result.lower():
                return True
            else:
                self.logger.error(f"wget执行结果: {result}")
                return False
                
        except Exception as e:
            self.logger.error(f"通过telnet下载文件失败: {str(e)}")
            return False
    
    def _on_transfer_complete(self, success_count, total_count):
        """传输完成回调"""
        self.start_transfer_button.configure(state='normal', text='开始传输')
        
        if success_count == total_count:
            self._update_status(f"传输完成: {success_count}/{total_count} 个文件成功")
            messagebox.showinfo("传输完成", f"成功传输 {success_count} 个文件")
        else:
            self._update_status(f"传输完成: {success_count}/{total_count} 个文件成功")
            messagebox.showwarning("传输完成", f"传输完成，但有 {total_count - success_count} 个文件失败")
        
        # 清空传输队列
        self._clear_transfer_queue()
    
    def _on_transfer_error(self, error_msg):
        """传输错误回调"""
        self.start_transfer_button.configure(state='normal', text='开始传输')
        self._update_status(f"传输错误: {error_msg}")
        messagebox.showerror("传输错误", f"文件传输时出错:\n{error_msg}")
    
    def _clear_log(self):
        """清空日志显示"""
        try:
            self.log_text.delete(1.0, tk.END)
            self.logger.info("日志已清空")
        except Exception as e:
            self.logger.error(f"清空日志失败: {str(e)}")
    
    def _save_log(self):
        """保存日志到文件"""
        try:
            log_content = self.log_text.get(1.0, tk.END)
            if not log_content.strip():
                messagebox.showinfo("无内容", "日志为空，无需保存")
                return
            
            file_path = filedialog.asksaveasfilename(
                title="保存日志文件",
                defaultextension=".txt",
                filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
            )
            
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(log_content)
                messagebox.showinfo("保存成功", f"日志已保存到:\n{file_path}")
                self.logger.info(f"日志已保存到: {file_path}")
                
        except Exception as e:
            self.logger.error(f"保存日志失败: {str(e)}")
            messagebox.showerror("保存失败", f"保存日志时出错:\n{str(e)}")
    
    def _append_log(self, message):
        """添加日志消息到界面"""
        try:
            self.log_text.insert(tk.END, message + '\n')
            self.log_text.see(tk.END)
            
            # 限制日志行数，避免内存占用过多
            lines = int(self.log_text.index('end-1c').split('.')[0])
            if lines > 1000:  # 限制最多1000行
                self.log_text.delete(1.0, '100.0')
                
        except Exception:
            pass  # 日志显示失败不应影响主功能
    
    def _update_status(self, message):
        """更新状态栏消息"""
        try:
            self.status_var.set(message)
            self.root.update_idletasks()
        except Exception:
            pass
    
    def _on_closing(self):
        """处理窗口关闭事件"""
        try:
            # 询问用户是否确认退出
            if messagebox.askokcancel("退出确认", "确定要退出文件传输工具吗？"):
                self.logger.info("用户确认退出程序")
                self._cleanup()
                self.root.destroy()
        except Exception as e:
            print(f"关闭程序时出错: {e}")
            self.root.destroy() 