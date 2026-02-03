@cls
@setlocal enabledelayedexpansion
@chcp 65001 >nul

@echo ****************************************
@echo   开始安装依赖包...
@echo ****************************************
@pip install av numpy pillow psutil pyinstaller
@if !ERRORLEVEL!==1 goto PackagingFail "安装依赖包"

@echo
@echo ****************************************
@echo   开始打包应用...
@echo ****************************************
@pyinstaller .\ohscrcpy_client.py --name "OHScrcpy" --noconfirm --clean --windowed --console --onefile --add-data "ohscrcpy_server:." --add-data "ohscrcpy_server.cfg:." --add-data "HUAWEI\ohscrcpy_server:HUAWEI" --icon app.ico
@if !ERRORLEVEL!==1 goto PackagingFail "打包"

@echo
@echo ++++++++++++++++++++++++++++++++++++++++
@echo   打包成功！可执行文件位于 dist 目录下
@echo ++++++++++++++++++++++++++++++++++++++++
@pause
@exit /b 0


:PackagingFail
@echo
@echo --------------------------------------------------
@echo   %1% 失败！请检查日志，解决问题后重试
@echo --------------------------------------------------
@pause
@exit /b 1