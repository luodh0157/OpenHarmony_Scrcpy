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
主窗口模块
"""

import os
import time
import threading
import webbrowser
import gc
import tkinter as tk
from tkinter import messagebox
from datetime import datetime
from typing import Optional, Callable, Dict, List, Any

import numpy as np

from core import (
    AUTHOR,
    PROJECT_URL,
    VERSION,
    HOST,
    HEARTBEAT_TIMEOUT,
    LogLevel,
    ServerDeployState,
    print_log,
    HDCCommandExecutor,
    ServerManager,
    DeviceManager,
)

from video import VideoStreamClient

from gui.device_panel import DevicePanel
from gui.control_panel import ControlPanel, InfoPanel
from gui.video_panel import VideoPanel
from gui.device_controller import DeviceController


class MainWindow:
    """主窗口"""
    
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title(f"OHScrcpy - OpenHarmony投屏工具 {VERSION}    （作者: {AUTHOR}）")
        self.root.geometry("1200x800")
        
        self.log_title = "GUI"
        
        self.is_connected = False
        self.current_frame = None
        self.tk_image = None
        self.last_display_time = 0
        self.server_deploy_lock = threading.Lock()
        self.server_deploy_state = ServerDeployState.IDLE
        
        self.video_width = 0
        self.video_height = 0
        self.video_ratio = 0.0
        self.display_width = 0
        self.display_height = 0
        self.canvas_width = 800
        self.canvas_height = 600
        
        self.fps = 0
        self.frame_counter = 0
        self.last_fps_time = time.time()
        self.displayed_frames = 0
        self.last_print_frames = 0
        
        self.last_gc_frame_count = 0
        self.gc_interval_frames = 500
        self.image_refs = []
        
        self.video_canvas = None
        self.status_text_id = None
        self.running_status_text_id = None
        
        self.device_panel = None
        self.control_panel = None
        self.video_panel = None
        self.info_panel = None
        
        self.hdc_executor = None
        self.device_manager = None
        self.server_manager = None
        self.device_controller = None
        self.video_client = None
        
        self._setup_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.root.bind('<Configure>', self._on_window_resize)
        
        self._init_components_async()
        
        print_log(LogLevel.INFO, self.log_title, f"初始化完成")
    
    def _setup_ui(self) -> None:
        """设置UI"""
        self._create_title_bar()
        self._create_main_content()
        self._create_status_bar()
        self._show_waiting_screen()
    
    def _create_title_bar(self) -> None:
        """创建标题栏"""
        title_frame = tk.Frame(self.root, height=30, bg="#2c3e50")
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)
        
        left_frame = tk.Frame(title_frame, bg="#2c3e50")
        left_frame.pack(side=tk.LEFT, padx=10, pady=5)
        
        tk.Label(left_frame, text="OHScrcpy - OpenHarmony投屏工具", 
                font=("Microsoft YaHei", 12), fg="white", bg="#2c3e50").pack(side=tk.LEFT)
        
        right_frame = tk.Frame(title_frame, bg="#2c3e50")
        right_frame.pack(side=tk.RIGHT, padx=10, pady=5)
        
        tk.Button(right_frame, text="关于", font=("Microsoft YaHei", 9),
                 bg="#2c3e50", fg="white", relief=tk.FLAT, width=6,
                 command=self._show_about_dialog).pack(side=tk.RIGHT, padx=(10, 0))
        
        self.device_status_label = tk.Label(right_frame, text="设备: 未连接",
                                            font=("Microsoft YaHei", 9), fg="#ecf0f1", bg="#2c3e50")
        self.device_status_label.pack(side=tk.RIGHT, padx=(0, 10))
    
    def _create_main_content(self) -> None:
        """创建主内容区"""
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.video_panel = VideoPanel(main_frame, self._on_click, self._on_drag)
        self.video_canvas = self.video_panel.get_canvas()
        
        control_frame = tk.Frame(main_frame, width=300)
        control_frame.pack(side=tk.RIGHT, fill=tk.Y)
        control_frame.pack_propagate(False)
        
        self.device_panel = DevicePanel(control_frame, self._refresh_devices,
                                        self._trigger_connection, self._on_combobox_select)
        
        callbacks = {
            'power': self._power_key,
            'home': self._home_key,
            'back': self._back_key,
            'unlock': self._unlock_screen,
            'volume_up': self._volume_up,
            'volume_down': self._volume_down,
        }
        self.control_panel = ControlPanel(control_frame, callbacks)
        
        self.info_panel = InfoPanel(control_frame)
    
    def _create_status_bar(self) -> None:
        """创建状态栏"""
        status_frame = tk.Frame(self.root, height=25, bg="#34495e")
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        status_frame.pack_propagate(False)
        
        self.status_label = tk.Label(status_frame, text="就绪",
                                     font=("Microsoft YaHei", 9), fg="white", bg="#34495e", anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, padx=10)
        
        self.connection_status_label = tk.Label(status_frame, text="未连接",
                                                 font=("Microsoft YaHei", 9), fg="#e74c3c", bg="#34495e", anchor=tk.E)
        self.connection_status_label.pack(side=tk.RIGHT, padx=10)
        
        self.performance_label = tk.Label(status_frame, text="FPS: 0 | 帧数: 0",
                                          font=("Microsoft YaHei", 9), fg="#3498db", bg="#34495e")
        self.performance_label.pack(side=tk.RIGHT, padx=20)
    
    def _init_components_async(self) -> None:
        """异步初始化组件"""
        def init() -> None:
            self.hdc_executor = HDCCommandExecutor()
            self.device_manager = DeviceManager(self.hdc_executor)
            self.video_client = VideoStreamClient(device_manager=self.device_manager,
                                                  on_frame_decoded=self._on_frame_decoded,
                                                  debug=False)
            self.device_controller = None
            self._refresh_devices()
        threading.Thread(target=init, daemon=True).start()
    
    def _open_project_url(self, event: Optional[tk.Event] = None) -> None:
        """打开项目地址"""
        webbrowser.open(PROJECT_URL)
    
    def _show_about_dialog(self) -> None:
        """显示关于对话框"""
        about_window = tk.Toplevel(self.root)
        about_window.title("关于 OHScrcpy")
        about_window.resizable(False, False)
        about_window.transient(self.root)
        about_window.grab_set()
        
        root_x = self.root.winfo_rootx()
        root_y = self.root.winfo_rooty()
        root_w = self.root.winfo_width()
        root_h = self.root.winfo_height()
        win_w = 420
        win_h = 260
        x = root_x + (root_w - win_w) // 2
        y = root_y + (root_h - win_h) // 2
        about_window.geometry(f"{win_w}x{win_h}+{x}+{y}")
        
        main_frame = tk.Frame(about_window, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(main_frame, text="OHScrcpy - OpenHarmony投屏工具",
                font=("Microsoft YaHei", 12, "bold"), anchor="center").pack(pady=(0, 15))
        
        content_frame = tk.Frame(main_frame)
        content_frame.pack(fill=tk.X, anchor="w")
        
        tk.Label(content_frame, text=f"版本: {VERSION}",
                font=("Microsoft YaHei", 10), anchor="w").pack(anchor="w", padx=10, pady=2)
        
        tk.Label(content_frame, text=f"作者: {AUTHOR}",
                font=("Microsoft YaHei", 10), anchor="w").pack(anchor="w", padx=10, pady=2)
        
        tk.Label(content_frame, text="项目地址:", font=("Microsoft YaHei", 10), anchor="w").pack(anchor="w", padx=10, pady=2)
        
        url_label = tk.Label(content_frame, text=PROJECT_URL,
                             font=("Microsoft YaHei", 10), fg="blue", cursor="hand2", anchor="w")
        url_label.pack(anchor="w", padx=10, pady=2)
        url_label.bind("<Button-1>", self._open_project_url)
        
        tk.Button(main_frame, text="关闭", command=about_window.destroy,
                 font=("Microsoft YaHei", 9), width=10).pack(pady=(20, 0))
        about_window.focus_set()
    
    def _on_frame_decoded(self, frame: np.ndarray) -> None:
        """帧解码回调"""
        self.current_frame = frame
        self.frame_counter += 1
        
        current_time = time.time()
        if current_time - self.last_fps_time >= 1.0:
            self.fps = self.frame_counter
            self.frame_counter = 0
            self.last_fps_time = current_time
            self.performance_label.config(text=f"FPS: {self.fps} | 帧数: {self.video_client.frame_count}")
    
    def _on_click(self, x: int, y: int) -> None:
        """处理点击"""
        pass
    
    def _on_drag(self, start_x: int, start_y: int, end_x: int, end_y: int) -> None:
        """处理拖动"""
        pass
    
    def _update_video_display(self) -> None:
        """更新视频显示"""
        current_time = time.time()
        
        if self.is_connected and hasattr(self.video_client, 'last_data_time'):
            time_since_last_data = current_time - self.video_client.last_data_time
            if time_since_last_data > HEARTBEAT_TIMEOUT:
                print_log(LogLevel.WARN, self.log_title, f"检测到心跳超时 ({time_since_last_data:.1f}秒)，断开连接")
                self._disconnect_device()
                return
        
        if current_time - self.last_display_time < 0.033:
            self.root.after(10, self._update_video_display)
            return
        
        self.last_display_time = current_time
        
        if not self.is_connected:
            self.root.after(100, self._update_video_display)
            return
        
        try:
            import numpy as np
            frame = self.video_client.get_current_frame(timeout=0.001)
            if frame is None:
                frame = self.current_frame
            
            if frame is not None:
                self.displayed_frames += 1
                
                if self.last_print_frames != self.displayed_frames and self.displayed_frames % 100 == 0:
                    self.last_print_frames = self.displayed_frames
                    print_log(LogLevel.DEBUG, self.log_title, f"已显示 {self.displayed_frames} 帧，队列大小: {self.video_client.frame_queue.qsize()}")
                
                if self.displayed_frames - self.last_gc_frame_count >= self.gc_interval_frames:
                    self.last_gc_frame_count = self.displayed_frames
                
                try:
                    from PIL import Image
                    pil_img = Image.fromarray(frame)
                except Exception as e:
                    print_log(LogLevel.ERROR, self.log_title, f"创建PIL图像失败: {e}")
                    self.root.after(10, self._update_video_display)
                    return
                
                if self.video_width != pil_img.width or self.video_height != pil_img.height:
                    self.video_width = pil_img.width
                    self.video_height = pil_img.height
                    self.video_ratio = 0.0
                    print_log(LogLevel.INFO, self.log_title, f"原始视频尺寸: {self.video_width}x{self.video_height}")
                    
                    self.canvas_width = self.video_canvas.winfo_width()
                    self.canvas_height = self.video_canvas.winfo_height()
                    print_log(LogLevel.INFO, self.log_title, f"画布尺寸: {self.canvas_width}x{self.canvas_height}")
                    if self.canvas_width <= 10 or self.canvas_height <= 10:
                        self.canvas_width = 800
                        self.canvas_height = 600
                    
                    width_ratio = self.canvas_width / pil_img.width
                    height_ratio = self.canvas_height / pil_img.height
                    self.video_ratio = min(width_ratio, height_ratio)
                    self.display_width = int(pil_img.width * self.video_ratio)
                    self.display_height = int(pil_img.height * self.video_ratio)
                    print_log(LogLevel.INFO, self.log_title, f"显示尺寸: {self.display_width}x{self.display_height} ratio:{self.video_ratio}")
                    
                    if self.device_controller:
                        self.device_controller.set_display_resolution(self.display_width, self.display_height, self.video_ratio)
                
                try:
                    pil_img_resized = pil_img.resize((self.display_width, self.display_height),
                                                     Image.Resampling.LANCZOS)
                except Exception as e:
                    print_log(LogLevel.ERROR, self.log_title, f"缩放图像失败: {e}")
                    pil_img_resized = pil_img
                
                x_offset = (self.canvas_width - self.display_width) // 2
                y_offset = (self.canvas_height - self.display_height) // 2
                
                try:
                    from PIL import ImageTk
                    self.tk_image = ImageTk.PhotoImage(pil_img_resized)
                    self.image_refs.clear()
                    self.image_refs.append(self.tk_image)
                except Exception as e:
                    print_log(LogLevel.ERROR, self.log_title, f"创建Tkinter图像失败: {e}")
                    self.root.after(10, self._update_video_display)
                    return
                
                self.video_canvas.delete("all")
                
                self.video_canvas.create_image(
                    x_offset, y_offset,
                    anchor=tk.NW,
                    image=self.tk_image
                )
                
                if self.status_text_id:
                    self.video_canvas.delete(self.status_text_id)
                
                status_text = f"帧数: {self.video_client.frame_count} | FPS: {self.fps} | 尺寸: {self.display_width}x{self.display_height}"
                self.status_text_id = self.video_canvas.create_text(
                    10, 10,
                    anchor=tk.NW,
                    text=status_text,
                    fill="white",
                    font=("Microsoft YaHei", 9),
                    tags="status"
                )
                
                self.video_canvas.update_idletasks()
            
        except Exception as e:
            if self.is_connected:
                print_log(LogLevel.ERROR, self.log_title, f"显示错误: {e}")
        
        self.root.after(10, self._update_video_display)
    
    def _show_waiting_screen(self) -> None:
        """显示等待画面"""
        self.video_canvas.delete("all")
        self.video_canvas.config(bg="#1a1a2e")
        
        canvas_width = self.video_canvas.winfo_width()
        canvas_height = self.video_canvas.winfo_height()
        
        if canvas_width <= 10 or canvas_height <= 10:
            canvas_width = 800
            canvas_height = 600
        
        self.video_canvas.create_text(
            canvas_width // 2, canvas_height // 2 - 30,
            text="OHScrcpy - OpenHarmony投屏工具",
            fill="white",
            font=("Microsoft YaHei", 14, "bold")
        )
        
        self.running_status_text_id = self.video_canvas.create_text(
            canvas_width // 2, canvas_height // 2 + 10,
            text="等待连接设备...",
            fill="#3498db",
            font=("Microsoft YaHei", 12)
        )
        
        self.video_canvas.create_text(
            canvas_width // 2, canvas_height // 2 + 50,
            text="请先选择设备，然后点击[连接]按钮进行投屏",
            fill="#95a5a6",
            font=("Microsoft YaHei", 10)
        )
        
        self.status_text_id = None
    
    def _update_running_status(self, content: str) -> None:
        """更新运行状态"""
        self.video_canvas.itemconfig(self.running_status_text_id, text=content)
    
    def _refresh_devices(self) -> None:
        """刷新设备"""
        self._update_device_status("正在扫描设备...")
        devices = self.device_manager.discover_devices()
        display_names = [d.display_name() for d in devices]
        current_selection = self.device_panel.get_selected_device()
        
        if not self.is_connected:
            if devices:
                self.device_panel.update_devices(display_names)
                self._update_device_status(f"发现 {len(devices)} 个设备")
                self._on_combobox_select(None)
            else:
                self.device_panel.update_devices([])
                self._update_device_status("未发现设备")
            return
        
        if not devices:
            messagebox.showwarning("提示", "当前投屏设备已断开")
            self._disconnect_device()
            self.device_panel.update_devices([])
            self._update_device_status("设备已断开，未发现其他设备")
            return
        
        current_list = list(self.device_panel.device_combo['values'] or [])
        if current_selection and current_selection not in display_names:
            messagebox.showwarning("提示", "当前投屏设备已断开")
            self._disconnect_device()
            if current_selection in current_list:
                current_list.remove(current_selection)
            self.device_panel.update_devices(current_list if current_list else display_names)
            self._update_device_status(f"设备已断开，剩余 {len(current_list)} 个设备")
            return
        
        current_list = list(self.device_panel.device_combo['values'] or [])
        new_devices = [name for name in display_names if name not in current_list]
        
        if new_devices:
            self.device_panel.update_devices(current_list + new_devices)
            self._update_device_status(f"发现 {len(new_devices)} 个新设备（投屏中）")
            print_log(LogLevel.INFO, self.log_title, f"新增设备: {new_devices}")
        else:
            self._update_device_status(f"未发现新设备（投屏中，列表 {len(current_list)} 个）")
    
    def _trigger_connection(self) -> None:
        """连接/断开设备"""
        if not self.is_connected:
            self._connect_device()
        else:
            self._disconnect_device()
    
    def _set_server_deploy_state(self, state: ServerDeployState) -> None:
        """设置服务部署状态"""
        with self.server_deploy_lock:
            self.server_deploy_state = state
    
    def _get_server_deploy_state(self) -> ServerDeployState:
        """获取服务部署状态"""
        with self.server_deploy_lock:
            return self.server_deploy_state
    
    def _on_combobox_select(self, event: Optional[tk.Event]) -> None:
        """设备选择事件"""
        print_log(LogLevel.INFO, self.log_title, "-"*60)
        
        selected_device = self.device_panel.get_selected_device()
        print_log(LogLevel.INFO, self.log_title, f"用户选择设备: {selected_device}")
        
        # 情况1：正在投屏中
        if self.is_connected:
            current_device = self.device_manager.get_current_device()
            
            if current_device is None:
                print_log(LogLevel.WARN, self.log_title, f"投屏中但无法获取当前设备信息")
                return
            
            # 检查是否选择了同一设备
            if current_device.display_name() == selected_device:
                print_log(LogLevel.INFO, self.log_title, f"选择了当前正在投屏的设备，保持投屏状态")
                return
            
            # 选择了不同设备，询问用户是否切换
            print_log(LogLevel.INFO, self.log_title, f"投屏中切换设备: {current_device.display_name()} -> {selected_device}")
            
            # 弹出确认对话框
            response = messagebox.askyesno(
                "切换设备确认",
                f"当前正在投屏设备:\n{current_device.display_name()}\n\n"
                f"是否切换到设备:\n{selected_device}?\n\n"
                "切换将断开当前投屏连接。"
            )
            
            if not response:
                # 用户不同意切换，恢复显示为当前投屏设备
                print_log(LogLevel.INFO, self.log_title, f"用户取消切换，恢复设备选择显示")
                self.device_panel.set_selected_device(current_device.display_name())
                return
            
            # 用户同意切换，继续后续流程（断开连接将在 _install_and_start_server_async 中执行）
            print_log(LogLevel.INFO, self.log_title, f"用户确认切换设备，准备断开当前连接")
        
        # 情况2：未投屏，或投屏中用户同意切换
        print_log(LogLevel.INFO, self.log_title, f"投屏准备: 开始安装和启动服务端...")
        threading.Thread(target=self._install_and_start_server_async, daemon=True).start()
    
    def _on_server_deploy_finish(self, succ: bool, msg: str) -> None:
        """服务部署完成回调"""
        self.connection_status_label.config(text="未连接", fg="#e74c3c")
        if not succ:
            messagebox.showerror("错误", f"{msg}")
    
    def _install_and_start_server_async(self) -> None:
        """异步安装并启动服务端"""
        was_connected = self.is_connected
        
        # 只有在连接状态时才触发断开流程
        if was_connected:
            print_log(LogLevel.INFO, self.log_title, f"断开当前设备连接...")
            self.is_connected = False
            self.video_client.disconnect()
            
            self.image_refs.clear()
            
            self.device_controller = None
            
            print_log(LogLevel.INFO, self.log_title, f"连接已断开，准备切换到新设备")
        
        self._show_waiting_screen()
        
        self.device_panel.set_connect_button_state("连接", "#2ecc71")
        
        if was_connected:
            self.connection_status_label.config(text="切换中...", fg="#f39c12")
        else:
            self.connection_status_label.config(text="未连接", fg="#e74c3c")
        
        self.performance_label.config(text="FPS: 0 | 帧数: 0")
        
        self.video_width = 0
        self.video_height = 0
        self.video_ratio = 0.0
        self.display_width = 0
        self.display_height = 0
        
        selected = self.device_panel.get_selected_device()
        if not selected:
            print_log(LogLevel.WARN, self.log_title, f"用户选择设备为空")
            return
        
        target_device = None
        for device in self.device_manager.devices:
            if device.display_name() == selected:
                target_device = device
                break
        
        if not target_device or not self.device_manager.select_device(target_device.sn):
            self._update_device_status("设备选择失败")
            return
        
        self._update_running_status(f"[预安装] 正在获取可用转发端口，请稍等...")
        port = self.device_manager.get_port_forwarding()
        if port == -1:
            print_log(LogLevel.ERROR, self.log_title, f"获取可用转发端口失败！")
            self.root.after(0, self._on_server_deploy_finish, False, "获取可用转发端口失败！")
            return
        
        self._update_running_status(f"[预安装] 正在安装服务端，请稍等...")
        print_log(LogLevel.INFO, self.log_title, f"检查服务端安装状态...")
        if not self.device_manager.check_server_installed():
            print_log(LogLevel.INFO, self.log_title, f"服务端未安装，开始安装...")
            
            if not self.device_manager.install_server():
                print_log(LogLevel.ERROR, self.log_title, f"服务端安装失败！")
                self.root.after(0, self._on_server_deploy_finish, False, "服务端安装失败！")
                return
        else:
            print_log(LogLevel.INFO, self.log_title, f"服务端已安装")
        
        self._update_running_status(f"[预安装] 正在启动服务端，请稍等...")
        print_log(LogLevel.INFO, self.log_title, f"检查服务端运行状态...")
        if not self.device_manager.check_server_running():
            print_log(LogLevel.INFO, self.log_title, f"启动服务端...")
            if not self.device_manager.start_server(port):
                print_log(LogLevel.ERROR, self.log_title, f"服务端启动失败！")
                self._update_running_status(f"[预安装] 启动服务端失败！")
                self.root.after(0, self._on_server_deploy_finish, False, "服务端启动失败！")
                return
            
            print_log(LogLevel.INFO, self.log_title, f"等待服务端就绪...")
            time.sleep(1)
        else:
            print_log(LogLevel.INFO, self.log_title, f"服务端已在运行")
        self._update_running_status(f"[预安装] 服务端已就绪，可随时点击[连接]开始投屏！")
        self.connection_status_label.config(text="未连接", fg="#e74c3c")
    
    def _install_and_start_server(self, port: int) -> bool:
        """安装并启动服务端"""
        print_log(LogLevel.INFO, self.log_title, f"检查服务端安装状态...")
        if not self.device_manager.check_server_installed():
            print_log(LogLevel.INFO, self.log_title, f"服务端未安装，开始安装...")
            
            if not self.device_manager.install_server():
                messagebox.showerror("错误", "服务端安装失败！")
                print_log(LogLevel.ERROR, self.log_title, f"服务端安装失败")
                return False
        else:
            print_log(LogLevel.INFO, self.log_title, f"服务端已安装")
        
        print_log(LogLevel.INFO, self.log_title, f"检查服务端运行状态...")
        if not self.device_manager.check_server_running():
            print_log(LogLevel.INFO, self.log_title, f"启动服务端...")
            if not self.device_manager.start_server(port):
                messagebox.showerror("错误", f"服务端启动失败！")
                print_log(LogLevel.ERROR, self.log_title, f"服务端启动失败")
                return False
            
            print_log(LogLevel.INFO, self.log_title, f"等待服务端就绪...")
            time.sleep(1)
        else:
            print_log(LogLevel.INFO, self.log_title, f"服务端已在运行")
        return True
    
    def _connect_device(self) -> None:
        """连接设备"""
        selected = self.device_panel.get_selected_device()
        if not selected:
            messagebox.showwarning("警告", "请先选择设备")
            return
        
        target_device: Optional[Any] = None
        for device in self.device_manager.devices:
            if device.display_name() == selected:
                target_device = device
                break
        
        if not target_device or not self.device_manager.select_device(target_device.sn):
            self._update_device_status("设备选择失败")
            return
        
        def connect_device_async() -> None:
            port = self.device_manager.get_port_forwarding()
            if port == -1:
                print_log(LogLevel.ERROR, self.log_title, f"获取可用转发端口失败")
                self.device_panel.set_connect_button_state("连接", "#2ecc71")
                return
            
            if not self._install_and_start_server(port):
                self.device_panel.set_connect_button_state("连接", "#2ecc71")
                return

            print_log(LogLevel.INFO, self.log_title, f"设置端口转发...")
            if not self.device_manager.setup_port_forwarding(port, port):
                print_log(LogLevel.ERROR, self.log_title, f"端口转发失败，请尝试重新连接...")
                self.device_panel.set_connect_button_state("连接", "#2ecc71")
                return

            try:
                device = self.device_manager.get_current_device()
                self._update_device_status(f"正在连接设备: {device.sn}...")
            
                print_log(LogLevel.DEBUG, self.log_title, f"连接视频流服务器...")
                if self.video_client.connect(HOST, port):
                    config = self.video_client.config
                    
                    self.device_controller = DeviceController(self.hdc_executor)
                    self.device_controller.bind_video_canvas(self.video_canvas)
                    
                    self.is_connected = True
                    self.device_panel.set_connect_button_state("断开", "#e74c3c")
                    self.connection_status_label.config(text="已连接", fg="#2ecc71")
                    self.device_status_label.config(text=f"设备: {device.sn}")
                    
                    self.displayed_frames = 0
                    self.frame_counter = 0
                    self.last_fps_time = time.time()
                    self.last_print_frames = 0
                    
                    self.video_canvas.delete("all")
                    self.video_canvas.config(bg="black")
                    
                    self._update_video_display()
                    
                    self._update_device_status(f"连接成功！分辨率: {config.width}x{config.height}")
                else:
                    self._update_device_status("连接失败")
                    self.device_panel.set_connect_button_state("连接", "#2ecc71")
                    messagebox.showinfo("连接失败",
                        "无法连接到服务端！请检查:\n"
                        "1. 服务端是否在设备上运行\n"
                        "2. 服务端口是否正确")
                    return
                
            except Exception as e:
                import traceback
                self._update_device_status(f"连接失败: {str(e)}")
                traceback.print_exc()
                self._disconnect_device()
                return
        
        threading.Thread(target=connect_device_async, daemon=True).start()
        self.device_panel.set_connect_button_state("连接中", "#e74c3c")
    
    def _disconnect_device(self) -> None:
        """断开设备"""
        self.is_connected = False
        self.video_client.disconnect()
        
        self.image_refs.clear()
        
        self._show_waiting_screen()
        
        self.device_panel.set_connect_button_state("连接", "#2ecc71")
        self.connection_status_label.config(text="未连接", fg="#e74c3c")
        self.device_status_label.config(text="设备: 未连接")
        self.performance_label.config(text="FPS: 0 | 帧数: 0")
        
        self.video_width = 0
        self.video_height = 0
        self.video_ratio = 0.0
        self.display_width = 0
        self.display_height = 0
        self.canvas_width = 800
        self.canvas_height = 600
        
        self._force_garbage_collection()
        self._update_device_status("设备已断开")
        print_log(LogLevel.INFO, self.log_title, "-"*60)
    
    def _power_key(self) -> None:
        """电源键"""
        if self.is_connected and self.device_controller:
            self.device_controller.power_key()
            print_log(LogLevel.INFO, self.log_title, f"发送电源键")
    
    def _home_key(self) -> None:
        """主页键"""
        if self.is_connected and self.device_controller:
            self.device_controller.home_key()
            print_log(LogLevel.INFO, self.log_title, f"发送Home键")
    
    def _back_key(self) -> None:
        """返回键"""
        if self.is_connected and self.device_controller:
            self.device_controller.back_key()
            print_log(LogLevel.INFO, self.log_title, f"发送返回键")
    
    def _unlock_screen(self) -> None:
        """解锁"""
        if self.is_connected and self.device_controller:
            self.device_controller.unlock_screen()
            print_log(LogLevel.INFO, self.log_title, f"发送解锁屏幕")
    
    def _volume_up(self) -> None:
        """音量+"""
        if self.is_connected and self.device_controller:
            self.device_controller.volume_up()
            print_log(LogLevel.INFO, self.log_title, f"发送音量+")
    
    def _volume_down(self) -> None:
        """音量-"""
        if self.is_connected and self.device_controller:
            self.device_controller.volume_down()
            print_log(LogLevel.INFO, self.log_title, f"发送音量-")
    
    def _print_debug_info(self) -> None:
        """打印调试信息"""
        debug_info_title = "调试信息"
        print_log(LogLevel.INFO, debug_info_title, f"\n======== 调试信息 ========")
        print_log(LogLevel.INFO, debug_info_title, f"连接状态: {self.is_connected}")
        print_log(LogLevel.INFO, debug_info_title, f"当前fps: {self.fps}")
        print_log(LogLevel.INFO, debug_info_title, f"已显示帧数: {self.displayed_frames}")
        print_log(LogLevel.INFO, debug_info_title, f"视频尺寸: {self.video_width}x{self.video_height}")
        print_log(LogLevel.INFO, debug_info_title, f"图像引用数: {len(self.image_refs)}")
        
        if self.video_client:
            print_log(LogLevel.INFO, debug_info_title, f"总接收帧数: {self.video_client.frame_count}")
            print_log(LogLevel.INFO, debug_info_title, f"总字节数: {self.video_client.total_bytes}")
            print_log(LogLevel.INFO, debug_info_title, f"队列大小: {self.video_client.frame_queue.qsize()}")
            print_log(LogLevel.INFO, debug_info_title, f"最后数据时间: {time.time() - self.video_client.last_data_time:.1f}秒前")
            print_log(LogLevel.INFO, debug_info_title, f"坏包数: {self.video_client.bad_packet_bytes}")
            print_log(LogLevel.INFO, debug_info_title, f"SPS状态: {self.video_client.sps_received}")
            print_log(LogLevel.INFO, debug_info_title, f"PPS状态: {self.video_client.pps_received}")
            print_log(LogLevel.INFO, debug_info_title, f"VPS状态: {self.video_client.vps_received}")
            
            if self.video_client.decoder:
                decoder = self.video_client.decoder
                print_log(LogLevel.INFO, debug_info_title, f"解码统计: 成功={decoder.decode_success}, 失败={decoder.decode_failure}")
                print_log(LogLevel.INFO, debug_info_title, f"解码器状态: initialized={decoder.codec_ctx is not None}")
        
        try:
            import psutil
            process = psutil.Process()
            mem_info = process.memory_info()
            print_log(LogLevel.INFO, debug_info_title, f"内存使用: RSS={mem_info.rss / 1024 / 1024:.1f}MB, VMS={mem_info.vms / 1024 / 1024:.1f}MB")
        except ImportError:
            pass
        print_log(LogLevel.INFO, debug_info_title, f"==========================\n")
    
    def _save_debug_frame(self) -> None:
        """保存当前帧用于调试"""
        debug_frame_title = "保存调试帧"
        if self.current_frame is not None:
            try:
                from PIL import Image
                debug_dir = "debug_frames"
                os.makedirs(debug_dir, exist_ok=True)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = os.path.join(debug_dir, f"debug_{timestamp}.png")
                
                pil_img = Image.fromarray(self.current_frame)
                pil_img.save(filename)
                
                print_log(LogLevel.INFO, debug_frame_title, f"调试帧保存在: {filename}")
                print_log(LogLevel.INFO, debug_frame_title, f"图像尺寸: {pil_img.size}")
            except Exception as e:
                print_log(LogLevel.ERROR, debug_frame_title, f"保存调试帧失败: {e}")
    
    def _show_debug_window(self) -> None:
        """显示调试窗口"""
        debug_window = tk.Toplevel(self.root)
        debug_window.title("调试信息")
        debug_window.geometry("600x400")
        debug_window.transient(self.root)
        debug_window.grab_set()
        
        text_widget = tk.Text(debug_window, wrap=tk.WORD)
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        debug_info = []
        debug_info.append(f"连接状态: {self.is_connected}")
        debug_info.append(f"当前fps: {self.fps}")
        debug_info.append(f"已显示帧数: {self.displayed_frames}")
        debug_info.append(f"视频尺寸: {self.video_width}x{self.video_height}")
        
        if self.video_client:
            debug_info.append(f"总接收帧数: {self.video_client.frame_count}")
            debug_info.append(f"总字节数: {self.video_client.total_bytes}")
            debug_info.append(f"队列大小: {self.video_client.frame_queue.qsize()}")
            debug_info.append(f"坏包数: {self.video_client.bad_packet_bytes}")
            debug_info.append(f"SPS状态: {self.video_client.sps_received}")
            debug_info.append(f"PPS状态: {self.video_client.pps_received}")
            debug_info.append(f"VPS状态: {self.video_client.vps_received}")
            
            if self.video_client.decoder:
                decoder = self.video_client.decoder
                debug_info.append(f"解码成功: {decoder.decode_success}")
                debug_info.append(f"解码失败: {decoder.decode_failure}")
            
            if hasattr(self.video_client, 'last_data_time'):
                time_since_last_data = time.time() - self.video_client.last_data_time
                debug_info.append(f"心跳状态: {time_since_last_data:.1f}秒前收到数据")
        
        text_widget.insert(tk.END, "\n".join(debug_info))
        text_widget.config(state=tk.DISABLED)
    
    def _force_garbage_collection(self) -> None:
        """强制垃圾回收"""
        def _async_garbage_collection_func() -> None:
            print_log(LogLevel.INFO, self.log_title, f"强制垃圾回收...")
            collected = gc.collect()
            print_log(LogLevel.INFO, self.log_title, f"回收了 {collected} 个对象")
        
        threading.Thread(target=_async_garbage_collection_func, daemon=True).start()
    
    def _update_device_status(self, message: str) -> None:
        """更新状态"""
        self.status_label.config(text=message)
        print_log(LogLevel.INFO, "GUI设备状态更新", f"{message}")
    
    def _on_closing(self) -> None:
        """关闭窗口"""
        if self.is_connected:
            if messagebox.askokcancel("退出", "设备仍处于连接状态，确定要退出吗？"):
                self._disconnect_device()
                self.root.destroy()
        else:
            if self.video_client:
                self.video_client.disconnect()
            self.root.destroy()
    
    def _on_window_resize(self, event: tk.Event) -> None:
        """窗口大小改变"""
        print_log(LogLevel.DEBUG, self.log_title, f"窗口大小变化: {event.width}x{event.height}")
        self.video_ratio = 0.0
    
    def run(self) -> None:
        """运行"""
        self.root.mainloop()


__all__ = ["MainWindow"]