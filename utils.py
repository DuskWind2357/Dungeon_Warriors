"""
Dungeon Warriors — 工具函数
资源路径解析（兼容 PyInstaller 打包和开发模式）
"""

import os
import sys


def resource_path(relative_path: str) -> str:
    """
    获取资源文件的绝对路径。
    开发模式：相对于项目根目录
    PyInstaller 打包：从临时目录获取
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包模式
        base_path = sys._MEIPASS  # type: ignore
    else:
        # 开发模式
        base_path = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_path, relative_path)
