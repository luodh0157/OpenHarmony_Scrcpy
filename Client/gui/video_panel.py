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
from typing import Callable, Optional, Any


class VideoPanel:
    """视频显示面板"""
    
    def __init__(self, parent: tk.Widget, on_click: Callable[[int, int], None], on_drag: Callable[[int, int, int, int], None]) -> None:
        self.parent: tk.Widget = parent
        self.on_click: Callable[[int, int], None] = on_click
        self.on_drag: Callable[[int, int, int, int], None] = on_drag
        
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
        
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_release)
        
        self.drag_start_x: int = 0
        self.drag_start_y: int = 0
        
        self.frame = frame
    
    def _on_canvas_click(self, event: tk.Event) -> None:
        """处理画布点击"""
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        if self.on_click:
            self.on_click(event.x, event.y)
    
    def _on_canvas_drag(self, event: tk.Event) -> None:
        """处理画布拖动"""
        pass
    
    def _on_canvas_release(self, event: tk.Event) -> None:
        """处理画布释放"""
        if self.drag_start_x != event.x or self.drag_start_y != event.y:
            if self.on_drag:
                self.on_drag(self.drag_start_x, self.drag_start_y, event.x, event.y)
    
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