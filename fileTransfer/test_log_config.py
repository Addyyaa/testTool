#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志配置测试脚本

用于验证统一日志配置系统是否正常工作
"""

from fileTransfer.logger_utils import get_logger
from fileTransfer.log_config import LOG_CONFIG, update_log_level, LogLevel

def test_logging_system():
    """测试日志系统"""
    print("=== 日志配置系统测试 ===\n")
    
    # 显示当前配置
    print("1. 当前日志配置:")
    print(f"   全局日志等级: {LOG_CONFIG['GLOBAL_LOG_LEVEL']} (INFO=20, DEBUG=10)")
    print(f"   模块特定配置: {LOG_CONFIG['MODULE_LOG_LEVELS']}")
    print()
    
    # 测试不同模块的日志器
    print("2. 测试不同模块的日志器:")
    
    # 测试GUI主窗口日志器 (应该是DEBUG等级)
    gui_logger = get_logger("fileTransfer.gui.main_window")
    print(f"   GUI主窗口日志器等级: {gui_logger.level} (应该是10-DEBUG)")
    
    # 测试HTTP服务器日志器 (应该是INFO等级)
    http_logger = get_logger("fileTransfer.http_server")
    print(f"   HTTP服务器日志器等级: {http_logger.level} (应该是20-INFO)")
    
    # 测试未配置模块的日志器 (应该使用全局等级)
    test_logger = get_logger("fileTransfer.test_module")
    print(f"   测试模块日志器等级: {test_logger.level} (应该是20-INFO)")
    print()
    
    # 测试日志输出
    print("3. 测试日志输出:")
    gui_logger.debug("这是GUI的DEBUG信息 - 应该显示")
    gui_logger.info("这是GUI的INFO信息 - 应该显示")
    
    http_logger.debug("这是HTTP的DEBUG信息 - 不应该显示")
    http_logger.info("这是HTTP的INFO信息 - 应该显示")
    
    test_logger.debug("这是测试模块的DEBUG信息 - 不应该显示")
    test_logger.info("这是测试模块的INFO信息 - 应该显示")
    print()
    
    # 测试动态调整日志等级
    print("4. 测试动态调整日志等级:")
    print("   将HTTP服务器日志等级调整为DEBUG...")
    update_log_level(LogLevel.DEBUG, 'fileTransfer.http_server')
    
    print(f"   调整后HTTP服务器日志器等级: {http_logger.level} (应该是10-DEBUG)")
    http_logger.debug("这是调整后的HTTP DEBUG信息 - 现在应该显示")
    print()
    
    print("=== 测试完成 ===")

if __name__ == "__main__":
    test_logging_system() 