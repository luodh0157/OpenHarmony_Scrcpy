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
服务端部署器 - 负责服务端的安装、启动和部署状态管理
"""

import threading
import time
from typing import Optional, Callable

from core import LogLevel, print_log, ServerDeployState, DeviceManager


class ServerDeployer:
    """服务端部署器"""
    
    def __init__(
        self,
        device_manager: DeviceManager,
        on_deploy_finish: Optional[Callable[[bool, str], None]] = None,
    ) -> None:
        self.device_manager = device_manager
        self.on_deploy_finish = on_deploy_finish
        
        self._state = ServerDeployState.IDLE
        self._lock = threading.Lock()
        self._server_manager = None
        
        self.log_title = "服务端部署器"
    
    @property
    def state(self) -> ServerDeployState:
        with self._lock:
            return self._state
    
    def _set_state(self, state: ServerDeployState) -> None:
        with self._lock:
            self._state = state
    
    def get_server_manager(self):
        """获取服务端管理器"""
        return self._server_manager
    
    def deploy(self, selected_device_name: str, devices: list, update_running_status: Callable, ui_callback: Callable) -> None:
        """异步部署服务端
        
        Args:
            selected_device_name: 选中的设备显示名称
            devices: 设备列表
            update_running_status: 更新运行状态文本的函数
            ui_callback: 在主线程执行回调的函数，签名: (func) -> None，如 root.after(0, func)
        """
        threading.Thread(
            target=self._deploy_async,
            args=(selected_device_name, devices, update_running_status, ui_callback),
            daemon=True,
        ).start()
    
    def _deploy_async(self, selected_device_name: str, devices: list, update_running_status: Callable, ui_callback: Callable) -> None:
        """异步部署流程"""
        target_device = None
        for device in devices:
            if device.display_name() == selected_device_name:
                target_device = device
                break
        
        if not target_device or not self.device_manager.select_device(target_device.sn):
            ui_callback(lambda: self._report_finish(False, "设备选择失败"))
            return
        
        self._server_manager = self.device_manager.create_server_manager(target_device.manufacturer)
        
        update_running_status(f"[预安装] 正在获取可用转发端口，请稍等...")
        port = self.device_manager.get_port_forwarding()
        if port == -1:
            print_log(LogLevel.ERROR, self.log_title, f"获取可用转发端口失败！")
            ui_callback(lambda: self._report_finish(False, "获取可用转发端口失败！"))
            return
        
        update_running_status(f"[预安装] 正在安装服务端，请稍等...")
        print_log(LogLevel.INFO, self.log_title, f"检查服务端安装状态...")
        if not self.device_manager.check_server_installed(self._server_manager):
            print_log(LogLevel.INFO, self.log_title, f"服务端未安装，开始安装...")
            
            if not self.device_manager.install_server(self._server_manager):
                print_log(LogLevel.ERROR, self.log_title, f"服务端安装失败！")
                ui_callback(lambda: self._report_finish(False, "服务端安装失败！"))
                return
        else:
            print_log(LogLevel.INFO, self.log_title, f"服务端已安装")
        
        update_running_status(f"[预安装] 正在启动服务端，请稍等...")
        print_log(LogLevel.INFO, self.log_title, f"检查服务端运行状态...")
        if not self.device_manager.check_server_running(self._server_manager):
            print_log(LogLevel.INFO, self.log_title, f"启动服务端...")
            if not self.device_manager.start_server(self._server_manager, port):
                print_log(LogLevel.ERROR, self.log_title, f"服务端启动失败！")
                update_running_status(f"[预安装] 启动服务端失败！")
                ui_callback(lambda: self._report_finish(False, "服务端启动失败！"))
                return
            
            print_log(LogLevel.INFO, self.log_title, f"等待服务端就绪...")
            time.sleep(1)
        else:
            print_log(LogLevel.INFO, self.log_title, f"服务端已在运行")
        
        update_running_status(f"[预安装] 服务端已就绪，可随时点击[连接]开始投屏！")
        ui_callback(lambda: self._report_finish(True, ""))
    
    def _report_finish(self, success: bool, message: str) -> None:
        """报告部署完成"""
        if self.on_deploy_finish:
            self.on_deploy_finish(success, message)
    
    def stop(self) -> None:
        """停止服务端"""
        if self._server_manager:
            self._server_manager.stop_server()


__all__ = ["ServerDeployer"]
