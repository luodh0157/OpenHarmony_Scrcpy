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
REM                  OpenHarmony OHScrcpy 总一键打包脚本 (Windows)
REM ================================================================================

@cls
@setlocal enabledelayedexpansion
@chcp 936 >nul
@echo off

title OpenHarmony OHScrcpy 一键打包工具
color 0a

set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..
set VERSION=v2.1.0

:main_menu

cls
echo =========================================
echo     OpenHarmony OHScrcpy 一键打包工具    
echo =========================================
echo.
echo 版本：%VERSION%
echo.
echo 请选择打包方式：
echo.
echo   1. Executer (单文件可执行程序)
echo   2. Installer (安装包)
echo   3. 批量打包两种方式
echo   4. 清理所有临时文件
echo   5. 退出
echo.

set /p choice=请输入选项 [1-5]: 

if "%choice%"=="1" goto :build_executer
if "%choice%"=="2" goto :build_installer
if "%choice%"=="3" goto :batch_build
if "%choice%"=="4" goto :cleanup_all
if "%choice%"=="5" goto :exit_tool

echo.
echo 无效选项，请重新选择！
echo.
timeout /t 2 >nul
goto :main_menu

:build_executer
echo.
echo =======================================
echo 开始Executer打包...
echo =======================================
echo.
if exist "%SCRIPT_DIR%\build_executer.bat" (
    call "%SCRIPT_DIR%\build_executer.bat"
) else (
    echo ---------------------------------------
    echo [错误] 未找到 build_executer.bat
    echo ---------------------------------------
)
echo.
pause
goto :main_menu

:build_installer
echo.
echo =======================================
echo 开始Installer打包...
echo =======================================
echo.
if exist "%SCRIPT_DIR%\build_installer.bat" (
    call "%SCRIPT_DIR%\build_installer.bat"
) else (
    echo ---------------------------------------
    echo [错误] 未找到 build_installer.bat
    echo ---------------------------------------
)
echo.
pause
goto :main_menu

:batch_build
echo.
echo =======================================
echo   批量打包两种方式
echo =======================================
echo.

set SUCCESS_COUNT=0
set FAIL_COUNT=0

echo +++++++++++++++++++++++++++++++++++++++
echo [1/2] 开始Executer打包...
echo +++++++++++++++++++++++++++++++++++++++
echo.
if exist "%SCRIPT_DIR%\build_executer.bat" (
    call "%SCRIPT_DIR%\build_executer.bat"
    if !errorlevel! equ 0 (
        set /a SUCCESS_COUNT+=1
        echo.
        echo ***************************************
        echo Executer打包成功！
        echo ***************************************
    ) else (
        set /a FAIL_COUNT+=1
        echo.
        echo ---------------------------------------
        echo Executer打包失败！
        echo ---------------------------------------
    )
) else (
    echo ---------------------------------------
    echo [错误] 未找到 build_executer.bat
    echo ---------------------------------------
    set /a FAIL_COUNT+=1
)

echo.
echo +++++++++++++++++++++++++++++++++++++++
echo [2/2] 开始Installer打包...
echo +++++++++++++++++++++++++++++++++++++++
echo.
if exist "%SCRIPT_DIR%\build_installer.bat" (
    call "%SCRIPT_DIR%\build_installer.bat"
    if !errorlevel! equ 0 (
        set /a SUCCESS_COUNT+=1
        echo.
        echo ***************************************
        echo Installer打包成功！
        echo ***************************************
    ) else (
        set /a FAIL_COUNT+=1
        echo.
        echo ---------------------------------------
        echo Installer打包失败！
        echo ---------------------------------------
    )
) else (
    echo ---------------------------------------
    echo [错误] 未找到 build_installer.bat
    echo ---------------------------------------
    set /a FAIL_COUNT+=1
)

echo.
echo =======================================
echo 批量打包完成！
echo =======================================
echo.
echo 成功：%SUCCESS_COUNT% 个
echo 失败：%FAIL_COUNT% 个
echo.

if %FAIL_COUNT% equ 0 (
    echo 全部打包成功！
) else (
    echo 部分打包失败，请检查错误信息
)
echo.
pause
goto :main_menu

:cleanup_all
set NO_PAUSE=1
echo.
echo =======================================
echo 正在清理所有临时文件...
echo =======================================
echo.

cd /d "%SCRIPT_DIR%\Executer"
if exist clear_for_executer.bat (
    call clear_for_executer.bat
    echo ***************************************
    echo [完成] Executer目录清理完成
    echo ***************************************
) else (
    echo ---------------------------------------------------
    echo [警告] 未找到 clear_for_executer.bat，请手动清理！
    echo ---------------------------------------------------
)
cd /d "%SCRIPT_DIR%"

cd /d "%SCRIPT_DIR%\Installer"
if exist clear_for_installer.bat (
    call clear_for_installer.bat
    echo ***************************************
    echo [完成] Installer目录清理完成
    echo ***************************************
) else (
    echo ----------------------------------------------------
    echo [警告] 未找到 clear_for_installer.bat，请手动清理！
    echo ----------------------------------------------------
)
cd /d "%SCRIPT_DIR%"

echo.
echo =======================================
echo 所有临时文件已清理完成！
echo =======================================
echo.
pause
goto :main_menu

:exit_tool
echo.
echo =======================================
echo 退出打包工具！
echo =======================================
echo.
exit /b 0
