# -*- mode: python ; coding: utf-8 -*-
"""36Ke 完整版 PyInstaller 配置（36kr + 亿欧 + Playwright）。"""

from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None

spec_dir = Path(SPECPATH)
project_root = spec_dir.parent

cpca_datas, cpca_binaries, cpca_hidden = collect_all("cpca")
pw_datas, pw_binaries, pw_hidden = collect_all("playwright")

a = Analysis(
    [str(project_root / "main.py")],
    pathex=[str(project_root)],
    binaries=cpca_binaries + pw_binaries,
    datas=cpca_datas + pw_datas,
    hiddenimports=[
        *cpca_hidden,
        *pw_hidden,
        *collect_submodules("kr36"),
        "playwright.sync_api",
        "playwright._impl",
        "playwright._impl._api_structures",
        "playwright._impl._connection",
        "playwright._impl._driver",
        "openpyxl",
        "typer",
        "typer.main",
        "click",
        "shellingham",
        "rich",
        "pandas",
        "cpca",
        "certifi",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(spec_dir / "runtime_hook_playwright.py")],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="36Ke",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="36Ke",
)
