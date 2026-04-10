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
