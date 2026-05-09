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
#               OpenHarmony OHScrcpy 服务端日志删除脚本 (Linux/Mac)
# ================================================================================
#
# 功能：从设备删除服务端日志文件
#
# 参数：PID - 服务端进程PID（可选）
#       - 指定PID：只删除该PID对应的日志文件（精确操作，无需确认）
#       - 不指定PID：删除所有服务端日志文件（批量操作，需要确认）
#
# PID获取方式：
#   - 从客户端日志中获取（客户端启动服务端后会自动输出PID）
#   - 客户端日志示例：[INFO][服务端管理器] 服务正在运行，PID: 12345
#   - 也可通过 hdc shell pgrep -f ohscrcpy_server 查询
#
# 日志文件格式：
#   - 文件命名：server_PID_YYYYMMDD_HHMMSS.log
#   - 示例：server_12345_20260506_143000.log
#   - 存储位置：设备上 /data/local/tmp/
#
# 使用示例：
#   ./delete_server_logs.sh 12345       # 删除PID=12345的日志文件（无需确认）
#   ./delete_server_logs.sh            # 删除所有服务端日志文件（需要确认）
#
# 注意事项：
#   - 删除前请确保服务端进程已停止
#   - 精确删除（指定PID）直接执行，无需确认
#   - 批量删除（不指定PID）需要用户确认，避免误操作
#   - 多设备连接时会提示选择设备
#
# ================================================================================

export TERM=xterm-256color
clear

echo -e "\033[32m=================================================================\033[0m"
echo -e "\033[32m     OpenHarmony OHScrcpy 服务端日志删除脚本（Linux/Mac平台）    \033[0m"
echo -e "\033[32m=================================================================\033[0m"
echo ""

SERVER_LOG_DIR="/data/local/tmp"

# 获取脚本所在目录（脚本在根目录下）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INTERNAL_DIR="$SCRIPT_DIR/_internal"

# HDC工具路径（hdc在 _internal/ 目录下，脚本在根目录下）
HDC_PATH="$INTERNAL_DIR/hdc"

# 选择hdc工具
select_hdc_tool() {
    # 优先使用_internal目录下的hdc
    if [ -f "$HDC_PATH" ] && [ -x "$HDC_PATH" ]; then
        echo "$HDC_PATH"
        return 0
    fi
    
    # 否则使用系统PATH中的hdc
    if command -v hdc &> /dev/null; then
        echo "hdc"
        return 0
    fi
    
    echo ""
    return 1
}

HDC_CMD=$(select_hdc_tool)

if [ -z "$HDC_CMD" ]; then
    echo -e "\033[31m-----------------------------------------\033[0m"
    echo -e "\033[31m[错误] hdc工具未找到\033[0m"
    echo -e "\033[31m-----------------------------------------\033[0m"
    echo "请确保以下条件之一满足:"
    echo "  1. _internal目录下存在hdc工具: $HDC_PATH"
    echo "  2. 系统PATH中存在hdc命令"
    read -p "按任意键继续..."
    exit 1
fi

# 检查设备连接并选择设备
echo "[信息] 查询设备列表..."
DEVICE_LIST=$($HDC_CMD list targets 2>/dev/null | grep -v "^$")
DEVICE_COUNT=$(echo "$DEVICE_LIST" | wc -l | tr -d ' ')

if [ "$DEVICE_COUNT" -eq 0 ]; then
    echo -e "\033[31m-----------------------------------------\033[0m"
    echo -e "\033[31m[错误] 未连接设备\033[0m"
    echo -e "\033[31m-----------------------------------------\033[0m"
    read -p "按任意键继续..."
    exit 1
fi

if [ "$DEVICE_COUNT" -eq 1 ]; then
    SELECTED_DEVICE=$(echo "$DEVICE_LIST" | head -1)
    echo "[信息] 自动选择设备：$SELECTED_DEVICE"
else
    echo -e "\033[33m-----------------------------------------\033[0m"
    echo -e "\033[33m[信息] 检测到多个设备连接（共$DEVICE_COUNT个）\033[0m"
    echo -e "\033[33m-----------------------------------------\033[0m"
    echo "请选择设备："
    
    # 显示设备列表（带编号）
    idx=1
    while IFS= read -r device; do
        echo "  $idx. $device"
        eval "DEVICE_$idx=\"$device\""
        idx=$((idx + 1))
    done <<< "$DEVICE_LIST"
    
    echo ""
    read -p "请输入设备编号(1-$DEVICE_COUNT): " DEVICE_CHOICE
    
    if [ "$DEVICE_CHOICE" -lt 1 ] || [ "$DEVICE_CHOICE" -gt "$DEVICE_COUNT" ]; then
        echo -e "\033[31m-----------------------------------------\033[0m"
        echo -e "\033[31m[错误] 无效的设备编号\033[0m"
        echo -e "\033[31m-----------------------------------------\033[0m"
        read -p "按任意键继续..."
        exit 1
    fi
    
    eval "SELECTED_DEVICE=\$DEVICE_$DEVICE_CHOICE"
    echo "[信息] 已选择设备：$SELECTED_DEVICE"
fi

# 获取PID参数
PID="$1"

if [ -n "$PID" ]; then
    echo "[信息] 删除PID=$PID的日志文件..."
    $HDC_CMD -t "$SELECTED_DEVICE" shell "rm -f $SERVER_LOG_DIR/server_${PID}_*.log"
    echo -e "\033[32m****************************\033[0m"
    echo -e "\033[32m[完成] 已删除日志文件\033[0m"
    echo -e "\033[32m****************************\033[0m"
else
    echo -e "\033[33m-----------------------------------------\033[0m"
    echo -e "\033[33m[警告] 将删除设备上所有服务端日志文件！\033[0m"
    echo -e "\033[33m-----------------------------------------\033[0m"
    echo "日志位置: $SERVER_LOG_DIR"
    echo "请确保服务端进程已停止"
    echo ""
    read -p "继续吗？(y/n): " CONFIRM
    
    if [ "$CONFIRM" = "y" ] || [ "$CONFIRM" = "Y" ]; then
        $HDC_CMD -t "$SELECTED_DEVICE" shell "rm -f $SERVER_LOG_DIR/server_*.log"
        echo -e "\033[32m****************************\033[0m"
        echo -e "\033[32m[完成] 所有日志文件已删除\033[0m"
        echo -e "\033[32m****************************\033[0m"
    else
        echo "[信息] 操作已取消"
    fi
fi

echo ""
read -p "按任意键继续..."
