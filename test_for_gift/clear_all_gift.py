import sys
import logging
import requests
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from api_sender import Api_sender


logger = logging.getLogger(__name__)


class Clear_all_gift:
    def __init__(self, account: str, password: str, host: str, port: str):
        self.account = account
        self.password = password
        self.api_sender = Api_sender(account, password, host, port)
        self.token = self.api_sender.get_token()
        
    def clear_single_gift(self, gift_code: str):
        data = {
            "id": gift_code,
        }
        result = requests.post(self.api_sender.gift_del, params=data, headers={"X-TOKEN": self.token})
        logger.info(f"clear_single_gift: {result.text}")
        return result
    
    def clear_all_gift(self):
        result = self.api_sender.send_api(self.api_sender.gift_list_receive, {}, "post")
        gift_list = []
        if result and result.status_code == 200:
            result_json = result.json()
            if result_json["code"] == 20:
                for _ in result_json["data"]:
                    gift_list.append(_["id"])
                logger.info(f"clear_all_gift: {gift_list}")
            else:
                logger.error(f"clear_all_gift: {result_json['message']}")
                sys.exit(1)
        else:
            logger.error(f"clear_all_gift: {result.text}")
            sys.exit(1)
        
        if gift_list:
            for gift_code in gift_list:
                self.clear_single_gift(gift_code)       
            logger.info("删除完毕！")                                                                              


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d ===> %(message)s')
    clear_all_gift = Clear_all_gift("2698567570@qq.com", "sf123123", "cloud-service.austinelec.com", "8080")
    clear_all_gift.clear_all_gift()