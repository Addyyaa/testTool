import json
import logging
import sys

import requests
from login import Login


class Api_sender:
    def __init__(self, user, passwd):
        self.user = user
        self.passwd = passwd
        server = "139.224.192.36"
        port = "8082"
        base_url = f"http://{server}:{port}"
        self.login_interface = f"{base_url}/api/v1/account/login"
        self.get_device = f"{base_url}/api/v1/host/screen/group/device/list"
        self.screen_list = f"{base_url}/api/v1/host/screen/group/list/relationWithVersion?screenGroupId="
        self.display = f"{base_url}/api/v1/host/screen/update/display"
        self.album_list = f"{base_url}/api/v1/photo/list"
        self.qiniu_filesystem = "http://up-z2.qiniup.com"
        self.qiniu_token = f"{base_url}/api/v1/files/token?code=86"
        self.meta_api = f"{base_url}/api/v1/capacity/file/meta"
        self.upload_ok = f"{base_url}/api/v1/photo/"
        self.user_id_api = f"{base_url}/api/v1/user/profile"
        self.get_screen_picture = f"{base_url}/api/v1/host/screen"
        self.video_to_commit = f"{base_url}/api/v1/screenVideo/publish/increment"
        self.get_album_images = f"{base_url}/api/v1/photo/info?albumId="
        self.album_picture_to_screen = f"{base_url}/api/v1/screenPicture/publish"
        self.get_storage = f"{base_url}/api/v1/screenVideo/extend"
        self.publish1 = f"{base_url}/api/v1/host/screen/update/pictureV3"
        self.publish2 = f"{base_url}/api/v1/screenPicture/publish"
        self.publish_sync = f"{base_url}/api/v1/screen/picture/sync/publish"
        self.screen_switch = f"{base_url}/api/v1/host/screen/group/switch"
        self.screen_timer_machine = f"{base_url}/api/v1/host/screen/group/switch/machine"
        self.ota_list = f"{base_url}/api/v1/otaUpgradeRecord/list"
        self.confirm_to_ota = f"{base_url}/api/v1/otaUpgradeRecord/confirm"
        self.cloud_sync = f"{base_url}/api/v1/screen/picture/sync/refresh"  #  云同步接口
        self.get_pic_withNoTf = f"{base_url}/api/v1/host/screen?screenDeviceId="  #  获取没有TF卡的屏幕图片
        self.get_pic_withTF = f"{base_url}/api/v1/screenPicture/page/list?pageNum=1&pageSize=10000&screenId="  #  获取有TF卡的屏幕图片
        self.device_type = f"{base_url}/api/v1/host/screen/group/list/relationWithVersion?screenGroupId="  #  获取设备类型
        self.qiuniutoken = None
        self.header = {
            "Content-Type": "application/json",
            "Accept-Encoding": "gzip",
            "user-agent": "Mozilla/5.0 (Linux; Android 13; M2104K10AC Build/TP1A.220624.014; wv) AppleWebKit/537.36 (KHTML,"
                          "like Gecko) Version/4.0 Chrome/115.0.5790.166 Mobile Safari/537.36 uni-app Html5Plus/1.0 ("
                          "Immersed/34.909092)",
        }
        self.__set_token()

    def send_api(self, api, data, method="post"):
        try:
            # data = json.dumps(data)
            if method.upper() == "POST":
                response1 = requests.post(api, json=data, headers=self.header, proxies=None)
            else:
                response1 = requests.get(api, params=data, headers=self.header, proxies=None)
            return response1
        except Exception as e:
            logging.error(f"请求发生错误：{e}")

    def __set_token(self):
        token = Login(self.user, self.passwd).login()
        self.header['X-TOKEN'] = token



