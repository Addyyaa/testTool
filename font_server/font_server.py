#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
字体服务器 - 根据客户端需求动态生成字体子集文件
用于解决终端设备存储空间有限但需要国际化支持的问题

作者: Assistant
日期: 2024
版本: 1.0.0
"""

import os
import sys
import json
import hashlib
import logging
import argparse
from pathlib import Path
from typing import Set, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import threading
import time

from flask import Flask, request, jsonify, send_file, Response
from werkzeug.serving import make_server
import fontTools.subset
from fontTools.ttLib import TTFont
from fontTools.fontBuilder import FontBuilder


class FontSubsetCache:
    """字体子集缓存管理器"""
    
    def __init__(self, cache_dir: str = "cache", max_cache_size: int = 100, cache_ttl: int = 3600):
        """
        初始化缓存管理器
        
        Args:
            cache_dir: 缓存目录
            max_cache_size: 最大缓存数量
            cache_ttl: 缓存过期时间（秒）
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.max_cache_size = max_cache_size
        self.cache_ttl = cache_ttl
        self.cache_info: Dict[str, Dict] = {}
        self._lock = threading.RLock()
        
        # 启动清理线程
        self._cleanup_thread = threading.Thread(target=self._cleanup_expired, daemon=True)
        self._cleanup_thread.start()
        
        # 加载现有缓存信息
        self._load_cache_info()
    
    def _load_cache_info(self):
        """加载缓存信息"""
        info_file = self.cache_dir / "cache_info.json"
        if info_file.exists():
            try:
                with open(info_file, 'r', encoding='utf-8') as f:
                    self.cache_info = json.load(f)
                    
                # 清理已不存在的文件
                to_remove = []
                for cache_key, info in self.cache_info.items():
                    cache_file = self.cache_dir / info['filename']
                    if not cache_file.exists():
                        to_remove.append(cache_key)
                
                for key in to_remove:
                    del self.cache_info[key]
                    
            except Exception as e:
                logging.warning(f"加载缓存信息失败: {e}")
                self.cache_info = {}
    
    def _save_cache_info(self):
        """保存缓存信息"""
        info_file = self.cache_dir / "cache_info.json"
        try:
            with open(info_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache_info, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"保存缓存信息失败: {e}")
    
    def _cleanup_expired(self):
        """清理过期缓存"""
        while True:
            try:
                time.sleep(300)  # 每5分钟检查一次
                with self._lock:
                    current_time = datetime.now().timestamp()
                    to_remove = []
                    
                    for cache_key, info in self.cache_info.items():
                        if current_time - info['created_at'] > self.cache_ttl:
                            to_remove.append(cache_key)
                    
                    for key in to_remove:
                        self._remove_cache_file(key)
                        
            except Exception as e:
                logging.error(f"清理缓存失败: {e}")
    
    def _remove_cache_file(self, cache_key: str):
        """移除缓存文件"""
        if cache_key in self.cache_info:
            info = self.cache_info[cache_key]
            cache_file = self.cache_dir / info['filename']
            
            try:
                if cache_file.exists():
                    cache_file.unlink()
                del self.cache_info[cache_key]
                logging.info(f"移除缓存文件: {cache_key}")
            except Exception as e:
                logging.error(f"移除缓存文件失败 {cache_key}: {e}")
    
    def get_cache_key(self, font_path: str, characters: Set[str], format_type: str) -> str:
        """生成缓存键"""
        # 使用字体文件路径、字符集合和格式生成唯一键
        char_str = ''.join(sorted(characters))
        content = f"{font_path}:{char_str}:{format_type}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def get(self, cache_key: str) -> Optional[Path]:
        """获取缓存文件"""
        with self._lock:
            if cache_key in self.cache_info:
                info = self.cache_info[cache_key]
                cache_file = self.cache_dir / info['filename']
                
                # 检查文件是否存在且未过期
                if cache_file.exists():
                    current_time = datetime.now().timestamp()
                    if current_time - info['created_at'] <= self.cache_ttl:
                        # 更新访问时间
                        info['last_accessed'] = current_time
                        return cache_file
                    else:
                        # 过期，移除
                        self._remove_cache_file(cache_key)
                else:
                    # 文件不存在，移除记录
                    del self.cache_info[cache_key]
            
            return None
    
    def put(self, cache_key: str, font_data: bytes, format_type: str) -> Path:
        """存储缓存文件"""
        with self._lock:
            # 检查缓存大小限制
            if len(self.cache_info) >= self.max_cache_size:
                self._cleanup_oldest()
            
            # 生成文件名
            timestamp = int(datetime.now().timestamp())
            filename = f"{cache_key}_{timestamp}.{format_type.lower()}"
            cache_file = self.cache_dir / filename
            
            # 写入文件
            with open(cache_file, 'wb') as f:
                f.write(font_data)
            
            # 更新缓存信息
            current_time = datetime.now().timestamp()
            self.cache_info[cache_key] = {
                'filename': filename,
                'created_at': current_time,
                'last_accessed': current_time,
                'size': len(font_data),
                'format': format_type
            }
            
            self._save_cache_info()
            logging.info(f"缓存字体文件: {cache_key} -> {filename}")
            
            return cache_file
    
    def _cleanup_oldest(self):
        """清理最旧的缓存"""
        if not self.cache_info:
            return
        
        # 按访问时间排序，删除最旧的
        oldest_key = min(self.cache_info.keys(), 
                        key=lambda k: self.cache_info[k]['last_accessed'])
        self._remove_cache_file(oldest_key)
    
    def get_stats(self) -> Dict:
        """获取缓存统计信息"""
        with self._lock:
            total_size = sum(info['size'] for info in self.cache_info.values())
            return {
                'cache_count': len(self.cache_info),
                'total_size': total_size,
                'max_cache_size': self.max_cache_size,
                'cache_ttl': self.cache_ttl,
                'cache_dir': str(self.cache_dir)
            }


class FontProcessor:
    """字体处理器"""
    
    def __init__(self):
        """初始化字体处理器"""
        self.supported_formats = ['ttf', 'otf', 'woff', 'woff2', 'ttc']
    
    def validate_font_file(self, font_path: str) -> bool:
        """验证字体文件"""
        if not os.path.isfile(font_path):
            return False
        
        try:
            # 对于TTC文件，需要特殊处理
            if font_path.lower().endswith('.ttc'):
                # TTC文件包含多个字体，验证第一个
                font = TTFont(font_path, fontNumber=0)
            else:
                font = TTFont(font_path)
            font.close()
            return True
        except Exception as e:
            logging.error(f"字体文件验证失败 {font_path}: {e}")
            return False
    
    def get_available_characters(self, font_path: str) -> Set[str]:
        """获取字体文件中可用的字符"""
        try:
            # 对于TTC文件，使用第一个字体
            if font_path.lower().endswith('.ttc'):
                font = TTFont(font_path, fontNumber=0)
            else:
                font = TTFont(font_path)
                
            cmap = font.getBestCmap()
            characters = set()
            
            for unicode_value in cmap.keys():
                try:
                    character = chr(unicode_value)
                    characters.add(character)
                except ValueError:
                    # 跳过无效的Unicode值
                    continue
            
            font.close()
            return characters
            
        except Exception as e:
            logging.error(f"获取字体字符失败 {font_path}: {e}")
            return set()
    
    def create_font_subset(self, font_path: str, characters: Set[str], 
                          output_format: str = 'ttf') -> bytes:
        """
        创建字体子集
        
        Args:
            font_path: 源字体文件路径
            characters: 需要的字符集合
            output_format: 输出格式 (ttf, otf, woff, woff2)
            
        Returns:
            字体文件的二进制数据
        """
        try:
            # 创建临时文件
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=f'.{output_format}', delete=False) as tmp_file:
                temp_output = tmp_file.name
            
            # 加载原始字体，检查哪些字符实际存在
            # 对于TTC文件，使用第一个字体
            if font_path.lower().endswith('.ttc'):
                font = TTFont(font_path, fontNumber=0)
                logging.info(f"处理TTC字体文件: {font_path} (使用第一个字体)")
            else:
                font = TTFont(font_path)
                
            cmap = font.getBestCmap()
            
            # 只保留字体中实际存在的字符
            valid_unicodes = []
            valid_chars = set()
            
            for char in characters:
                unicode_val = ord(char)
                if unicode_val in cmap:
                    valid_unicodes.append(unicode_val)
                    valid_chars.add(char)
                else:
                    logging.warning(f"字体中不存在字符: '{char}' (U+{unicode_val:04X})")
            
            if not valid_unicodes:
                font.close()
                raise ValueError("字体中不包含任何请求的字符")
            
            logging.info(f"字体中存在的字符: {len(valid_chars)} / {len(characters)}")
            
            # 使用fontTools创建子集 - 使用更严格的设置
            subsetter = fontTools.subset.Subsetter()
            
            # 严格模式：只保留必要的内容
            subsetter.options.layout_features = []  # 不保留布局特性
            subsetter.options.name_IDs = [1, 2]     # 只保留基本名称 (Family, Subfamily)
            subsetter.options.hinting = False       # 不保留提示信息
            subsetter.options.glyph_names = False   # 不保留字形名称
            subsetter.options.legacy_kern = False   # 不保留旧版字距调整
            subsetter.options.notdef_glyph = True   # 保留.notdef字形
            subsetter.options.notdef_outline = False # 不保留.notdef轮廓
            subsetter.options.recommended_glyphs = False  # 不包含推荐字形
            subsetter.options.recalc_bounds = True  # 重新计算边界
            subsetter.options.recalc_timestamp = True  # 重新计算时间戳
            
            # 执行子集化 - 只包含指定的Unicode码点
            subsetter.populate(unicodes=valid_unicodes)
            subsetter.subset(font)
            
            # 保存到临时文件 - TTC文件只能输出为TTF格式
            if output_format.lower() == 'woff':
                font.flavor = 'woff'
            elif output_format.lower() == 'woff2':
                font.flavor = 'woff2'
            
            font.save(temp_output)
            font.close()
            
            # 读取生成的文件
            with open(temp_output, 'rb') as f:
                font_data = f.read()
            
            # 清理临时文件
            os.unlink(temp_output)
            
            logging.info(f"成功创建字体子集: {len(valid_chars)} 个字符, 格式: {output_format}")
            return font_data
            
        except Exception as e:
            logging.error(f"创建字体子集失败: {e}")
            raise


class FontServer:
    """字体服务器主类"""
    
    def __init__(self, fonts_dir: str = "fonts", cache_dir: str = "cache", 
                 host: str = "0.0.0.0", port: int = 8889):
        """
        初始化字体服务器
        
        Args:
            fonts_dir: 字体文件目录
            cache_dir: 缓存目录
            host: 服务器主机地址
            port: 服务器端口
        """
        self.fonts_dir = Path(fonts_dir)
        self.fonts_dir.mkdir(exist_ok=True)
        
        self.host = host
        self.port = port
        
        # 初始化组件
        self.cache = FontSubsetCache(cache_dir)
        self.processor = FontProcessor()
        
        # 创建Flask应用
        self.app = Flask(__name__)
        self.app.json.ensure_ascii = False
        
        # 注册路由
        self._register_routes()
        
        # 扫描可用字体
        self.available_fonts = self._scan_fonts()
        
        logging.info(f"字体服务器初始化完成，发现 {len(self.available_fonts)} 个字体文件")
    
    def _scan_fonts(self) -> Dict[str, str]:
        """扫描可用字体文件"""
        fonts = {}
        
        for font_file in self.fonts_dir.rglob("*"):
            if font_file.is_file() and font_file.suffix.lower()[1:] in self.processor.supported_formats:
                if self.processor.validate_font_file(str(font_file)):
                    # 使用相对路径作为字体名称
                    font_name = str(font_file.relative_to(self.fonts_dir))
                    fonts[font_name] = str(font_file)
                    
        return fonts
    
    def _register_routes(self):
        """注册API路由"""
        
        @self.app.route('/api/fonts', methods=['GET'])
        def list_fonts():
            """获取可用字体列表"""
            try:
                fonts_info = {}
                for font_name, font_path in self.available_fonts.items():
                    # 获取字体基本信息
                    font_info = {
                        'path': font_name,
                        'size': os.path.getsize(font_path),
                        'modified': os.path.getmtime(font_path)
                    }
                    
                    # 尝试获取字体元信息
                    try:
                        font = TTFont(font_path)
                        name_table = font['name']
                        
                        # 获取字体家族名
                        family_name = None
                        for record in name_table.names:
                            if record.nameID == 1:  # Family name
                                try:
                                    family_name = record.toUnicode()
                                    break
                                except:
                                    continue
                        
                        if family_name:
                            font_info['family_name'] = family_name
                        
                        font.close()
                    except:
                        pass
                    
                    fonts_info[font_name] = font_info
                
                return jsonify({
                    'success': True,
                    'fonts': fonts_info,
                    'count': len(fonts_info)
                })
                
            except Exception as e:
                logging.error(f"获取字体列表失败: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/font/characters/<path:font_name>', methods=['GET'])
        def get_font_characters(font_name):
            """获取字体中可用的字符"""
            try:
                if font_name not in self.available_fonts:
                    return jsonify({'success': False, 'error': '字体不存在'}), 404
                
                font_path = self.available_fonts[font_name]
                characters = self.processor.get_available_characters(font_path)
                
                return jsonify({
                    'success': True,
                    'font': font_name,
                    'characters': list(characters),
                    'count': len(characters)
                })
                
            except Exception as e:
                logging.error(f"获取字体字符失败: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/font/subset/<path:font_name>', methods=['POST'])
        def create_font_subset(font_name):
            """创建字体子集"""
            try:
                if font_name not in self.available_fonts:
                    return jsonify({'success': False, 'error': '字体不存在'}), 404
                
                # 获取请求参数
                data = request.get_json()
                if not data:
                    return jsonify({'success': False, 'error': '缺少请求数据'}), 400
                
                # 支持两种参数格式：text（字符串）或 characters（字符数组）
                text = data.get('text', '')
                characters = data.get('characters', [])
                
                # 优先使用text参数，如果没有则使用characters参数
                if text:
                    # 从文字字符串中提取唯一字符
                    char_set = set(text)
                elif characters:
                    # 兼容原有的字符数组格式
                    char_set = set(characters)
                else:
                    return jsonify({'success': False, 'error': '缺少文字内容，请提供text或characters参数'}), 400
                
                output_format = data.get('format', 'ttf').lower()
                if output_format not in self.processor.supported_formats:
                    return jsonify({'success': False, 'error': f'不支持的格式: {output_format}'}), 400
                
                font_path = self.available_fonts[font_name]
                
                # 检查缓存
                cache_key = self.cache.get_cache_key(font_path, char_set, output_format)
                cached_file = self.cache.get(cache_key)
                
                if cached_file:
                    logging.info(f"使用缓存字体文件: {cache_key}")
                    return send_file(
                        cached_file,
                        as_attachment=True,
                        download_name=f"{Path(font_name).stem}_subset.{output_format}",
                        mimetype=f'font/{output_format}'
                    )
                
                # 创建字体子集
                font_data = self.processor.create_font_subset(font_path, char_set, output_format)
                
                # 缓存结果
                cached_file = self.cache.put(cache_key, font_data, output_format)
                
                return send_file(
                    cached_file,
                    as_attachment=True,
                    download_name=f"{Path(font_name).stem}_subset.{output_format}",
                    mimetype=f'font/{output_format}'
                )
                
            except Exception as e:
                logging.error(f"创建字体子集失败: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/stats', methods=['GET'])
        def get_stats():
            """获取服务器统计信息"""
            try:
                cache_stats = self.cache.get_stats()
                
                return jsonify({
                    'success': True,
                    'stats': {
                        'fonts_count': len(self.available_fonts),
                        'fonts_dir': str(self.fonts_dir),
                        'cache': cache_stats,
                        'server': {
                            'host': self.host,
                            'port': self.port
                        }
                    }
                })
                
            except Exception as e:
                logging.error(f"获取统计信息失败: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/cache/clear', methods=['POST'])
        def clear_cache():
            """清理缓存"""
            try:
                import shutil
                shutil.rmtree(self.cache.cache_dir)
                self.cache.cache_dir.mkdir(exist_ok=True)
                self.cache.cache_info = {}
                self.cache._save_cache_info()
                
                return jsonify({'success': True, 'message': '缓存已清理'})
                
            except Exception as e:
                logging.error(f"清理缓存失败: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/health', methods=['GET'])
        def health_check():
            """健康检查"""
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'version': '1.0.0'
            })
        
        @self.app.errorhandler(404)
        def not_found(error):
            return jsonify({'success': False, 'error': 'API不存在'}), 404
        
        @self.app.errorhandler(500)
        def internal_error(error):
            return jsonify({'success': False, 'error': '服务器内部错误'}), 500
    
    def run(self, debug: bool = False):
        """启动服务器"""
        try:
            logging.info(f"字体服务器启动在 http://{self.host}:{self.port}")
            logging.info(f"API文档: http://{self.host}:{self.port}/health")
            
            # 使用Werkzeug的多线程服务器
            server = make_server(self.host, self.port, self.app, threaded=True)
            server.serve_forever()
            
        except KeyboardInterrupt:
            logging.info("服务器已停止")
        except Exception as e:
            logging.error(f"服务器启动失败: {e}")
            raise


def setup_logging(level: str = "INFO"):
    """设置日志"""
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('font_server.log', encoding='utf-8')
        ]
    )


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='字体服务器 - 动态字体子集化服务')
    parser.add_argument('--fonts-dir', default='fonts', help='字体文件目录 (默认: fonts)')
    parser.add_argument('--cache-dir', default='cache', help='缓存目录 (默认: cache)')
    parser.add_argument('--host', default='0.0.0.0', help='服务器主机地址 (默认: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=8889, help='服务器端口 (默认: 8889)')
    parser.add_argument('--log-level', default='INFO', 
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='日志级别 (默认: INFO)')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    
    args = parser.parse_args()
    
    # 设置日志
    setup_logging(args.log_level)
    
    # 创建并启动服务器
    server = FontServer(
        fonts_dir=args.fonts_dir,
        cache_dir=args.cache_dir,
        host=args.host,
        port=args.port
    )
    
    server.run(debug=args.debug)


if __name__ == '__main__':
    main()
