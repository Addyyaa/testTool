from telnet_connecter import Telnet_connector
from .log_factory import LogFactory
import re
import asyncio

class TelnetService:
    async def pack_log(self, ip, log_type, username="root", password="ya!2dkwy7-934^"):
        log_strategy = LogFactory.get_log_strategy(log_type)
        async with Telnet_connector(ip, username=username, password=password) as conn:
            # 进入日志目录
            result = await conn.send_command("cd /customer/log")
            print(f"已进入日志目录{ip}-{result}")
            
            # 执行打包命令
            tar_cmd = log_strategy.get_pack_cmd()
            print(f"执行打包命令: {tar_cmd}")
            tar_result = await conn.send_command(tar_cmd)
            print(f"打包命令输出: {tar_result}")
            
            # 检查打包结果，带超时控制
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    print(f"第 {attempt + 1} 次检查打包结果...")
                    response = await asyncio.wait_for(
                        conn.send_command("ls -l *.tar.gz"),
                        timeout=5.0
                    )
                    print(f"ls 原始输出: {response}")
                    
                    # 如果响应中包含登录提示，说明需要重新登录
                    if any(x in response.lower() for x in ["login:", "password:"]):
                        print("检测到登录提示，可能需要重新登录")
                        continue
                        
                    # 处理输出
                    lines = response.split('\n')
                    # 过滤掉空行和命令行
                    lines = [line for line in lines if line.strip() and not line.strip().startswith("ls")]
                    
                    if lines:
                        print(f"处理后的 ls 输出: {lines}")
                        # 检查是否存在目标文件
                        target_file = f"{log_strategy.name}.tar.gz"
                        if any(target_file in line for line in lines):
                            print(f"找到目标文件: {target_file}")
                            # 启动 HTTP 服务（忽略端口已被使用的错误）
                            http_result = await conn.send_command("httpd -p 88")
                            if "Address already in use" in http_result:
                                print("HTTP 服务已在运行")
                            else:
                                print(f"启动 HTTP 服务结果: {http_result}")
                            return
                    
                    print(f"未找到目标文件，等待1秒后重试...")
                    await asyncio.sleep(1)
                    
                except asyncio.TimeoutError:
                    print(f"命令执行超时，重试中... ({attempt + 1}/{max_retries})")
                    continue
                except Exception as e:
                    print(f"执行出错: {str(e)}")
                    raise
            
            # 如果重试次数用完还没找到文件
            raise Exception(f"打包失败: 在 {max_retries} 次尝试后未找到 {log_strategy.name}.tar.gz")
