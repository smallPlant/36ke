@echo off
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
cd /d "%ROOT%" 2>nul
set "PLAYWRIGHT_BROWSERS_PATH=%ROOT%\browsers"
set "KR36_PUSH_FEISHU=true"
if exist "%ROOT%\tools\node\node.exe" set "PATH=%ROOT%\tools\node;%PATH%"
if exist "%ROOT%\tools\lark-cli\lark-cli.exe" set "LARK_CLI_BIN=%ROOT%\tools\lark-cli\lark-cli.exe"
if exist "%ROOT%\tools\npm\lark-cli.cmd" set "LARK_CLI_BIN=%ROOT%\tools\npm\lark-cli.cmd"
