@echo off
call "%~dp0_env.bat"
"%~dp036Ke.exe" schedule --source all --days 3 --push-feishu
