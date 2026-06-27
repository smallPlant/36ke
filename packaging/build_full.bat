@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul

cd /d "%~dp0.."
set ROOT=%CD%
set VENV=%ROOT%\.venv-build
set DIST=%ROOT%\dist\36Ke
set BROWSERS_SRC=%LOCALAPPDATA%\ms-playwright

echo ========================================
echo   36Ke 完整版打包（内置 Chromium）
echo   需在 Windows 上运行
echo ========================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 python，请先安装 Python 3.11+
    pause
    exit /b 1
)

if not exist "%VENV%\Scripts\activate.bat" (
    echo [1/6] 创建构建虚拟环境...
    python -m venv "%VENV%"
)

call "%VENV%\Scripts\activate.bat"

echo [2/6] 安装依赖...
python -m pip install -U pip
pip install -r requirements.txt -r packaging/requirements-build.txt

echo [3/6] 下载 Chromium（Playwright）...
playwright install chromium
if errorlevel 1 (
    echo [错误] playwright install chromium 失败
    pause
    exit /b 1
)

echo [4/6] PyInstaller 打包...
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

echo [5/6] 复制内置 Chromium 与启动脚本...
if not exist "%DIST%\browsers" mkdir "%DIST%\browsers"

set COPIED=0
for /d %%D in ("%BROWSERS_SRC%\chromium*") do (
    echo   复制 %%~nxD ...
    xcopy /E /I /Y /Q "%%D" "%DIST%\browsers\%%~nxD\" >nul
    set COPIED=1
)

if "!COPIED!"=="0" (
    echo [错误] 未找到 Chromium，请先确认 playwright install chromium 成功
    echo 路径: %BROWSERS_SRC%
    pause
    exit /b 1
)

copy /Y packaging\launcher\*.bat "%DIST%\" >nul
copy /Y packaging\launcher\*.txt "%DIST%\" >nul

echo [6/6] 压缩发布包...
powershell -NoProfile -Command "Compress-Archive -Path '%DIST%' -DestinationPath '%ROOT%\dist\36Ke-完整版-win64.zip' -Force"

echo.
echo ========================================
echo   打包完成
echo   目录: %DIST%
echo   压缩包: %ROOT%\dist\36Ke-完整版-win64.zip
echo   分发给用户: 解压后双击「启动-最近3天.bat」
echo   用户电脑无需安装 Python
echo ========================================
pause
