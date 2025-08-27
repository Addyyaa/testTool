@echo off
<<<<<<< HEAD
chcp 65001 >nul
echo 开始打包固件发布工具...

python -m nuitka version_publisher.py ^
    --onefile ^
    --standalone ^
    --msvc=latest ^
    --lto=yes ^
    --remove-output ^
    --enable-plugin=upx ^
    --include-package-data=asserts ^
    --windows-icon-from-ico=asserts/publisher.ico ^
    --enable-plugin=pyside6

if %errorlevel% equ 0 (
    echo 打包完成！
    echo 可执行文件位置: version_publisher.exe
) else (
    echo 打包失败，错误代码: %errorlevel%
)

pause
