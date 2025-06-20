#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
拖拽下载功能测试脚本

用于测试拖拽下载管理器和相关组件的功能
"""

import os
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, MagicMock, patch

# 添加模块路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from fileTransfer.drag_download_manager import DragDownloadManager, DragDownloadTask
from fileTransfer.logger_utils import get_logger


class TestDragDownloadTask(unittest.TestCase):
    """测试拖拽下载任务"""
    
    def test_task_creation(self):
        """测试任务创建"""
        task = DragDownloadTask("/remote/path/file.txt", "/local/path", "file.txt")
        
        self.assertEqual(task.remote_file_path, "/remote/path/file.txt")
        self.assertEqual(task.local_target_path, "/local/path")
        self.assertEqual(task.filename, "file.txt")
        self.assertEqual(task.status, "pending")
        self.assertEqual(task.progress, 0.0)
        self.assertEqual(task.error_message, "")
        self.assertEqual(task.file_size, 0)
        self.assertEqual(task.downloaded_size, 0)


class TestDragDownloadManager(unittest.TestCase):
    """测试拖拽下载管理器"""
    
    def setUp(self):
        """设置测试环境"""
        self.manager = DragDownloadManager()
        self.temp_dir = tempfile.mkdtemp()
        
        # 创建模拟的客户端
        self.mock_telnet_client = Mock()
        self.mock_http_server = Mock()
        self.mock_http_server.get_local_ip.return_value = "127.0.0.1"
        self.mock_http_server.port = 88
        self.mock_http_server.temp_dir = self.temp_dir
        
        self.manager.set_clients(self.mock_telnet_client, self.mock_http_server)
    
    def tearDown(self):
        """清理测试环境"""
        self.manager.cleanup()
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_manager_initialization(self):
        """测试管理器初始化"""
        self.assertIsNotNone(self.manager.logger)
        self.assertEqual(len(self.manager.download_tasks), 0)
        self.assertFalse(self.manager.is_downloading)
        self.assertIsNotNone(self.manager.temp_dir)
    
    def test_set_clients(self):
        """测试设置客户端"""
        telnet_client = Mock()
        http_server = Mock()
        
        self.manager.set_clients(telnet_client, http_server)
        
        self.assertEqual(self.manager.telnet_client, telnet_client)
        self.assertEqual(self.manager.http_server, http_server)
    
    def test_add_download_task(self):
        """测试添加下载任务"""
        remote_path = "/remote/test.txt"
        local_path = self.temp_dir
        
        task = self.manager.add_download_task(remote_path, local_path)
        
        self.assertIsInstance(task, DragDownloadTask)
        self.assertEqual(task.remote_file_path, remote_path)
        self.assertEqual(task.local_target_path, local_path)
        self.assertEqual(task.filename, "test.txt")
        self.assertEqual(len(self.manager.download_tasks), 1)
        self.assertTrue(os.path.exists(local_path))
    
    def test_callback_setting(self):
        """测试回调函数设置"""
        progress_callback = Mock()
        completion_callback = Mock()
        error_callback = Mock()
        
        self.manager.set_progress_callback(progress_callback)
        self.manager.set_completion_callback(completion_callback)
        self.manager.set_error_callback(error_callback)
        
        self.assertEqual(self.manager.progress_callback, progress_callback)
        self.assertEqual(self.manager.completion_callback, completion_callback)
        self.assertEqual(self.manager.error_callback, error_callback)
    
    def test_get_download_status(self):
        """测试获取下载状态"""
        # 添加一些任务
        self.manager.add_download_task("/remote/file1.txt", self.temp_dir)
        self.manager.add_download_task("/remote/file2.txt", self.temp_dir)
        
        status = self.manager.get_download_status()
        
        self.assertEqual(status['total_tasks'], 2)
        self.assertEqual(status['completed_tasks'], 0)
        self.assertEqual(status['failed_tasks'], 0)
        self.assertEqual(status['downloading_tasks'], 0)
        self.assertFalse(status['is_downloading'])
        self.assertEqual(len(status['tasks']), 2)
    
    def test_clear_completed_tasks(self):
        """测试清除已完成任务"""
        # 添加任务并设置状态
        task1 = self.manager.add_download_task("/remote/file1.txt", self.temp_dir)
        task2 = self.manager.add_download_task("/remote/file2.txt", self.temp_dir)
        task3 = self.manager.add_download_task("/remote/file3.txt", self.temp_dir)
        
        task1.status = "completed"
        task2.status = "failed"
        task3.status = "pending"
        
        self.manager.clear_completed_tasks()
        
        # 只有pending状态的任务应该保留
        self.assertEqual(len(self.manager.download_tasks), 1)
        self.assertEqual(self.manager.download_tasks[0].status, "pending")
    
    def test_cancel_all_downloads(self):
        """测试取消所有下载"""
        self.manager.add_download_task("/remote/file1.txt", self.temp_dir)
        self.manager.add_download_task("/remote/file2.txt", self.temp_dir)
        self.manager.is_downloading = True
        
        self.manager.cancel_all_downloads()
        
        self.assertEqual(len(self.manager.download_tasks), 0)
        self.assertFalse(self.manager.is_downloading)
    
    @patch('requests.get')
    def test_download_single_file_success(self, mock_get):
        """测试单文件下载成功"""
        # 设置模拟响应
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'content-length': '100'}
        mock_response.iter_content.return_value = [b'test data chunk']
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # 设置模拟telnet客户端
        self.mock_telnet_client.execute_command.return_value = "copy success"
        
        # 创建测试任务
        task = DragDownloadTask("/remote/test.txt", self.temp_dir, "test.txt")
        
        # 执行下载
        result = self.manager._download_single_file(task)
        
        self.assertTrue(result)
        self.mock_telnet_client.execute_command.assert_called()
        mock_get.assert_called()
    
    def test_start_downloads_without_clients(self):
        """测试没有客户端时开始下载"""
        self.manager.telnet_client = None
        self.manager.http_server = None
        
        self.manager.add_download_task("/remote/test.txt", self.temp_dir)
        self.manager.start_downloads()
        
        # 应该不会开始下载
        self.assertFalse(self.manager.is_downloading)
    
    def test_start_downloads_no_tasks(self):
        """测试没有任务时开始下载"""
        self.manager.start_downloads()
        
        # 应该不会开始下载
        self.assertFalse(self.manager.is_downloading)
    
    def test_start_downloads_already_downloading(self):
        """测试正在下载时开始下载"""
        self.manager.is_downloading = True
        self.manager.add_download_task("/remote/test.txt", self.temp_dir)
        
        self.manager.start_downloads()
        
        # 状态应该保持不变
        self.assertTrue(self.manager.is_downloading)


class TestDragDownloadIntegration(unittest.TestCase):
    """拖拽下载集成测试"""
    
    def setUp(self):
        """设置集成测试环境"""
        self.manager = DragDownloadManager()
        self.temp_dir = tempfile.mkdtemp()
        
        # 创建测试文件
        self.test_file_content = b"This is a test file for drag download"
        self.test_file_path = os.path.join(self.temp_dir, "test_source.txt")
        with open(self.test_file_path, 'wb') as f:
            f.write(self.test_file_content)
    
    def tearDown(self):
        """清理集成测试环境"""
        self.manager.cleanup()
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_callback_execution(self):
        """测试回调函数执行"""
        progress_calls = []
        completion_calls = []
        error_calls = []
        
        def progress_callback(task, progress):
            progress_calls.append((task.filename, progress))
        
        def completion_callback(task, success):
            completion_calls.append((task.filename, success))
        
        def error_callback(task, error_message):
            error_calls.append((task.filename, error_message))
        
        self.manager.set_progress_callback(progress_callback)
        self.manager.set_completion_callback(completion_callback)
        self.manager.set_error_callback(error_callback)
        
        # 创建一个会失败的任务（没有客户端）
        task = self.manager.add_download_task("/nonexistent/file.txt", self.temp_dir)
        
        # 模拟下载失败
        task.status = "failed"
        task.error_message = "Test error"
        
        if self.manager.error_callback:
            self.manager.error_callback(task, task.error_message)
        
        # 验证回调被调用
        self.assertEqual(len(error_calls), 1)
        self.assertEqual(error_calls[0][0], "file.txt")
        self.assertEqual(error_calls[0][1], "Test error")


def run_manual_test():
    """运行手动测试"""
    print("=== 拖拽下载功能手动测试 ===")
    
    # 创建管理器
    manager = DragDownloadManager()
    
    # 设置回调
    def progress_callback(task, progress):
        print(f"下载进度: {task.filename} - {progress:.1f}%")
    
    def completion_callback(task, success):
        if success:
            print(f"下载完成: {task.filename}")
        else:
            print(f"下载失败: {task.filename}")
    
    def error_callback(task, error_message):
        print(f"下载错误: {task.filename} - {error_message}")
    
    manager.set_progress_callback(progress_callback)
    manager.set_completion_callback(completion_callback)
    manager.set_error_callback(error_callback)
    
    print("✅ 拖拽下载管理器初始化完成")
    print("✅ 回调函数设置完成")
    
    # 测试任务管理
    temp_dir = tempfile.mkdtemp()
    try:
        task1 = manager.add_download_task("/test/file1.txt", temp_dir)
        task2 = manager.add_download_task("/test/file2.txt", temp_dir)
        
        print(f"✅ 添加了 {len(manager.download_tasks)} 个下载任务")
        
        # 获取状态
        status = manager.get_download_status()
        print(f"✅ 状态查询: 总任务 {status['total_tasks']}, 进行中 {status['downloading_tasks']}")
        
        # 清理任务
        manager.clear_completed_tasks()
        print("✅ 清理任务完成")
        
        print("✅ 手动测试完成")
        
    finally:
        manager.cleanup()
        import shutil
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


if __name__ == '__main__':
    print("拖拽下载功能测试")
    print("=" * 50)
    
    # 运行单元测试
    print("\n1. 运行单元测试...")
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    print("\n" + "=" * 50)
    
    # 运行手动测试
    print("\n2. 运行手动测试...")
    run_manual_test()
    
    print("\n" + "=" * 50)
    print("测试完成！") 