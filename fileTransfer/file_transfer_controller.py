#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件传输控制器

负责协调整个文件传输过程
"""

import asyncio
import os
import time
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Optional, Callable, Any
import logging
from datetime import datetime


class TransferStatus(Enum):
    """传输状态枚举"""
    PENDING = "pending"
    PREPARING = "preparing"
    UPLOADING = "uploading"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TransferTask:
    """传输任务数据类"""
    id: str
    source_file: str
    target_path: str
    filename: str
    file_size: int
    status: TransferStatus
    progress: float = 0.0
    error_message: str = ""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    retry_count: int = 0
    temp_file_path: Optional[str] = None
    download_url: Optional[str] = None


class FileTransferController:
    """文件传输控制器"""
    
    def __init__(self, http_server=None, telnet_client=None):
        """初始化文件传输控制器"""
        self.http_server = http_server
        self.telnet_client = telnet_client
        self.transfer_queue: List[TransferTask] = []
        self.active_tasks: Dict[str, TransferTask] = {}
        self.completed_tasks: List[TransferTask] = []
        self.is_running = False
        
        # 回调函数
        self.progress_callback: Optional[Callable[[TransferTask], None]] = None
        self.status_callback: Optional[Callable[[TransferTask], None]] = None
        
        # 配置日志
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.INFO)
    
    def add_transfer_task(self, source_file: str, target_path: str, custom_filename: Optional[str] = None) -> Optional[str]:
        """添加传输任务"""
        try:
            if not os.path.exists(source_file):
                return None
            
            task_id = f"task_{int(time.time())}_{len(self.transfer_queue)}"
            filename = custom_filename or os.path.basename(source_file)
            file_size = os.path.getsize(source_file)
            
            task = TransferTask(
                id=task_id,
                source_file=source_file,
                target_path=target_path,
                filename=filename,
                file_size=file_size,
                status=TransferStatus.PENDING
            )
            
            self.transfer_queue.append(task)
            self.logger.info(f"传输任务已添加: {filename}")
            return task_id
            
        except Exception as e:
            self.logger.error(f"添加传输任务失败: {str(e)}")
            return None
    
    def start_transfer(self):
        """开始传输"""
        if not self.http_server or not self.telnet_client:
            return False
        
        self.is_running = True
        self.logger.info("文件传输已开始")
        return True
    
    def stop_transfer(self):
        """停止传输"""
        self.is_running = False
        self.logger.info("文件传输已停止") 