import logging
import sys
import time
from tkinter import NO
import requests
import os

# 配置 logging 模块
logger = logging.getLogger(__name__)



class Login:
    def __init__(self, account: str, password: str, server: str = "139.224.192.36", port: str = "8082"):
        self.account = account
        self.password = password
        self.server = server
        self.port = port
        self.login_interface = f"http://{self.server}:{self.port}/api/v1/account/login"
        
        # 将 header 和 body_data 作为实例变量初始化
        self.header = {
            "Content-Type": "application/json",
            "Accept-Encoding": "gzip",
            "user-agent": "Mozilla/5.0 (Linux; Android 13; M2104K10AC Build/TP1A.220624.014; wv) AppleWebKit/537.36 (KHTML,"
                          "like Gecko) Version/4.0 Chrome/115.0.5790.166 Mobile Safari/537.36 uni-app Html5Plus/1.0 ("
                          "Immersed/34.909092)",
        }
        self.body_data = {
            "account": "",
            "password": "",
            "areaCode": "+86",
            "loginType": "2"
        }

    def login(self):
        if '@' in self.account:
            if "areaCode" in self.body_data:
                self.body_data.pop("areaCode")
            self.body_data['loginType'] = '3'
        else:
            self.body_data['areaCode'] = '+86'
            self.body_data['loginType'] = '2'  # 明确设置手机登录类型
        self.body_data["account"] = self.account
        self.body_data["password"] = self.password
        for i in range(3):
            response = requests.post(self.login_interface, json=self.body_data, headers=self.header)
            if response.status_code == 200 and response.json()["code"] == 20:
                rp = response.json()
                # 提取token
                self.header['X-TOKEN'] = rp["data"]
                logger.debug(f"body_data: {self.body_data}")
                logger.debug("登录成功！")
                return rp["data"]
            else:
                logger.error(f"{response.status_code}\n{response.text}\n{self.body_data}")
                logger.error(f"登录失败，重试{i+1}次")
                time.sleep(1)
        sys.exit()
            
        
    def get_header(self):
        return self.header


class Manager:
    def __init__(self, server: str = "139.224.192.36", port: str = "8082"):
        self.server = server
        self.port = port
        self.user_name = os.getenv("ACCOUNT", "sysadmin")
        self.password = os.getenv("PASSWORD", "OST139.224.192.36")  
        self.token = None
        self.get_screen_ip = f"http://{self.server}:{self.port}/api/v1/manage/screen/list?pageSize=10&pageNum=1&screenId="
        self.login()

    def login(self):
        login_api = f"http://{self.server}:{self.port}/api/v1/manage/system/auth/login"
        headers = {
            "Content-Type": "application/json",  # 明确指定 JSON 格式
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Linux; Android 13; M2104K10AC Build/TP1A.220624.014; wv) AppleWebKit/537.36 (KHTML,"
                          "like Gecko) Version/4.0 Chrome/115.0.5790.166 Mobile Safari/537.36 uni-app Html5Plus/1.0 ("
                          "Immersed/34.909092)",
        }
        body = {
            "account": self.user_name,
            "password": self.password,
            "username": self.user_name,
            "loginType": "2"
        }
        
        try:
            # 使用 json 参数自动序列化并设置 Content-Type
            response = requests.post(login_api, json=body, headers=headers, timeout=10)
            
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    if response_data.get("code") == 20:  # 根据接口文档调整成功码
                        self.token = response_data["data"]
                        return self.token
                    else:
                        logger.error(f"登录失败: {response_data}")
                except ValueError:
                    logger.error(f"响应不是 JSON 格式: {response.text}")
            else:
                logger.error(f"HTTP 错误: {response.status_code}")
            
            sys.exit(1)
        except requests.exceptions.RequestException as e:
            logger.error(f"请求异常: {e}")
            sys.exit(1)

    def get_token(self):
        return self.token if self.token else self.login()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s - %(filename)s - %(lineno)d')
    manager = Manager()