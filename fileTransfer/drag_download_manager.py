#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
拖拽下载管理器

负责处理从远程目录列表拖拽文件到本地的下载功能
支持单文件和多文件拖拽下载，提供进度反馈
"""

import os
import threading
import tempfile
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path

from fileTransfer.logger_utils import get_logger


class DragDownloadTask:
    """拖拽下载任务"""
    
    def __init__(self, remote_file_path: str, local_target_path: str, filename: str):
        """初始化下载任务
        
        Args:
            remote_file_path: 远程文件路径
            local_target_path: 本地目标路径
            filename: 文件名
        """
        self.remote_file_path = remote_file_path
        self.local_target_path = local_target_path
        self.filename = filename
        self.status = "pending"  # pending, downloading, completed, failed
        self.progress = 0.0
        self.error_message = ""
        self.file_size = 0
        self.downloaded_size = 0


class DragDownloadManager:
    """拖拽下载管理器"""
    
    def __init__(self, telnet_client=None, http_server=None, event_loop=None, telnet_lock=None):
        """初始化拖拽下载管理器
        
        Args:
            telnet_client: Telnet客户端实例
            http_server: HTTP服务器实例
            event_loop: 异步事件循环
            telnet_lock: Telnet锁
        """
        self.logger = get_logger(self.__class__)
        self.telnet_client = telnet_client
        self.http_server = http_server
        self.event_loop = event_loop
        self.telnet_lock = telnet_lock
        
        # 下载任务队列
        self.download_tasks: List[DragDownloadTask] = []
        self.is_downloading = False
        
        # 回调函数
        self.progress_callback: Optional[Callable] = None
        self.completion_callback: Optional[Callable] = None
        self.error_callback: Optional[Callable] = None
        
        # 临时文件目录
        self.temp_dir = tempfile.mkdtemp(prefix="drag_download_")
        
        self.logger.info("拖拽下载管理器初始化完成")
    
    def set_clients(self, telnet_client, http_server, event_loop=None, telnet_lock=None):
        """设置客户端实例
        
        Args:
            telnet_client: Telnet客户端
            http_server: HTTP服务器
            event_loop: 异步事件循环
            telnet_lock: Telnet锁
        """
        self.telnet_client = telnet_client
        self.http_server = http_server
        if event_loop:
            self.event_loop = event_loop
        if telnet_lock:
            self.telnet_lock = telnet_lock
        self.logger.debug("已更新客户端实例")
    
    def set_progress_callback(self, callback: Callable):
        """设置进度回调函数
        
        Args:
            callback: 回调函数，接收 (task, progress) 参数
        """
        self.progress_callback = callback
    
    def set_completion_callback(self, callback: Callable):
        """设置完成回调函数
        
        Args:
            callback: 回调函数，接收 (task, success) 参数
        """
        self.completion_callback = callback
    
    def set_error_callback(self, callback: Callable):
        """设置错误回调函数
        
        Args:
            callback: 回调函数，接收 (task, error_message) 参数
        """
        self.error_callback = callback
    
    def add_download_task(self, remote_file_path: str, local_target_path: str) -> DragDownloadTask:
        """添加下载任务
        
        Args:
            remote_file_path: 远程文件路径
            local_target_path: 本地目标路径
            
        Returns:
            创建的下载任务
        """
        filename = os.path.basename(remote_file_path)
        
        # 确保目标目录存在
        os.makedirs(local_target_path, exist_ok=True)
        
        # 创建下载任务
        task = DragDownloadTask(remote_file_path, local_target_path, filename)
        self.download_tasks.append(task)
        
        self.logger.info(f"添加下载任务: {filename} -> {local_target_path}")
        return task
    
    def start_downloads(self):
        """开始执行下载任务"""
        if self.is_downloading:
            self.logger.warning("下载任务正在进行中")
            return
        
        if not self.download_tasks:
            self.logger.info("没有待下载的任务")
            return
        
        # 客户端检查移到下载执行时进行，这里只是启动
        self.logger.info(f"开始执行 {len(self.download_tasks)} 个下载任务")
        self.is_downloading = True
        
        # 在后台线程中执行下载
        threading.Thread(target=self._execute_downloads, daemon=True).start()
    
    def _execute_downloads(self):
        """执行下载任务（后台线程）"""
        try:
            # 检查客户端实例
            if not self.telnet_client or not self.http_server:
                self.logger.error("缺少必要的客户端实例，无法执行下载")
                # 标记所有任务为失败
                for task in self.download_tasks:
                    task.status = "failed"
                    task.error_message = "缺少必要的客户端实例"
                    if self.error_callback:
                        self.error_callback(task, task.error_message)
                return
            
            completed_count = 0
            failed_count = 0
            
            for task in self.download_tasks:
                try:
                    self.logger.info(f"开始下载: {task.filename}")
                    task.status = "downloading"
                    
                    # 执行下载
                    success = self._download_single_file(task)
                    
                    if success:
                        task.status = "completed"
                        task.progress = 100.0
                        completed_count += 1
                        self.logger.info(f"下载完成: {task.filename}")
                        
                        if self.completion_callback:
                            self.completion_callback(task, True)
                    else:
                        task.status = "failed"
                        failed_count += 1
                        self.logger.error(f"下载失败: {task.filename} - {task.error_message}")
                        
                        if self.error_callback:
                            self.error_callback(task, task.error_message)
                
                except Exception as e:
                    task.status = "failed"
                    task.error_message = str(e)
                    failed_count += 1
                    self.logger.error(f"下载异常: {task.filename} - {str(e)}")
                    
                    if self.error_callback:
                        self.error_callback(task, str(e))
            
            self.logger.info(f"下载任务完成: 成功 {completed_count}, 失败 {failed_count}")
            
        except Exception as e:
            self.logger.error(f"执行下载任务时发生异常: {str(e)}")
        finally:
            self.is_downloading = False
            self.download_tasks.clear()
    
    def _download_single_file(self, task: DragDownloadTask) -> bool:
        """下载单个文件
        
        Args:
            task: 下载任务
            
        Returns:
            是否下载成功
        """
        try:
            import requests
            import time
            
            # 生成临时文件名
            temp_filename = f"download_{int(time.time())}_{task.filename}"
            
            # 获取HTTP服务器信息
            if hasattr(self.http_server, 'get_local_ip'):
                local_ip = self.http_server.get_local_ip()
            else:
                local_ip = "127.0.0.1"
            
            port = getattr(self.http_server, 'port', 88)
            
            # 通过telnet读取远程文件内容并写入HTTP服务器目录
            if hasattr(self.http_server, 'temp_dir'):
                http_temp_dir = self.http_server.temp_dir
                local_temp_file = os.path.join(http_temp_dir, temp_filename)
                
                self.logger.debug(f"开始传输文件: {task.remote_file_path} -> {local_temp_file}")
                
                # 首先尝试使用cat命令读取文件内容（适用于文本文件）
                cat_command = f'cat "{task.remote_file_path}"'
                self.logger.debug(f"执行cat命令: {cat_command}")
                
                file_content_result = self._execute_telnet_command(cat_command)
                
                # 检查cat命令是否成功
                if ("No such file" in file_content_result or 
                    "cannot open" in file_content_result or
                    "Permission denied" in file_content_result):
                    raise Exception(f"无法读取文件: {file_content_result}")
                
                # 检查是否为二进制文件（通过检测内容是否包含控制字符）
                is_likely_binary = self._is_likely_binary_content(file_content_result)
                
                if is_likely_binary or len(file_content_result.strip()) == 0:
                    # 对于二进制文件或空文件，使用base64编码传输
                    self.logger.debug("检测到二进制文件或空文件，使用base64传输")
                    base64_command = f'base64 "{task.remote_file_path}"'
                    self.logger.debug(f"执行base64命令: {base64_command}")
                    
                    base64_result = self._execute_telnet_command(base64_command)
                    
                    if ("No such file" in base64_result or 
                        "cannot open" in base64_result or
                        len(base64_result.strip()) == 0):
                        raise Exception(f"base64编码失败: {base64_result}")
                    
                    # 解码base64并写入文件
                    import base64
                    try:
                        # 清理base64输出（移除换行符和空格）
                        clean_base64 = ''.join(base64_result.split())
                        file_data = base64.b64decode(clean_base64)
                        
                        with open(local_temp_file, 'wb') as f:
                            f.write(file_data)
                        
                        self.logger.info(f"通过base64传输文件成功: {temp_filename} ({len(file_data)} bytes)")
                        
                    except Exception as e:
                        raise Exception(f"base64解码失败: {e}")
                else:
                    # 文本文件，直接写入
                    try:
                        with open(local_temp_file, 'w', encoding='utf-8', errors='replace') as f:
                            f.write(file_content_result)
                        
                        self.logger.info(f"通过文本传输文件成功: {temp_filename} ({len(file_content_result)} chars)")
                        
                    except Exception as e:
                        # 如果UTF-8写入失败，尝试其他编码
                        try:
                            with open(local_temp_file, 'w', encoding='gbk', errors='replace') as f:
                                f.write(file_content_result)
                            self.logger.info(f"通过GBK编码传输文件成功: {temp_filename}")
                        except Exception as e2:
                            raise Exception(f"文件写入失败: UTF-8({e}), GBK({e2})")
                
                # 构建下载URL
                download_url = f"http://{local_ip}:{port}/{temp_filename}"
                self.logger.info(f"开始从URL下载: {download_url}")
                
                # 下载文件
                response = requests.get(download_url, stream=True, timeout=30)
                response.raise_for_status()
                
                # 获取文件大小
                task.file_size = int(response.headers.get('content-length', 0))
                
                # 确定最终文件路径
                target_file_path = os.path.join(task.local_target_path, task.filename)
                
                # 如果文件已存在，生成新名称
                if os.path.exists(target_file_path):
                    base_name, ext = os.path.splitext(task.filename)
                    counter = 1
                    while os.path.exists(target_file_path):
                        new_filename = f"{base_name}_{counter}{ext}"
                        target_file_path = os.path.join(task.local_target_path, new_filename)
                        counter += 1
                    
                    self.logger.info(f"目标文件已存在，重命名为: {os.path.basename(target_file_path)}")
                
                # 写入文件
                with open(target_file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            task.downloaded_size += len(chunk)
                            
                            # 更新进度
                            if task.file_size > 0:
                                task.progress = (task.downloaded_size / task.file_size) * 100
                                
                                if self.progress_callback:
                                    self.progress_callback(task, task.progress)
                
                # 清理本地临时文件
                try:
                    if os.path.exists(local_temp_file):
                        os.remove(local_temp_file)
                        self.logger.debug(f"已清理本地临时文件: {local_temp_file}")
                except Exception as e:
                    self.logger.warning(f"清理本地临时文件失败: {e}")
                
                self.logger.info(f"文件已下载到: {target_file_path}")
                return True
            else:
                task.error_message = "HTTP服务器未提供临时目录"
                return False
            
        except Exception as e:
            task.error_message = f"下载文件时发生错误: {str(e)}"
            self.logger.error(task.error_message)
            return False
    
    def get_download_status(self) -> Dict[str, Any]:
        """获取下载状态
        
        Returns:
            下载状态信息
        """
        total_tasks = len(self.download_tasks)
        completed_tasks = sum(1 for task in self.download_tasks if task.status == "completed")
        failed_tasks = sum(1 for task in self.download_tasks if task.status == "failed")
        downloading_tasks = sum(1 for task in self.download_tasks if task.status == "downloading")
        
        return {
            'is_downloading': self.is_downloading,
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'failed_tasks': failed_tasks,
            'downloading_tasks': downloading_tasks,
            'tasks': self.download_tasks
        }
    
    def clear_completed_tasks(self):
        """清除已完成的任务"""
        self.download_tasks = [task for task in self.download_tasks if task.status not in ["completed", "failed"]]
        self.logger.info("已清除完成的下载任务")
    
    def cancel_all_downloads(self):
        """取消所有下载任务"""
        self.is_downloading = False
        self.download_tasks.clear()
        self.logger.info("已取消所有下载任务")
    
    def _is_likely_binary_content(self, content: str) -> bool:
        """检测内容是否可能是二进制文件
        
        Args:
            content: 文件内容字符串
            
        Returns:
            是否可能是二进制文件
        """
        if not content:
            return True
        
        # 检查是否包含控制字符（除了常见的换行符、制表符等）
        control_chars = 0
        printable_chars = 0
        
        for char in content[:1000]:  # 只检查前1000个字符
            char_code = ord(char)
            
            # 控制字符（除了常见的空白字符）
            if char_code < 32 and char not in '\t\n\r':
                control_chars += 1
            # 不可打印字符
            elif char_code > 126:
                control_chars += 1
            else:
                printable_chars += 1
        
        total_chars = control_chars + printable_chars
        if total_chars == 0:
            return True
        
        # 如果控制字符比例超过10%，认为是二进制文件
        control_ratio = control_chars / total_chars
        return control_ratio > 0.1

    def cleanup(self):
        """清理资源"""
        try:
            # 清理临时目录
            import shutil
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                self.logger.info("已清理临时目录")
        except Exception as e:
            self.logger.error(f"清理临时目录失败: {str(e)}")
        
        self.cancel_all_downloads()
        self.logger.info("拖拽下载管理器已清理")
    
    def _execute_telnet_command(self, command: str) -> str:
        """执行telnet命令
        
        Args:
            command: 要执行的命令
            
        Returns:
            命令执行结果
        """
        try:
            import asyncio
            import concurrent.futures
            
            if not self.telnet_client:
                raise Exception("Telnet客户端未设置")
            
            # 如果是异步方法，使用主事件循环执行
            if asyncio.iscoroutinefunction(self.telnet_client.execute_command):
                # 如果有主事件循环，使用它
                if self.event_loop and not self.event_loop.is_closed():
                    # 创建一个Future来获取结果
                    future = concurrent.futures.Future()
                    
                    async def execute_command():
                        try:
                            if self.telnet_lock:
                                async with self.telnet_lock:
                                    result = await self.telnet_client.execute_command(command)
                            else:
                                result = await self.telnet_client.execute_command(command)
                            future.set_result(result)
                        except Exception as e:
                            future.set_exception(e)
                    
                    # 在主事件循环中执行
                    asyncio.run_coroutine_threadsafe(execute_command(), self.event_loop)
                    
                    # 等待结果（最多30秒）
                    return future.result(timeout=30)
                else:
                    # 如果没有主事件循环，创建新的事件循环
                    async def execute_command():
                        if self.telnet_lock:
                            async with self.telnet_lock:
                                return await self.telnet_client.execute_command(command)
                        else:
                            return await self.telnet_client.execute_command(command)
                    
                    # 使用新的事件循环执行
                    loop = asyncio.new_event_loop()
                    try:
                        result = loop.run_until_complete(execute_command())
                        return result
                    finally:
                        loop.close()
            else:
                # 同步执行
                return self.telnet_client.execute_command(command)
                    
        except Exception as e:
            self.logger.error(f"执行telnet命令失败: {e}")
            raise 