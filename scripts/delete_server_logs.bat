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
REM OpenHarmony OHScrcpy 服务端日志删除脚本 (Windows)
REM ================================================================================
REM
REM 功能：从设备删除服务端日志文件
REM
REM 参数：PID - 服务端进程PID（可选）
REM       - 指定PID：只删除该PID对应的日志文件（精确操作，无需确认）
REM       - 不指定PID：删除所有服务端日志文件（批量操作，需要确认）
REM
REM PID获取方式：
REM   - 从客户端日志中获取（客户端启动服务端后会自动输出PID）
REM   - 客户端日志示例：[INFO][服务端管理器] 服务正在运行，PID: 12345
REM   - 也可通过 hdc shell pgrep -f ohscrcpy_server 查询
REM
REM 日志文件格式：
REM   - 文件命名：server_PID_YYYYMMDD_HHMMSS.log
REM   - 示例：server_12345_20260506_143000.log
REM   - 存储位置：设备上 /data/local/tmp/
REM
REM 使用示例：
REM   delete_server_logs.bat 12345       # 删除PID=12345的日志文件（无需确认）
REM   delete_server_logs.bat            # 删除所有服务端日志文件（需要确认）
REM
REM 注意事项：
REM   - 删除前请确保服务端进程已停止
REM   - 精确删除（指定PID）直接执行，无需确认
REM   - 批量删除（不指定PID）需要用户确认，避免误操作
REM   - 多设备连接时会提示选择设备
REM
REM ================================================================================

@cls
@setlocal enabledelayedexpansion
@chcp 65001 >nul
@echo off

title OpenHarmony OHScrcpy 服务端日志删除脚本
color 0a
echo ===========================================================
echo      OpenHarmony OHScrcpy 服务端日志删除脚本（Windows平台）
echo ===========================================================
echo.

set SERVER_LOG_DIR=/data/local/tmp

REM 获取脚本所在目录（脚本在根目录下）
set SCRIPT_DIR=%~dp0
set INTERNAL_DIR=%SCRIPT_DIR%_internal

REM HDC工具路径（hdc在 _internal 目录下，脚本在根目录下）
set HDC_PATH=%INTERNAL_DIR%\hdc.exe

REM 选择hdc工具
set HDC_CMD=

REM 优先使用_internal目录下的hdc
if exist "%HDC_PATH%" (
    set HDC_CMD="%HDC_PATH%"
    goto hdc_found
)

REM 否则使用系统PATH中的hdc
where hdc >nul 2>&1
if not errorlevel 1 (
    set HDC_CMD=hdc
    goto hdc_found
)

echo -----------------------------------------
echo [错误] hdc工具未找到
echo -----------------------------------------
echo 请确保以下条件之一满足:
echo   1. _internal目录下存在hdc工具: %HDC_PATH%
echo   2. 系统PATH中存在hdc命令
pause
exit /b 1

:hdc_found

REM 检查设备连接并选择设备
echo [信息] 查询设备列表...
set DEVICE_COUNT=0
set SELECTED_DEVICE=

for /f "tokens=1 delims=" %%i in ('%HDC_CMD% list targets 2^>nul') do (
    set /a DEVICE_COUNT+=1
    set "DEVICE[!DEVICE_COUNT!]=%%i"
)

if %DEVICE_COUNT% equ 0 (
    echo -----------------------------------------
    echo [错误] 未连接设备
    echo -----------------------------------------
    pause
    exit /b 1
)

if %DEVICE_COUNT% equ 1 (
    echo [信息] 自动选择设备：!DEVICE[1]!
    set SELECTED_DEVICE=!DEVICE[1]!
    goto device_selected
)

echo -----------------------------------------
echo [信息] 检测到多个设备连接（共%DEVICE_COUNT%个）
echo -----------------------------------------
echo 请选择设备：
for /L %%i in (1,1,%DEVICE_COUNT%) do (
    echo   %%i. !DEVICE[%%i]!
)
echo.
set /p DEVICE_CHOICE="请输入设备编号(1-%DEVICE_COUNT%): "

if %DEVICE_CHOICE% geq 1 if %DEVICE_CHOICE% leq %DEVICE_COUNT% (
    set SELECTED_DEVICE=!DEVICE[%DEVICE_CHOICE%]!
    echo [信息] 已选择设备：!DEVICE[%DEVICE_CHOICE%]!
    goto device_selected
)

echo -----------------------------------------
echo [错误] 无效的设备编号
echo -----------------------------------------
pause
exit /b 1

:device_selected

REM 获取PID参数
set PID=%1

if defined PID (
    echo [信息] 删除PID=%PID%的日志文件...
    %HDC_CMD% -t %SELECTED_DEVICE% shell "rm -f %SERVER_LOG_DIR%/server_%PID%_*.log"
    echo ****************************
    echo [完成] 已删除日志文件
    echo ****************************
) else (
    echo -----------------------------------------
    echo [警告] 将删除设备上所有服务端日志文件！
    echo -----------------------------------------
    echo 日志位置: %SERVER_LOG_DIR%
    echo 请确保服务端进程已停止
    echo.
    set /p CONFIRM="继续吗？(y/n): "
    
    if /i "!CONFIRM!"=="y" (
        %HDC_CMD% -t %SELECTED_DEVICE% shell "rm -f %SERVER_LOG_DIR%/server_*.log"
        echo ****************************
        echo [完成] 所有日志文件已删除
        echo ****************************
    ) else (
        echo [信息] 操作已取消
    )
)

echo.
pause