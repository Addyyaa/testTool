#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件传输控制器

负责协调整个文件传输过程，并新增文件编辑功能
"""

import asyncio
from typing import Optional, Any
import logging
from fileTransfer.logger_utils import get_logger


class RemoteFileEditor:
    """远程文件编辑器

    提供在GUI中直接编辑远端设备文件的能力。

    设计目标：
    1. 读取远端文件内容（UTF-8 编码）。
    2. 将编辑后的内容写回远端并保持原始文件权限。
    3. 在写回之前，保证远端 / 路径下启动的 httpd 服务在 88 端口可用。

    Note: 本类只负责与远端交互的底层逻辑，实际的 GUI 窗口由调用者创建。
    """

    SUPPORTED_EXTS = (".ini", ".txt", ".log", ".sh")
    LARGE_FILE_SIZE = 400 * 1024  # 400 KB 以上使用 HTTP 下载

    def __init__(self,
                 telnet_client: Any,
                 http_server: Any,
                 event_loop: Optional[asyncio.AbstractEventLoop] = None,
                 telnet_lock: Optional[asyncio.Lock] = None,
                 logger: Optional[logging.Logger] = None):
        self.telnet_client = telnet_client
        self.http_server = http_server
        self.loop = event_loop or asyncio.get_event_loop()
        self.telnet_lock = telnet_lock or asyncio.Lock()

        # 如果外部传入了 logger，则创建子 logger，确保日志名称可准确定位到 RemoteFileEditor
        if logger is not None:
            self.logger = logger.getChild(self.__class__.__name__)
        else:
            # 使用统一工具生成 logger
            self.logger = get_logger(self.__class__)

        self.remote_ip = getattr(telnet_client, 'host', None)

    # ------------------------------------------------------------------
    # public helpers
    # ------------------------------------------------------------------
    async def read_file(self, remote_path: str) -> str:
        """读取远端文件并返回其内容 (UTF-8)。失败时返回空字符串"""
        try:
            await self._ensure_httpd_service()

            # 始终通过 HTTP 下载文件内容
            content = await self._download_via_http(remote_path)
            if content is not None:
                self.logger.info(f"已通过HTTP读取文件: {remote_path} (长度 {len(content)} 字节)")
                return content
            # 若 HTTP 失败作为保底再用 telnet cat
            self.logger.warning("HTTP 下载失败，回退 telnet 方案，使用cat读取")
            async with self.telnet_lock:
                cmd = f'cat "{remote_path}"'
                output = await self.telnet_client.execute_command(cmd, timeout=30)
            return output
        except Exception as e:
            self.logger.error(f"读取远程文件失败: {e}")
            return ""

    async def read_file_preview(self, remote_path: str, max_lines: int = 1000) -> str:
        """快速读取文件前 max_lines 行，用于预览，提升大文件打开速度"""
        try:
            await self._ensure_httpd_service()
            content = await self._download_via_http(remote_path)
            if content is None:
                return ""
            self.logger.info(f"预览通过HTTP获取: {remote_path} (前 {max_lines} 行)")
            # 截断到前 max_lines 行
            lines = content.split('\n')[:max_lines]
            return '\n'.join(lines)
        except Exception as e:
            self.logger.error(f"读取预览失败: {e}")
            return ""

    async def write_file(self, remote_path: str, new_content: str) -> bool:
        """将 new_content 写回 remote_path。
        过程：
        1. 记录原文件权限
        2. 生成本地临时文件并写入新内容
        3. 使用现有 HTTP 服务器上传至远端 (wget)
        4. 恢复文件权限（若有变动）
        """
        try:
            await self._ensure_httpd_service()

            # 记录权限（如 stat 不可用则退化为 644）
            async with self.telnet_lock:
                perm_cmd = f"stat -c %a '{remote_path}' 2>/dev/null || echo '644'"
                perms = await self.telnet_client.execute_command(perm_cmd)
                perms = perms.strip() or "644"
                self.logger.debug(f"原始权限: {perms}")

            # 写入本地临时文件
            import tempfile, os
            base_dir, filename = os.path.split(remote_path)
            # 统一换行符为Unix格式（\n），避免Windows的\r\n导致Linux上显示^M
            normalized_content = new_content.replace('\r\n', '\n').replace('\r', '\n')
            with tempfile.NamedTemporaryFile(delete=False, mode="w", encoding="utf-8", suffix=os.path.splitext(filename)[1], newline='\n') as tmp:
                tmp.write(normalized_content)
                local_tmp_path = tmp.name

            # 上传文件
            if not self.http_server:
                self.logger.error("HTTP 服务器尚未启动，无法写回文件")
                return False

            server_tmp_path = self.http_server.add_file(local_tmp_path, filename)
            if not server_tmp_path:
                self.logger.error("无法将文件添加到 HTTP 服务器临时目录")
                return False

            host_ip = self.http_server._get_local_ip()
            download_url = self.http_server.get_download_url(filename, host_ip)
            wget_cmd = f'cd "{base_dir}" && wget -q -O "{filename}" "{download_url}"'
            self.logger.debug(f"执行写入命令: {wget_cmd}")
            async with self.telnet_lock:
                await self.telnet_client.execute_command(wget_cmd, timeout=30)

            # 恢复权限
            chmod_cmd = f'chmod {perms} "{remote_path}"'
            self.logger.debug(f"恢复权限命令: {chmod_cmd}")
            async with self.telnet_lock:
                await self.telnet_client.execute_command(chmod_cmd)

            # 清理
            self.http_server.remove_file(filename)
            os.unlink(local_tmp_path)
            return True
        except Exception as e:
            self.logger.error(f"写回远程文件失败: {e}")
            return False

    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------
    async def _ensure_httpd_service(self):
        """确保远端根目录 httpd -p 88 已经启动。如果已启动但工作目录不为 / ，则重新启动。"""
        try:
            async with self.telnet_lock:
                # 检查 httpd 进程
                ps_res = await self.telnet_client.execute_command("pidof httpd")
                need_restart = True
                if ps_res.strip():
                    # 进程存在，检查工作目录是否为 / （通过 /proc/PID/cwd 链接）
                    pid = ps_res.strip()
                    cwd_cmd = f'readlink -f /proc/{pid}/cwd'
                    cwd = await self.telnet_client.execute_command(cwd_cmd)
                    cwd = cwd.strip()
                    self.logger.info(f"httpd cwd: {cwd}")
                    if cwd == "/ #":
                        need_restart = False
                if need_restart:
                    self.logger.info("重新启动 httpd 服务以确保位于根目录 ...")
                    await self.telnet_client.execute_command('killall -9 httpd || true')
                    await self.telnet_client.execute_command('cd / && httpd -p 88')
        except Exception as e:
            self.logger.error(f"_ensure_httpd_service error: {e}") 

    async def _get_remote_file_size(self, remote_path: str) -> Optional[int]:
        """获取远端文件大小，单位 byte，失败返回 None"""
        try:
            async with self.telnet_lock:
                res = await self.telnet_client.execute_command(f'stat -c %s "{remote_path}" 2>/dev/null || du -b "{remote_path}" | cut -f1')
            res = res.strip().split('\n')[0].strip()
            return int(res) if res.isdigit() else None
        except Exception as e:
            self.logger.debug(f"获取文件大小失败: {e}")
            return None

    async def _download_via_http(self, remote_path: str) -> Optional[str]:
        """通过远端 httpd 端口 88 下载文件内容"""
        from urllib import parse, request
        # 动态获取当前连接的IP，避免使用缓存的旧IP
        current_ip = getattr(self.telnet_client, 'host', self.remote_ip)
        encoded_path = parse.quote(remote_path, safe='/')
        url = f'http://{current_ip}:88{encoded_path}'
        self.logger.debug(f"HTTP 下载 URL: {url}")

        def _fetch():
            try:
                with request.urlopen(url, timeout=20) as resp:
                    data = resp.read()
                    self.logger.debug(f"HTTP 下载成功, 字节数 {len(data)}")
                    return data.decode('utf-8', errors='replace')
            except Exception as e:
                self.logger.error(f"HTTP 下载异常: {e}")
                return None

        loop = asyncio.get_event_loop()
        content = await loop.run_in_executor(None, _fetch)
        return content

    async def get_file_bytes(self, remote_path: str) -> Optional[bytes]:
        """下载远端文件并返回 bytes，用于图片预览等"""
        await self._ensure_httpd_service()
        from urllib import parse, request
        # 动态获取当前连接的IP，避免使用缓存的旧IP
        current_ip = getattr(self.telnet_client, 'host', self.remote_ip)
        encoded_path = parse.quote(remote_path, safe='/')
        url = f'http://{current_ip}:88{encoded_path}'
        self.logger.debug(f"HTTP(二进制) URL: {url}")

        def _fetch_bytes():
            try:
                with request.urlopen(url, timeout=20) as resp:
                    return resp.read()
            except Exception as e:
                self.logger.error(f"HTTP 下载图片失败: {e}")
                return None

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _fetch_bytes)

    # GUI兼容性方法
    async def read_file_async(self, remote_path: str) -> str:
        """GUI兼容性方法：异步读取文件内容"""
        return await self.read_file(remote_path)
    
    async def download_file_async(self, remote_path: str) -> Optional[bytes]:
        """GUI兼容性方法：异步下载文件字节数据"""
        await self._ensure_httpd_service()
        return await self.get_file_bytes(remote_path)
    
    async def write_file_async(self, remote_path: str, new_content: str) -> bool:
        """GUI兼容性方法：异步写入文件内容"""
        return await self.write_file(remote_path, new_content)