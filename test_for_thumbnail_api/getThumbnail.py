import sys
import os
from PIL import Image
from io import BytesIO
import time
import asyncio
import aiohttp  # 新增：异步HTTP客户端
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)  # 获取上级目录（项目根目录）
sys.path.insert(0, project_root)  # 将项目根目录添加到Python路径
from api_sender import Api_sender
# 修复：使用正确的模块导入方式
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '202_detect_tool'))
from detect_tool_for_202.media_transfer_to_screen import GetFileFromAlbum
import logging
from typing import Literal
from datetime import datetime

logger = logging.getLogger(__name__)

class AsyncApiSender:
    """异步API发送器"""
    def __init__(self, api_sender: Api_sender):
        self.api_sender = api_sender
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def send_api_async(self, url: str, headers: dict, method: str = "GET"):
        """异步发送API请求"""
        try:
            if method.upper() == "GET":
                async with self.session.get(url, headers=headers) as response:
                    if response.status == 200:
                        content = await response.read()
                        return type('Response', (), {
                            'status_code': response.status,
                            'content': content,
                            'text': content.decode('utf-8', errors='ignore')
                        })()
                    else:
                        logger.error(f"API请求失败，状态码: {response.status}")
                        return None
            else:
                async with self.session.post(url, headers=headers) as response:
                    if response.status == 200:
                        content = await response.read()
                        return type('Response', (), {
                            'status_code': response.status,
                            'content': content,
                            'text': content.decode('utf-8', errors='ignore')
                        })()
                    else:
                        logger.error(f"API请求失败，状态码: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"异步请求发生错误：{e}")
            return None

class GetThumbnail:
    file_widht_list = Literal[199, 108]
    def __init__(self, async_api_sender: AsyncApiSender):
        self.async_api_sender = async_api_sender
    
    async def get_thumbnail(self, fileId: str, file_widht: Literal[199, 108]):
        file_widht = str(file_widht)
        server, port = self.async_api_sender.api_sender.get_server_and_port()
        url = f"http://{server}:{port}/api/v1/files/s3/{fileId}/h/{file_widht}"
        
        # 使用异步API调用
        result = await self.async_api_sender.send_api_async(url, self.async_api_sender.api_sender.header, "GET")
        
        if result is None:
            logger.error("API请求失败，返回None")
            return None
            
        if result.status_code != 200:
            logger.error(f"API请求失败，状态码: {result.status_code}")
            return None
            
        logger.info(f"成功获取缩略图，文件大小: {len(result.content)} 字节")
        return result

class GetPictureReslution:
    async def get_thumbnail_resolution(self, pic_bytes: bytes):
        try:
            # 使用线程池执行CPU密集型任务
            loop = asyncio.get_event_loop()
            img = await loop.run_in_executor(None, Image.open, BytesIO(pic_bytes))
            width, height = img.size
            logger.info(f"图片尺寸: {width}x{height}")
            return img.size
        except Exception as e:
            logger.error(f"获取图片分辨率失败: {e}")
            return None

class ImageViewer:
    """新增图片查看器类"""
    def __init__(self):
        pass
    
    def show_image(self, pic_bytes: bytes, title: str = "缩略图预览"):
        """显示图片"""
        try:
            img = Image.open(BytesIO(pic_bytes))
            logger.info(f"正在显示图片: {title}, 尺寸: {img.size}")
            img.show()  # 使用系统默认图片查看器显示
            return True
        except Exception as e:
            logger.error(f"显示图片失败: {e}")
            return False
    
    def save_image(self, pic_bytes: bytes, filename: str):
        """保存图片到本地"""
        try:
            img = Image.open(BytesIO(pic_bytes))
            img.save(filename)
            logger.info(f"图片已保存到: {filename}")
            return True
        except Exception as e:
            logger.error(f"保存图片失败: {e}")
            return False

async def process_single_image(get_thumbnail, get_picture_reslution, pic: str, index: int, total_count: int):
    """处理单张图片的异步函数"""
    start_time = time.time()
    try:
        result = await get_thumbnail.get_thumbnail(pic, 108)
        if result is None:
            logger.error(f"{index}/{total_count} {pic} 获取缩略图失败")
            return None, 0
        
        resolution = await get_picture_reslution.get_thumbnail_resolution(result.content)
        end_time = time.time()
        spent_time = round(end_time - start_time, 2)
        
        logger.info(f"{index}/{total_count} {pic} 获取缩略图耗时: {spent_time}s")
        logger.info(f"{index}/{total_count} {pic} 分辨率: {resolution}")
        
        return resolution, spent_time
    except Exception as e:
        logger.error(f"处理图片 {pic} 时出错: {e}")
        return None, 0

async def main_async():
    """主异步函数"""
    print("正在初始化API发送器...")
    api_sender = Api_sender("2698567570@qq.com", "sf123123", "18.215.241.226", 8080)
    
    try:
        pic_getter = GetFileFromAlbum(api_sender)
        pic_list = pic_getter.get_file_from_album()
        
        print("正在创建异步缩略图获取器...")
        async with AsyncApiSender(api_sender) as async_api_sender:
            get_thumbnail = GetThumbnail(async_api_sender)
            get_picture_reslution = GetPictureReslution()
            
            total_pic_count = len(pic_list)
            print(f"开始并发处理 {total_pic_count} 张图片...")
            
            # 创建所有图片的异步任务
            tasks = []
            for index, pic in enumerate(pic_list, 1):
                task = process_single_image(get_thumbnail, get_picture_reslution, pic, index, total_pic_count)
                tasks.append(task)
            
            # 并发执行所有任务
            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()
            
            # 统计结果
            successful_results = [r for r in results if r is not None and r[0] is not None]
            time_consume_list = [r[1] for r in results if r is not None and r[1] > 0]
            
            total_time = round(end_time - start_time, 2)
            avg_time = sum(time_consume_list) / len(time_consume_list) if time_consume_list else 0
            
            logger.info(f"并发处理完成！总耗时: {total_time}s")
            logger.info(f"成功处理: {len(successful_results)}/{total_pic_count} 张图片")
            logger.info(f"平均单张耗时: {avg_time:.2f}s")
            logger.info(f"并发效率提升: {total_time / (avg_time * total_pic_count) * 100:.1f}%")
            
    except Exception as e:
        logger.error(f"程序执行出错: {e}")
        print(f"程序执行出错: {e}")

if __name__ == "__main__":
    import os
    # 在当前目录下创建logs目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"当前目录: {current_dir}")
    os.makedirs(os.path.join(current_dir, 'logs'), exist_ok=True)

    # 生成日志文件名，包含时间戳
    log_filename = os.path.join(current_dir, 'logs', f'media_transfer_to_screen_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s %(filename)s:%(lineno)d',
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ],
        force=True
    ) 
    
    # 运行异步主函数
    asyncio.run(main_async())

