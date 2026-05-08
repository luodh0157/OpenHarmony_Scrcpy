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
OpenHarmony_Scrcpy 设备控制器
"""

import tkinter as tk
from typing import Tuple, Optional, Any

from core.constants import LogLevel
from core.logger import print_log
from core.hdc_executor import HDCCommandExecutor


class DeviceController:
    """设备控制器"""
    
    KEY_MAPPINGS: dict = {
        "home": 1,
        "back": 2,
        "volume_up": 16,
        "volume_down": 17,
        "power": 18,
        "camera": 19,
    }
    
    def __init__(self, hdc_executor: HDCCommandExecutor) -> None:
        self.hdc: HDCCommandExecutor = hdc_executor
        self.display_width: int = 0
        self.display_height: int = 0
        self.display_ratio: float = 0.0
        self.left: int = 0
        self.right: int = 0
        self.top: int = 0
        self.bottom: int = 0
        self.video_canvas: Optional[tk.Canvas] = None
        self.drag_start: Optional[Tuple[int, int]] = None
        self.log_title: str = "设备控制器"
    
    def set_display_resolution(self, width: int, height: int, ratio: float) -> None:
        """设置显示分辨率"""
        self.display_width = width
        self.display_height = height
        self.display_ratio = ratio
        if self.video_canvas:
            self.left = int((self.video_canvas.winfo_width() - width) / 2)
            self.right = int((self.video_canvas.winfo_width() - width) / 2 + width)
            self.top = int((self.video_canvas.winfo_height() - height) / 2)
            self.bottom = int((self.video_canvas.winfo_height() - height) / 2 + height)
            print_log(LogLevel.DEBUG, self.log_title, f"图像显示区域: left:{self.left} right:{self.right} top:{self.top} bottom:{self.bottom}")
    
    def bind_video_canvas(self, canvas: tk.Canvas) -> None:
        """绑定视频画布"""
        self.video_canvas = canvas
        
        canvas.bind("<ButtonPress-1>", self._on_mouse_down)
        canvas.bind("<B1-Motion>", self._on_mouse_drag)
        canvas.bind("<ButtonRelease-1>", self._on_mouse_up)
    
    def _window_to_device_coords(self, window_x: int, window_y: int) -> Tuple[int, int]:
        """窗口坐标转设备坐标"""
        if not self.video_canvas:
            return 0, 0
        
        device_x = int((window_x - self.left) / self.display_ratio)
        device_y = int((window_y - self.top) / self.display_ratio)
        print_log(LogLevel.DEBUG, self.log_title, f"winow({window_x},{window_y}) ==> device({device_x},{device_y})")
        
        return device_x, device_y
    
    def _on_mouse_down(self, event: tk.Event) -> None:
        """鼠标按下"""
        if self.left <= event.x <= self.right and self.top <= event.y <= self.bottom:
            self.drag_start = (event.x, event.y)
    
    def _on_mouse_drag(self, event: tk.Event) -> None:
        """鼠标拖动"""
        pass  # 实时预览可以在这里实现
    
    def _on_mouse_up(self, event: tk.Event) -> None:
        """鼠标释放"""
        if self.drag_start is None:
            return
        
        start_x, start_y = self.drag_start
        end_x, end_y = event.x, event.y
        
        dev_start_x, dev_start_y = self._window_to_device_coords(start_x, start_y)
        dev_end_x, dev_end_y = self._window_to_device_coords(end_x, end_y)
        
        drag_distance = ((end_x - start_x)**2 + (end_y - start_y)**2)**0.5
        
        if drag_distance > 10:
            # 滑动操作
            smooth_time = 100
            self.send_swipe(dev_start_x, dev_start_y, dev_end_x, dev_end_y, smooth_time)
        else:
            # 点击操作
            self.send_tap(dev_start_x, dev_start_y)
        
        self.drag_start = None
    
    def send_key(self, key_name: str) -> bool:
        """发送按键"""
        if key_name not in self.KEY_MAPPINGS:
            print_log(LogLevel.WARN, self.log_title, f"未知按键: {key_name}")
            return False
        
        keycode = self.KEY_MAPPINGS[key_name]
        args = ["shell", "uinput", "-K", "-d", str(keycode), "-u", str(keycode)]
        result = self.hdc.execute(args)
        
        if result["success"]:
            print_log(LogLevel.DEBUG, self.log_title, f"发送按键: {key_name} (keycode={keycode})")
        else:
            print_log(LogLevel.WARN, self.log_title, f"发送按键失败: {key_name}")
        
        return result["success"]
    
    def send_swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 100) -> bool:
        """发送滑动"""
        args = ["shell", "uinput", "-T", "-m", str(x1), str(y1), str(x2), str(y2), str(duration_ms)]
        result = self.hdc.execute(args)
        
        if result["success"]:
            print_log(LogLevel.DEBUG, self.log_title, f"发送滑动: ({x1},{y1}) -> ({x2},{y2}), duration={duration_ms}ms")
        
        return result["success"]
    
    def send_tap(self, x: int, y: int) -> bool:
        """发送点击"""
        args = ["shell", "uinput", "-T", "-d", str(x), str(y), "-u", str(x), str(y)]
        result = self.hdc.execute(args)
        
        if result["success"]:
            print_log(LogLevel.DEBUG, self.log_title, f"发送点击: ({x},{y})")
        
        return result["success"]
    
    def power_key(self) -> bool:
        """电源键"""
        return self.send_key("power")
    
    def home_key(self) -> bool:
        """Home键"""
        return self.send_key("home")
    
    def back_key(self) -> bool:
        """返回键"""
        return self.send_key("back")
    
    def unlock_screen(self) -> bool:
        """解锁屏幕"""
        return self.send_swipe(350, 1100, 350, 500, 200)
    
    def volume_up(self) -> bool:
        """音量加"""
        return self.send_key("volume_up")
    
    def volume_down(self) -> bool:
        """音量减"""
        return self.send_key("volume_down")



__all__ = ["DeviceController"]
