import sys
from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow
from service.history_service import HistoryService
from service.telnet_service import TelnetService
from service.http_service import download_log


class MainController:
    def __init__(self, window):
        self.window = window
        self.history_service = HistoryService()
        self.telnet_service = TelnetService()
        self._init_ui()

    def _init_ui(self):
        # 加载历史IP
        self.window.ip_combo.addItems(self.history_service.history)
        self.window.clear_history_btn.clicked.connect(self.clear_history)
        self.window.download_btn.clicked.connect(self.download_log)

    def clear_history(self):
        self.history_service.clear()
        self.window.ip_combo.clear()
        self.window.log_output.append("历史已清除。")

    def set_status(self, msg):
        self.window.status_label.setText(f"状态：{msg}")

    def download_log(self):
        ip = self.window.ip_combo.currentText().strip()
        if not ip:
            self.set_status("请输入IP地址")
            return
        log_items = self.window.log_list.selectedItems()
        if not log_items:
            self.set_status("请选择日志类型")
            return
        log_type = log_items[0].text()
        self.set_status("正在打包日志，请稍候...")
        self.window.log_output.append(f"开始处理 {ip} 的 {log_type} 日志...")

        # 保存历史
        self.history_service.add(ip)
        self.window.ip_combo.clear()
        self.window.ip_combo.addItems(self.history_service.history)

        # 异步处理
        import asyncio
        async def task():
            try:
                await self.telnet_service.pack_log(ip, log_type, username="root", password="ya!2dkwy7-934^")
                self.set_status("日志打包完成，开始下载...")
                local_path = download_log(ip, log_type)
                self.set_status("下载完成")
                self.window.log_output.append(f"日志已保存到: {local_path}")
            except Exception as e:
                import traceback
                self.set_status("操作失败")
                self.window.log_output.append(f"错误: {e}\n{traceback.format_exc()}")

        asyncio.ensure_future(task())


if __name__ == "__main__":
    import asyncio

    app = QApplication(sys.argv)
    window = MainWindow(controller=None)
    controller = MainController(window)
    window.show()
    # 让asyncio和Qt事件循环兼容
    try:
        from qasync import QEventLoop

        loop = QEventLoop(app)
        asyncio.set_event_loop(loop)
        with loop:
            loop.run_forever()
    except ImportError:
        sys.exit(app.exec())
