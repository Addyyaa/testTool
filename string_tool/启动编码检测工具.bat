@echo off
chcp 65001 >nul
title 编码格式检测工具
cd /d "%~dp0"
python start_encoding_detector.py
pause 