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
连接管理器 - 负责设备连接的生命周期管理
"""

import threading
import time
from typing import Optional, Callable, Any

from core import (
    HOST, HEARTBEAT_TIMEOUT, LogLevel, print_log,
    HDCCommandExecutor, DeviceManager,
)
from video import VideoStreamClient


class ConnectionState:
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"


class ConnectionManager:
    """连接管理器"""
    
    def __init__(
        self,
        device_manager: DeviceManager,
        hdc_executor: HDCCommandExecutor,
        on_frame_decoded: Callable,
        on_state_changed: Optional[Callable[[str], None]] = None,
        debug: bool = False,
    ) -> None:
        self.device_manager = device_manager
        self.hdc_executor = hdc_executor
        self.on_frame_decoded = on_frame_decoded
        self.on_state_changed = on_state_changed
        self.debug = debug
        
        self._state = ConnectionState.DISCONNECTED
        self._lock = threading.Lock()
        
        self.video_client: Optional[VideoStreamClient] = None
        self._server_manager = None
        self._forwarded_port: int = -1
        
        self.log_title = "连接管理器"
        
        self._init_video_client()
    
    def _init_video_client(self) -> None:
        """初始化视频流客户端"""
        self.video_client = VideoStreamClient(
            device_manager=self.device_manager,
            on_frame_decoded=self.on_frame_decoded,
            debug=self.debug,
        )
    
    @property
    def state(self) -> str:
        with self._lock:
            return self._state
    
    @property
    def is_connected(self) -> bool:
        return self.state == ConnectionState.CONNECTED
    
    def set_server_manager(self, server_manager) -> None:
        """设置或更新服务端管理器（复用已有实例）"""
        if self._server_manager is None:
            self._server_manager = server_manager
        else:
            # 复用已有实例，只更新 manufacturer
            self._server_manager.update_manufacturer(server_manager.manufacturer)
    
    def ensure_server_manager(self, manufacturer: str, hdc_executor: HDCCommandExecutor) -> None:
        """确保服务端管理器存在（复用或创建）"""
        if self._server_manager is None:
            from core.server_manager import ServerManager
            self._server_manager = ServerManager(manufacturer, hdc_executor)
        else:
            self._server_manager.update_manufacturer(manufacturer)
    
    def connect(self, port: int) -> bool:
        """同步连接设备（返回是否成功）"""
        self._set_state(ConnectionState.CONNECTING)
        
        try:
            print_log(LogLevel.DEBUG, self.log_title, f"连接视频流服务器...")
            if self.video_client.connect(HOST, port):
                self._forwarded_port = port
                self._set_state(ConnectionState.CONNECTED)
                print_log(LogLevel.INFO, self.log_title, f"连接成功")
                return True
            else:
                self._set_state(ConnectionState.DISCONNECTED)
                return False
        except Exception as e:
            print_log(LogLevel.ERROR, self.log_title, f"连接异常: {e}")
            self._set_state(ConnectionState.DISCONNECTED)
            return False
    
    def disconnect(self) -> None:
        """断开连接"""
        self._set_state(ConnectionState.DISCONNECTING)
        
        if self.video_client:
            self.video_client.disconnect()
        
        if self._server_manager:
            self._server_manager.stop_server()
        
        port = self._forwarded_port
        if port > 0:
            self.device_manager.remove_port_forwarding(port, port)
            self.device_manager.reset_port_forwarding()
            self._forwarded_port = -1
        
        self._set_state(ConnectionState.DISCONNECTED)
        print_log(LogLevel.INFO, self.log_title, f"断开连接已完成")
    
    def get_video_client(self) -> Optional[VideoStreamClient]:
        return self.video_client
    
    def get_server_manager(self):
        return self._server_manager
    
    def _set_state(self, state: str) -> None:
        with self._lock:
            self._state = state
        if self.on_state_changed:
            self.on_state_changed(state)


__all__ = ["ConnectionManager", "ConnectionState"]
