from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QComboBox, QPushButton, QListWidget, QLabel, QTextEdit, QSizePolicy, QAbstractItemView
)
from PySide6.QtCore import Qt

class MainWindow(QMainWindow):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setWindowTitle("日志获取工具")
        self.resize(700, 500)

        # 主部件和主布局
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)

        # 顶部：IP输入和历史
        ip_layout = QHBoxLayout()
        self.ip_combo = QComboBox()
        self.ip_combo.setEditable(True)
        self.ip_combo.setPlaceholderText("请输入设备IP")
        self.clear_history_btn = QPushButton("清除历史")
        ip_layout.addWidget(QLabel("设备IP:"))
        ip_layout.addWidget(self.ip_combo)
        ip_layout.addWidget(self.clear_history_btn)
        main_layout.addLayout(ip_layout)

        # 中部：日志类型选择
        self.log_list = QListWidget()
        self.log_list.addItems(["视频", "图片", "mqtt", "daemon", "screen", "蓝牙", "misc"])
        self.log_list.setSelectionMode(QAbstractItemView.SingleSelection)
        main_layout.addWidget(QLabel("选择日志类型:"))
        main_layout.addWidget(self.log_list)

        # 操作按钮
        self.download_btn = QPushButton("获取日志")
        main_layout.addWidget(self.download_btn)

        # 底部：状态/日志输出
        self.status_label = QLabel("状态：等待操作")
        self.status_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        main_layout.addWidget(self.status_label)
        main_layout.addWidget(self.log_output, stretch=1)

        self.setCentralWidget(central_widget)
