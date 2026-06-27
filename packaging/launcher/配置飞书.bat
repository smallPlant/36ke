@echo off
chcp 65001 >nul
cd /d "%~dp0"
title 36Ke - 飞书推送配置

echo 配置飞书推送（需先安装 Node.js）
echo.
36Ke.exe setup-feishu
pause
