#!/bin/bash
# ================================================
#       OpenHarmony OHScrcpy Linux 安装脚本
# ================================================
# 使用方法: ./install_ohscrcpy.sh [安装路径]

set -e

APP_NAME="OHScrcpy"
CMD_LINK_NAME="ohscrcpy"
UNINSTALL_CMD_NAME="ohscrcpy-uninstall"
VERSION="1.0.0"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_info() {
    echo -e "${GREEN}[信息]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[警告]${NC} $1"
}

print_error() {
    echo -e "${RED}[错误]${NC} $1"
}

show_help() {
    cat << EOF
${APP_NAME} 安装脚本 v${VERSION}

使用方法: $0 [选项] [安装路径]

选项:
  -h, --help          显示此帮助信息
  -p, --path PATH     指定安装路径
  --no-link           不创建命令链接
  --no-desktop        不创建桌面快捷方式
  --system            安装到系统目录 (需要root权限)

示例:
  $0                     # 交互式安装
  $0 ~/apps/ohscrcpy     # 安装到指定目录
  $0 --system            # 系统级安装
  $0 --path /opt/ohscrcpy --no-desktop
EOF
}

# 解析命令行参数
parse_arguments() {
    INSTALL_DIR=""
    CREATE_LINK=true
    CREATE_DESKTOP=true
    INSTALL_MODE="user"
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -p|--path)
                INSTALL_DIR="$2"
                shift 2
                ;;
            --no-link)
                CREATE_LINK=false
                shift
                ;;
            --no-desktop)
                CREATE_DESKTOP=false
                shift
                ;;
            --system)
                INSTALL_MODE="system"
                shift
                ;;
            *)
                # 如果参数不是选项，则视为安装路径
                if [[ "$1" != -* ]]; then
                    INSTALL_DIR="$1"
                else
                    print_error "未知选项: $1"
                    show_help
                    exit 1
                fi
                shift
                ;;
        esac
    done
    
    # 设置默认安装路径
    if [ -z "$INSTALL_DIR" ]; then
        if [ "$INSTALL_MODE" = "system" ]; then
            DEFAULT_DIR="/opt/ohscrcpy"
        else
            DEFAULT_DIR="$HOME/.local/share/ohscrcpy"
        fi
        INSTALL_DIR="$DEFAULT_DIR"
    fi
}

# 检查依赖
check_dependencies() {
    print_info "检查系统依赖..."
    
    # 检查是否有桌面环境
    if [ -z "$XDG_CURRENT_DESKTOP" ] && [ -z "$DESKTOP_SESSION" ]; then
        print_warn "未检测到桌面环境，跳过桌面快捷方式创建"
        CREATE_DESKTOP=false
    fi
    
    # 检查是否有必要的工具
    if ! command -v unzip > /dev/null 2>&1; then
        print_warn "未找到unzip命令，某些功能可能受限"
    fi
    
    return 0
}

# 验证安装目录
validate_install_dir() {
    local dir="$1"
    
    # 展开路径中的 ~
    dir="${dir/#\~/$HOME}"
    
    # 检查是否为绝对路径
    if [[ "$dir" != /* ]]; then
        print_error "安装路径必须是绝对路径: $dir"
        return 1
    fi
    
    # 检查父目录是否可写
    local parent_dir=$(dirname "$dir")
    if [ ! -w "$parent_dir" ] && [ ! -w "$(dirname "$parent_dir")" ]; then
        print_error "无法在 '$parent_dir' 下创建目录（无写入权限）"
        
        if [ "$INSTALL_MODE" = "user" ]; then
            print_info "建议使用用户目录，例如: $HOME/.local/share/ohscrcpy"
        fi
        return 1
    fi
    
    echo "$dir"
}

# 交互式选择安装目录
choose_install_dir_interactive() {
    local default_dir="$1"
    local user_dir
    
    read -p "请选择安装目录:
  1. 用户目录 ($HOME/.local/share/ohscrcpy)
  2. 系统目录 (/opt/ohscrcpy) - 需要root权限
  3. 自定义路径
  请选择 [1/2/3] (默认: 1): " choice
    case "$choice" in
        1)
            user_dir="$HOME/.local/share/ohscrcpy"
            ;;
        2)
            if [ "$EUID" -ne 0 ]; then
                print_warn "需要root权限安装到系统目录"
                read -p "是否使用sudo? [y/N]: " -n 1 -r
                echo
                if [[ $REPLY =~ ^[Yy]$ ]]; then
                    INSTALL_MODE="system"
                    user_dir="/opt/ohscrcpy"
                else
                    user_dir="$HOME/.local/share/ohscrcpy"
                fi
            else
                INSTALL_MODE="system"
                user_dir="/opt/ohscrcpy"
            fi
            ;;
        3)
            read -p "请输入自定义路径: " custom_dir
            user_dir="$custom_dir"
            ;;
        *)
            user_dir="$default_dir"
            ;;
    esac
    
    echo "$user_dir"
}

# 复制文件
copy_files() {
    local src_dir="$1"
    local dest_dir="$2"
    
    #print_info "复制文件从 $src_dir 到 $dest_dir"
    
    # 创建目标目录
    mkdir -p "$dest_dir"
    
    # 复制所有文件
    cd $src_dir
    cp -rf $src_dir/* "$dest_dir/" >&2>/dev/null
    cd -
    
    # 设置可执行权限
    if [ -f "$dest_dir/$APP_NAME" ]; then
        chmod +x "$dest_dir/$APP_NAME"
    fi
    
    print_info "文件复制完成"
}

# 创建命令链接
create_command_link() {
    local install_dir="$1"
    local app_path="$install_dir/$APP_NAME"
    
    if [ "$CREATE_LINK" = false ]; then
        return
    fi
    
    if [ "$INSTALL_MODE" = "system" ]; then
        # 系统级链接
        if [ "$EUID" -eq 0 ]; then
            local link_path="/usr/local/bin/$CMD_LINK_NAME"
            ln -sf "$app_path" "$link_path"
            chmod +x "$link_path"
            print_info "创建系统命令链接: $link_path"
        else
            print_warn "需要root权限创建系统命令链接，跳过此步骤"
        fi
    else
        # 用户级链接
        local link_dir="$HOME/.local/bin"
        local link_path="$link_dir/$CMD_LINK_NAME"
        
        mkdir -p "$link_dir"
        ln -sf "$app_path" "$link_path"
        chmod +x "$link_path"
        print_info "创建用户命令链接: $link_path"
        
        # 检查PATH
        if [[ ":$PATH:" != *":$link_dir:"* ]]; then
            print_warn "$link_dir 不在PATH环境变量中"
            print_info "请添加以下行到 ~/.bashrc, ~/.zshrc 或 ~/.profile:"
            echo "    export PATH=\"\$HOME/.local/bin:\$PATH\""
        fi
    fi
}

# 创建桌面快捷方式
create_desktop_shortcut() {
    local install_dir="$1"
    
    if [ "$CREATE_DESKTOP" = false ]; then
        return
    fi
    
    if [ ! -d "$HOME/Desktop" ] && [ ! -d "$HOME/桌面" ]; then
        print_warn "未找到桌面目录，跳过创建桌面快捷方式"
        return
    fi
    
    local desktop_file="$HOME/.local/share/applications/ohscrcpy.desktop"
    mkdir -p "$(dirname "$desktop_file")"
    
    cat > "$desktop_file" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=$APP_NAME
Comment=OpenHarmony Screen Copy Tool
Exec=$install_dir/$APP_NAME
Icon=$install_dir/app.ico
Terminal=false
Categories=Utility;
EOF
    
    chmod +x "$desktop_file"
    print_info "创建桌面快捷方式: $desktop_file"
    
    # 复制到桌面（如果存在）
    if [ -d "$HOME/Desktop" ]; then
        cp "$desktop_file" "$HOME/Desktop/"
    elif [ -d "$HOME/桌面" ]; then
        cp "$desktop_file" "$HOME/桌面/"
    fi
}

# 添加环境变量配置
add_environment_config() {
    local install_dir="$1"
    local bashrc_file="$HOME/.bashrc"
    
    print_info "正在配置环境变量到 $bashrc_file"
    
    # 备份原文件
    if [ -f "$bashrc_file" ]; then
        cp "$bashrc_file" "$bashrc_file.bak.$(date +%s)"
    fi
    
    # 添加环境变量配置（带有标记便于卸载时识别）
    cat >> "$bashrc_file" << EOF

# OHScrcpy Environment Configuration - DO NOT EDIT THIS BLOCK MANUALLY
export OHSCRCPY_HOME="$install_dir"
export PATH="\$OHSCRCPY_HOME:\$PATH"
alias ohscrcpy="\$OHSCRCPY_HOME/$APP_NAME"
# END OHScrcpy Environment Configuration

EOF
    
    print_info "环境变量已配置到 $bashrc_file"
    print_info "请运行 'source $bashrc_file' 或重新打开终端使配置生效"
}

create_uninstall_link() {
    local install_dir="$1"
    local uninstall_script="$install_dir/uninstall_ohscrcpy.sh"
    
    # 创建卸载命令软链接
    if [ "$INSTALL_MODE" = "system" ] && [ "$EUID" -eq 0 ]; then
        ln -sf "$uninstall_script" "/usr/local/bin/$UNINSTALL_CMD_NAME"
        echo "创建系统卸载命令: $UNINSTALL_CMD_NAME"
    else
        mkdir -p "$HOME/.local/bin"
        ln -sf "$uninstall_script" "$HOME/.local/bin/$UNINSTALL_CMD_NAME"
        echo "创建用户卸载命令: $UNINSTALL_CMD_NAME"
    fi
}

# 主安装函数
perform_installation() {
    print_info "开始安装 OpenHarmony $APP_NAME..."
    
    # 获取安装目录
    INSTALL_DIR=$(choose_install_dir_interactive "$DEFAULT_DIR")
    
    # 验证并规范化路径
    INSTALL_DIR=$(validate_install_dir "$INSTALL_DIR")
    if [ $? -ne 0 ]; then
        exit 1
    fi
    
    # 显示安装摘要
    echo "+++++++++++++++++++++++++++++++++++++++++++++++++++"
    echo "  应用名称: $APP_NAME"
    echo "  安装目录: $INSTALL_DIR"
    echo "  安装模式: $INSTALL_MODE"
    echo "  创建命令链接: $CREATE_LINK"
    echo "  创建桌面快捷方式: $CREATE_DESKTOP"
    echo "+++++++++++++++++++++++++++++++++++++++++++++++++++"
    
    read -p "确认安装? [Y/n]: " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        print_info "安装已取消"
        exit 0
    fi
    
    # 复制文件
    copy_files "$SCRIPT_DIR" "$INSTALL_DIR"
    
    # 创建命令软链接
    create_command_link "$INSTALL_DIR"
    
    # 创建桌面快捷方式
    create_desktop_shortcut "$INSTALL_DIR"
    
    # 创建卸载软链接
    create_uninstall_link "$INSTALL_DIR"
    
    # 添加环境配置
    add_environment_config "$INSTALL_DIR"
    
    # 安装完成
    echo ""
    echo "================================"
    echo "OpenHarmony $APP_NAME 安装完成！"
    echo "================================"
    echo "安装目录: $INSTALL_DIR"
    echo "启动方式:"
    echo "  1. 直接运行: $INSTALL_DIR/$APP_NAME"
    
    if [ "$CREATE_LINK" = true ]; then
        if [ "$INSTALL_MODE" = "system" ]; then
            echo "  2. 系统命令: $CMD_LINK_NAME (需要重新登录或运行 'hash -r')"
        else
            echo "  2. 用户命令: $CMD_LINK_NAME"
        fi
    fi
    
    if [ "$CREATE_DESKTOP" = true ]; then
        echo "  3. 桌面快捷方式"
    fi
    echo "卸载方法: 执行命令 $UNINSTALL_CMD_NAME"
}

# 主程序
main() {
    echo "================================================"
    echo "      OpenHarmony $APP_NAME Linux 安装工具      "
    echo "================================================"
    parse_arguments "$@"
    check_dependencies
    perform_installation
}

# 运行主程序
main "$@"