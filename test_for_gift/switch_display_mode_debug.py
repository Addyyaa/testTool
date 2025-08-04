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

# 导入调试工具
from debug_connection_monitor import connection_monitor, log_timing, analyze_timing

logger = logging.getLogger(__name__)

class ScreenConfig(TypedDict):
    tn: Telnet_connector
    cmd_list: List[str]

class SwitchDisplayMode:
    def __init__(self):
        self.api_sender = Api_sender()

    def switch_display_mode(self, display_mode: Literal[1, 2, 3, 4, 5, 6, 7, 8], screen_id: str):
        """
        切换显示模式
        @param display_mode: 显示模式
        @param screen_id: 屏幕ID
        """
        log_timing(f"开始切换显示模式 {display_mode}", screen_id)
        
        url = f"http://192.168.1.1:8080/pintura/config/changeDisplayMode"
        data = {
            "screenId": screen_id,
            "displayMode": display_mode
        }
        result = self.api_sender.post(url, data=data)
        
        if result and result.get("code") == 200:
            logger.info("%s switch_display_mode success", screen_id)
            log_timing(f"切换显示模式 {display_mode} 成功", screen_id)
        else:
            logger.error("%s switch_display_mode failed: %s", screen_id, result)
            log_timing(f"切换显示模式 {display_mode} 失败", screen_id)

class RotateDispalyOrientation:
    def __init__(self):
        self.api_sender = Api_sender()

    def rotate_dispaly_orientation(self, orientation: Literal[1, 2], screen_id: str):
        """
        旋转屏幕方向
        @param orientation: 屏幕方向 1: 横屏, 2: 竖屏
        @param screen_id: 屏幕ID
        """
        log_timing(f"开始旋转屏幕方向 {orientation}", screen_id)
        
        url = f"http://192.168.1.1:8080/pintura/config/rotateDispalyOrientation"
        data = {
            "screenId": screen_id,
            "orientation": orientation
        }
        result = self.api_sender.post(url, data=data)
        
        if result and result.get("code") == 200:
            if orientation == 2:
                logger.info("%s 屏幕已旋转为竖屏", screen_id)
            else:
                logger.info("%s 屏幕已旋转为横屏", screen_id)
            log_timing(f"旋转屏幕方向 {orientation} 成功", screen_id)
        else:
            logger.error("%s 旋转屏幕方向失败: %s", screen_id, result)
            log_timing(f"旋转屏幕方向 {orientation} 失败", screen_id)

class ApplicationRestartObserver:
    """
    应用重启监控器
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
        log_timing("开始应用重启检查", "ALL")
        
        # 只在第一次时添加pidof前缀，避免重复累积
        for screen_id, config in screen_config1.items():
            if config["cmd_list"] and not config["cmd_list"][0].startswith("pidof"):
                config["cmd_list"] = [f"pidof {app}" for app in config["cmd_list"]]
                log_timing(f"初始化命令列表: {config['cmd_list']}", screen_id)

        async def safe_send_command(tn, cmd, screen_id, max_retries=3):
            """安全发送命令，包含重连机制"""
            log_timing(f"准备发送命令: {cmd}", screen_id)
            
            # 记录发送前的连接状态
            connection_monitor.record_connection_state(screen_id, tn, cmd)
            
            for retry in range(max_retries):
                try:
                    log_timing(f"发送命令尝试 {retry+1}/{max_retries}: {cmd}", screen_id)
                    result = await tn.send_command(cmd)
                    
                    # 记录成功状态
                    connection_monitor.record_connection_state(screen_id, tn, cmd)
                    log_timing(f"命令执行成功: {cmd}", screen_id)
                    return result
                    
                except ConnectionError as e:
                    logger.warning(f"连接错误 (尝试 {retry+1}/{max_retries}): {e}")
                    log_timing(f"连接错误 {retry+1}/{max_retries}: {str(e)}", screen_id)
                    
                    # 记录错误状态
                    connection_monitor.record_connection_state(screen_id, tn, cmd, str(e))
                    
                    if retry < max_retries - 1:
                        logger.info(f"尝试重新连接到 {screen_id}...")
                        log_timing(f"开始重连", screen_id)
                        
                        try:
                            # 强制断开并重新连接
                            await tn.disconnect()
                            log_timing(f"断开连接完成", screen_id)
                            await asyncio.sleep(0.5)  # 等待清理
                            
                            await tn.connect()
                            log_timing(f"重新连接完成", screen_id)
                            await asyncio.sleep(1)  # 等待连接稳定
                            
                            # 记录重连后状态
                            connection_monitor.record_connection_state(screen_id, tn, f"reconnect_after_{cmd}")
                            
                        except Exception as reconnect_error:
                            logger.error(f"重连失败: {reconnect_error}")
                            log_timing(f"重连失败: {str(reconnect_error)}", screen_id)
                            await asyncio.sleep(2)  # 等待更长时间再重试
                    else:
                        logger.error(f"命令发送失败，已达最大重试次数: {e}")
                        log_timing(f"命令最终失败: {str(e)}", screen_id)
                        return None
                        
                except Exception as e:
                    logger.error(f"发送命令时发生未知错误: {e}")
                    log_timing(f"未知错误: {str(e)}", screen_id)
                    connection_monitor.record_connection_state(screen_id, tn, cmd, f"Unknown: {str(e)}")
                    return None
            return None

        if not self.pid_map:
            log_timing("初始化PID映射", "ALL")
            for screen_id, config in screen_config1.items():
                for cmd in config["cmd_list"]:
                    pid = await safe_send_command(config["tn"], cmd, screen_id)
                    logger.info("pid: %s", pid)
                    if pid:
                        self.pid_map[screen_id] = {
                            cmd: pid
                        }
                    else:
                        self.pid_map[screen_id] = None
        else:
            log_timing("检查PID变化", "ALL")
            for screen_id, config in screen_config1.items():
                for cmd in config["cmd_list"]:
                    pid = await safe_send_command(config["tn"], cmd, screen_id)
                    logger.info("pid: %s", pid)
                    if pid and self.pid_map.get(screen_id) and pid == self.pid_map[screen_id].get(cmd):
                        logger.info("应用 %s 未重启", cmd)
                        log_timing(f"应用未重启: {cmd}", screen_id)
                        continue
                    else:
                        logger.error("%s-%s应用重启", screen_id, cmd)
                        log_timing(f"检测到应用重启: {cmd}", screen_id)
                        if screen_id not in self.pid_map:
                            self.pid_map[screen_id] = {}
                        self.pid_map[screen_id][cmd] = pid
        
        log_timing("应用重启检查完成", "ALL")

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d ===> %(message)s')
    
    # 显示模式映射
    display_mode = {
        1: "纯图片播放",
        2: "纯视频播放", 
        3: "混播随机播放",
        4: "混播顺序播放",
        5: "从其他显示模式回到视频",
        6: "重启他界面返回",
        7: "重启礼物界面",
        8: "重启主界面"
    }

    switch_display_mode = SwitchDisplayMode()
    rotate_dispaly_orientation = RotateDispalyOrientation()

    # 屏幕列表
    screen_list = [
        "PinturaV2test09529",
        "PSd4117cL000289", 
        "PinturaTest174280"
    ]

    # 初始化屏幕配置
    log_timing("开始初始化屏幕配置", "ALL")
    screen_ip_map = { screen_id: GetScreenIp().get_screen_ip(screen_id) for screen_id in screen_list }
    screen_config = { screen_id: ScreenConfig(tn=Telnet_connector(host=screen_ip_map[screen_id]), cmd_list=["mymqtt", "pintura", "video_player"]) for screen_id in screen_list }
    print(screen_config)
    application_restart_observer = ApplicationRestartObserver()
    log_timing("屏幕配置初始化完成", "ALL")
    
    # 初始化上一次选择的模式
    last_mode = None
    start_time = time.time()
    switch_times = 0
    
    try:
        while True:
            log_timing("=== 开始新的循环 ===", "ALL")
            
            # 检查应用是否重启
            log_timing("开始执行应用重启检查", "ALL")
            asyncio.run(application_restart_observer.application_restart_observer(screen_config))
            log_timing("应用重启检查完成", "ALL")
            
            print(f"======>{screen_config}")

            # 获取所有可用的显示模式索引
            available_modes = list(display_mode.keys())
            
            # 如果上一次有选择过模式，则从可选列表中移除
            if last_mode is not None and last_mode in available_modes:
                available_modes.remove(last_mode)

            # 随机旋转屏幕
            if random.random() < 0.5:
                selected_screen = random.choice(screen_list)
                selected_orientation = random.choice([1, 2])
                log_timing(f"随机旋转屏幕: {selected_orientation}", selected_screen)
                rotate_dispaly_orientation.rotate_dispaly_orientation(screen_id=selected_screen, orientation=selected_orientation)
            
            # 随机选择一个显示模式
            selected_mode = random.choice(available_modes)
            selected_mode_name = display_mode[selected_mode]

            print(f"随机切换到{selected_mode_name}模式")
            log_timing(f"开始切换到模式: {selected_mode_name}", "ALL")
            
            # 对所有屏幕执行切换
            for screen_id in screen_list:
                log_timing(f"切换屏幕显示模式", screen_id)
                switch_display_mode.switch_display_mode(display_mode=selected_mode, screen_id=screen_id)
                time.sleep(2)
                log_timing(f"屏幕切换完成，等待2秒", screen_id)
            
            # 更新上一次选择的模式
            last_mode = selected_mode
            switch_times += 1
            
            log_timing("显示模式切换完成", "ALL")
            
            # 打印连接状态分析
            print("\n" + "="*50)
            print("连接状态分析:")
            connection_monitor.print_analysis()
            print("="*50 + "\n")
            
            # 可选：在切换下一个模式前等待一段时间
            print("等待5秒后进行下一次随机切换...")
            log_timing("开始等待5秒", "ALL")
            time.sleep(5)
            log_timing("等待结束", "ALL")
            
    except KeyboardInterrupt:
        log_timing("程序被用户中断", "ALL")
        
        # 打印最终分析报告
        print("\n" + "="*80)
        print("最终分析报告:")
        print("="*80)
        
        # 时序分析
        analyze_timing()
        
        # 连接状态分析
        connection_monitor.print_analysis()
        
        # 运行时统计
        time_stamp = time.time() - start_time
        result = format_time_duration(int(time_stamp), max_unit="D", min_unit="S")
        logger.info("程序运行时间: %s", result)
        logger.info("切换次数: %s", switch_times)
        
        sys.exit(0)