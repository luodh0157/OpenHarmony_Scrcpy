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

::@cls
@setlocal enabledelayedexpansion
@chcp 936 >nul
@echo off

title OpenHarmony OHScrcpy 安装程序制作脚本
color 0a
echo ============================================================
echo     OpenHarmony OHScrcpy 安装程序制作脚本（Windows平台）    
echo ============================================================
echo.

set VERSION="v2.1.0"

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

set "ISCC_PATH="
where ISCC >nul 2>nul
if %errorlevel% neq 0 (
    echo [错误] 未找到Inno Setup编译器ISCC.exe, 请确认是否已经安装Inno Setup
    echo 如果已安装, 请将安装路径增加到系统环境变量Path中
    echo 如果未安装, 请按照如下指引安装和配置Inno Setup:
    echo   1. 下载Inno Setup, https://jrsoftware.org/isdl.php
    echo   2. 安装Inno Setup, 选择"Install Inno Setup Preprocessor"
    echo   3. 将Inno Setup安装目录配置到系统环境变量Path中
    timeout /t 5
    exit /b 1
)

for /f "delims=" %%a in ('where ISCC 2^>nul') do (
    set "ISCC_PATH=%%a"
    goto:found_iscc
)

:not_found_iscc
echo [错误] 未找到 Inno Setup 编译器（ISCC），请确认已安装并添加至 PATH。
timeout /t 5
exit /b 1

:found_iscc
echo [信息] 找到Inno Setup编译器："!ISCC_PATH!"

echo [信息] 检查必要文件...
if not exist ohscrcpy_setup.iss (
    echo [错误] 未找到 ohscrcpy_setup.iss 配置文件
    timeout /t 5
    exit /b 1
)

if not exist dist\OHScrcpy\OHScrcpy.exe (
    echo [错误] 未找到OHScrcpy.exe程序文件
    echo 请先运行 make_ohscrcpy_executer_onedir.bat 进行打包
    timeout /t 5
    exit /b 1
)

echo [信息] 检查文档文件...
if not exist docs\LICENSE.txt (
    echo [警告] 未找到 docs\LICENSE.txt
    timeout /t 5
    exit /b 1
)

if not exist docs\INSTALL.txt (
    echo [警告] 未找到 docs\INSTALL.txt
    timeout /t 5
    exit /b 1
)

if not exist output\Windows\%ARCH% mkdir output\Windows\%ARCH%

echo [信息] 开始编译安装程序，请稍后...
"!ISCC_PATH!" /Qp /O".\output\Windows\%ARCH%" /F"OHScrcpy_Setup_Windows_%ARCH%_%VERSION%" ohscrcpy_setup.iss
if %errorlevel% neq 0 (
    echo [错误] 编译安装程序失败
    timeout /t 5
    exit /b 1
)

echo [信息] 检查生成的安装程序...
set INSTALLER=
for %%f in (output\Windows\%ARCH%\*.exe) do set INSTALLER=%%f

if "%INSTALLER%"=="" (
    echo [错误] 未生成安装程序
    timeout /t 5
    exit /b 1
)

for %%f in (output\Windows\%ARCH%\*.exe) do (
    echo [完成] 安装程序已生成：%%f
    set size=%%~zf
    set /a sizeMB=size/1048576
    echo 文件大小：!sizeMB! MB
)
echo 安装程序位置：%cd%\output\Windows\%ARCH%\


echo [信息] 生成安装包信息...
set PACKAGE_INFO_FILE="output\Windows\%ARCH%\package_info.txt"
echo OHScrcpy %VERSION% 安装包> %PACKAGE_INFO_FILE%
echo ==============================>> %PACKAGE_INFO_FILE%
echo 生成时间：%date% %time%>> %PACKAGE_INFO_FILE%
echo.>> %PACKAGE_INFO_FILE%
echo 包含文件：>> %PACKAGE_INFO_FILE%
dir dist\OHScrcpy\* /b >> %PACKAGE_INFO_FILE%
echo. >> %PACKAGE_INFO_FILE%
echo 文档文件：>> %PACKAGE_INFO_FILE%
dir docs\* /b >> %PACKAGE_INFO_FILE%

echo [信息] 生成安装程序哈希值...
pushd output\Windows\%ARCH%\
where certutil >nul 2>nul
if %errorlevel% equ 0 (
    set "HASH_FILE=OHScrcpy_setup_Windows_%ARCH%_hash.txt"
    echo 安装程序哈希值：> "!HASH_FILE!"
    echo ============================================================================>> "!HASH_FILE!"
    for %%f in (.\*.exe) do (
        set "HASH_SRC_FILE=%%f"
        echo 文件：!HASH_SRC_FILE!>> "!HASH_FILE!"
        ::certutil -hashfile "!HASH_SRC_FILE!" MD5>> "!HASH_FILE!" 2>nul
        set HASH_VALUE=
        for /f %%a in ('certutil -hashfile "!HASH_SRC_FILE!" MD5 ^| findstr /r "^[0-9a-fA-F][0-9a-fA-F]*$"') do (
            set "HASH_VALUE=%%a"
            echo   MD5: !HASH_VALUE!>> "!HASH_FILE!" 2>nul
        )
        
        ::certutil -hashfile "!HASH_SRC_FILE!" SHA256>> "!HASH_FILE!" 2>nul
        for /f %%a in ('certutil -hashfile "!HASH_SRC_FILE!" SHA256 ^| findstr /r "^[0-9a-fA-F][0-9a-fA-F]*$"') do (
            set "HASH_VALUE=%%a"
            echo   SHA256: !HASH_VALUE!>> "!HASH_FILE!" 2>nul
        )
    )
    echo ============================================================================>> "!HASH_FILE!"
    echo [完成] 哈希文件已生成：!HASH_FILE!
)
popd

echo.
echo =============================================
echo OpenHarmony OHScrcpy 安装程序制作完成！
echo =============================================
echo.
if not defined NO_PAUSE (
    pause
) else (
    timeout /t 5
)