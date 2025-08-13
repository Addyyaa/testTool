import asyncio
import re
import telnetlib3
import logging

# 嘗試導入 telnetlib3 的特定類型，如果失敗也沒關係，後面有檢查
try:
    from telnetlib3.stream_writers import TelnetWriterUnicode
except ImportError:
    TelnetWriterUnicode = None  # 定義一個佔位符


def ip_address_validator(ip: str) -> bool:
    """驗證給定的字符串是否為有效的 IPv4 或 IPv6 地址。

    Args:
        ip: 需要驗證的 IP 地址字符串。

    Returns:
        如果 IP 地址有效則返回 True，否則返回 False。

    Raises:
        TypeError: 如果輸入的 ip 不是字符串類型。
    """
    ipv4_pattern = re.compile(
        r"^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\."
        r"(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\."
        r"(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\."
        r"(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
    )

    ipv6_pattern = re.compile(
        r"^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$|"
        r"^::([0-9a-fA-F]{1,4}:){0,6}[0-9a-fA-F]{1,4}$|"
        r"^([0-9a-fA-F]{1,4}:){1,6}::([0-9a-fA-F]{1,4}:){0,5}[0-9a-fA-F]{1,4}$|"
        r"^([0-9a-fA-F]{1,4}:){1,5}:([0-9a-fA-F]{1,4}:){0,4}[0-9a-fA-F]{1,4}$|"
        r"^([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}$|"
        r"^([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}$|"
        r"^([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}$|"
        r"^[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})$|"
        r"^:((:[0-9a-fA-F]{1,4}){1,7}|:)$"
    )
    if not isinstance(ip, str):
        raise TypeError("IP 地址必須為字符串類型")

    ip_str = ip.strip()
    if "." in ip_str:
        return bool(ipv4_pattern.match(ip_str))
    elif ":" in ip_str:
        return bool(ipv6_pattern.match(ip_str))
    else:
        return False


class Telnet_connector:
    """提供非同步 Telnet 連接和命令執行功能的類。

    通過此類，可以連接到 Telnet 服務器，發送命令，並獲取響應。
    支持異步上下文管理器 (`async with`) 自動管理連接。

    Attributes:
        host (str): 目標 Telnet 服務器的主機名或 IP 地址。
        reader (asyncio.StreamReader | None): 用於讀取數據的異步流讀取器。
        writer (asyncio.StreamWriter | None): 用於寫入數據的異步流寫入器。
        is_unicode_mode (bool): 標識當前連接是否處於 Unicode 模式（由 telnetlib3 協商）。
    """

    def __init__(self, host: str, port=23, username=None, password=None):
        """初始化 Telnet_connector。

        Args:
            host: 目標 Telnet 服務器的主機名或 IP 地址。
            port: 目標 Telnet 服務器的端口號，默認為 23。
            username: 登錄用戶名，如果需要。
            password: 登錄密碼，如果需要。

        Raises:
            ValueError: 如果提供的 host 不是有效的 IP 地址或主機名。
        """
        if not ip_address_validator(host):
            raise ValueError("Invalid host")
        self.host = host
        self.port = port
        self.reader: asyncio.StreamReader | None = None
        self.writer: asyncio.StreamWriter | None = None
        self.is_unicode_mode = False  # 添加標誌
        self.shell = None  # 如果需要的话
        self.username = username if username else "root"
        self.password = password if password else "ya!2dkwy7-934^"
        self._loop: asyncio.AbstractEventLoop | None = None  # 綁定創建連接時的事件循環
        # 串行化同一設備上的關鍵操作，避免並發重入導致 writer/reader 置空
        self._conn_lock = asyncio.Lock()
        self._io_lock = asyncio.Lock()
        print(f"username: {self.username}, password: {self.password}")
        print(f"Telnet_connector initialized for host: {self.host}")

    async def connect(self, timeout=10):
        """建立到目標主機的 Telnet 連接。

        如果已存在連接，則此方法不執行任何操作。
        連接成功後，會設置 self.reader 和 self.writer。
        會檢測並設置 self.is_unicode_mode 標誌。

        Raises:
            ConnectionError: 如果連接超時、被拒絕或發生其他連接錯誤。
            Exception: 其他底層異常。
        """
        async with self._conn_lock:
            # 二次檢查，避免已在其他協程建立好連接
            if self.writer and not self.writer.is_closing():
                try:
                    if (
                        hasattr(self.writer, "_transport")
                        and self.writer._transport is not None
                    ):
                        print("Connection is healthy, skipping reconnect.")
                        return
                except Exception:
                    pass
                print("Connection appears unhealthy, forcing reconnect...")
                await self.disconnect()

            print(f"Connecting to {self.host}...")
            try:
                self.reader, self.writer = await asyncio.wait_for(
                    telnetlib3.open_connection(self.host, self.port, shell=self.shell),
                    timeout=timeout,
                )
                # 綁定當前事件循環
                try:
                    self._loop = asyncio.get_running_loop()
                except RuntimeError:
                    self._loop = None
                print(f"Successfully connected to {self.host}.")
                # 檢查 writer 類型
                if TelnetWriterUnicode is not None and self.writer is not None:
                    if isinstance(self.writer, TelnetWriterUnicode):  # type: ignore[arg-type]
                        logging.debug("Connection is using Unicode mode.")
                        self.is_unicode_mode = True
                    else:
                        logging.debug(
                            "Connection is using Bytes mode (standard writer detected)."
                        )
                        self.is_unicode_mode = False
                elif self.writer is not None:
                    logging.debug(
                        "Connection is using Bytes mode (TelnetWriterUnicode import failed)."
                    )
                    self.is_unicode_mode = False
                else:
                    logging.debug("Writer is None, connection likely failed earlier.")
                    self.is_unicode_mode = False

                # 自动登录
                await self._auto_login()
            except asyncio.TimeoutError as exc:
                logging.debug("Connection to %s timed out.", self.host)
                self.reader = None
                self.writer = None
                raise ConnectionError(f"Connection timed out to {self.host}") from exc
            except ConnectionRefusedError as exc:
                logging.debug("Connection to %s refused.", self.host)
                self.reader = None
                self.writer = None
                raise ConnectionError(f"Connection refused by {self.host}") from exc
            except Exception as e:
                logging.debug("Failed to connect to %s: %s", self.host, e)
                self.reader = None
                self.writer = None
                raise ConnectionError(f"Failed to connect: {e}") from e

    async def _auto_login(self):
        """优化的自动登录机制"""
        if not self.username or not self.password:
            return  # 未设置用户名密码则跳过

        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                # 减少等待时间，提高响应速度
                output = await self.read_until_timeout(1.5)  # 从2秒减少到1.5秒

                # 检查是否需要用户名
                if any(x in output.lower() for x in ["login:", "username:"]):
                    logging.info(f"检测到登录提示，发送用户名: {self.username}")
                    self.writer.write(self.username + "\r\n")
                    await self.writer.drain()
                    output = await self.read_until_timeout(1.5)  # 减少等待时间

                # 检查是否需要密码
                if "password:" in output.lower():
                    logging.info("检测到密码提示，发送密码")
                    self.writer.write(self.password + "\r\n")
                    await self.writer.drain()
                    await asyncio.sleep(0.5)  # 从1秒减少到0.5秒

                    # 验证登录是否成功
                    verification = await self.read_until_timeout(1)
                    if any(x in verification for x in ["#", "$", ">"]):
                        logging.info("登录成功")
                        return

                # 如果已经看到提示符，说明已经登录
                if any(x in output for x in ["#", "$", ">"]):
                    logging.info("已经处于登录状态")
                    return

            except Exception as e:
                logging.warning(f"登录尝试 {attempt+1} 失败: {e}")
                if attempt < max_attempts - 1:
                    await asyncio.sleep(0.5)  # 短暂等待后重试
                else:
                    logging.error("自动登录失败")
                    raise

    async def health_check(self, timeout=2.0):
        """快速健康检查连接状态"""
        try:
            # 基础状态检查
            if not self.writer or self.writer.is_closing():
                logging.debug("健康检查失败: writer不存在或正在关闭")
                return False

            # 检查底层传输
            if hasattr(self.writer, "_transport") and self.writer._transport is None:
                logging.debug("健康检查失败: transport为空")
                return False

            # 发送简单的echo命令测试连接
            result = await asyncio.wait_for(
                self.send_command("echo ping"), timeout=timeout
            )
            is_healthy = "ping" in result
            logging.debug(f"健康检查结果: {is_healthy}, 响应: {result[:50]}")
            return is_healthy
        except Exception as e:
            logging.debug(f"健康检查异常: {e}")
            return False

    async def ensure_connection(self):
        """确保连接有效，如果无效则重连"""
        # 先进行快速检查
        if self.writer and not self.writer.is_closing():
            # 如果基础状态正常，再进行深度检查
            if (
                hasattr(self.writer, "_transport")
                and self.writer._transport is not None
            ):
                # 连接看起来正常，跳过健康检查以提高性能
                return False

        # 如果基础检查失败，进行完整的健康检查
        if not await self.health_check():
            logging.info(f"连接到 {self.host} 无效，正在重连...")
            await self.disconnect()
            await self.connect()
            return True
        return False

    async def connect_and_warmup(self, timeout=10):
        """连接并预热（发送一个测试命令确保连接稳定）"""
        await self.connect(timeout)
        try:
            # 发送一个简单命令预热连接
            await self.send_command("echo warmup")
            logging.info(f"连接到 {self.host} 预热完成")
        except Exception as e:
            logging.warning(f"连接预热失败: {e}")

    async def disconnect(self):
        """關閉當前的 Telnet 連接。

        如果沒有活動連接，則此方法不執行任何操作。
        會嘗試優雅地關閉寫入器並等待其關閉。
        """
        async with self._conn_lock:
            if not self.writer:
                print("Already disconnected.")
                return
        # 單獨關閉需要避免長時間持有 conn_lock
        if self.writer:  # recheck
            print(f"Disconnecting from {self.host}...")
            try:
                # 動態檢查 writer 類型 (確保 writer 和 TelnetWriterUnicode 都非 None)
                is_unicode_writer = False
                # --- Start nested check ---
                if self.writer is not None:
                    if TelnetWriterUnicode is not None:
                        # Both self.writer and TelnetWriterUnicode are known to be non-None here
                        is_unicode_writer = isinstance(self.writer, TelnetWriterUnicode)  # type: ignore[arg-type]
                # --- End nested check ---

                if (
                    self.writer is not None and not self.writer.is_closing()
                ):  # Also ensure writer is not None
                    # before is_closing()
                    self.writer.close()
                    # 根據當前 writer 類型決定如何等待關閉
                    if not is_unicode_writer and hasattr(self.writer, "wait_closed"):
                        # 標準 StreamWriter
                        logging.debug("Waiting for standard writer closure...")
                        await self.writer.wait_closed()
                    elif is_unicode_writer:
                        # TelnetWriterUnicode 可能沒有 wait_closed 或類似方法
                        # close() 可能已經足夠，或者需要短暫等待
                        logging.debug(
                            "Closing Unicode writer, assuming close() is sufficient or using fallback sleep."
                        )
                        await asyncio.sleep(0.1)  # 短暫等待以允許關閉操作完成
                    else:
                        logging.debug(
                            "Unknown writer type or mode, using fallback sleep after close()."
                        )
                        await asyncio.sleep(0.1)  # Fallback
                print("Connection closed.")
            except Exception as e:
                logging.debug(f"Error during disconnect: {e}")
            finally:
                self.writer = None
                self.reader = None
                self._loop = None
        else:
            print("Already disconnected.")

    async def read_until_timeout(self, read_timeout: float = 1) -> str:
        """從連接讀取數據，直到指定的超時時間內沒有更多數據到達。

        此方法會持續讀取數據塊，直到 `reader.read()` 在 `read_timeout` 秒內
        沒有返回任何數據，這通常表示服務器已停止發送響應。
        無論底層接收到的是字節串還是字符串，最終都返回統一的字符串。

        Args:
            read_timeout: 在認為讀取完成之前，等待新數據的最長時間（秒）。

        Returns:
            從連接讀取到的所有數據，組合成的單個字符串。

        Raises:
            ConnectionError: 如果在讀取時連接未建立或已斷開。
        """
        if not self.reader:
            raise ConnectionError("Not connected.")

        output = ""  # 初始化為空字符串
        while True:
            try:
                # print(f"DEBUG: Waiting for data (timeout={read_timeout}s)...")
                chunk = await asyncio.wait_for(
                    self.reader.read(4096), timeout=read_timeout
                )
                # print(f"DEBUG: Received chunk raw: {chunk!r} (type: {type(chunk)})")

                if not chunk:
                    logging.debug("Connection closed by remote host while reading.")
                    self.reader = None
                    self.writer = None
                    break

                if isinstance(chunk, bytes):
                    # print("DEBUG: Decoding received bytes chunk.")
                    chunk_str = chunk.decode("utf-8", errors="ignore")
                elif isinstance(chunk, str):
                    # print("DEBUG: Received string chunk directly.")
                    chunk_str = chunk
                else:
                    logging.debug(
                        f"!!! WARNING: Received chunk of unexpected type: {type(chunk)}. Skipping."
                    )
                    continue

                # 累加字符串
                output += chunk_str

            except asyncio.TimeoutError:
                # logging.debug("DEBUG: Read timeout occurred. Finishing read.")
                if not output:  # 检查 output 是否为空
                    logging.debug("Read timeout occurred before receiving any data.")
                else:
                    logging.debug(
                        f"Read timeout occurred after receiving partial "
                        f"data (length={len(output)}).Finishing read."
                    )
                break
            except ConnectionAbortedError:
                logging.debug("Connection aborted while reading.")
                self.reader = None
                self.writer = None
                break
            except Exception as e:
                logging.debug(f"Error reading stream: {e} (Type: {type(e)})")
                self.reader = None
                self.writer = None
                break
        # logging.debug(f"DEBUG: Returning final string output (length={len(output)})")
        return output  # 直接返回累加的字符串

    async def send_command(self, command: str, read_timeout: float = 1.0) -> str:
        """向 Telnet 服務器發送命令並讀取響應。

        會自動在命令末尾添加 '\r\n'，並在連接異常時重試。
        """
        max_retries = 2
        last_exception: Exception | None = None
        base_retry_delay = 1.0
        retry_delay_multiplier = 2.0

        async with self._io_lock:
            for attempt in range(max_retries + 1):
                try:
                    # 事件循環變更檢查
                    try:
                        current_loop = asyncio.get_running_loop()
                    except RuntimeError:
                        current_loop = None
                    if (
                        self._loop is not None
                        and current_loop is not None
                        and current_loop is not self._loop
                    ):
                        logging.warning(
                            "Event loop has changed since connection was created; reconnecting..."
                        )
                        if self.writer and not self.writer.is_closing():
                            await self.disconnect()
                        await self.connect()

                    # 基礎連接狀態檢查
                    if not self.writer or not self.reader or self.writer.is_closing():
                        logging.warning(
                            f"[Attempt {attempt+1}/{max_retries+1}] Connection not established or closing. "
                            f"Attempting to connect... (writer: {bool(self.writer)}, reader: {bool(self.reader)}, "
                            f"closing: {self.writer.is_closing() if self.writer else 'N/A'})"
                        )
                        if self.writer and not self.writer.is_closing():
                            await self.disconnect()
                        await self.connect()
                        if not self.writer or not self.reader:
                            raise ConnectionError(
                                "Failed to establish connection components after connect()."
                            )

                        # 初始讀取，處理可能的登錄提示
                        initial_response = await self.read_until_timeout(
                            read_timeout=0.5
                        )
                        if initial_response and (
                            "login:" in initial_response.lower()
                            or "username:" in initial_response.lower()
                        ):
                            if not self.username:
                                raise ConnectionError(
                                    "检测到登录提示，但未设置用户名，无法继续"
                                )
                            logging.info(f"检测到登录提示，发送用户名: {self.username}")
                            await self._send_raw_command(self.username)
                            await asyncio.sleep(0.5)
                        if initial_response and "password:" in initial_response.lower():
                            if not self.password:
                                raise ConnectionError(
                                    "检测到密码提示，但未设置密码，无法继续"
                                )
                            logging.info("检测到密码提示，发送密码")
                            await self._send_raw_command(self.password)
                            await asyncio.sleep(1)

                    # 構造命令
                    command_str = command + "\r\n"
                    command_bytes = command_str.encode("utf-8", errors="ignore")
                    write_attempted_type = "string"

                    # 發送前連接健康檢查
                    if not self.writer or self.writer.is_closing():
                        raise ConnectionError("Writer is None or closing")
                    if (
                        hasattr(self.writer, "_transport")
                        and self.writer._transport is None
                    ):
                        raise ConnectionError("Transport is None")
                    if (
                        hasattr(self.writer, "_transport")
                        and self.writer._transport
                        and hasattr(self.writer._transport, "_loop")
                        and hasattr(self.writer._transport._loop, "_proactor")
                        and self.writer._transport._loop._proactor is None
                    ):
                        raise ConnectionError("Proactor is None")

                    # 發送命令（優先 string，回退 bytes）
                    try:
                        self.writer.write(command_str)  # type: ignore
                    except TypeError as te:
                        msg = str(te).lower()
                        if "bytes-like object is required" in msg:
                            write_attempted_type = "bytes (retry)"
                            self.writer.write(command_bytes)
                        elif "encoding without a string argument" in msg:
                            raise ConnectionError(
                                f"Unexpected encoding error sending string: {te}"
                            ) from te
                        else:
                            raise ConnectionError(
                                f"Unknown TypeError sending command: {te}"
                            ) from te

                    await self.writer.drain()
                    response = await self.read_until_timeout(read_timeout)

                    if not response and (
                        not self.reader or not self.writer or self.writer.is_closing()
                    ):
                        raise ConnectionError(
                            "Empty response with broken connection detected."
                        )

                    # 響應中的登錄提示處理
                    login_retry_count = getattr(self, "_login_retry_count", 0)
                    max_login_retries = 2
                    lower = (response or "").lower()
                    if (
                        response
                        and (
                            "login:" in lower
                            or "username:" in lower
                            or "password:" in lower
                        )
                        and login_retry_count < max_login_retries
                    ):
                        self._login_retry_count = login_retry_count + 1
                        if "login:" in lower or "username:" in lower:
                            if not self.username:
                                raise ConnectionError(
                                    "响应中检测到登录提示，但未设置用户名，无法继续"
                                )
                            await self._send_raw_command(self.username)
                            await asyncio.sleep(0.5)
                        if "password:" in lower:
                            if not self.password:
                                raise ConnectionError(
                                    "响应中检测到密码提示，但未设置密码，无法继续"
                                )
                            await self._send_raw_command(self.password)
                            await asyncio.sleep(1)
                        # 重新發送原命令
                        self.writer.write(command_str)
                        await self.writer.drain()
                        response = await self.read_until_timeout(read_timeout)
                    elif response and (
                        "login:" in lower
                        or "username:" in lower
                        or "password:" in lower
                    ):
                        raise ConnectionError(
                            f"达到最大登录重试次数({max_login_retries})，但仍检测到登录提示"
                        )
                    elif response and "notfount" in lower:
                        await self._send_raw_command("\n")
                        self.writer.write(command_str)
                        await self.writer.drain()
                        response = await self.read_until_timeout(read_timeout)
                    else:
                        self._login_retry_count = 0

                    logging.debug(
                        f"[Attempt {attempt+1}/{max_retries+1}] Command executed successfully. Response length: {len(response)}"
                    )
                    return response

                except ConnectionError as ce:
                    last_exception = ce
                    logging.warning(
                        f"[Attempt {attempt+1}/{max_retries+1}] ConnectionError occurred: {ce}"
                    )
                    if attempt < max_retries:
                        error_str = str(ce).lower()
                        is_retryable = any(
                            k in error_str
                            for k in [
                                "timeout",
                                "aborted",
                                "broken",
                                "closing",
                                "not connected",
                                "proactor",
                                "transport is none",
                                "writer is none",
                            ]
                        )
                        if not is_retryable:
                            logging.error(
                                f"[Attempt {attempt+1}/{max_retries+1}] Non-retryable ConnectionError: {ce}. Aborting retries."
                            )
                            raise ce
                        retry_delay = base_retry_delay * (
                            retry_delay_multiplier**attempt
                        )
                        logging.info(
                            f"Waiting {retry_delay:.1f} seconds before retry..."
                        )
                        await asyncio.sleep(retry_delay)
                        continue
                    else:
                        logging.error(
                            f"Command send failed after {max_retries} retries due to ConnectionError: {ce}"
                        )
                        raise last_exception
                except Exception as e:
                    logging.error(
                        f"[Attempt {attempt+1}/{max_retries+1}] Unexpected error during send_command: {e}",
                        exc_info=True,
                    )
                    raise ConnectionError(
                        f"Unexpected error during command send: {e}"
                    ) from e

        # 理論上不會到達這裡
        raise ConnectionError(
            f"Command send failed unexpectedly after {max_retries + 1} attempts. Last known error: {last_exception}"
        )

    async def _send_raw_command(self, command: str) -> str:
        """发送原始命令，不包含重试逻辑，仅用于内部调用

        Args:
            command: 要发送的命令

        Returns:
            命令响应
        """
        if not self.writer or not self.reader:
            raise ConnectionError("Not connected")

        command_str = command + "\r\n"
        try:
            self.writer.write(command_str)
            await self.writer.drain()
            return await self.read_until_timeout(0.5)
        except Exception as e:
            logging.error(f"Error in _send_raw_command: {e}")
            raise ConnectionError(f"Failed to send raw command: {e}")

    # 上下文管理器支持自動連接/斷開
    async def __aenter__(self):
        """异步上下文管理器的进入方法，建立连接。"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器的退出方法，断开连接。"""
        await self.disconnect()
