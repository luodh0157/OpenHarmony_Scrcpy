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
#                 OpenHarmony OHScrcpy 总一键打包脚本 (Linux/Mac)
# ================================================================================
#
# 功能：提供交互式菜单，支持多种打包选项
#
# 菜单选项：
#   1. Executer (单文件可执行程序)
#   2. Installer (安装包)
#   3. 批量打包两种方式
#   4. 清理所有临时文件
#   5. 退出
#
# 使用方法：
#   cd Package
#   ./build.sh
#
# ================================================================================

export TERM=xterm-256color
export NO_PAUSE=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cleanup_all() {
    echo ""
    echo "======================================="
    echo -e "\033[33m正在清理所有临时文件...\033[0m"
    echo "======================================="
    echo ""
    
    cd "$SCRIPT_DIR/Executer"
    if [ -f "clear_for_executer.sh" ]; then
        chmod +x clear_for_executer.sh
        ./clear_for_executer.sh
        echo "***************************************"
        echo "[完成] Executer目录清理完成"
        echo "***************************************"
    else
        echo --------------------------------------------------------------
        echo -e "\033[33m[警告] 未找到 clear_for_executer.sh，请手动清理！\033[0m"
        echo --------------------------------------------------------------
    fi
    cd "$SCRIPT_DIR"
    
    cd "$SCRIPT_DIR/Installer"
    if [ -f "clear_for_installer.sh" ]; then
        chmod +x clear_for_installer.sh
        ./clear_for_installer.sh
        echo "***************************************"
        echo "[完成] Installer目录清理完成"
        echo "***************************************"
    else
        echo ---------------------------------------------------------------
        echo -e "\033[33m[警告] 未找到 clear_for_installer.sh，请手动清理！\033[0m"
        echo ---------------------------------------------------------------
    fi
    cd "$SCRIPT_DIR"
    
    echo "======================================="
    echo -e "\033[32m所有临时文件已清理完成！\033[0m"
    echo "======================================="
}

batch_build() {
    echo ""
    echo -e "\033[33m=======================================\033[0m"
    echo -e "\033[33m批量打包两种方式\033[0m"
    echo -e "\033[33m=======================================\033[0m"
    echo ""
    
    SUCCESS_COUNT=0
    FAIL_COUNT=0
    
    echo "+++++++++++++++++++++++++++++++++++++++"
    echo -e "\033[32m[1/2] 开始Executer打包...\033[0m"
    echo "+++++++++++++++++++++++++++++++++++++++"
    echo ""
    if [ -f "$SCRIPT_DIR/build_executer.sh" ]; then
        chmod +x "$SCRIPT_DIR/build_executer.sh"
        "$SCRIPT_DIR/build_executer.sh"
        if [ $? -eq 0 ]; then
            SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
            echo "***************************************"
            echo -e "\033[32mExecuter打包成功！\033[0m"
            echo "***************************************"
        else
            FAIL_COUNT=$((FAIL_COUNT + 1))
            echo ---------------------------------------
            echo -e "\033[31mExecuter打包失败！\033[0m"
            echo ---------------------------------------
        fi
    else
        echo ----------------------------------------------
        echo -e "\033[31m[错误] 未找到 build_executer.sh\033[0m"
        echo ----------------------------------------------
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
    
    echo ""
    echo "+++++++++++++++++++++++++++++++++++++++"
    echo -e "\033[32m[2/2] 开始Installer打包...\033[0m"
    echo "+++++++++++++++++++++++++++++++++++++++"
    echo ""
    if [ -f "$SCRIPT_DIR/build_installer.sh" ]; then
        chmod +x "$SCRIPT_DIR/build_installer.sh"
        "$SCRIPT_DIR/build_installer.sh"
        if [ $? -eq 0 ]; then
            SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
            echo "***************************************"
            echo -e "\033[32mInstaller打包成功！\033[0m"
            echo "***************************************"
        else
            FAIL_COUNT=$((FAIL_COUNT + 1))
            echo ---------------------------------------
            echo -e "\033[31mInstaller打包失败！\033[0m"
            echo ---------------------------------------
        fi
    else
        echo -------------------------------------------------
        echo -e "\033[31m[错误] 未找到 build_installer.sh\033[0m"
        echo -------------------------------------------------
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
    
    echo ""
    echo -e "\033[32m=======================================\033[0m"
    echo -e "\033[32m批量打包完成！\033[0m"
    echo -e "\033[32m=======================================\033[0m"
    echo ""
    echo "成功: $SUCCESS_COUNT 个"
    echo "失败: $FAIL_COUNT 个"
    echo ""
    
    if [ $FAIL_COUNT -eq 0 ]; then
        echo -e "\033[32m全部打包成功！\033[0m"
    else
        echo -e "\033[33m部分打包失败，请检查错误信息\033[0m"
    fi
    echo ""
}

show_menu() {
    clear
    echo -e "\033[32m=========================================\033[0m"
    echo -e "\033[32m    OpenHarmony OHScrcpy 一键打包工具    \033[0m"
    echo -e "\033[32m=========================================\033[0m"
    echo ""
    echo "请选择打包方式："
    echo ""
    echo "  1. Executer (单文件可执行程序)"
    echo "  2. Installer (安装包)"
    echo "  3. 批量打包两种方式"
    echo "  4. 清理所有临时文件"
    echo "  5. 退出"
    echo ""
}

main() {
    while true; do
        show_menu
        read -p "请输入选项 [1-5]: " choice
        
        case "$choice" in
            1)
                echo ""
                echo "======================================="
                echo -e "\033[33m开始Executer打包...\033[0m"
                echo "======================================="
                echo ""
                if [ -f "$SCRIPT_DIR/build_executer.sh" ]; then
                    chmod +x "$SCRIPT_DIR/build_executer.sh"
                    "$SCRIPT_DIR/build_executer.sh"
                else
                    echo ---------------------------------------------
                    echo -e "\033[31m[错误] 未找到 build_executer.sh\033[0m"
                    echo ---------------------------------------------
                fi
                echo ""
                read -p "按回车键继续..."
                ;;
            2)
                echo ""
                echo "======================================="
                echo -e "\033[33m开始Installer打包...\033[0m"
                echo "======================================="
                echo ""
                if [ -f "$SCRIPT_DIR/build_installer.sh" ]; then
                    chmod +x "$SCRIPT_DIR/build_installer.sh"
                    "$SCRIPT_DIR/build_installer.sh"
                else
                    echo ----------------------------------------------
                    echo -e "\033[31m[错误] 未找到 build_installer.sh\033[0m"
                    echo ----------------------------------------------
                fi
                echo ""
                read -p "按回车键继续..."
                ;;
            3)
                batch_build
                read -p "按回车键继续..."
                ;;
            4)
                cleanup_all
                read -p "按回车键继续..."
                ;;
            5)
                echo ""
                echo "======================================="
                echo -e "\033[32m退出打包工具！\033[0m"
                echo "======================================="
                exit 0
                ;;
            *)
                echo ""
                echo "======================================="
                echo -e "\033[31m无效选项，请重新选择！\033[0m"
                echo "======================================="
                sleep 1
                ;;
        esac
    done
}

main