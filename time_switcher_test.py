import logging
import sys
from datetime import datetime, timedelta
import asyncio
from telnet_connecter import Telnet_connector
from api_sender import Api_sender
import re

host = ['192.168.1.10']
config = {
    "user": "root",
    "password": "ya!2dkwy7-934^",
    "on_time": "09:35",  # 24小时制
    "off_time": "18:30",
}


class Time_switcher_tester:

    def __init__(self, host1: str, api_sender1: Api_sender, selected_id2: str, selected_name3: str):
        # 声明一个变量用来存储tn实例
        self.host = host1
        # 初始化api发送器
        self.api_sender = api_sender1
        self.tn: Telnet_connector | None = None  # Ensure tn starts as None and has type hint
        self.selected_id = selected_id2
        self.selected_name = selected_name3
        # DO NOT run async io here

    async def check_local_screen_status(self) -> str:
        # --- Restore the lazy initialization check --- 
        if self.tn is None:
            print(f"[{self.host}] Telnet connection not initialized. Initializing...")
            await self.tn_initialize()
            # Add a check after initialization in case tn_initialize failed silently
            if self.tn is None:
                raise ConnectionError(f"[{self.host}] Failed to initialize Telnet connection within tn_initialize.")
        # -------------------------------------------

        # 登陆telnet
        # Now self.tn should be a valid connector object
        await self.tn.send_command(config["user"])
        await self.tn.send_command(config["password"])
        while True:
            response: str = await self.tn.send_command('cat /tmp/screen_on_off', read_timeout=2)
            if len(response) <= 0:
                continue
            else:
                break
        lines = response.split('\n')[1:-2]
        screen_status = '\n'.join(lines).strip().replace(' ', '')
        if len(lines) <= 0:
            pattern = r'\b(on|off)\b'
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                screen_status = match.group()
        return screen_status

    async def tn_initialize(self):
        self.tn = Telnet_connector(self.host)
        await self.tn.connect()

    async def set_screen_on_off(self, group_id: str, on_off: str):
        body = {
            "screenGroupId": group_id,
            "switchType": 1 if on_off.upper() == 'ON' else 2
        }
        try:
            response = self.api_sender.send_api(self.api_sender.screen_switch, data=body, method="post")
        except Exception as e:
            logging.error(f"背光请求发生错误：{e}")
            return False
        if response.status_code == 200 and response.json()["code"] == 20:
            logging.info(f"已下发背光开关指令：{on_off}")
            return True
        else:
            return False

    async def set_timer_screen_on_off(self, on_off: str, group_id: str):
        on_time = config["on_time"]
        off_time = config["off_time"]
        on_hour = datetime.strptime(on_time, "%H:%M").hour
        on_min = datetime.strptime(on_time, "%H:%M").minute
        off_hour = datetime.strptime(off_time, "%H:%M").hour
        off_min = datetime.strptime(off_time, "%H:%M").minute
        on = on_hour << 8 | on_min
        off = off_hour << 8 | off_min
        if on and off:
            body = {
                "screenGroupId": group_id,
                "screenIds": [],
                "startHour": on,
                "endHour": off,
                "switchType": 1 if on_off.upper() == 'ON' else 2
            }
            try:
                response = self.api_sender.send_api(self.api_sender.screen_timer_machine, data=body, method="post")
                if response.status_code == 200 and response.json()["code"] == 20:
                    # Clarified log based on seems switchType usage
                    log_action = "关机" if on_off.upper() == 'OFF' else "开机"
                    logging.info(f"定时{log_action}已重新设置为：开：{config['on_time']}-关：{config['off_time']}")
                    return True
                else:
                    # Log API failure details
                    logging.error(f"设置定时开关 API 请求失败。状态码: {response.status_code}, 响应: {response.text}")
                    return False
            except Exception as e:
                logging.error(f"定时开关请求发生错误：{e}")
                return False
        else:
            # This 'else' might be unreachable if strptime fails first
            logging.error(
                f"计算出的 on/off 值无效 (on={on}, off={off}) 或时间格式错误 (on_time={on_time}, off_time={off_time})")
            # Consider not exiting the whole script here, maybe return False
            # sys.exit() 
            return False  # Return False instead of exiting

    @staticmethod
    def get_groupId_name(api_sender1: Api_sender):
        group_list = []
        group_option = []
        response = api_sender1.send_api(api_sender1.get_device, data="", method="get")
        if response.status_code == 200 and response.json()["code"] == 20:
            group = response.json()["data"]["group"]
            for i in group:
                group_list.append(i["id"])
                group_option.append(i["name"])
            return group_list, group_option
        else:
            input(f"该账号下没有设备，按回车键退出程序")
            sys.exit()

    @staticmethod
    def display_group_menu(id2: list, name1: list):
        # 使用 await 调用方法
        length = len(id2)
        print(f"请选择屏幕组：")
        for index, _ in enumerate(name1):
            print(f"{index + 1}.\t{_}")
        option = None
        while True:
            try:
                option = int(input("请选择（序号）："))
                if option > length:
                    raise ValueError
                break
            except ValueError:
                print("输入错误，请选择正确的序号")
                continue

        selected_id1 = id2[option - 1]
        selected_name1 = name1[option - 1]
        return selected_id1, selected_name1

    async def verify_timed_switch_function(self):
        try:
            wait_time = 2  # hour #TODO 设置开机和关机之间的时间间隔
            times = 100  # 设置测试定时开关的次数  #TODO 设置测试次数
            # 开始之前先检查屏幕当前的状态，确保屏幕处于开启状态
            enable_times = 0
            break_time = 3
            is_retry = False
            while True:
                if enable_times > 0:
                    is_retry = True
                    logging.error(f"[{self.host}] 测试前，开启屏幕失败，开始重新尝试开启屏幕")
                current_screen_status = await self.check_local_screen_status()
                enable_times += 1
                if str(current_screen_status).upper() == 'OFF':
                    await self.set_screen_on_off(self.selected_id, 'on')
                    status = await self.check_local_screen_status()
                    await asyncio.sleep(2)
                    if str(status).upper() != 'ON' and is_retry:
                        logging.error(
                            f"[{self.host}] 测试前，第{enable_times}次设备开启屏幕失败\t屏幕读取的状态为：{status}")
                else:
                    break
                if enable_times > break_time:
                    break
            for _ in range(times):
                now = datetime.now()
                off_dt = now + timedelta(minutes=1)
                # (TODO: 增加1小时，设备是京东时区，比主机快一小时，后续设备其他时区需要响应增加)
                off_dt_adjusted = off_dt + timedelta(hours=1)
                time_off = off_dt_adjusted.strftime("%H:%M")
                wait_delta = timedelta(hours=wait_time)
                on_dt_adjusted = off_dt_adjusted + wait_delta
                time_on = on_dt_adjusted.strftime("%H:%M")

                config["off_time"] = time_off
                config["on_time"] = time_on

                result = await self.set_timer_screen_on_off('off', self.selected_id)
                if result:
                    # Wait slightly longer than a minute to ensure the off time has passed
                    off_wait_seconds = 70  # Wait 70 seconds (more than 1 min)
                    logging.info(f"[{self.host}] 定时关机任务已设置 ({time_off})，等待 {off_wait_seconds} 秒检查状态...")
                    await asyncio.sleep(off_wait_seconds)
                    screen_status = await self.check_local_screen_status()
                    if str(screen_status).upper() != 'OFF':
                        logging.error(
                            f"[{self.host}] 第{_ + 1}次测试失败：定时关机时间 ({time_off}) 到达后，屏幕没有关闭 (状态: {screen_status})")
                        continue
                    else:
                        logging.info(f"[{self.host}] 定时关机 ({time_off}) 成功。屏幕状态: {screen_status}")
                    time_until_on = on_dt_adjusted - datetime.now()
                    on_wait_seconds = max(0.0, time_until_on.total_seconds()) + 70.0
                    logging.info(
                        f"[{self.host}] 定时开机任务设置 ({time_on})，等待约 {on_wait_seconds: .0f} 秒检查状态...")
                    await asyncio.sleep(on_wait_seconds)  # asyncio.sleep accepts float
                    screen_status = await self.check_local_screen_status()
                    if str(screen_status).upper() != 'ON':
                        logging.error(
                            f"[{self.host}] 第{_ + 1}次测试失败：定时开机时间 ({time_on}) 到达后，屏幕没有开启 (状态: {screen_status})")
                        continue
                    else:
                        logging.info(f"[{self.host}] 定时开机 ({time_on}) 成功。屏幕状态: {screen_status}")
                        print(f"[{self.host}] 第 {_ + 1}/{times} 次测试通过。")
                else:
                    logging.warning(f"[{self.host}] 第{_ + 1}次测试：设置定时关机 ({time_off}) 失败，跳过本次验证。")

            print(f"[{self.host}] 所有 {times} 次定时开关测试完成。")
        except Exception as e:
            tb_lineno = e.__traceback__.tb_lineno if hasattr(e, '__traceback__') and e.__traceback__ else 'N/A'
            logging.error(f"测试设备定时开关时发生异常：{e} - Line: {tb_lineno}",
                          exc_info=True)  # Added exc_info=True for full traceback in logs
        finally:
            # 断开连接
            logging.info(f"{self.host} 断开连接")
            # Ensure self.tn exists before disconnecting
            if self.tn:
                await self.tn.disconnect()


if __name__ == "__main__":
    # 配置 logging
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s -  %(lineno)d - %(funcName)-%('
                                                    'message)s')

    hosts = ['192.168.1.14', '192.168.1.12', '192.168.1.13', '192.168.1.10']
    # account = input("请输入账号: ") # TODO 取消硬编码
    # password = input("请输入密码: ")
    account = 'test2@tester.com'
    password = 'sf123123'
    api_sender = Api_sender(account, password)
    # 获取屏幕组id
    ids, names = Time_switcher_tester.get_groupId_name(api_sender)
    selected_id, selected_name = Time_switcher_tester.display_group_menu(ids, names)


    async def test(host1: str):
        tester = Time_switcher_tester(host1, api_sender, selected_id, selected_name)
        # 直接 await 异步函数，而不是再次調用 asyncio.run
        await tester.verify_timed_switch_function()


    async def run():
        tasks = [test(host2) for host2 in hosts]
        await asyncio.gather(*tasks)


    asyncio.run(run())
