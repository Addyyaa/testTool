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
        url = f"http://192.168.1.1:8080/pintura/config/changeDisplayMode"
        data = {
            "screenId": screen_id,
            "displayMode": display_mode
        }
        result = self.api_sender.post(url, data=data)
        
        if result and result.get("code") == 200:
            logger.info("%s switch_display_mode success", screen_id)
        else:
            logger.error("%s switch_display_mode failed: %s", screen_id, result)

class RotateDispalyOrientation:
    def __init__(self):
        self.api_sender = Api_sender()

    def rotate_dispaly_orientation(self, orientation: Literal[1, 2], screen_id: str):
        """
        旋转屏幕方向
        @param orientation: 屏幕方向 1: 横屏, 2: 竖屏
        @param screen_id: 屏幕ID
        """
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
        else:
            logger.error("%s 旋转屏幕方向失败: %s", screen_id, result)

class ApplicationRestartObserver:
    """
    应用重启监控器 - 优化版本
    """
    def __init__(self):
        self.pid_map = {}

    async def application_restart_observer(self, screen_config1: dict[str, ScreenConfig]):
        """
        检查应用是否重启 - 优化版本
        """
        # 只在第一次时添加pidof前缀，避免重复累积
        for screen_id, config in screen_config1.items():
            if config["cmd_list"] and not config["cmd_list"][0].startswith("pidof"):
                config["cmd_list"] = [f"pidof {app}" for app in config["cmd_list"]]

        async def optimized_send_command(tn, cmd, screen_id, max_retries=2):
            """优化的命令发送函数"""
            for retry in range(max_retries):
                try:
                    # 使用优化的连接确保方法
                    reconnected = await tn.ensure_connection()
                    if reconnected:
                        logger.info(f"{screen_id} 连接已重建")
                    
                    # 发送命令
                    result = await tn.send_command(cmd)
                    return result
                    
                except ConnectionError as e:
                    logger.warning(f"{screen_id} 连接错误 (尝试 {retry+1}/{max_retries}): {e}")
                    
                    if retry < max_retries - 1:
                        logger.info(f"{screen_id} 尝试强制重连...")
                        try:
                            # 强制重连
                            await tn.disconnect()
                            await asyncio.sleep(0.5)
                            await tn.connect_and_warmup()
                            
                        except Exception as reconnect_error:
                            logger.error(f"{screen_id} 重连失败: {reconnect_error}")
                            await asyncio.sleep(1)
                    else:
                        logger.error(f"{screen_id} 命令发送最终失败: {e}")
                        return None
                        
                except Exception as e:
                    logger.error(f"{screen_id} 发送命令时发生错误: {e}")
                    return None
            return None

        if not self.pid_map:
            logger.info("初始化PID映射...")
            for screen_id, config in screen_config1.items():
                self.pid_map[screen_id] = {}
                for cmd in config["cmd_list"]:
                    pid = await optimized_send_command(config["tn"], cmd, screen_id)
                    logger.info(f"{screen_id} - {cmd}: {pid}")
                    if pid:
                        self.pid_map[screen_id][cmd] = pid.strip()
                    else:
                        self.pid_map[screen_id][cmd] = None
        else:
            logger.info("检查PID变化...")
            for screen_id, config in screen_config1.items():
                for cmd in config["cmd_list"]:
                    pid = await optimized_send_command(config["tn"], cmd, screen_id)
                    if pid:
                        pid = pid.strip()
                        
                    if pid and self.pid_map.get(screen_id) and pid == self.pid_map[screen_id].get(cmd):
                        logger.info(f"{screen_id} - {cmd}: 未重启")
                        continue
                    else:
                        logger.error(f"{screen_id} - {cmd}: 应用重启 (旧PID: {self.pid_map.get(screen_id, {}).get(cmd)}, 新PID: {pid})")
                        if screen_id not in self.pid_map:
                            self.pid_map[screen_id] = {}
                        self.pid_map[screen_id][cmd] = pid

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
    print("🚀 初始化优化的屏幕配置...")
    screen_ip_map = { screen_id: GetScreenIp().get_screen_ip(screen_id) for screen_id in screen_list }
    screen_config = { screen_id: ScreenConfig(tn=Telnet_connector(host=screen_ip_map[screen_id]), cmd_list=["mymqtt", "pintura", "video_player"]) for screen_id in screen_list }
    
    # 预热所有连接
    async def warmup_all_connections():
        """预热所有连接"""
        print("🔥 预热所有连接...")
        tasks = []
        for screen_id, config in screen_config.items():
            tasks.append(config["tn"].connect_and_warmup())
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = 0
        for i, result in enumerate(results):
            screen_id = screen_list[i]
            if isinstance(result, Exception):
                print(f"❌ {screen_id} 预热失败: {result}")
            else:
                print(f"✅ {screen_id} 预热成功")
                success_count += 1
        
        print(f"📊 预热完成: {success_count}/{len(screen_list)} 设备成功")
        return success_count > 0
    
    print(screen_config)
    application_restart_observer = ApplicationRestartObserver()
    
    # 初始化上一次选择的模式
    last_mode = None
    start_time = time.time()
    switch_times = 0
    
    try:
        # 预热连接
        if not asyncio.run(warmup_all_connections()):
            print("❌ 所有设备预热失败，程序退出")
            sys.exit(1)
        
        print("\n🎮 开始优化的显示模式切换循环...")
        
        while True:
            loop_start_time = time.time()
            print(f"\n{'='*60}")
            print(f"🔄 第 {switch_times + 1} 轮切换 (运行时间: {time.time() - start_time:.1f}s)")
            print('='*60)
            
            # 检查应用是否重启
            print("🔍 检查应用重启状态...")
            check_start_time = time.time()
            asyncio.run(application_restart_observer.application_restart_observer(screen_config))
            check_duration = time.time() - check_start_time
            print(f"✅ 应用检查完成，耗时: {check_duration:.2f}s")

            # 获取所有可用的显示模式索引
            available_modes = list(display_mode.keys())
            
            # 如果上一次有选择过模式，则从可选列表中移除
            if last_mode is not None and last_mode in available_modes:
                available_modes.remove(last_mode)

            # 随机旋转屏幕
            if random.random() < 0.3:  # 降低旋转频率
                selected_screen = random.choice(screen_list)
                selected_orientation = random.choice([1, 2])
                print(f"🔄 随机旋转 {selected_screen} 屏幕方向: {selected_orientation}")
                rotate_dispaly_orientation.rotate_dispaly_orientation(screen_id=selected_screen, orientation=selected_orientation)
            
            # 随机选择一个显示模式
            selected_mode = random.choice(available_modes)
            selected_mode_name = display_mode[selected_mode]

            print(f"🎯 切换到: {selected_mode_name} (模式 {selected_mode})")
            
            # 对所有屏幕执行切换
            switch_start_time = time.time()
            for screen_id in screen_list:
                switch_display_mode.switch_display_mode(display_mode=selected_mode, screen_id=screen_id)
                time.sleep(1)  # 减少等待时间从2秒到1秒
            
            switch_duration = time.time() - switch_start_time
            print(f"✅ 显示模式切换完成，耗时: {switch_duration:.2f}s")
            
            # 更新上一次选择的模式
            last_mode = selected_mode
            switch_times += 1
            
            # 计算本轮总耗时
            loop_duration = time.time() - loop_start_time
            print(f"📊 本轮总耗时: {loop_duration:.2f}s (检查: {check_duration:.2f}s + 切换: {switch_duration:.2f}s)")
            
            # 可选：在切换下一个模式前等待一段时间
            wait_time = 3  # 减少等待时间从5秒到3秒
            print(f"⏳ 等待 {wait_time} 秒后进行下一次切换...")
            time.sleep(wait_time)
            
    except KeyboardInterrupt:
        print("\n⏹️ 程序被用户中断")
        
        # 运行时统计
        time_stamp = time.time() - start_time
        result = format_time_duration(int(time_stamp), max_unit="D", min_unit="S")
        
        print(f"\n📊 运行统计:")
        print(f"  运行时间: {result}")
        print(f"  切换次数: {switch_times}")
        print(f"  平均切换间隔: {time_stamp/switch_times:.1f}s" if switch_times > 0 else "")
        
        # 断开所有连接
        print("\n🔌 正在断开所有连接...")
        async def cleanup_connections():
            tasks = []
            for screen_id, config in screen_config.items():
                tasks.append(config["tn"].disconnect())
            await asyncio.gather(*tasks, return_exceptions=True)
            print("✅ 所有连接已断开")
        
        asyncio.run(cleanup_connections())
        sys.exit(0)