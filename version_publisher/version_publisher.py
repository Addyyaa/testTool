import hashlib
import os
from pathlib import Path
import re
import sys
import traceback
import json
from PySide6.QtCore import QObject, Signal, Slot, Qt, QEvent, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QMessageBox,
    QCheckBox,
    QTextEdit,
    QComboBox,
    QProgressBar,
)
from dataclasses import dataclass
import threading
import aiohttp
import asyncio
import logging
import base64
import tarfile
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


# 静态方法，将资源包变成包资源
def package_resource(resource_path: str, file_name: str):
    """
    静态方法，将资源包变成包资源
    """
    # 1) 优先：作为包资源（Nuitka/PyInstaller/源码都可）
    try:
        from importlib.resources import files, as_file

        res = files(resource_path).joinpath(file_name)
        with as_file(res) as p:
            if p.is_file():
                return p
    except Exception as e:
        logger.error(f"将资源包变成包资源失败: {e}")

    # 2) 其次：exe 目录 / _MEIPASS（PyInstaller）/ 模块目录 / CWD
    exe_dir = Path(sys.argv[0]).resolve().parent  # exe 所在目录（Nuitka/普通运行均可）
    meipass = Path(getattr(sys, "_MEIPASS", exe_dir))  # PyInstaller 兼容
    module_dir = Path(__file__).resolve().parent
    cwd = Path.cwd()

    candidates = [
        # 打包运行（PyInstaller 可能会命中）
        meipass / resource_path / file_name,
        meipass / file_name,
        # 外置文件：exe 同目录（最常用）
        exe_dir / file_name,
        # 源码/临时解包目录
        module_dir / resource_path / file_name,
        module_dir / file_name,
        # 外置文件：当前工作目录
        cwd / file_name,
        cwd / resource_path / file_name,
    ]
    for p in candidates:
        if p.is_file():
            return p
    raise FileNotFoundError(
        "未找到 user.env，请确认它位于 asserts 目录（与 exe 同目录或已打包为资源）"
    )


def singleton(cls):
    """单例模式装饰器"""
    _instances = {}

    def get_instance(*args, **kwargs):
        if cls not in _instances:
            _instances[cls] = cls(*args, **kwargs)
        return _instances[cls]

    return get_instance


@singleton
@dataclass
class DataInfo:
    # 运行环境：ts 测试、cn 正式-中国、en 正式-海外
    env_info = "ts"
    package_name = "SStarOta.bin.gz"
    current_path = os.path.dirname(os.path.abspath(__file__))
    # 用户可在GUI中选择的包根目录（默认与脚本同级的 package/{env_info} 根）
    base_dir = os.path.join(current_path, f"package/{env_info}")
    id_lcd_type_mapping_table = {}
    # 相对 base_dir 的相对路径；1/3/5共用，2/4/6共用
    relative_path_map = {
        "1": f"{env_info}/10_1920_1200_vvx10f002a/{package_name}",
        "3": f"{env_info}/10_1920_1200_vvx10f002a/{package_name}",
        "5": f"{env_info}/10_1920_1200_vvx10f002a/{package_name}",
        "2": f"{env_info}/13_1920_1080_nv156fhm/{package_name}",
        "4": f"{env_info}/13_1920_1080_nv156fhm/{package_name}",
        "6": f"{env_info}/13_1920_1080_nv156fhm/{package_name}",
        "7": f"{env_info}/10_800_1280_fp7721bx2_innolux/{package_name}",
        "8": f"{env_info}/10_800_1280_fp7721bx2_boe/{package_name}",
        "9": f"{env_info}/16_1920_1200_vvx10f002a/{package_name}",
    }

    def set_base_dir(self, new_base_dir: str):
        self.base_dir = new_base_dir

    def get_local_path(self, lcd_type: str) -> str:
        """
        根据设备类型获取本地固件路径
        """
        rel = self.relative_path_map.get(lcd_type)
        if not rel:
            return ""
        return os.path.join(self.base_dir, rel)

    def set_env(self, env_key: str):
        """切换环境，并更新依赖字段。
        env_key: ts/cn/en
        """
        if env_key not in {"ts", "cn", "en"}:
            raise ValueError("环境参数错误，应为 ts/cn/en")
        # 更新环境
        type(self).env_info = env_key
        # 更新派生字段
        type(self).region_path = (
            "public-files-en" if env_key == "en" else "public-files-cn"
        )
        type(self).remote_package_prefix = (
            f"apk/clinet/ota/{self.remote_package_middle_str[env_key]}/"
        )
        # 端口
        self.server_info["port"] = 8082 if env_key == "ts" else 8080
        # base_dir（若用户未自定义，将指向新环境默认目录）
        default_dir = os.path.join(self.current_path, f"package/{env_key}")
        if os.path.basename(self.base_dir) in {"ts", "cn", "en"}:  # 用户没改过时跟随
            self.base_dir = default_dir

    product_name = {
        "1": "1920*1200 早期",
        "2": "1920*1080 早期",
        "3": "1920*1200 0.5G",
        "4": "1920*1080 0.5G",
        "5": "1920*1200 64G",
        "6": "1920*1080 64G",
        "7": "800*1280 群创",
        "8": "800*1280 BOE",
        # 同名显示，兼容键9和10
        "9": "1920*1200 16寸",
    }
    version_info = {
        "1": None,
        "2": None,
        "3": None,
        "4": None,
        "5": None,
        "6": None,
        "7": None,
        "8": None,
        "9": None,
    }
    file_md5 = {
        "1": None,
        "2": None,
        "3": None,
        "4": None,
        "5": None,
        "6": None,
        "7": None,
        "8": None,
        "9": None,
    }
    region_path = "public-files-en" if env_info == "en" else "public-files-cn"
    remote_package_middle_str = {
        "cn": "zh",
        "en": "en",
        "ts": "test",
    }
    remote_package_prefix = f"apk/clinet/ota/{remote_package_middle_str[env_info]}/"
    server_info = {
        "api_server": {
            "cn": "cloud-service.austinelec.com",
            "en": "cloud-service-us.austinelec.com",
            "ts": "139.224.192.36",
            "qiniu": {
                "query_path": "api.qiniu.com",
            },
        },
        "api": {
            "qiniuToken": "/api/v1/manage/OTAPackageManage/getUploadToken",
            "qiniuak": "/v2/query",
            "qiniu_upload": f"/buckets/{region_path}/objects/",
            "manager_login": "/api/v1/manage/system/auth/login",
            "otaPackage_manage": "/api/v1/manage/OTAPackageManage/update",
            "id_lcd_type_mapping_table": "/api/v1/manage/OTAPackageManage/list",
        },
        "remote_path_base64": {
            "1": None,
            "2": None,
            "3": None,
            "4": None,
            "5": None,
            "6": None,
            "7": None,
            "8": None,
            "9": None,
        },
        "port": 8082 if env_info == "ts" else 8080,
    }


@singleton
class GetfirewareInfo(QObject):
    def __init__(self):
        super().__init__()
        self.data_info = DataInfo()

    def read_file_content(self, lcd_type: str, file_name: str):
        """
        封装读取内容方法
        """
        path = self.data_info.get_local_path(lcd_type)
        if not path or not os.path.isfile(path):
            raise FileNotFoundError(f"固件文件不存在: {path}")
        mode = "r:gz" if path.endswith(".gz") else "r"
        try:
            with tarfile.open(path, mode) as tar:
                for member in tar.getmembers():
                    if member.isfile() and os.path.basename(member.name) == file_name:
                        file_obj = tar.extractfile(member)
                        if file_obj:
                            content = file_obj.read().decode("utf-8")
                            return content
                return None
        except Exception as e:
            logger.error(f"获取固件版本失败: {e}")
            sys.exit(1)

    def get_fireware_version(self, lcd_type: str):
        """
        获取固件版本号
        """
        try:
            content = self.read_file_content(lcd_type, "version.ini")
            pattern = r"=\s*(.*?)\n"
            version = re.search(pattern, content).group(1)
            self.data_info.version_info[lcd_type] = version
            return version
        except Exception as e:
            logger.error(f"获取固件版本失败: {e}")
            sys.exit(1)

    def get_file_md5(self, lcd_type: str):
        """
        获取文件md5
        """
        file_path = self.data_info.get_local_path(lcd_type)
        try:
            with open(file_path, "rb") as f:
                md5_obj = hashlib.md5()
                while True:
                    data = f.read(8192)
                    if not data:
                        break
                    md5_obj.update(data)
            self.data_info.file_md5[lcd_type] = md5_obj.hexdigest()
            return md5_obj.hexdigest()
        except Exception as e:
            logger.error(f"获取文件md5失败: {e}")
            sys.exit(1)

    def get_fireware_lcd_type(self, lcd_type: str):
        """
        对比固件内部的lcdty与外部传入的lcd_type是否一致 # TODO：无法实现，当前固件升级包中没有任何地方记录lcd_type
        """
        pass


class Uploader(QObject):
    upload_error = Signal(str)
    upload_success = Signal(str)
    upload_progress = Signal(str, int)
    total_progress = Signal(int, int)

    def __init__(self):
        super().__init__()
        self.data_info = DataInfo()
        self.fw_getter = GetfirewareInfo()
        self.manager_token = None
        self.qiniu_token = None
        self.qiniu_up_server = None
        self.upload_queue = []
        self.remote_upload_info = {}
        self.total_blocks = 0
        self.uploaded_blocks = 0
        self.pintura_account = None
        self.pintura_password = None
        self.get_pintura_account_info()

    def get_pintura_account_info(self):
        """
        获取Pintura管理员账号信息
        """

        # 兼容 PyInstaller 打包与源码运行的 env 文件定位
        env_path = package_resource("asserts", "user.env")
        load_dotenv(dotenv_path=env_path, override=True)
        account_info = {
            "ts": os.getenv("ts"),
            "cn": os.getenv("cn"),
            "en": os.getenv("en"),
        }
        selected = account_info.get(self.data_info.env_info)
        if not selected:
            logger.error(
                f"未读取到环境 {self.data_info.env_info} 的账号配置，请检查 {env_path} 是否包含对应键(ts/cn/en)。"
            )
            sys.exit(1)
        try:
            env_account_info = json.loads(selected)
        except Exception as exc:
            logger.error(
                f"解析 {self.data_info.env_info} 账号配置失败，请检查 JSON 格式是否正确: {exc}"
            )
            sys.exit(1)
        self.pintura_account = env_account_info.get("username")
        self.pintura_password = env_account_info.get("password")
        if not self.pintura_account or not self.pintura_password:
            logger.error(
                f"从 {self.data_info.env_info} 环境配置中未获取到 username/password，请检查 {env_path} 内容。"
            )
            sys.exit(1)

    def _caculate_total_blocks(self, selected_lcd_types: list[str]) -> int:
        """计算所有固件包的总块数"""
        total_blocks = 0
        # 去重分组，得到代表类型集合
        reps: set[str] = set(self._group_rep(x) for x in selected_lcd_types)

        for rep in reps:
            file_path = self.data_info.get_local_path(rep)
            if os.path.exists(file_path):
                total_size = os.path.getsize(file_path)
                part_size = 4 * 1024 * 1024  # 4MB
                part_count = (total_size + part_size - 1) // part_size
                total_blocks += part_count

        return total_blocks

    @Slot(list)
    def receive_file_list(self, file_list: list):
        """接收用户输入的列表"""
        try:
            if not file_list:
                self.upload_error.emit("请选择要更新固件的设备")
                return
            for _ in file_list:
                if str(_) not in self.data_info.relative_path_map.keys():
                    logger.error(f"用户选择的设备类型{_}不支持:")
                    sys.exit(1)
                self.update_remote_path_base64(str(_))
            self.upload_queue = file_list
        except Exception as e:
            logger.error(f"接收文件列表失败: {e}")
            sys.exit(1)

    async def get_manager_token(self):
        """
        获取Pintura管理员token
        """
        try:
            url = f"http://{self.data_info.server_info['api_server']['ts']}:{self.data_info.server_info['port']}{self.data_info.server_info['api']['manager_login']}"
            print(url)
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json={
                        "username": self.pintura_account,
                        "password": self.pintura_password,
                        "loginType": 2,
                        "account": self.pintura_account,
                    },
                ) as response:
                    res = await response.json()
                    self.manager_token = res["data"]
                    return res["data"]
        except Exception as e:
            logger.error(f"获取管理员token失败: {e}")
            self.upload_error.emit(f"获取管理员token失败: {e}")
            sys.exit(1)

    async def get_qiniu_token(self):
        """
        获取七牛上传token
        """
        try:
            headers = {"x-token": await self.get_manager_token()}
            if headers["x-token"] is None:
                logger.error("获取管理员token失败")
                sys.exit(1)
            url = f"http://{self.data_info.server_info['api_server']['ts']}:{self.data_info.server_info['port']}{self.data_info.server_info['api']['qiniuToken']}"
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(url) as response:
                    res = await response.json()
                    self.qiniu_token = res["data"]
                    return res["data"]
        except Exception as e:
            logger.error(f"获取七牛token失败: {e}")
            sys.exit(1)

    def extra_partInfo(self, qiniu_token: str):
        return qiniu_token.split(":")[0]

    async def get_qiniu_server(self):
        """
        获取七牛上传服务器
        """
        res = await self.get_qiniu_token()
        path_auth = self.extra_partInfo(res)
        url = f"http://{self.data_info.server_info['api_server']['qiniu']['query_path']}{self.data_info.server_info['api']['qiniuak']}"
        params = {
            "ak": path_auth,
            "bucket": self.data_info.region_path,
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                res = await response.json()
                qiniu_up_server = res["up"]["acc"]["main"][0]
                self.qiniu_up_server = qiniu_up_server
                return qiniu_up_server

    def remote_file_path_to_base64(self, remote_file_path: str):
        return base64.b64encode(remote_file_path.encode("utf-8")).decode("ascii")

    def update_remote_path_base64(self, lcd_type: str):
        """
        更新远程文件路径为base64
        """
        self.fw_getter.get_fireware_version(lcd_type)
        try:
            remote_file_path = (
                self.data_info.remote_package_prefix
                + lcd_type
                + self.data_info.version_info[lcd_type]
                + "/"
                + self.data_info.package_name
            )
            self.data_info.server_info["remote_path_base64"][lcd_type] = (
                self.remote_file_path_to_base64(remote_file_path)
            )
            return self.remote_file_path_to_base64(remote_file_path)
        except Exception as e:
            logger.error(f"更新远程文件路径base64失败: {e}")
            sys.exit(1)

    async def get_qiniu_uploadID(self, lcd_type: str):
        """
        获取七牛上传ID
        """
        url = f"https://{self.qiniu_up_server}{self.data_info.server_info['api']['qiniu_upload']}{self.data_info.server_info['remote_path_base64'][lcd_type]}/uploads"
        logger.info(f"url: {url}")
        header = {"authorization": "UpToken " + self.qiniu_token}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=header) as response:
                    res = await response.json()
                    self.remote_upload_info[lcd_type] = {
                        "uploadId": res["uploadId"],
                        "expireAt": res["expireAt"],
                    }
        except Exception as e:
            logger.error(f"获取七牛上传ID失败: {e}")
            sys.exit(1)
        logger.info(f"remote_upload_info: {self.remote_upload_info}")

    async def upload_file(self, lcd_type: str) -> str:
        """
        七牛分块上传（Multipart Upload v2）
        依赖：
          - self.qiniu_up_server 已通过 get_qiniu_server() 获取
          - self.qiniu_token 已通过 get_qiniu_token() 获取
          - self.remote_upload_info[lcd_type]['uploadId'] 已通过 get_qiniu_uploadID(lcd_type) 获取
          - self.data_info.server_info["remote_path_base64"][lcd_type] 已通过 update_remote_path_base64(lcd_type) 生成
        """
        try:
            # 1) 校验前置条件
            if not self.qiniu_up_server:
                await self.get_qiniu_server()
            if not self.qiniu_token:
                await self.get_qiniu_token()
            if (
                lcd_type not in self.data_info.server_info["remote_path_base64"]
                or not self.data_info.server_info["remote_path_base64"][lcd_type]
            ):
                self.update_remote_path_base64(lcd_type)
            if (
                lcd_type not in self.remote_upload_info
                or "uploadId" not in self.remote_upload_info[lcd_type]
            ):
                await self.get_qiniu_uploadID(lcd_type)

            file_path = self.data_info.get_local_path(lcd_type)
            if not os.path.exists(file_path):
                self.upload_error.emit(f"文件不存在: {file_path}")
                return

            filename = os.path.basename(file_path)
            total_size = os.path.getsize(file_path)
            part_size = 4 * 1024 * 1024  # 4MB
            part_count = (total_size + part_size - 1) // part_size

            base_url = (
                f"https://{self.qiniu_up_server}"
                f"{self.data_info.server_info['api']['qiniu_upload']}"
                f"{self.data_info.server_info['remote_path_base64'][lcd_type]}"
                f"/uploads/{self.remote_upload_info[lcd_type]['uploadId']}"
            )
            headers_common = {
                "authorization": "UpToken " + self.qiniu_token,
            }

            parts = []
            bytes_sent = 0

            # 2) 顺序上传每个分块（如需并发可改成并发任务）
            async with aiohttp.ClientSession(headers=headers_common) as session:
                with open(file_path, "rb") as f:
                    for i in range(part_count):
                        part_number = i + 1
                        start = i * part_size
                        size = part_size if i < part_count - 1 else (total_size - start)

                        f.seek(start)
                        data = f.read(size)

                        part_url = f"{base_url}/{part_number}"
                        # 建议指定二进制类型；Content-Length aiohttp 会自动设置
                        part_headers = {
                            "Content-Type": "application/octet-stream",
                        }

                        etag_val = await self._upload_part_with_retry(
                            session, part_url, data, part_headers, part_number
                        )
                        parts.append({"partNumber": part_number, "etag": etag_val})
                        bytes_sent += size

                        # 更新总体进度
                        self.uploaded_blocks += 1
                        self.total_progress.emit(
                            self.uploaded_blocks, self.total_blocks
                        )

                        self.upload_progress.emit(
                            filename, int(bytes_sent * 100 / max(total_size, 1))
                        )

            # 3) 完成合并
            complete_url = base_url  # POST 到 .../uploads/{uploadId}
            payload = {"parts": sorted(parts, key=lambda x: x["partNumber"])}

            async with aiohttp.ClientSession(headers=headers_common) as session:
                async with session.post(complete_url, json=payload) as resp:
                    rs = await resp.json()
                    logger.info(f"resp: {rs}")
                    if resp.status // 100 != 2:
                        text = await resp.text()
                        self.upload_error.emit(
                            f"合并分块失败，HTTP {resp.status}: {text}"
                        )
                        raise RuntimeError(text)
                    download_url = rs["key"]
                    self.upload_progress.emit(filename, 100)
                    return download_url
        except Exception as e:
            logger.exception("分块上传异常")
            self.upload_error.emit(f"上传异常: {e}")
            raise

    async def _upload_part_with_retry(
        self, session, url, data, headers, part_number, max_retries=3, base_delay=0.5
    ):
        """
        对单个分块PUT上传添加重试（指数退避）
        重试条件：429/5xx/超时/网络连接错误
        返回：etag字符串
        """
        for attempt in range(1, max_retries + 1):
            try:
                async with session.put(url, data=data, headers=headers) as resp:
                    rs = await resp.json()
                    logger.debug(f"resp: {rs}")
                    if 200 <= resp.status < 300:
                        # 兼容两种返回，优先头部，再尝试JSON
                        etag = resp.headers.get("ETag") or resp.headers.get("Etag")
                        if not etag:
                            ctype = resp.headers.get("Content-Type", "").lower()
                            if "application/json" in ctype:
                                body = await resp.json(content_type=None)
                                etag = body.get("etag")
                            else:
                                _ = await resp.text()  # 读掉响应避免连接泄漏
                        if not etag:
                            raise RuntimeError(
                                f"part {part_number} 上传成功但未返回etag"
                            )
                        return etag

                    # 非2xx，判断是否可重试
                    if resp.status in (408, 425, 429) or 500 <= resp.status < 600:
                        if attempt == max_retries:
                            text = await resp.text()
                            raise RuntimeError(
                                f"part {part_number} 失败 HTTP {resp.status}: {text}"
                            )
                    else:
                        text = await resp.text()
                        raise RuntimeError(
                            f"part {part_number} 不可重试错误 HTTP {resp.status}: {text}"
                        )

            except (aiohttp.ClientConnectionError, asyncio.TimeoutError) as e:
                if attempt == max_retries:
                    raise RuntimeError(f"part {part_number} 网络/超时失败: {e}") from e

            # 指数退避
            await asyncio.sleep(base_delay * (2 ** (attempt - 1)))

    def _group_rep(self, lcd_type: str) -> str:
        """返回该类型所属上传代表类型：1/3/5->1，2/4/6->2，其余自身。"""
        if lcd_type in {"1", "3", "5"}:
            return "1"
        if lcd_type in {"2", "4", "6"}:
            return "2"
        return lcd_type

    async def post_ota_update(
        self, lcd_type: str, download_url: str, remark_cn: str, remark_en: str
    ) -> None:
        """
        提交更新到pintura服务器
        """
        ota_url = f"http://{self.data_info.server_info['api_server']['ts']}:{self.data_info.server_info['port']}{self.data_info.server_info['api']['otaPackage_manage']}"
        data = {
            "appVersion": self.data_info.version_info[lcd_type],
            "downloadUrl": download_url,
            "encryption": self.data_info.file_md5.get(lcd_type)
            or self.data_info.file_md5[self._group_rep(lcd_type)],
            "id": self.data_info.id_lcd_type_mapping_table[lcd_type],
            "remark": remark_cn,
            "remarkEn": remark_en,
        }
        # 需要携带管理后台token
        headers = {"x-token": self.manager_token or await self.get_manager_token()}
        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.post(ota_url, json=data) as resp:
                    rs = await resp.json()
                    if rs and rs["code"] == 20:
                        self.upload_success.emit(
                            f"{self.data_info.product_name[lcd_type]} 上传完成"
                        )
                    else:
                        self.upload_error.emit(f"提交到pintura服务器失败：{rs['msg']}")
                    if resp.status // 100 != 2:
                        text = await resp.text()
                        raise RuntimeError(
                            f"提交到pintura服务器失败，HTTP {resp.status}: {text}"
                        )
        except Exception as e:
            self.upload_error.emit(f"提交更新失败：{str(e)}\n{traceback.format_exc()}")
            logger.error(f"提交更新失败：{str(e)}")

    async def publish_selected(
        self, selected_lcd_types: list[str], remark_cn: str, remark_en: str
    ) -> None:
        """
        1. 上传固件到七牛
        2. 提交更新到pintura服务器
        """
        await self.init_id_lcd_type_mapping_table()  # 初始化映射表

        # 校验必填日志
        if not remark_cn.strip() or not remark_en.strip():
            raise ValueError("发布日志(中/英)为必填项")

        # 预热服务端信息
        await self.get_qiniu_server()

        # 计算总块数并初始化进度
        self.total_blocks = self._caculate_total_blocks(selected_lcd_types)
        self.uploaded_blocks = 0
        # 发送初始进度
        self.total_progress.emit(0, self.total_blocks)

        # 去重分组，得到代表类型集合
        reps: set[str] = set(self._group_rep(x) for x in selected_lcd_types)

        # 为代表类型准备版本、md5、上传ID并上传一次，得到 download_url（并发，最多5个）
        rep_to_url: dict[str, str] = {}
        rep_sem = asyncio.Semaphore(5)

        async def _process_rep(rep: str):
            async with rep_sem:
                # 生成远程路径base64与版本（内部可能抛出文件不存在错误）
                self.update_remote_path_base64(rep)
                # 计算MD5（用于后续各成员）
                self.fw_getter.get_file_md5(rep)
                # 获取 uploadId 并上传
                await self.get_qiniu_uploadID(rep)
                download_url = await self.upload_file(rep)
                rep_to_url[rep] = download_url

        await asyncio.gather(*[_process_rep(rep) for rep in reps])

        # 对每个被选中的 lcd_type，使用对应代表的 download_url 逐一更新服务端记录
        # 并发提交更新（最多5个）
        upd_sem = asyncio.Semaphore(5)

        async def _process_update(lcd: str):
            try:
                async with upd_sem:
                    rep = self._group_rep(lcd)
                    # 确保版本号（同一物理包，路径相同，直接复用或读取）
                    self.fw_getter.get_fireware_version(lcd)
                    # 对齐 MD5（同链路复用代表）
                    self.data_info.file_md5[lcd] = self.data_info.file_md5[rep]
                    await self.post_ota_update(
                        lcd, rep_to_url[rep], remark_cn, remark_en
                    )
            except Exception as e:
                self.upload_error.emit(
                    f"提交更新失败：{str(e)}\n{traceback.format_exc()}"
                )
                logger.error(f"提交更新失败：{str(e)}")

        await asyncio.gather(*[_process_update(lcd) for lcd in selected_lcd_types])

    async def init_id_lcd_type_mapping_table(self):
        """
        由于不同环境的数据库表的结构不一致，以及后期可能有所变动，所以通过接口获取id和lcdtype映射关系
        """
        header = {"x-token": self.manager_token or await self.get_manager_token()}
        url = f"http://{self.data_info.server_info['api_server']['ts']}:{self.data_info.server_info['port']}{self.data_info.server_info['api']['id_lcd_type_mapping_table']}"
        async with aiohttp.ClientSession(headers=header) as session:
            async with session.get(url) as resp:
                rs = await resp.json()
                for _ in rs["data"]:
                    self.data_info.id_lcd_type_mapping_table[str(_["appType"])] = str(
                        _["id"]
                    )


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.uploader = Uploader()
        self.last_fireware_dir = LastFirewareDir()  # 添加这行
        self.init_ui()
        self.connect_signal()
        self.is_login = False

    def init_ui(self):
        self.setWindowTitle("固件发布工具")
        self.setWindowIcon(QIcon("version_publisher/assets/icon.png"))
        self.setGeometry(100, 100, 900, 640)

        root = QWidget(self)
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        # 初始化映射表

        # 环境选择
        env_row = QHBoxLayout()
        env_row.addWidget(QLabel("环境:"))
        self.env_combo = QComboBox()
        self.env_combo.addItem("测试环境", userData="ts")
        self.env_combo.addItem("正式环境-中国", userData="cn")
        self.env_combo.addItem("正式环境-海外", userData="en")
        # 设置默认值
        cur_env = self.uploader.data_info.env_info
        idx = {"ts": 0, "cn": 1, "en": 2}[cur_env]
        self.env_combo.setCurrentIndex(idx)
        env_row.addWidget(self.env_combo)
        env_row.addStretch(1)
        layout.addLayout(env_row)

        # 选择区域：全选 + 9个复选框
        select_row = QHBoxLayout()
        self.cb_select_all = QCheckBox("全选")
        select_row.addWidget(self.cb_select_all)
        layout.addLayout(select_row)

        # 产品复选框容器
        self.cb_map = {}
        grid_row = QHBoxLayout()
        left_col = QVBoxLayout()
        right_col = QVBoxLayout()
        for idx, key in enumerate(["1", "2", "3", "4", "5", "6", "7", "8", "9"]):
            cb = QCheckBox(
                f"{key}. {self.uploader.data_info.product_name.get(key, key)}"
            )
            self.cb_map[key] = cb
            (left_col if idx < 5 else right_col).addWidget(cb)
        grid_row.addLayout(left_col)
        grid_row.addLayout(right_col)
        layout.addLayout(grid_row)

        # 日志输入（必填）
        layout.addWidget(QLabel("发布日志（中文，必填）"))
        self.remark_cn_edit = QTextEdit()
        self.remark_cn_edit.setPlaceholderText("请输入中文发布日志…")
        layout.addWidget(self.remark_cn_edit)

        layout.addWidget(QLabel("Release Notes (English, required)"))
        self.remark_en_edit = QTextEdit()
        self.remark_en_edit.setPlaceholderText("Please input English release notes…")
        layout.addWidget(self.remark_en_edit)

        # 选择包根目录
        dir_row = QHBoxLayout()
        dir_row.addWidget(QLabel("包根目录:"))

        # 尝试加载上次选择的目录
        last_dir = self.last_fireware_dir.get_last_fireware_dir()
        initial_dir = (
            last_dir
            if last_dir and os.path.exists(last_dir)
            else self.uploader.data_info.base_dir
        )

        self.base_dir_edit = QLineEdit(initial_dir)
        btn_browse = QPushButton("浏览…")
        dir_row.addWidget(self.base_dir_edit)
        dir_row.addWidget(btn_browse)
        layout.addLayout(dir_row)

        # 提交按钮
        btn_row = QHBoxLayout()
        self.btn_publish = QPushButton("提交发布")
        btn_row.addStretch(1)
        btn_row.addWidget(self.btn_publish)
        layout.addLayout(btn_row)

        # 新增：总体上传进度条
        progress_row = QHBoxLayout()
        progress_row.addWidget(QLabel("总体上传进度:"))
        self.total_progress_bar = QProgressBar()
        self.total_progress_bar.setStyleSheet(
            """
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 3px;
                background-color: #f0f0f0;
                text-align: center;
                width: 45em;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 2px;
            }
            """
        )
        self.total_progress_bar.setVisible(False)  # 初始隐藏
        progress_row.addWidget(self.total_progress_bar)
        self.progress_label = QLabel("0/0 块")
        self.progress_label.setVisible(False)  # 初始隐藏
        progress_row.addWidget(self.progress_label)
        progress_row.addStretch(1)
        layout.addLayout(progress_row)

        self.env_combo.installEventFilter(self)
        self.show()

    def connect_signal(self):
        self.uploader.upload_error.connect(self.on_upload_error)
        self.uploader.upload_success.connect(self.on_upload_success)
        self.cb_select_all.stateChanged.connect(self.on_select_all_changed)
        # 新增总体进度信号连接
        self.uploader.total_progress.connect(self.on_total_progress)
        self.cb_select_all.stateChanged.connect(self.on_select_all_changed)
        self.btn_publish.clicked.connect(self.on_publish_clicked)

        # 环境切换
        def _on_env_changed(index: int):
            env_key = self.env_combo.itemData(index)
            try:
                self.uploader.data_info.set_env(env_key)
                # 切环境时，若base_dir仍为默认结构，自动切到新环境目录
                self.base_dir_edit.setText(self.uploader.data_info.base_dir)
            except Exception as e:
                self.uploader.upload_error.emit(f"环境切换：{str(e)}")

        self.env_combo.currentIndexChanged.connect(_on_env_changed)

        # 目录浏览
        def _choose_dir():
            dlg = QFileDialog(self, "选择包根目录")
            dlg.setFileMode(QFileDialog.Directory)
            dlg.setOption(QFileDialog.ShowDirsOnly, True)
            if dlg.exec():
                dirs = dlg.selectedFiles()
                if dirs:
                    selected_dir = dirs[0]
                    self.base_dir_edit.setText(selected_dir)
                    self.uploader.data_info.set_base_dir(selected_dir)
                    # 保存用户选择的目录
                    self.last_fireware_dir.save_last_fireware_dir(selected_dir)

        # 绑定按钮
        for w in self.findChildren(QPushButton):
            if w.text() == "浏览…":
                w.clicked.connect(_choose_dir)

    def eventFilter(self, obj, event):
        if obj == self.env_combo and event.type() == QEvent.MouseButtonPress:
            if not self.is_login:
                dialog = LoginDialog(self)
                if dialog.exec() == QDialog.Accepted:
                    self.is_login = True
                    return False  # 登录成功，继续事件处理（打开下拉框）
                else:
                    return True  # 登录失败，阻止事件处理（不打开下拉框）
        return super().eventFilter(obj, event)

    def on_upload_error(self, error_message: str):
        QMessageBox.warning(self, "错误", error_message)

    def on_upload_success(self, success_message: str):
        QMessageBox.information(self, "成功", success_message)

    def on_select_all_changed(self, state: int):
        checked = state == Qt.Checked
        for cb in self.cb_map.values():
            cb.blockSignals(True)
            cb.setTristate(False)
            cb.setChecked(checked)
            cb.blockSignals(False)

    def on_publish_clicked(self):
        # 收集选择
        selected = [k for k, cb in self.cb_map.items() if cb.checkState() == Qt.Checked]

        # 重置进度条
        self.total_progress_bar.setValue(0)
        self.progress_label.setText("0/0 块")
        # 兜底：若全选被勾选但selected仍为空，则按全选处理
        if self.cb_select_all.isChecked() and not selected:
            selected = list(self.cb_map.keys())
        if not selected:
            QMessageBox.warning(self, "提示", "请至少选择一个升级产品")
            return

        remark_cn = self.remark_cn_edit.toPlainText().strip()
        remark_en = self.remark_en_edit.toPlainText().strip()
        if not remark_cn or not remark_en:
            QMessageBox.warning(self, "提示", "发布日志（中/英）为必填项")
            return

        # 在后台线程运行异步发布，避免阻塞GUI且无需引入qasync
        def _thread_target():
            try:
                asyncio.run(
                    self.uploader.publish_selected(selected, remark_cn, remark_en)
                )
            except Exception as e:
                self.uploader.upload_error.emit(f"发布失败：{str(e)}")

        threading.Thread(target=_thread_target, daemon=True).start()

    def on_total_progress(self, current_blocks: int, total_blocks: int):
        """处理总体上传进度"""
        if total_blocks > 0:
            percentage = int(current_blocks * 100 / total_blocks)
            self.total_progress_bar.setValue(percentage)
            self.progress_label.setText(f"{current_blocks}/{total_blocks} 块")

            # 显示进度条和标签
            self.total_progress_bar.setVisible(True)
            self.progress_label.setVisible(True)

            # 如果完成，延迟隐藏进度条
            if current_blocks >= total_blocks:
                QTimer.singleShot(3000, self._hide_progress)

    def _hide_progress(self):
        """隐藏进度条和标签"""
        self.total_progress_bar.setVisible(False)
        self.progress_label.setVisible(False)


class LoginDialog(QDialog):
    def __init__(self, parent: MainWindow):
        super().__init__(parent)
        self.setWindowTitle("登录")
        self.setModal(True)
        self.resize(250, 120)

        self.username_edit = QLineEdit()
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.login_btn = QPushButton("登录")
        self.cancel_btn = QPushButton("取消")
        self.layout = QVBoxLayout()
        self.layout.addWidget(QLabel("用户名"))
        self.layout.addWidget(self.username_edit)
        self.layout.addWidget(QLabel("密码"))
        self.layout.addWidget(self.password_edit)
        self.layout.addWidget(self.login_btn)
        self.layout.addWidget(self.cancel_btn)
        self.setLayout(self.layout)

        self.login_btn.clicked.connect(self.login)
        self.cancel_btn.clicked.connect(self.reject)

    def login(self):
        if (
            self.username_edit.text() == "addyya"
            and self.password_edit.text() == "sf123123"
        ):
            self.accept()
        else:
            QMessageBox.warning(self, "错误", "用户名或密码错误")
            self.reject()


@singleton
class LastFirewareDir:
    def __init__(self):
        self.last_fireware_dir = None
        self.config_file = os.path.join(
            os.path.dirname(__file__), "last_fireware_dir.json"
        )
        self.load_last_fireware_dir()

    def get_last_fireware_dir(self):
        """获取最近选择的固件目录"""
        return self.last_fireware_dir

    def save_last_fireware_dir(self, fireware_dir: str):
        """保存最近选择的固件目录到JSON文件"""
        self.last_fireware_dir = fireware_dir
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(
                    {"last_fireware_dir": fireware_dir}, f, ensure_ascii=False, indent=2
                )
        except Exception as e:
            logger.warning(f"保存固件目录配置失败: {e}")

    def load_last_fireware_dir(self):
        """从JSON文件加载最近选择的固件目录"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.last_fireware_dir = data.get("last_fireware_dir")
                    # 验证目录是否仍然存在
                    if self.last_fireware_dir and not os.path.exists(
                        self.last_fireware_dir
                    ):
                        logger.info(
                            f"保存的固件目录不存在，已清除: {self.last_fireware_dir}"
                        )
                        self.last_fireware_dir = None
        except Exception as e:
            logger.warning(f"加载固件目录配置失败: {e}")
            self.last_fireware_dir = None

    def clear_last_fireware_dir(self):
        """清除最近选择的固件目录"""
        self.last_fireware_dir = None
        try:
            if os.path.exists(self.config_file):
                os.remove(self.config_file)
        except Exception as e:
            logger.warning(f"删除固件目录配置文件失败: {e}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s - %(filename)s - %(lineno)d",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    app = QApplication(sys.argv)
    win = MainWindow()
    sys.exit(app.exec())
