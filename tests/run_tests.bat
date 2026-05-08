@echo off
REM OpenHarmony_Scrcpy Windows Test Script

set SCRIPT_DIR=%~dp0
set PROJECT_DIR=%SCRIPT_DIR%..

cd /d "%PROJECT_DIR%"

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

pause