@cls
@setlocal enabledelayedexpansion
@chcp 65001

@for /f "tokens=1 delims=" %%i in ('hdc list targets') do @(
    @echo %%i | findstr Empty
    @if !ERRORLEVEL!==1 call:UninstallScrcpyServer %%i
)

@if !ERRORLEVEL!==0 pause
@exit /b 0

:UninstallScrcpyServer
hdc -t %1 target mount
hdc -t %1 shell pkill ohscrcpy_server
hdc -t %1 shell rm /system/bin/ohscrcpy_server
hdc -t %1 shell rm /system/etc/init/ohscrcpy_server.cfg

@goto:eof