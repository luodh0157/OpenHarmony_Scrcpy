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
设备控制面板
"""

import tkinter as tk
from typing import Dict, Callable, Optional


class ControlPanel:
    """设备控制面板"""
    
    def __init__(self, parent: tk.Widget, callbacks: Dict[str, Callable[[], None]]) -> None:
        self.parent: tk.Widget = parent
        self.callbacks: Dict[str, Callable[[], None]] = callbacks
        
        self.frame: Optional[tk.LabelFrame] = None
        
        self._create_panel()
    
    def _create_panel(self) -> None:
        frame = tk.LabelFrame(self.parent, text="设备控制", font=("Microsoft YaHei", 10))
        frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        controls = [
            ("电源", self.callbacks.get('power', lambda: None), "#e74c3c"),
            ("主页", self.callbacks.get('home', lambda: None), "#2ecc71"),
            ("返回", self.callbacks.get('back', lambda: None), "#3498db"),
            ("解锁", self.callbacks.get('unlock', lambda: None), "#3498db"),
            ("音量+", self.callbacks.get('volume_up', lambda: None), "#9b59b6"),
            ("音量-", self.callbacks.get('volume_down', lambda: None), "#9b59b6"),
        ]
        
        for i, (text, command, color) in enumerate(controls):
            btn = tk.Button(frame, text=text, command=command, bg=color, fg="white", height=2, width=8)
            row, col = divmod(i, 2)
            btn.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
        
        for i in range(2):
            frame.grid_columnconfigure(i, weight=1)
        
        self.frame = frame
    
    def get_frame(self) -> tk.LabelFrame:
        """获取面板frame"""
        return self.frame


class InfoPanel:
    """信息面板"""
    
    def __init__(self, parent: tk.Widget) -> None:
        self.parent: tk.Widget = parent
        self.frame: Optional[tk.LabelFrame] = None
        
        self._create_panel()
    
    def _create_panel(self) -> None:
        frame = tk.LabelFrame(self.parent, text="操作说明", font=("Microsoft YaHei", 10))
        frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        instructions = """
            在视频区域：
            • 点击 → 设备点击
            • 拖动 → 设备滑动

            快捷键：
            • F5：刷新设备列表
            • F6：截图
            • F8：显示调试信息
            • F9：强制垃圾回收

            注意：
            1. 确保设备已连接并启用USB调试
            2. 首次连接可能需要授权
            3. 确保HDC工具可用"""
        
        tk.Label(
            frame, 
            text=instructions, 
            justify=tk.LEFT, 
            padx=10,
            pady=10, 
            font=("Microsoft YaHei", 9)
        ).pack()
        
        self.frame = frame
    
    def get_frame(self) -> tk.LabelFrame:
        """获取面板frame"""
        return self.frame


__all__ = ["ControlPanel", "InfoPanel"]