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
OpenHarmony_Scrcpy 设备管理器
"""

from dataclasses import dataclass
from typing import Optional, List

from .constants import DEFAULT_PORT, LogLevel
from .logger import print_log
from .hdc_executor import HDCCommandExecutor


@dataclass
class DeviceInfo:
    """设备信息"""
    sn: str
    model: str = "Unknown Model"
    manufacturer: str = "default"
    
    def display_name(self) -> str:
        return f"{self.sn[:8]}****{self.sn[-8:]} ({self.model})"


class DeviceManager:
    """设备管理器"""
    
    def __init__(self, hdc_executor: HDCCommandExecutor) -> None:
        self.hdc = hdc_executor
        self.devices: List[DeviceInfo] = []
        self.current_device: Optional[DeviceInfo] = None
        self.port_forwarding = -1
        self.log_title = "设备管理器"
        
    def discover_devices(self) -> List[DeviceInfo]:
        """发现可用设备"""
        result = self.hdc.execute(["list", "targets"], False)
        if not result["success"]:
            return []
        
        devices = []
        lines = result["stdout"].strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            parts = line.split()
            if not parts:
                continue
            
            sn = parts[0].strip()
            if sn == "[Empty]":
                continue
            model = self.get_device_param(sn, "const.product.model")
            manufacturer = self.get_device_param(sn, "const.product.manufacturer")
            devices.append(DeviceInfo(sn=sn, model=model, manufacturer=manufacturer))
        
        self.devices = devices
        return devices
    
    def get_device_param(self, sn: str, param: str) -> str:
        """获取指定设备系统属性"""
        if not param:
            print_log(LogLevel.WARN, self.log_title, f"查询的系统属性不能为空")
            return ""
        
        cmd = ["-t", sn, "shell", "param", "get"]
        cmd.append(param)
        result = self.hdc.execute(cmd)
        if not result["success"]:
            print_log(LogLevel.ERROR, self.log_title, f"获取系统属性: [{param}] 失败")
            return ""
        ret = result["stdout"].strip()
        print_log(LogLevel.INFO, self.log_title, f"获取系统属性: [{param}], 结果: [{ret}]")
        return ret
    
    def select_device(self, sn: str) -> bool:
        """选择设备"""
        print_log(LogLevel.INFO, self.log_title, f"选择设备: [{sn}]")
        for device in self.devices:
            if device.sn == sn:
                self.current_device = device
                self.hdc.set_device(sn)
                return True
        return False
    
    def get_current_device(self) -> Optional[DeviceInfo]:
        """获取当前设备"""
        return self.current_device
    
    def reset_port_forwarding(self) -> None:
        self.port_forwarding = -1
    
    def get_port_forwarding(self) -> int:
        """获取空闲转发端口"""
        if not self.current_device:
            return -1
        
        if self.port_forwarding > 0:
            return self.port_forwarding
        
        result = self.hdc.execute(["fport", "ls"])
        if not result["success"]:
            print_log(LogLevel.ERROR, self.log_title, f"查询端口转发失败: {result.get('error', '未知错误')}")
            return -1
        
        output_result = result["stdout"]
        port = DEFAULT_PORT
        while port < 65535:
            if not str(port) in output_result:
                self.port_forwarding = port
                print_log(LogLevel.INFO, self.log_title, f"获取到可用转发端口: {port}")
                return port
            else:
                port = port + 1
                continue
        
        return -1
    
    def setup_port_forwarding(self, local_port: int, remote_port: int) -> bool:
        """设置端口转发"""
        if not self.current_device:
            return False
        
        result = self.hdc.execute(["fport", f"tcp:{local_port}", f"tcp:{remote_port}"])
        if not result["success"]:
            print_log(LogLevel.ERROR, self.log_title, f"添加端口转发失败: {result.get('error', '未知错误')}")
            return False
        
        print_log(LogLevel.INFO, self.log_title, f"添加端口转发成功: [{local_port}, {remote_port}]")
        return True
    
    def remove_port_forwarding(self, local_port: int, remote_port: int) -> bool:
        """移除端口转发"""
        if not self.current_device:
            return False
        
        result = self.hdc.execute(["fport", "rm", f"tcp:{local_port}", f"tcp:{remote_port}"])
        if not result["success"]:
            print_log(LogLevel.ERROR, self.log_title, f"移除端口转发失败: {result.get('error', '未知错误')}")
            return False
        
        print_log(LogLevel.INFO, self.log_title, f"移除端口转发转发成功: [{local_port}, {remote_port}]")
        return True
    
    def create_server_manager(self, manufacturer: str):
        """创建服务端管理器"""
        from .server_manager import ServerManager
        return ServerManager(manufacturer, self.hdc)
    
    def install_server(self, server_manager) -> bool:
        """安装服务端"""
        return server_manager.install_server()
    
    def uninstall_server(self, server_manager) -> bool:
        """卸载服务端"""
        return server_manager.uninstall_server()
    
    def start_server(self, server_manager, port: int) -> bool:
        """启动服务端"""
        return server_manager.start_server(port)
    
    def stop_server(self, server_manager) -> bool:
        """停止服务端"""
        return server_manager.stop_server()
        
    def check_server_installed(self, server_manager) -> bool:
        """检查服务端是否已安装"""
        return server_manager.check_server_installed()
        
    def check_server_running(self, server_manager) -> bool:
        """检查服务端是否在运行"""
        return server_manager.check_server_running()


__all__ = ["DeviceInfo", "DeviceManager"]