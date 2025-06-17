#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
连接问题调试工具
专门用于测试和调试连接过程中的卡死问题
"""

import tkinter as tk
from tkinter import messagebox
import threading
import asyncio
import time
import logging
from datetime import datetime

class ConnectionDebugger:
    def __init__(self):
        self.setup_logging()
        self.setup_gui()
        self.telnet_client = None
        self.is_connected = False
        
    def setup_logging(self):
        """设置详细的日志记录"""
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('connection_debug.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def setup_gui(self):
        """创建简单的调试界面"""
        self.root = tk.Tk()
        self.root.title("连接调试工具")
        self.root.geometry("600x500")
        
        # 连接信息
        tk.Label(self.root, text="IP地址:").pack(pady=5)
        self.ip_entry = tk.Entry(self.root, width=30)
        self.ip_entry.pack(pady=5)
        self.ip_entry.insert(0, "192.168.1.45")
        
        tk.Label(self.root, text="用户名:").pack(pady=5)
        self.username_entry = tk.Entry(self.root, width=30)
        self.username_entry.pack(pady=5)
        self.username_entry.insert(0, "root")
        
        tk.Label(self.root, text="密码:").pack(pady=5)
        self.password_entry = tk.Entry(self.root, width=30, show='*')
        self.password_entry.pack(pady=5)
        self.password_entry.insert(0, "ya!2dkwy7-934^")
        
        # 测试按钮
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=20)
        
        self.test1_btn = tk.Button(button_frame, text="测试1: 简单连接", 
                                  command=self.test_simple_connection, width=15)
        self.test1_btn.pack(side=tk.LEFT, padx=5)
        
        self.test2_btn = tk.Button(button_frame, text="测试2: 无事件循环", 
                                  command=self.test_no_event_loop, width=15)
        self.test2_btn.pack(side=tk.LEFT, padx=5)
        
        self.test3_btn = tk.Button(button_frame, text="测试3: 同步连接", 
                                  command=self.test_sync_connection, width=15)
        self.test3_btn.pack(side=tk.LEFT, padx=5)
        
        # 状态显示
        self.status_label = tk.Label(self.root, text="就绪", fg="blue")
        self.status_label.pack(pady=10)
        
        # 日志显示
        self.log_text = tk.Text(self.root, height=15, width=70)
        self.log_text.pack(pady=10, fill=tk.BOTH, expand=True)
        
        # 滚动条
        scrollbar = tk.Scrollbar(self.log_text)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.log_text.yview)
        
    def log_message(self, message):
        """在界面上显示日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        full_message = f"[{timestamp}] {message}\n"
        
        def update_log():
            self.log_text.insert(tk.END, full_message)
            self.log_text.see(tk.END)
            
        if threading.current_thread() == threading.main_thread():
            update_log()
        else:
            self.root.after(0, update_log)
            
        self.logger.info(message)
        
    def update_status(self, status, color="black"):
        """更新状态显示"""
        def update():
            self.status_label.config(text=status, fg=color)
            
        if threading.current_thread() == threading.main_thread():
            update()
        else:
            self.root.after(0, update)
    
    def test_simple_connection(self):
        """测试1: 简单连接测试，使用原始的异步架构"""
        self.log_message("=== 开始测试1: 简单连接 ===")
        self.update_status("测试中...", "orange")
        
        def test_thread():
            try:
                self.log_message("步骤1: 导入telnet客户端")
                from telnetTool.telnetConnect import CustomTelnetClient
                
                self.log_message("步骤2: 创建telnet客户端实例")
                self.telnet_client = CustomTelnetClient(
                    host=self.ip_entry.get().strip(),
                    port=23,
                    timeout=10.0
                )
                
                self.log_message("步骤3: 启动事件循环")
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                self.log_message("步骤4: 开始连接")
                async def connect_test():
                    success = await self.telnet_client.connect(
                        username=self.username_entry.get().strip(),
                        password=self.password_entry.get(),
                        shell_prompt='#'
                    )
                    if success:
                        self.log_message("步骤5: 连接成功，执行测试命令")
                        result = await self.telnet_client.execute_command('pwd')
                        self.log_message(f"命令结果: {result}")
                        return True
                    return False
                
                result = loop.run_until_complete(connect_test())
                loop.close()
                
                if result:
                    self.log_message("测试1成功完成")
                    self.update_status("测试1: 成功", "green")
                else:
                    self.log_message("测试1失败")
                    self.update_status("测试1: 失败", "red")
                    
            except Exception as e:
                self.log_message(f"测试1异常: {str(e)}")
                self.update_status("测试1: 异常", "red")
                import traceback
                self.log_message(f"详细错误: {traceback.format_exc()}")
        
        threading.Thread(target=test_thread, daemon=True).start()
    
    def test_no_event_loop(self):
        """测试2: 不使用独立事件循环的连接测试"""
        self.log_message("=== 开始测试2: 无独立事件循环 ===")
        self.update_status("测试中...", "orange")
        
        def test_thread():
            try:
                self.log_message("步骤1: 导入telnet客户端")
                from telnetTool.telnetConnect import CustomTelnetClient
                
                self.log_message("步骤2: 创建telnet客户端实例")
                self.telnet_client = CustomTelnetClient(
                    host=self.ip_entry.get().strip(),
                    port=23,
                    timeout=10.0
                )
                
                self.log_message("步骤3: 直接使用asyncio.run执行连接")
                async def connect_test():
                    self.log_message("步骤3.1: 开始异步连接")
                    success = await self.telnet_client.connect(
                        username=self.username_entry.get().strip(),
                        password=self.password_entry.get(),
                        shell_prompt='#'
                    )
                    
                    if success:
                        self.log_message("步骤3.2: 连接成功，执行测试命令")
                        result = await self.telnet_client.execute_command('pwd')
                        self.log_message(f"命令结果: {result}")
                        
                        self.log_message("步骤3.3: 执行ls命令测试")
                        result = await self.telnet_client.execute_command('ls -la')
                        self.log_message(f"ls结果: {result[:200]}...")  # 只显示前200字符
                        
                        return True
                    return False
                
                # 使用asyncio.run而不是独立的事件循环
                result = asyncio.run(connect_test())
                
                if result:
                    self.log_message("测试2成功完成")
                    self.update_status("测试2: 成功", "green")
                else:
                    self.log_message("测试2失败")
                    self.update_status("测试2: 失败", "red")
                    
            except Exception as e:
                self.log_message(f"测试2异常: {str(e)}")
                self.update_status("测试2: 异常", "red")
                import traceback
                self.log_message(f"详细错误: {traceback.format_exc()}")
        
        threading.Thread(target=test_thread, daemon=True).start()
    
    def test_sync_connection(self):
        """测试3: 模拟原始程序的连接流程"""
        self.log_message("=== 开始测试3: 模拟原程序流程 ===")
        self.update_status("测试中...", "orange")
        
        def test_thread():
            try:
                self.log_message("步骤1: 启动独立事件循环线程")
                loop = asyncio.new_event_loop()
                
                def run_loop():
                    asyncio.set_event_loop(loop)
                    self.log_message("事件循环线程已启动")
                    loop.run_forever()
                
                loop_thread = threading.Thread(target=run_loop, daemon=True)
                loop_thread.start()
                
                # 等待事件循环启动
                time.sleep(0.1)
                
                self.log_message("步骤2: 创建telnet客户端")
                from telnetTool.telnetConnect import CustomTelnetClient
                self.telnet_client = CustomTelnetClient(
                    host=self.ip_entry.get().strip(),
                    port=23,
                    timeout=10.0
                )
                
                self.log_message("步骤3: 在事件循环中执行连接")
                async def connect_test():
                    success = await self.telnet_client.connect(
                        username=self.username_entry.get().strip(),
                        password=self.password_entry.get(),
                        shell_prompt='#'
                    )
                    if success:
                        result = await self.telnet_client.execute_command('pwd')
                        self.log_message(f"命令结果: {result}")
                        return True
                    return False
                
                # 模拟原程序的调用方式
                future = asyncio.run_coroutine_threadsafe(connect_test(), loop)
                self.log_message("步骤4: 等待连接结果...")
                
                # 这里是可能卡死的地方
                result = future.result(timeout=15)
                
                if result:
                    self.log_message("测试3成功完成")
                    self.update_status("测试3: 成功", "green")
                else:
                    self.log_message("测试3失败")
                    self.update_status("测试3: 失败", "red")
                
                # 停止事件循环
                loop.call_soon_threadsafe(loop.stop)
                    
            except Exception as e:
                self.log_message(f"测试3异常: {str(e)}")
                self.update_status("测试3: 异常", "red")
                import traceback
                self.log_message(f"详细错误: {traceback.format_exc()}")
        
        threading.Thread(target=test_thread, daemon=True).start()
    
    def run(self):
        """启动调试工具"""
        self.log_message("连接调试工具已启动")
        self.log_message("请选择测试方法来诊断连接问题")
        self.root.mainloop()

if __name__ == "__main__":
    debugger = ConnectionDebugger()
    debugger.run() 