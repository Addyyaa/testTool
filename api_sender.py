
import logging
import curlify
import requests
from .login import Login

logger = logging.getLogger(__name__)

class Api_sender:
    def __init__(self, user, passwd, host, port, login_type=None):
        self.user = user
        self.passwd = passwd
        self.server = host
        self.port = port
        
        self.login = Login(self.user, self.passwd, self.server, self.port)
        self.login.login()  # 执行登录
        self.header = self.login.header # 获取登录后的header

        if not self.header.get("X-TOKEN"):
            logger.error("获取token失败,请检查账号密码")
            return

        base_url = f"http://{self.server}:{self.port}"
        self.login_interface = f"{base_url}/api/v1/account/login"
        self.get_device = f"{base_url}/api/v1/host/screen/group/device/list"
        self.screen_list = f"{base_url}/api/v1/host/screen/group/list/relationWithVersion?screenGroupId="
        self.display = f"{base_url}/api/v1/host/screen/update/display"
        self.album_list = f"{base_url}/api/v1/photo/list"
        self.album_picture_list = f"{base_url}/api/v1/photo/album/list?albumId="
        self.album_picture_list_with_page = f"{base_url}/api/v1/photo/album/list"
        self.group_list = f"{base_url}/api/v1/host/screen/group/list?pageNum=1&pageSize=10000"
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
        self.screen_type_info = f"{base_url}/api/v1/host/screen/group/list/relationWithVersionStorage?screenGroupId="
        self.add_gift = f"{base_url}/api/v1/gifts/add"
        self.get_gift = f"{base_url}/api/v1/gifts/receive"
        self.gift_del = f"{base_url}/api/v1/gifts/del"
        self.gift_list = f"{base_url}/api/v1/gifts/list"
        self.gift_list_receive = f"{base_url}/api/v1/gifts/receive/list"
        self.qiuniutoken = None
        self.header = {
            "Content-Type": "application/json",
            "Accept-Encoding": "gzip",
            "user-agent": "Mozilla/5.0 (Linux; Android 13; M2104K10AC Build/TP1A.220624.014; wv) AppleWebKit/537.36 (KHTML,"
                          "like Gecko) Version/4.0 Chrome/115.0.5790.166 Mobile Safari/537.36 uni-app Html5Plus/1.0 ("
                          "Immersed/34.909092)",
        }
        self.__set_token()

    def send_api(self, api, data, method="post", print_curl=False):
        try:
            # data = json.dumps(data)
            if method.upper() == "POST":
                response1 = requests.post(api, json=data, headers=self.header, proxies=None)
            else:
                response1 = requests.get(api, params=data, headers=self.header, proxies=None)
            if response1.status_code == 401:
                raise Exception("401")
            if response1.status_code == 200:
                if print_curl:
                    logger.info(f"{'=' * 50 + 'CURL' + '=' * 50}\n{curlify.to_curl(response1.request)}\n{'=' * 50 + 'END' + '=' * 50}")
                    logger.info(f"{'=' * 50 + 'RESPONSE' + '=' * 50}\n{response1.headers}\nCONTENT:\t{response1.content}\n{'=' * 50 + 'END' + '=' * 50}")
                return response1
            return response1  # 返回其他状态码的响应，让调用者处理
        except Exception as e:
            if str(e) == "401":  # 修改这里，使用str(e)来比较 
                self.__set_token()
                return self.send_api(api, data, method)
            else:
                logger.error(f"请求发生错误：{e}")
                return None
    
            

    def __set_token(self):
        token = Login(self.user, self.passwd, self.server, self.port).login()
        self.header['X-TOKEN'] = token
    
    def get_token(self):
        return self.header['X-TOKEN']

    def get_server_and_port(self):
        return self.server, self.port



