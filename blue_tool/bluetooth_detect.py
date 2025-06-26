import asyncio
from bleak import BleakScanner
import time
import logging

TARGET_ADDRESS = "C8:FE:0F:2C:7A:57"

async def monitor_ble_device():
    while True:
        try:
            print("正在扫描附近的 BLE 设备...")
            devices = await BleakScanner.discover(timeout=3.0)
            found = False
            for d in devices:
                if d.address.upper() == TARGET_ADDRESS:
                    logging.info(f"\r🎯 发现目标设备：{d.name} [{d.address}]")
                    found = True
            if not found:
                logging.info("目标设备未发现")
        except Exception as e:
            logging.error(f"扫描异常：{e}")
        
        await asyncio.sleep(5)  # 每隔5秒重复一次扫描

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
    asyncio.run(monitor_ble_device())
