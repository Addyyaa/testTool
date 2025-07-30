import logging
# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s %(filename)s:%(lineno)d')
from api_sender import Api_sender
import sys
import requests
from PIL import Image
from io import BytesIO




class Upload_pic_size_test:
    def __init__(self):
        # self.user, self.passwd = self.ask_login_info()
        self.user = "test2@tester.com"
        self.passwd = "sf123123"
        self.port = 8082
        # self.port = 8080
        self.protocol = "http"
        # self.server = "cloud-service.austinelec.com"
        self.server = "139.224.192.36"
        self.base_url = f"{self.protocol}://{self.server}"
        self.api_sender = Api_sender(self.user, self.passwd, self.server, self.port)
        # self.file_domian = "files-static.austinelec.com"  # 环境切换需要更换
        self.file_domian = "files-static-test.austinelec.com"  # 环境切换需要更换
        self.detect_item = {"detect_file_size": self.detect_file_size_info, "detect_screen_resolution": self.detect_picture_resolution_item}
        self.alubm_detect_item = {"detect_album_file_size": self.detect_album_file_size_info, "detect_album_picture_resolution": self.detect_album_picture_resolution_item}
        self.test_flag = True
        self.android_file_all_smaller_than_2 = True
        self.album_file_all_smaller_than_1 = True
        self.android_picture_resolution_all_smaller_than_1920 = True
        self.album_picture_max_size = 2
        self.max_short_size = 1920
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
                return selected_screens

            except ValueError:
                print("输入错误，请使用数字序号")
                continue
    
    def get_screen_picture(self, selected_screen: list[dict]):
        screen_pictures = {}
        group_screen_type_info = {}
        group_screen_resolution_info = {}
        for screen in selected_screen:
            hasTF_card = self.judge_hasTF_card(screen['screenId'])
            screen_type, screen_resolution = self.get_screen_type_info(screen['groupId'])
            group_screen_type_info[screen['screenId']] = screen_type[screen['screenId']]
            group_screen_resolution_info[screen['screenId']] = screen_resolution[screen['screenId']]
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
        
        return screen_pictures, group_screen_type_info, group_screen_resolution_info

    def get_screen_type_info(self, group_id: int):
        screen_type_info = {}
        screen_resolution_info = {}
        api_sender1 = self.api_sender
        response = api_sender1.send_api(api_sender1.device_type + f"{str(group_id)}", data="", method="get")
        if response.status_code == 200 and response.json()["code"] == 20:
            screen_type_info_list = response.json()["data"]
            for screen in screen_type_info_list:
                screen_type_info[screen['screenId']] = "Linux" if screen['deviceType'] == 1 else "Android"
                screen_resolution_info[screen['screenId']] = screen.get("format")
            return screen_type_info, screen_resolution_info
        else:
            logging.error(response.text)
            sys.exit()
    
    def get_picture_info(self, screen_pictures: dict, screen_type_info: dict, screen_resolution_info: dict):
        """
        获取图片的文件大小和分辨率信息
        
        Args:
            screen_pictures (dict): 屏幕图片URL字典
            screen_type_info (dict): 屏幕类型信息
            screen_resolution_info (dict): 屏幕分辨率信息
        """
        has_android_screen = False
        
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
            if screen_type_info[screen] == "Android":
                has_android_screen = True
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
                        picture_resolution = f"{width} * {height}"
                        format_type = img.format if img.format else "未知"
                        mode = img.mode if img.mode else "未知"
                        def print_picture_info(msg: str = ""):
                            logging.error(msg)
                            # 格式化输出
                            print(f"图片URL: {picture_url}")
                            print(f"  - 文件大小: {picture_size_bytes:,} 字节 ({picture_size_mb:.2f} MB)")
                            print(f"  - 分辨率: {width} × {height} 像素")
                            print(f"  - 格式: {format_type}")
                            # print(f"  - 色彩模式: {mode}")
                            print("-" * 50)
                        args = {"screen": screen, "picture_url": picture_url, "file_size_mb": picture_size_mb, "screen_type": screen_type_info[screen], "screen_resolution": screen_resolution_info[screen], "picture_resolution": picture_resolution, "print_picture_info": print_picture_info}
                        if enable_pic_info.upper() == "Y":
                            print_picture_info()
                        for detect_item in self.detect_item:
                            self.detect_item[detect_item](args)
                    else:
                        logging.error(f"获取屏幕{screen}的图片{picture_url}失败\t状态码: {response.status_code}")
                        print(f"  ❌ 获取失败: {picture_url} (状态码: {response.status_code})")
                        
                except requests.exceptions.RequestException as e:
                    logging.error(f"网络请求失败: {picture_url}, 错误: {str(e)}")
                    print(f"  ❌ 网络请求失败: {picture_url}")
                    
                except Exception as e:
                    logging.error(f"处理图片时发生错误: {picture_url}, 错误: {str(e)}")
                    print(f"  ❌ 处理图片时发生错误: {picture_url}")
            logging.info(f"屏幕：{screen} 总计测试 {len(screen_pictures[screen])} 张图片")
        if self.test_flag:
            print("测试通过，所有图片大小均符合要求")
        else:
            print("测试不通过，请检查图片大小是否符合要求")
        
        if has_android_screen:
            if self.android_file_all_smaller_than_2:
                logging.warning("Android图片大小均小于2MB，可能压缩参数设置问题，请检查参数上限是否为6M")

            if self.android_picture_resolution_all_smaller_than_1920:
                logging.warning(f"Android图片分辨率均小于{self.max_short_size}，可能压缩参数设置问题，请检查参数上限是否为{self.max_short_size}")
        
    
    def detect_file_size_info(self, args: dict):
        
        try:
            file_size_mb = args["file_size_mb"]
            screen_type = args["screen_type"]
            print_picture_info = args["print_picture_info"]
            msg = f"屏幕{args["screen"]}的图片 {args["picture_url"]} 的大小为{file_size_mb:.2f} MB, 超过{2 if screen_type == "Linux" else 6}MB, 请检查"
            if screen_type == "Linux":
                if file_size_mb > 2:
                    self.test_flag = False
                    print_picture_info(msg)
            else:
                if file_size_mb > 6:
                    self.test_flag = False
                    print_picture_info(msg)
                if file_size_mb > 2:
                    self.android_file_all_smaller_than_2 = False
        except Exception as e:
            logging.error(f"处理图片时发生错误: {args['picture_url']}, 错误: {str(e)}")
            sys.exit()

    def detect_picture_resolution_item(self, args: dict):
        try:
            screen_resolution = args["screen_resolution"]
            print_picture_info = args["print_picture_info"]
            picture_resolution = args["picture_resolution"]
            msg = f"屏幕{args["screen"]}的图片 {args["picture_url"]} 的分辨率{picture_resolution}超过屏幕分辨率{screen_resolution}, 请检查"
            screen_type = args["screen_type"]
            # 如果图片分辨率超过屏幕分辨率，则测试失败
            picture_resolution_list = picture_resolution.split(" * ")
            picture_resolution_list = [int(i) for i in picture_resolution_list]
            screen_resolution_list = screen_resolution.split(" * ")
            screen_resolution_list = [int(i) for i in screen_resolution_list]
            if screen_type == "Linux":
                if max(picture_resolution_list) > max(screen_resolution_list):
                    self.test_flag = False
                    print("分辨率测试")
                    print_picture_info(msg)
                if min(picture_resolution_list) > min(screen_resolution_list):
                    self.test_flag = False
                    print("分辨率测试")
                    print_picture_info(msg)
            elif screen_type == "Android":
                if min(picture_resolution_list) > self.max_short_size:
                    self.test_flag = False
                    print("分辨率测试")
                    print_picture_info(msg)
                if max(picture_resolution_list) > self.max_short_size:
                    self.android_picture_resolution_all_smaller_than_1920 = False
            else:
                logging.error(f"屏幕类型错误: {screen_type}")
                sys.exit()
            
            
        except Exception as e:
            logging.error(f"处理图片时发生错误: {args['picture_url']}, 错误: {str(e)}")

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
    
    def get_album_list(self):
        api_sender1 = self.api_sender
        response = api_sender1.send_api(api_sender1.album_list, data="", method="get")
        if response.status_code == 200 and response.json()["code"] == 20:
            album_list = response.json()["data"]
            return album_list
        else:
            logging.error(response.text)
            sys.exit()
     
    def show_album_list(self):
        album_list = self.get_album_list()
        selected_album = None
        for index, album in enumerate(album_list):
            print(f"{index + 1}. {album['albumName']}")
        while True:
            option = input("请选择要检查的相册（序号，多选请用空格分隔）：")
            if option.isdigit():
                selected_album = album_list[int(option) - 1]
                break
            else:
                print("输入错误，请重新输入")
                continue
        return selected_album
    
    def get_album_picture_url(self):
        api_sender1 = self.api_sender
        selected_album = self.show_album_list()
        album_id = selected_album['albumId']
        api = api_sender1.album_picture_list + str(album_id) + "&pageNum=1&pageSize=10000"
        response = api_sender1.send_api(api=api, data="", method="get")
        if response.status_code == 200 and response.json()["code"] == 20:
            album_picture_url = response.json()["data"]['records']
            album_picture_url = [f"{self.protocol}://{self.file_domian}/{picture}" for picture in album_picture_url]
            return album_picture_url, selected_album['albumName']
        else:
            logging.error(response.text)

    def get_album_picture_info(self):
        album_picture_url, album_name = self.get_album_picture_url()
        while True:
            enable_pic_info = input("是否打印所有图片信息？（y/n）")
            if enable_pic_info == "y":
                break
            elif enable_pic_info == "n":
                break
            else:
                print("输入错误，请重新输入")
                continue
        for url in album_picture_url:
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    # 获取文件大小
                    picture_size_bytes = len(response.content)
                    picture_size_mb = picture_size_bytes / (1024 * 1024)
                    
                    # 获取图片分辨率
                    try:
                        img = Image.open(BytesIO(response.content))
                    except Exception as e:
                        location1 = (album_picture_url.index(url) + 1) // 3
                        location2 = (album_picture_url.index(url) + 1) % 3
                        logging.error(f"第{location1}行第{location2}列的图片，处理时发生错误: {url}, 错误: {str(e)}\t请手工确认该图片是否正常")
                        continue
                    width, height = img.size
                    picture_resolution = f"{width} * {height}"
                    format_type = img.format if img.format else "未知"
                    mode = img.mode if img.mode else "未知"
                    def print_picture_info(msg: str = ""):
                        logging.error(msg)
                        # 格式化输出
                        print(f"图片URL: {url}")
                        print(f"  - 文件大小: {picture_size_bytes:,} 字节 ({picture_size_mb:.2f} MB)")
                        print(f"  - 分辨率: {width} × {height} 像素")
                        print(f"  - 格式: {format_type}")
                        # print(f"  - 色彩模式: {mode}")
                        print("-" * 50)
                    args = {
                        "album_name": album_name, 
                        "picture_url": url, 
                        "file_size_mb": picture_size_mb, 
                        "picture_resolution": picture_resolution,
                        "print_picture_info": print_picture_info
                        }
                    if enable_pic_info.upper() == "Y":
                        print_picture_info()
                    for detect_item in self.alubm_detect_item:
                        self.alubm_detect_item[detect_item](args)
                else:
                    logging.error(f"获取相册{album_name}的图片{url}失败\t状态码: {response.status_code}")
                    print(f"  ❌ 获取失败: {url} (状态码: {response.status_code})")
                        
            except requests.exceptions.RequestException as e:
                logging.error(f"网络请求失败: {url}, 错误: {str(e)}")
                print(f"  ❌ 网络请求失败: {url}")
                
            except Exception as e:
                logging.error(f"处理图片时发生错误: {url}, 错误: {str(e)}")
                print(f"  ❌ 处理图片时发生错误: {url}")
        logging.info(f"相册：{album_name} 总计测试 {len(album_picture_url)} 张图片")
        if self.album_file_all_smaller_than_1:
            logging.warning("相册图片大小均小于1MB，可能压缩参数设置问题，请检查参数上限是否为2M")

    def detect_album_file_size_info(self, args: dict):
        try:
            file_size_mb = args["file_size_mb"]
            album_name = args["album_name"]
            print_picture_info = args["print_picture_info"]
            msg = f"相册【{album_name}】的图片 {args["picture_url"]} 的大小为{file_size_mb:.2f} MB, 超过{self.album_picture_max_size}MB, 请检查"
            if file_size_mb > self.album_picture_max_size:
                self.test_flag = False
                print_picture_info(msg)
            if file_size_mb > 1:
                self.album_file_all_smaller_than_1 = False          
        except Exception as e:
            logging.error(f"处理图片时发生错误: {args['picture_url']}, 错误: {str(e)}")
            sys.exit()
    
    def detect_album_picture_resolution_item(self, args: dict):
        try:
            picture_resolution = args["picture_resolution"]
            album_name = args["album_name"] 
            print_picture_info = args["print_picture_info"]
            msg = f"相册{album_name}的图片 {args["picture_url"]} 的分辨率{picture_resolution} 的短边超过{self.max_short_size}, 请检查"
            # 如果图片分辨率超过屏幕分辨率，则测试失败
            picture_resolution_list = picture_resolution.split(" * ")
            picture_resolution_list = [int(i) for i in picture_resolution_list]
            if min(picture_resolution_list) > self.max_short_size:
                self.test_flag = False
                print_picture_info(msg)
        except Exception as e:
            logging.error(f"处理图片时发生错误: {args['picture_url']}, 错误: {str(e)}")
            sys.exit()


    def main(self):
        def test_screen_picture():
            selected_screens = self.show_screen_menus()
            screen_pictures, group_screen_type_info, group_screen_resolution_info = self.get_screen_picture(selected_screens)
            
            # 显示详细的图片信息
            self.get_picture_info(screen_pictures, group_screen_type_info, group_screen_resolution_info)

        def test_album_picture():
            self.get_album_picture_info()
        
        while True:
            option = input("请选择要测试的类型：\n1. 屏幕图片 \n2. 相册图片\n请选择：")
            if option == "1":
                test_screen_picture()
            elif option == "2":
                test_album_picture()
            else:
                print("输入错误，请重新输入")
        # 显示统计信息
        # self.get_detailed_picture_stats(screen_pictures)

if __name__ == "__main__":
    tester = Upload_pic_size_test()
    tester.main()
