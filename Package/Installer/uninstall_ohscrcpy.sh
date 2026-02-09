#!/bin/bash
# ================================================
#       OpenHarmony OHScrcpy Linux 卸载脚本
# ================================================
# 使用方法: ./uninstall_ohscrcpy.sh

APP_NAME="OHScrcpy"
CMD_LINK_NAME="ohscrcpy"
UNINSTALL_CMD_NAME="ohscrcpy-uninstall"
VERSION="1.0.0"

echo "================================================"
echo "      OpenHarmony $APP_NAME Linux 卸载工具      "
echo "================================================"

remove_environment_config() {
    local bashrc_file="$HOME/.bashrc"
    
    if [ -f "$bashrc_file" ]; then
        echo "正在清理 $bashrc_file 中的环境变量..."
        
        # 创建临时文件
        local temp_file="$bashrc_file.tmp"
        
        # 使用awk精确删除OHScrcpy配置块
        awk '
            BEGIN { in_block = 0 }
            /# OHScrcpy Environment Configuration - DO NOT EDIT THIS BLOCK MANUALLY/ { in_block = 1 }
            !in_block { print }
            /# END OHScrcpy Environment Configuration/ { in_block = 0 }
        ' "$bashrc_file" > "$temp_file"
        
        # 替换原文件
        mv "$temp_file" "$bashrc_file"
        
        echo "清理环境变量配置完成"
    fi
}

# 通过which找到安装目录
if ! INSTALL_PATH=$(which "$CMD_LINK_NAME" 2>/dev/null); then
    echo "错误: 未找到 $CMD_LINK_NAME，可能未安装或不在PATH中"
    exit 1
fi

# 解析真实路径
INSTALL_DIR=$(dirname "$(readlink -f "$INSTALL_PATH")")

# 确认卸载
echo "安装目录: $INSTALL_DIR"
read -p "确认卸载? (输入 'yes' 继续): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "卸载已取消"
    exit 0
fi

echo "开始卸载..."

# 删除命令软链接
echo "删除软链接文件..."
rm -f "$INSTALL_PATH"
rm -f "$HOME/.local/bin/$CMD_LINK_NAME" 2>/dev/null
rm -f "/usr/local/bin/$CMD_LINK_NAME" 2>/dev/null
rm -f "$HOME/.local/bin/$UNINSTALL_CMD_NAME" 2>/dev/null
rm -f "/usr/local/bin/$UNINSTALL_CMD_NAME" 2>/dev/null

# 删除桌面快捷方式
echo "删除快捷方式..."
rm -f "$HOME/.local/share/applications/ohscrcpy.desktop" 2>/dev/null
rm -f "$HOME/Desktop/ohscrcpy.desktop" 2>/dev/null
rm -f "$HOME/桌面/ohscrcpy.desktop" 2>/dev/null

# 删除安装目录
echo "删除安装目录..."
if [ -d "$INSTALL_DIR" ]; then
    rm -rf "$INSTALL_DIR"
fi

# 移除环境变量配置
remove_environment_config

echo "================================"
echo "OpenHarmony $APP_NAME 卸载完成！"
echo "================================"