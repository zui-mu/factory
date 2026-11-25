@echo off
chcp 65001 >nul
cd /d "%~dp0"
call backend\ensure-python.bat
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -X utf8 -B backend\tools\setup_mysql.py --local %*
if errorlevel 1 goto failed
pause
exit /b 0
:failed
echo 配置失败，请根据上方提示检查 MySQL 安装位置。
pause
exit /b 1
