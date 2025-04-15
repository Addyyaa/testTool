from telnet_connecter import Telnet_connector
from api_sender import Api_sender

host = ['192.168.1.14']


class Time_switcher_tester:
    config = {
        "user": "root",
        "password": "ya!2dkwy7-934^",
    }

    def __init__(self, host: str):
        account = input("请输入账号: ")
        password = input("请输入密码: ")
        self.host = host
        # 初始化api发送器
        self.api_sender = Api_sender(account, password)

    async def check_local_screen_status(self):
        await self.tn_initialize()

    async def tn_initialize(self):
        tn = Telnet_connector(self.host)
        await tn.connect()


if __name__ == "__main__":
    tester = Time_switcher_tester(host[0])
    tester.check_local_screen_status()
