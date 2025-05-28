import os
import paho.mqtt.client as mqtt
import json
from dotenv import load_dotenv
import logging
import threading
import time

logging.basicConfig(level=logging.DEBUG)

class PinturaDeviceMonitoring:
    def __init__(self):
        self.mqtt_username, self.mqtt_password = self.load_env()
        # self.server_ip = "cloud-service.austinelec.com"
        self.client_id = "PSd4117cL000289"
        self.server_ip = "139.224.192.36"
        self.server_port = 1883
        self.client = mqtt.Client(
            client_id=self.client_id,
            userdata=None,
            protocol=mqtt.MQTTv5,
            transport="tcp",
        )
        self.sub_topics = [
            "/screen/magicframe/cloud/setplaymode[-flat]/mf50",
            "/screen/magicframe/cloud/downloadpicture[-flat]/mf50",
            "/screen/magicframe/cloud/setbrightness[-flat]/mf50",
            "/screen/magicframe/cloud/setcolortemp[-flat]/mf50",
            "/screen/magicframe/cloud/turnon[-flat]/mf50",
            "/screen/magicframe/cloud/setsleepschedule[-flat]/mf50",
            "/screen/magicframe/cloud/playsync[-flat]/mf50",
            "/screen/magicframe/cloud/delvideo[-flat]/mf50",
            "/screen/magicframe/cloud/delpicture[-flat]/mf50", 
            "/screen/magicframe/cloud/upgrade[-flat]/mf50", 
            "/screen/magicframe/cloud/broadcast[-flat]/mf50",
            "/screen/magicframe/cloud/setscreengroupidandno[-flat]/mf50",
            "/screen/magicframe/cloud/setvolume[-flat]/mf50",
            "/screen/magicframe/cloud/setdirection[-flat]/mf50",
            "/screen/magicframe/cloud/reset[-flat]/mf50",
            "/screen/magicframe/cloud/settimezone[-flat]/mf50", 
        ]
        self.pub_topics = [
            "mf50/screen/cloud/heartbeat[-flat]/",
        ]


    def get_device_status(self):
        pass

    def subscribe_topic(self, topics):
        """
        支持单个topic字符串或topic字符串列表的订阅
        """
        if isinstance(topics, list):
            for topic in topics:
                result, mid = self.client.subscribe(topic)
                logging.info(f"正在订阅: {topic}, result={result}, mid={mid}")
        else:
            result, mid = self.client.subscribe(topics)
            logging.info(f"正在订阅: {topics}, result={result}, mid={mid}")

    def unsubscribe_topic(self, topic):
        self.client.unsubscribe(topic)

    def get_device_info(self):
        pass

    def load_env(self):
        load_dotenv()
        mqtt_username = os.getenv("MQTT_USERNAME")
        mqtt_password = os.getenv("MQTT_PASSWORD")
        print(f"Loaded username: {mqtt_username}, password: {mqtt_password}")  # 调试用
        return mqtt_username, mqtt_password

    def connect_mqtt(self):
        print(f"Connecting to MQTT broker with username: {self.mqtt_username}")
        try:
            self.client.username_pw_set(self.mqtt_username, self.mqtt_password)
            self.client.connect(self.server_ip, self.server_port, 60)
        except Exception as e:
            logging.error(f"MQTT connect error: {e}")
    
    def on_connect(self, client, userdata, flags, reasonCode, properties):
        if reasonCode == 0:
            logging.info("Connected to MQTT broker")
            self.subscribe_topic(self.sub_topics)
        else:
            logging.error(f"Failed to connect, return code {reasonCode}\n")
    
    def on_message(self, client, userdata, msg):
        logging.info(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")
    
    def on_subscribe(self, client, userdata, mid, granted_qos, properties=None):
        logging.info(f"订阅成功: mid={mid}, granted_qos={granted_qos}")

    def create_mqtt_client(self):
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_subscribe = self.on_subscribe
        self.connect_mqtt()

    def publish_message(self, topic, payload, qos=2, retain=False):
        """
        发布消息到指定topic
        """
        result = self.client.publish(topic, payload, qos, retain)
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            logging.info(f"消息已发布到 {topic}: {payload}")
        else:
            logging.error(f"消息发布失败: {result}")

    def start_heartbeat(self, interval=5):
        """
        定时发布心跳报文
        """
        msg = {
            "status": 1,
            "time": 5,
            "version": "2.00.32.0",
            "ip": "192.168.1.100",
            "horizpixel": 1920,
            "vertpixel": 1080,
            "playmode": 1,
            "brightness": 1,
            "colortemp": 1,
            "SN": 2,
            "carouseltime": 3,
            "volume": 50
        }
        def heartbeat_loop():
            while True:
                for topic in self.pub_topics:
                    full_topic = topic + self.client_id
                    self.publish_message(full_topic, json.dumps(msg))
                time.sleep(interval)
        t = threading.Thread(target=heartbeat_loop, daemon=True)
        t.start()

    def main(self):
        self.create_mqtt_client()
        self.start_heartbeat(interval=5)  # 启动心跳定时器
        self.client.loop_forever()

if __name__ == "__main__":
    pintura_device_monitoring = PinturaDeviceMonitoring()
    pintura_device_monitoring.main()
