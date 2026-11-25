@echo off
chcp 65001 >nul
if not exist "%~dp0Build\Windows\质因云联仿真工厂.exe" (
    echo 请先用 Unity 菜单“质因云联 / 导出 Windows 程序”生成程序。
    pause
    exit /b 1
)
start "" "%~dp0Build\Windows\质因云联仿真工厂.exe"
