import subprocess

# 假设 'example.exe' 是你想运行的可执行文件
result = subprocess.run(['E:/OA3.0在线烧录/InjectionDPK_WithMSCserverOnline/ReadDPK-PKID.bat'], stdout=subprocess.PIPE, 
                        stderr=subprocess.PIPE, text=True)

# 打印标准输出和标准错误
print('Standard Output:', result.stdout)
print('Standard Error:', result.stderr)