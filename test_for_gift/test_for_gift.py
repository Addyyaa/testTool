import asyncio
import os
import subprocess
import json
import sys
import time
import random
from tkinter import filedialog
import datetime
import logging
from typing import Iterable
from PIL import Image
from ..api_sender import Api_sender
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed, ThreadPoolExecutor
import requests
import aiohttp
# 全局变量
protocol = "http"
host = "139.224.192.36"
port = "8082"
logger = logging.getLogger(__name__)

class addGift:
    def __init__(self, timezone: str, media_list: list = [], 
                 greetingContent: str = "", 
                 greentingTitile: str = "", 
                 greetingImg: str = "", 
                 receiver_name: str = "", 
                 sender_name: str = ""):
        """
        添加礼物
        :param timezone: 时区
        :param media_list: 媒体列表
        :param greetingContent: 祝福内容
        :param greentingTitile: 祝福标题
        :param greetingImg: 祝福图片
        :param receiver_name: 接收者姓名
        :param sender_name: 发送者姓名
        """
        self.timezone = timezone
        self.media_list = media_list
        self.greetingContent = greetingContent
        self.greentingTitile = greentingTitile
        self.greetingImg = greetingImg
        self.receiver_name = receiver_name
        self.sender_name = sender_name
        self.data = {
            "timezone": self.timezone,
            "giftsMediaList": self.media_list,
            "greetingContent": self.greetingContent,
            "greetingTitle": self.greentingTitile,
            "greetingImage": self.greetingImg,
            "recipientName": self.receiver_name,
            "signature": self.sender_name,
            "sendTime": datetime.datetime.now().strftime("%Y-%m-%d"),

        }
        self.user = "test2@tester.com"
        self.passwd = "sf123123"
        self.api_sender = Api_sender(self.user, self.passwd, host, port)
     
    def add_gift(self):
        
        result = self.api_sender.send_api(self.api_sender.add_gift, self.data, "post")
        if result and result.status_code == 200:
            content = result.json()
            if content["code"] == 20:
                data = content["data"]
                return data
            else:
                logger.error(f"添加礼物失败: {content['message']}")
        elif result:
            logger.error(f"添加礼物失败: {result.status_code}\t{result.text}")
        else:
            logger.error(f"添加礼物失败: {result}")

class file_uploader_to_fileServer:
    def __init__(self):
        self.user = "test2@tester.com"
        self.passwd = "sf123123"
        self.api_sender = Api_sender(self.user, self.passwd, host, port)
        self.qiniu_token = None
        self.userid = None
        self.qiniu_header = {
            "Accept-Encoding": "gzip",
            "user-agent": "Mozilla/5.0 (Linux; Android 13; M2104K10AC Build/TP1A.220624.014; wv) AppleWebKit/537.36 (KHTML, "
                        "like Gecko) Version/4.0 Chrome/115.0.5790.166 Mobile Safari/537.36 uni-app Html5Plus/1.0 ("
                        "Immersed/34.909092)",
            "host": "up-z2.qiniup.com",
            'Connection': 'Keep-Alive',
            'Charset': 'UTF-8',
        }
        def get_userid():
            if self.userid is None:
                retry_time = 3
                for i in range(retry_time):
                    result = self.api_sender.send_api(self.api_sender.user_id_api, self.api_sender.header, "get")
                    if result:
                        self.userid = result.json()["data"]["userId"]
                        logger.info(f"userid: {self.userid}")
                        break
                    else:
                        logger.error(f"获取userid失败, 重试{i+1}次")
                        time.sleep(1)
                if self.userid is None:
                    logger.error("获取userid失败")
                    sys.exit(1)
        get_userid()
    
    def read_local_file(self):
        try:
            file_path = filedialog.askopenfilenames(title="选择图片或视频文件进行上传", filetypes=[("所有文件", "*.*"),
                                                                                   ("图片文件", "*.jpg *.png *.jpeg *.webp"),
                                                                    ("视频文件", "*.mp4 *.avi *.mov *.wmv *.flv *.mkv *.webm")])
            return file_path
        except Exception as e:
            logger.error(f"选择文件失败: {e}")
            return None
    
    def judge_file_type(self, file_path):
        """
        判断文件类型。

        :param file_path: 文件的完整路径。
        :return: 返回 "image"（图片）、"video"（视频）或 "unknown"（未知）。如果路径无效，则返回 "invalid_path"。
        """
        if not file_path or not isinstance(file_path, str):
            logger.warning("提供的文件路径无效。")
            return "invalid_path"

        try:
            # 分离文件名和扩展名
            _, file_extension = os.path.splitext(file_path)
            # 将扩展名转换为小写以便于比较
            file_extension = file_extension.lower()

            # 定义支持的图片和视频文件扩展名
            image_extensions = ['.jpg', '.png', '.jpeg', '.webp', '.gif', '.bmp']
            video_extensions = ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv', '.webm']

            if file_extension in image_extensions:
                return {"image": file_extension}
            elif file_extension in video_extensions:
                return {"video": file_extension}
            else:
                return {"unknown": file_extension}
        except Exception as e:
            logger.error(f"在判断文件类型时发生错误: {e}")
            return "error"

    def convert_file_to_support_format(self):
        """
        将本地文件转换为支持的格式
        1. 读取本地文件
        2. 判断文件类型
        3. 转换文件
        4. 返回存储转换后的文件的临时目录
        """
        def create_temp_dir():
            dir_name = "tmp"
            current_dir = Path.cwd()
            dir_path = current_dir / dir_name
            if not dir_path.exists():
                dir_path.mkdir(parents=True)
            return dir_path
        
        def convert_image_to_jpg(file_path, save_path):
            now = datetime.datetime.now()
            timestamp = now.strftime("%Y%m%d%H%M%S") + f"{now.microsecond // 1000:03d}"
            file_name = f"{self.userid}_{timestamp}"
            file_name_with_extension = f"{file_name}.jpg"
            full_save_path = save_path / file_name_with_extension
            try:
                with Image.open(file_path) as img:
                    if img.mode in ('RGBA', 'P', 'LA', 'L'):
                        img = img.convert('RGB')
                    img.save(full_save_path, 'JPEG', quality=95, optimize=True)
                return full_save_path
            except Exception as e:
                logger.error(f"转换图片-{file_path}失败: {e}")
                return None

        def convert_video_to_mp4(file_path, save_path):
            now = datetime.datetime.now()
            timestamp = now.strftime("%Y%m%d%H%M%S") + f"{now.microsecond // 1000:03d}"
            file_name = f"{self.userid}_{timestamp}"
            file_name_with_extension = f"{file_name}.mp4"
            full_save_path = save_path / file_name_with_extension
            try:
                logger.info(f"开始转换视频-{file_path}为mp4格式")
                cmd = [
                    'ffmpeg',
                    '-i', file_path,
                    '-c:v', 'libx264',
                    '-r', '30',
                    '-vsync', 'vfr',
                    '-c:a', 'aac',
                    '-strict', '-2',
                    full_save_path
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                if result.returncode == 0:
                    logger.info(f"转换视频-{file_path}成功")
                    return full_save_path
                else:
                    logger.error(f"转换视频-{file_path}失败: {result.stderr}")
                    return None
            except Exception as e:
                logger.error(f"转换视频-{file_path}失败: {e}")
                return None

        def multiprocess_convert(file_list: list, save_path: Path, deal_event, max_workers: int = 4):
            result = []
            with ProcessPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(deal_event, file, save_path) for file in file_list]
                for future in as_completed(futures):
                    try:
                        result.append(future.result())
                    except Exception as e:
                        logger.error(f"处理文件时发生错误: {e}")
            return result
        
        def generate_convert_file_list(file_path_list: Iterable):
            video_convert_list = []
            image_convert_list = []
            for file_path in file_path_list:
                file_type = self.judge_file_type(file_path)
                if file_type == "invalid_path" or file_type == "error":
                        logger.error(f"文件路径无效或判断文件类型时出错: {file_path}")
                        sys.exit(1) 
                if file_type == "image":
                    if file_type["image"] != ".jpg" and file_type["image"] != ".png":
                        # 需要转换为jpg格式的图片
                        image_convert_list.append(file_path)
                elif file_type == "video":
                    if file_type["video"] != ".mp4":
                        # 需要转换为mp4格式的视频
                        video_convert_list.append(file_path)
                else:
                    logger.error(f"文件类型错误: {file_path}") 
            return image_convert_list, video_convert_list
        
        def start():
            # 创建一个临时目录用于存放转换后的文件
            temp_dir = create_temp_dir()
            # 读取需要上传的文件
            file_path_list = self.read_local_file()
            if file_path_list is None:
                logger.error("没有选择文件")
                sys.exit(1)
            # 生成需要上传的文件列表
            image_convert_list, video_convert_list = generate_convert_file_list(file_path_list)
            # 转换图片
            pic_process_result = multiprocess_convert(image_convert_list, temp_dir, convert_image_to_jpg)
            # 转换视频
            video_process_result = multiprocess_convert(video_convert_list, temp_dir, convert_video_to_mp4)
            
            if pic_process_result and video_process_result:
                logger.info("所有文件转换成功")
            else:
                logger.error("部分文件转换失败")
            return temp_dir
        
        return start()
        
        
    def upload_file(self, file_path_list: Iterable):
        uploaded_images_list = []
        uploaded_videos_list = []
        def get_qiniu_token():
            self.qiniu_token = self.api_sender.send_api(self.api_sender.qiniu_token, self.api_sender.header, "get")
        
        # 获取qiniu的token
        if self.qiniu_token is None:
            get_qiniu_token()
        async def upload_file_to_qiniu(file_path):
            ext = os.path.splitext(file_path)[-1].lower()
            media_type = "image/jpeg" if ext == ".jpg" else "video/mp4"
            file_name = os.path.basename(file_path)
            key = os.path.splitext(file_name)[0]
            logger.info(f"上传文件{file_path}，文件名{file_name}，key{key}，媒体类型{media_type}")
            for i in range(3):
                try:
                    data = aiohttp.FormData()
                    data.add_field('token', self.qiniu_token)
                    data.add_field('fname', f"user/photos/{self.userid}/{file_name}")
                    data.add_field('key', key)
                    data.add_field('file', open(file_path, 'rb'), filename=file_name, content_type=media_type)
                    async with aiohttp.ClientSession() as session:
                        async with session.post(self.api_sender.qiniu_filesystem, data=data, headers=self.qiniu_header) as resp:
                            if resp.status == 200:
                                logger.info(f"上传文件{file_path}成功")
                                if media_type.startswith("image"):
                                    uploaded_images_list.append(key)
                                else:
                                    uploaded_videos_list.append(key)
                                break
                            else:
                                logger.warning(f"上传文件{file_path}失败，重试{i+1}次")
                                await asyncio.sleep(1)
                except Exception as e:
                    logger.error(f"上传文件{file_path}失败: {e}")
                    await asyncio.sleep(1)
                

        async def start():
            tasks = [upload_file_to_qiniu(file_path) for file_path in file_path_list]
            await asyncio.gather(*tasks)
            return uploaded_images_list, uploaded_videos_list
        return asyncio.run(start())
    
    
    def start(self):
        temp_dir = self.convert_file_to_support_format()
        # 读取该目录下的所有文件
        file_list = os.listdir(temp_dir)
        # 上传文件
        self.upload_file(file_list)
          

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s %(filename)s:%(lineno)d')
    # add_gift = addGift(timezone="Asia/Shanghai", media_list=[], greetingContent="这是一个礼物脚本测试", greentingTitile="这是一个礼物脚本测试", greetingImg="", receiver_name="Andyya", sender_name="Andyya")
    # add_gift.add_gift()
    fu = file_uploader_to_fileServer()
    file_list = fu.read_local_file()
    fu.upload_file(file_list)
