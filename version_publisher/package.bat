@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

rem ===============================
rem 基本配置（可按需修改）
rem ===============================
set "PROJECT_ROOT=%~dp0.."
set "ENTRY_FILE=version_publisher\version_publisher.py"
set "OUTPUT_EXE=version_publisher.exe"
set "DO_PIP_INSTALL=1"  rem 置为 0 可跳过依赖安装
set "MSVC_ARCH=x64"
set "HOST_ARCH=x64"

rem 自动检测图标（存在则使用）
set "ICON_FILE=asserts\publisher.ico"
set "ICON_OPT="
if exist "%PROJECT_ROOT%\%ICON_FILE%" (
  set "ICON_OPT=--windows-icon-from-ico=%ICON_FILE%"
)

rem Nuitka 编译参数（按需添加/删除）
set "NUITKA_OPTS=--onefile --standalone --msvc=latest --plugin-enable=pyside6 --include-qt-plugins=sensible,styles --lto=yes --remove-output"

rem ===============================
rem 帮助与清理
rem ===============================
if /I "%~1"=="/h" goto :help
if /I "%~1"=="-h" goto :help
if /I "%~1"=="help" goto :help
if /I "%~1"=="clean" goto :clean

echo [INFO] 切换到项目根目录: %PROJECT_ROOT%
pushd "%PROJECT_ROOT%" 1>nul 2>&1 || (
  echo [ERROR] 无法进入项目根目录: %PROJECT_ROOT%
  exit /b 1
)

if not exist "%ENTRY_FILE%" (
  echo [ERROR] 入口文件不存在: %ENTRY_FILE%
  popd & exit /b 1
)

rem ===============================
rem 加载 VS2022 开发者环境（优先 BuildTools，其次 Community/Professional）
rem ===============================
set "VSDEV_CMD="
if exist "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\Common7\Tools\VsDevCmd.bat" set "VSDEV_CMD=C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\Common7\Tools\VsDevCmd.bat"
if not defined VSDEV_CMD if exist "C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\Tools\VsDevCmd.bat" set "VSDEV_CMD=C:\Program Files\Microsoft Visual Studio\2022\Community\Common7\Tools\VsDevCmd.bat"
if not defined VSDEV_CMD if exist "C:\Program Files\Microsoft Visual Studio\2022\Professional\Common7\Tools\VsDevCmd.bat" set "VSDEV_CMD=C:\Program Files\Microsoft Visual Studio\2022\Professional\Common7\Tools\VsDevCmd.bat"

if not defined VSDEV_CMD (
  echo [WARN] 未找到 VsDevCmd.bat，继续尝试直接编译（可能拾取错误的 MSVC 版本）。
) else (
  echo [INFO] 加载 VS 开发者环境: "%VSDEV_CMD%" -arch=%MSVC_ARCH% -host_arch=%HOST_ARCH%
  call "%VSDEV_CMD%" -arch=%MSVC_ARCH% -host_arch=%HOST_ARCH%
  if errorlevel 1 (
    echo [WARN] VsDevCmd 返回了非零码，继续尝试但可能失败。
  )
)

goto :after_vs

:after_vs

rem 显示 cl 版本以便确认 MSVC v143 是否生效
echo [INFO] 检查 cl 编译器...
where.exe cl >nul 2>nul
if errorlevel 1 (
  echo [WARN] 未找到 cl，可继续尝试但可能失败。
) else (
  for /f "tokens=*" %%i in ('where.exe cl') do echo [INFO] cl 路径: %%i
  rem 检测编译器版本输出是否包含 19.42+（v143+）
  cl 2>&1 | findstr /r /c:"19\.4[2-9]" >nul
  if errorlevel 1 (
    echo [WARN] 未检测到 19.4x 版本，可能仍为旧版 MSVC。
  ) else (
    echo [INFO] 检测到 MSVC 19.4x（v143+）
  )
)

rem ===============================
rem 可选：安装/更新依赖
rem ===============================
if "%DO_PIP_INSTALL%"=="1" (
  echo [INFO] 安装/更新打包依赖（可通过 DO_PIP_INSTALL=0 跳过）
  echo [INFO] 升级打包工具...
  python -m pip install -U pip setuptools wheel
  echo [INFO] 安装运行依赖...
  python -m pip install -U nuitka PySide6 python-dotenv ordered-set zstandard
)

rem ===============================
rem 执行 Nuitka 打包
rem ===============================
echo [INFO] 开始打包: %ENTRY_FILE%
echo [INFO] Nuitka 选项: %NUITKA_OPTS% %ICON_OPT%

python -m nuitka %NUITKA_OPTS% %ICON_OPT% "%ENTRY_FILE%"
set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
  echo [ERROR] 打包失败，错误码 %ERR%
  popd & exit /b %ERR%
)

if exist "%PROJECT_ROOT%\%OUTPUT_EXE%" (
  for %%F in ("%PROJECT_ROOT%\%OUTPUT_EXE%") do (
    set "SIZE=%%~zF"
  )
  echo [SUCCESS] 生成成功: %PROJECT_ROOT%\%OUTPUT_EXE% （大小: !SIZE! 字节）
) else (
  echo [WARN] 未在预期位置找到输出 EXE: %PROJECT_ROOT%\%OUTPUT_EXE%
)

popd >nul 2>&1
echo.
echo [INFO] 完成。按任意键退出...
pause >nul
exit /b 0

:clean
echo [INFO] 清理 Nuitka 构建产物...
pushd "%PROJECT_ROOT%" 1>nul 2>&1 || exit /b 1
if exist version_publisher.build (
  rmdir /s /q version_publisher.build
  echo   - 删除 version_publisher.build
)
if exist version_publisher.dist (
  rmdir /s /q version_publisher.dist
  echo   - 删除 version_publisher.dist
)
if exist version_publisher.onefile-build (
  rmdir /s /q version_publisher.onefile-build
  echo   - 删除 version_publisher.onefile-build
)
if exist "%OUTPUT_EXE%" (
  del /q "%OUTPUT_EXE%"
  echo   - 删除 %OUTPUT_EXE%
)
popd >nul 2>&1
exit /b 0

:help
echo 用法:
echo   package.bat              ^> 在 VS2022 环境下使用 Nuitka 打包 EXE
echo   package.bat clean        ^> 清理上次构建产物
echo   package.bat -h ^| /h ^| help ^> 显示帮助
echo.
echo 说明:
echo  1. 自动检测 VS2022 開發者環境並調用 VsDevCmd，確保 MSVC v143。
echo  2. 默認會安裝/更新依賴，可將 DO_PIP_INSTALL 置為 0 跳過。
echo  3. 自動檢測圖標文件 resource\logo\logo.ico 並用作 EXE 圖標（若存在）。
exit /b 0


