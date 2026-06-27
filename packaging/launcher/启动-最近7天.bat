@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PLAYWRIGHT_BROWSERS_PATH=%~dp0browsers
title 36Ke - 拉取最近7天融资数据

echo 正在拉取 36氪 + 亿欧 最近 7 天融资数据，请稍候...
echo.

36Ke.exe --source all --days 7 --no-push-feishu

echo.
if exist "data" (
    echo 完成，正在打开输出目录...
    explorer "data"
) else (
    echo 运行结束。
)
pause
