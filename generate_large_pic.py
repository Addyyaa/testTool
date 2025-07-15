from PIL import Image, ImageDraw, ImageFont
import numpy as np
import os
import math

def get_user_input():
    """获取用户输入参数"""
    print("=== 智能图片生成器 ===")
    print("请输入目标文件大小，程序将自动调整分辨率和噪声：")
    
    # 获取目标文件大小
    while True:
        try:
            file_size_mb = float(input("请输入目标文件大小（MB）: "))
            if file_size_mb <= 0:
                print("文件大小必须大于0，请重新输入")
                continue
            break
        except ValueError:
            print("请输入有效的数字")
    
    # 获取分辨率上限
    print("\n分辨率限制设置：")
    print("程序将优先通过调整分辨率来达到目标文件大小（保证最佳图片质量）")
    print("只有在分辨率达到上限时才会添加噪声")
    
    max_resolution = None
    while True:
        try:
            resolution_input = input("请输入分辨率上限（例如：1920x1080，留空表示无限制）: ").strip()
            if resolution_input == "":
                max_resolution = None
                print("✅ 设置为无分辨率限制")
                break
            elif "x" in resolution_input.lower():
                parts = resolution_input.lower().split("x")
                if len(parts) == 2:
                    max_width = int(parts[0].strip())
                    max_height = int(parts[1].strip())
                    if max_width > 0 and max_height > 0:
                        max_resolution = (max_width, max_height)
                        print(f"✅ 设置分辨率上限为：{max_width}x{max_height}")
                        break
                    else:
                        print("分辨率必须大于0，请重新输入")
                else:
                    print("请使用正确的格式（例如：1920x1080）")
            else:
                print("请使用正确的格式（例如：1920x1080）或留空")
        except ValueError:
            print("请输入有效的分辨率格式")
    
    # 获取图片格式选择
    print("\n图片格式选择：")
    print("1. PNG - 无损压缩，适合图标和简单图片")
    print("2. JPG - 有损压缩，适合照片和复杂图片")
    print("3. BMP - 无压缩，文件较大但质量最高")
    print("4. 智能选择 - 自动选择最适合的格式（推荐）")
    
    while True:
        try:
            format_choice = input("请选择图片格式（1-4，默认为4）: ").strip()
            if format_choice == "" or format_choice == "4":
                selected_format = "auto"
                break
            elif format_choice == "1":
                selected_format = "png"
                break
            elif format_choice == "2":
                selected_format = "jpg"
                break
            elif format_choice == "3":
                selected_format = "bmp"
                break
            else:
                print("请输入1-4之间的数字")
        except ValueError:
            print("请输入有效的选择")
    
    return file_size_mb, max_resolution, selected_format

def calculate_optimal_dimensions_for_size(target_size_bytes, format_type='png'):
    """根据目标文件大小精确计算最佳分辨率（无噪声）"""
    # 基于经验公式：PNG文件大小 ≈ 宽度 × 高度 × 3 × 压缩比
    if format_type == 'png':
        compression_ratio = 0.15  # PNG无噪声时压缩率较高
    elif format_type == 'jpg':
        compression_ratio = 0.12  # JPEG压缩率
    else:  # BMP
        compression_ratio = 1.0   # 无压缩
    
    # 计算像素总数
    total_pixels = target_size_bytes / (3 * compression_ratio)
    
    # 假设16:9的宽高比作为默认
    aspect_ratio = 16 / 9
    
    # 计算高度和宽度
    height = int(math.sqrt(total_pixels / aspect_ratio))
    width = int(height * aspect_ratio)
    
    # 确保最小分辨率
    width = max(width, 100)
    height = max(height, 100)
    
    return width, height

def estimate_clean_file_size(width, height, format_type='png', quality=None):
    """估算无噪声图片的文件大小（字节）"""
    base_size = width * height * 3  # RGB 3字节
    
    if format_type == 'png':
        # PNG无噪声时有很好的压缩率
        compression_ratio = 0.12 + (width * height / 1000000) * 0.03  # 分辨率越高压缩率稍微降低
    elif format_type == 'jpg':
        # JPEG压缩率基于质量
        if quality:
            compression_ratio = 0.05 + (quality / 100) * 0.15  # 质量越高文件越大
        else:
            compression_ratio = 0.1  # 默认质量
    else:  # BMP
        compression_ratio = 1.0  # 无压缩
    
    return int(base_size * compression_ratio)

def binary_search_resolution(target_size_bytes, max_resolution, format_type='png', tolerance=0.05):
    """二分查找最佳分辨率"""
    print(f"🔍 使用二分查找算法寻找最佳分辨率...")
    
    # 设置搜索范围
    min_width, min_height = 100, 100
    if max_resolution:
        max_width, max_height = max_resolution
    else:
        # 如果无限制，设置一个合理的最大值
        max_width, max_height = 8000, 8000
    
    best_result = None
    best_diff = float('inf')
    iteration = 0
    max_iterations = 15  # 二分查找最多15次就能找到很好的结果
    
    tolerance_bytes = target_size_bytes * tolerance
    
    while iteration < max_iterations and min_width <= max_width and min_height <= max_height:
        iteration += 1
        
        # 计算中间值
        mid_width = (min_width + max_width) // 2
        mid_height = (min_height + max_height) // 2
        
        # 保持16:9比例
        aspect_ratio = 16 / 9
        mid_height = int(mid_width / aspect_ratio)
        
        print(f"  第{iteration}次搜索: {mid_width}x{mid_height}")
        
        # 估算文件大小
        estimated_size = estimate_clean_file_size(mid_width, mid_height, format_type)
        diff = abs(estimated_size - target_size_bytes)
        
        print(f"  估算大小: {estimated_size / 1024 / 1024:.2f}MB, 误差: {((estimated_size - target_size_bytes) / target_size_bytes * 100):+.1f}%")
        
        # 记录最佳结果
        if diff < best_diff:
            best_diff = diff
            best_result = {
                'width': mid_width,
                'height': mid_height,
                'estimated_size': estimated_size,
                'diff': diff
            }
        
        # 检查是否满足容忍度
        if diff <= tolerance_bytes:
            print(f"  ✅ 找到满足条件的分辨率：{mid_width}x{mid_height}")
            break
        
        # 调整搜索范围
        if estimated_size < target_size_bytes:
            # 文件太小，需要增加分辨率
            min_width = mid_width + 1
            min_height = mid_height + 1
        else:
            # 文件太大，需要减少分辨率
            max_width = mid_width - 1
            max_height = mid_height - 1
    
    return best_result

def create_base_image(width, height):
    """创建基础图片，显示分辨率信息"""
    # 创建白色背景
    image = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(image)
    
    # 尝试使用系统字体
    try:
        # 计算合适的字体大小
        font_size = max(width, height) // 20
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        try:
            font_size = max(width, height) // 20
            font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", font_size)
        except:
            font = ImageFont.load_default()
    
    # 绘制分辨率信息
    text = f"{width}x{height}"
    
    # 获取文本尺寸
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # 居中绘制文本
    x = (width - text_width) // 2
    y = (height - text_height) // 2
    
    draw.text((x, y), text, fill='black', font=font)
    
    return image

def add_smart_noise(image, noise_level):
    """智能添加噪声"""
    if noise_level <= 0:
        return image
    
    # 转换为numpy数组
    img_array = np.array(image)
    
    if noise_level <= 100:
        # 常规噪声
        noise = np.random.randint(-noise_level, noise_level + 1, img_array.shape, dtype=np.int16)
        noisy_array = np.clip(img_array.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    else:
        # 高级噪声：添加随机像素块
        noisy_array = img_array.copy()
        num_blocks = min(noise_level - 100, 1000)  # 限制块数量
        
        for _ in range(num_blocks):
            y = np.random.randint(0, img_array.shape[0])
            x = np.random.randint(0, img_array.shape[1])
            block_size = np.random.randint(1, 8)
            
            y_end = min(y + block_size, img_array.shape[0])
            x_end = min(x + block_size, img_array.shape[1])
            
            # 添加随机颜色块
            noisy_array[y:y_end, x:x_end] = np.random.randint(0, 256, (y_end-y, x_end-x, 3), dtype=np.uint8)
    
    return Image.fromarray(noisy_array)

def find_optimal_format(image, target_size_bytes, preferred_format="auto"):
    """找到最佳文件格式和参数"""
    best_result = None
    best_diff = float('inf')
    
    # 根据用户选择确定策略
    if preferred_format == "png":
        strategies = [('png', 0), ('png', 1), ('png', 6), ('png', 9)]
    elif preferred_format == "jpg":
        strategies = [('jpg', 95), ('jpg', 85), ('jpg', 75), ('jpg', 65), ('jpg', 55), ('jpg', 45), ('jpg', 35), ('jpg', 25), ('jpg', 15), ('jpg', 5)]
    elif preferred_format == "bmp":
        strategies = [('bmp', None)]
    else:  # auto - 智能选择
        strategies = [
            # PNG策略（优先）
            ('png', 0), ('png', 1), ('png', 6), ('png', 9),
            # JPEG策略
            ('jpg', 85), ('jpg', 75), ('jpg', 65), ('jpg', 55), ('jpg', 45), ('jpg', 35), ('jpg', 25),
            # BMP策略（最后）
            ('bmp', None)
        ]
    
    for format_type, param in strategies:
        try:
            temp_path = f"temp_optimal_{format_type}_{param}.{format_type}"
            
            if format_type == 'png':
                image.save(temp_path, format='PNG', compress_level=param)
            elif format_type == 'jpg':
                image.save(temp_path, format='JPEG', quality=param)
            elif format_type == 'bmp':
                image.save(temp_path, format='BMP')
            
            file_size = os.path.getsize(temp_path)
            diff = abs(file_size - target_size_bytes)
            
            if diff < best_diff:
                best_diff = diff
                best_result = {
                    'format': format_type,
                    'param': param,
                    'size': file_size,
                    'diff': diff,
                    'image': image  # 保存图像对象而不是文件路径
                }
            
            # 立即删除临时文件
            try:
                os.remove(temp_path)
            except:
                pass
                
        except Exception as e:
            print(f"格式 {format_type} 测试失败: {e}")
            continue
    
    return best_result

def super_smart_generate_v2(target_size_bytes, max_resolution=None, preferred_format="auto", max_iterations=10):
    """新版超强智能生成算法 - 优先分辨率调整，再考虑噪声"""
    print(f"\n🚀 启动新版超强智能算法...")
    print(f"🎯 目标文件大小: {target_size_bytes / 1024 / 1024:.2f}MB")
    
    if max_resolution:
        print(f"📐 分辨率上限: {max_resolution[0]}x{max_resolution[1]}")
    else:
        print(f"📐 分辨率限制: 无限制")
        
    if preferred_format != "auto":
        print(f"🎨 指定格式: {preferred_format.upper()}")
    else:
        print(f"🎨 格式策略: 智能自动选择")
    
    # 阶段1：确定最佳格式
    print(f"\n=== 阶段1：确定最佳格式 ===")
    format_to_use = preferred_format if preferred_format != "auto" else "png"  # 默认用PNG估算
    
    # 阶段2：智能分辨率调整（实际测试）
    print(f"\n=== 阶段2：智能分辨率调整（实际测试策略）===")
    
    # 从一个合理的初始分辨率开始
    base_width, base_height = calculate_optimal_dimensions_for_size(target_size_bytes, format_to_use)
    print(f"🧠 初始预估分辨率: {base_width}x{base_height}")
    
    # 智能分辨率搜索
    best_result = None
    best_diff = float('inf')
    tolerance = target_size_bytes * 0.05  # 5%容忍度
    
    # 搜索策略：从预估分辨率开始，根据实际结果调整
    scale_factors = [0.5, 0.7, 0.85, 1.0, 1.2, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0]
    
    iteration = 0
    for scale in scale_factors:
        iteration += 1
        if iteration > max_iterations:
            break
            
        curr_width = int(base_width * scale)
        curr_height = int(base_height * scale)
        
        # 检查分辨率限制
        if max_resolution:
            if curr_width > max_resolution[0] or curr_height > max_resolution[1]:
                print(f"  ⚠️ 分辨率 {curr_width}x{curr_height} 超过限制，跳过")
                continue
        
        print(f"\n🔍 第{iteration}次尝试: {curr_width}x{curr_height}")
        
        # 创建无噪声图片并实际测试
        clean_image = create_base_image(curr_width, curr_height)
        format_result = find_optimal_format(clean_image, target_size_bytes, preferred_format)
        
        if format_result:
            print(f"  📁 实际文件大小: {format_result['size'] / 1024 / 1024:.2f}MB")
            print(f"  📊 误差: {((format_result['size'] - target_size_bytes) / target_size_bytes * 100):+.1f}%")
            
            # 记录最佳结果
            if format_result['diff'] < best_diff:
                best_diff = format_result['diff']
                best_result = {
                    'width': curr_width,
                    'height': curr_height,
                    'image': clean_image,
                    'format': format_result['format'],
                    'param': format_result['param'],
                    'size': format_result['size'],
                    'diff': format_result['diff'],
                    'noise_level': 0
                }
            
            # 如果找到满足条件的分辨率
            if format_result['diff'] <= tolerance:
                final_path = f"output_image_{curr_width}x{curr_height}_clean.{format_result['format']}"
                
                # 保存无噪声图片
                if format_result['format'] == 'png':
                    clean_image.save(final_path, format='PNG', compress_level=format_result['param'])
                elif format_result['format'] == 'jpg':
                    clean_image.save(final_path, format='JPEG', quality=format_result['param'])
                elif format_result['format'] == 'bmp':
                    clean_image.save(final_path, format='BMP')
                
                print(f"\n✅ 分辨率调整成功！生成完美图片：{final_path}")
                print(f"📐 最终分辨率：{curr_width}x{curr_height}")
                print(f"🎵 噪声级别：0（无噪声）")
                print(f"📁 文件大小：{format_result['size'] / 1024 / 1024:.2f}MB")
                print(f"🎯 目标大小：{target_size_bytes / 1024 / 1024:.2f}MB")
                print(f"📊 精确度：{((format_result['size'] - target_size_bytes) / target_size_bytes * 100):+.1f}%")
                print(f"🎨 最佳格式：{format_result['format'].upper()}")
                print(f"🔄 总计尝试次数：{iteration}")
                
                return final_path
    
    # 如果通过分辨率调整无法达到目标（通常是因为分辨率限制）
    if not best_result:
        print("❌ 无法找到合适的分辨率")
        return None
    
    print(f"\n=== 分辨率调整阶段完成 ===")
    print(f"🎯 最佳分辨率: {best_result['width']}x{best_result['height']}")
    print(f"📁 无噪声文件大小: {best_result['size'] / 1024 / 1024:.2f}MB")
    print(f"📊 当前误差: {((best_result['size'] - target_size_bytes) / target_size_bytes * 100):+.1f}%")
    
    # 判断是否需要添加噪声
    need_noise = False
    reason = ""
    
    if max_resolution:
        # 有分辨率限制的情况
        max_width, max_height = max_resolution
        if (best_result['width'] >= max_width * 0.95 or best_result['height'] >= max_height * 0.95) and best_result['diff'] > tolerance:
            need_noise = True
            reason = "已接近分辨率上限"
    else:
        # 无分辨率限制的情况 - 只有在尝试了足够大的分辨率仍无法达到目标时才使用噪声
        if best_result['size'] < target_size_bytes and iteration >= max_iterations:
            need_noise = True
            reason = "已尝试最大搜索范围"
        elif best_result['size'] > target_size_bytes:
            # 如果文件过大，可以考虑微调噪声（但这种情况很少）
            need_noise = True
            reason = "需要微调减小文件大小"
    
    if not need_noise:
        # 无分辨率限制且还有搜索空间，应该继续增加分辨率
        if not max_resolution and best_result['size'] < target_size_bytes:
            print(f"\n=== 继续扩大分辨率搜索范围 ===")
            print(f"💡 无分辨率限制，继续增加分辨率来达到目标...")
            
            # 扩大搜索范围
            extended_scales = [6.0, 8.0, 10.0, 15.0, 20.0]
            
            for scale in extended_scales:
                iteration += 1
                curr_width = int(base_width * scale)
                curr_height = int(base_height * scale)
                
                # 设置合理的最大分辨率限制（防止过度消耗资源）
                if curr_width > 15000 or curr_height > 15000:
                    print(f"  ⚠️ 分辨率 {curr_width}x{curr_height} 过大，停止搜索")
                    break
                
                print(f"\n🔍 第{iteration}次尝试（扩展搜索）: {curr_width}x{curr_height}")
                
                clean_image = create_base_image(curr_width, curr_height)
                format_result = find_optimal_format(clean_image, target_size_bytes, preferred_format)
                
                if format_result:
                    print(f"  📁 实际文件大小: {format_result['size'] / 1024 / 1024:.2f}MB")
                    print(f"  📊 误差: {((format_result['size'] - target_size_bytes) / target_size_bytes * 100):+.1f}%")
                    
                    if format_result['diff'] < best_diff:
                        best_diff = format_result['diff']
                        best_result = {
                            'width': curr_width,
                            'height': curr_height,
                            'image': clean_image,
                            'format': format_result['format'],
                            'param': format_result['param'],
                            'size': format_result['size'],
                            'diff': format_result['diff'],
                            'noise_level': 0
                        }
                    
                    if format_result['diff'] <= tolerance:
                        final_path = f"output_image_{curr_width}x{curr_height}_clean.{format_result['format']}"
                        
                        if format_result['format'] == 'png':
                            clean_image.save(final_path, format='PNG', compress_level=format_result['param'])
                        elif format_result['format'] == 'jpg':
                            clean_image.save(final_path, format='JPEG', quality=format_result['param'])
                        elif format_result['format'] == 'bmp':
                            clean_image.save(final_path, format='BMP')
                        
                        print(f"\n✅ 扩展搜索成功！生成完美图片：{final_path}")
                        print(f"📐 最终分辨率：{curr_width}x{curr_height}")
                        print(f"🎵 噪声级别：0（无噪声）")
                        print(f"📁 文件大小：{format_result['size'] / 1024 / 1024:.2f}MB")
                        print(f"🎯 目标大小：{target_size_bytes / 1024 / 1024:.2f}MB")
                        print(f"📊 精确度：{((format_result['size'] - target_size_bytes) / target_size_bytes * 100):+.1f}%")
                        print(f"🎨 最佳格式：{format_result['format'].upper()}")
                        print(f"🔄 总计尝试次数：{iteration}")
                        
                        return final_path
            
            # 如果扩展搜索后仍无法达到目标，才考虑噪声
            need_noise = True
            reason = "扩展搜索后仍无法达到目标"
    
    # 阶段3：如果确实需要添加噪声
    if need_noise:
        print(f"\n=== 阶段3：添加噪声调整 ===")
        print(f"💡 {reason}，开始添加噪声来调整文件大小...")
        
        target_width = best_result['width']
        target_height = best_result['height']
        clean_image = best_result['image']
        
        # 确定噪声调整方向
        if best_result['size'] < target_size_bytes:
            print(f"📈 需要增加噪声来增大文件")
            noise_range = [0, 25, 50, 100, 150, 200, 300, 500]
        else:
            print(f"📉 需要减少噪声或微调")
            noise_range = [0, 10, 25]
        
        best_noise_result = None
        best_noise_diff = float('inf')
        
        for noise_level in noise_range:
            print(f"  🔧 测试噪声级别: {noise_level}")
            
            # 添加噪声
            noisy_image = add_smart_noise(clean_image, noise_level)
            
            # 测试文件大小
            noise_result = find_optimal_format(noisy_image, target_size_bytes, preferred_format)
            
            if noise_result:
                print(f"    文件大小: {noise_result['size'] / 1024 / 1024:.2f}MB, 误差: {((noise_result['size'] - target_size_bytes) / target_size_bytes * 100):+.1f}%")
                
                if noise_result['diff'] < best_noise_diff:
                    best_noise_diff = noise_result['diff']
                    best_noise_result = {
                        'image': noisy_image,
                        'noise_level': noise_level,
                        'format': noise_result['format'],
                        'param': noise_result['param'],
                        'size': noise_result['size'],
                        'diff': noise_result['diff']
                    }
                
                # 如果找到满足条件的结果
                if noise_result['diff'] <= tolerance:
                    final_path = f"output_image_{target_width}x{target_height}_noise{noise_level}.{noise_result['format']}"
                    
                    # 保存带噪声图片
                    if noise_result['format'] == 'png':
                        noisy_image.save(final_path, format='PNG', compress_level=noise_result['param'])
                    elif noise_result['format'] == 'jpg':
                        noisy_image.save(final_path, format='JPEG', quality=noise_result['param'])
                    elif noise_result['format'] == 'bmp':
                        noisy_image.save(final_path, format='BMP')
                    
                    print(f"\n✅ 噪声策略成功！生成目标图片：{final_path}")
                    print(f"📐 最终分辨率：{target_width}x{target_height}")
                    print(f"🎵 噪声级别：{noise_level}")
                    print(f"📁 文件大小：{noise_result['size'] / 1024 / 1024:.2f}MB")
                    print(f"🎯 目标大小：{target_size_bytes / 1024 / 1024:.2f}MB")
                    print(f"📊 精确度：{((noise_result['size'] - target_size_bytes) / target_size_bytes * 100):+.1f}%")
                    print(f"🎨 最佳格式：{noise_result['format'].upper()}")
                    
                    return final_path
        
        # 返回噪声调整的最佳结果
        if best_noise_result:
            final_path = f"output_image_{target_width}x{target_height}_noise{best_noise_result['noise_level']}.{best_noise_result['format']}"
            
            if best_noise_result['format'] == 'png':
                best_noise_result['image'].save(final_path, format='PNG', compress_level=best_noise_result['param'])
            elif best_noise_result['format'] == 'jpg':
                best_noise_result['image'].save(final_path, format='JPEG', quality=best_noise_result['param'])
            elif best_noise_result['format'] == 'bmp':
                best_noise_result['image'].save(final_path, format='BMP')
            
            print(f"\n⚡ 噪声调整完成！返回最佳结果：{final_path}")
            print(f"📐 最终分辨率：{target_width}x{target_height}")
            print(f"🎵 噪声级别：{best_noise_result['noise_level']}")
            print(f"📁 文件大小：{best_noise_result['size'] / 1024 / 1024:.2f}MB")
            print(f"🎯 目标大小：{target_size_bytes / 1024 / 1024:.2f}MB")
            print(f"📊 精确度：{((best_noise_result['size'] - target_size_bytes) / target_size_bytes * 100):+.1f}%")
            print(f"🎨 最佳格式：{best_noise_result['format'].upper()}")
            
            return final_path
    
    # 如果所有方法都无法满足，返回最佳的无噪声结果
    if best_result:
        final_path = f"output_image_{best_result['width']}x{best_result['height']}_final.{best_result['format']}"
        
        if best_result['format'] == 'png':
            best_result['image'].save(final_path, format='PNG', compress_level=best_result['param'])
        elif best_result['format'] == 'jpg':
            best_result['image'].save(final_path, format='JPEG', quality=best_result['param'])
        elif best_result['format'] == 'bmp':
            best_result['image'].save(final_path, format='BMP')
        
        print(f"\n⚡ 算法完成！返回最接近的结果：{final_path}")
        print(f"📐 最终分辨率：{best_result['width']}x{best_result['height']}")
        print(f"🎵 噪声级别：{best_result['noise_level']}")
        print(f"📁 文件大小：{best_result['size'] / 1024 / 1024:.2f}MB")
        print(f"🎯 目标大小：{target_size_bytes / 1024 / 1024:.2f}MB")
        print(f"📊 精确度：{((best_result['size'] - target_size_bytes) / target_size_bytes * 100):+.1f}%")
        print(f"🎨 最佳格式：{best_result['format'].upper()}")
        
        return final_path
    
    # 最后的备选方案
    fallback_path = f"output_image_1000x563_fallback.png"
    fallback_image = create_base_image(1000, 563)
    fallback_image.save(fallback_path, compress_level=0)
    
    print(f"\n❌ 算法未能达到理想效果，生成基础图片：{fallback_path}")
    return fallback_path

def cleanup_temp_files(temp_files):
    """清理临时文件"""
    for temp_file in temp_files:
        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        except:
            pass

def main():
    """主函数"""
    try:
        # 获取用户输入
        file_size_mb, max_resolution, selected_format = get_user_input()
        
        # 转换文件大小为字节
        target_size_bytes = int(file_size_mb * 1024 * 1024)
        
        # 显示参数信息
        print(f"\n=== 参数确认 ===")
        print(f"目标文件大小: {file_size_mb}MB")
        print(f"图片格式: {selected_format.upper()}")
        
        if max_resolution:
            print(f"分辨率上限: {max_resolution[0]}x{max_resolution[1]}")
        else:
            print("分辨率上限: 无限制")
        
        # 使用新版超强智能算法生成图片
        output_path = super_smart_generate_v2(target_size_bytes, max_resolution, selected_format)
        
        if output_path:
            print(f"\n🎉 图片生成完成！")
            print(f"📍 文件路径: {os.path.abspath(output_path)}")
        else:
            print(f"\n❌ 图片生成失败！")
        
    except KeyboardInterrupt:
        print("\n\n❌ 用户取消操作")
    except Exception as e:
        print(f"\n❌ 发生错误: {str(e)}")

if __name__ == "__main__":
    main()