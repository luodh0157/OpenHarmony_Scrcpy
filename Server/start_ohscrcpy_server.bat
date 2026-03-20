@cls
@setlocal enabledelayedexpansion
@chcp 65001

@for /f "tokens=1 delims=" %%i in ('hdc list targets') do @(
    @echo %%i | findstr Empty
    @if !ERRORLEVEL!==1 call:StartScrcpyServer %%i
)

@if !ERRORLEVEL!==0 pause
@exit /b 0

:StartScrcpyServer
hdc -t %1 power-shell wakeup
hdc -t %1 power-shell timeout -o 86400000
hdc -t %1 power-shell setmode 602
hdc -t %1 uinput -T -m 350 1100 350 500 200
hdc -t %1 hidumper -s 3301 -a -t
hdc -t %1 /system/bin/ohscrcpy_server
@goto:eof
