"""
Dungeon Warriors — 调试日志
在 windowed 模式下将 stderr/stdout 重定向到文件
"""

import sys
import os
import datetime


def setup_debug_log():
    """将 stdout/stderr 重定向到日志文件"""
    log_dir = os.path.dirname(os.path.abspath(__file__))
    if getattr(sys, 'frozen', False):
        log_dir = os.path.dirname(sys.executable)

    log_path = os.path.join(log_dir, "debug.log")

    try:
        log_file = open(log_path, "w", encoding="utf-8", buffering=1)
        sys.stdout = log_file
        sys.stderr = log_file
        print(f"[{datetime.datetime.now()}] Debug log started")
        print(f"[DEBUG] sys.frozen = {getattr(sys, 'frozen', False)}")
        print(f"[DEBUG] log dir = {log_dir}")
        return True
    except Exception as e:
        print(f"Failed to setup debug log: {e}")
        return False
