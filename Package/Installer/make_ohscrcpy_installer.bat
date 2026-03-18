@cls
@setlocal enabledelayedexpansion
@chcp 65001 >nul
@echo off

title OpenHarmony OHScrcpy 安装程序制作脚本
color 0a
echo ===========================================================
echo     OpenHarmony OHScrcpy 安装程序制作脚本（Windows平台）
echo ===========================================================
echo.

set VERSION="v1.6.0"

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

set ISCC_PATH=
where ISCC >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] 未找到Inno Setup编译器ISCC.exe, 请确认是否已经安装Inno Setup
    echo 如果已安装, 请将安装路径增加到系统环境变量Path中
    echo 如果未安装, 请按照如下指引安装和配置Inno Setup:
    echo   1. 下载Inno Setup, https://jrsoftware.org/isdl.php
    echo   2. 安装Inno Setup, 选择"Install Inno Setup Preprocessor"
    echo   3. 将Inno Setup安装目录配置到系统环境变量Path中
    pause
    exit /b 1
)

for /f "tokens=" %%a in ('where ISCC') do (
    set ISCC_PATH=%%a
    goto:exit_iscc_loop
)

:exit_iscc_loop
echo [信息] 找到Inno Setup编译器：%ISCC_PATH%

echo [信息] 检查必要文件...
if not exist ohscrcpy_setup.iss (
    echo [错误] 未找到 ohscrcpy_setup.iss 配置文件
    pause
    exit /b 1
)

if not exist dist\OHScrcpy\OHScrcpy.exe (
    echo [错误] 未找到OHScrcpy.exe程序文件
    echo 请先运行 package_ohscrcpy.bat 进行打包
    pause
    exit /b 1
)

echo [信息] 检查文档文件...
if not exist docs\LICENSE.txt (
    echo [警告] 未找到 docs\LICENSE.txt
    pause
    exit /b 1
)

if not exist docs\INSTALL.txt (
    echo [警告] 未找到 docs\INSTALL.txt
    pause
    exit /b 1
)

if not exist output\Windows mkdir output\Windows

echo [信息] 开始编译安装程序...
%ISCC_PATH% ohscrcpy_setup.iss
if %errorlevel% neq 0 (
    echo [错误] 编译安装程序失败
    pause
    exit /b 1
)

echo [信息] 检查生成的安装程序...
set INSTALLER=
for %%f in (output\Windows\*.exe) do set INSTALLER=%%f

if "%INSTALLER%"=="" (
    echo [错误] 未生成安装程序
    pause
    exit /b 1
)

for %%f in (output\Windows\*.exe) do (
    echo [完成] 安装程序已生成：%%f
    set size=%%~zf
    set /a sizeMB=size/1048576
    echo 文件大小：!sizeMB! MB
)
echo 安装程序位置：%cd%\output\Windows\


echo [信息] 生成安装包信息...
echo OHScrcpy %VERSION% 安装包> output\Windows\package_info.txt
echo ==============================>> output\Windows\package_info.txt
echo 生成时间：%date% %time%>> output\Windows\package_info.txt
echo.>> output\Windows\package_info.txt
echo 包含文件：>> output\Windows\package_info.txt
dir dist\OHScrcpy\* /b >> output\Windows\package_info.txt
echo. >> output\Windows\package_info.txt
echo 文档文件：>> output\Windows\package_info.txt
dir docs\* /b >> output\Windows\package_info.txt

echo [信息] 生成安装程序哈希值...
where certutil >nul 2>nul
if %errorlevel% equ 0 (
    echo 安装程序哈希值：>> output\Windows\OHScrcpy_setup_Windows_%ARCH%_hash.txt
    echo ==============================>> output\Windows\OHScrcpy_setup_Windows_%ARCH%_hash.txt
    for %%f in (output\Windows\*.exe) do (
        echo 文件：%%f>> output\Windows\OHScrcpy_setup_Windows_%ARCH%_hash.txt
        certutil -hashfile "output\Windows\%%f" MD5>> output\Windows\OHScrcpy_setup_Windows_%ARCH%_hash.txt 2>nul
        echo.>> output\Windows\OHScrcpy_setup_Windows_%ARCH%_hash.txt
        certutil -hashfile "output\Windows\%%f" SHA256>> output\Windows\OHScrcpy_setup_Windows_%ARCH%_hash.txt 2>nul
        echo.>> output\Windows\OHScrcpy_setup_Windows_%ARCH%_hash.txt
        echo ==============================>> output\Windows\OHScrcpy_setup_Windows_%ARCH%_hash.txt
    )
    echo [完成] 哈希文件已生成：output\Windows\OHScrcpy_setup_Windows_%ARCH%_hash.txt
)

echo.
echo =============================================
echo OpenHarmony OHScrcpy 安装程序制作完成！
echo =============================================
echo.
pause