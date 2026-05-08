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
设备选择面板
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional, List


class DevicePanel:
    """设备选择面板"""
    
    def __init__(self, parent: tk.Widget, on_refresh: Callable[[], None], on_connect: Callable[[], None], on_select: Callable[[Optional[tk.Event]], None]) -> None:
        self.parent: tk.Widget = parent
        self.on_refresh: Callable[[], None] = on_refresh
        self.on_connect: Callable[[], None] = on_connect
        self.on_select: Callable[[Optional[tk.Event]], None] = on_select
        
        self.frame: Optional[tk.LabelFrame] = None
        self.device_var: Optional[tk.StringVar] = None
        self.device_combo: Optional[ttk.Combobox] = None
        self.connect_btn: Optional[tk.Button] = None
        
        self._create_panel()
    
    def _create_panel(self) -> None:
        frame = tk.LabelFrame(self.parent, text="设备选择", font=("Microsoft YaHei", 10))
        frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        self.device_var = tk.StringVar()
        self.device_combo = ttk.Combobox(frame, textvariable=self.device_var, state="readonly")
        self.device_combo.bind("<<ComboboxSelected>>", self.on_select)
        self.device_combo.pack(fill=tk.X, padx=10, pady=(0, 5))
        
        btn_frame = tk.Frame(frame)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Button(btn_frame, text="刷新", command=self.on_refresh,
                 font=("Microsoft YaHei", 9), bg="#3498db", fg="white", width=8
                 ).pack(side=tk.LEFT, padx=(0, 5))
        
        self.connect_btn = tk.Button(
            btn_frame, text="连接", command=self.on_connect,
            font=("Microsoft YaHei", 9), bg="#2ecc71", fg="white", width=8
        )
        self.connect_btn.pack(side=tk.RIGHT)
        
        self.frame = frame
    
    def update_devices(self, devices: List[str]) -> None:
        """更新设备列表"""
        if devices:
            self.device_combo['values'] = devices
            self.device_combo.current(0)
        else:
            self.device_combo['values'] = []
            self.device_var.set("")
    
    def get_selected_device(self) -> str:
        """获取选中的设备"""
        return self.device_var.get()
    
    def set_connect_button_state(self, text: str, bg_color: str) -> None:
        """设置连接按钮状态"""
        self.connect_btn.config(text=text, bg=bg_color)
    
    def get_frame(self) -> tk.LabelFrame:
        """获取面板frame"""
        return self.frame


__all__ = ["DevicePanel"]