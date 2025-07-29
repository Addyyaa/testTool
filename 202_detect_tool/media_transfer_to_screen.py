import asyncio
from calendar import c
from datetime import datetime
from doctest import debug
import random
import sys
import os
import time
from turtle import circle
from unittest import result
import requests


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api_sender import Api_sender
from login import Manager
from telnet_connecter import Telnet_connector
import logging

logger = logging.getLogger(__name__)
# TODO 临时全局变量，等pad修复错误上报存储状态后删除
is_pad_has_tf = None

class GetFileFromAlbum:
    def __init__(self, api_sender):
        self.api_sender = api_sender
    
    def get_file_from_album(self):
        def _get_album_list(album_id):
            try:
                pic_api = self.api_sender.album_picture_list_with_page + '?albumId=' + str(album_id) + '&pageNum=1&pageSize=100000'
                result = self.api_sender.send_api(pic_api, {}, "get").json()
                album_list = result["data"]
                return album_list
            except Exception as e:
                logger.error(f"获取文件失败: {e}")
                sys.exit(1)
        
        def _album_list_with_pic_count(album_list):
            for album in album_list:
                record = _get_album_list(album["albumId"])["records"]
                album["photoCount"] = len(record)
                album["picList"] = record
            return album_list
        
        def _show_album_list(album_list):
            # 固定总宽度（建议60-80）
            TOTAL_WIDTH = 40
            # 序号区域宽度（如"10. "占4字符）
            INDEX_WIDTH = len(str(len(album_list))) + 2
            
            # 更健壮的显示宽度计算
            def display_width(text):
                if not isinstance(text, str):  # 处理非字符串输入
                    text = str(text)
                width = 0
                for char in text:
                    try:
                        # 汉字=2，其他=1（包括emoji）
                        width += 2 if '\u4e00' <= char <= '\u9fff' else 1
                    except TypeError:  # 处理意外字符类型
                        width += 1
                return width
            
            print("=" * 34 + "相册" + "=" * 34)
            
            for index, album in enumerate(album_list, 1):
                try:
                    name = str(album.get('albumName', '未知相册'))  # 强制转为字符串
                    count = album.get('photoCount', 0)
                    
                    # 计算填充空格
                    used_width = INDEX_WIDTH + display_width(name)
                    padding = max(1, TOTAL_WIDTH - used_width - 5)  # -5是"|| X张"的宽度
                    
                    # 构建行
                    line = (
                        f"{str(index).rjust(len(str(len(album_list))))}. "
                        f"{name}{' ' * padding}|| {count}张"
                    )
                    print(line)
                except Exception as e:
                    logger.error(f"格式化相册行失败: {e}")
                    continue  # 跳过错误行继续执行
            
            print("请选择相册:", end="")
            album_counts = len(album_list)
            while True:
                album_id = input()
                if album_id.isdigit() and 1 <= int(album_id) <= album_counts:
                    break
                else:
                    print("请输入有效的相册编号")
            return album_list[int(album_id) - 1]["albumId"]
        
        def _get_pic_list(album_id):
            pic_list = _get_album_list(album_id)["records"]
            return pic_list
        
        try:
            result = self.api_sender.send_api(self.api_sender.album_list, {}, "get").json()
            album_list1 = result["data"]
            album_list = _album_list_with_pic_count(album_list1)
            album_id = _show_album_list(album_list)
            pic_list = _get_pic_list(album_id)
            return pic_list      
        except Exception as e:
            logger.error(f"获取文件失败: {e}")
            sys.exit(1)

class SendCmdWithNewestContent:
    def __init__(self, tn: Telnet_connector):
        self.tn = tn
        self.is_first = True
        self.last_content = None
    
    async def send_cmd_with_newest_content(self, cmd: str):
        if self.is_first:
            result = await self.tn.send_command(cmd)
            self.last_content = result
            self.is_first = False
        else:
            result = await self.tn.send_command(cmd)
            if result.startswith(self.last_content):
                return result[len(self.last_content)].strip().replace(cmd, "")
        return result.replace(cmd, "")

class CheckScreenType:
    def __init__(self, api_sender, screen_id: str, gourp_id: str):
        self.api_sender = api_sender
        self.screen_id = screen_id
        self.gourp_id = gourp_id
    
    def check_screen_has_tf(self):
        screen_info = self.get_screen_type_info(self.screen_id, self.gourp_id)
        if int(screen_info["totalStorage"]) > 0:
            return True
        else:
            return False

    def check_screen_is_sync_version(self):
        screen_info = self.get_screen_type_info(self.screen_id, self.gourp_id)
        version = screen_info["version"].split(".")
        total_value = int(version[0]) * 1000 + int(version[1]) * 100 + int(version[2]) * 10 + int(version[3])
        if total_value >= 2100:
            return True
        else:
            return False



    
    def get_screen_type_info(self, screen_id: str, gourp_id: str):
        # TODO 临时全局变量，等pad修复错误上报存储状态后删除  
        global is_pad_has_tf
        if is_pad_has_tf is not None:
            return is_pad_has_tf
        # ----------------------------
        logger.info(f"screen_id: {screen_id}, gourp_id: {gourp_id}")
        try:
            type_info = self.api_sender.send_api(self.api_sender.screen_type_info + gourp_id, {}, "get", print_curl=True).json()["data"]
        except Exception as e:
            logger.error(f"获取屏幕信息失败: {e}")
            sys.exit(1)
        screen_info = None
        for screen in type_info:
            if screen["screenId"] == screen_id:
                screen_info = screen
                break
        if screen_info is None:
            logger.error(f"获取屏幕信息失败: {screen_id}")
            sys.exit(1)
        return screen_info

class Ask_user_for_info:
    def __init__(self, api_sender) -> None:
        self.api_sender = api_sender
    
    def show_album_list(self):
        """
        return:
            pic_list: list   用户选择的相册中的图片列表
        """
        get_file_from_album = GetFileFromAlbum(self.api_sender)
        pic_list = get_file_from_album.get_file_from_album()
        return pic_list

    def show_screen_list(self):
        """
        return:
            screen_id: str   用户选择的屏幕id
            screen_list: list   屏幕列表
        """
        get_screen_list = GetScreenList(self.api_sender)
        screen_list = get_screen_list.get_screen_list()
        for index, screen in enumerate(screen_list, 1):
            print(f"\n{index}. {screen['screenId']}{'\t' *3}所属屏幕组：{screen['groupName']}")
        print("请选择屏幕:", end="")
        while True:
            screen_id = input()
            if screen_id.isdigit() and 1 <= int(screen_id) <= len(screen_list):
                break
            else:
                print("请输入有效的屏幕编号")
        screen_id = screen_list[int(screen_id) - 1]["screenId"]
        return screen_id, screen_list
    


class TransferFileToScreen:
    def __init__(self, api_sender):
        self.api_sender = api_sender

    

    def transfer_file_to_screen(self, pic_list: list, screen_id: str, group_id: str):
        check_screen_type = CheckScreenType(self.api_sender, screen_id, group_id)
        if not check_screen_type.check_screen_has_tf():
            # 0.5GB版本使用v3接口
            try:
                body = []
                for index, pic in enumerate(pic_list, 1):
                    body.append({"pictureFileId": pic, "pictureSeq": index + 1, "screenDeviceId": screen_id})
                result = self.api_sender.send_api(self.api_sender.publish1, body, "post", print_curl=True).json()
                logger.info(f"result: {result}")
                if result and result["code"] == 20:
                    logger.info(f"文件传输成功")
                else:
                    logger.error(f"文件传输失败: {result["data"]}")
                    sys.exit(1)
            except Exception as e:
                logger.error(f"文件传输失败: {e}")
                sys.exit(1)
        elif check_screen_type.check_screen_is_sync_version():
            # 使用云同步版本接口
            try:
                body = {"screenId": screen_id, "screenPictureSet": []}
                for index, pic in enumerate(pic_list, 1):
                    body["screenPictureSet"].append({"fileId": pic, "sortOrder": index, "screenId": screen_id, "thumbnail": pic, "fileMd5": ""})
                result = self.api_sender.send_api(self.api_sender.publish_sync, body, "post", print_curl=True).json()
                logger.info(f"result: {result}")
                if result and result["code"] == 20:
                    logger.info(f"文件传输成功")
                    logger.info(f"提交图片{pic_list}到屏幕: {screen_id}")
                else:
                    logger.error(f"文件传输失败: {result["data"]}")
                    sys.exit(1)
            except Exception as e:
                logger.error(f"文件传输失败: {e}")
                sys.exit(1)
        else:
            # 带存储卡但是不是云同步版本
            try:
                body = {"screenId": screen_id, "screenPictureSet": []}
                for index, pic in enumerate(pic_list, 1):
                    body["screenPictureSet"].append({"fileId": pic, "sortOrder": index, "screenId": screen_id, "thumbnail": pic, "fileMd5": ""})
                result = self.api_sender.send_api(self.api_sender.album_picture_to_screen, body, "post", print_curl=True).json()
                if result and result["code"] == 20:
                    logger.info(f"文件传输成功")
                    logger.info(f"提交图片{pic_list}到屏幕: {screen_id}")
                else:
                    logger.error(f"文件传输失败: {result["data"]}")
                    sys.exit(1)
            except Exception as e:
                logger.error(f"文件传输失败: {e}")
                sys.exit(1)

    def main(self, pic_list: list, screen_id: str, group_id: str):
        self.transfer_file_to_screen(pic_list, screen_id, group_id)
        return pic_list, screen_id

class GetGroupList:
    def __init__(self, api_sender):
        self.api_sender = api_sender

    def get_group_list(self):
        try:
            result = self.api_sender.send_api(self.api_sender.group_list, {}, "get").json()
            return result["data"]
        except Exception as e:
            logger.error(f"获取文件失败: {e}")
            sys.exit(1)

class GetScreenList:
    def __init__(self, api_sender):
        self.api_sender = api_sender
    
    def get_screen_list(self):
        group_id_list = GetGroupList(self.api_sender).get_group_list()
        try:
            screen_list = []
            for group_id in group_id_list:
                result = self.api_sender.send_api(self.api_sender.screen_list + str(group_id['id']), {}, "get").json()
                screen_list.extend(result["data"])
            # 给屏幕列表数据增加所有屏幕组的组名
            for screen in screen_list:
                for group_id in group_id_list:
                    if screen["groupId"] == group_id['id']:
                        screen["groupName"] = group_id['name']
                        break
            return screen_list
        except Exception as e:
            logger.error(f"获取文件失败: {e}")
            sys.exit(1)

class CheckScreeenDownlaod:
    def __init__(self):
        self.tn = None
        self.send_cmd_with_newest_content = None
        self.has_tf = False
        self.start_detect = False
    
    async def check_screen_download(self, screen_id: str, pic_list: list):
        pic_list_config = pic_list.copy()
        pic_count = len(pic_list)
        screen_ip = GetScreenIp().get_screen_ip(screen_id)
        if self.tn is None:
            self.tn = Telnet_connector(screen_ip)
            await self.tn.connect()
            self.send_cmd_with_newest_content = SendCmdWithNewestContent(self.tn)
        has_tf = await self.send_cmd_with_newest_content.send_cmd_with_newest_content("ls /mnt/syncall.flag")
        if "/mnt/syncall.flag" in has_tf:
            self.has_tf = True

        if self.has_tf:
            cmd_pic_dir = "ls /mnt/picture/ | grep " 
        else:
            cmd_pic_dir = "ls /customer/picture/"
        
        while True:
            try:
                logger.info(f"pic_list: {pic_list}")
                if len(pic_list) == 0:
                    config_list = [ f"/customer/config/picture_config_{i}.ini" for i in range(1, 16)]
                    # 图片都已经下载完了，需要检查图片播放配置是否配置正确
                    for index, pic in enumerate(pic_list_config, 1):
                        logger.info(f"检查图片{index}/{len(pic_list_config)}: {pic}是否配置")
                        for config in config_list:
                            pic_config = await self.send_cmd_with_newest_content.send_cmd_with_newest_content(f"cat {config} | grep {pic}")
                            if pic in pic_config:
                                pic_list_config.remove(pic)
                                logger.info(f"图片{pic}已配置")
                                break
                    logger.info(f"图片{pic_list_config}未配置")
                    break
                try: 
                    pic_cache = await self.send_cmd_with_newest_content.send_cmd_with_newest_content("ls /customer/picture_cache/ |wc -l") 
                except Exception as e:
                    logger.error(f"转换pic_cache失败: {e}")
                    continue
                logger.info(f"pic_cache: {pic_cache}, pic_count: {pic_count}")
                if not self.start_detect:
                    self.start_detect = True
                    logger.info(f"开始检测屏幕是否下载完成")
                time_out = pic_count * 3
                start_time = time.time()
                async def _check_pic_download(pic_list):
                    if time.time() - start_time > time_out:
                        logger.error(f"图片下载超时, {pic_list} 未下载完成")
                        return
                    if len(pic_list) == 0:
                        return
                    for index, pic in enumerate(pic_list, 1):
                        cmd_pic = cmd_pic_dir + pic
                        result = await self.send_cmd_with_newest_content.send_cmd_with_newest_content(cmd_pic)
                        if pic in result:
                            logger.info(f"图片{index}/{len(pic_list)}: {pic}已下载完成")
                            pic_list.remove(pic)
                        else:
                            logger.info(f"图片{index}/{len(pic_list)}: {pic}未检测到，等待下一轮查询")
                        await asyncio.sleep(1)
                    
                    # 直接递归调用，无需 asyncio.run
                    await _check_pic_download(pic_list)

                await _check_pic_download(pic_list)
            except Exception as e:
                logger.error(f"获取缓存图片数量失败: {e}")
        
class GetScreenIp:
    def __init__(self):
        self.manager = Manager()

    def get_screen_ip(self, screen_id: str):
        token = self.manager.get_token()
        header = {
            "content-type": "application/json",
            "x-token": token
        }
        url = self.manager.get_screen_ip + screen_id
        response = requests.get(url, headers=header)
        return response.json()["data"]["records"][0]["ip"]



if __name__ == "__main__":
    import os
    #在当前目录下创建logs目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"current_dir: {current_dir}")
    os.makedirs(os.path.join(current_dir, 'logs'), exist_ok=True)

    # 生成日志文件名，包含时间戳
    log_filename = os.path.join(current_dir, 'logs', f'media_transfer_to_screen_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')

    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - [%(levelname)s] - %(module)s:%(filename)s:%(lineno)d - %(funcName)s() - %(message)s',
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ],
        force=True  # 强制重新配置，移除所有现有处理器
    )
    logger = logging.getLogger(__name__)
    logger.info("脚本启动，测试日志功能")  # 测试日志

    # 强制刷新日志
    for handler in logging.root.handlers:
        handler.flush()

    api_sender = Api_sender("test2@tester.com", "sf123123", "139.224.192.36", "8082")
    transfer_file_to_screen = TransferFileToScreen(api_sender)
    ask_user_for_info = Ask_user_for_info(api_sender)
    pic_list = ask_user_for_info.show_album_list()
    pic_list_copy = pic_list.copy()
    screen_id, screen_list = ask_user_for_info.show_screen_list()
    for screen in screen_list:
            if screen["screenId"] == screen_id:
                group_id = str(screen["groupId"])
                logger.info(f"group_id: {group_id}")
                break

    pic_len = len(pic_list)
    circle_count = 0
    # 从piclist随机挑选形成要测试的图片列表
    while True:
        test_pic_list = random.sample(pic_list_copy, k=int(pic_len * 0.1))
        pic_list, screen_id = transfer_file_to_screen.main(test_pic_list, screen_id, group_id)
        logger.info(f"circle_count: {circle_count}")
        circle_count += 1
        ck = CheckScreeenDownlaod()
        asyncio.run(ck.check_screen_download(screen_id, test_pic_list))