@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
call "%~dp0_env.bat"
title 36Ke - 配置环境

echo.
echo ========================================
echo   环境配置（飞书）
echo ========================================
echo.
echo 飞书 CLI（安装 + 应用初始化 + 浏览器授权）
echo 企查查将在拉取时自动检测 Cookie，失效时弹出浏览器扫码登录
echo.

36Ke.exe setup-feishu
if errorlevel 1 (
    echo [错误] 飞书配置未完成。
    pause
    exit /b 1
)

echo.
echo [OK] 环境配置完成，可运行「立即执行.bat」或「每日定时任务.bat」
pause
