@echo off
cd /d "%~dp0.."
if exist ".venv\Scripts\python.exe" goto dependencies
where py >nul 2>nul
if errorlevel 1 (
  python -m venv .venv
) else (
  py -3 -m venv .venv
)
if errorlevel 1 exit /b 1
:dependencies
".venv\Scripts\python.exe" -c "import pymysql,cryptography" >nul 2>nul
if not errorlevel 1 exit /b 0
".venv\Scripts\python.exe" -m pip install -r backend\requirements.txt
exit /b %errorlevel%
