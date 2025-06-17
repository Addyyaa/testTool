#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自定义Telnet连接类

这个模块提供了一个自定义的Telnet类，继承自telnetlib3，
重新封装了常用的telnet操作方法，使其更易于使用。

TODO: 添加更多的连接选项和错误处理
FIXME: 优化超时处理机制
"""

import asyncio
import logging
import time
import sys
from typing import Optional, Union, Tuple, Dict, Any
import telnetlib3
from telnetlib3 import TelnetWriter, TelnetReader


class CustomTelnetClient:
    """
    自定义Telnet客户端类
    
    基于telnetlib3实现的异步Telnet客户端，提供了更简洁的API接口。
    支持自动连接、命令执行、响应解析等功能。
    
    Attributes:
        host (str): 目标主机地址
        port (int): 目标端口号
        timeout (float): 连接超时时间
        encoding (str): 字符编码
        reader (TelnetReader): telnet读取器
        writer (TelnetWriter): telnet写入器
        is_connected (bool): 连接状态
        logger (logging.Logger): 日志记录器
    
    Example:
        >>> client = CustomTelnetClient("192.168.1.100", 23)
        >>> await client.connect()
        >>> response = await client.execute_command("ls -la")
        >>> await client.disconnect()
    """
    
    def __init__(
        self, 
        host: str = "localhost", 
        port: int = 23,
        timeout: float = 60.0,
        encoding: str = "utf-8",
        connect_timeout: float = 10.0,
        log_level: str = "INFO"
    ):
        """
        初始化Telnet客户端
        
        Args:
            host (str): 目标主机地址，默认为localhost
            port (int): 目标端口号，默认为23
            timeout (float): 操作超时时间，默认30秒
            encoding (str): 字符编码，默认utf-8
            connect_timeout (float): 连接超时时间，默认10秒
            log_level (str): 日志级别，默认INFO
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.encoding = encoding
        self.connect_timeout = connect_timeout
        
        # 连接相关属性
        self.reader: Optional[TelnetReader] = None
        self.writer: Optional[TelnetWriter] = None
        self.is_connected = False
        self._last_prompt = ""
        self._connection_start_time = 0.0
        
        # 认证信息存储（用于自动重新登录）
        self._stored_username: Optional[str] = None
        self._stored_password: Optional[str] = None
        self._stored_shell_prompt: str = "#"
        
        # 设置日志
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # 创建控制台处理器
        if not self.logger.handlers:
            console_handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
    
    async def connect(
        self, 
        username: Optional[str] = None, 
        password: Optional[str] = None,
        login_prompt: str = "login:",
        password_prompt: str = "Password:",
        shell_prompt: str = "#"
    ) -> bool:
        """
        连接到Telnet服务器并进行认证
        
        Args:
            username (str, optional): 用户名
            password (str, optional): 密码
            login_prompt (str): 登录提示符，默认"login:"
            password_prompt (str): 密码提示符，默认"Password:"
            shell_prompt (str): Shell提示符，默认"#"
        
        Returns:
            bool: 连接是否成功
        
        Raises:
            ConnectionError: 连接失败时抛出
            TimeoutError: 连接超时时抛出
        """
        # 参数防御
        for p in [login_prompt, password_prompt, shell_prompt]:
            if not isinstance(p, str) or not p:
                raise ValueError("所有提示符参数必须为非空字符串")
        try:
            self.logger.info(f"正在连接到 {self.host}:{self.port}")
            self._connection_start_time = time.time()
            
            # 建立telnet连接
            self.reader, self.writer = await asyncio.wait_for(
                telnetlib3.open_connection(
                    host=self.host,
                    port=self.port,
                    encoding=False  # 禁用自动编码，手动处理更稳定
                ),
                timeout=self.connect_timeout
            )
            
            self.is_connected = True
            self.logger.info(f"成功连接到 {self.host}:{self.port}")
            
            # 如果提供了认证信息，进行登录
            if username and password:
                await self._authenticate(username, password, login_prompt, password_prompt, shell_prompt)
                # 存储认证信息用于后续自动重新登录
                self._stored_username = username
                self._stored_password = password
                self._stored_shell_prompt = shell_prompt
            
            return True
            
        except asyncio.TimeoutError:
            error_msg = f"连接 {self.host}:{self.port} 超时"
            self.logger.error(error_msg)
            raise TimeoutError(error_msg)
        except Exception as e:
            error_msg = f"连接 {self.host}:{self.port} 失败: {str(e)}"
            self.logger.error(error_msg)
            raise ConnectionError(error_msg)
    
    async def _authenticate(
        self, 
        username: str, 
        password: str,
        login_prompt: str,
        password_prompt: str,
        shell_prompt: str
    ) -> None:
        """
        处理登录认证过程
        
        Args:
            username (str): 用户名
            password (str): 密码
            login_prompt (str): 登录提示符
            password_prompt (str): 密码提示符
            shell_prompt (str): Shell提示符
        """
        # 参数防御
        for p in [login_prompt, password_prompt, shell_prompt]:
            if not isinstance(p, str) or not p:
                raise ValueError("所有提示符参数必须为非空字符串")
        try:
            # 等待登录提示符
            await self._wait_for_prompt(login_prompt, timeout=10.0)
            
            # 发送用户名
            await self._send_line(username)
            self.logger.debug(f"已发送用户名: {username}")
            
            # 等待密码提示符
            await self._wait_for_prompt(password_prompt, timeout=10.0)
            
            # 发送密码
            await self._send_line(password)
            self.logger.debug("已发送密码")
            
            # 等待Shell提示符，表示登录成功
            await self._wait_for_prompt(shell_prompt, timeout=15.0)
            self.logger.info("认证成功")
            
        except Exception as e:
            error_msg = f"认证失败: {str(e)}"
            self.logger.error(error_msg)
            raise ConnectionError(error_msg)
    
    async def _check_and_handle_login(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        shell_prompt: str = "#",
        login_prompt: str = "login:",
        password_prompt: str = "Password:"
    ) -> None:
        """
        检查登录状态并处理重新登录
        
        Args:
            username (str, optional): 用户名
            password (str, optional): 密码
            shell_prompt (str): Shell提示符，默认"#"
            login_prompt (str): 登录提示符，默认"login:"
            password_prompt (str): 密码提示符，默认"Password:"
        """
        try:
            self.logger.debug("检查登录状态...")
            
            # 发送回车检查当前状态
            await self._send_line("")
            
            # 尝试读取响应，看看是否有登录提示
            try:
                response = await asyncio.wait_for(
                    self.reader.read(1024),
                    timeout=2.0  # 短超时，快速检查
                )
                
                if not response:
                    self.logger.debug("没有收到响应，可能已经在shell中")
                    return
                
                # 解码响应
                if isinstance(response, bytes):
                    decoded_response = response.decode(self.encoding)
                elif isinstance(response, str):
                    decoded_response = response
                else:
                    decoded_response = str(response)
                
                self.logger.debug(f"收到响应: {repr(decoded_response)}")
                
                # 检查是否包含登录提示符
                if login_prompt.lower() in decoded_response.lower():
                    self.logger.info("检测到登录提示符，需要重新登录")
                    
                    if not username or not password:
                        raise ConnectionError("检测到需要登录，但未提供用户名或密码")
                    
                    # 执行重新登录
                    await self._authenticate(username, password, login_prompt, password_prompt, shell_prompt)
                    
                elif shell_prompt in decoded_response:
                    self.logger.debug("已经在shell中，无需登录")
                    
                else:
                    # 可能是其他状态，尝试等待shell提示符
                    self.logger.debug("状态不明确，尝试等待shell提示符")
                    try:
                        await self._wait_for_prompt(shell_prompt, timeout=3.0)
                        self.logger.debug("成功获得shell提示符")
                    except asyncio.TimeoutError:
                        self.logger.warning("无法获得shell提示符，可能需要手动处理")
                        
            except asyncio.TimeoutError:
                # 没有立即响应，可能已经在shell中
                self.logger.debug("没有立即响应，假设已经在shell中")
                
        except Exception as e:
            self.logger.warning(f"检查登录状态时出现错误: {str(e)}")
            # 不抛出异常，让命令执行继续进行
    
    async def execute_command(
        self, 
        command: str, 
        timeout: Optional[float] = None,
        end_prompt: str = "#",
        strip_command: bool = True,
        username: Optional[str] = None,
        password: Optional[str] = None,
        auto_login: bool = True
    ) -> str:
        """
        执行命令并返回结果
        
        Args:
            command (str): 要执行的命令
            timeout (float, optional): 命令执行超时时间，默认使用实例超时时间
            end_prompt (str): 命令结束提示符，默认"#"
            strip_command (bool): 是否从结果中移除命令本身，默认True
            username (str, optional): 用户名，用于自动重新登录
            password (str, optional): 密码，用于自动重新登录
            auto_login (bool): 是否自动检查并处理登录，默认True
        
        Returns:
            str: 命令执行结果
        
        Raises:
            ConnectionError: 未连接时抛出
            TimeoutError: 命令执行超时时抛出
        """
        if not self.is_connected:
            raise ConnectionError("未连接到服务器")
        
        if timeout is None:
            timeout = self.timeout
        
        try:
            self.logger.debug(f"执行命令: {command}")
            
            # 执行命令前检查登录状态
            if auto_login:
                # 如果没有提供认证信息，使用存储的认证信息
                auth_username = username or self._stored_username
                auth_password = password or self._stored_password
                await self._check_and_handle_login(auth_username, auth_password, end_prompt)
            
            # 发送命令
            await self._send_line(command)
            
            # 等待命令执行完成
            response = await self._wait_for_prompt(end_prompt, timeout=timeout)
            
            # 处理响应
            if strip_command:
                # 移除命令本身，只保留输出结果
                lines = response.split('\n')
                if lines and command in lines[0]:
                    response = '\n'.join(lines[1:])
            
            self.logger.debug(f"命令执行完成，响应长度: {len(response)}")
            return response.strip()
            
        except asyncio.TimeoutError:
            error_msg = f"命令 '{command}' 执行超时"
            self.logger.error(error_msg)
            raise TimeoutError(error_msg)
        except Exception as e:
            error_msg = f"命令 '{command}' 执行失败: {str(e)}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    async def send_raw_data(self, data: Union[str, bytes]) -> None:
        """
        发送原始数据
        
        Args:
            data (Union[str, bytes]): 要发送的数据
        
        Raises:
            ConnectionError: 未连接时抛出
        """
        if not self.is_connected:
            raise ConnectionError("未连接到服务器")
        
        if isinstance(data, str):
            data = data.encode(self.encoding)
        
        self.writer.write(data)
        await self.writer.drain()
        self.logger.debug(f"发送原始数据: {len(data)} 字节")
    
    async def read_until(
        self, 
        expected: str, 
        timeout: Optional[float] = None
    ) -> str:
        """
        读取数据直到遇到指定字符串
        
        Args:
            expected (str): 期望的结束字符串
            timeout (float, optional): 超时时间
        
        Returns:
            str: 读取到的数据
        
        Raises:
            ConnectionError: 未连接时抛出
            TimeoutError: 读取超时时抛出
        """
        if not self.is_connected:
            raise ConnectionError("未连接到服务器")
        
        if timeout is None:
            timeout = self.timeout
        
        try:
            response = await asyncio.wait_for(
                self.reader.readuntil(expected.encode(self.encoding)),
                timeout=timeout
            )
            # 手动处理编码
            if isinstance(response, bytes):
                return response.decode(self.encoding)
            elif isinstance(response, str):
                return response
            else:
                return str(response)
        except asyncio.TimeoutError:
            error_msg = f"读取数据超时，期望: {expected}"
            self.logger.error(error_msg)
            raise TimeoutError(error_msg)
    
    async def read_available(self, timeout: float = 1.0) -> str:
        """
        读取当前可用的所有数据
        
        Args:
            timeout (float): 等待超时时间，默认1秒
        
        Returns:
            str: 读取到的数据
        """
        if not self.is_connected:
            raise ConnectionError("未连接到服务器")
        
        try:
            data = await asyncio.wait_for(
                self.reader.read(1024),
                timeout=timeout
            )
            if not data:
                return ""
            # 手动处理编码
            if isinstance(data, bytes):
                return data.decode(self.encoding)
            elif isinstance(data, str):
                return data
            else:
                self.logger.error(f"read_available收到未知类型: {type(data)}")
                return ""
        except asyncio.TimeoutError:
            return ""
    
    async def disconnect(self) -> None:
        """
        断开连接
        """
        if self.is_connected and self.writer:
            try:
                self.writer.close()
                self.logger.info(f"已断开与 {self.host}:{self.port} 的连接")
            except Exception as e:
                self.logger.warning(f"断开连接时出现错误: {str(e)}")
            finally:
                self.is_connected = False
                self.reader = None
                self.writer = None
    
    async def _send_line(self, line: str) -> None:
        """
        发送一行数据（自动添加换行符）
        
        Args:
            line (str): 要发送的行
        """
        data = f"{line}\n".encode(self.encoding)
        self.writer.write(data)
        await self.writer.drain()
    
    async def _wait_for_prompt(self, prompt: str, timeout: float) -> str:
        """
        等待指定的提示符出现
        
        Args:
            prompt (str): 期望的提示符
            timeout (float): 超时时间
        
        Returns:
            str: 收到的完整响应
        """
        assert isinstance(prompt, str) and prompt, "prompt 必须为非空字符串"
        self.logger.debug(f"等待提示符: '{prompt}', 超时: {timeout}秒")
        response = ""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                chunk = await asyncio.wait_for(
                    self.reader.read(1024),
                    timeout=0.5
                )
                if not chunk:
                    continue
                # 手动处理编码
                if isinstance(chunk, bytes):
                    try:
                        decoded_chunk = chunk.decode(self.encoding)
                    except Exception as e:
                        self.logger.error(f'解码chunk失败: {e}, chunk内容: {chunk}')
                        continue
                elif isinstance(chunk, str):
                    decoded_chunk = chunk
                else:
                    self.logger.error(f'收到未知类型chunk: {type(chunk)}，内容: {chunk}')
                    continue
                response += decoded_chunk
                if prompt in response:
                    self._last_prompt = prompt
                    return response
            except asyncio.TimeoutError:
                continue
        raise asyncio.TimeoutError(f"等待提示符 '{prompt}' 超时")
    
    def set_auth_info(
        self, 
        username: str, 
        password: str, 
        shell_prompt: str = "#"
    ) -> None:
        """
        设置认证信息用于自动重新登录
        
        Args:
            username (str): 用户名
            password (str): 密码
            shell_prompt (str): Shell提示符，默认"#"
        """
        self._stored_username = username
        self._stored_password = password
        self._stored_shell_prompt = shell_prompt
        self.logger.debug("已更新存储的认证信息")
    
    def get_connection_info(self) -> Dict[str, Any]:
        """
        获取连接信息
        
        Returns:
            Dict[str, Any]: 连接信息字典
        """
        connection_duration = time.time() - self._connection_start_time if self.is_connected else 0
        
        return {
            "host": self.host,
            "port": self.port,
            "is_connected": self.is_connected,
            "encoding": self.encoding,
            "timeout": self.timeout,
            "connection_duration": connection_duration,
            "last_prompt": self._last_prompt,
            "has_stored_auth": bool(self._stored_username and self._stored_password)
        }
    
    def __str__(self) -> str:
        """
        返回对象的字符串表示
        
        Returns:
            str: 对象描述
        """
        status = "已连接" if self.is_connected else "未连接"
        return f"CustomTelnetClient({self.host}:{self.port}, {status})"
    
    def __repr__(self) -> str:
        """
        返回对象的详细表示
        
        Returns:
            str: 对象详细描述
        """
        return f"CustomTelnetClient(host='{self.host}', port={self.port}, timeout={self.timeout})"
    
    async def __aenter__(self):
        """
        异步上下文管理器入口
        
        Returns:
            CustomTelnetClient: 当前实例
        """
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        异步上下文管理器退出
        """
        await self.disconnect()


# 便利函数
async def quick_telnet_command(
    host: str,
    command: str,
    port: int = 23,
    username: Optional[str] = None,
    password: Optional[str] = None,
    timeout: float = 30.0
) -> str:
    """
    快速执行单个Telnet命令的便利函数
    
    Args:
        host (str): 目标主机
        command (str): 要执行的命令
        port (int): 端口号，默认23
        username (str, optional): 用户名
        password (str, optional): 密码
        timeout (float): 超时时间，默认30秒
    
    Returns:
        str: 命令执行结果
    
    Example:
        >>> result = await quick_telnet_command("192.168.1.100", "uptime", username="admin", password="123456")
        >>> print(result)
    """
    async with CustomTelnetClient(host, port, timeout=timeout) as client:
        await client.connect(username, password)
        return await client.execute_command(command)


if __name__ == "__main__":
    """
    测试代码示例
    """
    async def test_example():
        # 基本连接测试
        client = CustomTelnetClient("192.168.1.45", 23)
        
        try:
            # 连接到服务器
            await client.connect(username="root", password="ya!2dkwy7-934^")
            
            # 执行一些命令
            result1 = await client.execute_command("whoami")
            print(f"当前用户: {result1}")
            
            result2 = await client.execute_command("pwd")
            print(f"当前目录: {result2}")

            result3 = await client.execute_command("ls -la")
            print(f"文件列表: {result3}")
            
            # 测试自动登录检查功能
            result4 = await client.execute_command("uptime")
            print(f"系统运行时间: {result4}")

            
            # 获取连接信息
            info = client.get_connection_info()
            print(f"连接信息: {info}")
            
        except Exception as e:
            print(f"测试过程出现错误: {e}")
        finally:
            await client.disconnect()
    
    # 使用异步上下文管理器的示例
    async def test_context_manager():
        async with CustomTelnetClient("localhost", 23) as client:
            await client.connect(username="testuser", password="testpass")
            result = await client.execute_command("ls -la")
            print(f"文件列表: {result}")
    
    asyncio.run(test_example())
    