@cls
@setlocal enabledelayedexpansion
@chcp 65001

set cur_path=%~dp0
@for /f "tokens=1 delims=" %%i in ('hdc list targets') do @(
    @echo %%i | findstr Empty
    @if !ERRORLEVEL!==1 call:InstallScrcpyServer %%i
)

@if !ERRORLEVEL!==0 pause
@exit /b 0

:InstallScrcpyServer
hdc -t %1 target mount
hdc -t %1 file send %cur_path%/bin/rk3568/ohscrcpy_server /system/bin/
hdc -t %1 shell chmod +x /system/bin/ohscrcpy_server
hdc -t %1 file send %cur_path%/ohscrcpy_server.cfg /system/etc/init/
@goto:eof
