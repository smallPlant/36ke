from __future__ import annotations

import shutil
import subprocess
import sys

LARK_CLI_PACKAGE = "@larksuite/cli"
NODEJS_URL = "https://nodejs.org/"


def lark_cli_path() -> str | None:
    return shutil.which("lark-cli")


def npm_path() -> str | None:
    return shutil.which("npm")


def install_lark_cli() -> bool:
    path = lark_cli_path()
    if path:
        print(f"✓ lark-cli 已安装: {path}")
        return True

    npm = npm_path()
    if not npm:
        print("未检测到 npm（Node.js 未安装或未加入 PATH）。")
        print(f"请先安装 Node.js LTS: {NODEJS_URL}")
        print("安装完成后重新运行: python main.py setup-feishu")
        return False

    print(f"正在通过 npm 安装 {LARK_CLI_PACKAGE} ...")
    result = subprocess.run(
        [npm, "install", "-g", LARK_CLI_PACKAGE],
        check=False,
    )
    if result.returncode != 0:
        print("lark-cli 安装失败。可尝试手动执行:")
        print(f"  npm install -g {LARK_CLI_PACKAGE}")
        return False

    path = lark_cli_path()
    if not path:
        print("安装完成但未在 PATH 中找到 lark-cli，请重启终端后重试。")
        return False

    print(f"✓ lark-cli 安装成功: {path}")
    return True


def auth_login() -> bool:
    cli = lark_cli_path()
    if not cli:
        print("未找到 lark-cli，请先完成安装。")
        return False

    print("即将打开浏览器，请使用飞书账号完成授权（仅需一次）...")
    result = subprocess.run([cli, "auth", "login"], check=False)
    if result.returncode != 0:
        print("飞书授权未完成。可稍后手动执行: lark-cli auth login")
        return False

    print("✓ 飞书授权完成，之后运行 main.py 即可自动推送 Excel。")
    return True


def run_setup(*, skip_login: bool = False) -> bool:
    if not install_lark_cli():
        return False
    if skip_login:
        print("已跳过授权。需要推送时请执行: lark-cli auth login")
        return True
    return auth_login()


def main(argv: list[str] | None = None) -> int:
    skip_login = "--skip-login" in (argv or sys.argv[1:])
    return 0 if run_setup(skip_login=skip_login) else 1
