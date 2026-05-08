#!/bin/bash
# 正确生成Windows批处理脚本（UTF-8 + CRLF + @chcp 65001）

SCRIPT_DIR="/home/luodonghui/OpenHarmony_Scrcpy/scripts"

# fetch_server_logs.bat
printf 'REM Copyright (c) 2026 luodh0157.\r
REM Licensed under the Apache License, Version 2.0 (the \"License\").\r
REM you may not use this file except in compliance with the License.\r
REM You may obtain a copy of the License at\r
REM\r
REM     http://www.apache.org/licenses/LICENSE-2.0\r
REM\r
REM Unless required by applicable law or agreed to in writing, software\r
REM distributed under the License is distributed on an \"AS IS\" BASIS,\r
REM WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.\r
REM See the License for the specific language governing permissions and\r
REM limitations under the License.\r
\r
@cls\r
@setlocal enabledelayedexpansion\r
@chcp 65001 >nul\r
@echo off\r
\r
title OpenHarmony OHScrcpy 服务端日志拉取脚本\r
color 0a\r
\r
set SERVER_LOG_DIR=/data/local/tmp\r
set DEST_DIR=logs\r
\r
REM 获取脚本所在目录（脚本在根目录下）\r
set SCRIPT_DIR=%~dp0\r
set INTERNAL_DIR=%SCRIPT_DIR%_internal\r
\r
REM HDC工具路径（hdc在 _internal 目录下，脚本在根目录下）\r
set HDC_PATH=%INTERNAL_DIR%\\hdc.exe\r
\r
REM 选择hdc工具\r
set HDC_CMD=\r
\r
REM 优先使用_internal目录下的hdc\r
if exist \"%HDC_PATH%\" (\r
    set HDC_CMD=\"%HDC_PATH%\"\r
    goto hdc_found\r
)\r
\r
REM 否则使用系统PATH中的hdc\r
where hdc >nul 2>&1\r
if not errorlevel 1 (\r
    set HDC_CMD=hdc\r
    goto hdc_found\r
)\r
\r
echo 错误: hdc工具未找到\r
echo 请确保以下条件之一满足:\r
echo   1. _internal目录下存在hdc工具: %HDC_PATH%\r
echo   2. 系统PATH中存在hdc命令\r
pause\r
exit /b 1\r
\r
:hdc_found\r
\r
REM 检查HDC连接状态\r
%HDC_CMD% list targets >nul 2>&1\r
if errorlevel 1 (\r
    echo 错误: 未连接设备或HDC不工作\r
    pause\r
    exit /b 1\r
)\r
\r
REM 创建本地logs目录\r
if not exist \"%DEST_DIR%\" mkdir \"%DEST_DIR%\"\r
\r
REM 获取PID参数\r
set PID=%1\r
\r
if defined PID (\r
    REM 精确拉取指定PID的日志文件\r
    echo 拉取PID=%PID%的日志文件...\r
    set LOG_PATTERN=server_%PID%_*.log\r
) else (\r
    REM 批量拉取所有日志文件\r
    echo 拉取所有服务端日志文件...\r
    set LOG_PATTERN=server_*.log\r
)\r
\r
REM 列出设备上的日志文件\r
for /f \"delims=\" %%i in ('%HDC_CMD% shell \"ls %SERVER_LOG_DIR%/%LOG_PATTERN% 2>/dev/null\"') do (\r
    set log_file=%%i\r
    if not \"!log_file!\"==\"\" (\r
        echo 找到日志文件: !log_file!\r
        \r
        REM 拉取日志文件到本地\r
        set dest_file=%DEST_DIR%\\!log_file!\r
        %HDC_CMD% file recv %SERVER_LOG_DIR%/!log_file! !dest_file! >nul 2>&1\r
        \r
        if exist \"!dest_file!\" (\r
            echo 已拉取到本地: !dest_file!\r
        ) else (\r
            echo 错误: 拉取失败 !log_file!\r
        )\r
    )\r
)\r
\r
echo.\r
echo 完成. 日志文件已拉取到: %DEST_DIR%\\r
echo.\r
pause\r
' > "$SCRIPT_DIR/fetch_server_logs.bat"

echo "fetch_server_logs.bat generated with UTF-8+CRLF+chcp65001"
