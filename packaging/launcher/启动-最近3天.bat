@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PLAYWRIGHT_BROWSERS_PATH=%~dp0browsers
title 36Ke - 拉取最近3天融资数据

echo 正在拉取 36氪+企查查最近3天 + 亿欧首页，请稍候...
echo.

36Ke.exe --no-push-feishu

echo.
if exist "data" (
    echo 完成，正在打开输出目录...
    explorer "data"
) else (
    echo 运行结束。
)
pause
