from PIL import Image, ImageDraw, ImageFont
import os

def generate_resolution_image(width, height):
    # 创建黑色背景图片
    image = Image.new('RGB', (width, height), color='black')
    draw = ImageDraw.Draw(image)
    
    # 设置文字内容
    text = f"{width}x{height}"
    
    # 尝试加载系统字体，如果失败则使用默认字体
    try:
        font = ImageFont.truetype("arial.ttf", min(width, height) // 10)
    except:
        font = ImageFont.load_default()
    
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
    output_path = os.path.join(output_dir, f"{width}x{height}.png")
    image.save(output_path)
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
    except ValueError:
        print("请输入有效的数字")
