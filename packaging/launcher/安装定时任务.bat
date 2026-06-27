@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PLAYWRIGHT_BROWSERS_PATH=%~dp0browsers
schtasks /Delete /TN "36Ke_DailySchedule" /F >nul 2>&1
schtasks /Create /TN "36Ke_DailySchedule" /SC ONLOGON /RL LIMITED /F ^
  /TR "\"%~dp036Ke.exe\" schedule --source all --days 3 --no-push-feishu" ^
  /RU "%USERNAME%"
if errorlevel 1 (
    echo 创建计划任务失败，请以管理员身份运行或手动双击「启动-最近3天.bat」
) else (
    echo 已安装：登录后自动在每天约 9:00 执行（时间随机）
    echo 日志: %~dp0data\schedule.log
)
pause
