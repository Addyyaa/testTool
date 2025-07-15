import sys
import time
import random
from testTool.api_sender import Api_sender
import logging
from ..date_tool import convert_timestamp_to_time, format_time_duration

logger = logging.getLogger(__name__)

class SwitchDisplayMode:
    def __init__(self, account: str, password: str, host: str, port: str):
        self.api_sender = Api_sender(account, password, host, port)
        self.account = account
        self.password = password
    def switch_display_mode(self, display_mode: str, screen_id: str):
        """
        1. 图片轮播
        2. 图片独播
        3. 时钟
        4. 万年历
        5. 序号
        6. 重启他界面返回
        7. 视频轮播
        8. 视频独播
        9. 从其他显示模式回到视频模式
        11. 图片随机播放
        12. 视频随机播放
        13. 混播随机播放
        """
        data = {
            "displayMode": display_mode,
            "screenId": screen_id
        }
        result = self.api_sender.send_api(self.api_sender.display, data=data, method="post")
        if result is not None:
            try:
                resp_json = result.json()
                if resp_json.get("code") == 20:
                    logger.info(f"{screen_id} switch_display_mode success")
                else:
                    logger.error(f"switch_display_mode failed\t{result.text}\nbody:{data}")
            except Exception as e:
                logger.error(f"解析响应失败: {e}\t{getattr(result, 'text', '')}")
        else:
            logger.error(f"switch_display_mode failed, no response")

    # def convert_timestamp_to_time(self, timestamp: int, max_unit: str = "Y", min_unit: str = "s"):
    #     max_unit = max_unit.upper()
    #     min_unit = min_unit.upper()
        
    #     divisor = {
    #         "Y": 365 * 24 * 60 * 60,
    #         "MO": 30 * 24 * 60 * 60,
    #         "D": 24 * 60 * 60,
    #         "H": 60 * 60,
    #         "M": 60,
    #         "S": 1,
    #     }

    #     zh_unit_map = {
    #         "Y": "年",
    #         "MO": "月",
    #         "D": "日",
    #         "H": "时",
    #         "M": "分",
    #         "S": "秒",
    #     }

    #     time_map = {
    #         "Y": 6,
    #         "MO": 5,
    #         "D": 4,
    #         "H": 3,
    #         "M": 2,
    #         "S": 1,
    #     }
    #     if time_map[max_unit] < time_map[min_unit]:
    #         logger.error(f"max_unit: {max_unit} 不能小于 min_unit: {min_unit}")
    #         return {}
    #     result = {}
    #     for key, value in time_map.items():
    #         if value > time_map[max_unit]:
    #             continue
    #         if value < time_map[min_unit]:
    #             continue
    #         result[zh_unit_map[key]] = timestamp // divisor[key]
    #         timestamp = timestamp % divisor[key]
    #     return result



             


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d ===> %(message)s')
    switch_display_mode = SwitchDisplayMode(account="test2@tester.com", password="sf123123", host="139.224.192.36", port="8082")

    display_mode = {
        "1": "图片轮播",
        "2": "图片独播",
        "3": "时钟",
        "4": "万年历",
        "5": "序号",
        "6": "重启他界面返回",
        "7": "视频轮播",
        "8": "视频独播",
        "9": "从其他显示模式回到视频模式",
        "11": "图片随机播放",
        "12": "视频随机播放",
        "13": "混播随机播放",
    }
    screen_list = [
        "PinturaV2test00001",
        "PinturaTest173459",
        "PinturaV2test09529",
        "PSd4117cL000289",
        "PinturaTest174280"
    ]
    
    # 初始化上一次选择的模式
    last_mode = None
    start_time = time.time()
    switch_times = 0
    try:
        while True:
            # 获取所有可用的显示模式索引
            available_modes = list(display_mode.keys())
            
            # 如果上一次有选择过模式，则从可选列表中移除
            if last_mode is not None and last_mode in available_modes:
                available_modes.remove(last_mode)
            
            # 随机选择一个显示模式
            selected_mode = random.choice(available_modes)
            selected_mode_name = display_mode[selected_mode]
            
            print(f"随机切换到{selected_mode_name}模式")
            
            # 对所有屏幕执行切换
            for screen_id in screen_list:
                switch_display_mode = SwitchDisplayMode(account="test2@tester.com", password="sf123123", host="139.224.192.36", port="8082")
                switch_display_mode.switch_display_mode(display_mode=selected_mode, screen_id=screen_id)
                time.sleep(2)
            
            # 更新上一次选择的模式
            last_mode = selected_mode
            switch_times += 1
            
            # 可选：在切换下一个模式前等待一段时间
            print("等待5秒后进行下一次随机切换...")
            time.sleep(5)
    except KeyboardInterrupt:
        time_stamp = time.time() - start_time
        result = format_time_duration(int(time_stamp), max_unit="D", min_unit="S")
        logger.info(f"程序运行时间: {result}")
        logger.info(f"切换次数: {switch_times}")
        sys.exit(0)