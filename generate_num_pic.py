from PIL import Image, ImageDraw, ImageFont
import pillow_heif
import os


def generate_resolution_image(width, height):
    img_format = "PNG"
    # 创建黑色背景图片
    image = Image.new('RGB', (width, height), color='black')
    draw = ImageDraw.Draw(image)

    def caculate_correct_rs(width, height):
        short_side = min(width, height)
        if short_side > 1920:
            if width > height:
                width = 1920 * width / height
                height = 1920
            else:
                height = 1920 * height / width
                width = 1920
        return width, height
    

    width1, height1 = caculate_correct_rs(width, height)

    # 设置文字内容
    text = f"{width}x{height}\nThe compressed resolution shoud be\n{width1}x{height1}"
    # text = f"{img_format}\tPic"

    # 自动计算合适的字体大小
    def get_optimal_font_size(text, max_width, max_height):
        # 尝试加载系统字体，如果失败则使用默认字体
        try:
            font_path = "arial.ttf"
            # 从较大的字体开始尝试
            for font_size in range(min(max_width, max_height) // 5, 10, -1):
                try:
                    font = ImageFont.truetype(font_path, font_size)
                    text_bbox = draw.textbbox((0, 0), text, font=font)
                    text_width = text_bbox[2] - text_bbox[0]
                    text_height = text_bbox[3] - text_bbox[1]
                    
                    # 留出一些边距，确保文字不会贴边
                    margin = min(max_width, max_height) * 0.05
                    if text_width <= max_width - 2 * margin and text_height <= max_height - 2 * margin:
                        return font
                except:
                    continue
            # 如果所有尝试都失败，使用最小字体
            return ImageFont.truetype(font_path, 12)
        except:
            # 如果无法加载系统字体，使用默认字体
            return ImageFont.load_default()
    
    # 获取最优字体
    font = get_optimal_font_size(text, width, height)

    # 计算文字位置使其居中
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]

    x = (width - text_width) // 2
    y = (height - text_height) // 2

    # 绘制白色文字
    draw.text((x, y), text, fill='white', font=font)

    # 确保输出目录存在
    output_dir = "generate_output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 保存图片
    output_path = os.path.join(output_dir, f"{width}x{height}.{img_format}")
    if img_format.upper() == "HEIC":
        pillow_heif.from_pillow(image).save(output_path)
    else:
        image.save(output_path, format=img_format)
    return output_path


if __name__ == "__main__":
    try:
        width = int(input("请输入图片宽度: "))
        height = int(input("请输入图片高度: "))

        if width <= 0 or height <= 0:
            print("宽度和高度必须大于0")
        else:
            output_path = generate_resolution_image(width, height)
            print(f"图片已生成并保存到: {output_path}")
    except ValueError as e:
        print(f"请输入有效的数字\t{e}")
