@echo off
chcp 65001 > nul
title 字体服务器启动程序

echo ============================================================
echo                     字体服务器启动程序
echo ============================================================
echo.

echo 正在启动字体服务器...
echo.

REM 检查Python是否安装
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未找到Python，请先安装Python 3.7或更高版本
    pause
    exit /b 1
)

REM 运行启动脚本
python start_font_server.py

echo.
echo 字体服务器已停止
pause 