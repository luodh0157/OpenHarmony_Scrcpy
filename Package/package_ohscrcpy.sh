#!/bin/bash

packaging_fail() {
    local exit_code=$?
    local step_name=$1

    if [ $exit_code -ne 0 ]; then
        echo ""
        echo "--------------------------------------------------"
        echo "  ${step_name} 失败！请检查日志，解决问题后重试
        echo "--------------------------------------------------"
        read -p "按 Enter 键退出..."
        exit 1
    fi
}

clear

echo "****************************************"
echo "  开始安装依赖包..."
echo "****************************************"
pip install av numpy pillow psutil pyinstaller
packaging_fail "安装依赖包"

echo "****************************************"
echo "  开始打包应用..."
echo "****************************************"
pyinstaller ./ohscrcpy_client.py --name "OHScrcpy" --noconfirm --clean --windowed --console --onefile --add-data "ohscrcpy_server:." --add-data "ohscrcpy_server.cfg:." --add-data "HUAWEI\ohscrcpy_server:HUAWEI" --icon app.ico
packaging_fail "打包"

echo ""
echo "++++++++++++++++++++++++++++++++++++++++"
echo "  打包成功！可执行文件位于 dist 目录下  "
echo "++++++++++++++++++++++++++++++++++++++++"
read -p "按 Enter 键继续..."

exit 0