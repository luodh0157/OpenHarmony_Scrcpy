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
OpenHarmony_Scrcpy 服务端管理器
"""

import sys
import os
import time
import subprocess
from typing import Optional

from .constants import LogLevel
from .logger import print_log, get_log_file
from .hdc_executor import HDCCommandExecutor


class ServerManager:
    """服务端管理器"""
    
    def __init__(self, manufacturer: str, hdc_executor: HDCCommandExecutor) -> None:
        self.hdc = hdc_executor
        self.server_process: Optional[subprocess.Popen] = None
        self.manufacturer = manufacturer
        self.log_title = "服务端管理器"
        
        self.server_exe_file = self._get_resource_path("ohscrcpy_server", manufacturer)
        self.server_cfg_file = self._get_resource_path("ohscrcpy_server.cfg")
    
    def _get_resource_path(self, filename: str, manufacturer: str = "default") -> str:
        """获取资源文件的正确路径（支持PyInstaller打包）"""
        try:
            if hasattr(sys, '_MEIPASS'):
                base_path = sys._MEIPASS
            else:
                # 开发环境 - 获取 Client 目录（父目录）
                current_dir = os.path.dirname(os.path.abspath(__file__))
                base_path = os.path.dirname(current_dir)  # 从 core/ 向上到 Client/
            
            if manufacturer != "default":
                manu_path = os.path.join(base_path, manufacturer)
                file_path = os.path.join(manu_path, filename)
                if os.path.exists(manu_path) and os.path.exists(file_path):
                    base_path = os.path.join(base_path, manufacturer)
            
            server_path = os.path.join(base_path, filename)
            print_log(LogLevel.DEBUG, self.log_title, f"待安装服务端可执行文件路径: {server_path}")
            return server_path
        except Exception as e:
            print_log(LogLevel.ERROR, self.log_title, f"获取资源路径失败: {e}")
            return filename
    
    def update_manufacturer(self, manufacturer: str) -> None:
        """更新设备制造商信息"""
        self.manufacturer = manufacturer
        self.server_exe_file = self._get_resource_path("ohscrcpy_server", manufacturer)
        self.server_cfg_file = self._get_resource_path("ohscrcpy_server.cfg")
    
    def install_server(self) -> bool:
        """安装服务端"""
        print_log(LogLevel.INFO, self.log_title, f"开始安装...")
        
        if not os.path.exists(self.server_exe_file):
            print_log(LogLevel.FATAL, self.log_title, f"错误: {self.server_exe_file} 文件不存在")
            return False
        
        if not os.path.exists(self.server_cfg_file):
            print_log(LogLevel.FATAL, self.log_title, f"错误: {self.server_cfg_file} 文件不存在")
            return False
        
        print_log(LogLevel.DEBUG, self.log_title, f"挂载系统为读写模式...")
        result = self.hdc.execute(["target", "mount"])
        if not result["success"]:
            print_log(LogLevel.ERROR, self.log_title, f"挂载失败: {result.get('stderr', '未知错误')}")
        
        print_log(LogLevel.DEBUG, self.log_title, f"推送可执行文件...")
        result = self.hdc.execute(["file", "send", self.server_exe_file, "/system/bin/"])
        if not result["success"]:
            print_log(LogLevel.ERROR, self.log_title, f"推送 ohscrcpy_server 失败: {result.get('stderr', '未知错误')}")
            return False
        
        print_log(LogLevel.DEBUG, self.log_title, f"设置可执行权限...")
        result = self.hdc.execute(["shell", "chmod", "+x", "/system/bin/ohscrcpy_server"])
        if not result["success"]:
            print_log(LogLevel.ERROR, self.log_title, f"设置可执行权限失败: {result.get('stderr', '未知错误')}")
            return False
        
        print_log(LogLevel.DEBUG, self.log_title, f"推送配置文件...")
        result = self.hdc.execute(["file", "send", self.server_cfg_file, "/system/etc/init/"])
        if not result["success"]:
            print_log(LogLevel.ERROR, self.log_title, f"推送 ohscrcpy_server.cfg 失败: {result.get('stderr', '未知错误')}")
            return False
        
        print_log(LogLevel.INFO, self.log_title, f"安装完成")
        return True

    def uninstall_server(self) -> bool:
        """卸载服务端"""
        print_log(LogLevel.INFO, self.log_title, f"开始卸载...")
        
        self.stop_server()
        
        result = self.hdc.execute(["shell", "rm", "-f", "/system/bin/ohscrcpy_server"])
        if not result["success"]:
            print_log(LogLevel.ERROR, self.log_title, f"删除 ohscrcpy_server 失败: {result.get('stderr', '未知错误')}")
        
        result = self.hdc.execute(["shell", "rm", "-f", "/system/etc/init/ohscrcpy_server.cfg"])
        if not result["success"]:
            print_log(LogLevel.ERROR, self.log_title, f"删除 ohscrcpy_server.cfg 失败: {result.get('stderr', '未知错误')}")
        
        print_log(LogLevel.INFO, self.log_title, f"卸载完成")
        return True
    
    def start_server(self, port: int) -> bool:
        """启动服务端"""
        self.prepare_server()
        print_log(LogLevel.INFO, self.log_title, f"开始启动...")
        
        device_sn = self.hdc.get_current_device()
        cmd_args = ["shell", "/system/bin/ohscrcpy_server", "-p", f"{port}"]
        
        if get_log_file() is not None:
            cmd_args.append("--log")
            print_log(LogLevel.DEBUG, self.log_title, "服务端日志落盘已使能")
        
        self.server_process = self.hdc.execute_async_in_shell(cmd_args, title=f"ohscrcpy_server {device_sn}")
        
        if self.server_process:
            print_log(LogLevel.INFO, self.log_title, f"启动命令已执行")
            need_print = True
            start_time = time.time()
            while time.time() - start_time < 5.0:
                if self.check_server_running(need_print):
                    print_log(LogLevel.INFO, self.log_title, f"启动成功")
                    return True
                need_print = False
                time.sleep(0.2)
            
            print_log(LogLevel.WARN, self.log_title, f"等待服务启动超时，可能启动失败")
            return False
        else:
            print_log(LogLevel.ERROR, self.log_title, f"启动失败")
            return False
    
    def stop_server(self) -> bool:
        """停止服务端"""
        print_log(LogLevel.INFO, self.log_title, f"开始停止...")
        
        if self.server_process:
            try:
                self.server_process.terminate()
                self.server_process.wait(timeout=1)
                print_log(LogLevel.INFO, self.log_title, f"服务进程已停止")
            except (OSError, subprocess.TimeoutExpired):
                try:
                    self.server_process.kill()
                except (OSError, subprocess.SubprocessError):
                    pass
            finally:
                self.server_process = None
        
        result = self.hdc.execute(["shell", "pkill", "-f", "ohscrcpy_server"])
        
        if not result["success"]:
            result = self.hdc.execute(["shell", "killall", "ohscrcpy_server"])
        
        self.hdc.stop_async_processes()
        print_log(LogLevel.INFO, self.log_title, f"停止完成")
        return True
    
    def check_server_installed(self) -> bool:
        """检查服务端是否已安装"""
        executable_exists = self.hdc.check_file_exists("/system/bin/ohscrcpy_server")
        config_exists = self.hdc.check_file_exists("/system/etc/init/ohscrcpy_server.cfg")
        
        if executable_exists and config_exists:
            print_log(LogLevel.INFO, self.log_title, f"服务已安装")
            return True
        
        print_log(LogLevel.INFO, self.log_title, f"服务未安装")
        return False
    
    def check_server_running(self, need_print: bool = True) -> bool:
        """检查服务端是否在运行"""
        result = self.hdc.execute(["shell", "pgrep", "-f", "ohscrcpy_server"])
        
        if result["success"] and result["stdout"]:
            pid = result["stdout"].strip()
            print_log(LogLevel.INFO, self.log_title, f"服务正在运行，PID: {pid}")
            return True
        else:
            if need_print:
                print_log(LogLevel.INFO, self.log_title, f"服务未运行")
            return False
    
    def prepare_server(self) -> bool:
        """准备服务端（唤醒设备等）"""
        print_log(LogLevel.DEBUG, self.log_title, f"准备环境...")
        
        print_log(LogLevel.INFO, self.log_title, f"唤醒设备...")
        result = self.hdc.execute(["shell", "power-shell", "wakeup"])
        if not result["success"]:
            print_log(LogLevel.ERROR, self.log_title, f"唤醒设备失败，继续执行...")
        
        unlock_args = ["shell", "uinput", "-T", "-m", str(350), str(1100), str(350), str(500), str(200)]
        result = self.hdc.execute(unlock_args)
        if not result["success"]:
            print_log(LogLevel.ERROR, self.log_title, f"解锁设备屏幕失败，继续执行...")
        
        print_log(LogLevel.INFO, self.log_title, f"设置屏幕常亮...")
        result = self.hdc.execute(["shell", "power-shell", "setmode", str(602)])
        result = self.hdc.execute(["shell", "power-shell", "timeout", "-o", str(86400000)])
        result = self.hdc.execute(["shell", "hidumper", "-s", str(3301), "-a", "-t"])
        if not result["success"]:
            print_log(LogLevel.ERROR, self.log_title, f"设置屏幕常亮失败，继续执行...")

        return True


__all__ = ["ServerManager"]