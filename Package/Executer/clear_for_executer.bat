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
REM        OpenHarmony OHScrcpy 自动清理资源脚本 - Executer打包方式 (Windows)
REM ================================================================================
REM
REM 功能：自动清理从项目根目录拷贝的资源
REM
REM 使用方法：
REM   1. 在Package目录下执行：clear_for_executer.bat
REM   2. 脚本自动清理所有资源文件
REM
REM 清理内容：
REM   - Client目录：main.py + core/video/gui/utils/config/hdc
REM   - Server文件：ohscrcpy_server + ohscrcpy_server.cfg
REM   - scripts目录：日志管理脚本
REM
REM ================================================================================

::@cls
@setlocal enabledelayedexpansion
@chcp 936 >nul
@echo off

title OpenHarmony OHScrcpy Executer资源清理脚本
color 0a
echo =================================================================
echo      OpenHarmony OHScrcpy Executer资源清理脚本（Windows平台）    
echo =================================================================
echo.

set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..\..
set TARGET_DIR=%SCRIPT_DIR%

echo [信息] 项目根目录：%PROJECT_ROOT%
echo [信息] 目标目录：%TARGET_DIR%
echo.

echo [信息] 清理目标目录资源文件...
cd /d "%TARGET_DIR%"
if exist core rd /s /q core
if exist video rd /s /q video
if exist gui rd /s /q gui
if exist utils rd /s /q utils
if exist config rd /s /q config
if exist hdc rd /s /q hdc
if exist scripts rd /s /q scripts
if exist main.py del main.py
if exist ohscrcpy_server del ohscrcpy_server
if exist ohscrcpy_server.cfg del ohscrcpy_server.cfg
if exist HUAWEI rd /s /q HUAWEI

if exist OHScrcpy.spec del OHScrcpy.spec
if exist fetch_server_logs.bat del fetch_server_logs.bat
if exist fetch_server_logs.sh del fetch_server_logs.sh
if exist delete_server_logs.bat del delete_server_logs.bat
if exist delete_server_logs.sh del delete_server_logs.sh
if exist fetch_and_delete_server_logs.bat del fetch_and_delete_server_logs.bat
if exist fetch_and_delete_server_logs.sh del fetch_and_delete_server_logs.sh
cd /d "%SCRIPT_DIR%"
echo.

echo [信息] 清理构建临时文件...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist __pycache__ rmdir /s /q __pycache__

echo ****************************
echo [完成] 资源清理完成！
echo ****************************

if not defined NO_PAUSE pause