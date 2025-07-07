from ..api_sender import Api_sender
import logging

logger = logging.getLogger(__name__)

class SwitchDisplayMode:
    def __init__(self, account: str, password: str, host: str, port: str):
        self.api_sender = Api_sender(account, password, host, port)
        self.account = account
        self.password = password
    def switch_display_mode(self, display_mode: str, screen_id: str):
        """
        1. 图片轮播
        2. 图片独播
        3. 时钟
        4. 万年历
        5. 序号
        6. 重启他界面返回
        7. 视频轮播
        8. 视频独播
        9. 从其他显示模式回到视频模式
        11. 图片随机播放
        12. 视频随机播放
        13. 混播随机播放
        """
        data = {
            "displayMode": display_mode,
            "screenId": screen_id
        }
        result = self.api_sender.send_api(self.api_sender.display, data=data, method="post")
        if result is not None:
            try:
                resp_json = result.json()
                if resp_json.get("code") == 200:
                    if resp_json.get("code") == 20:
                        logger.info(f"switch_display_mode success")
                    else:
                        logger.error(f"switch_display_mode failed\t{result.text}")
                else:
                    logger.error(f"switch_display_mode failed\t{result.text}\nbody:{data}")
            except Exception as e:
                logger.error(f"解析响应失败: {e}\t{getattr(result, 'text', '')}")
        else:
            logger.error(f"switch_display_mode failed, no response")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d ===> %(message)s')
    switch_display_mode = SwitchDisplayMode(account="test2@tester.com", password="sf123123", host="139.224.192.36", port="8082")
    switch_display_mode.switch_display_mode(display_mode="7", screen_id="PinturaV2test00001")