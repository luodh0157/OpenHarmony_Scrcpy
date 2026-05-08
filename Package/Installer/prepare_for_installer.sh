#!/bin/bash

# Copyright (c) 2026 luodh0157.
# Licensed under the Apache License, Version 2.0 (the "License").
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# ================================================================================
#      OpenHarmony OHScrcpy 自动准备资源脚本 - Installer打包方式 (Linux/Mac)
# ================================================================================
#
# 功能：自动从项目根目录拷贝所需资源到Package/Installer目录
#
# 使用方法：
#   1. 在Package目录下执行：./prepare_for_installer.sh
#   2. 脚本自动拷贝所有必需文件
#   3. 完成后进入Package/Installer目录执行打包脚本
#
# 拷贝内容：
#   - Client目录：main.py + core/video/gui/utils/config/hdc
#   - Server文件：ohscrcpy_server + ohscrcpy_server.cfg
#   - CHANGELOG.txt：拷贝到docs目录
#
# 输出位置：
#   - Package/Installer/（当前目录）
#
# 下一步操作：
#   - cd Package/Installer
#   - ./make_ohscrcpy_executer_onedir.sh
#   - ./make_ohscrcpy_installer.sh
#
# ================================================================================

export TERM=xterm-256color
clear

echo -e "\033[32m===============================================================\033[0m"
echo -e "\033[32m     OpenHarmony OHScrcpy Installer资源准备脚本（Linux/Mac平台）    \033[0m"
echo -e "\033[32m===============================================================\033[0m"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
TARGET_DIR="$SCRIPT_DIR"

echo "[信息] 项目根目录：$PROJECT_ROOT"
echo "[信息] 目标目录：$TARGET_DIR"
echo ""

# 检查项目根目录是否存在必要文件
if [ ! -f "$PROJECT_ROOT/Client/main.py" ]; then
    echo -e "\033[31m-----------------------------------------\033[0m"
    echo -e "\033[31m[错误] 未找到 Client/main.py\033[0m"
    echo -e "\033[31m-----------------------------------------\033[0m"
    read -p "按任意键继续..."
    exit 1
fi

if [ ! -d "$PROJECT_ROOT/Client/core" ]; then
    echo -e "\033[31m-----------------------------------------\033[0m"
    echo -e "\033[31m[错误] 未找到 Client/core 目录\033[0m"
    echo -e "\033[31m-----------------------------------------\033[0m"
    read -p "按任意键继续..."
    exit 1
fi

echo "[信息] 清理目标目录旧文件..."
cd "$TARGET_DIR"
rm -rf core video gui utils config hdc scripts
rm -f main.py ohscrcpy_server ohscrcpy_server.cfg
rm -rf HUAWEI
rm -f fetch_server_logs.sh fetch_server_logs.bat
rm -f delete_server_logs.sh delete_server_logs.bat
rm -f fetch_and_delete_server_logs.sh fetch_and_delete_server_logs.bat
cd "$SCRIPT_DIR"
echo "[完成] 清理完成"
echo ""

echo "[信息] 拷贝Client文件和目录..."
cp "$PROJECT_ROOT/Client/main.py" "$TARGET_DIR/"
cp -r "$PROJECT_ROOT/Client/core" "$TARGET_DIR/"
cp -r "$PROJECT_ROOT/Client/video" "$TARGET_DIR/"
cp -r "$PROJECT_ROOT/Client/gui" "$TARGET_DIR/"
cp -r "$PROJECT_ROOT/Client/utils" "$TARGET_DIR/"
cp -r "$PROJECT_ROOT/Client/config" "$TARGET_DIR/"
cp -r "$PROJECT_ROOT/Client/hdc" "$TARGET_DIR/"

echo "[信息] 拷贝Server文件..."
if [ -f "$PROJECT_ROOT/Server/bin/rk3568/ohscrcpy_server" ]; then
    cp "$PROJECT_ROOT/Server/bin/rk3568/ohscrcpy_server" "$TARGET_DIR/"
elif [ -f "$PROJECT_ROOT/Server/bin/rk3588/ohscrcpy_server" ]; then
    cp "$PROJECT_ROOT/Server/bin/rk3588/ohscrcpy_server" "$TARGET_DIR/"
else
    echo -e "\033[33m-----------------------------------------\033[0m"
    echo -e "\033[33m[警告] 未找到ohscrcpy_server文件\033[0m"
    echo -e "\033[33m-----------------------------------------\033[0m"
fi

cp "$PROJECT_ROOT/Server/ohscrcpy_server.cfg" "$TARGET_DIR/"

mkdir -p "$TARGET_DIR/HUAWEI"
if [ -f "$PROJECT_ROOT/Server/bin/harmonyos/ohscrcpy_server" ]; then
    cp "$PROJECT_ROOT/Server/bin/harmonyos/ohscrcpy_server" "$TARGET_DIR/HUAWEI/"
else
    echo -e "\033[33m-----------------------------------------\033[0m"
    echo -e "\033[33m[警告] 未找到HUAWEI/ohscrcpy_server文件\033[0m"
    echo -e "\033[33m-----------------------------------------\033[0m"
fi

echo "[信息] 拷贝CHANGELOG到docs目录..."
if [ -f "$PROJECT_ROOT/CHANGELOG.txt" ]; then
    mkdir -p "$TARGET_DIR/docs"
    cp "$PROJECT_ROOT/CHANGELOG.txt" "$TARGET_DIR/docs/"
else
    echo -e "\033[33m-----------------------------------------\033[0m"
    echo -e "\033[33m[警告] 未找到CHANGELOG.txt文件\033[0m"
    echo -e "\033[33m-----------------------------------------\033[0m"
fi

echo "[信息] 拷贝日志脚本到根目录..."
cp "$PROJECT_ROOT/scripts/fetch_server_logs.sh" "$TARGET_DIR/"
cp "$PROJECT_ROOT/scripts/fetch_server_logs.bat" "$TARGET_DIR/"
cp "$PROJECT_ROOT/scripts/delete_server_logs.sh" "$TARGET_DIR/"
cp "$PROJECT_ROOT/scripts/delete_server_logs.bat" "$TARGET_DIR/"
cp "$PROJECT_ROOT/scripts/fetch_and_delete_server_logs.sh" "$TARGET_DIR/"
cp "$PROJECT_ROOT/scripts/fetch_and_delete_server_logs.bat" "$TARGET_DIR/"

echo ""
echo -e "\033[32m****************************\033[0m"
echo -e "\033[32m[完成] 资源准备完成！\033[0m"
echo -e "\033[32m****************************\033[0m"
echo ""
echo "已拷贝的文件和目录："
cd "$TARGET_DIR"
ls -la | grep -E "^d|^-" | grep -v "^total"
cd "$SCRIPT_DIR"
echo ""
echo "下一步："
echo "  ./make_ohscrcpy_executer_onedir.sh"
echo "  ./make_ohscrcpy_installer.sh"
echo ""
read -p "按任意键继续..."
