import logging
import sys
import asyncio
import time

from telnet_connecter import Telnet_connector
from api_sender import Api_sender
import re

config = {
    "user": "root",
    "password": "ya!2dkwy7-934^",
    "on_time": "09:35",  # 24小时制
    "off_time": "18:30",
}


class Black_bug_tester:
    def __init__(self, host1: str, api_sender1: Api_sender, selected_id2: str, selected_name3: str):
        # 声明一个变量用来存储tn实例
        self.host = host1
        # 初始化api发送器
        self.api_sender = api_sender1
        self.tn: Telnet_connector | None = None  # Ensure tn starts as None and has type hint
        self.selected_id = selected_id2
        self.selected_name = selected_name3

    async def tn_initialize(self):
        self.tn = Telnet_connector(self.host, port=23)
        await self.tn.connect()

    def screen_off(self):
        body = {
            "screenGroupId": self.selected_id,
            "switchType": 2
        }
        response = self.api_sender.send_api(self.api_sender.screen_switch, body)
        if response.status_code == 200:
            if response.json()["code"] == 20:
                logging.info(f"{self.host}-已下发屏幕开关指令：OFF")
            else:
                logging.error(response.text)
        else:
            logging.error(response.text)

    def screen_on(self):
        body = {
            "screenGroupId": self.selected_id,
            "switchType": 1
        }
        response = self.api_sender.send_api(self.api_sender.screen_switch, body)
        if response.status_code == 200:
            if response.json()["code"] == 20:
                logging.info(f"{self.host}-已下发屏幕开关指令：ON")
            else:
                logging.error(response.text)
        else:
            logging.error(response.text)

    def black_screen_tester(self):
        pass

    async def cmd_sender_strict_check(self, cmd: str, expected_result1: str, expected_result2: str = None):
        cmd_response_matches = None
        lines = None
        if self.tn is None:
            print(f"[{self.host}] Telnet未进行初始化，开始初始化...")
            await self.tn_initialize()
            if self.tn is None:
                raise ConnectionError(f"[{self.host}] tn初始化失败.")
        await self.tn.send_command(config["user"])
        await self.tn.send_command(config["password"])
        while True:
            response: str = await self.tn.send_command(cmd, read_timeout=2)
            if len(response) <= 0:
                continue
            elif 'ya!2dkwy7-934' in response:
                continue
            else:
                lines = response.split('\n')[1:-2]
                cmd_response_matches = '\n'.join(lines).strip().replace(' ', '')
                if len(lines) <= 0:
                    pattern = fr'\b({expected_result1}|{expected_result2})\b'
                    match = re.search(pattern, response, re.IGNORECASE)
                    lines = match
                    if match:
                        cmd_response_matches = match.group()
                        break
                else:
                    if len(lines) > 1:
                        cmd_response_matches = lines[0]  # 有的时候会存在把命令也列出来的情况，导致匹配不上
                    break
        return cmd_response_matches, lines

    async def check_screen_backlight(self):
        result1, lines1 = await self.cmd_sender_strict_check('cat /sys/class/gpio/gpio5/value', '1', '0')
        result2, lines2 = await self.cmd_sender_strict_check('cat /sys/class/gpio/gpio69/value', '1', '0')
        result1 = result1.strip()
        result2 = result2.strip()
        if str(result1) == '1' and str(result2) == '0':
            return 'OFF'
        elif str(result1) == '0' and str(result2) == '1':
            return 'ON'
        else:
            logging.error(f"{self.host}屏幕背光状态检测失败\t-\tGPIO5状态：{result1}\tGPIO69状态：{result2}\tlines{lines1}\t{lines2}")
            print(f"result1: {result1}\nresult2: {result2}\nlines1: {lines1}\nlines2: {lines2}")
            sys.exit()  # TODO 移除
            return False

    async def screen_checker(self, test_count: int = 100, delay: int = 2):
        has_circled = 0
        while True:
            if has_circled >= test_count:
                break
            self.screen_on()
            time.sleep(delay)
            screen_real_status = await self.check_screen_backlight()
            if not screen_real_status:
                logging.error(f"{self.host}-第{has_circled + 1}次测试失败！")
                sys.exit()  # TODO 移除
                continue
            if screen_real_status.upper() == 'ON':
                logging.info("检测通过！")
            else:
                logging.error(f"{self.host}-第{has_circled + 1}检测失败！屏幕真实状态：{screen_real_status}")
            self.screen_off()
            time.sleep(delay)
            screen_real_status = await self.check_screen_backlight()
            if not screen_real_status:
                logging.error(f"{self.host}-第{has_circled + 1}次测试失败！")
                sys.exit()  # TODO 移除
                continue
            if screen_real_status.upper() == 'OFF':
                logging.info("检测通过！")
            else:
                logging.error(f"{self.host}-第{has_circled + 1}检测失败！屏幕真实状态：{screen_real_status}")
                sys.exit()  # TODO 移除
            has_circled += 1
            logging.info(f"第{has_circled}次测试通过")

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


if __name__ == '__main__':
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    # 创建格式器
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(lineno)d - %(funcName)s - %(message)s')
    # 文件处理器（'a' 表示追加模式）
    file_handler = logging.FileHandler('black_screen_test.log', mode='a', encoding='utf-8')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    # 控制台处理器（可选）
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG)

    # 添加 handler 到 logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # 主程序逻辑
    logging.info("========== 程序启动 ==========")
    hosts = ['192.168.1.14', '192.168.1.12', '192.168.1.13', '192.168.1.10']
    account = 'test2@tester.com'
    password = 'sf123123'
    api_sender = Api_sender(account, password)
    # 获取屏幕组id
    ids, names = Black_bug_tester.get_groupId_name(api_sender)
    selected_id, selected_name = Black_bug_tester.display_group_menu(ids, names)
    print(f"您选择的屏幕组是：{selected_name}\t{selected_id}")


    async def test(host1: str):
        tester = Black_bug_tester(host1, api_sender, selected_id, selected_name)
        # 直接 await 异步函数，而不是再次調用 asyncio.run
        await tester.screen_checker()


    async def run():
        tasks = [test(host2) for host2 in hosts]
        await asyncio.gather(*tasks)


    asyncio.run(run())
