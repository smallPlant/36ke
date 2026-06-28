"""飞书推送依赖安装：便携 Node.js + lark-cli 并引导 config init / OAuth 授权。"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from urllib.request import urlopen

from kr36.core.paths import (
    app_dir,
    bundled_lark_cli,
    bundled_node_dir,
    bundled_node_exe,
    bundled_npm_cmd,
    bundled_npm_prefix,
    tools_dir,
)

LARK_CLI_PACKAGE = "@larksuite/cli"
NODEJS_URL = "https://nodejs.org/"
NODE_VERSION = "20.18.1"
NODE_DIST_URL = (
    f"https://nodejs.org/dist/v{NODE_VERSION}/node-v{NODE_VERSION}-win-x64.zip"
)


def lark_cli_path() -> str | None:
    """查找 lark-cli 可执行文件路径。"""
    bundled = bundled_lark_cli()
    if bundled:
        return str(bundled)
    return shutil.which("lark-cli")


def npm_path() -> str | None:
    """查找 npm 可执行文件路径。"""
    bundled = bundled_npm_cmd()
    if bundled:
        return str(bundled)
    return shutil.which("npm")


def _run(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    capture: bool = False,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        check=False,
        capture_output=capture,
        text=capture,
    )


def is_lark_configured(cli: str) -> bool:
    """检查 lark-cli 是否已完成 config init（app-id / secret）。"""
    result = _run([cli, "config", "show"], capture=True)
    return result.returncode == 0


def init_lark_config(cli: str) -> bool:
    """首次使用：创建飞书应用并完成 config 初始化（阻塞至用户在浏览器完成）。"""
    print("首次使用需初始化飞书应用（lark-cli config init --new）")
    print("即将输出验证链接，请在浏览器中完成应用创建，完成后回到本窗口...")
    result = _run([cli, "config", "init", "--new", "--lang", "zh_cn"])
    if result.returncode != 0:
        print("飞书应用初始化失败。可手动执行:")
        print("  lark-cli config init --new")
        return False
    print("[OK] 飞书应用配置已初始化")
    return True


def install_portable_node() -> bool:
    """Windows 打包版：下载便携 Node.js 到 tools/node（已存在则跳过）。"""
    if bundled_node_exe():
        print(f"[OK] 便携 Node.js 已就绪: {bundled_node_exe()}")
        return True

    if sys.platform != "win32":
        print("非 Windows 环境，请手动安装 Node.js LTS。")
        print(f"下载: {NODEJS_URL}")
        return False

    tools_dir().mkdir(parents=True, exist_ok=True)
    zip_path = tools_dir() / f"node-v{NODE_VERSION}-win-x64.zip"
    extract_root = tools_dir() / "_node_extract"

    print(f"正在下载 Node.js v{NODE_VERSION}（约 30MB）...")
    try:
        with urlopen(NODE_DIST_URL, timeout=120) as response:
            zip_path.write_bytes(response.read())
    except OSError as exc:
        print(f"下载 Node.js 失败: {exc}")
        print(f"请手动安装 Node.js LTS: {NODEJS_URL}")
        return False

    try:
        if extract_root.is_dir():
            shutil.rmtree(extract_root)
        extract_root.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(extract_root)
        src = extract_root / f"node-v{NODE_VERSION}-win-x64"
        if not src.is_dir():
            print("Node.js 解压结构异常，请手动安装 Node.js。")
            return False
        dest = bundled_node_dir()
        if dest.is_dir():
            shutil.rmtree(dest)
        shutil.move(str(src), str(dest))
    finally:
        zip_path.unlink(missing_ok=True)
        if extract_root.is_dir():
            shutil.rmtree(extract_root, ignore_errors=True)

    if not bundled_node_exe():
        print("便携 Node.js 安装失败。")
        return False

    print(f"[OK] 便携 Node.js 安装成功: {bundled_node_exe()}")
    return True


def install_lark_cli() -> bool:
    """通过 npm 安装 lark-cli 到 tools/npm，已安装则直接返回成功。"""
    path = lark_cli_path()
    if path:
        print(f"[OK] lark-cli 已安装: {path}")
        return True

    npm = npm_path()
    if not npm:
        if getattr(sys, "frozen", False) or app_dir().name == "36Ke":
            if not install_portable_node():
                return False
            npm = npm_path()
        if not npm:
            print("未检测到 npm（Node.js 未安装或未加入 PATH）。")
            print(f"请先安装 Node.js LTS: {NODEJS_URL}")
            print("安装完成后重新运行: python main.py setup-feishu")
            return False

    prefix = bundled_npm_prefix()
    prefix.mkdir(parents=True, exist_ok=True)

    print(f"正在通过 npm 安装 {LARK_CLI_PACKAGE} 到 {prefix} ...")
    env = os.environ.copy()
    node_dir = bundled_node_dir()
    if node_dir.is_dir():
        env["PATH"] = str(node_dir) + os.pathsep + env.get("PATH", "")
    result = subprocess.run(
        [npm, "install", "-g", LARK_CLI_PACKAGE, "--prefix", str(prefix)],
        check=False,
        env=env,
    )
    if result.returncode != 0:
        print("lark-cli 安装失败。可尝试手动执行:")
        print(f"  npm install -g {LARK_CLI_PACKAGE} --prefix {prefix}")
        return False

    path = lark_cli_path()
    if not path:
        print("安装完成但未找到 lark-cli，请重启终端后重试。")
        return False

    print(f"[OK] lark-cli 安装成功: {path}")
    return True


def auth_login() -> bool:
    """config init（如需）+ 浏览器 OAuth 授权。"""
    cli = lark_cli_path()
    if not cli:
        print("未找到 lark-cli，请先完成安装。")
        return False

    if not is_lark_configured(cli):
        if not init_lark_config(cli):
            return False

    print("即将打开浏览器，请使用飞书账号完成授权（仅需一次）...")
    result = _run([cli, "auth", "login"])
    if result.returncode != 0:
        print("飞书授权未完成。可稍后手动执行:")
        print("  lark-cli config init --new")
        print("  lark-cli auth login")
        return False

    print("[OK] 飞书授权完成，之后运行即可自动推送 Excel。")
    return True


def run_setup(*, skip_login: bool = False) -> bool:
    """安装 lark-cli 并可选执行飞书 config + 授权。"""
    if not install_lark_cli():
        return False
    if skip_login:
        print("已跳过授权。需要推送时请执行: python main.py setup-feishu")
        return True
    return auth_login()


def main(argv: list[str] | None = None) -> int:
    """CLI 入口：安装 lark-cli 并授权。"""
    skip_login = "--skip-login" in (argv or sys.argv[1:])
    return 0 if run_setup(skip_login=skip_login) else 1
