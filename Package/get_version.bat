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

REM 从 constants.py 获取版本号
REM 用法: call get_version.bat  (会设置 VERSION 环境变量)

@echo off

for /f "delims=" %%i in ('python -c "import sys; sys.path.insert(0, '..\\Client'); from core.constants import VERSION; print(VERSION)" 2^>nul') do set VERSION=%%i

if not defined VERSION set VERSION=v2.1.0
