from PIL import Image
import random
import numpy as np
from tkinter import filedialog
import os


def corrupt_image(image_path, corruption_percentage=0.1):
    """
    破坏指定图片的像素

    Args:
        image_path (str): 图片文件路径
        corruption_percentage (float): 破坏像素的百分比，默认10%

    Returns:
        bool: 操作是否成功
    """
    try:
        # 检查文件是否存在
        if not os.path.exists(image_path):
            print(f"错误：文件 {image_path} 不存在")
            return False

        # 打开图片
        im = Image.open(image_path)
        data = np.array(im)

        # 获取图像尺寸
        height, width = data.shape[:2]
        total_pixels = height * width

        # 计算要破坏的像素数量
        num_pix_to_corrupt = int(total_pixels * corruption_percentage)

        # 确保破坏数量不超过总像素数
        if num_pix_to_corrupt > total_pixels:
            num_pix_to_corrupt = total_pixels

        print(f"图像尺寸: {width} x {height}")
        print(f"总像素数: {total_pixels}")
        print(f"将破坏像素数: {num_pix_to_corrupt}")

        # 生成随机像素索引（确保在有效范围内）
        indices = random.sample(range(total_pixels), num_pix_to_corrupt)

        # 破坏像素
        for idx in indices:
            row = idx // width
            col = idx % width

            # 添加边界检查
            if 0 <= row < height and 0 <= col < width:
                # 根据图像类型设置像素值
                if len(data.shape) == 3:  # 彩色图像
                    channels = data.shape[2]
                    if channels == 3:  # RGB
                        data[row, col] = [
                            random.randint(0, 255),
                            random.randint(0, 255),
                            random.randint(0, 255),
                        ]
                    elif channels == 4:  # RGBA
                        data[row, col] = [
                            random.randint(0, 255),
                            random.randint(0, 255),
                            random.randint(0, 255),
                            255,  # 保持不透明度
                        ]
                else:  # 灰度图像
                    data[row, col] = random.randint(0, 255)

        # 创建破坏后的图像
        corrupted_img = Image.fromarray(data)

        # 确保输出目录存在
        output_dir = "image_tool/generate_file"
        os.makedirs(output_dir, exist_ok=True)

        # 生成输出文件名
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        output_path = os.path.join(output_dir, f"{base_name}_corrupted.jpg")

        # 保存图像
        corrupted_img.save(output_path)
        print(f"破坏后的图像已保存到: {output_path}")

        return True

    except Exception as e:
        print(f"处理图像时发生错误: {str(e)}")
        return False


def main():
    """主函数"""
    print("图片破坏工具")
    print("=" * 30)

    # 选择图片文件
    image_path = filedialog.askopenfilename(
        defaultextension=".jpg",
        filetypes=[("图像文件", "*.jpg *.jpeg *.png *.bmp *.gif *.webp")],
        title="请选择要破坏的图片",
    )

    if not image_path:
        print("未选择文件，程序退出")
        return

    print(f"选择的图片: {image_path}")

    # 询问破坏百分比
    try:
        percentage = float(
            input("请输入要破坏的像素百分比 (0.1-1.0，默认0.1): ") or "0.1"
        )
        if not (0.1 <= percentage <= 1.0):
            print("百分比必须在0.1到1.0之间，使用默认值0.1")
            percentage = 0.1
    except ValueError:
        print("输入无效，使用默认值0.1")
        percentage = 0.1

    # 执行图像破坏
    if corrupt_image(image_path, percentage):
        print("图像破坏完成！")
    else:
        print("图像破坏失败！")


if __name__ == "__main__":
    main()
