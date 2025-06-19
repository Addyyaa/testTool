"""logger_utils
通用日志工具模块

提供 get_logger 函数，根据给定的类、模块或字符串生成合适的 logger 名称，
保证日志定位精确到源码位置。

遵循项目代码规范：
1. 代码需包含中文文档字符串。
2. 不使用全局可变状态。
3. 覆盖率简单易测。
"""

from __future__ import annotations

import inspect
import logging
import os
from pathlib import Path
from types import ModuleType
from typing import Union, Type

__all__ = ["get_logger"]


def _path_to_module(file_path: str) -> str:
    """将文件路径转换为类似 package.module 的格式。

    假设工程根目录下存在类似 *fileTransfer/main_gui.py* ，
    则返回 ``fileTransfer.main_gui``。
    如果无法定位 "fileTransfer"，则仅返回文件名去掉后缀。
    """
    try:
        p = Path(file_path).resolve()
        parts = list(p.parts)
        if "fileTransfer" in parts:
            idx = parts.index("fileTransfer")
            module_parts = parts[idx:]  # 从 fileTransfer 开始
            module_parts[-1] = module_parts[-1].rsplit(".", 1)[0]  # 去掉 .py
            return ".".join(module_parts)
        # 未找到 fileTransfer，退化为文件名
        return p.stem
    except Exception:
        return os.path.splitext(os.path.basename(file_path))[0]


def _build_logger_name(owner: Union[Type, ModuleType, str]) -> str:
    """根据传入对象构造 logger 名称。"""
    if isinstance(owner, str):
        return owner

    if isinstance(owner, ModuleType):
        module_name = owner.__name__
        if module_name == "__main__":
            file_path = getattr(owner, "__file__", None)
            if file_path:
                module_name = _path_to_module(file_path)
        return module_name

    if isinstance(owner, type):
        module_name = owner.__module__
        if module_name == "__main__":
            # 运行脚本方式，尝试从文件路径推断
            file_path = inspect.getfile(owner)
            module_name = _path_to_module(file_path)
        return f"{module_name}.{owner.__name__}"

    # 兜底：直接字符串化
    return str(owner)


def get_logger(owner: Union[Type, ModuleType, str]) -> logging.Logger:
    """获取 logger 实例。

    统一入口，内部会自动处理 ``__main__`` 情况，
    保证返回的 logger.name 足够明确（至少包含 ``fileTransfer`` 包名）。
    """
    name = _build_logger_name(owner)
    return logging.getLogger(name) 