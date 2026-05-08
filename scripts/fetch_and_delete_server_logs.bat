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
REM OpenHarmony OHScrcpy 服务端日志管理脚本 (Windows - 拉取并删除)
REM ================================================================================
REM
REM 功能：串行执行拉取+删除服务端日志文件
REM
REM 参数：PID - 服务端进程PID（可选）
REM       - 指定PID：只处理该PID对应的日志文件（精确操作）
REM       - 不指定PID：处理所有服务端日志文件（批量操作，删除前需要确认）
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
REM   - 拉取位置：本地 logs\ 目录
REM
REM 使用示例：
REM   fetch_and_delete_server_logs.bat 12345  # 拉取并删除PID=12345的日志文件
REM   fetch_and_delete_server_logs.bat        # 拉取所有日志，然后删除（需确认）
REM
REM 注意事项：
REM   - 自动执行：先拉取到本地，然后删除设备上的日志
REM   - 指定PID：拉取后直接删除，无需确认
REM   - 不指定PID：拉取所有日志后，删除前需要确认（安全机制）
REM   - 多设备连接时会提示选择设备
REM
REM ================================================================================

@cls
@setlocal enabledelayedexpansion
@chcp 65001 >nul
@echo off

title OpenHarmony OHScrcpy 服务端日志拉取并删除脚本
color 0a
echo ===========================================================
echo      OpenHarmony OHScrcpy 服务端日志拉取并删除脚本（Windows平台）
echo ===========================================================
echo.

set SERVER_LOG_DIR=/data/local/tmp
set DEST_DIR=logs

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

REM 创建本地logs目录
if not exist "%DEST_DIR%" mkdir "%DEST_DIR%"

REM 获取PID参数
set PID=%1

if defined PID (
    echo [信息] 拉取PID=%PID%的日志文件...
    set LOG_PATTERN=server_%PID%_*.log
) else (
    echo [信息] 拉取所有服务端日志文件...
    set LOG_PATTERN=server_*.log
)

REM ========== 第一步：拉取日志 ==========

echo.
echo ========================================
echo 第一步：拉取日志到本地
echo ========================================
echo.

REM 列出设备上的日志文件
set FETCH_COUNT=0
for /f "delims=" %%i in ('%HDC_CMD% -t %SELECTED_DEVICE% shell "ls %SERVER_LOG_DIR%/%LOG_PATTERN% 2>/dev/null"') do (
    set full_path=%%i
    if not "!full_path!"=="" (
        if "!full_path!" neq "No such file or directory" (
            REM 从完整路径中提取文件名（basename）
            for %%f in ("!full_path!") do set log_file=%%~nxf
            
            echo 找到日志文件: !log_file!
            
            REM 拉取日志文件到本地
            set dest_file=%DEST_DIR%\!log_file!
            %HDC_CMD% -t %SELECTED_DEVICE% file recv %SERVER_LOG_DIR%/!log_file! !dest_file! >nul 2>&1
            
            if exist "!dest_file!" (
                echo [完成] 已拉取到本地: !dest_file!
                set /a FETCH_COUNT+=1
            ) else (
                echo -----------------------------------------
                echo [错误] 拉取失败 !log_file!
                echo -----------------------------------------
            )
        )
    )
)

echo.
echo ****************************
echo [完成] 已拉取 %FETCH_COUNT% 个日志文件到: %DEST_DIR%\
echo ****************************
echo.

REM ========== 第二步：删除日志 ==========

echo.
echo ========================================
echo 第二步：删除设备上的日志
echo ========================================
echo.

if defined PID (
    REM 指定PID：直接删除，无需确认
    echo [信息] 删除PID=%PID%的日志文件...
    %HDC_CMD% -t %SELECTED_DEVICE% shell "rm -f %SERVER_LOG_DIR%/server_%PID%_*.log"
    echo ****************************
    echo [完成] 已删除设备上的日志文件
    echo ****************************
) else (
    REM 不指定PID：批量删除，需要确认
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
        echo [完成] 已删除设备上的所有日志文件
        echo ****************************
    ) else (
        echo [信息] 删除操作已取消（日志已拉取到本地）
    )
)

echo.
echo ****************************
echo [完成] 全流程完成
echo ****************************
echo.
pause