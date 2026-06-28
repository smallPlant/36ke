#!/usr/bin/env python3
"""拉取亿欧投资事件列表并导出 Excel。"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import typer

from kr36.sources.infra.iyiou.browser import IyiouBrowser
from kr36.sources.events.iyiou.client import IyiouInvestClient
from kr36.sources.events.iyiou.export import save_invest_excel

app = typer.Typer(add_completion=False, help="亿欧投资事件拉取")


@app.command()
def main(
    pages: int = typer.Option(1, "--pages", "-p", min=1, help="拉取页数（登录后可翻页）"),
    page_size: int = typer.Option(20, "--page-size", min=1, max=100, help="每页条数"),
    output: Path = typer.Option(Path("data"), "--output", "-o", help="Excel 输出目录"),
    profile: Path | None = typer.Option(
        None,
        "--profile",
        help="浏览器用户目录；登录后可保存 Cookie 并支持翻页",
    ),
    headless: bool = typer.Option(True, "--headless/--no-headless", help="无头模式"),
) -> None:
    """通过 Playwright 访问亿欧并拉取投资事件，导出 Excel。"""
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    excel_path = output / f"亿欧投资事件_{stamp}.xlsx"

    with IyiouBrowser(headless=headless, profile=profile) as browser:
        client = IyiouInvestClient(browser)
        client.warmup()
        rows, total = client.fetch_pages(max_pages=pages, page_size=page_size)
        if not rows:
            rows, total = client.fetch_initial_state()

    save_invest_excel(rows, excel_path)
    typer.echo(f"完成：共 {len(rows)} 条（总计 {total} 条）")
    typer.echo(f"Excel: {excel_path}")
    if pages > 1 and len(rows) <= page_size:
        typer.echo("提示：未登录时 API 可能只返回首页数据，请使用 --profile 登录后再拉取多页。")


if __name__ == "__main__":
    app()
