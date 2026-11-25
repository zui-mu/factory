@echo off
chcp 65001 >nul
cd /d "%~dp0"
call backend\ensure-python.bat
if errorlevel 1 goto failed
if not exist "data\mysql.json" (
  ".venv\Scripts\python.exe" -X utf8 -B backend\tools\setup_mysql.py --local
  if errorlevel 1 goto failed
)
".venv\Scripts\python.exe" -X utf8 -B run.py --host 0.0.0.0 --open
if errorlevel 1 goto failed
pause
exit /b 0
:failed
echo 启动失败，请根据上方提示检查 Python、MySQL 和运行说明。
pause
exit /b 1
