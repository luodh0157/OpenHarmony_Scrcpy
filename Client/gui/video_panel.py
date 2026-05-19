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
视频显示面板
"""

import tkinter as tk
from typing import Optional


class VideoPanel:
    """视频显示面板"""
    
    def __init__(self, parent: tk.Widget) -> None:
        self.parent: tk.Widget = parent
        
        self.frame: Optional[tk.LabelFrame] = None
        self.canvas: Optional[tk.Canvas] = None
        self.status_text_id: Optional[int] = None
        self.running_status_text_id: Optional[int] = None
        
        self._create_panel()
    
    def _create_panel(self) -> None:
        frame = tk.LabelFrame(self.parent, text="视频显示", font=("Microsoft YaHei", 10))
        frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        self.canvas = tk.Canvas(frame, bg="#1a1a2e", highlightthickness=1)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        self.frame = frame
    
    def show_waiting_screen(self, message: str = "等待连接...") -> None:
        """显示等待画面"""
        self.canvas.delete("all")
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        if canvas_width <= 10 or canvas_height <= 10:
            canvas_width = 800
            canvas_height = 600
        
        self.canvas.create_rectangle(0, 0, canvas_width, canvas_height, fill="#1a1a2e", outline="")
        
        text_x = canvas_width // 2
        text_y = canvas_height // 2
        
        self.status_text_id = self.canvas.create_text(
            text_x, text_y - 30,
            text=message,
            font=("Microsoft YaHei", 16),
            fill="#ecf0f1"
        )
    
    def update_running_status(self, content: str) -> None:
        """更新运行状态"""
        if self.running_status_text_id:
            self.canvas.itemconfig(self.running_status_text_id, text=content)
        else:
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            self.running_status_text_id = self.canvas.create_text(
                canvas_width // 2, canvas_height - 20,
                text=content,
                font=("Microsoft YaHei", 9),
                fill="#bdc3c7"
            )
    
    def clear_running_status(self) -> None:
        """清除运行状态"""
        if self.running_status_text_id:
            self.canvas.delete(self.running_status_text_id)
            self.running_status_text_id = None
    
    def get_canvas(self) -> tk.Canvas:
        """获取画布"""
        return self.canvas
    
    def get_frame(self) -> tk.LabelFrame:
        """获取面板frame"""
        return self.frame


__all__ = ["VideoPanel"]