from api_sender import Api_sender
import logging
import sys

class Syn_202_test:
    def __init__(self):
        self.user, self.passwd = self.ask_login_info()
        self.api_sender = Api_sender(self.user, self.passwd)

    def ask_login_info(self):
        while True:
            user = input("请输入用户名：")
            if len(user) <= 0:
                print("输入错误，请重新输入")
                continue
            passwd = input("请输入密码：")
            if len(passwd) <= 0:
                print("输入错误，请重新输入")
            if user and passwd:
                return user, passwd
            else:
                print("输入错误，请重新输入")

    def show_screen_menus(self):
        group_device_relation = self.get_ota_data()
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
                
                print(f"result: {result}\nscreen_lastest_version_map1: {screen_lastest_version_map1}")

                return result, screen_lastest_version_map1

            except ValueError:
                print("输入错误，请使用数字序号")
                continue
    def get_ota_data(self) -> list[dict]:
        api_sender1 = self.api_sender
        response = api_sender1.send_api(api_sender1.ota_list, data="", method="get")
        if response.status_code == 200 and response.json()["code"] == 20:
            group_device_relation = response.json()["data"]
            return group_device_relation
        else:
            logging.error(response.text)
            sys.exit()
    
    def check_device_suitability_for_cloud_sync(self, screen_id: list, screen_lastest_version_map1: dict) -> bool:
        need_cloud_sync_screen_id = []
        for screen_dic in screen_id:
            for screen in screen_dic['ids']:
                if screen_lastest_version_map1[screen].startswith('2.'):
                    need_cloud_sync_screen_id.append(screen)
                else:
                    print(f"设备{screen}版本为{screen_lastest_version_map1[screen]}, 不支持云同步")
        return need_cloud_sync_screen_id

    def send_sync_request(self, screen_id: list):
        api_sender1 = self.api_sender
        def send_request(screen_id: str):
            response = api_sender1.send_api(api_sender1.cloud_sync, data={"screenId": screen_id, "syncMethod": 3}, method="post")
            if response.status_code == 200 and response.json()["code"] == 20:
                return True
            else:
                return False
        for screen in screen_id:
            result = send_request(screen)
            if result:
                print(f"设备{screen}云同步请求发送成功")
            else:
                print(f"设备{screen}云同步请求发送失败")

    
    
    def main(self):
        user_choice_screen_id, screen_lastest_version_map1 = self.show_screen_menus()
        need_cloud_sync_screen_id = self.check_device_suitability_for_cloud_sync(user_choice_screen_id, screen_lastest_version_map1)
        if len(need_cloud_sync_screen_id) > 0:
            print(f"需要云同步的设备: {need_cloud_sync_screen_id}")
            self.send_sync_request(need_cloud_sync_screen_id)
            input("按回车键突出...")
        else:
            print("没有需要云同步的设备")

if __name__ == "__main__":
    syn_202_test = Syn_202_test()
    syn_202_test.main()
