@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul

cd /d "%~dp0.."
set ROOT=%CD%
set VENV=%ROOT%\.venv-build
set DIST=%ROOT%\dist\36Ke
set BROWSERS_SRC=%LOCALAPPDATA%\ms-playwright
set ZIP=%ROOT%\dist\36Ke-全功能版-win64.zip

echo ========================================
echo   36Ke 全功能版打包
echo   全数据源 + 飞书推送 + 定时任务
echo   需在 Windows 上运行
echo ========================================
echo.

where py >nul 2>&1
if not errorlevel 1 (
    set PYTHON=py -3.11
) else (
    set PYTHON=python
)

%PYTHON% --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python 3.11+，请先安装
    pause
    exit /b 1
)

if not exist "%VENV%\Scripts\activate.bat" (
    echo [1/7] 创建构建虚拟环境...
    %PYTHON% -m venv "%VENV%"
)

call "%VENV%\Scripts\activate.bat"

echo [2/7] 安装依赖...
python -m pip install -U pip
pip install -r requirements.txt -r packaging/requirements-build.txt

echo [3/7] 下载 Chromium（Playwright）...
playwright install chromium
if errorlevel 1 (
    echo [错误] playwright install chromium 失败
    pause
    exit /b 1
)

echo [4/7] PyInstaller 打包...
pyinstaller packaging\36ke-full.spec --noconfirm --distpath dist --workpath build
if errorlevel 1 (
    echo [错误] PyInstaller 打包失败
    pause
    exit /b 1
)

if not exist "%DIST%" (
    echo [错误] 未找到输出目录 %DIST%
    pause
    exit /b 1
)

echo [5/7] 复制内置 Chromium...
if not exist "%DIST%\browsers" mkdir "%DIST%\browsers"

set COPIED=0
for /d %%D in ("%BROWSERS_SRC%\chromium*") do (
    echo   复制 %%~nxD ...
    xcopy /E /I /Y /Q "%%D" "%DIST%\browsers\%%~nxD\" >nul
    set COPIED=1
)

if "!COPIED!"=="0" (
    for /d %%D in ("%PLAYWRIGHT_BROWSERS_PATH%\chromium*") do (
        echo   复制 %%~nxD ...
        xcopy /E /I /Y /Q "%%D" "%DIST%\browsers\%%~nxD\" >nul
        set COPIED=1
    )
)

if "!COPIED!"=="0" (
    echo [错误] 未找到 Chromium，请先确认 playwright install chromium 成功
    pause
    exit /b 1
)

echo [6/7] 打包 Node.js + lark-cli 与启动脚本...
powershell -NoProfile -ExecutionPolicy Bypass -File packaging\bundle_tools.ps1
if errorlevel 1 (
    echo [错误] tools 打包失败
    pause
    exit /b 1
)

copy /Y packaging\launcher\*.bat "%DIST%\" >nul
copy /Y packaging\launcher\*.txt "%DIST%\" >nul

echo [7/7] 压缩发布包...
powershell -NoProfile -Command "Compress-Archive -Path '%DIST%' -DestinationPath '%ZIP%' -Force"

echo.
echo ========================================
echo   打包完成
echo   目录: %DIST%
echo   压缩包: %ZIP%
echo   用户: 解压后「配置环境.bat」→「立即执行.bat」
echo ========================================
pause
