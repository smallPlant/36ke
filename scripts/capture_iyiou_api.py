#!/usr/bin/env python3
"""使用 Playwright 抓取亿欧投资事件列表页的 XHR/Fetch 接口。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import typer

from kr36.sources.events.iyiou.capture import IyiouCaptureRunner
from kr36.sources.infra.iyiou.constants import IYIOU_INVEST_LIST_URL

app = typer.Typer(add_completion=False, help="Playwright 自动抓包亿欧 data.iyiou.com 接口")


@app.command()
def main(
    url: str = typer.Option(IYIOU_INVEST_LIST_URL, "--url", "-u", help="目标页面 URL"),
    wait: int = typer.Option(30, "--wait", "-w", min=5, help="打开页面后等待秒数（用于手动登录/翻页）"),
    headless: bool = typer.Option(False, "--headless/--no-headless", help="无头模式（有反爬，建议关闭）"),
    output: Path = typer.Option(Path("data/capture"), "--output", "-o", help="抓包结果输出目录"),
    profile: Path | None = typer.Option(
        None,
        "--profile",
        "-p",
        help="浏览器用户数据目录，可复用登录态（首次需手动登录）",
    ),
    auto_paginate: bool = typer.Option(True, "--auto-paginate/--no-auto-paginate", help="自动尝试点击下一页"),
) -> None:
    """打开目标页，监听网络响应，保存 JSON、curl 与 API 规格。"""
    typer.echo(f"目标页面: {url}")
    if profile:
        typer.echo(f"用户目录: {profile.resolve()}（复用登录态）")
    typer.echo(f"等待 {wait} 秒，请在浏览器中登录、翻页或切换筛选以触发接口…")

    runner = IyiouCaptureRunner(
        url=url,
        output_dir=output,
        headless=headless,
        profile=profile,
        wait_seconds=wait,
        auto_paginate=auto_paginate,
    )
    out_dir = runner.run()

    typer.echo("")
    typer.echo(f"完成：共捕获 {len(runner.records)} 个接口")
    typer.echo(f"摘要: {out_dir / 'summary.json'}")
    typer.echo(f"API 规格: {out_dir / 'api_spec.json'}")
    typer.echo(f"登录态: {out_dir / 'storage_state.json'}")
    if runner.records:
        typer.echo("建议优先查看 URL 含 apidata.iyiou.com/spa/invest/defaultList 的请求。")
    else:
        typer.echo("未捕获到 XHR。已写入 api_spec.json，可直接用 fetch_iyiou_invest.py 拉取首页数据。")


if __name__ == "__main__":
    app()
