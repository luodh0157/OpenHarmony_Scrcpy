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
OpenHarmony_Scrcpy 接口定义（Protocol）
"""

from typing import Protocol, Optional, List, Dict, Any, Callable
import numpy as np


class IHDCExecutor(Protocol):
    """HDC命令执行器接口"""
    
    device_sn: Optional[str]
    log_title: str
    hdc_path: str
    
    def execute(self, args: List[str], need_sn: bool = True, timeout: float = 5.0) -> Dict[str, Any]:
        """执行HDC命令"""
        ...
    
    def execute_async_in_shell(self, args: List[str], need_sn: bool = True, 
                                title: str = "Command Output", 
                                keep_open: bool = False) -> Optional[Any]:
        """异步执行HDC命令"""
        ...
    
    def set_device(self, device_sn: str) -> None:
        """设置设备"""
        ...
    
    def get_current_device(self) -> str:
        """获取当前设备"""
        ...
    
    def check_file_exists(self, remote_path: str) -> bool:
        """检查远程文件是否存在"""
        ...


class IServerManager(Protocol):
    """服务端管理器接口"""
    
    log_title: str
    manufacturer: str
    
    def install_server(self) -> bool:
        """安装服务端"""
        ...
    
    def start_server(self, port: int) -> bool:
        """启动服务端"""
        ...
    
    def stop(self) -> None:
        """停止服务端"""
        ...
    
    def is_installed(self) -> bool:
        """检查是否已安装"""
        ...
    
    def is_running(self) -> bool:
        """检查是否正在运行"""
        ...
    
    def update_manufacturer(self, manufacturer: str) -> None:
        """更新制造商信息"""
        ...


class IDeviceManager(Protocol):
    """设备管理器接口"""
    
    log_title: str
    hdc: IHDCExecutor
    
    def list_devices(self) -> List[Any]:
        """列出设备"""
        ...
    
    def select_device(self, device_sn: str) -> bool:
        """选择设备"""
        ...
    
    def get_current_device(self) -> Optional[str]:
        """获取当前设备"""
        ...
    
    def get_device_info(self, device_sn: str) -> Optional[Any]:
        """获取设备信息"""
        ...
    
    def add_port_forwarding(self, local_port: int, remote_port: int) -> bool:
        """添加端口转发"""
        ...
    
    def remove_port_forwarding(self, local_port: int, remote_port: int) -> bool:
        """移除端口转发"""
        ...
    
    def get_port_forwarding(self) -> int:
        """获取端口转发"""
        ...
    
    def reset_port_forwarding(self) -> None:
        """重置端口转发"""
        ...


class IVideoDecoder(Protocol):
    """视频解码器接口"""
    
    codec_name: str
    log_title: str
    decode_success: int
    decode_failure: int
    consecutive_errors: int
    waiting_for_keyframe: bool
    
    def is_ready(self) -> bool:
        """检查是否就绪"""
        ...
    
    def decode_frame(self, frame_data: bytes, is_keyframe: bool = False) -> Optional[np.ndarray]:
        """解码帧"""
        ...
    
    def set_vps(self, vps_data: bytes) -> bool:
        """设置VPS"""
        ...
    
    def set_sps(self, sps_data: bytes) -> bool:
        """设置SPS"""
        ...
    
    def set_pps(self, pps_data: bytes) -> bool:
        """设置PPS"""
        ...
    
    def cleanup(self) -> None:
        """清理资源"""
        ...


class IVideoStreamClient(Protocol):
    """视频流客户端接口"""
    
    is_connected: bool
    is_streaming: bool
    frame_count: int
    total_bytes: int
    decode_failure: int
    frame_queue: Any
    
    def connect(self, host: str, port: int, timeout: float = 5.0, 
                max_retries: int = 3, retry_interval: float = 1.0) -> bool:
        """连接服务器"""
        ...
    
    def disconnect(self) -> None:
        """断开连接"""
        ...
    
    def get_current_frame(self, timeout: float = 0.001) -> Optional[np.ndarray]:
        """获取当前帧"""
        ...


class IDeviceController(Protocol):
    """设备控制器接口"""
    
    log_title: str
    
    def set_display_resolution(self, width: int, height: int, ratio: float) -> None:
        """设置显示分辨率"""
        ...
    
    def handle_click(self, x: int, y: int) -> None:
        """处理点击"""
        ...
    
    def handle_drag(self, start_x: int, start_y: int, end_x: int, end_y: int) -> None:
        """处理拖动"""
        ...


__all__ = [
    "IHDCExecutor",
    "IServerManager",
    "IDeviceManager",
    "IVideoDecoder",
    "IVideoStreamClient",
    "IDeviceController",
]