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

# 从 constants.py 获取版本号
# 用法: VERSION=$(./get_version.sh)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

VERSION=$(python3 -c "
import sys
sys.path.insert(0, '$PROJECT_ROOT/Client')
try:
    from core.constants import VERSION
    print(VERSION)
except Exception:
    print('v2.1.0')
" 2>/dev/null)

# 如果 python 失败，从 git tag 获取
if [ -z "$VERSION" ] || [ "$VERSION" = "v2.1.0" ]; then
    TAG=$(git describe --tags --exact-match 2>/dev/null)
    if [ -n "$TAG" ]; then
        VERSION="$TAG"
    fi
fi

# 如果还是空，使用默认值
if [ -z "$VERSION" ]; then
    VERSION="v2.1.0"
fi

echo "$VERSION"
