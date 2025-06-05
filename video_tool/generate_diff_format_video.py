from moviepy.editor import TextClip, CompositeVideoClip, ColorClip
import os
import subprocess

# 视频编码方案配置字典
ENCODING_PROFILES = {
    # H.264 / AVC 编码
    "h264_mp4": {
        "codec": "libx264",  # H.264/AVC 编码器（广泛兼容）
        "container": "mp4",  # MP4 封装格式，适用于大多数平台
        "description": "H.264/AVC 编码 + MP4封装，兼容性好，推荐使用"
    },
    "h264_mkv": {
        "codec": "libx264",  # H.264/AVC 编码器
        "container": "mkv",  # Matroska 封装格式
        "description": "H.264/AVC 编码 + MKV封装，支持多音轨和字幕"
    },
    "h264_avi": {
        "codec": "libx264",  # H.264/AVC 编码器
        "container": "avi",  # AVI 封装格式
        "description": "H.264/AVC 编码 + AVI封装，传统格式兼容性"
    },

    # H.265 / HEVC 编码
    "h265_mp4": {
        "codec": "libx265",  # H.265/HEVC 编码器（更省空间）
        "container": "mp4",
        "description": "H.265/HEVC 编码 + MP4封装，高压缩但部分设备不兼容"
    },
    "h265_mkv": {
        "codec": "libx265",  # H.265/HEVC 编码器
        "container": "mkv",
        "description": "H.265/HEVC 编码 + MKV封装，高压缩率"
    },

    # VP8 编码
    "vp8_webm": {
        "codec": "libvpx",  # VP8 编码器（Google主推）
        "container": "webm",  # WebM 封装格式（适合 Web 浏览器）
        "description": "VP8 编码 + WebM封装，适合网页嵌入"
    },
    "vp8_mkv": {
        "codec": "libvpx",  # VP8 编码器
        "container": "mkv",
        "description": "VP8 编码 + MKV封装，开源格式"
    },

    # VP9 编码
    "vp9_webm": {
        "codec": "libvpx-vp9",  # VP9 编码器（更高压缩率）
        "container": "webm",
        "description": "VP9 编码 + WebM封装，更高压缩率但编码较慢"
    },
    "vp9_mkv": {
        "codec": "libvpx-vp9",  # VP9 编码器
        "container": "mkv",
        "description": "VP9 编码 + MKV封装，高效压缩"
    },

    # AV1 编码（下一代编码标准）
    "av1_mp4": {
        "codec": "libaom-av1",  # AV1 编码器（最新标准）
        "container": "mp4",
        "description": "AV1 编码 + MP4封装，最新压缩标准，编码极慢但压缩率极高"
    },
    "av1_webm": {
        "codec": "libaom-av1",  # AV1 编码器
        "container": "webm",
        "description": "AV1 编码 + WebM封装，未来标准"
    },
    "av1_mkv": {
        "codec": "libaom-av1",  # AV1 编码器
        "container": "mkv",
        "description": "AV1 编码 + MKV封装，开源未来标准"
    },

    # MPEG-2 编码
    "mpeg2_mpg": {
        "codec": "mpeg2video",  # MPEG-2 编码器（DVD标准）
        "container": "mpg",  # MPEG 封装格式
        "description": "MPEG-2 编码 + MPG封装，DVD标准格式"
    },
    "mpeg2_mp4": {
        "codec": "mpeg2video",  # MPEG-2 编码器
        "container": "mp4",
        "description": "MPEG-2 编码 + MP4封装，广播标准"
    },

    # MPEG-4 Part 2 编码
    "mpeg4_avi": {
        "codec": "mpeg4",  # MPEG-4 Part 2 编码器（老旧但兼容性好）
        "container": "avi",  # AVI 封装格式（适用于传统播放器）
        "description": "MPEG-4 Part 2 编码 + AVI封装，兼容老旧设备"
    },
    "mpeg4_mp4": {
        "codec": "mpeg4",  # MPEG-4 Part 2 编码器
        "container": "mp4",
        "description": "MPEG-4 Part 2 编码 + MP4封装，经典格式"
    },

    # Theora 编码（开源）
    "theora_ogv": {
        "codec": "libtheora",  # Theora 编码器（开源）
        "container": "ogv",  # Ogg 封装格式
        "description": "Theora 编码 + OGV封装，完全开源格式"
    },
    "theora_mkv": {
        "codec": "libtheora",  # Theora 编码器
        "container": "mkv",
        "description": "Theora 编码 + MKV封装，开源组合"
    },

    # WMV 编码（Windows Media Video）
    "wmv3_wmv": {
        "codec": "wmv2",  # WMV 编码器（Windows专用）
        "container": "wmv",  # WMV 封装格式
        "description": "WMV 编码 + WMV封装，Windows Media格式"
    },
    "wmv3_asf": {
        "codec": "wmv2",  # WMV 编码器
        "container": "asf",  # ASF 封装格式
        "description": "WMV 编码 + ASF封装，Windows流媒体格式"
    },

    # 其他常用格式
    "xvid_avi": {
        "codec": "libxvid",  # Xvid 编码器（MPEG-4的开源实现）
        "container": "avi",
        "description": "Xvid 编码 + AVI封装，开源MPEG-4实现"
    },
    "prores_mov": {
        "codec": "prores",  # Apple ProRes 编码器（专业视频）
        "container": "mov",  # QuickTime 封装格式
        "description": "ProRes 编码 + MOV封装，苹果专业视频格式"
    },
    "dnxhd_mxf": {
        "codec": "dnxhd",  # Avid DNxHD 编码器（专业视频）
        "container": "mxf",  # MXF 封装格式
        "description": "DNxHD 编码 + MXF封装，专业广播格式"
    }
}

# 安全的字体列表（优先使用这些字体）
SAFE_FONTS = [
    'Arial', 'Times-New-Roman', 'Courier-New', 'Verdana', 'Tahoma',
    'Calibri', 'Georgia', 'Comic-Sans-MS', 'Impact', 'Trebuchet-MS',
    'Microsoft-YaHei', 'SimHei', 'SimSun', 'KaiTi', 'FangSong'
]


def get_safe_font():
    """获取一个安全可用的字体"""
    available_fonts = TextClip.list('font')

    # 优先使用安全字体列表中的字体
    for safe_font in SAFE_FONTS:
        if safe_font in available_fonts:
            return safe_font

    # 如果安全字体都不可用，使用Arial或第一个可用字体
    if 'Arial' in available_fonts:
        return 'Arial'
    elif available_fonts:
        return available_fonts[0]
    else:
        return None


def create_text_video(
        text,
        output_filename="output",
        duration=5,
        resolution=(1280, 720),
        fontsize=80,
        font=None,
        text_color="white",
        bg_color="black",
        codec="libx264",  # 控制编码格式
        container="mp4"  # 控制输出封装格式
):
    """
    创建一个文字视频，支持自定义编码和容器格式

    :param text: 显示的文字
    :param output_filename: 输出文件的名字（不带扩展名）
    :param duration: 视频时长（秒）
    :param resolution: 分辨率 (宽, 高)
    :param fontsize: 字体大小
    :param font: 字体名（确保系统已安装），如果为None则自动选择安全字体
    :param text_color: 字体颜色
    :param bg_color: 背景颜色
    :param codec: 视频编码器，比如 'libx264', 'mpeg4', 'libvpx'
    :param container: 容器格式，比如 'mp4', 'avi', 'webm'
    """

    print(f"生成文字视频: '{text}'，编码: {codec}，封装: {container}")

    # 检查编码器可用性
    if not check_codec_availability(codec):
        print(f"⚠️  编码器 {codec} 不可用，尝试使用H.264备用编码器...")
        original_codec = codec
        codec = "libx264"
        container = "mp4"  # H.264通常使用MP4容器

        if not check_codec_availability(codec):
            print(f"❌ 备用编码器 {codec} 也不可用，跳过此视频生成")
            return

        print(f"✅ 使用备用编码器: {codec}")
        # 更新输出文件名以反映编码器变更
        output_filename = f"{output_filename}_fallback_from_{original_codec.replace('-', '_')}"

    # 如果没有指定字体，自动选择安全字体
    if font is None:
        font = get_safe_font()

    if font is None:
        print("❌ 没有找到可用的字体")
        return

    print(f"当前使用字体：{font}")

    # 创建文字剪辑
    try:
        # 方法1：尝试使用caption方法
        try:
            text_clip = TextClip(
                text,
                fontsize=fontsize,
                font=font,
                color=text_color,
                size=resolution,
                method='caption'
            )
        except:
            # 方法2：如果caption方法失败，尝试使用label方法
            print("⚠️ caption方法失败，尝试使用label方法")
            text_clip = TextClip(
                text,
                fontsize=fontsize,
                font=font,
                color=text_color,
                method='label'
            )

        # 设置持续时间和位置
        text_clip = text_clip.set_duration(duration).set_position("center")

        # 创建背景 - 确保颜色格式正确
        if isinstance(bg_color, str):
            # 如果是字符串颜色名，转换为RGB元组
            color_map = {
                'black': (0, 0, 0),
                'white': (255, 255, 255),
                'red': (255, 0, 0),
                'green': (0, 255, 0),
                'blue': (0, 0, 255)
            }
            bg_color_rgb = color_map.get(bg_color.lower(), (0, 0, 0))
        else:
            bg_color_rgb = bg_color

        bg_clip = ColorClip(size=resolution, color=bg_color_rgb, duration=duration)

        # 合成视频
        video = CompositeVideoClip([bg_clip, text_clip])

    except Exception as e:
        print(f"❌ 创建文字剪辑失败：{e}")
        print("尝试使用备用方案...")

        # 备用方案：使用更简单的参数
        try:
            text_clip = TextClip(
                text,
                fontsize=fontsize,
                color=text_color
            ).set_duration(duration).set_position("center")

            # 确保背景颜色格式正确
            if isinstance(bg_color, str):
                color_map = {
                    'black': (0, 0, 0),
                    'white': (255, 255, 255),
                    'red': (255, 0, 0),
                    'green': (0, 255, 0),
                    'blue': (0, 0, 255)
                }
                bg_color_rgb = color_map.get(bg_color.lower(), (0, 0, 0))
            else:
                bg_color_rgb = bg_color

            bg_clip = ColorClip(size=resolution, color=bg_color_rgb, duration=duration)
            video = CompositeVideoClip([bg_clip, text_clip])

        except Exception as e2:
            print(f"❌ 备用方案也失败了：{e2}")
            return

    # 确保输出目录存在
    output_dir = "F:/临时文档/tmp/输出视频"
    os.makedirs(output_dir, exist_ok=True)

    # 构造输出文件名
    output_path = f"{output_dir}/{output_filename}.{container}"

    try:
        # 准备FFmpeg参数
        ffmpeg_params = []

        # 为不同编码器添加特定参数
        if codec == "libaom-av1":
            # AV1编码器需要更多参数
            ffmpeg_params.extend([
                "-strict", "-2",  # 允许实验性编码器
                "-cpu-used", "8",  # 使用最快的编码速度
                "-row-mt", "1",  # 启用行级多线程
                "-tiles", "2x2",  # 使用2x2瓦片布局
                "-crf", "30",  # 设置质量参数
                "-b:v", "0"  # 使用CRF模式
            ])
        elif codec == "libx265":
            # H.265编码器优化参数
            ffmpeg_params.extend([
                "-preset", "fast",  # 使用快速预设
                "-crf", "23"  # 设置质量参数
            ])
        elif codec == "libvpx-vp9":
            # VP9编码器优化参数
            ffmpeg_params.extend([
                "-deadline", "realtime",  # 实时编码
                "-cpu-used", "8",  # 最快编码速度
                "-crf", "30",  # 质量参数
                "-b:v", "0"  # 使用CRF模式
            ])
        elif codec == "libvpx":
            # VP8编码器优化参数
            ffmpeg_params.extend([
                "-deadline", "realtime",  # 实时编码
                "-cpu-used", "16",  # 最快编码速度
                "-crf", "10"  # 质量参数
            ])

        # 写出视频
        print(f"🔧 使用FFmpeg参数: {ffmpeg_params}")

        if ffmpeg_params:
            video.write_videofile(
                output_path,
                fps=24,
                codec=codec,
                ffmpeg_params=ffmpeg_params,
                verbose=False,  # 减少输出信息
                logger=None  # 禁用日志
            )
        else:
            video.write_videofile(
                output_path,
                fps=24,
                codec=codec,
                verbose=False,
                logger=None
            )
        print(f"✅ 视频已生成: {output_path}")

    except Exception as e:
        print(f"❌ 视频写入失败：{e}")

        # 如果是AV1编码失败，尝试使用备用编码器
        if codec == "libaom-av1":
            print("🔄 AV1编码失败，尝试使用H.264备用方案...")
            try:
                backup_path = f"{output_dir}/{output_filename}_backup_h264.mp4"
                video.write_videofile(
                    backup_path,
                    fps=24,
                    codec="libx264",
                    verbose=False,
                    logger=None
                )
                print(f"✅ 备用视频已生成: {backup_path}")
            except Exception as e2:
                print(f"❌ 备用方案也失败了：{e2}")

        # 如果是其他高级编码器失败，也提供备用方案
        elif codec in ["libx265", "libvpx-vp9", "libvpx"]:
            print(f"🔄 {codec}编码失败，尝试使用H.264备用方案...")
            try:
                backup_path = f"{output_dir}/{output_filename}_backup_h264.mp4"
                video.write_videofile(
                    backup_path,
                    fps=24,
                    codec="libx264",
                    verbose=False,
                    logger=None
                )
                print(f"✅ 备用视频已生成: {backup_path}")
            except Exception as e2:
                print(f"❌ 备用方案也失败了：{e2}")

    finally:
        # 清理资源
        video.close()


def list_all_formats():
    """列出所有可用的编码格式"""
    print("🎬 所有可用的视频编码格式：")
    print("=" * 80)

    # 按编码类型分组
    format_groups = {
        "H.264/AVC": [],
        "H.265/HEVC": [],
        "VP8": [],
        "VP9": [],
        "AV1": [],
        "MPEG-2": [],
        "MPEG-4 Part 2": [],
        "Theora": [],
        "WMV": [],
        "其他": []
    }

    for key, profile in ENCODING_PROFILES.items():
        codec = profile["codec"]
        if "libx264" in codec:
            format_groups["H.264/AVC"].append((key, profile))
        elif "libx265" in codec:
            format_groups["H.265/HEVC"].append((key, profile))
        elif codec == "libvpx":
            format_groups["VP8"].append((key, profile))
        elif "libvpx-vp9" in codec:
            format_groups["VP9"].append((key, profile))
        elif "libaom-av1" in codec:
            format_groups["AV1"].append((key, profile))
        elif "mpeg2video" in codec:
            format_groups["MPEG-2"].append((key, profile))
        elif codec == "mpeg4":
            format_groups["MPEG-4 Part 2"].append((key, profile))
        elif "libtheora" in codec:
            format_groups["Theora"].append((key, profile))
        elif "wmv" in codec:
            format_groups["WMV"].append((key, profile))
        else:
            format_groups["其他"].append((key, profile))

    for group_name, formats in format_groups.items():
        if formats:
            print(f"\n📁 {group_name} 编码:")
            for key, profile in formats:
                print(f"  • {key:15} - {profile['description']}")

    print(f"\n总计: {len(ENCODING_PROFILES)} 种编码格式")
    print("=" * 80)


def test_specific_formats(format_keys, test_text="测试视频"):
    """
    测试指定的编码格式
    
    :param format_keys: 要测试的格式键列表
    :param test_text: 测试文本内容
    """
    print(f"🧪 开始测试 {len(format_keys)} 种指定编码格式...")

    success_count = 0
    failed_formats = []

    for format_key in format_keys:
        if format_key not in ENCODING_PROFILES:
            print(f"❌ 格式 '{format_key}' 不存在，跳过...")
            failed_formats.append(format_key)
            continue

        print(f"\n🎬 正在测试 {format_key} 格式...")

        try:
            create_text_video(
                text=f"{test_text}_{format_key}",
                output_filename=f"custom_test_{format_key}",
                duration=3,
                codec=ENCODING_PROFILES[format_key]["codec"],
                container=ENCODING_PROFILES[format_key]["container"]
            )
            print(f"✅ {format_key} 格式测试成功")
            success_count += 1
        except Exception as e:
            print(f"❌ {format_key} 格式测试失败: {e}")
            failed_formats.append(format_key)

    print(f"\n📊 测试结果统计:")
    print(f"  • 成功: {success_count}/{len(format_keys)} 种格式")
    print(f"  • 失败: {len(failed_formats)} 种格式")

    if failed_formats:
        print(f"  • 失败的格式: {', '.join(failed_formats)}")

    return success_count, failed_formats


def get_formats_by_codec_type(codec_type):
    """
    根据编码类型获取格式列表
    
    :param codec_type: 编码类型 ('h264', 'h265', 'vp8', 'vp9', 'av1', 'mpeg2', 'mpeg4', 'theora', 'wmv', 'other')
    :return: 格式键列表
    """
    codec_mapping = {
        'h264': lambda codec: 'libx264' in codec,
        'h265': lambda codec: 'libx265' in codec,
        'vp8': lambda codec: codec == 'libvpx',
        'vp9': lambda codec: 'libvpx-vp9' in codec,
        'av1': lambda codec: 'libaom-av1' in codec,
        'mpeg2': lambda codec: 'mpeg2video' in codec,
        'mpeg4': lambda codec: codec == 'mpeg4',
        'theora': lambda codec: 'libtheora' in codec,
        'wmv': lambda codec: 'wmv' in codec,
        'other': lambda codec: not any([
            'libx264' in codec, 'libx265' in codec, codec == 'libvpx',
            'libvpx-vp9' in codec, 'libaom-av1' in codec, 'mpeg2video' in codec,
            codec == 'mpeg4', 'libtheora' in codec, 'wmv' in codec
        ])
    }

    if codec_type not in codec_mapping:
        return []

    check_func = codec_mapping[codec_type]
    return [key for key, profile in ENCODING_PROFILES.items()
            if check_func(profile['codec'])]


def check_codec_availability(codec):
    """
    检查指定的编码器是否可用
    
    :param codec: 编码器名称，如 'libx264', 'libaom-av1' 等
    :return: True 如果编码器可用，False 如果不可用
    """
    try:
        # 使用ffmpeg -encoders命令检查编码器
        result = subprocess.run(
            ['ffmpeg', '-encoders'],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            # 检查编码器是否在输出中
            return codec in result.stdout
        else:
            return False

    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        # 如果ffmpeg不可用或出现其他错误，返回False
        return False


def get_available_codecs():
    """
    获取系统中所有可用的编码器列表
    
    :return: 可用编码器的字典，格式为 {profile_key: is_available}
    """
    availability = {}

    print("🔍 正在检查编码器可用性...")

    for profile_key, profile in ENCODING_PROFILES.items():
        codec = profile["codec"]
        is_available = check_codec_availability(codec)
        availability[profile_key] = is_available

        status = "✅ 可用" if is_available else "❌ 不可用"
        print(f"  • {profile_key:15} ({codec:12}) - {status}")

    available_count = sum(availability.values())
    total_count = len(availability)
    print(f"\n📊 编码器可用性统计: {available_count}/{total_count} 个编码器可用")

    return availability


# 示例用法
if __name__ == "__main__":
    # 显示所有可用格式
    list_all_formats()

    # 检查编码器可用性
    print("\n" + "=" * 80)
    codec_availability = get_available_codecs()

    # 只测试可用的编码格式
    available_formats = [key for key, available in codec_availability.items() if available]
    unavailable_formats = [key for key, available in codec_availability.items() if not available]

    if unavailable_formats:
        print(f"\n⚠️  跳过不可用的编码器: {', '.join(unavailable_formats)}")

    if not available_formats:
        print("\n❌ 没有找到可用的编码器，无法进行测试")
        exit(1)

    print(f"\n🧪 开始测试 {len(available_formats)} 种可用的编码格式...")

    success_count = 0
    failed_formats = []

    for encode_format in available_formats:
        print(f"\n🎬 正在测试 {encode_format} 格式...")

        try:
            create_text_video(
                text=f"视频格式_{encode_format}",
                output_filename=f"test_{encode_format}",
                duration=3,
                codec=ENCODING_PROFILES[encode_format]["codec"],
                container=ENCODING_PROFILES[encode_format]["container"]
            )
            print(f"✅ {encode_format} 格式测试成功")
            success_count += 1
        except Exception as e:
            print(f"❌ {encode_format} 格式测试失败: {e}")
            failed_formats.append(encode_format)

    print(f"\n🎉 测试完成！")
    print(f"📊 最终统计:")
    print(f"  • 总编码器数量: {len(ENCODING_PROFILES)}")
    print(f"  • 系统可用编码器: {len(available_formats)}")
    print(f"  • 测试成功: {success_count}")
    print(f"  • 测试失败: {len(failed_formats)}")

    if failed_formats:
        print(f"  • 失败的格式: {', '.join(failed_formats)}")

    if success_count > 0:
        print(f"\n✅ 成功生成了 {success_count} 个视频文件到 F:/临时文档/tmp/输出视频/ 目录")
