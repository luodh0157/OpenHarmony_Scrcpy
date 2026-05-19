@echo off
REM OpenHarmony_Scrcpy Windows Test Script

set SCRIPT_DIR=%~dp0
set PROJECT_DIR=%SCRIPT_DIR%..

cd /d "%PROJECT_DIR%"

REM 禁止生成Python字节码缓存，避免 __pycache__ 目录污染代码仓库
set PYTHONDONTWRITEBYTECODE=1

echo ==========================================
echo OpenHarmony_Scrcpy Unit Tests
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
echo Running Tests...
echo ==========================================

python -m pytest tests\ -v --tb=short

echo.
echo ==========================================
echo Tests Complete
echo ==========================================

REM 清理可能遗留的缓存目录（保险机制）
echo.
echo Cleaning up cache directories...
for /d /r tests %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d" 2>nul
for /d /r Client %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d" 2>nul
if exist .pytest_cache rd /s /q .pytest_cache 2>nul
echo Cleanup complete

pause
