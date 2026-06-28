@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
call "%~dp0_env.bat"
title 36Ke - 每日定时任务

echo.
echo 安装计划任务: 登录后每天约 9:00 自动拉取（全源 + 飞书推送）
echo 首次使用请先运行「配置环境.bat」
echo 日志: %~dp0data\schedule.log
echo.

schtasks /Delete /TN "36Ke_DailySchedule" /F >nul 2>&1
schtasks /Create /TN "36Ke_DailySchedule" /SC ONLOGON /RL LIMITED /F ^
  /TR "\"%~dp0_schedule-runner.bat\"" ^
  /RU "%USERNAME%"

if errorlevel 1 (
    echo [错误] 创建失败，请右键「以管理员身份运行」。
    pause
    exit /b 1
)

echo [OK] 已安装「36Ke_DailySchedule」
echo 卸载: schtasks /Delete /TN "36Ke_DailySchedule" /F
pause
