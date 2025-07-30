import asyncio
from bleak import BleakScanner, BleakClient
from bleak.exc import BleakError  # Import BleakError from bleak.exc

# 目标设备的 MAC 地址
DEVICE_ADDRESS = "D4:8A:3B:88:97:8A"
DEVICE_NAME = "Pintura-blt-L000289"

async def scan_and_connect():
    try:
        # 扫描设备
        print(f"正在扫描设备 {DEVICE_ADDRESS} ({DEVICE_NAME})...")
        devices = await BleakScanner.discover(timeout=10.0)
        target_device = None
        for device in devices:
            if device.address == DEVICE_ADDRESS:
                target_device = device
                print(f"找到设备: {device.name} ({device.address})")
                break

        if not target_device:
            print(f"未找到设备 {DEVICE_ADDRESS}")
            return

        # 连接到设备
        async with BleakClient(target_device.address, timeout=20.0) as client:
            print(f"已连接到 {target_device.name} ({target_device.address})")

            # 获取并打印服务和特性
            print("\n获取 GATT 服务和特性...")
            services = await client.get_services()
            if not services:
                print("未发现任何 GATT 服务")
                return

            for service in services:
                print(f"\n服务 UUID: {service.uuid}")
                print(f"  描述: {service.description}")
                for characteristic in service.characteristics:
                    print(f"  特性 UUID: {characteristic.uuid}")
                    print(f"    属性: {characteristic.properties}")
                    print(f"    描述: {characteristic.description}")
                    # 检查特性是否支持读取
                    if "read" in characteristic.properties:
                        try:
                            value = await client.read_gatt_char(characteristic.uuid)
                            print(f"    值: {value}")
                        except Exception as e:
                            print(f"    值: 读取失败 - {e}")
                    else:
                        print(f"    值: 不支持读取")

    except BleakError as e:
        print(f"BLE 错误: {e}")
    except Exception as e:
        print(f"发生错误: {e}")

# 运行异步函数
if __name__ == "__main__":
    asyncio.run(scan_and_connect())