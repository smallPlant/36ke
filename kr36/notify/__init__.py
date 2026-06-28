"""通知渠道（飞书）。"""

from kr36.notify.feishu import FeishuNotifier
from kr36.notify.setup import run_setup

__all__ = ["FeishuNotifier", "run_setup"]
