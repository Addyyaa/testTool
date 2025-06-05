import logging
import sys
import asyncio
import os
from datetime import datetime
from sql_connecter import DatabaseConnectionPool

from telnet_connecter import Telnet_connector
from api_sender import Api_sender

# 创建logs目录（如果不存在）
if not os.path.exists('logs'):
    os.makedirs('logs')

# 生成日志文件名，包含时间戳
log_filename = os.path.join('logs', f'ota_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(module)s:%(filename)s:%(lineno)d - %(funcName)s() - %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ],
    force=True  # 强制重新配置，移除所有现有处理器
)

# 添加一个测试日志
logging.info("OTA测试程序启动")

config = {
    "user": "root",
    "password": "ya!2dkwy7-934^",
    "ota_wait_time": 60,  # 升级所需要的时间，单位秒
    "hosts": ['192.168.1.45'],
    "test_times": 1000
}

# 添加全局变量用于跟踪成功次数
success_times = 0


class OTA_test:
    _db_pool = None  # 类级别的数据库连接池

    def __init__(self, host1: str, api_sender1: Api_sender, selected_screens2: list, screen_lastest_version_map2: dict):
        self.host = host1
        self.api_sender = api_sender1
        # 初始化时就创建Telnet_connector实例，并传入用户名和密码
        self.tn = Telnet_connector(self.host, port=23, username=config["user"], password=config["password"])
        self.local_version = None
        self.screenId = None
        self.selected_screens1 = selected_screens2
        self.screen_lastest_version_map1 = screen_lastest_version_map2

    @classmethod
    def get_db_pool(cls):
        """获取或初始化数据库连接池"""
        if cls._db_pool is None:
            cls._db_pool = DatabaseConnectionPool()
        return cls._db_pool

    @classmethod
    def query_sql(cls, sql: str, params: tuple = None) -> list:
        """执行SQL查询"""
        try:
            # 不需要再传递数据库配置，直接获取连接
            with cls.get_db_pool().get_connection('mysql') as db:
                results = db.execute(sql, params) if params else db.execute(sql)
                return results
        except Exception as e:
            logging.error(f"数据库查询出错: {str(e)}")
            # 不要抛出异常，返回空结果
            return []

    async def initialize(self):
        await self.connect_to_device()
        self.local_version = await self.get_current_local_version()
        self.screenId = await self.get_screenId_from_host()
        return self

    async def test(self, screen_lastest_version_map2: dict):
        global success_times
        self.send_ota_request()
        await asyncio.sleep(config["ota_wait_time"])  # 等待升级重启后检查版本号
        if_failed_retry_query_times = 3
        has_sucess_ota = False
        local_version = None

        for _ in range(if_failed_retry_query_times):
            has_sucess_ota, local_version = await self.check_ota_status(screen_lastest_version_map2)
            if has_sucess_ota:
                logging.info(f"{self.host}：升级成功")
                success_times += 1  # 升级成功时增加计数
                break
            else:
                if _ < if_failed_retry_query_times - 1:
                    await asyncio.sleep((_ + 1) * 2)
                    continue
                else:
                    logging.error(
                        f"{self.host}：升级失败, 本地版本号为：{local_version}，待升级版本号：{screen_lastest_version_map2[self.screenId]}")

    async def connect_to_device(self):
        await self.tn.connect()

    async def check_ota_status(self, screen_lastest_version_map2: dict):
        if not self.local_version or not self.screenId:
            await self.initialize()
        local_version = await self.get_current_local_version()
        screenId = self.screenId
        lastest_version = screen_lastest_version_map2[screenId]
        if local_version == lastest_version:
            return True, local_version
        else:
            return False, local_version

    async def cmd_sender(self, cmd: str, expect_response: str):
        retry_time = 3
        current_time = 0
        cmd_response_matches = None

        # 确保 cmd 是字符串类型
        if cmd is None:
            cmd = ""
            logging.warning(f"{self.host}: 命令为None，使用空字符串")
        elif not isinstance(cmd, str):
            try:
                old_cmd = cmd
                cmd = str(cmd)
                logging.warning(f"{self.host}: 命令类型不是字符串 (type: {type(old_cmd)})，已转换为: {cmd}")
            except Exception as e:
                logging.error(f"{self.host}: 无法将命令转换为字符串: {e}")
                cmd = ""

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

                # 先发送用户名和密码，处理可能的登录状态
                login_response = await self.tn.send_command("", read_timeout=0.5)  # 发送空命令获取当前提示
                if "login:" in login_response:
                    logging.info(f"{self.host}: 检测到登录提示，发送用户名...")
                    await self.tn.send_command(config["user"])
                    login_response = await self.tn.send_command("", read_timeout=0.5)

                if "Password:" in login_response or "password:" in login_response:
                    logging.info(f"{self.host}: 检测到密码提示，发送密码...")
                    await self.tn.send_command(config["password"])
                    await asyncio.sleep(1)  # 等待登录处理完成
                else:
                    # 如果没有检测到登录提示，发送一个换行符刷新提示符
                    await self.tn.send_command("")

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

    async def set_sql_need_to_update(self):
        try:
            # noinspection SqlResolve
            sql = "UPDATE t_ota_upgrade_record SET status = %s WHERE device_id = %s"
            if not self.screenId:
                self.screenId = await self.get_screenId_from_host()

            result = self.query_sql(sql=sql, params=(1, self.screenId))
            print(f"+++++>{result}")
            if result is not None:
                logging.info(f"{self.host}：更新设备 {self.screenId} 的OTA状态成功")
        except Exception as e:
            logging.error(f"{self.host}：更新ota状态失败: {e}")
            # 继续执行，不让数据库错误影响主要功能

    def send_ota_request(self):
        for _ in self.selected_screens1:
            response = api_sender.send_api(api_sender.confirm_to_ota, data=_, method="post")
            if response.status_code == 200 and response.json()["code"] == 20:
                logging.info(f"{self.host}-已发送升级请求")
            else:
                error_msg = f"{self.host}-发送升级请求失败: {response.text}"
                logging.error(error_msg)
                raise RuntimeError(error_msg)
        return self.selected_screens1, self.screen_lastest_version_map1

    async def get_current_local_version(self):
        try:
            retry_times = 3
            current_times = 0
            while True:
                if current_times >= retry_times:
                    error_msg = f"{self.host}：获取本地版本失败，已达到最大重试次数"
                    logging.error(error_msg)
                    raise RuntimeError(error_msg)
                current_times += 1
                local_version1 = await self.cmd_sender("cat /software/version.ini", "any")
                if not local_version1:
                    continue
                else:
                    break
            local_version = local_version1.split('=')[1].strip()
            logging.info(f"{self.host}：本地版本：{local_version}")
        except Exception as e:
            error_msg = f"{self.host}：获取版本号失败: {e}"
            logging.error(error_msg)
            # 捕获异常但重新抛出，不使用sys.exit()
            raise RuntimeError(error_msg)
        return local_version

    async def get_screenId_from_host(self):
        screenId = await self.cmd_sender("cat customer/screenId.ini", "deviceId")
        screenId = screenId.split('=')[1].strip()
        logging.info(f"{self.host}：屏幕ID：{screenId}")
        return screenId

    async def restore_factory_settings(self):
        await self.cmd_sender("/software/script/restore_factory_settings.sh", "any")
        logging.info(f"{self.host}：已执行恢复出厂设置命令，等待设备重启...")
        # 更新ota状态
        await self.set_sql_need_to_update()
        await asyncio.sleep(120)  # 增加等待时间至120秒

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
    pool = DatabaseConnectionPool()
    # 显示菜单
    selected_screens1, screen_lastest_version_map1 = OTA_test.show_screen_menus()
    screen_counts = 0
    for screen_count in selected_screens1:
        screen_counts += len(screen_count['ids'])
    if screen_counts != len(config['hosts']):
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
                    ota_test = OTA_test(host, api_sender, selected_screens1, screen_lastest_version_map1)
                    await ota_test.initialize()
                    await ota_test.test(screen_lastest_version_map1)
                    await ota_test.restore_factory_settings()
                except Exception as e:
                    logging.error(f"{host}：测试过程中发生错误：{str(e)}")
                    # 不再抛出异常，让其他设备继续测试

            # 使用asyncio.gather同时执行所有设备的测试任务
            tasks = [test_device(host) for host in config['hosts']]
            # 使用return_exceptions=True确保一个任务失败不会影响其他任务
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 检查是否有任务异常
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    host = config['hosts'][i] if i < len(config['hosts']) else f"未知设备({i})"
                    logging.error(f"{host}：任务执行失败: {str(result)}")
            logging.info(f"第 {test_round + 1} 轮测试完成---【{success_times}/{test_times}】")

            logging.getLogger().handlers[0].flush()  # 强制刷新文件处理器的缓冲


    try:
        asyncio.run(main())
        logging.info("所有测试完成")
    except KeyboardInterrupt:
        logging.info("测试被用户中断")
    except Exception as e:
        logging.error(f"测试过程中发生未处理的错误: {e}")
        sys.exit(1)
