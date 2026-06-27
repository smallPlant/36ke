#!/usr/bin/env python3
"""36氪融资关联公司拉取 CLI。"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from kr36.config import DEFAULT_DELAY_MAX, DEFAULT_DELAY_MIN, DEFAULT_PAGE_SIZE, Settings
from kr36.paths import default_data_dir, default_db_path
from kr36.pipeline import FinancingRelationPipeline

app = typer.Typer(help="36氪融资关联公司拉取", add_completion=False)


def _run_pipeline(
    *,
    days: Optional[int],
    pages: int,
    page_size: int,
    delay_min: float,
    delay_max: float,
    output: Path,
    db_path: Path,
    cache_ttl_days: int,
    source: str,
    push_feishu: bool,
) -> None:
    settings = Settings(
        delay_min=delay_min,
        delay_max=delay_max,
        page_size=page_size,
        output_dir=str(output),
        db_path=str(db_path),
        cache_ttl_days=cache_ttl_days,
    )
    pipeline = FinancingRelationPipeline(settings)
    rows, related_excel_path, financing_excel_path, financing_count, meta = pipeline.run(
        max_pages=pages,
        page_size=page_size,
        days=days,
        output_dir=str(output),
        push_feishu=push_feishu,
        source=source,
    )
    scope = f"最近 {days} 天" if days else f"{pages} 页"
    cache = meta["cache"]
    typer.echo(f"完成：拉取范围 {scope}，融资公司 {financing_count} 家，华南关联 {len(rows)} 条")
    typer.echo(f"缓存：命中 {cache['hits']}，过期 {cache['expired']}，新拉取 {cache['misses']}")
    typer.echo(f"数据库: {meta['db_path']}（批次 #{meta['batch_id']}）")
    typer.echo(f"融资列表: {financing_excel_path}")
    typer.echo(f"华南关联: {related_excel_path}")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    days: Optional[int] = typer.Option(None, "--days", "-d", min=1, help="仅拉取最近 N 天的融资数据（自动翻页）"),
    pages: int = typer.Option(1, "--pages", "-p", min=1, help="融资列表拉取页数（未指定 --days 时生效）"),
    page_size: int = typer.Option(DEFAULT_PAGE_SIZE, "--page-size", min=1, max=100, help="每页条数"),
    delay_min: float = typer.Option(DEFAULT_DELAY_MIN, "--delay-min", help="请求随机间隔下限（秒）"),
    delay_max: float = typer.Option(DEFAULT_DELAY_MAX, "--delay-max", help="请求随机间隔上限（秒）"),
    output: Path = typer.Option(default_data_dir(), "--output", "-o", help="Excel 输出目录"),
    db_path: Path = typer.Option(default_db_path(), "--db", help="SQLite 数据库路径"),
    cache_ttl_days: int = typer.Option(30, "--cache-ttl-days", min=1, help="公司详情缓存有效期（天）"),
    source: str = typer.Option("36kr", "--source", help="数据源：36kr / iyiou / all"),
    push_feishu: bool = typer.Option(True, "--push-feishu/--no-push-feishu", help="完成后通过 lark-cli 发送 Excel 给自己"),
) -> None:
    """执行完整流程：拉取融资公司 → 解析股东（带缓存）→ 筛选华南关联 → 导出 Excel → 飞书通知。"""
    if ctx.invoked_subcommand is not None:
        return
    _run_pipeline(
        days=days,
        pages=pages,
        page_size=page_size,
        delay_min=delay_min,
        delay_max=delay_max,
        output=output,
        db_path=db_path,
        cache_ttl_days=cache_ttl_days,
        source=source,
        push_feishu=push_feishu,
    )


@app.command("schedule")
def schedule_daily(
    days: int = typer.Option(3, "--days", "-d", min=1, help="每次拉取最近 N 天"),
    source: str = typer.Option("all", "--source", help="数据源：36kr / iyiou / all"),
    push_feishu: bool = typer.Option(True, "--push-feishu/--no-push-feishu", help="完成后推送飞书"),
    hour: int = typer.Option(9, "--hour", min=0, max=23, help="目标小时（本地时间）"),
    spread: int = typer.Option(30, "--spread", min=10, max=120, help="随机偏移范围（分钟，±spread/2）"),
    dry_run: bool = typer.Option(False, "--dry-run", help="仅显示下次执行时间"),
    output: Path = typer.Option(default_data_dir(), "--output", "-o", help="Excel 输出目录"),
    db_path: Path = typer.Option(default_db_path(), "--db", help="SQLite 数据库路径"),
    cache_ttl_days: int = typer.Option(30, "--cache-ttl-days", min=1, help="公司详情缓存有效期（天）"),
) -> None:
    """每天约在指定小时执行一次拉取（时间带随机偏移，避免固定时刻）。"""
    from kr36.scheduler import run_daily_scheduler

    def job() -> None:
        _run_pipeline(
            days=days,
            pages=1,
            page_size=DEFAULT_PAGE_SIZE,
            delay_min=DEFAULT_DELAY_MIN,
            delay_max=DEFAULT_DELAY_MAX,
            output=output,
            db_path=db_path,
            cache_ttl_days=cache_ttl_days,
            source=source,
            push_feishu=push_feishu,
        )

    run_daily_scheduler(job, hour=hour, spread_minutes=spread, dry_run=dry_run)


@app.command("setup-feishu")
def setup_feishu(
    skip_login: bool = typer.Option(False, "--skip-login", help="仅安装 lark-cli，跳过飞书授权"),
) -> None:
    """安装 lark-cli 并引导用户完成飞书授权（推送 Excel 前只需执行一次）。"""
    from kr36.feishu_setup import run_setup

    if not run_setup(skip_login=skip_login):
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
