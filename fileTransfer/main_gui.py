#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
现代化文件传输工具主入口

模块化重构后的主入口，使用组件化的GUI架构
"""

import os
import sys

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 导入新的模块化GUI
from fileTransfer.gui import ModernFileTransferGUI


def main():
    """主程序入口"""
    try:
        # 创建并运行GUI应用
        app = ModernFileTransferGUI()
        app.run()
    except ImportError as e:
        print(f"缺少依赖模块: {e}")
        print("请安装必要的依赖:")
        print("pip install tkinterdnd2 telnetlib3")
    except Exception as e:
        print(f"程序启动失败: {e}")
        import traceback  
        traceback.print_exc()


if __name__ == "__main__":
    main()