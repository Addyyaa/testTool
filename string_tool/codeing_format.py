#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
编码格式检测工具
提供GUI界面用于实时检测用户输入文本的编码格式

Author: Assistant
Date: 2024
Version: 1.0
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import chardet
import threading
import time
from typing import Dict, Optional, Tuple


class EncodingDetector:
    """编码检测业务逻辑类"""
    
    def __init__(self):
        self.supported_encodings = [
            'utf-8', 'utf-16', 'utf-32',
            'gbk', 'gb2312', 'gb18030',
            'ascii', 'latin1', 'cp1252',
            'big5', 'shift_jis', 'euc-jp',
            'euc-kr', 'iso-8859-1'
        ]
        
        # 编码显示名称映射
        self.encoding_display_names = {
            'utf-8': 'UTF-8 (Unicode)',
            'utf-16': 'UTF-16 (Unicode)',
            'utf-32': 'UTF-32 (Unicode)',
            'gbk': 'GBK (简体中文)',
            'gb2312': 'GB2312 (简体中文)',
            'gb18030': 'GB18030 (中文国标)',
            'ascii': 'ASCII (基础英文)',
            'latin1': 'Latin1 (ISO-8859-1)',
            'cp1252': 'CP1252 (Windows西欧)',
            'big5': 'Big5 (繁体中文)',
            'shift_jis': 'Shift_JIS (日文)',
            'euc-jp': 'EUC-JP (日文)',
            'euc-kr': 'EUC-KR (韩文)',
            'iso-8859-1': 'ISO-8859-1 (西欧)'
        }
    
    def detect_encoding(self, text: str) -> Dict[str, any]:
        """
        检测文本编码格式
        
        Args:
            text: 输入文本
            
        Returns:
            包含编码信息的字典
        """
        if not text:
            return {
                'encoding': 'Unknown',
                'confidence': 0.0,
                'details': '请输入文本进行检测'
            }
        
        try:
            # 将文本编码为字节以便检测
            text_bytes = text.encode('utf-8')
            result = chardet.detect(text_bytes)
            
            encoding = result.get('encoding', 'Unknown')
            confidence = result.get('confidence', 0.0)
            
            # 获取更详细的信息
            details = self._get_encoding_details(text, encoding)
            
            return {
                'encoding': encoding or 'Unknown',
                'confidence': confidence,
                'details': details
            }
            
        except Exception as e:
            return {
                'encoding': 'Error',
                'confidence': 0.0,
                'details': f'检测出错: {str(e)}'
            }
    
    def _get_encoding_details(self, text: str, encoding: str) -> str:
        """获取编码详细信息"""
        details = []
        
        # 字符统计
        char_count = len(text)
        byte_count = len(text.encode('utf-8'))
        
        details.append(f"字符数: {char_count}")
        details.append(f"字节数 (UTF-8): {byte_count}")
        
        # 字符类型分析
        ascii_count = sum(1 for c in text if ord(c) < 128)
        chinese_count = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        
        if ascii_count > 0:
            details.append(f"ASCII字符: {ascii_count}")
        if chinese_count > 0:
            details.append(f"中文字符: {chinese_count}")
        
        # 编码特征
        if encoding:
            if encoding.lower() in ['utf-8', 'utf8']:
                details.append("特征: Unicode标准编码，支持全球所有字符")
            elif encoding.lower() in ['gbk', 'gb2312', 'gb18030']:
                details.append("特征: 中文编码，主要用于简体中文")
            elif encoding.lower() == 'ascii':
                details.append("特征: 基础英文编码，仅支持128个字符")
            elif encoding.lower() in ['big5']:
                details.append("特征: 繁体中文编码")
        
        return " | ".join(details)
    
    def convert_to_encoding(self, text: str, target_encoding: str) -> Dict[str, any]:
        """
        将文本转换为指定编码格式并显示相关信息
        
        Args:
            text: 输入文本
            target_encoding: 目标编码格式
            
        Returns:
            包含转换结果的字典
        """
        if not text:
            return {
                'success': False,
                'encoded_bytes': b'',
                'hex_representation': '',
                'byte_length': 0,
                'error_message': '请输入文本进行转换'
            }
        
        try:
            # 将文本编码为指定格式的字节
            encoded_bytes = text.encode(target_encoding)
            
            # 生成十六进制表示
            hex_repr = ' '.join(f'{b:02X}' for b in encoded_bytes)
            
            # 生成可读的字节表示（限制长度）
            if len(encoded_bytes) <= 100:
                byte_repr = str(list(encoded_bytes))
            else:
                byte_repr = str(list(encoded_bytes[:50])) + f" ... (共{len(encoded_bytes)}字节)"
            
            return {
                'success': True,
                'encoded_bytes': encoded_bytes,
                'hex_representation': hex_repr,
                'byte_representation': byte_repr,
                'byte_length': len(encoded_bytes),
                'error_message': ''
            }
            
        except UnicodeEncodeError as e:
            return {
                'success': False,
                'encoded_bytes': b'',
                'hex_representation': '',
                'byte_representation': '',
                'byte_length': 0,
                'error_message': f'编码错误: 无法使用 {target_encoding} 编码字符 "{e.object[e.start:e.end]}"'
            }
        except LookupError:
            return {
                'success': False,
                'encoded_bytes': b'',
                'hex_representation': '',
                'byte_representation': '',
                'byte_length': 0,
                'error_message': f'不支持的编码格式: {target_encoding}'
            }
        except Exception as e:
            return {
                'success': False,
                'encoded_bytes': b'',
                'hex_representation': '',
                'byte_representation': '',
                'byte_length': 0,
                'error_message': f'转换失败: {str(e)}'
            }


class EncodingDetectorGUI:
    """编码检测GUI界面类"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.detector = EncodingDetector()
        self.detection_timer = None
        self.conversion_timer = None
        self.setup_ui()
        self.setup_styles()
    
    def setup_ui(self):
        """设置用户界面"""
        self.root.title("编码格式检测与转换工具")
        self.root.geometry("1000x800")
        self.root.minsize(800, 600)
        
        # 设置图标（如果存在）
        try:
            self.root.iconbitmap("../resource/logo/log.ico")
        except:
            pass
        
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        
        # 标题
        title_label = ttk.Label(
            main_frame, 
            text="编码格式检测与转换工具", 
            font=("微软雅黑", 16, "bold")
        )
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # 创建左右两列布局
        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        
        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(10, 0))
        
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # === 左侧：编码检测功能 ===
        left_frame.columnconfigure(0, weight=1)
        
        # 检测功能标题
        detect_title = ttk.Label(left_frame, text="🔍 编码格式检测", font=("微软雅黑", 12, "bold"))
        detect_title.grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        
        # 输入区域标签
        input_label = ttk.Label(left_frame, text="请输入要检测的文本：", font=("微软雅黑", 10))
        input_label.grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        
        # 文本输入框
        self.text_input = scrolledtext.ScrolledText(
            left_frame,
            height=10,
            width=45,
            font=("Consolas", 11),
            wrap=tk.WORD
        )
        self.text_input.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 15))
        left_frame.rowconfigure(2, weight=2)
        
        # 绑定文本变化事件
        self.text_input.bind('<KeyRelease>', self.on_text_change)
        self.text_input.bind('<Button-1>', self.on_text_change)
        self.text_input.bind('<Control-v>', self.on_text_change)
        
        # 检测结果显示区域
        result_frame = ttk.LabelFrame(left_frame, text="检测结果", padding="10")
        result_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        result_frame.columnconfigure(1, weight=1)
        left_frame.rowconfigure(3, weight=1)
        
        # 编码格式显示
        ttk.Label(result_frame, text="编码格式:", font=("微软雅黑", 10, "bold")).grid(
            row=0, column=0, sticky=tk.W, padx=(0, 10)
        )
        self.detected_encoding_var = tk.StringVar(value="请输入文本")
        self.encoding_label = ttk.Label(
            result_frame, 
            textvariable=self.detected_encoding_var,
            font=("Consolas", 12, "bold"),
            foreground="blue"
        )
        self.encoding_label.grid(row=0, column=1, sticky=tk.W)
        
        # 置信度显示
        ttk.Label(result_frame, text="置信度:", font=("微软雅黑", 10, "bold")).grid(
            row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0)
        )
        self.confidence_var = tk.StringVar(value="0%")
        self.confidence_label = ttk.Label(
            result_frame,
            textvariable=self.confidence_var,
            font=("Consolas", 12)
        )
        self.confidence_label.grid(row=1, column=1, sticky=tk.W, pady=(10, 0))
        
        # 详细信息显示
        ttk.Label(result_frame, text="详细信息:", font=("微软雅黑", 10, "bold")).grid(
            row=2, column=0, sticky=(tk.W, tk.N), padx=(0, 10), pady=(10, 0)
        )
        self.details_text = tk.Text(
            result_frame,
            height=4,
            width=60,
            font=("微软雅黑", 9),
            wrap=tk.WORD,
            state=tk.DISABLED,
            bg="#f0f0f0"
        )
        self.details_text.grid(row=2, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        result_frame.rowconfigure(2, weight=1)
        
        # 检测功能按钮区域
        detect_button_frame = ttk.Frame(left_frame)
        detect_button_frame.grid(row=4, column=0, pady=(10, 0))
        
        # 清空按钮
        clear_btn = ttk.Button(
            detect_button_frame,
            text="清空文本",
            command=self.clear_text
        )
        clear_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 示例按钮
        example_btn = ttk.Button(
            detect_button_frame,
            text="示例文本",
            command=self.load_example
        )
        example_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # === 右侧：编码转换功能 ===
        right_frame.columnconfigure(0, weight=1)
        
        # 转换功能标题
        convert_title = ttk.Label(right_frame, text="🔧 编码格式转换", font=("微软雅黑", 12, "bold"))
        convert_title.grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        
        # 编码选择区域
        encoding_select_frame = ttk.Frame(right_frame)
        encoding_select_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        encoding_select_frame.columnconfigure(1, weight=1)
        
        ttk.Label(encoding_select_frame, text="目标编码：", font=("微软雅黑", 10)).grid(
            row=0, column=0, sticky=tk.W, padx=(0, 10)
        )
        
        # 编码下拉列表
        self.encoding_var = tk.StringVar(value="utf-8")
        encoding_options = []
        for encoding, display_name in self.detector.encoding_display_names.items():
            encoding_options.append(f"{encoding} - {display_name}")
        
        self.encoding_combo = ttk.Combobox(
            encoding_select_frame,
            textvariable=self.encoding_var,
            values=encoding_options,
            state="readonly",
            width=35
        )
        self.encoding_combo.grid(row=0, column=1, sticky=(tk.W, tk.E))
        self.encoding_combo.bind('<<ComboboxSelected>>', self.on_encoding_change)
        
        # 转换输入区域
        convert_input_label = ttk.Label(right_frame, text="请输入要转换的文本：", font=("微软雅黑", 10))
        convert_input_label.grid(row=2, column=0, sticky=tk.W, pady=(10, 5))
        
        self.convert_text_input = scrolledtext.ScrolledText(
            right_frame,
            height=8,
            width=45,
            font=("Consolas", 11),
            wrap=tk.WORD
        )
        self.convert_text_input.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 15))
        right_frame.rowconfigure(3, weight=1)
        
        # 绑定转换文本变化事件
        self.convert_text_input.bind('<KeyRelease>', self.on_convert_text_change)
        self.convert_text_input.bind('<Button-1>', self.on_convert_text_change)
        self.convert_text_input.bind('<Control-v>', self.on_convert_text_change)
        
        # 转换结果显示区域
        convert_result_frame = ttk.LabelFrame(right_frame, text="转换结果", padding="10")
        convert_result_frame.grid(row=4, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        convert_result_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(4, weight=1)
        
        # 字节长度显示
        byte_length_frame = ttk.Frame(convert_result_frame)
        byte_length_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        byte_length_frame.columnconfigure(1, weight=1)
        
        ttk.Label(byte_length_frame, text="字节长度:", font=("微软雅黑", 10, "bold")).grid(
            row=0, column=0, sticky=tk.W, padx=(0, 10)
        )
        self.byte_length_var = tk.StringVar(value="0 字节")
        self.byte_length_label = ttk.Label(
            byte_length_frame,
            textvariable=self.byte_length_var,
            font=("Consolas", 12),
            foreground="blue"
        )
        self.byte_length_label.grid(row=0, column=1, sticky=tk.W)
        
        # 十六进制显示
        ttk.Label(convert_result_frame, text="十六进制表示:", font=("微软雅黑", 10, "bold")).grid(
            row=1, column=0, sticky=tk.W, pady=(10, 5)
        )
        self.hex_text = scrolledtext.ScrolledText(
            convert_result_frame,
            height=3,
            font=("Consolas", 9),
            wrap=tk.WORD,
            state=tk.DISABLED,
            bg="#f8f8f8"
        )
        self.hex_text.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 字节数组显示
        ttk.Label(convert_result_frame, text="字节数组:", font=("微软雅黑", 10, "bold")).grid(
            row=3, column=0, sticky=tk.W, pady=(10, 5)
        )
        self.byte_array_text = scrolledtext.ScrolledText(
            convert_result_frame,
            height=3,
            font=("Consolas", 9),
            wrap=tk.WORD,
            state=tk.DISABLED,
            bg="#f8f8f8"
        )
        self.byte_array_text.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 错误信息显示
        self.error_var = tk.StringVar()
        self.error_label = ttk.Label(
            convert_result_frame,
            textvariable=self.error_var,
            font=("微软雅黑", 9),
            foreground="red",
            wraplength=400
        )
        self.error_label.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        
        # 转换功能按钮区域
        convert_button_frame = ttk.Frame(right_frame)
        convert_button_frame.grid(row=5, column=0, pady=(10, 0))
        
        # 清空转换文本按钮
        clear_convert_btn = ttk.Button(
            convert_button_frame,
            text="清空文本",
            command=self.clear_convert_text
        )
        clear_convert_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 复制结果按钮
        copy_result_btn = ttk.Button(
            convert_button_frame,
            text="复制十六进制",
            command=self.copy_hex_result
        )
        copy_result_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 主按钮区域（跨两列）
        main_button_frame = ttk.Frame(main_frame)
        main_button_frame.grid(row=2, column=0, columnspan=2, pady=(20, 0))
        
        # 关于按钮
        about_btn = ttk.Button(
            main_button_frame,
            text="关于",
            command=self.show_about
        )
        about_btn.pack()
    
    def setup_styles(self):
        """设置界面样式"""
        style = ttk.Style()
        
        # 使用现代主题
        try:
            style.theme_use('clam')
        except:
            pass
        
        # 自定义按钮样式
        style.configure('Modern.TButton', padding=(10, 5))
    
    def on_text_change(self, event=None):
        """检测文本改变事件处理"""
        # 取消之前的定时器
        if self.detection_timer:
            self.root.after_cancel(self.detection_timer)
        
        # 设置新的定时器，延迟检测以避免频繁计算
        self.detection_timer = self.root.after(300, self.detect_encoding_async)
    
    def on_convert_text_change(self, event=None):
        """转换文本改变事件处理"""
        # 取消之前的定时器
        if self.conversion_timer:
            self.root.after_cancel(self.conversion_timer)
        
        # 设置新的定时器，延迟转换以避免频繁计算
        self.conversion_timer = self.root.after(300, self.convert_encoding_async)
    
    def on_encoding_change(self, event=None):
        """编码选择改变事件处理"""
        self.convert_encoding_async()
    
    def detect_encoding_async(self):
        """异步检测编码"""
        text = self.text_input.get(1.0, tk.END).strip()
        
        # 在后台线程中执行检测
        thread = threading.Thread(target=self._detect_and_update, args=(text,))
        thread.daemon = True
        thread.start()
    
    def _detect_and_update(self, text: str):
        """检测编码并更新界面"""
        result = self.detector.detect_encoding(text)
        
        # 在主线程中更新界面
        self.root.after(0, self._update_result, result)
    
    def _update_result(self, result: Dict[str, any]):
        """更新检测结果显示"""
        encoding = result['encoding']
        confidence = result['confidence']
        details = result['details']
        
        # 更新编码格式
        self.detected_encoding_var.set(encoding)
        
        # 更新置信度
        confidence_text = f"{confidence:.1%}" if confidence > 0 else "0%"
        self.confidence_var.set(confidence_text)
        
        # 设置置信度颜色
        if confidence >= 0.8:
            color = "green"
        elif confidence >= 0.5:
            color = "orange"
        else:
            color = "red"
        self.confidence_label.config(foreground=color)
        
        # 更新详细信息
        self.details_text.config(state=tk.NORMAL)
        self.details_text.delete(1.0, tk.END)
        self.details_text.insert(1.0, details)
        self.details_text.config(state=tk.DISABLED)
    
    def clear_text(self):
        """清空检测文本"""
        self.text_input.delete(1.0, tk.END)
        self.detected_encoding_var.set("请输入文本")
        self.confidence_var.set("0%")
        self.details_text.config(state=tk.NORMAL)
        self.details_text.delete(1.0, tk.END)
        self.details_text.config(state=tk.DISABLED)
    
    def load_example(self):
        """加载示例文本"""
        example_texts = [
            "Hello World! 你好世界！",
            "This is ASCII text.",
            "这是中文文本，包含GBK编码特征。",
            "日本語のテキストです。",
            "한국어 텍스트입니다.",
            "Français avec des accents: café, naïve, résumé"
        ]
        
        import random
        example = random.choice(example_texts)
        self.clear_text()
        self.text_input.insert(1.0, example)
        self.on_text_change()
    
    def show_about(self):
        """显示关于信息"""
        about_text = """编码格式检测与转换工具 v2.0

功能特性：
🔍 编码检测功能：
• 实时检测文本编码格式
• 显示检测置信度和详细信息
• 字符类型统计和分析

🔧 编码转换功能：
• 将文本转换为指定编码格式
• 显示十六进制和字节数组表示
• 支持复制结果到剪贴板
• 智能错误处理和提示

✨ 界面特性：
• 现代化双栏布局设计
• 实时响应和异步处理
• 响应式窗口缩放支持

支持的编码格式：
UTF-8, UTF-16, UTF-32, GBK, GB2312, 
GB18030, ASCII, Latin1, Big5, 
Shift_JIS, EUC-JP, EUC-KR 等

技术栈：
Python 3 + Tkinter + chardet + threading

作者：Assistant
版本：2.0"""
        
        messagebox.showinfo("关于", about_text)
    
    def convert_encoding_async(self):
        """异步转换编码"""
        text = self.convert_text_input.get(1.0, tk.END).strip()
        selected_encoding = self.encoding_var.get().split(' - ')[0]  # 提取编码名称
        
        # 在后台线程中执行转换
        thread = threading.Thread(target=self._convert_and_update, args=(text, selected_encoding))
        thread.daemon = True
        thread.start()
    
    def _convert_and_update(self, text: str, encoding: str):
        """转换编码并更新界面"""
        result = self.detector.convert_to_encoding(text, encoding)
        
        # 在主线程中更新界面
        self.root.after(0, self._update_conversion_result, result)
    
    def _update_conversion_result(self, result: Dict[str, any]):
        """更新转换结果显示"""
        if result['success']:
            # 更新字节长度
            self.byte_length_var.set(f"{result['byte_length']} 字节")
            
            # 更新十六进制显示
            self.hex_text.config(state=tk.NORMAL)
            self.hex_text.delete(1.0, tk.END)
            self.hex_text.insert(1.0, result['hex_representation'])
            self.hex_text.config(state=tk.DISABLED)
            
            # 更新字节数组显示
            self.byte_array_text.config(state=tk.NORMAL)
            self.byte_array_text.delete(1.0, tk.END)
            self.byte_array_text.insert(1.0, result['byte_representation'])
            self.byte_array_text.config(state=tk.DISABLED)
            
            # 清空错误信息
            self.error_var.set("")
        else:
            # 显示错误信息
            self.error_var.set(result['error_message'])
            
            # 清空结果显示
            self.byte_length_var.set("0 字节")
            self.hex_text.config(state=tk.NORMAL)
            self.hex_text.delete(1.0, tk.END)
            self.hex_text.config(state=tk.DISABLED)
            self.byte_array_text.config(state=tk.NORMAL)
            self.byte_array_text.delete(1.0, tk.END)
            self.byte_array_text.config(state=tk.DISABLED)
    
    def clear_convert_text(self):
        """清空转换文本"""
        self.convert_text_input.delete(1.0, tk.END)
        self.byte_length_var.set("0 字节")
        self.hex_text.config(state=tk.NORMAL)
        self.hex_text.delete(1.0, tk.END)
        self.hex_text.config(state=tk.DISABLED)
        self.byte_array_text.config(state=tk.NORMAL)
        self.byte_array_text.delete(1.0, tk.END)
        self.byte_array_text.config(state=tk.DISABLED)
        self.error_var.set("")
    
    def copy_hex_result(self):
        """复制十六进制结果到剪贴板"""
        try:
            hex_content = self.hex_text.get(1.0, tk.END).strip()
            if hex_content:
                self.root.clipboard_clear()
                self.root.clipboard_append(hex_content)
                messagebox.showinfo("成功", "十六进制内容已复制到剪贴板")
            else:
                messagebox.showwarning("警告", "没有可复制的内容")
        except Exception as e:
            messagebox.showerror("错误", f"复制失败: {str(e)}")
    
    def run(self):
        """运行应用程序"""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            pass
        except Exception as e:
            messagebox.showerror("错误", f"程序运行出错：{str(e)}")


def main():
    """主函数"""
    try:
        app = EncodingDetectorGUI()
        app.run()
    except Exception as e:
        print(f"程序启动失败：{e}")
        input("按回车键退出...")


if __name__ == "__main__":
    main()
