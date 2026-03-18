#!/bin/bash

export TERM=xterm-256color
clear

echo -e "\033[32m===============================================================\033[0m"
echo -e "\033[32m     OpenHarmony OHScrcpy 自动化构建脚本（Linux/macOS平台）    \033[0m"
echo -e "\033[32m===============================================================\033[0m"
echo ""

OS="$(uname -s)"
case "${OS}" in
    Linux*)
        OS_TYPE="Linux"
        OS_NAME="Linux"
        ;;
    Darwin*)
        OS_TYPE="macOS"
        OS_NAME="Darwin"
        ;;
    *)
        OS_TYPE="UNKNOWN"
        OS_NAME="${OS}"
esac

ARCH="$(uname -m)"
case "${ARCH}" in
    x86_64 | amd64)
        echo "这是64位 x86系统（x64）"
        ARCH="x64"
        ;;
    i[3456]86 | i86pc)
        echo "这是32位 x86系统（x86）"
        ARCH="x86"
        ;;
    aarch64 | arm64)
        echo "这是64位 ARM系统（arm64）"
        ARCH="arm64"
        ;;
    armv7l | armv6l | armv7)
        echo "这是32位 ARM系统（arm）"
        ARCH="arm"
        ;;
    *)
        echo "未知架构：$ARCH"
        ;;
esac

echo "[信息] 检测到操作系统: ${OS_TYPE}, 架构：${ARCH}"

if ! command -v python3 &> /dev/null; then
    echo "-----------------------------------------"
    echo -e "\033[31m[错误] 未找到Python3，请先安装Python 3.7+\033[0m"
    echo "-----------------------------------------"
    
    if [ "${OS_TYPE}" = "macOS" ]; then
        echo "对于macOS，建议使用以下方式安装："
        echo "1. 使用 Homebrew: brew install python"
        echo "2. 从官网下载: https://www.python.org/downloads/"
    else
        echo "对于Linux，请使用系统包管理器安装："
        echo "Ubuntu/Debian: sudo apt install python3 python3-pip"
        echo "CentOS/RHEL: sudo yum install python3 python3-pip"
    fi
    
    read -p "按任意键继续..."
    exit 1
fi

if ! command -v pyinstaller &> /dev/null; then
    echo "[警告] PyInstaller未安装，正在安装..."
    
    if command -v pip3 &> /dev/null; then
        PIP_CMD="pip3"
    elif command -v pip &> /dev/null; then
        PIP_CMD="pip"
    else
        echo "-----------------------------------------"
        echo -e "\033[31m[错误] 未找到pip，请先安装pip\033[0m"
        echo "-----------------------------------------"
        read -p "按任意键继续..."
        exit 1
    fi
    
    ${PIP_CMD} install pyinstaller
    if [ $? -ne 0 ]; then
        echo "---------------------------"
        echo -e "\033[31m[错误] PyInstaller安装失败\033[0m"
        echo "---------------------------"
        read -p "按任意键继续..."
        exit 1
    fi
    echo "[成功] PyInstaller安装完成"
fi

echo "[信息] 清理历史构建文件..."
rm -rf build/
rm -rf dist/
rm -rf __pycache__/
echo "[完成] 清理完成"

echo "[信息] 检查必要文件..."
if [ ! -f "ohscrcpy_client.py" ]; then
    echo "---------------------------------------------------"
    echo -e "\033[31m[错误] 未找到 ohscrcpy_client.py，请确保该文件存在\033[0m"
    echo "---------------------------------------------------"
    read -p "按任意键继续..."
    exit 1
fi

if [ ! -f "ohscrcpy_server" ]; then
    echo "------------------------------------------------"
    echo -e "\033[33m[警告] 未找到 ohscrcpy_server，请确保该文件存在\033[0m"
    echo "------------------------------------------------"
    read -p "按任意键继续..."
    exit 1
fi

if [ ! -f "HUAWEI/ohscrcpy_server" ]; then
    echo "-------------------------------------------------------"
    echo -e "\033[33m[警告] 未找到 HUAWEI/ohscrcpy_server，请确保该文件存在\033[0m"
    echo "-------------------------------------------------------"
    read -p "按任意键继续..."
    exit 1
fi

if [ ! -f "ohscrcpy_server.cfg" ]; then
    echo "----------------------------------------------------"
    echo -e "\033[33m[警告] 未找到 ohscrcpy_server.cfg，请确保该文件存在\033[0m"
    echo "----------------------------------------------------"
    read -p "按任意键继续..."
    exit 1
fi

if [ ! -f "hdc/${OS_NAME}/${ARCH}/hdc" ]; then
    echo "----------------------------------------------------"
    echo -e "\033[33m[警告] 未找到 hdc/${OS_NAME}/${ARCH}/hdc，请确保该文件存在\033[0m"
    echo "----------------------------------------------------"
    read -p "按任意键继续..."
    exit 1
fi

if [ ! -f "hdc/${OS_NAME}/${ARCH}/libusb_shared.so" ]; then
    echo "----------------------------------------------------"
    echo -e "\033[33m[警告] 未找到 hdc/${OS_NAME}/${ARCH}/libusb_shared.so，请确保该文件存在\033[0m"
    echo "----------------------------------------------------"
    read -p "按任意键继续..."
    exit 1
fi

if [ ! -f "app.ico" ] && [ ! -f "app.icns" ]; then
    echo "----------------------------------------"
    echo -e "\033[33m[警告] 未找到图标文件 app.ico 或 app.icns\033[0m"
    echo "----------------------------------------"
    read -p "按任意键继续..."
    exit 1
fi

ICON_FILE="app.ico"
if [ "${OS_TYPE}" = "macOS" ] && [ -f "app.icns" ]; then
    ICON_FILE="app.icns"
fi
echo "[信息] 使用图标文件: ${ICON_FILE}"

echo "*****************************"
echo "[信息] 开始安装python依赖..."
echo "*****************************"

if command -v pip3 &> /dev/null; then
    PIP_CMD="pip3"
else
    PIP_CMD="pip"
fi

${PIP_CMD} install av numpy pillow psutil pyinstaller
if [ $? -ne 0 ]; then
    echo "--------------------------"
    echo -e "\033[31m[错误] 安装python依赖失败\033[0m"
    echo "--------------------------"
    read -p "按任意键继续..."
    exit 1
fi
echo "*****************************"
echo "[完成] 安装python依赖完成"
echo "*****************************"

echo "******************************"
echo "[信息] 开始PyInstaller打包..."
echo "******************************"

PYINSTALLER_ARGS="--name \"OHScrcpy\" --noconfirm --clean --onefile"

if [ -f "ohscrcpy_server" ]; then
    PYINSTALLER_ARGS="${PYINSTALLER_ARGS} --add-data \"ohscrcpy_server:.\""
fi

if [ -f "ohscrcpy_server.cfg" ]; then
    PYINSTALLER_ARGS="${PYINSTALLER_ARGS} --add-data \"ohscrcpy_server.cfg:.\""
fi

if [ -f "HUAWEI/ohscrcpy_server" ]; then
    PYINSTALLER_ARGS="${PYINSTALLER_ARGS} --add-data \"HUAWEI/ohscrcpy_server:HUAWEI\""
fi

if [ -f "hdc/${OS_NAME}/${ARCH}/hdc" ]; then
    PYINSTALLER_ARGS="${PYINSTALLER_ARGS} --add-data \"hdc/${OS_NAME}/${ARCH}/hdc:HUAWEI\""
fi

if [ -f "hdc/${OS_NAME}/${ARCH}/libusb_shared.so" ]; then
    PYINSTALLER_ARGS="${PYINSTALLER_ARGS} --add-data \"hdc/${OS_NAME}/${ARCH}/libusb_shared.so:HUAWEI\""
fi

if [ -f "${ICON_FILE}" ]; then
    PYINSTALLER_ARGS="${PYINSTALLER_ARGS} --icon \"${ICON_FILE}\""
fi

if [ "${OS_TYPE}" = "macOS" ]; then
    PYINSTALLER_ARGS="${PYINSTALLER_ARGS} --osx-bundle-identifier \"com.openharmony.ohscrcpy\""
fi

echo "执行命令: pyinstaller ohscrcpy_client.py ${PYINSTALLER_ARGS}"
eval "pyinstaller ohscrcpy_client.py ${PYINSTALLER_ARGS}"

if [ $? -ne 0 ]; then
    echo "---------------------------"
    echo -e "\033[31m[错误] PyInstaller打包失败\033[0m"
    echo "---------------------------"
    read -p "按任意键继续..."
    exit 1
fi
echo "****************************"
echo "[完成] PyInstaller打包完成"
echo "****************************"

EXECUTABLE_NAME="OHScrcpy"
echo "[信息] 验证打包结果..."
if [ ! -f "dist/${EXECUTABLE_NAME}" ]; then
    echo "---------------------------"
    echo -e "\033[31m[错误] 未生成 ${EXECUTABLE_NAME} 可执行文件\033[0m"
    echo "---------------------------"
    read -p "按任意键继续..."
    exit 1
fi
chmod +x "dist/${EXECUTABLE_NAME}"

echo "**********************"
echo "[完成] 打包验证通过！"
echo "**********************"
echo "生成的文件："
ls -la "dist/"

echo "[信息] 生成文件哈希值..."
mkdir -p "output/${OS_TYPE}"
cp "dist/${EXECUTABLE_NAME}" "output/${OS_TYPE}" 2>/dev/null

generate_hash() {
    local file="$1"
    local output_file="$2"
    
    echo "文件哈希值：" > "${output_file}"
    echo "=================================================================" >> "${output_file}"
    
    if [ "${OS_TYPE}" = "macOS" ]; then
        if command -v md5 &> /dev/null; then
            echo "${EXECUTABLE_NAME} MD5" >> "${output_file}"
            md5 "${file}" | awk '{print $4}' >> "${output_file}"
            echo "" >> "${output_file}"
        fi
        
        if command -v shasum &> /dev/null; then
            echo "${EXECUTABLE_NAME} SHA256" >> "${output_file}"
            shasum -a 256 "${file}" | awk '{print $1}' >> "${output_file}"
        fi
    else
        if command -v md5sum &> /dev/null; then
            echo "${EXECUTABLE_NAME} MD5" >> "${output_file}"
            md5sum "${file}" | awk '{print $1}' >> "${output_file}"
            echo "" >> "${output_file}"
        fi
        
        if command -v sha256sum &> /dev/null; then
            echo "${EXECUTABLE_NAME} SHA256" >> "${output_file}"
            sha256sum "${file}" | awk '{print $1}' >> "${output_file}"
        fi
    fi
    
    echo "=================================================================" >> "${output_file}"
}

# 生成哈希文件
HASH_FILE="output/${OS_TYPE}/OHScrcpy_hash.txt"
if generate_hash "dist/${EXECUTABLE_NAME}" "${HASH_FILE}"; then
    echo "[完成] 哈希文件已生成：${HASH_FILE}"
    echo ""
    echo "生成的哈希值："
    cat "${HASH_FILE}"
else
    echo "[警告] 无法生成哈希文件（缺少哈希工具）"
    if [ "${OS_TYPE}" = "macOS" ]; then
        echo "对于macOS，可以安装GNU工具：brew install md5sha1sum"
    fi
fi

echo ""
echo -e "\033[32m=============================================\033[0m"
echo -e "\033[32mOpenHarmony OHScrcpy 自动化打包完成！\033[0m"
echo -e "\033[32m=============================================\033[0m"
echo "操作系统: ${OS_TYPE}"
echo "输出目录: output/${OS_TYPE}/"
echo "生成文件: ${EXECUTABLE_NAME}"
echo ""
read -p "按任意键继续..."