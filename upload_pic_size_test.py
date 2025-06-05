from api_sender import Api_sender
import logging
import sys
import requests
from PIL import Image
from io import BytesIO

class Upload_pic_size_test:
    def __init__(self):
        # self.user, self.passwd = self.ask_login_info()
        self.user = "test2@tester.com"
        self.passwd = "sf123123"
        self.api_sender = Api_sender(self.user, self.passwd)
        self.base_url = "http://192.168.1.100"
        self.port = 8080
        self.protocol = "http"
        self.file_domian = "files-static-test.austinelec.com"
    def show_screen_menus(self):
        group_device_relation = self.get_ota_data()
        # 屏幕最新版本对照表
        screen_lastest_version_map1 = {}
        screen_current_version_map1 = {}

        # 创建屏幕列表
        all_screens = []
        for group in group_device_relation:
            for screen in group['screenList']:
                all_screens.append({
                    'screenId': screen['screenId'],
                    'groupId': group['id'],
                })

        while True:
            print(f"\n请选择要检查的屏幕）")
            # 显示所有屏幕
            for index, screen in enumerate(all_screens):
                print(f"{index + 1}.\t{screen['screenId']}")

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
                selected_screens = []
                for idx in valid_selections:
                    screen = all_screens[idx]
                    selected_screens.append({'screenId': screen['screenId'], 'groupId': screen['groupId']})

                print(f"selected_screens: {selected_screens}")
                return selected_screens

            except ValueError:
                print("输入错误，请使用数字序号")
                continue
    
    def get_screen_picture(self, selected_screen: list[dict]):
        screen_pictures = {}
        for screen in selected_screen:
            hasTF_card = self.judge_hasTF_card(screen['screenId'])
            if hasTF_card:
                screen['hasTF_card'] = True
            else:
                screen['hasTF_card'] = False
        
        for screen in selected_screen:
            if screen['hasTF_card']:
                api = self.api_sender.get_pic_withTF + f"{screen['screenId']}"
            else:
                api = self.api_sender.get_pic_withNoTf + f"{screen['screenId']}"
            response = self.api_sender.send_api(api, data="", method="get")
            if response.status_code == 200 and response.json()["code"] == 20:
                if screen['hasTF_card']:
                    screen_picture = response.json()["data"]["records"]
                    screen_pictures[screen['screenId']] = screen_picture
                else:
                    screen_picture = response.json()["data"]["pictures"]
                    screen_pictures[screen['screenId']] = screen_picture
            else:
                logging.error(f"获取屏幕{screen['screenId']}的图片失败\t{response.text}")
        # 拼接图片地址
        for screen in screen_pictures:
            screen_pictures[screen] = [f"{self.protocol}://{self.file_domian}/{screen_picture['fileId']}" for screen_picture in screen_pictures[screen] if screen_picture['fileId'] != ""]
        return screen_pictures
    
    def get_picture_info(self, screen_pictures: dict):
        """
        获取图片的文件大小和分辨率信息
        
        Args:
            screen_pictures (dict): 屏幕图片URL字典
        """
        test_flag = True
        while True:
            enable_pic_info = input("是否打印所有图片信息？（y/n）")
            if enable_pic_info == "y":
                break
            elif enable_pic_info == "n":
                break
            else:
                print("输入错误，请重新输入")
                continue
        for screen in screen_pictures:
            for picture_url in screen_pictures[screen]:
                try:
                    response = requests.get(picture_url)
                    if response.status_code == 200:
                        # 获取文件大小
                        picture_size_bytes = len(response.content)
                        picture_size_mb = picture_size_bytes / (1024 * 1024)
                        
                        # 获取图片分辨率
                        img = Image.open(BytesIO(response.content))
                        width, height = img.size
                        format_type = img.format if img.format else "未知"
                        mode = img.mode if img.mode else "未知"
                        def print_picture_info():
                            logging.error(f"屏幕{screen}的图片{picture_url}的大小为{picture_size_mb:.2f} MB, 超过2MB, 请检查")
                            # 格式化输出
                            print(f"图片URL: {picture_url}")
                            print(f"  - 文件大小: {picture_size_bytes:,} 字节 ({picture_size_mb:.2f} MB)")
                            print(f"  - 分辨率: {width} × {height} 像素")
                            print(f"  - 格式: {format_type}")
                            print(f"  - 色彩模式: {mode}")
                            print("-" * 50)
                        if enable_pic_info.upper() == "Y":
                            print_picture_info()
                        if picture_size_mb > 2:
                            test_flag = False
                            print_picture_info()
                    else:
                        logging.error(f"获取屏幕{screen}的图片{picture_url}失败\t状态码: {response.status_code}")
                        print(f"  ❌ 获取失败: {picture_url} (状态码: {response.status_code})")
                        
                except requests.exceptions.RequestException as e:
                    logging.error(f"网络请求失败: {picture_url}, 错误: {str(e)}")
                    print(f"  ❌ 网络请求失败: {picture_url}")
                    
                except Exception as e:
                    logging.error(f"处理图片时发生错误: {picture_url}, 错误: {str(e)}")
                    print(f"  ❌ 处理图片时发生错误: {picture_url}")
        if test_flag:
            print("测试通过，所有图片大小均符合要求")
    
    def get_detailed_picture_stats(self, screen_pictures: dict):
        """
        获取所有图片的统计信息
        
        Args:
            screen_pictures (dict): 屏幕图片URL字典
        """
        total_size = 0
        total_count = 0
        resolution_stats = {}
        format_stats = {}
        
        
        for screen in screen_pictures:
            screen_size = 0
            screen_count = len(screen_pictures[screen])
            
            for picture_url in screen_pictures[screen]:
                try:
                    response = requests.get(picture_url)
                    if response.status_code == 200:
                        picture_size = len(response.content)
                        screen_size += picture_size
                        total_size += picture_size
                        total_count += 1
                        
                        # 获取分辨率和格式统计
                        img = Image.open(BytesIO(response.content))
                        resolution = f"{img.size[0]}×{img.size[1]}"
                        format_type = img.format if img.format else "未知"
                        
                        resolution_stats[resolution] = resolution_stats.get(resolution, 0) + 1
                        format_stats[format_type] = format_stats.get(format_type, 0) + 1
                        
                except Exception as e:
                    logging.error(f"统计图片信息时发生错误: {picture_url}, 错误: {str(e)}")
            
        
        print(f"\n总体统计:")
        print(f"  总图片数量: {total_count} 张")
        print(f"  总文件大小: {total_size / (1024 * 1024):.2f} MB")
        print(f"  平均文件大小: {(total_size / total_count) / (1024 * 1024):.2f} MB" if total_count > 0 else "  平均文件大小: 0 MB")
        
        if resolution_stats:
            print(f"\n分辨率分布:")
            for resolution, count in sorted(resolution_stats.items()):
                print(f"  {resolution}: {count} 张")
        
        if format_stats:
            print(f"\n格式分布:")
            for format_type, count in sorted(format_stats.items()):
                print(f"  {format_type}: {count} 张")
        
        print(f"{'='*60}")

    def judge_hasTF_card(self, screen_id: str):
        api_sender1 = self.api_sender
        storage_api = api_sender1.get_storage + f"/{screen_id}"
        response = api_sender1.send_api(storage_api, data="", method="get")
        if response.status_code == 200 and response.json()["code"] == 20:
            storage_info = response.json()["data"]
            if storage_info["totalStorage"] > 0:
                return True
            else:
                return False
        else:
            logging.error(f"获取屏幕{screen_id}的存储信息失败\t{response.text}")
            sys.exit()
    def get_ota_data(self) -> list[dict]:
        api_sender1 = self.api_sender
        response = api_sender1.send_api(api_sender1.ota_list, data="", method="get")
        if response.status_code == 200 and response.json()["code"] == 20:
            group_device_relation = response.json()["data"]
            return group_device_relation
        else:
            logging.error(response.text)
            sys.exit()

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
    
    def main(self):
        selected_screens = self.show_screen_menus()
        screen_pictures = self.get_screen_picture(selected_screens)
        
        # 显示详细的图片信息
        self.get_picture_info(screen_pictures)
        
        # 显示统计信息
        # self.get_detailed_picture_stats(screen_pictures)

if __name__ == "__main__":
    tester = Upload_pic_size_test()
    tester.main()
