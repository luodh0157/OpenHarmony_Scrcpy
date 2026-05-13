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

REM ================================================================================
REM           OpenHarmony OHScrcpy 一键打包脚本 - Installer方式 (Windows)
REM ================================================================================

::@cls
@setlocal enabledelayedexpansion
@chcp 936 >nul
@echo off

title OpenHarmony OHScrcpy 一键打包 - Installer方式
color 0a
echo ==================================================================
echo      OpenHarmony OHScrcpy 一键打包 - Installer方式（Windows）
echo ==================================================================
echo.

set NO_PAUSE=1
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..
set VERSION=v2.1.0

goto :main_start

:cleanup_on_error
echo [错误] 打包失败，正在自动清理临时文件...
cd /d "%SCRIPT_DIR%\Installer"
if exist clear_for_installer.bat (
    call clear_for_installer.bat
) else (
    echo -------------------------------------------------------------
    echo [警告] 未找到 clear_for_installer.bat，请手动清理！
    echo -------------------------------------------------------------
)
cd /d "%SCRIPT_DIR%"
echo [完成] 自动清理完成
exit /b 1

:main_start

echo +++++++++++++++++++++++++++++++++++++++
echo [步骤 1/6] 检查环境依赖...
echo +++++++++++++++++++++++++++++++++++++++
echo.

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo -------------------------------------------------------------
    echo [错误] 未找到Python，请先安装Python 3.7+
    echo -------------------------------------------------------------
    goto :cleanup_on_error
)

if not exist "%PROJECT_ROOT%\Client\main.py" (
    echo -------------------------------------------------------------
    echo [错误] 未找到项目源文件: Client\main.py
    echo -------------------------------------------------------------
    goto :cleanup_on_error
)

echo [信息] Python:
python --version
echo [信息] 项目根目录：%PROJECT_ROOT%
echo [信息] 打包目录：%SCRIPT_DIR%\Installer
echo.
echo [完成] 环境检查通过
echo.

echo +++++++++++++++++++++++++++++++++++++++
echo [步骤 2/6] 准备打包资源...
echo +++++++++++++++++++++++++++++++++++++++
echo.

cd /d "%SCRIPT_DIR%\Installer"
if not exist prepare_for_installer.bat (
    echo -------------------------------------------------------------
    echo [错误] 未找到 prepare_for_installer.bat
    echo -------------------------------------------------------------
    goto :cleanup_on_error
)

call prepare_for_installer.bat
if %errorlevel% neq 0 (
    cd /d "%SCRIPT_DIR%"
    goto :cleanup_on_error
)
cd /d "%SCRIPT_DIR%"

echo.
echo [完成] 资源准备完成
echo.

echo +++++++++++++++++++++++++++++++++++++++++++++++++
echo [步骤 3/6] 执行PyInstaller打包（onedir模式）...
echo +++++++++++++++++++++++++++++++++++++++++++++++++
echo.

cd /d "%SCRIPT_DIR%\Installer"
if not exist make_ohscrcpy_executer_onedir.bat (
    echo -------------------------------------------------------------
    echo [错误] 未找到 make_ohscrcpy_executer_onedir.bat
    echo -------------------------------------------------------------
    goto :cleanup_on_error
)

call make_ohscrcpy_executer_onedir.bat
if %errorlevel% neq 0 (
    cd /d "%SCRIPT_DIR%"
    goto :cleanup_on_error
)
cd /d "%SCRIPT_DIR%"

echo.
echo [完成] PyInstaller打包完成
echo.

echo ++++++++++++++++++++++++++++++++++++++++
echo [步骤 4/6] 制作安装包（Inno Setup）...
echo ++++++++++++++++++++++++++++++++++++++++
echo.
echo ------------------------------------------
echo 重要提示：
echo   建议暂时关闭杀毒软件（防止误拦截）
echo ------------------------------------------
echo.
if not defined NO_PAUSE (
    pause
) else (
    timeout /t 5
)
echo.

cd /d "%SCRIPT_DIR%\Installer"
if not exist make_ohscrcpy_installer.bat (
    echo -------------------------------------------------------------
    echo [错误] 未找到 make_ohscrcpy_installer.bat
    echo -------------------------------------------------------------
    goto :cleanup_on_error
)

call make_ohscrcpy_installer.bat
if %errorlevel% neq 0 (
    cd /d "%SCRIPT_DIR%"
    goto :cleanup_on_error
)
cd /d "%SCRIPT_DIR%"

echo.
echo [完成] 安装包制作完成
echo.

echo [步骤 5/6] 显示输出结果...
echo.

if defined PROCESSOR_ARCHITEW6432 (
    set "ARCH=AMD64"
) else (
    set "ARCH=%PROCESSOR_ARCHITECTURE%"
)

if /i "%ARCH%"=="AMD64" set "ARCH=x64"
if /i "%ARCH%"=="x86" set "ARCH=x86"
if /i "%ARCH%"=="ARM64" set "ARCH=arm64"
if /i "%ARCH%"=="ARM" set "ARCH=arm"

set OUTPUT_DIR=%SCRIPT_DIR%\Installer\output\Windows\%ARCH%
echo [信息] 输出目录：%OUTPUT_DIR%
echo.

if exist "%OUTPUT_DIR%" (
    echo 生成的文件：
    dir /b "%OUTPUT_DIR%" | findstr /i "Setup zip hash"
) else (
    echo -------------------------------------------------------------
    echo [警告] 未找到输出目录
    echo -------------------------------------------------------------
)

echo.
echo [完成] 输出结果显示完成
echo.

echo +++++++++++++++++++++++++++++++++++++++
echo [步骤 6/6] 清理临时资源文件...
echo +++++++++++++++++++++++++++++++++++++++
echo.

cd /d "%SCRIPT_DIR%\Installer"
if exist clear_for_installer.bat (
    call clear_for_installer.bat
) else (
    echo -------------------------------------------------------------
    echo [警告] 未找到 clear_for_installer.bat，请手动清理！
    echo -------------------------------------------------------------
)
cd /d "%SCRIPT_DIR%"

echo.
echo [完成] 清理完成
echo.

echo =============================================
echo  Installer打包完成！
echo =============================================
echo.
echo 版本：%VERSION%
echo 输出目录：%OUTPUT_DIR%
echo.
echo 使用方法：
echo   双击 OHScrcpy_Setup_Windows_%ARCH%_%VERSION%.exe 安装
echo   运行 OHScrcpy.exe 开始投屏
echo.
echo 成功完成所有步骤！
echo.
if not defined NO_PAUSE (
    pause
) else (
    timeout /t 5
)
exit /b 0
