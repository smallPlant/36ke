@echo off
chcp 65001 >nul
cd /d "%~dp0.."
echo === 36Ke 飞书 CLI 安装 ===
python main.py setup-feishu
if errorlevel 1 pause
exit /b %errorlevel%
