#!/usr/bin/env python

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

"""
OpenHarmony_Scrcpy 平台工具模块
"""

import platform
import subprocess
from typing import Optional

def get_default_shell_terminal() -> str:
    """获取类Linux系统默认终端"""
    system = platform.system()
    
    if system == "Darwin":  # macOS
        return "osascript"
    
    # Linux系统检测可用终端
    terminals = [
        "gnome-terminal",  # GNOME
        "konsole",         # KDE
        "terminator",      # Terminator
        "xfce4-terminal",  # XFCE
        "mate-terminal",   # MATE
        "lxterminal",      # LXDE
        "xterm"            # 最基础的X终端
    ]
    
    for term in terminals:
        if subprocess.run(["which", term], capture_output=True).returncode == 0:
            return term
    
    return "xterm"  # 默认

__all__ = ["get_default_shell_terminal"]