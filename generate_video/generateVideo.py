#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频生成工具
根据用户输入的数量、分辨率和文本内容生成对应的视频
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os
import threading
import time
from datetime import datetime
import json


class VideoGenerator:
    """视频生成器类"""
    
    def __init__(self):
        self.font_cache = {}
        self.default_font_size = 48
        
    def get_font(self, font_size, font_path=None):
        """获取字体对象"""
        if font_path and os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, font_size)
            except:
                pass
        
        # 尝试使用系统字体
        system_fonts = [
            "arial.ttf",
            "simhei.ttf",  # 黑体
            "simsun.ttc",  # 宋体
            "msyh.ttc",    # 微软雅黑
            "simkai.ttf",  # 楷体
            "C:/Windows/Fonts/simhei.ttf",
            "C:/Windows/Fonts/simsun.ttc",
            "C:/Windows/Fonts/msyh.ttc",
            "/System/Library/Fonts/Arial.ttf",  # macOS
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"  # Linux
        ]
        
        for font_name in system_fonts:
            try:
                if os.path.exists(font_name):
                    return ImageFont.truetype(font_name, font_size)
            except:
                continue
        
        # 最后使用默认字体
        try:
            return ImageFont.truetype("arial.ttf", font_size)
        except:
            return ImageFont.load_default()
    
    def create_text_frame(self, text, width, height, font_size=None, 
                         bg_color=(0, 0, 0), text_color=(255, 255, 255),
                         font_path=None):
        """创建包含文本的帧"""
        if font_size is None:
            # 根据分辨率自动计算字体大小
            font_size = min(width, height) // 20
        
        # 创建图像
        img = Image.new('RGB', (width, height), bg_color)
        draw = ImageDraw.Draw(img)
        
        # 获取字体
        font = self.get_font(font_size, font_path)
        
        # 处理多行文本
        lines = text.split('\n')
        if len(lines) == 1 and len(text) > 20:
            # 自动换行
            lines = self.wrap_text(text, width, font, draw)
        
        # 计算总文本高度
        total_height = 0
        line_heights = []
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            line_height = bbox[3] - bbox[1]
            line_heights.append(line_height)
            total_height += line_height
        
        # 计算起始Y位置（垂直居中）
        y = (height - total_height) // 2
        
        # 绘制每一行文本
        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            
            # 水平居中
            x = (width - text_width) // 2
            
            # 绘制文本
            draw.text((x, y), line, fill=text_color, font=font)
            
            # 移动到下一行
            y += line_heights[i]
        
        # 转换为OpenCV格式
        frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        return frame
    
    def wrap_text(self, text, max_width, font, draw):
        """文本自动换行"""
        words = text.split()
        lines = []
        current_line = ""
        
        for word in words:
            test_line = current_line + " " + word if current_line else word
            bbox = draw.textbbox((0, 0), test_line, font=font)
            text_width = bbox[2] - bbox[0]
            
            if text_width <= max_width * 0.8:  # 留20%边距
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        
        if current_line:
            lines.append(current_line)
        
        return lines if lines else [text]
    
    def generate_video(self, text, width, height, duration=3, fps=30,
                      output_path="output.mp4", font_size=None,
                      bg_color=(0, 0, 0), text_color=(255, 255, 255),
                      font_path=None):
        """生成视频"""
        # 计算总帧数
        total_frames = int(duration * fps)
        
        # 创建视频写入器
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        # 生成帧
        for i in range(total_frames):
            frame = self.create_text_frame(
                text, width, height, font_size, bg_color, text_color, font_path
            )
            out.write(frame)
        
        out.release()
        return output_path


class VideoGeneratorGUI:
    """视频生成器GUI界面"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("视频生成工具")
        self.root.geometry("600x700")
        self.root.resizable(True, True)
        
        # 输出目录
        self.output_dir = os.path.join(os.getcwd(), "generated_videos")
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 设置样式
        self.setup_styles()
        
        # 创建视频生成器
        self.generator = VideoGenerator()
        
        # 创建界面
        self.create_widgets()
        
        # 生成状态
        self.is_generating = False
        
    def setup_styles(self):
        """设置界面样式"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # 配置样式
        style.configure('Title.TLabel', font=('微软雅黑', 16, 'bold'))
        style.configure('Header.TLabel', font=('微软雅黑', 12, 'bold'))
        style.configure('Info.TLabel', font=('微软雅黑', 10))
        
    def create_widgets(self):
        """创建界面组件"""
        # 主容器
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # 标题
        title_label = ttk.Label(main_frame, text="视频生成工具", style='Title.TLabel')
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # 视频数量设置
        ttk.Label(main_frame, text="视频数量:", style='Header.TLabel').grid(
            row=1, column=0, sticky=tk.W, pady=(0, 5))
        
        self.count_var = tk.StringVar(value="1")
        count_frame = ttk.Frame(main_frame)
        count_frame.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=(0, 10))
        count_frame.columnconfigure(0, weight=1)
        
        self.count_entry = ttk.Entry(count_frame, textvariable=self.count_var, width=10)
        self.count_entry.grid(row=0, column=0, sticky=tk.W)
        
        ttk.Label(count_frame, text="个", style='Info.TLabel').grid(row=0, column=1, padx=(5, 0))
        
        # 视频分辨率设置
        ttk.Label(main_frame, text="视频分辨率:", style='Header.TLabel').grid(
            row=2, column=0, sticky=tk.W, pady=(0, 5))
        
        resolution_frame = ttk.Frame(main_frame)
        resolution_frame.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=(0, 10))
        resolution_frame.columnconfigure(1, weight=1)
        resolution_frame.columnconfigure(3, weight=1)
        
        # 宽度
        ttk.Label(resolution_frame, text="宽度:", style='Info.TLabel').grid(row=0, column=0, sticky=tk.W)
        self.width_var = tk.StringVar(value="1920")
        self.width_entry = ttk.Entry(resolution_frame, textvariable=self.width_var, width=8)
        self.width_entry.grid(row=0, column=1, sticky=tk.W, padx=(5, 10))
        
        # 高度
        ttk.Label(resolution_frame, text="高度:", style='Info.TLabel').grid(row=0, column=2, sticky=tk.W)
        self.height_var = tk.StringVar(value="1080")
        self.height_entry = ttk.Entry(resolution_frame, textvariable=self.height_var, width=8)
        self.height_entry.grid(row=0, column=3, sticky=tk.W, padx=(5, 0))
        
        # 预设分辨率
        preset_frame = ttk.Frame(main_frame)
        preset_frame.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=(0, 10))
        
        presets = [
            ("HD (1280x720)", "1280", "720"),
            ("Full HD (1920x1080)", "1920", "1080"),
            ("2K (2560x1440)", "2560", "1440"),
            ("4K (3840x2160)", "3840", "2160")
        ]
        
        for i, (name, w, h) in enumerate(presets):
            btn = ttk.Button(preset_frame, text=name, 
                           command=lambda w=w, h=h: self.set_resolution(w, h))
            btn.grid(row=0, column=i, padx=(0, 5))
        
        # 视频文本内容
        ttk.Label(main_frame, text="视频文本内容:", style='Header.TLabel').grid(
            row=4, column=0, sticky=tk.W, pady=(0, 5))
        
        self.text_var = tk.StringVar(value="")
        self.text_entry = ttk.Entry(main_frame, textvariable=self.text_var)
        self.text_entry.grid(row=4, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        
        # 添加提示标签
        ttk.Label(main_frame, text="(留空将自动填充序号文本)", style='Info.TLabel', foreground='gray').grid(
            row=4, column=1, sticky=tk.E, pady=(0, 10))
        
        # 多行文本输入
        ttk.Label(main_frame, text="多行文本内容:", style='Header.TLabel').grid(
            row=5, column=0, sticky=tk.W, pady=(0, 5))
        
        text_frame = ttk.Frame(main_frame)
        text_frame.grid(row=5, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)
        
        self.text_text = tk.Text(text_frame, height=6, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.text_text.yview)
        self.text_text.configure(yscrollcommand=scrollbar.set)
        
        self.text_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # 添加多行文本提示
        ttk.Label(main_frame, text="(留空将自动填充序号文本)", style='Info.TLabel', foreground='gray').grid(
            row=5, column=1, sticky=tk.E, pady=(0, 10))
        
        # 视频参数设置
        params_frame = ttk.LabelFrame(main_frame, text="视频参数", padding="10")
        params_frame.grid(row=6, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        params_frame.columnconfigure(1, weight=1)
        params_frame.columnconfigure(3, weight=1)
        
        # 视频时长
        ttk.Label(params_frame, text="视频时长(秒):", style='Info.TLabel').grid(row=0, column=0, sticky=tk.W)
        self.duration_var = tk.StringVar(value="3")
        self.duration_entry = ttk.Entry(params_frame, textvariable=self.duration_var, width=8)
        self.duration_entry.grid(row=0, column=1, sticky=tk.W, padx=(5, 10))
        
        # 帧率
        ttk.Label(params_frame, text="帧率(FPS):", style='Info.TLabel').grid(row=0, column=2, sticky=tk.W)
        self.fps_var = tk.StringVar(value="30")
        self.fps_entry = ttk.Entry(params_frame, textvariable=self.fps_var, width=8)
        self.fps_entry.grid(row=0, column=3, sticky=tk.W, padx=(5, 0))
        
        # 字体大小
        ttk.Label(params_frame, text="字体大小:", style='Info.TLabel').grid(row=1, column=0, sticky=tk.W, pady=(10, 0))
        self.font_size_var = tk.StringVar(value="自动")
        self.font_size_entry = ttk.Entry(params_frame, textvariable=self.font_size_var, width=8)
        self.font_size_entry.grid(row=1, column=1, sticky=tk.W, padx=(5, 10), pady=(10, 0))
        
        # 字体文件选择
        ttk.Label(params_frame, text="字体文件:", style='Info.TLabel').grid(row=1, column=2, sticky=tk.W, pady=(10, 0))
        self.font_path_var = tk.StringVar()
        font_path_frame = ttk.Frame(params_frame)
        font_path_frame.grid(row=1, column=3, sticky=(tk.W, tk.E), pady=(10, 0))
        font_path_frame.columnconfigure(0, weight=1)
        
        self.font_path_entry = ttk.Entry(font_path_frame, textvariable=self.font_path_var, state='readonly')
        self.font_path_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(5, 5))
        
        ttk.Button(font_path_frame, text="选择", command=self.select_font_file).grid(row=0, column=1)
        ttk.Button(font_path_frame, text="检测字体", command=self.detect_fonts).grid(row=0, column=2, padx=(5, 0))
        
        # 颜色设置
        color_frame = ttk.LabelFrame(main_frame, text="颜色设置", padding="10")
        color_frame.grid(row=7, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        color_frame.columnconfigure(1, weight=1)
        color_frame.columnconfigure(3, weight=1)
        
        # 背景颜色
        ttk.Label(color_frame, text="背景颜色:", style='Info.TLabel').grid(row=0, column=0, sticky=tk.W)
        self.bg_color_var = tk.StringVar(value="#000000")
        self.bg_color_entry = ttk.Entry(color_frame, textvariable=self.bg_color_var, width=10)
        self.bg_color_entry.grid(row=0, column=1, sticky=tk.W, padx=(5, 10))
        
        # 文本颜色
        ttk.Label(color_frame, text="文本颜色:", style='Info.TLabel').grid(row=0, column=2, sticky=tk.W)
        self.text_color_var = tk.StringVar(value="#FFFFFF")
        self.text_color_entry = ttk.Entry(color_frame, textvariable=self.text_color_var, width=10)
        self.text_color_entry.grid(row=0, column=3, sticky=tk.W, padx=(5, 0))
        
        # 输出目录设置
        output_frame = ttk.LabelFrame(main_frame, text="输出设置", padding="10")
        output_frame.grid(row=8, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        output_frame.columnconfigure(1, weight=1)
        
        ttk.Label(output_frame, text="输出目录:", style='Info.TLabel').grid(row=0, column=0, sticky=tk.W)
        self.output_dir_var = tk.StringVar(value=self.output_dir)
        output_dir_entry = ttk.Entry(output_frame, textvariable=self.output_dir_var, state='readonly')
        output_dir_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 5))
        
        ttk.Button(output_frame, text="选择", command=self.select_output_dir).grid(row=0, column=2)
        
        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=9, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 状态标签
        self.status_var = tk.StringVar(value="就绪")
        self.status_label = ttk.Label(main_frame, textvariable=self.status_var, style='Info.TLabel')
        self.status_label.grid(row=10, column=0, columnspan=2, pady=(0, 10))
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=11, column=0, columnspan=2, pady=(0, 10))
        
        self.generate_btn = ttk.Button(button_frame, text="开始生成", command=self.start_generation)
        self.generate_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(button_frame, text="打开输出目录", command=self.open_output_dir).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(button_frame, text="退出", command=self.root.quit).pack(side=tk.LEFT)
        
        # 配置主框架的行权重
        main_frame.rowconfigure(5, weight=1)
        
    def set_resolution(self, width, height):
        """设置分辨率"""
        self.width_var.set(width)
        self.height_var.set(height)
        
    def select_font_file(self):
        """选择字体文件"""
        font_path = filedialog.askopenfilename(
            title="选择字体文件",
            filetypes=[("字体文件", "*.ttf *.otf *.ttc"), ("所有文件", "*.*")]
        )
        if font_path:
            self.font_path_var.set(font_path)
    
    def detect_fonts(self):
        """检测系统可用字体"""
        system_fonts = [
            ("Arial", "arial.ttf"),
            ("黑体", "simhei.ttf"),
            ("宋体", "simsun.ttc"),
            ("微软雅黑", "msyh.ttc"),
            ("楷体", "simkai.ttf"),
            ("Windows字体目录", "C:/Windows/Fonts/simhei.ttf"),
            ("Windows字体目录", "C:/Windows/Fonts/simsun.ttc"),
            ("Windows字体目录", "C:/Windows/Fonts/msyh.ttc"),
        ]
        
        available_fonts = []
        for font_name, font_path in system_fonts:
            if os.path.exists(font_path):
                available_fonts.append(f"{font_name}: {font_path}")
        
        if available_fonts:
            font_info = "检测到的可用字体：\n\n" + "\n".join(available_fonts)
            messagebox.showinfo("字体检测结果", font_info)
        else:
            messagebox.showwarning("字体检测结果", "未检测到常用字体，建议手动选择字体文件")
            
    def select_output_dir(self):
        """选择输出目录"""
        output_dir = filedialog.askdirectory(title="选择输出目录")
        if output_dir:
            self.output_dir_var.set(output_dir)
            self.output_dir = output_dir
            
    def open_output_dir(self):
        """打开输出目录"""
        import subprocess
        import platform
        
        output_dir = self.output_dir_var.get()
        if os.path.exists(output_dir):
            if platform.system() == "Windows":
                subprocess.run(["explorer", output_dir])
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", output_dir])
            else:  # Linux
                subprocess.run(["xdg-open", output_dir])
                
    def validate_inputs(self):
        """验证输入参数"""
        try:
            count = int(self.count_var.get())
            if count <= 0 or count > 100:
                raise ValueError("视频数量必须在1-100之间")
                
            width = int(self.width_var.get())
            height = int(self.height_var.get())
            if width <= 0 or height <= 0:
                raise ValueError("分辨率必须大于0")
                
            duration = float(self.duration_var.get())
            if duration <= 0:
                raise ValueError("视频时长必须大于0")
                
            fps = int(self.fps_var.get())
            if fps <= 0:
                raise ValueError("帧率必须大于0")
                
            # 获取文本内容
            text = self.text_text.get("1.0", tk.END).strip()
            if not text:
                text = self.text_var.get().strip()
            # 如果用户没有输入文本，允许使用自动填充（不报错）
            # 文本内容将在生成视频时处理
                
            return True, {
                'count': count,
                'width': width,
                'height': height,
                'duration': duration,
                'fps': fps,
                'text': text
            }
            
        except ValueError as e:
            messagebox.showerror("输入错误", str(e))
            return False, None
            
    def hex_to_rgb(self, hex_color):
        """将十六进制颜色转换为RGB"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        
    def start_generation(self):
        """开始生成视频"""
        if self.is_generating:
            return
            
        # 验证输入
        valid, params = self.validate_inputs()
        if not valid:
            return
            
        # 获取字体大小
        font_size = None
        if self.font_size_var.get() != "自动":
            try:
                font_size = int(self.font_size_var.get())
            except ValueError:
                messagebox.showerror("错误", "字体大小必须是数字或'自动'")
                return
                
        # 获取颜色
        try:
            bg_color = self.hex_to_rgb(self.bg_color_var.get())
            text_color = self.hex_to_rgb(self.text_color_var.get())
        except:
            messagebox.showerror("错误", "颜色格式错误，请使用十六进制格式（如#000000）")
            return
            
        # 获取字体路径
        font_path = self.font_path_var.get() if self.font_path_var.get() else None
        
        # 在新线程中生成视频
        self.is_generating = True
        self.generate_btn.config(state='disabled')
        
        thread = threading.Thread(
            target=self.generate_videos,
            args=(params, font_size, bg_color, text_color, font_path)
        )
        thread.daemon = True
        thread.start()
        
    def generate_videos(self, params, font_size, bg_color, text_color, font_path):
        """生成视频（在后台线程中执行）"""
        try:
            count = params['count']
            total_videos = count
            
            for i in range(count):
                # 更新状态
                progress = (i / total_videos) * 100
                self.root.after(0, lambda p=progress: self.progress_var.set(p))
                self.root.after(0, lambda: self.status_var.set(f"正在生成第 {i+1}/{total_videos} 个视频..."))
                
                # 生成文件名
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"video_{i+1:03d}_{timestamp}.mp4"
                output_path = os.path.join(self.output_dir, filename)
                
                # 获取视频文本内容
                video_text = params['text']
                if not video_text or video_text.strip() == "":
                    # 如果用户没有输入文本，自动生成序号文本
                    video_text = self.generate_sequence_text(i + 1, count)
                    print(f"使用自动填充文本: {video_text}")  # 调试信息
                
                # 生成视频
                self.generator.generate_video(
                    text=video_text,
                    width=params['width'],
                    height=params['height'],
                    duration=params['duration'],
                    fps=params['fps'],
                    output_path=output_path,
                    font_size=font_size,
                    bg_color=bg_color,
                    text_color=text_color,
                    font_path=font_path
                )
                
                # 短暂延迟
                time.sleep(0.1)
                
            # 完成
            self.root.after(0, lambda: self.progress_var.set(100))
            self.root.after(0, lambda: self.status_var.set(f"生成完成！共生成 {total_videos} 个视频"))
            self.root.after(0, lambda: messagebox.showinfo("完成", f"视频生成完成！\n共生成 {total_videos} 个视频\n输出目录：{self.output_dir}"))
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("错误", f"生成视频时发生错误：{str(e)}"))
            self.root.after(0, lambda: self.status_var.set("生成失败"))
            
        finally:
            self.is_generating = False
            self.root.after(0, lambda: self.generate_btn.config(state='normal'))
    
    def generate_sequence_text(self, current_num, total_count):
        """生成序号文本"""
        # 英文序号映射
        english_numbers = {
            1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth",
            6: "sixth", 7: "seventh", 8: "eighth", 9: "ninth", 10: "tenth",
            11: "eleventh", 12: "twelfth", 13: "thirteenth", 14: "fourteenth", 15: "fifteenth",
            16: "sixteenth", 17: "seventeenth", 18: "eighteenth", 19: "nineteenth", 20: "twentieth"
        }
        
        # 如果总数小于等于20，使用英文序数词
        if total_count <= 20 and current_num <= 20:
            english_ordinal = english_numbers.get(current_num, f"{current_num}th")
            return f"the {english_ordinal} video"
        else:
            # 否则使用数字格式
            return f"video {current_num:03d}"


def main():
    """主函数"""
    # 检查依赖
    try:
        import cv2
        import numpy as np
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as e:
        print(f"缺少依赖库：{e}")
        print("请安装以下依赖：")
        print("pip install opencv-python numpy pillow")
        return
        
    # 创建主窗口
    root = tk.Tk()
    app = VideoGeneratorGUI(root)
    
    # 运行应用
    root.mainloop()


if __name__ == "__main__":
    main()