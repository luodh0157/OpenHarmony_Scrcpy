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
#           OpenHarmony OHScrcpy 一键打包脚本 - Executer方式 (Linux/Mac)
# ================================================================================
#
# 功能：自动完成Executer打包的所有步骤（准备→打包→清理）
#
# 流程：
#   [步骤1/5] 检查环境依赖
#   [步骤2/5] 执行prepare_for_executer.sh
#   [步骤3/5] 执行make_ohscrcpy_executer.sh
#   [步骤4/5] 显示输出结果
#   [步骤5/5] 执行clear_for_executer.sh
#
# 错误处理：失败时自动清理资源文件和构建产物
#
# 使用方法：
#   cd Package
#   ./build_executer.sh
#
# ================================================================================

export TERM=xterm-256color
export NO_PAUSE=1
clear

echo -e "\033[32m==================================================================\033[0m"
echo -e "\033[32m     OpenHarmony OHScrcpy 一键打包 - Executer方式（Linux/Mac）    \033[0m"
echo -e "\033[32m==================================================================\033[0m"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

VERSION="v2.1.0"

cleanup_on_error() {
    echo -e "\033[31m[错误] 打包失败，正在自动清理临时文件...\033[0m"
    cd "$SCRIPT_DIR/Executer"
    if [ -f "clear_for_executer.sh" ]; then
        chmod +x clear_for_executer.sh
        ./clear_for_executer.sh
    else
        echo -e "\033[33m[警告] 未找到 clear_for_executer.sh，请手动清理！\033[0m"
    fi
    cd "$SCRIPT_DIR"
    echo -e "\033[32m[完成] 自动清理完成\033[0m"
    exit 1
}

echo -e "\033[33m[步骤 1/5] 检查环境依赖...\033[0m"
echo ""

if ! command -v python3 &> /dev/null; then
    echo -e "\033[31m[错误] 未找到Python3，请先安装Python 3.7+\033[0m"
    cleanup_on_error
fi

if [ ! -f "$PROJECT_ROOT/Client/main.py" ]; then
    echo -e "\033[31m[错误] 未找到项目源文件: Client/main.py\033[0m"
    cleanup_on_error
fi

echo "[信息] Python3: $(python3 --version)"
echo "[信息] 项目根目录: $PROJECT_ROOT"
echo "[信息] 打包目录: $SCRIPT_DIR/Executer"
echo ""
echo -e "\033[32m[完成] 环境检查通过\033[0m"
echo ""

echo -e "\033[33m[步骤 2/5] 准备打包资源...\033[0m"
echo ""

cd "$SCRIPT_DIR/Executer"
if [ ! -f "prepare_for_executer.sh" ]; then
    echo -e "\033[31m[错误] 未找到 prepare_for_executer.sh\033[0m"
    cleanup_on_error
fi

chmod +x prepare_for_executer.sh
./prepare_for_executer.sh
if [ $? -ne 0 ]; then
    cleanup_on_error
fi
cd "$SCRIPT_DIR"

echo ""
echo -e "\033[32m[完成] 资源准备完成\033[0m"
echo ""

echo -e "\033[33m[步骤 3/5] 执行PyInstaller打包...\033[0m"
echo ""

cd "$SCRIPT_DIR/Executer"
if [ ! -f "make_ohscrcpy_executer.sh" ]; then
    echo -e "\033[31m[错误] 未找到 make_ohscrcpy_executer.sh\033[0m"
    cleanup_on_error
fi

chmod +x make_ohscrcpy_executer.sh
./make_ohscrcpy_executer.sh
if [ $? -ne 0 ]; then
    cleanup_on_error
fi
cd "$SCRIPT_DIR"

echo ""
echo -e "\033[32m[完成] PyInstaller打包完成\033[0m"
echo ""

echo -e "\033[33m[步骤 4/5] 显示输出结果...\033[0m"
echo ""

OS="$(uname -s)"
case "${OS}" in
    Linux*)     OS_TYPE="Linux";;
    Darwin*)    OS_TYPE="macOS";;
    *)          OS_TYPE="UNKNOWN"
esac

ARCH="$(uname -m)"
case "${ARCH}" in
    x86_64|amd64)  ARCH="x64";;
    i[3456]86)     ARCH="x86";;
    aarch64|arm64) ARCH="arm64";;
    armv7l|armv6l) ARCH="arm";;
esac

OUTPUT_DIR="$SCRIPT_DIR/Executer/output/${OS_TYPE}/${ARCH}"
echo "[信息] 输出目录: $OUTPUT_DIR"
echo ""

if [ -d "$OUTPUT_DIR" ]; then
    echo "生成的文件："
    ls -lh "$OUTPUT_DIR" | grep -E "OHScrcpy|\.zip|hash\.txt"
else
    echo -e "\033[33m[警告] 未找到输出目录\033[0m"
fi

echo ""
echo -e "\033[32m[完成] 输出结果显示完成\033[0m"
echo ""

echo -e "\033[33m[步骤 5/5] 清理临时资源文件...\033[0m"
echo ""

cd "$SCRIPT_DIR/Executer"
if [ -f "clear_for_executer.sh" ]; then
    chmod +x clear_for_executer.sh
    ./clear_for_executer.sh
else
    echo -e "\033[33m[警告] 未找到 clear_for_executer.sh，请手动清理！\033[0m"
fi
cd "$SCRIPT_DIR"

echo -e "\033[32m[完成] 清理完成\033[0m"
echo ""

echo -e "\033[32m============================================\033[0m"
echo -e "\033[32m Executer打包完成！\033[0m"
echo -e "\033[32m============================================\033[0m"
echo ""
echo "版本: $VERSION"
echo "输出目录: $OUTPUT_DIR"
echo ""
echo "使用方法："
echo "  解压 OHScrcpy_Exec_${OS_TYPE}_${ARCH}_${VERSION}.zip"
echo "  运行 OHScrcpy 开始投屏"
echo ""
echo -e "\033[32m成功完成所有步骤！\033[0m"
echo ""
exit 0