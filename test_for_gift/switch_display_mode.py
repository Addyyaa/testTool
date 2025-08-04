# pylint: disable=invalid-name,wrong-import-position
import sys
import time
import random
import logging
from pathlib import Path
from typing import Literal
import asyncio

from typing import TypedDict, List
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入模块
from detect_tool_for_202.media_transfer_to_screen import GetScreenIp
from api_sender import Api_sender 
from date_tool import format_time_duration
from telnet_connecter import Telnet_connector


logger = logging.getLogger(__name__)

class SwitchDisplayMode:
    """切换显示模式"""
    def __init__(self, api_sender: Api_sender):
        self.api_sender = api_sender
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

class RotateDispalyOrientation:
    """
    旋转屏幕显示方向
    """
    def __init__(self, api_sender: Api_sender):
        self.api_sender = api_sender
    def rotate_dispaly_orientation(self, screen_id: str, orientation: Literal[1, 2]):
        """
        @param screen_id: 屏幕ID
        @param orientation: 显示方向 1: 竖屏 2: 横屏
        """
        direction = {
            1: "竖屏",
            2: "横屏"
        }
        data = {
            "screenId": screen_id,
            "direction": orientation
        }
        response = self.api_sender.send_api(self.api_sender.rotate_display_orientation, data=data, method="post")
        if response is not None:
            try:
                resp_json = response.json()
                if resp_json.get("code") == 20:
                    logger.info("%s 屏幕已旋转为%s", screen_id, direction[orientation])
            except Exception as e:
                logger.error("解析响应失败: %s\t%s", e, getattr(response, 'text', ''))

class ScreenConfig(TypedDict):
    """
    屏幕配置
    @param tn: Telnet连接器
    @param "cmd_list": [
                    "mymqtt",
                    "pintura",
                    "video_player"
                ]
    """
    tn: Telnet_connector
    cmd_list: List[str]

class ApplicationRestartObserver:
    """
    应用重启观察者
    """
    def __init__(self):
        self.pid_map = {}
    
    async def application_restart_observer(self, screen_config1: dict[str, ScreenConfig]):
        """
        检查应用是否重启
        
        @param screen_config: 屏幕配置字典
        {
            "screen_id": ScreenConfig
        }
        """
        for screen_id, config in screen_config1.items():
            config["cmd_list"] = [f"pidof {app}" for app in config["cmd_list"]]

        if not self.pid_map:
            for screen_id, config in screen_config1.items():
                for cmd in config["cmd_list"]:
                    pid = await config["tn"].send_command(cmd)  # 使用 await
                    logger.info("pid: %s", pid)
                    if pid:
                        self.pid_map[screen_id] = {
                            cmd: pid
                        }
                    else:
                        self.pid_map[screen_id] = None
        else:
            for screen_id, config in screen_config1.items():
                for cmd in config["cmd_list"]:
                    pid = await config["tn"].send_command(cmd)  # 使用 await
                    logger.info("pid: %s", pid)
                    if pid and pid == self.pid_map[screen_id][cmd]:
                        logger.info("应用 %s 未重启", cmd)
                        continue
                    else:
                        logger.error("%s-%s应用重启", screen_id, cmd)
                        self.pid_map[screen_id] = {
                            cmd: pid
                        }
                        
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d ===> %(message)s')
    api_client = Api_sender(
        user="test2@tester.com",
        passwd="sf123123",
        host="139.224.192.36",
        port="8082")
    switch_display_mode = SwitchDisplayMode(api_client)
    rotate_dispaly_orientation = RotateDispalyOrientation(api_client)

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
        # "PinturaV2test00001",
        # "PinturaTest173459",
        "PinturaV2test09529",
        "PSd4117cL000289",
        "PinturaTest174280"
    ]

    # 初始化屏幕配置
    # 获取屏幕IP
    screen_ip_map = { screen_id: GetScreenIp().get_screen_ip(screen_id) for screen_id in screen_list }
    screen_config = { screen_id: ScreenConfig(tn=Telnet_connector(host=screen_ip_map[screen_id]), cmd_list=["mymqtt", "pintura", "video_player"]) for screen_id in screen_list }
    print(screen_config)
    application_restart_observer = ApplicationRestartObserver()
    
    # 初始化上一次选择的模式
    last_mode = None
    start_time = time.time()
    switch_times = 0
    try:
        while True:
            # 检查应用是否重启
            asyncio.run(application_restart_observer.application_restart_observer(screen_config))
            print(f"======>{screen_config}")

            # 获取所有可用的显示模式索引
            available_modes = list(display_mode.keys())
            
            # 如果上一次有选择过模式，则从可选列表中移除
            if last_mode is not None and last_mode in available_modes:
                available_modes.remove(last_mode)

            # 随机旋转屏幕
            if random.random() < 0.5:
                rotate_dispaly_orientation.rotate_dispaly_orientation(screen_id=random.choice(screen_list), orientation=random.choice([1, 2]))
            
            # 随机选择一个显示模式
            selected_mode = random.choice(available_modes)
            selected_mode_name = display_mode[selected_mode]

            print(f"随机切换到{selected_mode_name}模式")
            
            # 对所有屏幕执行切换
            for screen_id in screen_list:
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
        logger.info("程序运行时间: %s", result)
        logger.info("切换次数: %s", switch_times)
        sys.exit(0)