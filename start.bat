@echo off
setlocal
chcp 65001 >nul
title 全景可视化数字工厂 - 统一启动
cd /d "%~dp0"
call backend\ensure-python.bat
if errorlevel 1 goto failed
if not exist "data\mysql.json" (
  ".venv\Scripts\python.exe" -X utf8 -B backend\tools\setup_mysql.py --local
  if errorlevel 1 goto failed
)
echo 正在启动网页服务、浏览器客户端和 Unity WebGL…
".venv\Scripts\python.exe" -X utf8 -B run.py --open --workshop
if errorlevel 1 goto failed
pause
exit /b 0
:failed
echo 启动失败，请根据上方提示检查 Python、MySQL 和运行说明。
pause
exit /b 1
