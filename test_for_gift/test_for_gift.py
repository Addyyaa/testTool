import asyncio
import os
import subprocess
import json
import sys
import time
import random
import tkinter as tk
from tkinter import filedialog
import datetime
import logging
from typing import Iterable
from PIL import Image
from ..api_sender import Api_sender
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed, ThreadPoolExecutor
import aiohttp
from .config import Config
import tzlocal
from .text_generator import create_text_generator

# 全局变量
protocol = "http"
host = "139.224.192.36"
port = "8082"
gift_sender_account = "test2@tester.com"
gift_sender_passwd = "sf123123"
gift_receiver_account = "15250996938"
gift_receiver_passwd = "sf123123"
screen_id = None
logger = logging.getLogger(__name__)



class AddGift:
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
        
        # 优化: 确保 greetingContent 是字符串类型
        if isinstance(greetingContent, list):
            self.greetingContent = "\n".join(greetingContent)
        else:
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
        self.user = gift_sender_account
        self.passwd = gift_sender_passwd
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
            logger.error(f"添加礼物失败: {result.text}\n{json.dumps(self.data)}")

class FileProcessor:
    """独立的文件处理类，所有方法都是静态方法，支持多进程"""
    
    @staticmethod
    def convert_image_to_jpg(file_path, save_path, userid, max_long_side=None, max_short_side=None):
        """转换图片为JPG格式，并限制分辨率"""
        import datetime
        from PIL import Image
        import logging
        
        # 如果没有传递参数，使用Config的当前值
        if max_long_side is None:
            max_long_side = Config.MAX_LONG_SIDE
        if max_short_side is None:
            max_short_side = Config.MAX_SHORT_SIDE
        
        logger = logging.getLogger(__name__)
        logger.debug(f"🔍 convert_image_to_jpg 使用分辨率限制: {max_long_side}x{max_short_side}")
        
        now = datetime.datetime.now()
        timestamp = now.strftime("%Y%m%d%H%M%S") + f"{now.microsecond // 1000:03d}"
        file_name = f"{userid}_{timestamp}"
        file_name_with_extension = f"{file_name}.jpg"
        full_save_path = save_path / file_name_with_extension
        
        try:
            with Image.open(file_path) as img:
                # 转换颜色模式
                if img.mode in ('RGBA', 'P', 'LA', 'L'):
                    img = img.convert('RGB')
                
                # 检查并调整分辨率
                width, height = img.size
                long_side = max(width, height)
                short_side = min(width, height)
                
                # 如果超过限制，需要缩放
                if long_side > max_long_side or short_side > max_short_side:
                    # 计算缩放比例
                    ratio_long = max_long_side / long_side if long_side > max_long_side else 1
                    ratio_short = max_short_side / short_side if short_side > max_short_side else 1
                    ratio = min(ratio_long, ratio_short)  # 使用较小的比例确保都在限制内
                    
                    new_width = int(width * ratio)
                    new_height = int(height * ratio)
                    
                    logger.debug(f"缩放图片 {file_path}: {width}x{height} -> {new_width}x{new_height} (限制: {max_long_side}x{max_short_side})")
                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                img.save(full_save_path, 'JPEG', quality=95, optimize=True)
                logger.info(f"转换图片{file_path}成功")
                return full_save_path
        except Exception as e:
            logger.error(f"转换图片-{file_path}失败: {e}")
            return None

    @staticmethod
    def convert_video_to_mp4(file_path, save_path, userid, max_long_side=None, max_short_side=None):
        """转换视频为MP4格式，并限制分辨率和帧率"""
        import datetime
        import subprocess
        import logging
        
        # 如果没有传递参数，使用Config的当前值 TODO 视频需要使用固定720P
        if max_long_side is None:
            max_long_side = 1280
        if max_short_side is None:
            max_short_side = 720
        
        logger = logging.getLogger(__name__)
        logger.debug(f"🔍 convert_video_to_mp4 使用分辨率限制: {max_long_side}x{max_short_side}")
        
        now = datetime.datetime.now()
        timestamp = now.strftime("%Y%m%d%H%M%S") + f"{now.microsecond // 1000:03d}"
        file_name = f"{userid}_{timestamp}"
        file_name_with_extension = f"{file_name}.mp4"
        full_save_path = save_path / file_name_with_extension
        
        try:
            logger.info(f"开始转换视频-{file_path}为mp4格式")
            
            # 构建ffmpeg命令，限制分辨率和帧率
            scale_filter = f"scale='min({max_long_side},iw)':'min({max_short_side},ih)':force_original_aspect_ratio=decrease"
            
            cmd = [
                'ffmpeg',
                '-i', str(file_path),
                '-c:v', 'libx264',
                '-vf', scale_filter,  # 使用动态分辨率限制
                '-fps_mode', 'cfr',  # 使用恒定帧率模式
                '-r', '30',  # 限制帧率为30fps
                '-c:a', 'aac',
                '-b:a', '128k',  # 音频比特率
                '-movflags', '+faststart',  # 优化流媒体播放
                '-y',  # 覆盖输出文件
                str(full_save_path)
            ]
            
            logger.debug(f"视频转换命令: {' '.join(cmd)}")
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

    @staticmethod
    def copy_file_to_temp_dir(file_path, temp_dir, userid, max_long_side=None, max_short_side=None):
        """将文件复制到临时目录并重命名"""
        import datetime
        import os
        import shutil
        import logging
        
        # 如果没有传递参数，使用Config的当前值
        if max_long_side is None:
            max_long_side = Config.MAX_LONG_SIDE
        if max_short_side is None:
            max_short_side = Config.MAX_SHORT_SIDE
        
        logger = logging.getLogger(__name__)
        logger.debug(f"🔍 copy_file_to_temp_dir 使用分辨率限制: {max_long_side}x{max_short_side}")
        
        try:
            now = datetime.datetime.now()
            timestamp = now.strftime("%Y%m%d%H%M%S") + f"{now.microsecond // 1000:03d}"
            file_name = f"{userid}_{timestamp}"
            file_extension = os.path.splitext(file_path)[1]
            file_name_with_extension = f"{file_name}{file_extension}"
            full_save_path = temp_dir / file_name_with_extension
            
            shutil.copy2(file_path, full_save_path)
            logger.info(f"复制文件{file_path}到{full_save_path}")
            return full_save_path
        except Exception as e:
            logger.error(f"复制文件{file_path}失败: {e}")
            return None


class Get_screen_info:
    def __init__(self):
        self.api_sender = Api_sender(gift_receiver_account, gift_receiver_passwd, host, port)
    def get_screen_info(self):
        def get_ota_data() -> list[dict]:
            api_sender1 = self.api_sender
            response = api_sender1.send_api(api_sender1.ota_list, data="", method="get")
            if response.status_code == 200 and response.json()["code"] == 20:
                group_device_relation = response.json()["data"]
                return group_device_relation
            else:
                logging.error(response.text)
                sys.exit()

        def show_all_screen_info():
            group_device_relation = get_ota_data()
            all_screens = []
            for group in group_device_relation:
                for screen in group['screenList']:
                    all_screens.append({
                    'screenId': screen['screenId'],
                    'groupId': group['id'],
                    'resolution': screen['format']
                })
            
            # 计算最大长度用于对齐
            max_screen_id_len = max(len(screen['screenId']) for screen in all_screens)
            max_group_id_len = max(len(str(screen['groupId'])) for screen in all_screens)
            max_resolution_len = max(len(screen['resolution']) for screen in all_screens)
            
            # 打印表头
            print("\n" + "="*80)
            print(f"{'序号':<4} {'屏幕ID':<{max_screen_id_len}} {'组ID':<{max_group_id_len}} {'分辨率':<{max_resolution_len}}")
            print("-"*80)
            
            # 获取用户选择
            while True:
                for index, screen in enumerate(all_screens):
                    print(f"{index + 1:<4} {screen['screenId']:<{max_screen_id_len}} {screen['groupId']:<{max_group_id_len}} {screen['resolution']:<{max_resolution_len}}")
                
                print("-"*80)
                ipt = input(f"请选择接收礼物素材的屏幕 (1-{len(all_screens)}): ")
                available_options = [str(i) for i in range(1, len(all_screens) + 1)]
                if ipt in available_options:
                    selected_screen_id = all_screens[int(ipt) - 1]['screenId']
                    selected_screen = all_screens[int(ipt) - 1]
                    print(f"\n✅ 已选择屏幕: {selected_screen['screenId']} (组ID: {selected_screen['groupId']}, 分辨率: {selected_screen['resolution']})")
                    break
                else:
                    print(f"❌ 输入错误，请选择 1-{len(all_screens)} 之间的序号")
                    print()
            global screen_id
            screen_id = selected_screen_id
            return {selected_screen_id: all_screens[int(ipt) - 1]['resolution']}

        return show_all_screen_info()
    

class file_uploader_to_fileServer:
    def __init__(self):
        self.user = gift_sender_account
        self.passwd = gift_sender_passwd
        self.api_sender = Api_sender(self.user, self.passwd, host, port)
        self.qiniu_token = None
        self.userid = None
        self.max_long_side = Config.MAX_LONG_SIDE
        self.max_short_side = Config.MAX_SHORT_SIDE
        self.qiniu_header = {
            "Accept-Encoding": "gzip",
            "user-agent": "Mozilla/5.0 (Linux; Android 13; M2104K10AC Build/TP1A.220624.014; wv) AppleWebKit/537.36 (KHTML, "
                        "like Gecko) Version/4.0 Chrome/115.0.5790.166 Mobile Safari/537.36 uni-app Html5Plus/1.0 ("
                        "Immersed/34.909092)",
            "host": "up-z2.qiniup.com",
            'Connection': 'Keep-Alive',
            'Charset': 'UTF-8',
        }
        self._get_userid()
    
    def _get_userid(self):
        """获取用户ID"""
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
    
    def read_local_file(self):
        """读取本地文件"""
        try:
            # 创建临时顶层窗口作为文件对话框的父窗口
            root = tk.Tk()
            root.withdraw()  # 隐藏主窗口
            
            # 获取屏幕尺寸
            screen_width = root.winfo_screenwidth()
            screen_height = root.winfo_screenheight()
            
            # 计算窗口位置使其居中
            x = (screen_width - 800) // 2  # 假设对话框宽度800
            y = (screen_height - 600) // 2  # 假设对话框高度600
            
            # 设置文件对话框位置和置顶
            root.geometry(f"+{x}+{y}")
            root.attributes('-topmost', True)
            
            file_path = filedialog.askopenfilenames(
                parent=root,
                title="选择图片或视频文件进行上传", 
                filetypes=[
                    ("所有文件", "*.*"),
                    ("图片文件", "*.jpg *.png *.jpeg *.webp"),
                    ("视频文件", "*.mp4 *.avi *.mov *.wmv *.flv *.mkv *.webm")
                ]
            )
            
            root.destroy()
            return file_path
            
        except Exception as e:
            logger.error(f"选择文件失败: {e}")
            return None
    
    def check_image_resolution(self, file_path):
        """检查图片分辨率是否超过限制"""
        try:
            with Image.open(file_path) as img:
                width, height = img.size
                # 确定长边和短边
                long_side = max(width, height)
                short_side = min(width, height)
                
                # 检查是否超过限制：使用实例变量
                if long_side > self.max_long_side or short_side > self.max_short_side:
                    logger.info(f"图片 {file_path} 分辨率 {width}x{height} 超过限制(长边≤{self.max_long_side}, 短边≤{self.max_short_side})")
                    return True  # 需要转换
                else:
                    logger.info(f"图片 {file_path} 分辨率 {width}x{height} 符合要求(长边≤{self.max_long_side}, 短边≤{self.max_short_side})")
                    return False  # 不需要转换
        except Exception as e:
            logger.error(f"检查图片分辨率失败 {file_path}: {e}")
            return True  # 出错时默认需要转换

    def check_video_specs(self, file_path):
        """检查视频分辨率和帧率是否超过限制"""
        try:
            import subprocess
            
            # 使用ffprobe获取视频信息
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_streams',
                str(file_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                logger.error(f"获取视频信息失败 {file_path}: {result.stderr}")
                return True  # 出错时默认需要转换
            
            import json
            data = json.loads(result.stdout)
            
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'video':
                    width = stream.get('width', 0)
                    height = stream.get('height', 0)
                    
                    # 获取帧率
                    fps_str = stream.get('r_frame_rate', '0/1')
                    try:
                        if '/' in fps_str:
                            num, den = fps_str.split('/')
                            fps = float(num) / float(den) if float(den) != 0 else 0
                        else:
                            fps = float(fps_str)
                    except:
                        fps = 0
                    
                    logger.info(f"视频 {file_path} 分辨率 {width}x{height}, 帧率 {fps:.2f}fps")
                    
                    # 检查分辨率限制：使用实例变量
                    long_side = max(width, height)
                    short_side = min(width, height)
                    
                    if long_side > self.max_long_side or short_side > self.max_short_side or fps > 30:
                        logger.info(f"视频 {file_path} 超过限制(分辨率≤{self.max_short_side}x{self.max_long_side}, 帧率≤30fps)")
                        return True  # 需要转换
                    else:
                        logger.info(f"视频 {file_path} 符合要求(分辨率≤{self.max_short_side}x{self.max_long_side}, 帧率≤30fps)")
                        return False  # 不需要转换
            
            return True  # 未找到视频流，默认需要转换
            
        except Exception as e:
            logger.error(f"检查视频规格失败 {file_path}: {e}")
            return True  # 出错时默认需要转换

    def judge_file_type(self, file_path):
        """判断文件类型"""
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

    def _create_temp_dir(self):
        """创建临时目录并清理旧文件"""
        import shutil
        
        dir_name = "tmp"
        current_dir = Path.cwd()
        dir_path = current_dir / dir_name
        
        # 如果目录存在，先清理旧文件
        if dir_path.exists():
            logger.info(f"发现临时目录，清理旧文件: {dir_path}")
            try:
                # 删除目录中的所有文件
                file_count = 0
                for file_path in dir_path.glob("*"):
                    if file_path.is_file():
                        file_path.unlink()
                        file_count += 1
                if file_count > 0:
                    logger.info(f"清理了 {file_count} 个旧文件")
            except Exception as e:
                logger.warning(f"清理临时目录失败: {e}")
                # 如果清理失败，尝试删除整个目录重新创建
                try:
                    shutil.rmtree(dir_path)
                    logger.info(f"删除整个临时目录并重新创建")
                except Exception as e2:
                    logger.error(f"删除临时目录失败: {e2}")
        
        # 确保目录存在
        if not dir_path.exists():
            dir_path.mkdir(parents=True)
            logger.info(f"创建临时目录: {dir_path}")
        
        return dir_path

    def _multiprocess_convert(self, file_list: list, save_path: Path, worker_func, max_workers: int = 4):
        """使用多进程转换文件"""
        result = []
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # 不传递分辨率参数，让静态方法使用Config的当前值
            futures = [executor.submit(worker_func, file, save_path, self.userid) for file in file_list]
            for future in as_completed(futures):
                try:
                    result.append(future.result())
                except Exception as e:
                    logger.error(f"处理文件时发生错误: {e}")
        return result

    def _generate_convert_file_list(self, file_path_list: Iterable):
        """生成需要转换的文件列表 - 包含分辨率和帧率检查"""
        video_convert_list = []
        image_convert_list = []
        no_convert_list = []
        
        for file_path in file_path_list:
            file_type = self.judge_file_type(file_path)
            if file_type == "invalid_path" or file_type == "error":
                logger.error(f"文件路径无效或判断文件类型时出错: {file_path}")
                sys.exit(1) 
            
            if isinstance(file_type, dict) and "image" in file_type:
                # 图片处理逻辑
                if file_type["image"] not in [".jpg", ".png"]:
                    # 不支持的图片格式，需要转换
                    image_convert_list.append(file_path)
                    logger.debug(f"图片 {file_path} 格式不支持，需要转换为JPG")
                else:
                    # 支持的格式，但需要检查分辨率
                    if self.check_image_resolution(file_path):
                        image_convert_list.append(file_path)
                        logger.debug(f"图片 {file_path} 分辨率超限，需要转换")
                    else:
                        no_convert_list.append(file_path)
                        logger.debug(f"图片 {file_path} 无需转换")
                        
            elif isinstance(file_type, dict) and "video" in file_type:
                # 视频处理逻辑
                if file_type["video"] != ".mp4":
                    # 不支持的视频格式，需要转换
                    video_convert_list.append(file_path)
                    logger.debug(f"视频 {file_path} 格式不支持，需要转换为MP4")
                else:
                    # 支持的格式，但需要检查分辨率和帧率
                    if self.check_video_specs(file_path):
                        video_convert_list.append(file_path)
                        logger.debug(f"视频 {file_path} 规格超限，需要转换")
                    else:
                        no_convert_list.append(file_path)
                        logger.debug(f"视频 {file_path} 无需转换")
            else:
                logger.error(f"文件类型错误: {file_path}") 
                
        logger.debug(f"文件分类完成: 图片转换{len(image_convert_list)}个, 视频转换{len(video_convert_list)}个, 无需转换{len(no_convert_list)}个")
        return image_convert_list, video_convert_list, no_convert_list

    def convert_file_to_support_format(self):
        """将本地文件转换为支持的格式"""
        # 创建临时目录
        temp_dir = self._create_temp_dir()
        
        # 读取需要上传的文件
        file_path_list = self.read_local_file()
        if file_path_list is None:
            logger.error("没有选择文件")
            sys.exit(1)
        
        # 生成需要转换的文件列表
        image_convert_list, video_convert_list, no_convert_list = self._generate_convert_file_list(file_path_list)
        
        # 使用多进程转换文件，传递静态方法
        pic_process_result = self._multiprocess_convert(
            image_convert_list, temp_dir, FileProcessor.convert_image_to_jpg
        ) if image_convert_list else []
        
        video_process_result = self._multiprocess_convert(
            video_convert_list, temp_dir, FileProcessor.convert_video_to_mp4
        ) if video_convert_list else []
        
        copy_result = self._multiprocess_convert(
            no_convert_list, temp_dir, FileProcessor.copy_file_to_temp_dir
        ) if no_convert_list else []
        
        all_results = pic_process_result + video_process_result + copy_result
        success_count = sum(1 for result in all_results if result is not None)
        total_count = len(all_results)
        
        if success_count == total_count:
            logger.info(f"所有文件处理成功，共处理{total_count}个文件")
        else:
            logger.warning(f"部分文件处理失败，成功{success_count}个，失败{total_count - success_count}个")
        
        return temp_dir

    def _get_qiniu_token(self):
        """获取七牛云token"""
        result = self.api_sender.send_api(self.api_sender.qiniu_token, self.api_sender.header, "get")
        if result and result.status_code == 200:
            self.qiniu_token = result.json().get("data", {})
            return self.qiniu_token
        else:
            logger.error("获取七牛云token失败")
            return None

    async def _upload_single_file(self, file_path, session):
        """上传单个文件到七牛云"""
        ext = os.path.splitext(file_path)[-1].lower()
        media_type = "image/jpeg" if ext == ".jpg" else "video/mp4"
        file_name = os.path.basename(file_path)
        key = os.path.splitext(file_name)[0]
        
        
        for i in range(3):
            try:
                data = aiohttp.FormData()
                data.add_field('token', self.qiniu_token)
                data.add_field('fname', f"user/photos/{self.userid}/{file_name}")
                data.add_field('key', key)
                logger.debug(f"++++>key: {key}\tfile_name: {file_name}\tmedia_type: {media_type}")
                
                with open(file_path, 'rb') as f:
                    data.add_field('file', f, filename=file_name, content_type=media_type)
                    
                    async with session.post(self.api_sender.qiniu_filesystem, data=data, headers=self.qiniu_header) as resp:
                        if resp.status == 200:
                            logger.debug(f"上传文件{file_path}成功")
                            return {"key": key, "type": "image" if media_type.startswith("image") else "video"}
                        else:
                            logger.warning(f"上传文件{file_path}失败，状态码{resp.status}，重试{i+1}次")
                            await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"上传文件{file_path}失败: {e}")
                await asyncio.sleep(1)
        
        return None

    async def upload_file(self, file_path_list: Iterable):
        """上传文件列表"""
        uploaded_images_list = []
        uploaded_videos_list = []
        
        # 获取七牛云token
        if self.qiniu_token is None:
            self.qiniu_token = self._get_qiniu_token()
            if not self.qiniu_token:
                logger.error("无法获取七牛云token，上传失败")
                return uploaded_images_list, uploaded_videos_list
        
        async with aiohttp.ClientSession() as session:
            tasks = [self._upload_single_file(file_path, session) for file_path in file_path_list]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, dict) and result:
                    if result["type"] == "image":
                        uploaded_images_list.append(result["key"])
                    else:
                        uploaded_videos_list.append(result["key"])
                elif isinstance(result, Exception):
                    logger.error(f"上传任务异常: {result}")
        
        return uploaded_images_list, uploaded_videos_list
    
    def uploaded_file_record(self, uploaded_images_list: list, uploaded_videos_list: list):
        """上传文件记录到本地json文件 - 追加模式"""
        # 文件路径
        file_path = Path(__file__).parent / "uploaded_file.json"
        
        # 创建新的上传记录
        new_record = {
            "timestamp": datetime.datetime.now().isoformat(),
            "images": uploaded_images_list,
            "videos": uploaded_videos_list,
            "total_count": len(uploaded_images_list) + len(uploaded_videos_list),
            "image_count": len(uploaded_images_list),
            "video_count": len(uploaded_videos_list)
        }
        
        # 读取现有记录
        existing_records = []
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # 如果现有文件是旧格式（单个记录），转换为列表格式
                    if isinstance(data, dict) and "records" in data:
                        existing_records = data["records"]
                    elif isinstance(data, dict) and "timestamp" in data:
                        # 旧格式的单个记录
                        existing_records = [data]
                    elif isinstance(data, list):
                        existing_records = data
                    else:
                        # 其他格式，作为单个记录处理
                        existing_records = [data]
            except Exception as e:
                logger.warning(f"读取现有上传记录失败: {e}，将创建新文件")
                existing_records = []
        
        # 添加新记录
        existing_records.append(new_record)
        
        # 创建最终的数据结构
        final_data = {
            "records": existing_records,
            "total_uploads": len(existing_records),
            "last_updated": datetime.datetime.now().isoformat()
        }
        
        # 保存到文件
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(final_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"上传记录已追加保存到: {file_path}")
        logger.info(f"本次上传: 图片{len(uploaded_images_list)}个，视频{len(uploaded_videos_list)}个")
        logger.info(f"总记录数: {len(existing_records)}次上传")
        return file_path
    
    def start(self):
        """启动文件上传流程"""
        temp_dir = self.convert_file_to_support_format()
        
        # 读取该目录下的所有文件，生成完整路径
        file_list = [os.path.join(temp_dir, f) for f in os.listdir(temp_dir) if os.path.isfile(os.path.join(temp_dir, f))]
        
        logger.info(f"准备上传 {len(file_list)} 个文件: {[os.path.basename(f) for f in file_list]}")
        
        # 上传文件
        uploaded_images, uploaded_videos = asyncio.run(self.upload_file(file_list))
        logger.info(f"上传完成：图片{len(uploaded_images)}个，视频{len(uploaded_videos)}个")
        
        # 可选：上传完成后清理临时文件
        self._cleanup_temp_dir(temp_dir)
        self.uploaded_file_record(uploaded_images, uploaded_videos)        
        return uploaded_images, uploaded_videos
    
    def _cleanup_temp_dir(self, temp_dir):
        """清理临时目录"""
        try:
            import shutil
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
                logger.info(f"清理临时目录: {temp_dir}")
        except Exception as e:
            logger.warning(f"清理临时目录失败: {e}")


class ParagraphGenerator:
    def __init__(self, language: str = None, sentence_num: int = 1):
        """
        @language: 语言，'en'或'zh'
        @sentence_num: 句子数量
        """
        if language is None:
            language = random.choice(["en", "zh"])
        self.create_text_generator = create_text_generator(language)
        self.sentence_num = sentence_num
    def generate_paragraph(self, count: int = 1):
        return self.create_text_generator.generate(rule_name="origin", count=count)



class bind_media_to_gift_code:
    def __init__(self):
        self.api_sender = Api_sender(gift_sender_account, gift_sender_passwd, host, port)
        self.paragraph_generator = ParagraphGenerator(sentence_num=2)
    def media_num_control(self, count: int):
        video_count = random.randint(1,2)
        image_count = count - video_count
        return video_count, image_count

    def bind_media_to_gift_code(self):
        # 获取当前时区
        timezone = str(tzlocal.get_localzone())
        logger.debug(f"timezone: {timezone}")
        uploaded_list = self.read_uploaded_file()
        if uploaded_list is None:
            logger.error("没有上传文件")
            sys.exit(1)
        video_list, image_list = uploaded_list
        cover_image = image_list[random.randint(0, len(image_list) - 1)]
        video_count, image_count = self.media_num_control(len(video_list))
        gift_image_list = random.sample(image_list, image_count)
        gift_video_list = random.sample(video_list, video_count)
        media_list_image = [{"fileId": _, "thumbnail": _, "mediaType": 0} for _ in gift_image_list]
        media_list_video = [{"fileId": _, "thumbnail": _, "mediaType": 1} for _ in gift_video_list]
        media_list = media_list_image + media_list_video
        greetingContent = self.paragraph_generator.generate_paragraph(count=2)
        greentingTitile = "文本随机生成测试!"
        sender_name = "MR.SHEN"
        receiver_name = "Addya"

        add_gift = AddGift(timezone, media_list, greetingContent, greentingTitile, cover_image, receiver_name, sender_name)
        gift_code = add_gift.add_gift()
        return gift_code

    def read_uploaded_file(self):
        video_list = []
        image_list = []
        file_path = Path(__file__).parent / "uploaded_file.json"
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for _ in data['records']:
                    video_list.extend(_['videos'])
                    image_list.extend(_['images'])
                logger.info(f"video_list: {video_list}")
                logger.info(f"image_list: {image_list}")
                return video_list, image_list
        return None
    

class Gift_receiver:
    def __init__(self, gift_code: str, screen_id: str):
        self.api_sender = Api_sender(gift_receiver_account, gift_receiver_passwd, host, port)
        self.gift_code = gift_code
        self.screen_id = screen_id
    def receive_gift(self):
        data = {
            "giftCode": self.gift_code,
            "screenId": self.screen_id
        }
        result = self.api_sender.send_api(self.api_sender.get_gift, data, "post")
        for _ in range(3):
            if result.status_code == 200 and result.json().get("code") == 20:
                return result.json()
            else:
                logger.error(f"获取礼物失败: {result.text}")
                time.sleep(1)
        return result

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d ===> %(message)s')
    # 先初始化屏幕信息
    def init_screen_info():
        
        screen_info = Get_screen_info()
        screen_info = screen_info.get_screen_info()
        resolution = list(screen_info.values())[0]
        if "X" in resolution:
            resolution = resolution.split("X")
        else:
            resolution = resolution.split("*")
        resolution = [_.strip() for _ in resolution]
    
        # 修改Config的值
        Config.MAX_LONG_SIDE = max(int(resolution[0]), int(resolution[1]))
        Config.MAX_SHORT_SIDE = min(int(resolution[0]), int(resolution[1]))
        return screen_info
    screen_info = init_screen_info()
    logger.info(f"screen_info: {screen_info}")
    # 上传文件到服务器
    def upload_file_to_server():
        fu = file_uploader_to_fileServer()
        fu.start()
    upload_file_to_server()
    # 将上传的文件绑定到礼物码上
    binder = bind_media_to_gift_code()
    gift_code = binder.bind_media_to_gift_code()["giftCode"]
    logger.info(f"gift_code: {gift_code}")
    # 接收礼物
    receiver = Gift_receiver(gift_code, list(screen_info.keys())[0])
    gift_info = receiver.receive_gift()
    logger.info(f"gift_info: {gift_info}")

