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
            http_server: HTTP服务器实例（可选，不再必需）
            event_loop: 异步事件循环
            telnet_lock: Telnet锁
        """
        self.logger = get_logger(self.__class__)
        self.telnet_client = telnet_client
        self.http_server = http_server  # 保留但不再必需
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
        
        self.logger.info("拖拽下载管理器初始化完成（远程HTTP下载模式）")
    
    def set_clients(self, telnet_client, http_server=None, event_loop=None, telnet_lock=None):
        """设置客户端实例
        
        Args:
            telnet_client: Telnet客户端（必需）
            http_server: HTTP服务器（可选）
            event_loop: 异步事件循环
            telnet_lock: Telnet锁
        """
        self.telnet_client = telnet_client
        self.http_server = http_server  # 保留但不再必需
        if event_loop:
            self.event_loop = event_loop
        if telnet_lock:
            self.telnet_lock = telnet_lock
        self.logger.debug("已更新客户端实例（远程HTTP下载模式）")
    
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
            if not self.telnet_client:
                self.logger.error("缺少Telnet客户端实例，无法执行下载")
                # 标记所有任务为失败
                for task in self.download_tasks:
                    task.status = "failed"
                    task.error_message = "缺少Telnet客户端实例"
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
        """下载单个文件 - 从远程设备HTTP服务器下载
        
        Args:
            task: 下载任务
            
        Returns:
            是否下载成功
        """
        try:
            import requests
            
            self.logger.info(f"开始从远程设备下载文件: {task.remote_file_path}")
            
            # 获取远程设备IP地址
            if not self.telnet_client:
                raise Exception("缺少Telnet客户端实例")
            
            # 获取远程设备IP
            remote_ip = getattr(self.telnet_client, 'host', None)
            if not remote_ip:
                raise Exception("无法获取远程设备IP地址")
            
            # 构建远程HTTP下载URL
            import urllib.parse
            encoded_path = urllib.parse.quote(task.remote_file_path, safe='/')
            download_url = f"http://{remote_ip}:88{encoded_path}"
            
            self.logger.info(f"远程HTTP下载URL: {download_url}")
            
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
            
            # 从远程设备HTTP服务器下载文件
            self.logger.debug(f"开始HTTP下载: {download_url} -> {target_file_path}")
            
            response = requests.get(download_url, stream=True, timeout=30)
            response.raise_for_status()
            
            # 获取文件大小
            task.file_size = int(response.headers.get('content-length', 0))
            task.downloaded_size = 0
            
            # 写入文件并更新进度
            with open(target_file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        task.downloaded_size += len(chunk)
                        
                        # 更新进度
                        if task.file_size > 0:
                            task.progress = (task.downloaded_size / task.file_size) * 100
                        else:
                            task.progress = 100.0  # 未知大小的文件，完成时设为100%
                        
                        # 进度回调
                        if self.progress_callback:
                            self.progress_callback(task, task.progress)
            
            # 确保进度为100%
            task.progress = 100.0
            if self.progress_callback:
                self.progress_callback(task, 100.0)
            
            # 获取实际文件大小
            actual_size = os.path.getsize(target_file_path)
            task.file_size = actual_size
            task.downloaded_size = actual_size
            
            self.logger.info(f"文件下载成功: {task.filename} ({actual_size} bytes) -> {target_file_path}")
            return True
            
        except requests.exceptions.RequestException as e:
            task.error_message = f"HTTP下载失败: {str(e)}"
            self.logger.error(task.error_message)
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