import logging
import sys

from telnet_connecter import Telnet_connector
from api_sender import Api_sender

host = ['192.168.1.10']
config = {
    "user": "root",
    "password": "ya!2dkwy7-934^",
}


class Time_switcher_tester:

    def __init__(self, host1: str):
        # account = input("请输入账号: ")
        # password = input("请输入密码: ")
        self.account = 'test2@tester.com'
        self.password = 'sf123123'  # TODO 取消硬编码
        self.host = host1
        # 初始化api发送器
        self.api_sender = Api_sender(self.account, self.password)
        self.tn = None

    async def check_local_screen_status(self):
        await self.tn_initialize()
        # 登陆telnet
        await self.tn.send_command(config["user"])
        await self.tn.send_command(config["password"])
        response: str = await self.tn.send_command('cat customer/screen_on_off')  # TODO 需要改为优化版的路径
        lines = response.split('\n')[1:-2]
        screen_status = '\n'.join(lines).strip().replace(' ', '')
        return screen_status

    async def tn_initialize(self):
        self.tn = Telnet_connector(self.host)
        await self.tn.connect()

    @staticmethod
    async def check_multiple_devices(hosts1: list):
        results1 = {}
        for host1 in hosts1:
            tester = Time_switcher_tester(host1)
            try:
                status1 = await tester.check_local_screen_status()
                results1[host1] = status1
            except Exception as e:
                results1[host1] = f"Error: {str(e)}"
            finally:
                if tester.tn:
                    await tester.tn.disconnect()
        return results1

    async def set_screen_on_off(self, group_id: str, on_off: str):
        body = {
            "screenGroupId": group_id,
            "switchType": 1 if on_off == 'on' else 2
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

    async def set_timer_screen_on_off(self, on_off: str):
        # TODO 完善定时开关设置及相关测试业务
        pass

    async def get_groupId_name(self):
        group_list = []
        group_option = []
        response = self.api_sender.send_api(self.api_sender.get_device, data="", method="get")
        if response.status_code == 200 and response.json()["code"] == 20:
            group = response.json()["data"]["group"]
            for i in group:
                group_list.append(i["id"])
                group_option.append(i["name"])
            return group_list, group_option
        else:
            input(f"该账号下没有设备，按回车键退出程序")
            sys.exit()

    def display_group_menu(self):
        id1, name = asyncio.run(self.get_groupId_name())
        length = len(id1)
        print(f"请选择屏幕组：")
        for index, _ in enumerate(name):
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

        selected_id = id1[option - 1]
        selected_name = name[option - 1]
        return selected_id, selected_name


if __name__ == "__main__":
    import asyncio

    # 示例：检查多个设备
    hosts = ['192.168.1.10']  # 可以根据需要添加更多设备
    results = asyncio.run(Time_switcher_tester.check_multiple_devices(hosts))
    for host, status in results.items():
        print(f"设备 {host} 的状态: {status}")
    test1 = Time_switcher_tester(host)
    id, name = test1.display_group_menu()
    print(f"您选择的设备组是：{name}({id})")
    asyncio.run(test1.set_screen_on_off(id, 'on'))
