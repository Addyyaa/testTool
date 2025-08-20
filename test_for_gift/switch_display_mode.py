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
        self.display_mode_map = {
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

        data = {"displayMode": display_mode, "screenId": screen_id}
        result = self.api_sender.send_api(
            self.api_sender.display, data=data, method="post"
        )
        if result is not None:
            try:
                resp_json = result.json()
                if resp_json.get("code") == 20:
                    logger.info(
                        f"{screen_id} switch_display_mode {self.display_mode_map[display_mode]} success"
                    )
                else:
                    logger.error(
                        f"switch_display_mode failed\t{result.text}\nbody:{data}"
                    )
            except Exception as e:
                logger.error(f"解析响应失败: {e}\t{getattr(result, 'text', '')}")
        else:
            logger.error(f"switch_display_mode failed, no response")

    async def switch_display_mode_async(self, display_mode: str, screen_id: str):
        """异步切换显示模式（在线程池中执行同步HTTP请求）"""
        data = {"displayMode": display_mode, "screenId": screen_id}
        result = await asyncio.to_thread(
            self.api_sender.send_api, self.api_sender.display, data, "post"
        )
        if result is not None:
            try:
                resp_json = result.json()
                if resp_json.get("code") == 20:
                    logger.info(
                        f"{screen_id} switch_display_mode {self.display_mode_map[display_mode]} success"
                    )
                else:
                    logger.error(
                        f"switch_display_mode failed\t{result.text}\nbody:{data}"
                    )
            except Exception as e:
                logger.error(f"解析响应失败: {e}\t{getattr(result, 'text', '')}")
        else:
            logger.error("switch_display_mode failed, no response")

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
        direction = {1: "竖屏", 2: "横屏"}
        data = {"screenId": screen_id, "direction": orientation}
        response = self.api_sender.send_api(
            self.api_sender.rotate_display_orientation, data=data, method="post"
        )
        if response is not None:
            try:
                resp_json = response.json()
                if resp_json.get("code") == 20:
                    logger.info("%s 屏幕已旋转为%s", screen_id, direction[orientation])
            except Exception as e:
                logger.error("解析响应失败: %s\t%s", e, getattr(response, "text", ""))

    async def rotate_dispaly_orientation_async(
        self, screen_id: str, orientation: Literal[1, 2]
    ):
        """异步旋转屏幕（在线程池中执行同步HTTP请求）"""
        direction = {1: "竖屏", 2: "横屏"}
        data = {"screenId": screen_id, "direction": orientation}
        response = await asyncio.to_thread(
            self.api_sender.send_api,
            self.api_sender.rotate_display_orientation,
            data,
            "post",
        )
        if response is not None:
            try:
                resp_json = response.json()
                if resp_json.get("code") == 20:
                    logger.info("%s 屏幕已旋转为%s", screen_id, direction[orientation])
            except Exception as e:
                logger.error("解析响应失败: %s\t%s", e, getattr(response, "text", ""))


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

    async def application_restart_observer(
        self, screen_config1: dict[str, ScreenConfig]
    ):
        """
        检查应用是否重启

        @param screen_config: 屏幕配置字典
        {
            "screen_id": ScreenConfig
        }
        """
        for screen_id, config in screen_config1.items():
            if config["cmd_list"] and not config["cmd_list"][0].startswith("pidof"):
                config["cmd_list"] = [f"pidof {app}" for app in config["cmd_list"]]

        async def safe_send_command(tn, cmd, screen_id, max_retries=3):
            """安全发送命令，包含重连机制"""
            for retry in range(max_retries):
                try:
                    return await tn.send_command(cmd)
                except ConnectionError as e:
                    logger.warning(f"连接错误 (尝试 {retry+1}/{max_retries}): {e}")
                    if retry < max_retries - 1:
                        logger.info(f"尝试重新连接到 {screen_id}...")
                        try:
                            # 强制断开并重新连接
                            await tn.disconnect()  # 先断开
                            await asyncio.sleep(0.5)  # 等待清理
                            await tn.connect()  # 重新连接
                            await asyncio.sleep(1)  # 等待连接稳定
                        except Exception as reconnect_error:
                            logger.error(f"重连失败: {reconnect_error}")
                            await asyncio.sleep(2)  # 等待更长时间再重试
                    else:
                        logger.error(f"命令发送失败，已达最大重试次数: {e}")
                        return None
                except Exception as e:
                    logger.error(f"发送命令时发生未知错误: {e}")
                    return None
            return None

        # 并发获取所有屏幕/命令的 PID，提升速度
        tasks = []
        key_pairs = []  # 保存 (screen_id, cmd) 顺序以便回填
        for screen_id, config in screen_config1.items():
            for cmd in config["cmd_list"]:
                tasks.append(safe_send_command(config["tn"], cmd, screen_id))
                key_pairs.append((screen_id, cmd))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 组装新一轮 PID 映射
        new_pid_map: dict[str, dict[str, str | None]] = {}
        for (screen_id, cmd), pid in zip(key_pairs, results):
            if isinstance(pid, Exception):
                pid_value = None
            else:
                pid_value = pid.strip() if pid else None
            if screen_id not in new_pid_map:
                new_pid_map[screen_id] = {}
            new_pid_map[screen_id][cmd] = pid_value

        # 首次初始化
        if not self.pid_map:
            logger.info("初始化PID映射...")
            self.pid_map = new_pid_map
            for screen_id, cmd_map in new_pid_map.items():
                for cmd, pid in cmd_map.items():
                    logger.info("pid: %s", pid)
            return

        # 比较新旧，输出变化/未变化日志并更新缓存
        for screen_id, cmd_map in new_pid_map.items():
            for cmd, pid in cmd_map.items():
                logger.info("pid: %s", pid)
                old_pid = self.pid_map.get(screen_id, {}).get(cmd)
                if pid and old_pid and pid == old_pid:
                    logger.info("应用 %s 未重启", cmd)
                else:
                    logger.error(
                        "%s-%s应用重启\t重启前pid: %s\t重启后pid: %s",
                        screen_id,
                        cmd,
                        old_pid,
                        pid,
                    )
                if screen_id not in self.pid_map:
                    self.pid_map[screen_id] = {}
                self.pid_map[screen_id][cmd] = pid


if __name__ == "__main__":

    import os

    # 确保日志目录存在
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)

    # 使用绝对路径创建日志文件
    log_file = os.path.join(log_dir, "switch_display_mode.log")
    try:
        # 创建日志处理器
        file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
        console_handler = logging.StreamHandler(sys.stdout)

        # 设置日志格式
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d ===> %(message)s"
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # 配置根日志记录器
        logging.basicConfig(
            level=logging.INFO,
            handlers=[file_handler, console_handler],
            force=True,  # 强制重新配置
        )

        print(f"日志文件路径: {log_file}")

    except Exception as e:
        print(f"日志配置失败: {e}")
        # 使用简单的控制台日志作为备选
        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
        )

    api_client = Api_sender(
        user="test2@tester.com", passwd="sf123123", host="139.224.192.36", port="8082"
    )
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
        "PinturaV2test00001",
        # "PinturaTest173459",
        "PinturaV2test09529",
        "PSd4117cL000289",
        "PinturaTest174280",
    ]

    # 初始化屏幕配置
    # 获取屏幕IP
    screen_ip_map = {
        screen_id: GetScreenIp().get_screen_ip(screen_id) for screen_id in screen_list
    }
    screen_config = {
        screen_id: ScreenConfig(
            tn=Telnet_connector(host=screen_ip_map[screen_id]),
            cmd_list=["mymqtt", "pintura", "video_player"],
        )
        for screen_id in screen_list
    }
    print(screen_config)
    application_restart_observer = ApplicationRestartObserver()

    # 运行状态（闭包外）
    state = {
        "last_mode": None,
        "start_time": time.time(),
        "switch_times": 0,
    }
    try:

        async def warmup_all_tn():
            # 并发预热所有 tn 连接，确保后续命令稳定
            await asyncio.gather(
                *[
                    config["tn"].connect_and_warmup()
                    for config in screen_config.values()
                ]
            )

        async def main_loop():
            while True:
                # 确保连接健康（如断线则重连）
                await asyncio.gather(
                    *[
                        config["tn"].ensure_connection()
                        for config in screen_config.values()
                    ]
                )
                # 检查应用是否重启（保持在同一事件循环中）
                await application_restart_observer.application_restart_observer(
                    screen_config
                )
                print(f"======>{screen_config}")

                # 获取所有可用的显示模式索引
                available_modes = list(display_mode.keys())

                # 如果上一次有选择过模式，则从可选列表中移除
                if (
                    state["last_mode"] is not None
                    and state["last_mode"] in available_modes
                ):
                    available_modes.remove(state["last_mode"])

                # 随机旋转屏幕
                if random.random() < 0.5:
                    rid = random.choice(screen_list)
                    await rotate_dispaly_orientation.rotate_dispaly_orientation_async(
                        screen_id=rid,
                        orientation=random.choice([1, 2]),
                    )

                # 随机选择一个显示模式
                selected_mode = random.choice(available_modes)
                selected_mode_name = display_mode[selected_mode]

                print(f"随机切换到{selected_mode_name}模式")

                # 并发对所有屏幕执行切换
                await asyncio.gather(
                    *[
                        switch_display_mode.switch_display_mode_async(
                            display_mode=selected_mode, screen_id=screen_id
                        )
                        for screen_id in screen_list
                    ]
                )

                # 更新上一次选择的模式
                state["last_mode"] = selected_mode
                state["switch_times"] += 1

                # 可选：在切换下一个模式前等待一段时间
                print("等待5秒后进行下一次随机切换...")
                await asyncio.sleep(5)

        async def orchestrator():
            await warmup_all_tn()
            await main_loop()

        asyncio.run(orchestrator())
    except KeyboardInterrupt:
        time_stamp = time.time() - state["start_time"]
        result = format_time_duration(int(time_stamp), max_unit="D", min_unit="S")
        logger.info("程序运行时间: %s", result)
        logger.info("切换次数: %s", state["switch_times"])
        sys.exit(0)
