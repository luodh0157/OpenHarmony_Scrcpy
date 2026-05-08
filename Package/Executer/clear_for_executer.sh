#!/bin/bash

# Copyright (c) 2026 luodh0157.
# Licensed under the Apache License, Version 2.0 (the "License");
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
#       OpenHarmony OHScrcpy 自动清理资源脚本 - Executer打包方式 (Linux/Mac)
# ================================================================================
#
# 功能：自动清理从项目根目录拷贝的资源
#
# 使用方法：
#   1. 在Package目录下执行：./clear_for_executer.sh
#   2. 脚本自动清理所有资源文件
#
# 清理内容：
#   - Client目录：main.py + core/video/gui/utils/config/hdc
#   - Server文件：ohscrcpy_server + ohscrcpy_server.cfg
#   - scripts目录：日志管理脚本（拷贝到根目录）
#
# ================================================================================

export TERM=xterm-256color
clear

echo -e "\033[32m===================================================================\033[0m"
echo -e "\033[32m     OpenHarmony OHScrcpy Executer资源清理脚本（Linux/Mac平台）    \033[0m"
echo -e "\033[32m===================================================================\033[0m"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
TARGET_DIR="$SCRIPT_DIR"

echo "[信息] 项目根目录：$PROJECT_ROOT"
echo "[信息] 目标目录：$TARGET_DIR"
echo ""

echo "[信息] 清理目标目录资源文件..."
cd "$TARGET_DIR"
rm -rf core video gui utils config hdc scripts
rm -f main.py ohscrcpy_server ohscrcpy_server.cfg
rm -rf HUAWEI

rm -f OHScrcpy.spec
rm -f fetch_server_logs.sh fetch_server_logs.bat
rm -f delete_server_logs.sh delete_server_logs.bat
rm -f fetch_and_delete_server_logs.sh fetch_and_delete_server_logs.bat
cd "$SCRIPT_DIR"
echo ""

echo "[信息] 清理构建临时文件..."
rm -rf build/
rm -rf dist/
rm -rf __pycache__/
echo ""

echo -e "\033[32m****************************\033[0m"
echo -e "\033[32m[完成] 资源清理完成！\033[0m"
echo -e "\033[32m****************************\033[0m"
echo ""

read -p "按任意键继续..."