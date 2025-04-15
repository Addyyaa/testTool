import asyncio
import re
import telnetlib3

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
        r'^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.'
        r'(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.'
        r'(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.'
        r'(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
    )

    ipv6_pattern = re.compile(
        r'^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$|'
        r'^::([0-9a-fA-F]{1,4}:){0,6}[0-9a-fA-F]{1,4}$|'
        r'^([0-9a-fA-F]{1,4}:){1,6}::([0-9a-fA-F]{1,4}:){0,5}[0-9a-fA-F]{1,4}$|'
        r'^([0-9a-fA-F]{1,4}:){1,5}:([0-9a-fA-F]{1,4}:){0,4}[0-9a-fA-F]{1,4}$|'
        r'^([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}$|'
        r'^([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}$|'
        r'^([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}$|'
        r'^[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})$|'
        r'^:((:[0-9a-fA-F]{1,4}){1,7}|:)$'
    )
    if not isinstance(ip, str):
        raise TypeError("IP 地址必須為字符串類型")

    ip_str = ip.strip()
    if '.' in ip_str:
        return bool(ipv4_pattern.match(ip_str))
    elif ':' in ip_str:
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

    def __init__(self, host: str):
        """初始化 Telnet_connector。

        Args:
            host: 目標 Telnet 服務器的主機名或 IP 地址。

        Raises:
            ValueError: 如果提供的 host 不是有效的 IP 地址或主機名。
        """
        if not ip_address_validator(host):
            raise ValueError("Invalid host")
        self.host = host
        self.reader: asyncio.StreamReader | None = None
        self.writer: asyncio.StreamWriter | None = None
        self.is_unicode_mode = False  # 添加標誌
        print(f"Telnet_connector initialized for host: {self.host}")

    async def connect(self):
        """建立到目標主機的 Telnet 連接。

        如果已存在連接，則此方法不執行任何操作。
        連接成功後，會設置 self.reader 和 self.writer。
        會檢測並設置 self.is_unicode_mode 標誌。

        Raises:
            ConnectionError: 如果連接超時、被拒絕或發生其他連接錯誤。
            Exception: 其他底層異常。
        """
        if self.writer:
            print("Already connected.")
            return
        print(f"Connecting to {self.host}...")
        try:
            # 設置連接超時，由 asyncio.wait_for 控制
            self.reader, self.writer = await asyncio.wait_for(
                telnetlib3.open_connection(self.host),  # 移除不支持的 connect_timeout 參數
                timeout=6.0  # 保留總體超時
            )
            print(f"Successfully connected to {self.host}.")
            # 檢查 writer 類型以確定是否為 Unicode 模式
            # 首先確保 TelnetWriterUnicode 已成功導入且 self.writer 不是 None
            if TelnetWriterUnicode is not None and self.writer is not None:
                if isinstance(self.writer, TelnetWriterUnicode):  # type: ignore[arg-type]
                    print("Connection is using Unicode mode.")
                    self.is_unicode_mode = True
                else:
                    # writer 存在但不是 TelnetWriterUnicode，假定為 Bytes 模式
                    print("Connection is using Bytes mode (standard writer detected).")
                    self.is_unicode_mode = False
            elif self.writer is not None:
                # TelnetWriterUnicode 導入失敗，但 writer 存在，假定為 Bytes 模式
                print("Connection is using Bytes mode (TelnetWriterUnicode import failed).")
                self.is_unicode_mode = False
            else:
                # writer 為 None，連接失敗
                print("Writer is None, connection likely failed earlier.")
                self.is_unicode_mode = False  # 設置為 False 以防萬一

            # 可選：如果需要，讀取初始橫幅/提示
            # initial_output = await self.read_until_timeout()
            # print(f"Initial output:\n{initial_output}")
        except asyncio.TimeoutError:
            print(f"Connection to {self.host} timed out.")
            self.reader = None
            self.writer = None
            raise ConnectionError(f"Connection timed out to {self.host}")
        except ConnectionRefusedError:
            print(f"Connection to {self.host} refused.")
            self.reader = None
            self.writer = None
            raise ConnectionError(f"Connection refused by {self.host}")
        except Exception as e:
            print(f"Failed to connect to {self.host}: {e}")
            self.reader = None
            self.writer = None
            raise ConnectionError(f"Failed to connect: {e}") from e

    async def disconnect(self):
        """關閉當前的 Telnet 連接。

        如果沒有活動連接，則此方法不執行任何操作。
        會嘗試優雅地關閉寫入器並等待其關閉。
        """
        if self.writer:
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

                if self.writer is not None and not self.writer.is_closing():  # Also ensure writer is not None before is_closing()
                    self.writer.close()
                    # 根據當前 writer 類型決定如何等待關閉
                    if not is_unicode_writer and hasattr(self.writer, 'wait_closed'):
                        # 標準 StreamWriter
                        print("Waiting for standard writer closure...")
                        await self.writer.wait_closed()
                    elif is_unicode_writer:
                        # TelnetWriterUnicode 可能沒有 wait_closed 或類似方法
                        # close() 可能已經足夠，或者需要短暫等待
                        print("Closing Unicode writer, assuming close() is sufficient or using fallback sleep.")
                        await asyncio.sleep(0.1)  # 短暫等待以允許關閉操作完成
                    else:
                        print("Unknown writer type or mode, using fallback sleep after close().")
                        await asyncio.sleep(0.1)  # Fallback
                print("Connection closed.")
            except Exception as e:
                print(f"Error during disconnect: {e}")
            finally:
                self.writer = None
                self.reader = None
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
                chunk = await asyncio.wait_for(self.reader.read(4096), timeout=read_timeout)
                # print(f"DEBUG: Received chunk raw: {chunk!r} (type: {type(chunk)})")

                if not chunk:
                    print("Connection closed by remote host while reading.")
                    self.reader = None
                    self.writer = None
                    break

                # 處理接收到的 chunk，統一轉換為字符串
                chunk_str = ""
                if isinstance(chunk, bytes):
                    # print("DEBUG: Decoding received bytes chunk.")
                    chunk_str = chunk.decode('utf-8', errors='ignore')
                elif isinstance(chunk, str):
                    # print("DEBUG: Received string chunk directly.")
                    chunk_str = chunk
                else:
                    print(f"!!! WARNING: Received chunk of unexpected type: {type(chunk)}. Skipping.")
                    continue

                # 累加字符串
                output += chunk_str

            except asyncio.TimeoutError:
                # print("DEBUG: Read timeout occurred. Finishing read.")
                break
            except ConnectionAbortedError:
                print("Connection aborted while reading.")
                self.reader = None
                self.writer = None
                break
            except Exception as e:
                print(f"Error reading stream: {e} (Type: {type(e)})")
                self.reader = None
                self.writer = None
                break
        # print(f"DEBUG: Returning final string output (length={len(output)})")
        return output  # 直接返回累加的字符串

    async def send_command(self, command: str, read_timeout: float = 1.0) -> str:
        """向 Telnet 服務器發送命令並讀取響應。

        會自動在命令末尾添加 '\r\n'。
        該方法會嘗試智能地處理 telnetlib3 的 Unicode 模式和 Bytes 模式：
        1. 首先嘗試以字符串形式發送命令。
        2. 如果失敗並收到 "bytes-like object is required" 錯誤，則回退到
           以 UTF-8 編碼的字節串形式發送。
        發送成功後，調用 `read_until_timeout` 讀取服務器響應。

        Args:
            command: 要發送的命令字符串（不含結尾的換行符）。
            read_timeout: 發送命令後，等待響應數據的超時時間（秒），
                          傳遞給 `read_until_timeout`。

        Returns:
            服務器對命令的響應字符串。

        Raises:
            ConnectionError: 如果連接未建立、已關閉，或在發送/讀取過程中發生連接錯誤。
            TypeError: 如果底層 writer 的行為異常，無法處理字符串或字節串。
        """
        if not self.writer or not self.reader:
            raise ConnectionError("Not connected. Call connect() first.")

        # Ensure writer is still usable
        if self.writer.is_closing():
            raise ConnectionError("Connection is closing.")

        command_str = command + '\r\n'
        command_bytes = command_str.encode('utf-8', errors='ignore')

        # print(f"DEBUG: Prepared str: {command_str!r}, bytes: {command_bytes!r}")

        try:
            write_attempted_type = "string"
            # --- Primary attempt: Send string ---
            print(f"Attempting to send command as string: {command_str!r}")
            self.writer.write(command_str)  # type: ignore # Tolerate str for telnetlib3 unicode mode

        except TypeError as te:
            error_msg = str(te).lower()
            print(f"TypeError sending string: {te}")

            if "bytes-like object is required" in error_msg:
                # --- Fallback: Send bytes ---
                print(f"String write failed, retrying with bytes: {command_bytes!r}")
                try:
                    write_attempted_type = "bytes (retry)"
                    self.writer.write(command_bytes)
                except Exception as retry_e:
                    # Catch potential errors during the retry itself
                    print(f"!!! Error during byte retry write: {retry_e}")
                    await self.disconnect()
                    raise ConnectionError(f"Failed to send command on retry: {retry_e}") from retry_e
            elif "encoding without a string argument" in error_msg:
                # This is unexpected when sending a string first
                print("!!! Unexpected 'encoding' error when sending string. Telnetlib3 behavior unclear.")
                await self.disconnect()
                raise ConnectionError(f"Unexpected encoding error sending string: {te}") from te
            else:
                # Unknown TypeError
                print(f"!!! Unknown TypeError during string write: {te}")
                await self.disconnect()
                raise ConnectionError(f"Unknown TypeError sending command: {te}") from te

        # --- If write succeeded (either string initially or bytes on retry) ---
        try:
            print(f"Write ({write_attempted_type}) successful, draining buffer...")
            await self.writer.drain()
            print("Command sent, reading response...")
            response = await self.read_until_timeout(read_timeout)
            print(f"Received response (length: {len(response)})")
            return response
        except ConnectionError as ce:
            print(f"Connection error after successful write: {ce}")
            raise  # Re-raise connection errors (e.g., from read_until_timeout)
        except Exception as drain_read_e:
            print(f"Error during drain/read after write: {drain_read_e}")
            await self.disconnect()
            raise ConnectionError(f"Failed after sending command: {drain_read_e}") from drain_read_e

    # 上下文管理器支持自動連接/斷開
    async def __aenter__(self):
        """異步上下文管理器的進入方法，建立連接。"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """異步上下文管理器的退出方法，斷開連接。"""
        await self.disconnect()
