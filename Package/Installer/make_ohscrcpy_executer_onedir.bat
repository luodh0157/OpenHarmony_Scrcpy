REM Copyright (c) 2026 luodh0157.
REM Licensed under the Apache License, Version 2.0 (the "License");
REM you may not use this file except in compliance with the License.
REM You may obtain a copy of the License at
REM
REM     http://www.apache.org/licenses/LICENSE-2.0
REM
REM Unless required by applicable law or agreed to in writing, software
REM distributed under the License is distributed on an "AS IS" BASIS,
REM WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
REM See the License for the specific language governing permissions and
REM limitations under the License.

REM ================================================================================
REM                OpenHarmony OHScrcpy 自动化构建脚本（Windows平台）
REM ================================================================================
REM
REM 使用前准备：
REM   1. 将以下文件和目录拷贝到当前目录（Package/Installer）：
REM      - Client\ohscrcpy_client.py → 重命名为 main.py（或保持原名）
REM      - Server\bin\rk3568\ohscrcpy_server
REM      - Server\ohscrcpy_server.cfg
REM      - Server\bin\harmonyos\ohscrcpy_server → 拷贝到 HUAWEI\ 子目录下
REM      - Client\hdc\ 目录 → 拷贝整个目录
REM      - scripts\ 目录 → 拷贝整个目录（包含日志管理脚本）
REM   2. 确保已安装 Python 3.7+ 和 pip
REM   3. 运行此脚本：make_ohscrcpy_executer_onedir.bat
REM
REM 日志管理脚本包括：
REM   - fetch_fetch_and_delete_server_logs.bat - 拉取服务端日志脚本
REM   - delete_fetch_and_delete_server_logs.bat - 删除服务端日志脚本
REM   - fetch_and_delete_server_logs.bat - 二合一日志管理脚本
REM
REM ================================================================================

::@cls
@setlocal enabledelayedexpansion
@chcp 936 >nul
@echo off

title OpenHarmony OHScrcpy 打包构建脚本
color 0a
echo ===========================================================
echo      OpenHarmony OHScrcpy 自动化构建脚本（Windows平台）    
echo ===========================================================

set VERSION=v2.1.0

::PROCESSOR_ARCHITEW6432（仅在 64 位系统的 32 位进程中存在）
if defined PROCESSOR_ARCHITEW6432 (
    set "ARCH=AMD64"
) else (
    set "ARCH=%PROCESSOR_ARCHITECTURE%"
)

if /i "%ARCH%"=="AMD64" (
    echo 这是64位 x86系统（x64）
    set "ARCH=x64"
) else if /i "%ARCH%"=="x86" (
    echo 这是32位 x86系统（x86）
    set "ARCH=x86"
) else if /i "%ARCH%"=="IA64" (
    echo 这是Intel Itanium 64位系统（i64）
    set "ARCH=i64"
) else if /i "%ARCH%"=="ARM64" (
    echo 这是64位 ARM系统（arm64）
    set "ARCH=arm64"
) else if /i "%ARCH%"=="ARM" (
    echo 这是32位 ARM系统（arm）
    set "ARCH=arm"
) else (
    echo 未知架构：%ARCH%
)
echo [信息] 检测到操作系统: Windows, 架构：%ARCH%

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo -----------------------------------------
    echo [错误] 未找到Python，请先安装Python 3.7+
    echo -----------------------------------------
    ping 127.0.0.1 -n 6 >nul
    exit /b 1
)

where pyinstaller >nul 2>nul
if %errorlevel% neq 0 (
    echo [警告] PyInstaller未安装，正在安装...
    pip install pyinstaller
    if %errorlevel% neq 0 (
        echo ---------------------------
        echo [错误] PyInstaller安装失败
        echo ---------------------------
        ping 127.0.0.1 -n 6 >nul
        exit /b 1
    )
    echo [成功] PyInstaller安装完成
)

echo [信息] 清理历史构建文件...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist __pycache__ rmdir /s /q __pycache__
echo [完成] 清理完成

echo [信息] 检查必要文件...
if not exist main.py (
    echo ---------------------------------------------------
    echo [错误] 未找到 main.py，请确保该文件存在
    echo ---------------------------------------------------
    ping 127.0.0.1 -n 6 >nul
    exit /b 1
)

if not exist core (
    echo ---------------------------------------------------
    echo [错误] 未找到模块目录 core
    echo ---------------------------------------------------
    ping 127.0.0.1 -n 6 >nul
    exit /b 1
)

if not exist video (
    echo ---------------------------------------------------
    echo [错误] 未找到模块目录 video
    echo ---------------------------------------------------
    ping 127.0.0.1 -n 6 >nul
    exit /b 1
)

if not exist gui (
    echo ---------------------------------------------------
    echo [错误] 未找到模块目录 gui
    echo ---------------------------------------------------
    ping 127.0.0.1 -n 6 >nul
    exit /b 1
)

if not exist utils (
    echo ---------------------------------------------------
    echo [错误] 未找到模块目录 utils
    echo ---------------------------------------------------
    ping 127.0.0.1 -n 6 >nul
    exit /b 1
)

if not exist ohscrcpy_server (
    echo ------------------------------------------------
    echo [警告] 未找到 ohscrcpy_server，请确保该文件存在
    echo ------------------------------------------------
    ping 127.0.0.1 -n 6 >nul
    exit /b 1
)

if not exist HUAWEI\ohscrcpy_server (
    echo -------------------------------------------------------
    echo [警告] 未找到 HUAWEI\ohscrcpy_server，请确保该文件存在
    echo -------------------------------------------------------
    ping 127.0.0.1 -n 6 >nul
    exit /b 1
)

if not exist ohscrcpy_server.cfg (
    echo ----------------------------------------------------
    echo [警告] 未找到 ohscrcpy_server.cfg，请确保该文件存在
    echo ----------------------------------------------------
    ping 127.0.0.1 -n 6 >nul
    exit /b 1
)

if not exist resources\app.ico if not exist resources\app.icns (
    echo ----------------------------------------
    echo [警告] 未找到图标文件 resources\app.ico 或 resources\app.icns
    echo ----------------------------------------
    ping 127.0.0.1 -n 6 >nul
    exit /b 1
)

if not exist hdc\Windows\%ARCH%\hdc.exe (
    echo ------------------------------------------------------------
    echo [警告] 未找到 hdc\Windows\%ARCH%\hdc.exe，请确保该文件存在
    echo ------------------------------------------------------------
    ping 127.0.0.1 -n 6 >nul
    exit /b 1
)

if not exist hdc\Windows\%ARCH%\libusb_shared.dll (
echo ----------------------------------------------------------------------
echo [警告] 未找到 hdc\Windows\%ARCH%\libusb_shared.dll，请确保该文件存在
echo ----------------------------------------------------------------------
ping 127.0.0.1 -n 6 >nul
exit /b 1
)

echo *****************************
echo [信息] 开始安装python依赖...
echo *****************************
pip install av numpy pillow psutil pyinstaller
if %errorlevel% neq 0 (
    echo --------------------------
    echo [错误] 安装python依赖失败
    echo --------------------------
    ping 127.0.0.1 -n 6 >nul
    exit /b 1
)
echo *****************************
echo [完成] 安装python依赖完成
echo *****************************

echo ******************************
echo [信息] 开始PyInstaller打包...
echo ******************************
pyinstaller .\main.py --name "OHScrcpy" --noconfirm --clean --windowed --console --onedir --hidden-import core --hidden-import core.constants --hidden-import core.exceptions --hidden-import core.logger --hidden-import core.hdc_executor --hidden-import core.server_manager --hidden-import core.device_manager --hidden-import video --hidden-import video.config --hidden-import video.decoder --hidden-import video.stream_client --hidden-import gui --hidden-import gui.main_window --hidden-import utils --hidden-import utils.platform_utils --add-data "ohscrcpy_server:." --add-data "ohscrcpy_server.cfg:." --add-data "HUAWEI\ohscrcpy_server:HUAWEI" --add-data "hdc\Windows\%ARCH%\hdc.exe:." --add-data "hdc\Windows\%ARCH%\libusb_shared.dll:." --icon resources\app.ico
if %errorlevel% neq 0 (
    echo ---------------------------
    echo [错误] PyInstaller打包失败
    echo ---------------------------
    ping 127.0.0.1 -n 6 >nul
    exit /b 1
)
echo ****************************
echo [完成] PyInstaller打包完成
echo ****************************

echo [信息] 验证打包结果...
if not exist dist\OHScrcpy\OHScrcpy.exe (
    echo ---------------------------
    echo [错误] 未生成 OHScrcpy.exe
    echo ---------------------------
    ping 127.0.0.1 -n 6 >nul
    exit /b 1
)

if not exist dist\OHScrcpy\_internal\ohscrcpy_server (
    echo ------------------------------------
    echo [警告] 未找到打包的 ohscrcpy_server
    echo ------------------------------------
    ping 127.0.0.1 -n 6 >nul
    exit /b 1
)

if not exist dist\OHScrcpy\_internal\ohscrcpy_server.cfg (
    echo ----------------------------------------
    echo [警告] 未找到打包的 ohscrcpy_server.cfg
    echo ----------------------------------------
    ping 127.0.0.1 -n 6 >nul
    exit /b 1
)

if not exist dist\OHScrcpy\_internal\HUAWEI\ohscrcpy_server (
    echo -------------------------------------------
    echo [警告] 未找到打包的 HUAWEI\ohscrcpy_server
    echo -------------------------------------------
    ping 127.0.0.1 -n 6 >nul
    exit /b 1
)

if not exist dist\OHScrcpy\_internal\hdc.exe (
    echo ------------------------------------
    echo [警告] 未找到打包的 hdc.exe
    echo ------------------------------------
    ping 127.0.0.1 -n 6 >nul
    exit /b 1
)

if not exist dist\OHScrcpy\_internal\libusb_shared.dll (
    echo --------------------------------------
    echo [警告] 未找到打包的 libusb_shared.dll
    echo --------------------------------------
    ping 127.0.0.1 -n 6 >nul
    exit /b 1
)

echo **********************
echo [完成] 打包验证通过！
echo **********************
echo 生成的文件：
dir dist\OHScrcpy\* /b

echo [信息] 生成文件哈希值...
if not exist output\Windows mkdir output\Windows

where certutil >nul 2>nul
if %errorlevel% equ 0 (
    echo 文件哈希值：> output\Windows\OHScrcpy_dir_hash.txt
    echo ================================================================>> output\Windows\OHScrcpy_dir_hash.txt
    echo dist\OHScrcpy.exe MD5>> output\Windows\OHScrcpy_dir_hash.txt
    for /f "skip=1 delims=" %%i in ('certutil -hashfile dist\OHScrcpy.exe MD5') do (
        echo %%i>> output\Windows\OHScrcpy_dir_hash.txt 2>nul
        goto:exit_md5_loop
    )
    
    :exit_md5_loop
    echo.>> output\Windows\OHScrcpy_dir_hash.txt
    echo dist\OHScrcpy.exe SHA256>> output\Windows\OHScrcpy_dir_hash.txt
    for /f "skip=1 delims=" %%i in ('certutil -hashfile dist\OHScrcpy.exe SHA256') do (
        echo %%i>> output\Windows\OHScrcpy_dir_hash.txt 2>nul
        goto:exit_sha256_loop
    )
    
    :exit_sha256_loop
    echo ================================================================>> output\Windows\OHScrcpy_dir_hash.txt
    echo [完成] 哈希文件已生成：OHScrcpy_dir_hash.txt
    goto:succ_end
) else (
    echo [警告] 无法生成哈希文件（certutil不存在）
)

:succ_end
echo.
echo *************************************************
echo [信息] 复制日志管理脚本到dist\OHScrcpy\目录...
echo *************************************************
copy fetch_server_logs.bat dist\OHScrcpy\ >nul 2>nul
copy delete_server_logs.bat dist\OHScrcpy\ >nul 2>nul
copy fetch_and_delete_server_logs.bat dist\OHScrcpy\ >nul 2>nul
echo [完成] 日志管理脚本已复制到 dist\OHScrcpy\
dir dist\OHScrcpy\*.sh dist\OHScrcpy\*.bat /b 2>nul

echo.
echo =============================================
echo OpenHarmony OHScrcpy 自动化打包完成！
echo =============================================
echo 输出目录：dist\OHScrcpy\
echo.

echo 下一步：
echo   make_ohscrcpy_installer.bat
echo.
if not defined NO_PAUSE (
    pause
) else (
    ping 127.0.0.1 -n 6 >nul
)
