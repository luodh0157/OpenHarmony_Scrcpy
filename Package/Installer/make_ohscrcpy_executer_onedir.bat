@cls
@setlocal enabledelayedexpansion
@chcp 65001 >nul
@echo off

title OpenHarmony OHScrcpy 打包构建脚本
color 0a
echo ===========================================================
echo      OpenHarmony OHScrcpy 自动化构建脚本（Windows平台）    
echo ===========================================================

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
    pause
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
        pause
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
if not exist ohscrcpy_client.py (
    echo ---------------------------------------------------
    echo [错误] 未找到 ohscrcpy_client.py，请确保该文件存在
    echo ---------------------------------------------------
    pause
    exit /b 1
)

if not exist ohscrcpy_server (
    echo ------------------------------------------------
    echo [警告] 未找到 ohscrcpy_server，请确保该文件存在
    echo ------------------------------------------------
    pause
    exit /b 1
)

if not exist HUAWEI\ohscrcpy_server (
    echo -------------------------------------------------------
    echo [警告] 未找到 HUAWEI\ohscrcpy_server，请确保该文件存在
    echo -------------------------------------------------------
    pause
    exit /b 1
)

if not exist ohscrcpy_server.cfg (
    echo ----------------------------------------------------
    echo [警告] 未找到 ohscrcpy_server.cfg，请确保该文件存在
    echo ----------------------------------------------------
    pause
    exit /b 1
)

if not exist resources\app.ico (
    echo ----------------------------------------
    echo [警告] 未找到图标文件 resources\app.ico
    echo ----------------------------------------
    pause
    exit /b 1
)

if not exist hdc\Windows\%ARCH%\hdc.exe (
    echo --------------------------------------------------------
    echo [警告] 未找到 hdc\Windows\%ARCH%\hdc.exe，请确保该文件存在
    echo --------------------------------------------------------
    pause
    exit /b 1
)

if not exist hdc\Windows\%ARCH%\libusb_shared.dll (
    echo ------------------------------------------------------------------
    echo [警告] 未找到 hdc\Windows\%ARCH%\libusb_shared.dll，请确保该文件存在
    echo ------------------------------------------------------------------
    pause
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
    pause
    exit /b 1
)
echo *****************************
echo [完成] 安装python依赖完成
echo *****************************

echo ******************************
echo [信息] 开始PyInstaller打包...
echo ******************************
pyinstaller .\ohscrcpy_client.py --name "OHScrcpy" --noconfirm --clean --windowed --console --onedir --add-data "ohscrcpy_server:." --add-data "ohscrcpy_server.cfg:." --add-data "HUAWEI\ohscrcpy_server:HUAWEI" --add-data "hdc\Windows\%ARCH%\hdc.exe:." --add-data "hdc\Windows\%ARCH%\libusb_shared.dll:." --icon resources\app.ico
if %errorlevel% neq 0 (
    echo ---------------------------
    echo [错误] PyInstaller打包失败
    echo ---------------------------
    pause
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
    pause
    exit /b 1
)

if not exist dist\OHScrcpy\_internal\ohscrcpy_server (
    echo ------------------------------------
    echo [警告] 未找到打包的 ohscrcpy_server
    echo ------------------------------------
    pause
    exit /b 1
)

if not exist dist\OHScrcpy\_internal\ohscrcpy_server.cfg (
    echo ----------------------------------------
    echo [警告] 未找到打包的 ohscrcpy_server.cfg
    echo ----------------------------------------
    pause
    exit /b 1
)

if not exist dist\OHScrcpy\_internal\HUAWEI\ohscrcpy_server (
    echo -------------------------------------------
    echo [警告] 未找到打包的 HUAWEI\ohscrcpy_server
    echo -------------------------------------------
    pause
    exit /b 1
)

if not exist dist\OHScrcpy\_internal\hdc.exe (
    echo ------------------------------------
    echo [警告] 未找到打包的 hdc.exe
    echo ------------------------------------
    pause
    exit /b 1
)

if not exist dist\OHScrcpy\_internal\libusb_shared.dll (
    echo --------------------------------------
    echo [警告] 未找到打包的 libusb_shared.dll
    echo --------------------------------------
    pause
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
echo =============================================
echo OpenHarmony OHScrcpy 自动化打包完成！
echo =============================================
echo 输出目录：dist\OHScrcpy\
echo.
pause
goto:eof
