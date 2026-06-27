from __future__ import annotations

import random
import sys
import time
from collections.abc import Callable
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from kr36.paths import default_data_dir

DEFAULT_SCHEDULE_HOUR = 9
DEFAULT_SCHEDULE_SPREAD_MINUTES = 30
DEFAULT_SCHEDULE_LOG = default_data_dir() / "schedule.log"


def local_tz() -> timezone:
    return datetime.now().astimezone().tzinfo or timezone.utc


def daily_run_time(
    for_date: date,
    *,
    hour: int = DEFAULT_SCHEDULE_HOUR,
    spread_minutes: int = DEFAULT_SCHEDULE_SPREAD_MINUTES,
    tz: timezone | None = None,
) -> datetime:
    """某天的大约执行时刻：hour 点 ± spread/2，同一天结果固定（按日期种子）。"""
    tz = tz or local_tz()
    half = max(spread_minutes // 2, 1)
    rng = random.Random(for_date.isoformat())
    offset = rng.randint(-half, half)
    base = datetime(for_date.year, for_date.month, for_date.day, hour, 0, tzinfo=tz)
    return base + timedelta(minutes=offset)


def next_scheduled_run(
    now: datetime | None = None,
    *,
    hour: int = DEFAULT_SCHEDULE_HOUR,
    spread_minutes: int = DEFAULT_SCHEDULE_SPREAD_MINUTES,
) -> datetime:
    """返回下一次计划执行时间（本地时区）。"""
    now = now or datetime.now().astimezone()
    tz = now.tzinfo or local_tz()
    today = now.date()
    candidate = daily_run_time(today, hour=hour, spread_minutes=spread_minutes, tz=tz)
    if candidate > now:
        return candidate
    return daily_run_time(
        today + timedelta(days=1),
        hour=hour,
        spread_minutes=spread_minutes,
        tz=tz,
    )


def _append_log(log_path: Path, message: str) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(f"[{stamp}] {message}\n")


def sleep_until(target: datetime) -> None:
    while True:
        now = datetime.now().astimezone()
        seconds = (target - now).total_seconds()
        if seconds <= 0:
            return
        time.sleep(min(seconds, 3600))


def run_daily_scheduler(
    job: Callable[[], None],
    *,
    hour: int = DEFAULT_SCHEDULE_HOUR,
    spread_minutes: int = DEFAULT_SCHEDULE_SPREAD_MINUTES,
    log_path: Path = DEFAULT_SCHEDULE_LOG,
    dry_run: bool = False,
) -> None:
    """循环调度：每天在 hour 点附近随机执行一次 job。"""
    if dry_run:
        nxt = next_scheduled_run(hour=hour, spread_minutes=spread_minutes)
        print(f"下次计划执行: {nxt.strftime('%Y-%m-%d %H:%M:%S %Z')}（约 {hour}:00 ±{spread_minutes // 2} 分钟）")
        return

    _append_log(log_path, f"定时任务已启动（目标 {hour}:00 ±{spread_minutes // 2} 分钟）")
    print(f"定时任务已启动，日志: {log_path}")

    while True:
        target = next_scheduled_run(hour=hour, spread_minutes=spread_minutes)
        msg = f"下次执行: {target.strftime('%Y-%m-%d %H:%M:%S %Z')}"
        _append_log(log_path, msg)
        print(msg)
        sleep_until(target)

        _append_log(log_path, "开始执行拉取任务")
        print("开始执行拉取任务…")
        try:
            job()
            _append_log(log_path, "拉取任务完成")
            print("拉取任务完成")
        except Exception as exc:
            _append_log(log_path, f"拉取任务失败: {exc}")
            print(f"拉取任务失败: {exc}", file=sys.stderr)
