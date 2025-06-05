from PIL import Image
import numpy as np
import os

# 设置目标短边像素数
SHORT_SIDE = 1920
# 设置宽高比（例如16:9，可根据需要调整）
ASPECT_RATIO = 16 / 9
# 目标文件大小（50MB）
TARGET_SIZE_MB = 50
TARGET_SIZE_BYTES = TARGET_SIZE_MB * 1024 * 1024

# 计算长边像素数
if ASPECT_RATIO >= 1:
    # 宽图：宽度是长边，高度是短边
    width = int(SHORT_SIDE * ASPECT_RATIO)
    height = SHORT_SIDE
else:
    # 高图：高度是长边，宽度是短边
    width = SHORT_SIDE
    height = int(SHORT_SIDE / ASPECT_RATIO)

# 初始分辨率可能不足以达到50MB，动态调整分辨率
scale_factor = 1
file_size = 0
while file_size < TARGET_SIZE_BYTES:
    # 计算当前分辨率
    curr_width = int(width * scale_factor)
    curr_height = int(height * scale_factor)
    
    # 创建随机像素数组（RGB图像）
    # 使用随机数据避免压缩优化
    image_data = np.random.randint(0, 255, (curr_height, curr_width, 3), dtype=np.uint8)
    
    # 创建Pillow图像
    image = Image.fromarray(image_data, 'RGB')
    
    # 保存为PNG（无损格式，避免压缩）
    output_path = f"output_image_{curr_width}x{curr_height}.png"
    image.save(output_path, compress_level=0)  # compress_level=0 禁用压缩
    
    # 检查文件 inde大小
    file_size = os.path.getsize(output_path)
    
    # 如果文件大小不足，增加分辨率
    if file_size < TARGET_SIZE_BYTES:
        scale_factor += 0.5
        print(f"文件大小 {file_size / 1024 / 1024:.2f}MB 小于目标，增加分辨率到 {int(width * scale_factor)}x{int(height * scale_factor)}")
    else:
        print(f"生成图片成功：{output_path}")
        print(f"分辨率：{curr_width}x{curr_height}")
        print(f"文件大小：{file_size / 1024 / 1024:.2f}MB")
        break