@echo off
REM OpenHarmony_Scrcpy Performance Tests Runner (Windows)
REM
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

set SCRIPT_DIR=%~dp0
set PROJECT_DIR=%SCRIPT_DIR%..

cd /d "%PROJECT_DIR%"

REM 禁止生成Python字节码缓存，避免 __pycache__ 目录污染代码仓库
set PYTHONDONTWRITEBYTECODE=1

echo ==========================================
echo OpenHarmony_Scrcpy Performance Tests
echo ==========================================

python --version

REM Check pytest installation
python -m pytest --version >nul 2>nul
if errorlevel 1 (
    echo.
    echo Installing pytest...
    python -m pip install -r tests\requirements-test.txt
)

echo.
echo ==========================================
echo Running Performance Tests...
echo ==========================================

python -m pytest tests\test_performance.py -v --tb=short

echo.
echo ==========================================
echo Performance Tests Complete
echo ==========================================

REM 清理可能遗留的缓存目录（保险机制）
echo.
echo Cleaning up cache directories...
for /d /r tests %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d" 2>nul
for /d /r Client %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d" 2>nul
if exist .pytest_cache rd /s /q .pytest_cache 2>nul
echo Cleanup complete

pause