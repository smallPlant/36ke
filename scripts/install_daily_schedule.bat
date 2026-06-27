@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul

cd /d "%~dp0.."
set ROOT=%CD%
set TASK_NAME=36Ke_DailySchedule

where python >nul 2>&1
if errorlevel 1 (
    echo 未找到 python，请先安装 Python 3.11+
    pause
    exit /b 1
)

for /f "delims=" %%P in ('where python') do set PYTHON=%%P

schtasks /Delete /TN "%TASK_NAME%" /F >nul 2>&1

schtasks /Create /TN "%TASK_NAME%" /SC ONLOGON /RL LIMITED /F ^
  /TR "\"%PYTHON%\" \"%ROOT%\\main.py\" schedule --source all --days 3" ^
  /RU "%USERNAME%"

if errorlevel 1 (
    echo 创建计划任务失败，请尝试以管理员身份运行
    pause
    exit /b 1
)

echo 已安装 Windows 计划任务: %TASK_NAME%
echo   登录后自动启动调度守护进程
echo   每天约 9:00 ±15 分钟执行一次（时间随机）
echo   日志: %ROOT%\data\schedule.log
echo.
echo 查看下次执行时间:
echo   cd /d %ROOT% ^& set PYTHONPATH=. ^& python main.py schedule --dry-run
echo.
echo 卸载:
echo   schtasks /Delete /TN "%TASK_NAME%" /F
pause
