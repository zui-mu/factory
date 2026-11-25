@echo off
chcp 65001 >nul
cd /d "%~dp0.."
call backend\ensure-python.bat
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -X utf8 -B -c "from backend.local_mysql import ensure_local_server; from backend.mysql_store import settings; ensure_local_server(settings())"
if errorlevel 1 goto failed
if not defined ZY_MYSQL_TEST_CONFIG if exist "data\mysql-local\admin.json" set "ZY_MYSQL_TEST_CONFIG=%cd%\data\mysql-local\admin.json"
if not defined ZY_MYSQL_TEST_CONFIG (
  echo 请设置 ZY_MYSQL_TEST_CONFIG，指向可创建测试库的 MySQL 连接 JSON 文件。
  goto failed
)
".venv\Scripts\python.exe" -X utf8 -B -m unittest discover -s backend/tests -v
if errorlevel 1 goto failed
pause
exit /b 0
:failed
pause
exit /b 1
