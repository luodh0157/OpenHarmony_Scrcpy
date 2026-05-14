REM Copyright (c) 2026 luodh0157.
REM Licensed under the Apache License, Version 2.0 (the "License").
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

::@cls
@setlocal enabledelayedexpansion
@chcp 936 >nul
@echo off

title OpenHarmony OHScrcpy 打包构建脚本
color 0a
echo ============================================================
echo      OpenHarmony OHScrcpy 自动化构建脚本（Windows平台）     
echo ============================================================

REM 获取版本号（优先使用环境变量）
if not defined VERSION (
    call "%~dp0..\get_version.bat"
    if not defined VERSION (
        echo [警告] 未设置 VERSION 环境变量且未找到 get_version.bat，使用默认版本
        set VERSION=v2.1.0
    )
)

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
    timeout /t 5
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
        timeout /t 5
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
    timeout /t 5
    exit /b 1
)

if not exist core (
    echo ---------------------------------------------------
    echo [错误] 未找到模块目录 core
    echo ---------------------------------------------------
    timeout /t 5
    exit /b 1
)

if not exist video (
    echo ---------------------------------------------------
    echo [错误] 未找到模块目录 video
    echo ---------------------------------------------------
    timeout /t 5
    exit /b 1
)

if not exist gui (
    echo ---------------------------------------------------
    echo [错误] 未找到模块目录 gui
    echo ---------------------------------------------------
    timeout /t 5
    exit /b 1
)

if not exist utils (
    echo ---------------------------------------------------
    echo [错误] 未找到模块目录 utils
    echo ---------------------------------------------------
    timeout /t 5
    exit /b 1
)

if not exist ohscrcpy_server (
    echo ------------------------------------------------
    echo [警告] 未找到 ohscrcpy_server，请确保该文件存在
    echo ------------------------------------------------
    timeout /t 5
    exit /b 1
)

if not exist HUAWEI\ohscrcpy_server (
    echo -------------------------------------------------------
    echo [警告] 未找到 HUAWEI\ohscrcpy_server，请确保该文件存在
    echo -------------------------------------------------------
    timeout /t 5
    exit /b 1
)

if not exist ohscrcpy_server.cfg (
    echo ----------------------------------------------------
    echo [警告] 未找到 ohscrcpy_server.cfg，请确保该文件存在
    echo ----------------------------------------------------
    timeout /t 5
    exit /b 1
)

if not exist app.ico (
    echo ----------------------------------------
    echo [警告] 未找到图标文件 app.ico
    echo ----------------------------------------
    timeout /t 5
    exit /b 1
)

if not exist hdc\Windows\%ARCH%\hdc.exe (
    echo -----------------------------------------------------------
    echo [警告] 未找到 hdc\Windows\%ARCH%\hdc.exe，请确保该文件存在
    echo -----------------------------------------------------------
    timeout /t 5
    exit /b 1
)

if not exist hdc\Windows\%ARCH%\libusb_shared.dll (
    echo ---------------------------------------------------------------------
    echo [警告] 未找到 hdc\Windows\%ARCH%\libusb_shared.dll，请确保该文件存在
    echo ---------------------------------------------------------------------
    timeout /t 5
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
    timeout /t 5
    exit /b 1
)
echo *****************************
echo [完成] 安装python依赖完成
echo *****************************

echo ******************************
echo [信息] 开始PyInstaller打包...
echo ******************************
pyinstaller .\main.py --name "OHScrcpy" --noconfirm --clean --windowed --console --onefile --hidden-import core --hidden-import core.constants --hidden-import core.exceptions --hidden-import core.logger --hidden-import core.hdc_executor --hidden-import core.server_manager --hidden-import core.device_manager --hidden-import video --hidden-import video.config --hidden-import video.decoder --hidden-import video.stream_client --hidden-import gui --hidden-import gui.device_controller --hidden-import utils --hidden-import utils.platform_utils --add-data "ohscrcpy_server:." --add-data "ohscrcpy_server.cfg:." --add-data "HUAWEI\ohscrcpy_server:HUAWEI" --add-data "hdc\Windows\%ARCH%\hdc.exe:." --add-data "hdc\Windows\%ARCH%\libusb_shared.dll:." --icon app.ico
if %errorlevel% neq 0 (
    echo ---------------------------
    echo [错误] PyInstaller打包失败
    echo ---------------------------
    timeout /t 5
    exit /b 1
)
echo ****************************
echo [完成] PyInstaller打包完成
echo ****************************

echo [信息] 验证打包结果...
if not exist dist\OHScrcpy.exe (
    echo ---------------------------
    echo [错误] 未生成 OHScrcpy.exe
    echo ---------------------------
    timeout /t 5
    exit /b 1
)

echo **********************
echo [完成] 打包验证通过！
echo **********************
echo 生成的文件：
dir dist\* /b

echo [信息] 生成文件哈希值...
if not exist output\Windows\%ARCH% mkdir output\Windows\%ARCH%
copy dist\OHScrcpy.exe output\Windows\%ARCH%  >nul
where certutil >nul 2>nul
if %errorlevel% equ 0 (
    echo 文件哈希值：> output\Windows\%ARCH%\OHScrcpy_Exec_Windows_%ARCH%_hash.txt
    echo ================================================================>> output\Windows\%ARCH%\OHScrcpy_Exec_Windows_%ARCH%_hash.txt
    echo dist\OHScrcpy.exe MD5>> output\Windows\%ARCH%\OHScrcpy_Exec_Windows_%ARCH%_hash.txt
    for /f "skip=1 delims=" %%i in ('certutil -hashfile dist\OHScrcpy.exe MD5') do (
        echo %%i>> output\Windows\%ARCH%\OHScrcpy_Exec_Windows_%ARCH%_hash.txt 2>nul
        goto:exit_md5_loop
    )
    
    :exit_md5_loop
    echo.>> output\Windows\%ARCH%\OHScrcpy_Exec_Windows_%ARCH%_hash.txt
    echo dist\OHScrcpy.exe SHA256>> output\Windows\%ARCH%\OHScrcpy_Exec_Windows_%ARCH%_hash.txt
    for /f "skip=1 delims=" %%i in ('certutil -hashfile dist\OHScrcpy.exe SHA256') do (
        echo %%i>> output\Windows\%ARCH%\OHScrcpy_Exec_Windows_%ARCH%_hash.txt 2>nul
        goto:exit_sha256_loop
    )
    
    :exit_sha256_loop
    echo ================================================================>> output\Windows\%ARCH%\OHScrcpy_Exec_Windows_%ARCH%_hash.txt
    echo [完成] 哈希文件已生成：output\Windows\%ARCH%\OHScrcpy_Exec_Windows_%ARCH%_hash.txt
    goto:succ_end
) else (
    echo [警告] 无法生成哈希文件（certutil不存在）
)

:succ_end
echo.
echo ***************************************
echo [信息] 检查日志脚本（Windows平台）...
echo ***************************************

REM 只打包当前平台的日志脚本（Windows只打包.bat脚本）
set LOG_SCRIPTS=
set LOG_SCRIPTS_PS=
if exist fetch_server_logs.bat (
    set LOG_SCRIPTS=%LOG_SCRIPTS% fetch_server_logs.bat
    if defined LOG_SCRIPTS_PS (
        set LOG_SCRIPTS_PS=%LOG_SCRIPTS_PS%,fetch_server_logs.bat
    ) else (
        set LOG_SCRIPTS_PS=fetch_server_logs.bat
    )
)
if exist delete_server_logs.bat (
    set LOG_SCRIPTS=%LOG_SCRIPTS% delete_server_logs.bat
    if defined LOG_SCRIPTS_PS (
        set LOG_SCRIPTS_PS=%LOG_SCRIPTS_PS%,delete_server_logs.bat
    ) else (
        set LOG_SCRIPTS_PS=delete_server_logs.bat
    )
)
if exist fetch_and_delete_server_logs.bat (
    set LOG_SCRIPTS=%LOG_SCRIPTS% fetch_and_delete_server_logs.bat
    if defined LOG_SCRIPTS_PS (
        set LOG_SCRIPTS_PS=%LOG_SCRIPTS_PS%,fetch_and_delete_server_logs.bat
    ) else (
        set LOG_SCRIPTS_PS=fetch_and_delete_server_logs.bat
    )
)

if not defined LOG_SCRIPTS (
    echo [警告] 未找到日志脚本文件
) else (
    echo [信息] 包含日志脚本（Windows平台）：%LOG_SCRIPTS%
)

echo.
echo ******************************
echo [信息] 创建发布ZIP包...
echo ******************************

set ZIP_NAME=OHScrcpy_Exec_Windows_%ARCH%_%VERSION%.zip
set ZIP_PATH=output\Windows\%ARCH%\%ZIP_NAME%

REM 拷贝日志脚本到output目录
if defined LOG_SCRIPTS (
    for %%s in (%LOG_SCRIPTS%) do (
        if exist %%s copy %%s output\Windows\%ARCH%\ >nul
    )
)

cd output\Windows\%ARCH%

if defined LOG_SCRIPTS (
    echo [信息] 包含日志脚本到ZIP包...
    if exist ..\..\..\..\tools\7z.exe (
        ..\..\..\..\tools\7z.exe a -tzip %ZIP_NAME% OHScrcpy.exe OHScrcpy_Exec_Windows_%ARCH%_hash.txt %LOG_SCRIPTS%
    ) else (
        powershell -Command "Compress-Archive -Path OHScrcpy.exe,OHScrcpy_Exec_Windows_%ARCH%_hash.txt,%LOG_SCRIPTS_PS% -DestinationPath %ZIP_NAME% -Force"
    )
) else (
    if exist ..\..\..\..\tools\7z.exe (
        ..\..\..\..\tools\7z.exe a -tzip %ZIP_NAME% OHScrcpy.exe OHScrcpy_Exec_Windows_%ARCH%_hash.txt
    ) else (
        powershell -Command "Compress-Archive -Path OHScrcpy.exe,OHScrcpy_Exec_Windows_%ARCH%_hash.txt -DestinationPath %ZIP_NAME% -Force"
    )
)

chcp 936 >nul
cd ..\..\..\
if exist output\Windows\%ARCH%\%ZIP_NAME% (
    echo [完成] ZIP包已创建: %ZIP_PATH%
    dir output\Windows\%ARCH%\%ZIP_NAME%
) else (
    echo [警告] ZIP包创建失败
)

echo.
echo =============================================
echo OpenHarmony OHScrcpy 自动化打包完成！
echo =============================================
echo 输出目录：output\Windows\%ARCH%\
echo 生成文件：
echo   - OHScrcpy.exe
echo   - OHScrcpy_Exec_Windows_%ARCH%_hash.txt
if defined LOG_SCRIPTS (
    echo   - 日志脚本（3个.bat文件）
)
echo   - %ZIP_NAME%
echo.
if not defined NO_PAUSE (
    pause
)else (
    timeout /t 5
)
