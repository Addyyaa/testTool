import asyncio
import time

async def upload_file_to_qiniu(file_path):
    print(f"开始上传 {file_path}")
    await asyncio.sleep(2)  # 模拟 I/O 等待
    print(f"完成上传 {file_path}")

file_path_list = ["file1", "file2", "file3"]

for file_path in file_path_list:
    asyncio.run(upload_file_to_qiniu(file_path))