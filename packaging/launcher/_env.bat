@echo off
cd /d "%~dp0"
set PLAYWRIGHT_BROWSERS_PATH=%~dp0browsers
set KR36_PUSH_FEISHU=true
if exist "%~dp0tools\node" set "PATH=%~dp0tools\node;%PATH%"
if exist "%~dp0tools\lark-cli\lark-cli.exe" set "LARK_CLI_BIN=%~dp0tools\lark-cli\lark-cli.exe"
if exist "%~dp0tools\npm\lark-cli.cmd" set "LARK_CLI_BIN=%~dp0tools\npm\lark-cli.cmd"
