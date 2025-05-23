def calculate_resolution(width, height):
    """
    计算等比例缩放后的最大分辨率，确保不超过1920*1200
    :param width: 原始宽度
    :param height: 原始高度
    :return: 缩放后的宽度和高度
    """
    max_width = 1920
    max_height = 1200
    
    # 计算宽高比
    aspect_ratio = width / height
    
    # 计算缩放后的尺寸
    if width > max_width or height > max_height:
        # 如果宽度超过最大宽度，按宽度缩放
        if width / max_width > height / max_height:
            new_width = max_width
            new_height = int(max_width / aspect_ratio)
        # 如果高度超过最大高度，按高度缩放
        else:
            new_height = max_height
            new_width = int(max_height * aspect_ratio)
    else:
        new_width = width
        new_height = height
        
    return new_width, new_height

def main():
    try:
        # 获取用户输入
        width = int(input("请输入图片宽度: "))
        height = int(input("请输入图片高度: "))
        
        # 计算新分辨率
        new_width, new_height = calculate_resolution(width, height)
        
        # 输出结果
        print(f"\n原始分辨率: {width}x{height}")
        print(f"缩放后分辨率: {new_width}x{new_height}")
        print(f"宽高比: {width/height:.2f}")
        
    except ValueError:
        print("错误：请输入有效的数字！")
    except ZeroDivisionError:
        print("错误：高度不能为0！")
19
if __name__ == "__main__":
    main()
