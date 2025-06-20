#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一日志配置模块

集中管理整个项目的日志配置，包括日志等级、格式、输出等设置
"""

import logging
import os
from typing import Optional, Dict, Any

# 全局日志配置
LOG_CONFIG = {
    # 主要日志等级设置 - 在这里统一修改所有模块的日志等级
    'GLOBAL_LOG_LEVEL': logging.DEBUG,  # 可选: DEBUG, INFO, WARNING, ERROR, CRITICAL
    
    # 各模块的特定日志等级设置（可选）
    'MODULE_LOG_LEVELS': {
        'fileTransfer.gui.main_window': logging.DEBUG,  # GUI主窗口使用DEBUG等级
        'fileTransfer.http_server': logging.INFO,       # HTTP服务器使用INFO等级
        'fileTransfer.file_transfer_controller': logging.INFO,  # 文件传输控制器
        'telnetTool.telnetConnect': logging.WARNING,    # Telnet连接使用WARNING等级
        
        # 拖拽下载功能模块
        'drag_download_manager.DragDownloadManager': logging.INFO,    # 下载管理器显示基本信息
        'drag_handler.DragHandler': logging.DEBUG,                   # 拖拽处理器显示详细调试信息
        'directory_panel.DirectoryPanel': logging.DEBUG,             # 目录面板显示详细调试信息
    },
    
    # 日志格式设置
    'LOG_FORMAT': '%(asctime)s - %(levelname)s - %(name)s:%(lineno)d - %(message)s',
    'DATE_FORMAT': '%Y-%m-%d %H:%M:%S',
    
    # 控制台输出设置
    'CONSOLE_LOG_LEVEL': logging.INFO,  # 控制台日志等级
    'ENABLE_CONSOLE_LOG': True,         # 是否启用控制台日志
    
    # 文件输出设置
    'ENABLE_FILE_LOG': False,           # 是否启用文件日志
    'LOG_FILE_PATH': 'logs/app.log',    # 日志文件路径
    'FILE_LOG_LEVEL': logging.DEBUG,    # 文件日志等级
    'MAX_FILE_SIZE': 10 * 1024 * 1024,  # 最大文件大小 (10MB)
    'BACKUP_COUNT': 5,                  # 备份文件数量
}


def get_log_level(module_name: str) -> int:
    """获取指定模块的日志等级
    
    Args:
        module_name: 模块名称
        
    Returns:
        日志等级
    """
    # 首先检查是否有模块特定的日志等级设置
    if module_name in LOG_CONFIG['MODULE_LOG_LEVELS']:
        return LOG_CONFIG['MODULE_LOG_LEVELS'][module_name]
    
    # 否则使用全局日志等级
    return LOG_CONFIG['GLOBAL_LOG_LEVEL']


def setup_logging(logger_name: Optional[str] = None) -> logging.Logger:
    """设置日志系统
    
    Args:
        logger_name: 日志器名称，如果为None则设置根日志器
        
    Returns:
        配置好的日志器
    """
    # 获取或创建日志器
    if logger_name:
        logger = logging.getLogger(logger_name)
        log_level = get_log_level(logger_name)
    else:
        logger = logging.getLogger()
        log_level = LOG_CONFIG['GLOBAL_LOG_LEVEL']
    
    # 设置日志等级
    logger.setLevel(log_level)
    
    # 清除现有的处理器（避免重复添加）
    logger.handlers.clear()
    
    # 创建格式器
    formatter = logging.Formatter(
        LOG_CONFIG['LOG_FORMAT'],
        datefmt=LOG_CONFIG['DATE_FORMAT']
    )
    
    # 添加控制台处理器
    if LOG_CONFIG['ENABLE_CONSOLE_LOG']:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(LOG_CONFIG['CONSOLE_LOG_LEVEL'])
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # 添加文件处理器
    if LOG_CONFIG['ENABLE_FILE_LOG']:
        # 确保日志目录存在
        log_dir = os.path.dirname(LOG_CONFIG['LOG_FILE_PATH'])
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            LOG_CONFIG['LOG_FILE_PATH'],
            maxBytes=LOG_CONFIG['MAX_FILE_SIZE'],
            backupCount=LOG_CONFIG['BACKUP_COUNT'],
            encoding='utf-8'
        )
        file_handler.setLevel(LOG_CONFIG['FILE_LOG_LEVEL'])
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def configure_global_logging():
    """配置全局日志系统"""
    # 设置根日志器
    root_logger = setup_logging()
    
    # 设置第三方库的日志等级（避免过多输出）
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    
    return root_logger


def update_log_level(level: int, module_name: Optional[str] = None):
    """动态更新日志等级
    
    Args:
        level: 新的日志等级
        module_name: 模块名称，如果为None则更新全局等级
    """
    if module_name:
        LOG_CONFIG['MODULE_LOG_LEVELS'][module_name] = level
        logger = logging.getLogger(module_name)
        logger.setLevel(level)
    else:
        LOG_CONFIG['GLOBAL_LOG_LEVEL'] = level
        logging.getLogger().setLevel(level)


def get_current_config() -> Dict[str, Any]:
    """获取当前日志配置
    
    Returns:
        当前的日志配置字典
    """
    return LOG_CONFIG.copy()


# 日志等级常量，方便使用
class LogLevel:
    """日志等级常量"""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL


# 在模块导入时自动配置全局日志
configure_global_logging() 