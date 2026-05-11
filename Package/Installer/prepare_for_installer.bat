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
REM       OpenHarmony OHScrcpy 自动准备资源脚本 - Installer打包方式 (Windows)
REM ================================================================================

@cls
@setlocal enabledelayedexpansion
@chcp 936 >nul
@echo off

title OpenHarmony OHScrcpy Installer资源准备脚本
color 0a
echo ==================================================================
echo      OpenHarmony OHScrcpy Installer资源准备脚本（Windows平台）
echo ==================================================================
echo.

set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..\..
set TARGET_DIR=%SCRIPT_DIR%

echo [信息] 项目根目录：%PROJECT_ROOT%
echo [信息] 目标目录：%TARGET_DIR%
echo.

REM 检查项目根目录是否存在必要文件
if not exist "%PROJECT_ROOT%\Client\main.py" (
    echo -----------------------------------------
    echo [错误] 未找到 Client\main.py
    echo -----------------------------------------
    if not defined NO_PAUSE pause
    exit /b 1
)

if not exist "%PROJECT_ROOT%\Client\core" (
    echo -----------------------------------------
    echo [错误] 未找到 Client\core 目录
    echo -----------------------------------------
    if not defined NO_PAUSE pause
    exit /b 1
)

echo [信息] 清理目标目录旧文件...
cd /d "%TARGET_DIR%"
if exist clear_for_installer.bat (
    call clear_for_installer.bat
) else (
    echo [警告] 未找到 clear_for_installer.bat，请手动清理！
    exit /b 1
)
cd /d "%SCRIPT_DIR%"
echo [完成] 清理完成
echo.

echo [信息] 拷贝Client文件和目录...
copy "%PROJECT_ROOT%\Client\main.py" "%TARGET_DIR%\"
xcopy /E /I /Q "%PROJECT_ROOT%\Client\core" "%TARGET_DIR%\core"
xcopy /E /I /Q "%PROJECT_ROOT%\Client\video" "%TARGET_DIR%\video"
xcopy /E /I /Q "%PROJECT_ROOT%\Client\gui" "%TARGET_DIR%\gui"
xcopy /E /I /Q "%PROJECT_ROOT%\Client\utils" "%TARGET_DIR%\utils"
xcopy /E /I /Q "%PROJECT_ROOT%\Client\config" "%TARGET_DIR%\config"
xcopy /E /I /Q "%PROJECT_ROOT%\Client\hdc" "%TARGET_DIR%\hdc"

echo [信息] 拷贝Server文件...
if exist "%PROJECT_ROOT%\Server\bin\rk3568\ohscrcpy_server" (
    copy "%PROJECT_ROOT%\Server\bin\rk3568\ohscrcpy_server" "%TARGET_DIR%\"
) else if exist "%PROJECT_ROOT%\Server\bin\rk3588\ohscrcpy_server" (
    copy "%PROJECT_ROOT%\Server\bin\rk3588\ohscrcpy_server" "%TARGET_DIR%\"
) else (
    echo -----------------------------------------
    echo [警告] 未找到ohscrcpy_server文件
    echo -----------------------------------------
)

copy "%PROJECT_ROOT%\Server\ohscrcpy_server.cfg" "%TARGET_DIR%\"

mkdir "%TARGET_DIR%\HUAWEI"
if exist "%PROJECT_ROOT%\Server\bin\harmonyos\ohscrcpy_server" (
    copy "%PROJECT_ROOT%\Server\bin\harmonyos\ohscrcpy_server" "%TARGET_DIR%\HUAWEI\"
) else (
    echo -----------------------------------------
    echo [警告] 未找到HUAWEI\ohscrcpy_server文件
    echo -----------------------------------------
)

echo [信息] 拷贝CHANGELOG到docs目录...
if exist "%PROJECT_ROOT%\CHANGELOG.txt" (
    mkdir "%TARGET_DIR%\docs"
    copy "%PROJECT_ROOT%\CHANGELOG.txt" "%TARGET_DIR%\docs\"
) else (
    echo -----------------------------------------
    echo [警告] 未找到CHANGELOG.txt文件
    echo -----------------------------------------
)

echo [信息] 拷贝日志脚本到根目录...
copy "%PROJECT_ROOT%\scripts\fetch_server_logs.bat" "%TARGET_DIR%\"
copy "%PROJECT_ROOT%\scripts\fetch_server_logs.sh" "%TARGET_DIR%\"
copy "%PROJECT_ROOT%\scripts\delete_server_logs.bat" "%TARGET_DIR%\"
copy "%PROJECT_ROOT%\scripts\delete_server_logs.sh" "%TARGET_DIR%\"
copy "%PROJECT_ROOT%\scripts\fetch_and_delete_server_logs.bat" "%TARGET_DIR%\"
copy "%PROJECT_ROOT%\scripts\fetch_and_delete_server_logs.sh" "%TARGET_DIR%\"

echo.
echo ****************************
echo [完成] 资源准备完成！
echo ****************************
echo.
echo 已拷贝的文件和目录：
cd /d "%TARGET_DIR%"
dir /b
cd /d "%SCRIPT_DIR%"
echo.
echo 下一步：
echo   make_ohscrcpy_executer_onedir.bat
echo   make_ohscrcpy_installer.bat
echo.
if not defined NO_PAUSE pause
