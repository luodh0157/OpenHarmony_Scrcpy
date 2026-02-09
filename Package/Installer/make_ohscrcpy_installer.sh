#!/usr/bin/env bash
# OpenHarmony OHScrcpy 安装程序制作脚本

echo "================================================================"
echo "    OpenHarmony OHScrcpy 安装程序制作脚本（Linux/macOS平台）    "
echo "================================================================"

VERSION="v1.5.0"
OS="$(uname -s)"
case "${OS}" in
    Linux*)     OS_TYPE="Linux";;
    Darwin*)    OS_TYPE="macOS";;
    *)          OS_TYPE="UNKNOWN"
esac

echo "[信息] 检测到操作系统: ${OS_TYPE}"

echo "检查依赖..."
DIST_DIR="dist/OHScrcpy"
if [ ! -d "$DIST_DIR" ]; then
    echo "错误: 目录不存在: $DIST_DIR"
    read -p "按任意键继续..."
    exit 1
fi

if ! command -v zip > /dev/null 2>&1; then
    echo "未找到zip命令，无法打包"
    read -p "按任意键继续..."
    exit 1
fi

if [ ! -f "install_ohscrcpy.sh" ]; then
    echo "install_ohscrcpy.sh 文件不存在，无法打包"
    read -p "按任意键继续..."
    exit 1
fi

if [ ! -f "uninstall_ohscrcpy.sh" ]; then
    echo "uninstall_ohscrcpy.sh 文件不存在，无法打包"
    read -p "按任意键继续..."
    exit 1
fi
echo "检查依赖完成"

echo "开始打包..."
OUTPUT_DIR="output/${OS_TYPE}"
cp install_ohscrcpy.sh "${DIST_DIR}"
cp uninstall_ohscrcpy.sh "${DIST_DIR}"

cd "${DIST_DIR}"
zip -r -q -9 ../../${OUTPUT_DIR}/OHScrcpy_Setup_${OS_TYPE}_${VERSION}.zip ./*
cd -
echo "打包完成"

# 验证打包结果
echo "验证打包结果..."
if [ ! -f "${OUTPUT_DIR}/OHScrcpy_Setup_${OS_TYPE}_${VERSION}.zip" ]; then
    echo "错误: 打包失败，未生成压缩包文件"
    read -p "按任意键继续..."
    exit 1
fi
echo "验证打包结果完成"

echo "[信息] 生成文件哈希值..."
mkdir -p "output/${OS_TYPE}"

EXECUTABLE_NAME="OHScrcpy"
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
HASH_FILE="output/${OS_TYPE}/OHScrcpy_Setup_${OS_TYPE}_hash.txt"
if generate_hash "dist/OHScrcpy/${EXECUTABLE_NAME}" "${HASH_FILE}"; then
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
echo "============================================="
echo "OpenHarmony OHScrcpy 安装程序制作完成！      "
echo "============================================="
echo ""
read -p "按任意键继续..."