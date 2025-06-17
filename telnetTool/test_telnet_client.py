 #!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自定义Telnet客户端单元测试
作者: 系统管理员
创建日期: 2024
版本: 1.0.0

这个文件包含了CustomTelnetClient类的单元测试用例
"""

import asyncio
import pytest
import logging
from unittest.mock import AsyncMock, MagicMock, patch
from telnetConnect import CustomTelnetClient, quick_telnet_command


class TestCustomTelnetClient:
    """
    CustomTelnetClient类的测试用例
    """
    
    def setup_method(self):
        """
        每个测试方法执行前的设置
        """
        self.client = CustomTelnetClient(
            host="test.example.com",
            port=23,
            timeout=10.0,
            log_level="DEBUG"
        )
    
    def teardown_method(self):
        """
        每个测试方法执行后的清理
        """
        # 清理资源
        if hasattr(self.client, 'writer') and self.client.writer:
            self.client.writer = None
        if hasattr(self.client, 'reader') and self.client.reader:
            self.client.reader = None
        self.client.is_connected = False
    
    def test_init(self):
        """
        测试类初始化
        """
        assert self.client.host == "test.example.com"
        assert self.client.port == 23
        assert self.client.timeout == 10.0
        assert self.client.encoding == "utf-8"
        assert self.client.is_connected is False
        assert self.client.reader is None
        assert self.client.writer is None
    
    def test_str_representation(self):
        """
        测试字符串表示
        """
        expected = "CustomTelnetClient(test.example.com:23, 未连接)"
        assert str(self.client) == expected
        
        # 测试连接状态下的字符串表示
        self.client.is_connected = True
        expected_connected = "CustomTelnetClient(test.example.com:23, 已连接)"
        assert str(self.client) == expected_connected
    
    def test_repr(self):
        """
        测试repr表示
        """
        expected = "CustomTelnetClient(host='test.example.com', port=23, timeout=10.0)"
        assert repr(self.client) == expected
    
    def test_get_connection_info_not_connected(self):
        """
        测试未连接状态的连接信息
        """
        info = self.client.get_connection_info()
        expected = {
            "host": "test.example.com",
            "port": 23,
            "is_connected": False,
            "encoding": "utf-8",
            "timeout": 10.0,
            "connection_duration": 0,
            "last_prompt": ""
        }
        assert info == expected
    
    @pytest.mark.asyncio
    async def test_connect_timeout(self):
        """
        测试连接超时
        """
        with patch('telnetlib3.open_connection') as mock_open:
            # 模拟连接超时
            mock_open.side_effect = asyncio.TimeoutError()
            
            with pytest.raises(TimeoutError):
                await self.client.connect()
    
    @pytest.mark.asyncio
    async def test_connect_connection_error(self):
        """
        测试连接错误
        """
        with patch('telnetlib3.open_connection') as mock_open:
            # 模拟连接错误
            mock_open.side_effect = Exception("Connection failed")
            
            with pytest.raises(ConnectionError):
                await self.client.connect()
    
    @pytest.mark.asyncio
    async def test_connect_success_without_auth(self):
        """
        测试成功连接（无认证）
        """
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        
        with patch('telnetlib3.open_connection') as mock_open:
            mock_open.return_value = (mock_reader, mock_writer)
            
            result = await self.client.connect()
            
            assert result is True
            assert self.client.is_connected is True
            assert self.client.reader == mock_reader
            assert self.client.writer == mock_writer
    
    @pytest.mark.asyncio
    async def test_connect_success_with_auth(self):
        """
        测试成功连接（带认证）
        """
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        
        with patch('telnetlib3.open_connection') as mock_open:
            mock_open.return_value = (mock_reader, mock_writer)
            
            # 模拟认证过程
            with patch.object(self.client, '_authenticate') as mock_auth:
                mock_auth.return_value = None
                
                result = await self.client.connect(
                    username="testuser", 
                    password="testpass"
                )
                
                assert result is True
                assert self.client.is_connected is True
                mock_auth.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_command_not_connected(self):
        """
        测试未连接状态下执行命令
        """
        with pytest.raises(ConnectionError):
            await self.client.execute_command("test command")
    
    @pytest.mark.asyncio
    async def test_execute_command_success(self):
        """
        测试成功执行命令
        """
        # 设置连接状态
        self.client.is_connected = True
        
        # 模拟方法
        with patch.object(self.client, '_send_line') as mock_send:
            with patch.object(self.client, '_wait_for_prompt') as mock_wait:
                mock_send.return_value = None
                mock_wait.return_value = "test command\ncommand output\n$ "
                
                result = await self.client.execute_command("test command")
                
                assert result == "command output"
                mock_send.assert_called_once_with("test command")
                mock_wait.assert_called_once_with("$", timeout=10.0)
    
    @pytest.mark.asyncio
    async def test_execute_command_timeout(self):
        """
        测试命令执行超时
        """
        self.client.is_connected = True
        
        with patch.object(self.client, '_send_line') as mock_send:
            with patch.object(self.client, '_wait_for_prompt') as mock_wait:
                mock_send.return_value = None
                mock_wait.side_effect = asyncio.TimeoutError()
                
                with pytest.raises(TimeoutError):
                    await self.client.execute_command("test command")
    
    @pytest.mark.asyncio
    async def test_send_raw_data_not_connected(self):
        """
        测试未连接状态下发送原始数据
        """
        with pytest.raises(ConnectionError):
            await self.client.send_raw_data("test data")
    
    @pytest.mark.asyncio
    async def test_send_raw_data_success(self):
        """
        测试成功发送原始数据
        """
        self.client.is_connected = True
        mock_writer = AsyncMock()
        self.client.writer = mock_writer
        
        await self.client.send_raw_data("test data")
        
        mock_writer.write.assert_called_once_with(b"test data")
        mock_writer.drain.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_raw_data_bytes(self):
        """
        测试发送字节数据
        """
        self.client.is_connected = True
        mock_writer = AsyncMock()
        self.client.writer = mock_writer
        
        test_data = b"test bytes data"
        await self.client.send_raw_data(test_data)
        
        mock_writer.write.assert_called_once_with(test_data)
        mock_writer.drain.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_read_until_not_connected(self):
        """
        测试未连接状态下读取数据
        """
        with pytest.raises(ConnectionError):
            await self.client.read_until("expected")
    
    @pytest.mark.asyncio
    async def test_read_until_success(self):
        """
        测试成功读取数据
        """
        self.client.is_connected = True
        mock_reader = AsyncMock()
        mock_reader.readuntil.return_value = b"data until expected"
        self.client.reader = mock_reader
        
        result = await self.client.read_until("expected")
        
        assert result == "data until expected"
        mock_reader.readuntil.assert_called_once_with(b"expected")
    
    @pytest.mark.asyncio
    async def test_read_until_timeout(self):
        """
        测试读取数据超时
        """
        self.client.is_connected = True
        mock_reader = AsyncMock()
        mock_reader.readuntil.side_effect = asyncio.TimeoutError()
        self.client.reader = mock_reader
        
        with pytest.raises(TimeoutError):
            await self.client.read_until("expected")
    
    @pytest.mark.asyncio
    async def test_read_available_not_connected(self):
        """
        测试未连接状态下读取可用数据
        """
        with pytest.raises(ConnectionError):
            await self.client.read_available()
    
    @pytest.mark.asyncio
    async def test_read_available_success(self):
        """
        测试成功读取可用数据
        """
        self.client.is_connected = True
        mock_reader = AsyncMock()
        mock_reader.read.return_value = b"available data"
        self.client.reader = mock_reader
        
        result = await self.client.read_available()
        
        assert result == "available data"
        mock_reader.read.assert_called_once_with(1024)
    
    @pytest.mark.asyncio
    async def test_read_available_timeout(self):
        """
        测试读取可用数据超时
        """
        self.client.is_connected = True
        mock_reader = AsyncMock()
        mock_reader.read.side_effect = asyncio.TimeoutError()
        self.client.reader = mock_reader
        
        result = await self.client.read_available()
        
        assert result == ""
    
    @pytest.mark.asyncio
    async def test_disconnect_not_connected(self):
        """
        测试未连接状态下断开连接
        """
        await self.client.disconnect()
        assert self.client.is_connected is False
    
    @pytest.mark.asyncio
    async def test_disconnect_success(self):
        """
        测试成功断开连接
        """
        self.client.is_connected = True
        mock_writer = AsyncMock()
        self.client.writer = mock_writer
        
        await self.client.disconnect()
        
        mock_writer.close.assert_called_once()
        mock_writer.wait_closed.assert_called_once()
        assert self.client.is_connected is False
        assert self.client.reader is None
        assert self.client.writer is None
    
    @pytest.mark.asyncio
    async def test_disconnect_with_error(self):
        """
        测试断开连接时出现错误
        """
        self.client.is_connected = True
        mock_writer = AsyncMock()
        mock_writer.close.side_effect = Exception("Close error")
        self.client.writer = mock_writer
        
        # 应该不抛出异常，只是记录警告
        await self.client.disconnect()
        
        assert self.client.is_connected is False
        assert self.client.reader is None
        assert self.client.writer is None
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """
        测试异步上下文管理器
        """
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        
        with patch('telnetlib3.open_connection') as mock_open:
            mock_open.return_value = (mock_reader, mock_writer)
            
            async with CustomTelnetClient("test.example.com") as client:
                assert client is not None
                assert isinstance(client, CustomTelnetClient)
            
            # 确保连接被正确关闭
            mock_writer.close.assert_called_once()
            mock_writer.wait_closed.assert_called_once()


class TestQuickTelnetCommand:
    """
    quick_telnet_command函数的测试用例
    """
    
    @pytest.mark.asyncio
    async def test_quick_telnet_command_success(self):
        """
        测试快速命令执行成功
        """
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        
        with patch('telnetlib3.open_connection') as mock_open:
            mock_open.return_value = (mock_reader, mock_writer)
            
            # 模拟CustomTelnetClient的方法
            with patch.object(CustomTelnetClient, 'connect') as mock_connect:
                with patch.object(CustomTelnetClient, 'execute_command') as mock_execute:
                    mock_connect.return_value = True
                    mock_execute.return_value = "command result"
                    
                    result = await quick_telnet_command(
                        host="test.example.com",
                        command="test command",
                        username="testuser",
                        password="testpass"
                    )
                    
                    assert result == "command result"
                    mock_connect.assert_called_once_with("testuser", "testpass")
                    mock_execute.assert_called_once_with("test command")
    
    @pytest.mark.asyncio
    async def test_quick_telnet_command_connection_error(self):
        """
        测试快速命令执行连接错误
        """
        with patch('telnetlib3.open_connection') as mock_open:
            mock_open.side_effect = Exception("Connection failed")
            
            with pytest.raises(ConnectionError):
                await quick_telnet_command(
                    host="test.example.com",
                    command="test command"
                )


class TestIntegration:
    """
    集成测试用例
    """
    
    @pytest.mark.asyncio
    async def test_full_workflow_mock(self):
        """
        测试完整工作流程（使用mock）
        """
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        
        # 模拟认证过程的响应
        mock_reader.read.side_effect = [
            b"login: ",
            b"Password: ",
            b"$ ",
            b"test command\ncommand output\n$ "
        ]
        
        with patch('telnetlib3.open_connection') as mock_open:
            mock_open.return_value = (mock_reader, mock_writer)
            
            client = CustomTelnetClient("test.example.com")
            
            try:
                # 连接并认证
                await client.connect(username="testuser", password="testpass")
                assert client.is_connected is True
                
                # 执行命令（需要mock _wait_for_prompt方法）
                with patch.object(client, '_wait_for_prompt') as mock_wait:
                    mock_wait.return_value = "test command\ncommand output\n$ "
                    
                    result = await client.execute_command("test command")
                    assert "command output" in result
                
            finally:
                await client.disconnect()
                assert client.is_connected is False


class TestEdgeCases:
    """
    边界情况测试
    """
    
    def test_invalid_parameters(self):
        """
        测试无效参数
        """
        # 测试负数端口
        client = CustomTelnetClient("test.example.com", port=-1)
        assert client.port == -1
        
        # 测试负数超时
        client = CustomTelnetClient("test.example.com", timeout=-1.0)
        assert client.timeout == -1.0
    
    @pytest.mark.asyncio
    async def test_empty_command(self):
        """
        测试空命令
        """
        client = CustomTelnetClient("test.example.com")
        client.is_connected = True
        
        with patch.object(client, '_send_line') as mock_send:
            with patch.object(client, '_wait_for_prompt') as mock_wait:
                mock_send.return_value = None
                mock_wait.return_value = "\n$ "
                
                result = await client.execute_command("")
                assert result == ""
    
    @pytest.mark.asyncio
    async def test_large_response(self):
        """
        测试大响应数据
        """
        client = CustomTelnetClient("test.example.com")
        client.is_connected = True
        
        # 创建大响应数据
        large_response = "x" * 10000 + "\n$ "
        
        with patch.object(client, '_send_line') as mock_send:
            with patch.object(client, '_wait_for_prompt') as mock_wait:
                mock_send.return_value = None
                mock_wait.return_value = large_response
                
                result = await client.execute_command("large command")
                assert len(result) > 9000


if __name__ == "__main__":
    """
    运行测试
    """
    # 设置日志级别
    logging.basicConfig(level=logging.DEBUG)
    
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])