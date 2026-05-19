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

# OpenHarmony_Scrcpy 测试脚本 (Linux/Mac通用)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# 禁止生成Python字节码缓存，避免 __pycache__ 目录污染代码仓库
export PYTHONDONTWRITEBYTECODE=1

echo "=========================================="
echo "OpenHarmony_Scrcpy Unit Tests"
echo "=========================================="

# 检测Python命令 (Mac可能用python3或python)
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "ERROR: Python not found"
    exit 1
fi

echo "Python: $PYTHON_CMD"
$PYTHON_CMD --version

# 检查pytest是否安装
if ! $PYTHON_CMD -m pytest --version &> /dev/null; then
    echo ""
    echo "pytest not installed, installing..."
    $PYTHON_CMD -m pip install -r tests/requirements-test.txt
fi

echo ""
echo "=========================================="
echo "Running Tests..."
echo "=========================================="

$PYTHON_CMD -m pytest tests/ -v --tb=short

echo ""
echo "=========================================="
echo "Tests Complete"
echo "=========================================="

# 清理可能遗留的缓存目录（保险机制）
echo ""
echo "Cleaning up cache directories..."
find tests Client -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
rm -rf .pytest_cache 2>/dev/null || true
echo "Cleanup complete"