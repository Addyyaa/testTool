import logging
import sys

import requests

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
        response = requests.post(self.login_interface, json=self.body_data, headers=self.header)
        if response.status_code == 200 and response.json()["code"] == 20:
            rp = response.json()
            # 提取token
            self.header['X-TOKEN'] = rp["data"]
            logger.info(f"body_data: {self.body_data}")
            logger.info("登录成功！")
            return rp["data"]
        else:
            logging.error(f"{response.text}\n{self.body_data}")
            sys.exit()
    
    def get_header(self):
        return self.header
