"""PyInstaller 运行时：打包版使用内置 Chromium。"""
import os
import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    browsers = Path(sys.executable).resolve().parent / "browsers"
    if browsers.is_dir():
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(browsers)
