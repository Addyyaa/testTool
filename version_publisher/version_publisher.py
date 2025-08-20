from ast import pattern
import os
from pdb import run
import re
import sys
from PySide6.QtCore import QObject, Signal, Slot, Qt, QThread
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QProgressBar,
    QMessageBox,
)
from dataclasses import dataclass
import aiohttp
import asyncio
import logging
import base64
import tarfile

logger = logging.getLogger(__name__)


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

    env_info = "ts"
    package_name = "SStarOta.bin.gz"
    lcd_type_to_local_path = {
        "1": f"{env_info}/10.1_1920_1200/10_1920_1200_vvx10f002a/{package_name}",
        "2": f"{env_info}/13.3_1920_1080/13_1920_1080_nv156fhm/{package_name}",
        "7": f"{env_info}/10.1_800_1280/10_800_1280_fp7721bx2_innolux/{package_name}",
        "8": f"{env_info}/10.1_800_1280_BOE/10_800_1280_fp7721bx2_boe/{package_name}",
        "9": f"{env_info}/16_1920_1200/16_1920_1200_vvx10f002a/{package_name}",
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
        },
        "remote_path": {
            "10.1_800_1280": ""
        },  # TODO 需要继续完成根据屏幕类型，将remote地址base64编码请求七牛获取上传id
        "port": 8082 if env_info == "ts" else 8080,
    }


class Publisher(QObject):
    def __init__(self):
        super().__init__()
        pass


class GetfirewareInfo(QObject):
    def __init__(self):
        super().__init__()
        self.data_info = DataInfo()

    def get_fireware_version(self, path: str):
        mode = "r:gz" if path.endswith(".gz") else "r"
        try:
            with tarfile.open(path, mode) as tar:
                for member in tar.getmembers():
                    if (
                        member.isfile()
                        and os.path.basename(member.name) == "version.ini"
                    ):
                        file_obj = tar.extractfile(member)
                        if file_obj:
                            content = file_obj.read().decode("utf-8")
                            pattern = r"=\s*(.*?)\n"
                            version = re.search(pattern, content).group(1)
                            return version
                return None

        except Exception as e:
            logger.error(f"获取固件版本失败: {e}")
            sys.exit(1)


class Uploader(QObject):
    def __init__(self):
        super().__init__()
        self.data_info = DataInfo()
        self.manager_token = None
        self.qiniu_token = None
        self.qiniu_up_server = None

    async def get_manager_token(self):
        try:
            url = f"http://{self.data_info.server_info['api_server']['ts']}:{self.data_info.server_info['port']}{self.data_info.server_info['api']['manager_login']}"
            print(url)
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json={
                        "username": "sysadmin",
                        "password": "OST139.224.192.36",
                        "loginType": 2,
                        "account": "sysadmin",
                    },
                ) as response:
                    res = await response.json()
                    self.manager_token = res["data"]
                    return res["data"]
        except Exception as e:
            logger.error(f"获取管理员token失败: {e}")
            sys.exit(1)

    async def get_qiniu_token(self):
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

    async def get_qiniu_uploadID(self):

        url = f"https://{self.qiniu_up_server}{self.data_info.server_info['api']['qiniu_upload']}{self.data_info.server_info["remote_path"]}"

    async def upload_file(self, data):
        pass

    def main(self):
        res = asyncio.run(self.get_qiniu_server())
        print(res)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s - %(filename)s - %(lineno)d",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    up = Uploader()
    up.main()
    G = GetfirewareInfo()
    G.get_fireware_version(
        "F:/工作/照片墙/2代固件/优化版/2.01.39.4/2.01.39.4/cn/13_1920_1080_nv156fhm/SStarOta.bin.gz"
    )
