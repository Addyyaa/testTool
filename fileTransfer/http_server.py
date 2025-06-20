#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTTP文件服务器模块

这个模块提供了一个轻量级的HTTP文件服务器，用于远程设备通过wget下载文件。
服务器会在指定端口启动，并提供临时文件目录的文件下载服务。

Author: AI Assistant
Date: 2024
Version: 1.0
"""

import os
import shutil
import tempfile
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional, Dict, List
import logging
import urllib.parse
from datetime import datetime
from fileTransfer.logger_utils import get_logger


class FileHTTPRequestHandler(BaseHTTPRequestHandler):
    """
    自定义HTTP请求处理器
    
    处理文件下载请求，支持：
    - 静态文件服务
    - 文件下载
    - 目录浏览（可选）
    - 错误处理
    """
    
    def __init__(self, *args, server_instance=None, **kwargs):
        """初始化请求处理器"""
        self.server_instance = server_instance
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """处理GET请求"""
        try:
            # 解析URL路径
            parsed_path = urllib.parse.urlparse(self.path)
            encoded_file_path = parsed_path.path.lstrip('/')
            
            # URL解码文件路径，处理中文字符和特殊符号
            try:
                file_path = urllib.parse.unquote(encoded_file_path, encoding='utf-8')
                self.server_instance.logger.debug(f"  - UTF-8解码成功: {file_path}")
            except UnicodeDecodeError:
                # 如果UTF-8解码失败，尝试其他编码
                try:
                    file_path = urllib.parse.unquote(encoded_file_path, encoding='gbk')
                    self.server_instance.logger.debug(f"  - GBK解码成功: {file_path}")
                except UnicodeDecodeError:
                    file_path = encoded_file_path
                    self.server_instance.logger.warning(f"  - 解码失败，使用原始路径: {file_path}")
            
            # 记录访问日志  
            self.server_instance.logger.info(f"收到下载请求: {self.client_address[0]} -> 原始路径: {self.path}")
            self.server_instance.logger.info(f"  - 编码路径: {encoded_file_path}")
            self.server_instance.logger.info(f"  - 解码路径: {file_path}")
            
            if not file_path or file_path == '/':
                # 根路径请求，返回文件列表
                self._send_file_list()
                return
            
            # 构造完整文件路径
            full_path = os.path.join(self.server_instance.temp_dir, file_path)
            self.server_instance.logger.info(f"  - 完整路径: {full_path}")
            self.server_instance.logger.info(f"  - 文件存在: {os.path.exists(full_path)}")
            
            # 如果文件不存在，列出临时目录内容进行调试
            if not os.path.exists(full_path):
                try:
                    temp_files = os.listdir(self.server_instance.temp_dir)
                    self.server_instance.logger.error(f"  - 临时目录内容: {temp_files}")
                except Exception as list_error:
                    self.server_instance.logger.error(f"  - 无法列出临时目录: {list_error}")
            
            # 安全检查：防止路径遍历攻击
            if not self._is_safe_path(full_path):
                self.server_instance.logger.error(f"  - 路径不安全: {full_path}")
                self._send_error_response(403, "Forbidden")
                return
            
            # 检查文件是否存在
            if not os.path.exists(full_path):
                self.server_instance.logger.error(f"  - 文件不存在: {full_path}")
                self._send_error_response(404, "File Not Found")
                return
            
            # 检查是否为文件
            if not os.path.isfile(full_path):
                self.server_instance.logger.error(f"  - 不是文件: {full_path}")
                self._send_error_response(400, "Not a File")
                return
            
            # 发送文件
            self.server_instance.logger.info(f"  - 开始发送文件: {full_path}")
            self._send_file(full_path, file_path)
            
        except Exception as e:
            self.server_instance.logger.error(f"处理GET请求失败: {str(e)}")
            import traceback
            self.server_instance.logger.error(f"详细错误: {traceback.format_exc()}")
            self._send_error_response(500, "Internal Server Error")
    
    def do_HEAD(self):
        """处理HEAD请求"""
        try:
            parsed_path = urllib.parse.urlparse(self.path)
            file_path = parsed_path.path.lstrip('/')
            
            if not file_path:
                self._send_headers(200, "text/html", 0)
                return
            
            full_path = os.path.join(self.server_instance.temp_dir, file_path)
            
            if not self._is_safe_path(full_path) or not os.path.exists(full_path):
                self._send_headers(404, "text/plain", 0)
                return
            
            if os.path.isfile(full_path):
                file_size = os.path.getsize(full_path)
                content_type = self._get_content_type(file_path)
                self._send_headers(200, content_type, file_size)
            else:
                self._send_headers(400, "text/plain", 0)
                
        except Exception as e:
            self.server_instance.logger.error(f"处理HEAD请求失败: {str(e)}")
            self._send_headers(500, "text/plain", 0)
    
    def _is_safe_path(self, file_path):
        """检查文件路径是否安全（防止路径遍历攻击）"""
        try:
            # 获取规范化的绝对路径
            real_path = os.path.realpath(file_path)
            real_temp_dir = os.path.realpath(self.server_instance.temp_dir)
            
            # 检查文件路径是否在临时目录内
            return real_path.startswith(real_temp_dir)
            
        except Exception:
            return False
    
    def _send_file(self, file_path, requested_path):
        """发送文件内容"""
        try:
            file_size = os.path.getsize(file_path)
            content_type = self._get_content_type(requested_path)
            
            # 检测是否为二进制文件
            is_binary = self._is_binary_file(file_path)
            file_type_indicator = "[二进制]" if is_binary else "[文本]"
            
            # 发送响应头
            self._send_headers(200, content_type, file_size)
            
            # 发送文件内容
            with open(file_path, 'rb') as f:
                shutil.copyfileobj(f, self.wfile)
            
            self.server_instance.logger.info(f"文件下载完成: {requested_path} ({file_size} bytes) {file_type_indicator}")
            
            # 如果是需要可执行权限的二进制文件，记录需要添加可执行权限
            if self._is_executable_binary_file(file_path):
                self._schedule_chmod_executable(requested_path)

            # 延迟删除临时文件，避免Windows文件占用问题
            import threading
            def delayed_remove():
                import time
                time.sleep(2)  # 增加等待时间到2秒
                try:
                    # 直接删除文件，不通过remove_file方法
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        self.server_instance.logger.info(f"延迟删除文件成功: {os.path.basename(file_path)}")
                        
                        # 从映射中移除
                        for source_path, temp_path in list(self.server_instance.file_mapping.items()):
                            if temp_path == file_path:
                                del self.server_instance.file_mapping[source_path]
                                break
                    else:
                        self.server_instance.logger.warning(f"延迟删除时文件已不存在: {file_path}")
                except Exception as e:
                    self.server_instance.logger.error(f"延迟删除文件失败: {os.path.basename(file_path)} - {e}")
            
            threading.Thread(target=delayed_remove, daemon=True).start()
            
        except Exception as e:
            self.server_instance.logger.error(f"发送文件失败: {str(e)}")
            raise
    
    def _send_file_list(self):
        """发送文件列表页面"""
        try:
            files = []
            temp_dir = self.server_instance.temp_dir
            
            for item in os.listdir(temp_dir):
                item_path = os.path.join(temp_dir, item)
                if os.path.isfile(item_path):
                    file_size = os.path.getsize(item_path)
                    file_time = datetime.fromtimestamp(os.path.getmtime(item_path))
                    files.append({
                        'name': item,
                        'size': file_size,
                        'time': file_time.strftime('%Y-%m-%d %H:%M:%S')
                    })
            
            # 生成HTML页面
            html = self._generate_file_list_html(files)
            html_bytes = html.encode('utf-8')
            
            self._send_headers(200, "text/html; charset=utf-8", len(html_bytes))
            self.wfile.write(html_bytes)
            
        except Exception as e:
            self.server_instance.logger.error(f"发送文件列表失败: {str(e)}")
            self._send_error_response(500, "Internal Server Error")
    
    def _generate_file_list_html(self, files):
        """生成文件列表HTML页面"""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>文件传输服务器</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
                .file-list {{ margin-top: 20px; }}
                .file-item {{ padding: 10px; border-bottom: 1px solid #eee; }}
                .file-item:hover {{ background-color: #f5f5f5; }}
                .file-name {{ font-weight: bold; color: #333; }}
                .file-info {{ color: #666; font-size: 0.9em; }}
                a {{ text-decoration: none; }}
                a:hover {{ text-decoration: underline; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📁 文件传输服务器</h1>
                <p>可用文件列表 (端口: {port})</p>
            </div>
            <div class="file-list">
        """.format(port=self.server_instance.port)
        
        if not files:
            html += "<p>暂无可下载文件</p>"
        else:
            for file_info in files:
                # 对文件名进行URL编码，确保中文字符正确处理
                encoded_filename = urllib.parse.quote(file_info['name'], safe='')
                html += f"""
                <div class="file-item">
                    <a href="/{encoded_filename}" class="file-name">📄 {file_info['name']}</a>
                    <div class="file-info">
                        大小: {self._format_file_size(file_info['size'])} | 
                        修改时间: {file_info['time']}
                    </div>
                </div>
                """
        
        html += """
            </div>
            <div style="margin-top: 40px; color: #888; font-size: 0.8em;">
                <p>提示: 直接点击文件名即可下载，或使用 wget 命令下载</p>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _format_file_size(self, size):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    def _send_headers(self, status_code, content_type, content_length):
        """发送HTTP响应头"""
        self.send_response(status_code)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(content_length))
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
    
    def _send_error_response(self, status_code, message):
        """发送错误响应"""
        error_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>错误 {status_code}</title>
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; margin-top: 100px; }}
                .error {{ color: #cc0000; }}
            </style>
        </head>
        <body>
            <h1 class="error">错误 {status_code}</h1>
            <p>{message}</p>
        </body>
        </html>
        """
        error_bytes = error_html.encode('utf-8')
        
        self.send_response(status_code)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(error_bytes)))
        self.end_headers()
        self.wfile.write(error_bytes)
    
    def _get_content_type(self, file_path):
        """根据文件扩展名获取Content-Type"""
        import mimetypes
        
        content_type, _ = mimetypes.guess_type(file_path)
        if content_type is None:
            content_type = 'application/octet-stream'
        
        return content_type
    
    def _is_binary_file(self, file_path):
        """检测文件是否为二进制文件"""
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
                return True
            
            # 2. 通过文件内容检测
            with open(file_path, 'rb') as f:
                # 读取前1024字节进行检测
                chunk = f.read(1024)
                if not chunk:
                    return False
                
                # 检测空字节（二进制文件的典型特征）
                if b'\x00' in chunk:
                    return True
                
                # 检测非ASCII字符的比例
                non_ascii_count = sum(1 for byte in chunk if byte > 127)
                non_ascii_ratio = non_ascii_count / len(chunk)
                
                # 如果非ASCII字符超过30%，认为是二进制文件
                if non_ascii_ratio > 0.3:
                    return True
                
                # 检测控制字符（除了常见的换行、制表符等）
                control_chars = sum(1 for byte in chunk if byte < 32 and byte not in (9, 10, 13))
                control_ratio = control_chars / len(chunk)
                
                # 如果控制字符超过5%，认为是二进制文件
                if control_ratio > 0.05:
                    return True
            
            return False
            
        except Exception as e:
            self.server_instance.logger.warning(f"检测文件类型失败: {e}")
            # 出错时默认为文本文件
            return False
    
    def _is_executable_binary_file(self, file_path):
        """检测文件是否为需要可执行权限的二进制文件"""
        try:
            # 只有这些扩展名的文件才需要可执行权限
            executable_extensions = {
                '.exe', '.bin', '.so', '.dll', '.dylib', '.a', '.o', '.obj',
                '.deb', '.rpm', '.apk', '.ipa'
            }
            
            file_ext = os.path.splitext(file_path)[1].lower()
            if file_ext in executable_extensions:
                return True
            
            # 对于没有扩展名的文件，通过内容检测
            if not file_ext:
                # 检测是否为ELF文件（Linux可执行文件）
                try:
                    with open(file_path, 'rb') as f:
                        header = f.read(4)
                        if header == b'\x7fELF':  # ELF魔数
                            return True
                except Exception:
                    pass
            
            return False
            
        except Exception as e:
            self.server_instance.logger.warning(f"检测可执行文件类型失败: {e}")
            return False
    
    def _schedule_chmod_executable(self, requested_path):
        """安排为二进制文件添加可执行权限"""
        try:
            # 延迟执行chmod命令，确保文件传输完成
            import threading
            def delayed_chmod():
                import time
                time.sleep(3)  # 等待3秒确保文件传输完成
                try:
                    # 通过telnet连接执行chmod命令
                    if hasattr(self.server_instance, 'telnet_client') and self.server_instance.telnet_client:
                        import asyncio
                        
                        # 创建异步任务执行chmod
                        async def execute_chmod():
                            try:
                                # 获取telnet客户端
                                telnet_client = self.server_instance.telnet_client
                                
                                # 执行chmod +x命令
                                chmod_cmd = f'chmod +x "{requested_path}"'
                                self.server_instance.logger.info(f"为二进制文件添加可执行权限: {chmod_cmd}")
                                
                                # 执行命令
                                result = await telnet_client.execute_command(chmod_cmd, timeout=10)
                                
                                # 验证权限是否添加成功
                                verify_cmd = f'ls -l "{requested_path}"'
                                verify_result = await telnet_client.execute_command(verify_cmd, timeout=5)
                                
                                self.server_instance.logger.info(f"权限验证结果: {verify_result.strip()}")
                                
                                if 'x' in verify_result:
                                    self.server_instance.logger.info(f"✅ 成功为二进制文件添加可执行权限: {requested_path}")
                                else:
                                    self.server_instance.logger.warning(f"⚠️ 可执行权限可能未成功添加: {requested_path}")
                                    
                            except Exception as e:
                                self.server_instance.logger.error(f"❌ 添加可执行权限失败: {requested_path} - {e}")
                        
                        # 使用线程池执行异步任务，避免事件循环冲突
                        try:
                            # 检查是否有运行中的事件循环
                            try:
                                current_loop = asyncio.get_running_loop()
                                # 如果有运行中的循环，使用concurrent.futures在线程中执行
                                import concurrent.futures
                                
                                def run_in_thread():
                                    # 在新线程中创建新的事件循环
                                    new_loop = asyncio.new_event_loop()
                                    asyncio.set_event_loop(new_loop)
                                    try:
                                        return new_loop.run_until_complete(execute_chmod())
                                    finally:
                                        new_loop.close()
                                
                                # 在线程池中执行
                                with concurrent.futures.ThreadPoolExecutor() as executor:
                                    future = executor.submit(run_in_thread)
                                    future.result(timeout=15)  # 15秒超时
                                    
                            except RuntimeError:
                                # 没有运行中的事件循环，直接创建新的
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                try:
                                    loop.run_until_complete(execute_chmod())
                                finally:
                                    loop.close()
                                    
                        except Exception as e:
                            self.server_instance.logger.error(f"❌ 执行chmod命令失败: {e}")
                    else:
                        self.server_instance.logger.warning(f"⚠️ 无法获取telnet连接，跳过权限设置: {requested_path}")
                        
                except Exception as e:
                    self.server_instance.logger.error(f"❌ 延迟chmod执行失败: {requested_path} - {e}")
            
            threading.Thread(target=delayed_chmod, daemon=True).start()
            
        except Exception as e:
            self.server_instance.logger.error(f"安排chmod任务失败: {e}")
    
    def log_message(self, format, *args):
        """重写日志输出方法，使用自定义logger"""
        if self.server_instance and self.server_instance.logger:
            self.server_instance.logger.debug(f"HTTP: {format % args}")


class FileHTTPServer:
    """
    文件HTTP服务器
    
    提供简单的HTTP文件服务，用于文件传输：
    - 在指定端口启动HTTP服务
    - 管理临时文件目录
    - 支持文件上传和下载
    - 自动清理临时文件
    """
    
    def __init__(self, port: int = 88, temp_dir: Optional[str] = None, parent_logger=None, telnet_client=None):
        """
        初始化HTTP文件服务器
        
        Args:
            port (int): 服务端口，默认88
            temp_dir (str, optional): 临时文件目录，默认自动创建
            parent_logger (logging.Logger, optional): 父logger
            telnet_client (optional): telnet客户端，用于执行chmod命令
        """
        self.port = port
        self.temp_dir = temp_dir or self._create_temp_dir()
        self.server: Optional[HTTPServer] = None
        self.server_thread: Optional[threading.Thread] = None
        self.is_running = False
        self.file_mapping: Dict[str, str] = {}  # 原始文件路径到临时文件路径的映射
        self.telnet_client = telnet_client  # 添加telnet客户端引用
        
        # 配置日志
        self.logger = (parent_logger or get_logger(self.__class__)
                       ).getChild(self.__class__.__name__)
        
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        
        self.logger.info(f"HTTP文件服务器初始化完成，端口: {port}, 临时目录: {self.temp_dir}")
    
    def _create_temp_dir(self) -> str:
        """创建临时文件目录"""
        temp_dir = tempfile.mkdtemp(prefix='file_transfer_http_')
        return temp_dir
    
    def start(self):
        """启动HTTP服务器"""
        try:
            if self.is_running:
                self.logger.warning("HTTP服务器已在运行")
                return True
            
            # 创建请求处理器类，并传递服务器实例
            def handler_factory(*args, **kwargs):
                return FileHTTPRequestHandler(*args, server_instance=self, **kwargs)
            
            # 创建HTTP服务器
            self.server = HTTPServer(('', self.port), handler_factory)
            
            # 在新线程中启动服务器
            self.server_thread = threading.Thread(target=self._run_server, daemon=True)
            self.server_thread.start()
            
            # 等待服务器启动
            time.sleep(0.1)
            self.is_running = True
            
            self.logger.info(f"HTTP文件服务器已启动，监听端口: {self.port}")
            return True
            
        except Exception as e:
            self.logger.error(f"启动HTTP服务器失败: {str(e)}")
            return False
    
    def _run_server(self):
        """运行HTTP服务器"""
        try:
            self.server.serve_forever()
        except Exception as e:
            self.logger.error(f"HTTP服务器运行异常: {str(e)}")
        finally:
            self.is_running = False
    
    def stop(self):
        """停止HTTP服务器"""
        try:
            if not self.is_running:
                return
            
            if self.server:
                self.server.shutdown()
                self.server.server_close()
                self.server = None
            
            if self.server_thread:
                self.server_thread.join(timeout=5)
                self.server_thread = None
            
            self.is_running = False
            
            # 清理临时文件
            self._cleanup_temp_files()
            
            self.logger.info("HTTP文件服务器已停止")
            
        except Exception as e:
            self.logger.error(f"停止HTTP服务器失败: {str(e)}")
    
    def add_file(self, source_file_path: str, custom_filename: Optional[str] = None) -> Optional[str]:
        """
        添加文件到HTTP服务器
        
        Args:
            source_file_path (str): 源文件路径
            custom_filename (str, optional): 自定义文件名
        
        Returns:
            str: 临时文件路径，失败时返回None
        """
        try:
            if not os.path.exists(source_file_path):
                self.logger.error(f"源文件不存在: {source_file_path}")
                return None
            
            if not os.path.isfile(source_file_path):
                self.logger.error(f"源路径不是文件: {source_file_path}")
                return None
            
            # 确定目标文件名
            if custom_filename:
                filename = custom_filename
            else:
                filename = os.path.basename(source_file_path)
            
            # 生成临时文件路径
            temp_file_path = os.path.join(self.temp_dir, filename)
            
            # 如果文件已存在，生成唯一文件名
            if os.path.exists(temp_file_path):
                base_name, ext = os.path.splitext(filename)
                counter = 1
                while os.path.exists(temp_file_path):
                    new_filename = f"{base_name}_{counter}{ext}"
                    temp_file_path = os.path.join(self.temp_dir, new_filename)
                    counter += 1
                filename = os.path.basename(temp_file_path)
            
            # 复制文件到临时目录
            shutil.copy2(source_file_path, temp_file_path)
            
            # 记录文件映射
            self.file_mapping[source_file_path] = temp_file_path
            
            self.logger.info(f"文件已添加到HTTP服务器: {filename}")
            return temp_file_path
            
        except Exception as e:
            self.logger.error(f"添加文件失败: {str(e)}")
            return None
    
    def remove_file(self, filename: str) -> bool:
        """
        从HTTP服务器移除文件
        
        Args:
            filename (str): 文件名
        
        Returns:
            bool: 是否成功移除
        """
        try:
            file_path = os.path.join(self.temp_dir, filename)
            if os.path.exists(file_path):
                # Windows系统文件删除重试机制
                import time
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        os.remove(file_path)
                        break
                    except PermissionError as pe:
                        if attempt < max_retries - 1:
                            self.logger.warning(f"文件删除失败，重试 {attempt + 1}/{max_retries}: {filename}")
                            time.sleep(0.5)  # 等待0.5秒后重试
                        else:
                            self.logger.error(f"文件删除最终失败: {filename} - {pe}")
                            return False
                    except Exception as e:
                        self.logger.error(f"文件删除异常: {filename} - {e}")
                        return False
                
                # 从映射中移除
                for source_path, temp_path in list(self.file_mapping.items()):
                    if temp_path == file_path:
                        del self.file_mapping[source_path]
                        break
                
                self.logger.info(f"文件已从HTTP服务器移除: {filename}")
                return True
            else:
                self.logger.warning(f"要移除的文件不存在: {filename}")
                return False
                
        except Exception as e:
            self.logger.error(f"移除文件失败: {str(e)}")
            return False
    
    def list_files(self) -> List[Dict]:
        """
        获取服务器上的文件列表
        
        Returns:
            List[Dict]: 文件信息列表
        """
        files = []
        try:
            for item in os.listdir(self.temp_dir):
                item_path = os.path.join(self.temp_dir, item)
                if os.path.isfile(item_path):
                    files.append({
                        'name': item,
                        'size': os.path.getsize(item_path),
                        'mtime': os.path.getmtime(item_path)
                    })
        except Exception as e:
            self.logger.error(f"获取文件列表失败: {str(e)}")
        
        return files
    
    def get_download_url(self, filename: str, host_ip: str = None) -> str:
        """
        获取文件的下载URL
        
        Args:
            filename (str): 文件名
            host_ip (str, optional): 主机IP地址
        
        Returns:
            str: 下载URL
        """
        if host_ip is None:
            host_ip = self._get_local_ip()
        
        # 对文件名进行URL编码，确保中文字符正确处理
        encoded_filename = urllib.parse.quote(filename, safe='')
        return f"http://{host_ip}:{self.port}/{encoded_filename}"
    
    def _get_local_ip(self) -> str:
        """获取本机IP地址"""
        import socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except Exception:
            return "127.0.0.1"
    
    def _cleanup_temp_files(self):
        """清理临时文件"""
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                self.logger.info(f"临时文件目录已清理: {self.temp_dir}")
        except Exception as e:
            self.logger.error(f"清理临时文件失败: {str(e)}")
    
    def __del__(self):
        """析构函数，确保资源清理"""
        try:
            self.stop()
        except Exception:
            pass
    
    def __enter__(self):
        """上下文管理器入口"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.stop()


# 使用示例和测试代码
if __name__ == "__main__":
    # 基本使用示例
    def basic_example():
        """基本使用示例"""
        print("启动HTTP文件服务器示例...")
        
        with FileHTTPServer(port=8088) as server:
            print(f"服务器已启动，访问地址: http://localhost:8088")
            
            # 添加一个测试文件
            test_file = "test.txt"
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write("这是一个测试文件\n")
            
            server.add_file(test_file)
            print(f"测试文件已添加: {test_file}")
            
            # 等待用户测试
            input("按回车键停止服务器...")
            
            # 清理测试文件
            if os.path.exists(test_file):
                os.remove(test_file)
    
    # 运行示例
    basic_example()