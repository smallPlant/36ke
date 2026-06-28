@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
call "%~dp0_env.bat"
title 36Ke - 立即执行

echo.
echo ========================================
echo   36Ke 立即执行
echo ========================================
echo 数据源: 36氪 + 企查查 + 亿欧
echo 范围:   最近 3 天
echo 推送:   飞书
echo 首次使用请先运行「配置环境.bat」
echo.
echo 正在拉取，预计 3~10 分钟，请勿关闭本窗口...
echo ========================================
echo.

call 36Ke.exe --source all --days 3 --push-feishu
set EXIT_CODE=%ERRORLEVEL%

echo.
echo ========================================
if %EXIT_CODE% equ 0 (
    echo [完成] 拉取流程已结束
) else (
    echo [异常] 程序退出码: %EXIT_CODE% ^(详见上方日志^)
)
echo ========================================
echo.

if exist "data" (
    echo 输出目录: %~dp0data
    explorer "data"
)

echo 上方为完整运行日志，请查阅后再关闭。
echo 按任意键关闭本窗口...
pause >nul
exit /b %EXIT_CODE%
