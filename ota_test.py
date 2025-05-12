import logging
import sys
import asyncio

from telnet_connecter import Telnet_connector
from api_sender import Api_sender

config = {
    "user": "root",
    "password": "ya!2dkwy7-934^",
    "ota_wait_time": 60,  # 升级所需要的时间，单位秒
    "hosts": ['192.168.1.3', '192.168.1.2'],
    "test_times": 3
}


class OTA_test:
    def __init__(self, host1: str, api_sender1: Api_sender):
        self.host = host1
        self.api_sender = api_sender1
        self.tn: Telnet_connector | None = None
        self.local_version = None
        self.screenId = None

    async def initialize(self):
        await self.connect_to_device()
        self.local_version = await self.get_current_local_version()
        self.screenId = await self.get_screenId_from_host()
        return self

    async def test(self, screen_lastest_version_map1: dict):
        await asyncio.sleep(config["ota_wait_time"])  # 等待升级重启后检查版本号
        has_sucess_ota, local_version = await self.check_ota_status(screen_lastest_version_map1)
        if_failed_retry_query_times = 3
        for _ in range(if_failed_retry_query_times):
            if has_sucess_ota:
                logging.info(f"{self.host}：升级成功")
                break
            else:
                if _ < if_failed_retry_query_times - 1:
                    await asyncio.sleep((_ + 1) * 2)
                    continue
                else:
                    logging.error(
                        f"{self.host}：升级失败, 本地版本号为：{local_version}，待升级版本号：{screen_lastest_version_map1[self.screenId]}")

    async def connect_to_device(self):
        self.tn = Telnet_connector(self.host, port=23)
        await self.tn.connect()

    async def check_ota_status(self, screen_lastest_version_map1: dict):
        if not self.local_version or not self.screenId:
            await self.initialize()
        local_version = self.local_version
        screenId = self.screenId
        lastest_version = screen_lastest_version_map1[screenId]
        if local_version == lastest_version:
            return True, local_version
        else:
            return False, local_version

    async def cmd_sender(self, cmd: str, expect_response: str):
        retry_time = 3
        current_time = 0
        cmd_response_matches = None
        for _ in range(retry_time):
            try:
                if self.tn is None:
                    print(f"[{self.host}] Telnet未进行初始化，开始初始化...")
                    await self.connect_to_device()
                    if self.tn is None:
                        raise ConnectionError(f"[{self.host}] tn初始化失败.")

                # 检查连接状态，如果连接已关闭则重新连接
                if not self.tn.writer or not self.tn.reader or (
                        hasattr(self.tn.writer, 'is_closing') and self.tn.writer.is_closing()):
                    logging.info(f"{self.host}: 连接已关闭，尝试重新连接...")
                    await self.connect_to_device()
                    if self.tn is None or not self.tn.writer or not self.tn.reader:
                        raise ConnectionError(f"{self.host}: 无法重新建立连接")

                await self.tn.send_command(config["user"])
                await self.tn.send_command(config["password"])
                while True:
                    if current_time >= retry_time:
                        break
                    response: str = await self.tn.send_command(cmd, read_timeout=2)
                    current_time += 1
                    if len(response) <= 0:
                        continue
                    elif config["password"] in response:
                        continue
                    else:
                        response_tmp = response.split('\n')
                        response2 = [x for x in response_tmp if
                                     'busybox telnetd' not in x and '/ #' not in x and '# ' not in x]
                        current_cmd_response = response2[-1]
                        cmd_response_matches = current_cmd_response
                        # print(f"++++++{response2}++++++")
                        if expect_response == 'any':
                            break
                        else:
                            if expect_response in cmd_response_matches:
                                break
                            else:
                                continue
            except ConnectionError as e:
                if _ < retry_time - 1:
                    logging.warning(f"{self.host}：连接失败: {e}，等待30秒后重试...")
                    await asyncio.sleep(30)
                    continue
                else:
                    logging.error(f"{self.host}：重新连接到设备失败: {e}")

        return cmd_response_matches

    @staticmethod
    def get_ota_data() -> list[dict]:
        api_sender1 = api_sender
        response = api_sender1.send_api(api_sender1.ota_list, data="", method="get")
        if response.status_code == 200 and response.json()["code"] == 20:
            group_device_relation = response.json()["data"]
            return group_device_relation
        else:
            logging.error(response.text)
            sys.exit()

    @staticmethod
    def show_screen_menus():
        group_device_relation = OTA_test.get_ota_data()
        # 屏幕最新版本对照表
        screen_lastest_version_map1 = {}

        # 创建屏幕列表
        all_screens = []
        for group in group_device_relation:
            for screen in group['screenList']:
                all_screens.append({
                    'screenId': screen['screenId'],
                    'name': f"{screen['screenId']} - {group['name']} - (当前版本: {screen['version']}, 可升级到:"
                            f" {screen['lastestVersion']})",
                    'groupId': group['id'],
                    'lastestVersion': screen['lastestVersion']
                })
                screen_lastest_version_map1[screen['screenId']] = screen['lastestVersion']

        while True:
            print(f"\n请选择要升级的设备（选择序号，多选请使用空格分隔）")
            # 显示所有屏幕
            for index, screen in enumerate(all_screens):
                print(f"{index + 1}.\t{screen['name']}")

            # 获取用户选择
            option = input("请选择（序号，多选请用空格分隔）：")

            try:
                # 处理用户输入
                selected_indices = [int(x.strip()) - 1 for x in option.split() if x.strip().isdigit()]

                # 验证选择的有效性
                valid_selections = [idx for idx in selected_indices if 0 <= idx < len(all_screens)]

                if not valid_selections:
                    print("输入错误，请选择正确的序号")
                    continue

                # 按组ID组织选择的屏幕
                group_screens = {}
                for idx in valid_selections:
                    screen = all_screens[idx]
                    group_id = str(screen['groupId'])
                    if group_id not in group_screens:
                        group_screens[group_id] = {
                            'ids': [],
                            'versions': []
                        }
                    group_screens[group_id]['ids'].append(screen['screenId'])
                    group_screens[group_id]['versions'].append(screen['lastestVersion'])

                # 转换为所需格式
                result = [{
                    "ids": screens['ids'],
                    "screenGroupId": group_id,
                } for group_id, screens in group_screens.items()]

                print("\n已选择的设备：")
                for idx in valid_selections:
                    print(f"- {all_screens[idx]['name']}")

                return result, screen_lastest_version_map1

            except ValueError:
                print("输入错误，请使用数字序号")
                continue

    @staticmethod
    def send_ota_request():
        selected_screens1, screen_lastest_version_map1 = OTA_test.show_screen_menus()
        print(f"+++++===>{selected_screens1}")
        for _ in selected_screens1:
            response = api_sender.send_api(api_sender.confirm_to_ota, data=_, method="post")
            if response.status_code == 200 and response.json()["code"] == 20:
                logging.info("已发送升级请求")
            else:
                logging.error(response.text)
                sys.exit()
        return selected_screens1, screen_lastest_version_map1

    async def get_current_local_version(self):
        try:
            retry_times = 3
            current_times = 0
            while True:
                if current_times >= retry_times:
                    logging.error(f"{self.host}：获取本地版本失败")
                    sys.exit()
                current_times += 1
                local_version = await self.cmd_sender("cat /software/version.ini", "any")
                if not local_version:
                    continue
                else:
                    break
            print(f"本地版本：{local_version}")
            local_version = local_version.split('=')[1].strip()
            logging.info(f"{self.host}：本地版本：{local_version}")
        except Exception as e:
            logging.error(e)
            sys.exit()
        return local_version

    async def get_screenId_from_host(self):
        screenId = await self.cmd_sender("cat customer/screenId.ini", "deviceId")
        screenId = screenId.split('=')[1].strip()
        logging.info(f"{self.host}：屏幕ID：{screenId}")
        return screenId

    async def restore_factory_settings(self):
        await self.cmd_sender("/software/script/restore_factory_settings.sh", "any")
        logging.info(f"{self.host}：已执行恢复出厂设置命令，等待设备重启...")
        await asyncio.sleep(100)  # 增加等待时间至120秒

        # 确保关闭旧连接
        if self.tn:
            try:
                await self.tn.disconnect()
            except Exception as e:
                logging.error(f"{self.host}：关闭旧连接时发生错误：{e}")
            self.tn = None

        # 添加重试机制
        max_retries = 3
        for retry in range(max_retries):
            try:
                logging.info(f"{self.host}：尝试重新连接设备，第{retry + 1}次尝试...")
                await self.connect_to_device()
                logging.info(f"{self.host}：重新连接成功！")
                break
            except ConnectionError as e:
                if retry < max_retries - 1:
                    logging.warning(f"{self.host}：连接失败: {e}，等待30秒后重试...")
                    await asyncio.sleep(30)
                else:
                    logging.error(f"{self.host}：恢复出厂设置后无法重新连接到设备: {e}")
                    # 不抛出异常，让程序继续执行完成


if __name__ == "__main__":
    # account = input("请输入账号: ")
    # password = input("请输入密码: ")
    account = 'test2@tester.com'
    password = 'sf123123'
    api_sender = Api_sender(account, password)
    # 显示菜单
    selected_screens, screen_lastest_version_map = OTA_test.send_ota_request()
    print(f"数量：{len(selected_screens[0]['ids']), selected_screens[0]['ids']}, id列表：{len(config['hosts'])}")
    if len(selected_screens[0]['ids']) != len(config['hosts']):
        logging.error(f"选择的设备数量与主机host数量不匹配")
        sys.exit()


    async def main():
        # 根据config中的test_times参数执行对应次数的测试
        test_times = config.get("test_times", 1)  # 默认执行1次
        logging.info(f"将执行 {test_times} 次测试")

        for test_round in range(test_times):
            logging.info(f"开始执行第 {test_round + 1} 轮测试")

            # 创建所有设备的测试任务，实现并行测试
            async def test_device(host):
                try:
                    ota_test = OTA_test(host, api_sender)
                    await ota_test.initialize()
                    await ota_test.test(screen_lastest_version_map)
                    await ota_test.restore_factory_settings()
                except Exception as e:
                    logging.error(f"{host}：测试过程中发生错误：{e}")

            # 使用asyncio.gather同时执行所有设备的测试任务
            tasks = [test_device(host) for host in config['hosts']]
            await asyncio.gather(*tasks)
            logging.info(f"第 {test_round + 1} 轮测试完成")


    asyncio.run(main())
