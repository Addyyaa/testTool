import logging
import sys
from datetime import datetime
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
            logging.info(f"背光已切换为：{on_off}")
            return True
        else:
            return False

    async def set_timer_screen_on_off(self, on_off: str, group_id: str):
        on_time = config["on_time"]
        off_fime = config["off_time"]
        on_hour = datetime.strptime(on_time, "%H:%M").hour
        on_min = datetime.strptime(on_time, "%H:%M").minute
        off_hour = datetime.strptime(off_fime, "%H:%M").hour
        off_min = datetime.strptime(off_fime, "%H:%M").minute
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
                    logging.info(f"定时开关已重新设置为：开：{config['on_time']}-关：{config['off_time']}")
                    return True
            except Exception as e:
                logging.error(f"定时开关请求发生错误：{e}")
                return False
        else:
            logging.error("时间格式有误")
            sys.exit()

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
            current_screen_status = await self.check_local_screen_status()
            if str(current_screen_status).upper() == 'OFF':
                await self.set_screen_on_off(self.selected_id, 'on')
                status = await self.check_local_screen_status()
                await asyncio.sleep(2)
                if str(status).upper() != 'ON':
                    logging.error(f"[{self.host}] 测试前设备开启屏幕失败\n屏幕读取的状态为：{status}")
            for _ in range(times):
                current_time_hour = datetime.now().hour + 1  # TODO 设备设置了京东时区，所以要快一小时
                if current_time_hour > 24:
                    current_time_hour = current_time_hour - 24
                current_time_min = datetime.now().minute + 1  # 1分钟后关机
                time_off = str(current_time_hour) + ":" + str(current_time_min)
                time_on = str(current_time_hour + wait_time) + ":" + str(current_time_min)
                config["off_time"] = time_off
                config["on_time"] = time_on
                result = await self.set_timer_screen_on_off('off', self.selected_id)
                if result:
                    # 等待一分钟后检查屏幕是否已关闭
                    logging.info(f"[{self.host}] 定时关机任务已设置： ({time_off})，等待 {92} 秒...")
                    await asyncio.sleep(92)  # 使用 asyncio.sleep
                    screen_status = await self.check_local_screen_status()
                    print(screen_status)
                    if str(screen_status).upper() != 'OFF':
                        # 使用 logging 记录错误
                        logging.error(
                            f"[{self.host}] 第{_ + 1}次测试失败：定时关机时间到达，但屏幕没有关闭 (状态: {screen_status})")
                        rs = await self.tn.send_command("ls")
                        print(rs)
                        continue  # 记录错误继续下一次测试
                    else:
                        print(f"[{self.host}] 定时关机成功。")

                    on_delay = wait_time * 3600  # 定時2小時 (秒)
                    await asyncio.sleep(on_delay)  # 使用 asyncio.sleep
                    await asyncio.sleep(70)  # 等待70秒 设备开屏也有延时，近一分钟
                    screen_status = await self.check_local_screen_status()
                    if str(screen_status).upper() == 'OFF':
                        logging.error(
                            f"[{self.host}] 第{_ + 1}次测试失败：定时关机时间到达，但屏幕没有开启 (状态: {screen_status})")
                        continue
                    else:
                        print(f"[{self.host}] 第 {_ + 1}/{times} 次测试通过。")
                else:
                    logging.warning(f"[{self.host}] 第{_ + 1}次测试：定时开关验证失败，跳过本次验证。")

            print(f"[{self.host}] 所有 {times} 次定时开关测试完成。")
        except Exception as e:
            logging.error(f"测试设备定时开关时发生异常：{e}")
        finally:
            # 断开连接
            logging.info(f"{self.host} 断开连接")
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
