#!/usr/bin/env python
"""
OpenHarmony_Scrcpy 客户端
"""

import sys
import os
import platform
import subprocess
import socket
import threading
import queue
import time
import struct
import gc
import webbrowser
import traceback
import numpy as np
from enum import IntEnum, auto
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Tuple, Callable
import tkinter as tk
from tkinter import ttk, messagebox

# ==================== 常量定义 ====================
AUTHOR = "luodh0157"
PROJECT_URL = "https://gitcode.com/luodh0157/OpenHarmony_Scrcpy"
VERSION = "v1.5"
DEFAULT_PORT = 27183
HOST = "127.0.0.1"
HEARTBEAT_TIMEOUT = 5.0  # 心跳超时时间（秒）
HEARTBEAT_INTERVAL = 1.0  # 心跳发送间隔（秒）
PACKET_HEADER_SIZE = 8

# ==================== 数据包类型定义 ====================
class PacketType(IntEnum):
    PACKET_HEARTBEAT = 0
    PACKET_SPS = 1
    PACKET_PPS = 2
    PACKET_KEYFRAME = 3
    PACKET_FRAME = 4
    PACKET_CONFIG = 5

# ==================== 日志函数定义 ====================
class LogLevel(IntEnum):
    DEBUG = auto()
    INFO = auto()
    WARN = auto()
    ERROR = auto()
    FATAL = auto()

ENABLE_LOG_LEVEL = LogLevel.INFO

def print_log(level: LogLevel, title: str, content: str):
    if level >= ENABLE_LOG_LEVEL:
        print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}][{title}] {content}")

# ==================== 服务部署状态定义 ====================
class ServerDeployState(IntEnum):
    IDLE = auto()
    INSTALLING = auto()
    STARTING = auto()
    FINISHED = auto()

# ==================== 数据类定义 ====================
@dataclass
class DeviceInfo:
    """设备信息"""
    sn: str
    model: str = "Unknown Model"
    manufacturer: str = "default"
    
    def display_name(self) -> str:
        return f"{self.sn[:8]}****{self.sn[-8:]} ({self.model})"

@dataclass  
class VideoStreamConfig:
    """视频流配置"""
    width: int = 720
    height: int = 1280
    fps: int = 30
    bitrate: int = 1500000
    codec: str = "h264"

# ==================== HDC命令执行器 ====================
class HDCCommandExecutor:
    """HDC命令执行器"""
    
    def __init__(self, device_sn: Optional[str] = None):
        self.device_sn = device_sn
        self.hdc_path = self._find_hdc_path()
        self.async_processes = {}  # 存储异步进程
        self.log_title = "设备命令执行器"
    
    def _find_hdc_path(self) -> str:
        """查找hdc工具路径"""
        possible_paths = ["hdc", "hdc.exe", "/usr/bin/hdc", "/usr/local/bin/hdc"]
        
        for path in possible_paths:
            try:
                subprocess.run([path, "--version"], 
                             capture_output=True, 
                             text=True,
                             timeout=2,
                             check=False)
                return path
            except:
                continue
        
        return "hdc"
    
    def assemble_command(self, args: List[str], need_sn: bool = True) -> str:
        cmd = [self.hdc_path]
        
        if need_sn and self.device_sn:
            cmd.extend(["-t", self.device_sn])
        
        cmd.extend(args)
        return cmd
    
    def execute(self, args: List[str], need_sn: bool = True, timeout: float = 5.0) -> Dict[str, Any]:
        """执行hdc命令"""
        cmd = self.assemble_command(args, need_sn)
        cmd_str = " ".join(cmd)
        print_log(LogLevel.DEBUG, self.log_title, f"同步执行: [{cmd_str}]")
        
        try:
            process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='ignore'
            )
            
            try:
                stdout, stderr = process.communicate(timeout=timeout)
                return {
                    "success": process.returncode == 0,
                    "stdout": stdout.strip(),
                    "stderr": stderr.strip(),
                    "returncode": process.returncode
                }
            except subprocess.TimeoutExpired:
                process.kill()
                return {"success": False, "error": "命令执行超时"}
                
        except FileNotFoundError:
            return {"success": False, "error": f"hdc工具未找到: {self.hdc_path}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def execute_async_in_process(self, args: List[str], need_sn: bool = True) -> Optional[subprocess.Popen]:
        """新开进程异步执行hdc命令（用于启动持续运行的服务），无法查看日志，启动较快"""
        cmd = self.assemble_command(args, need_sn)
        cmd_str = " ".join(cmd)
        print_log(LogLevel.DEBUG, self.log_title, f"异步进程执行: [{cmd_str}]")
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='ignore'
            )
            
            # 保存进程引用，以便后续管理
            process_id = len(self.async_processes)
            self.async_processes[process_id] = process
            
            # 启动一个线程来异步触发命令执行
            threading.Thread(
                target=self._trigger_async_process,
                args=(process_id, process),
                daemon=True
            ).start()
            
            return process
        except Exception as e:
            print_log(LogLevel.ERROR, self.log_title, f"异步执行命令失败: {e}")
            return None
    
    def _trigger_async_process(self, process_id: int, process: subprocess.Popen):
        """监控异步进程的输出"""
        try:
            stdout, stderr = process.communicate()
            print_log(LogLevel.DEBUG, self.log_title, f"[异步进程 {process_id}] 输出: \n{stdout}")
            if stderr:
                print_log(LogLevel.ERROR, self.log_title, f"[异步进程 {process_id}] 错误: {stderr}")
        except Exception as e:
            print_log(LogLevel.ERROR, self.log_title, f"[异步进程 {process_id}] 监控异常: {e}")
        finally:
            # 移除已结束的进程
            if process_id in self.async_processes:
                del self.async_processes[process_id]
    
    def stop_async_processes(self):
        """停止所有异步进程"""
        for process_id, process in list(self.async_processes.items()):
            try:
                process.terminate()
                process.wait(timeout=1)
            except:
                try:
                    process.kill()
                except:
                    pass
            finally:
                if process_id in self.async_processes:
                    del self.async_processes[process_id]
    
    def execute_async_in_shell(self, args: List[str], need_sn: bool = True, title="Command Output", keep_open=False) -> Optional[subprocess.Popen]:
        """新开终端窗口异步执行hdc命令（用于启动持续运行的服务），可以查看日志，启动较慢"""
        command = " ".join(self.assemble_command(args, need_sn))
        
        system = platform.system()
        if system == "Windows":
            # Windows平台
            if keep_open:
                cmd = f'start "{title}" cmd /k "{command}"'
            else:
                cmd = f'start "{title}" cmd /c "{command}"'
            
            process = subprocess.Popen(cmd, shell=True)
            
        elif system == "Linux" or system == "Darwin":
            # Linux/macOS平台
            
            # 获取默认终端
            terminal = _get_default_shell_terminal()
            
            # 构建终端命令
            if keep_open:
                cmd = f"{command}; echo 'Press Enter to exit...'; read"
            else:
                cmd = command
                
            if terminal == "gnome-terminal":
                cmd = " ".join(["gnome-terminal", "--title", title, "--", "bash", "-c", cmd])
                process = subprocess.Popen(cmd)
            elif terminal == "konsole":
                cmd = " ".join(["konsole", "--title", title, "-e", "bash", "-c", cmd])
                process = subprocess.Popen(cmd)
            elif terminal == "xterm":
                cmd = " ".join(["xterm", "-title", title, "-e", f"bash -c '{terminal_cmd}'"])
                process = subprocess.Popen(cmd)
            elif terminal == "terminator":
                cmd = " ".join(["terminator", "-T", title, "-e", f"bash -c '{cmd}'"])
                process = subprocess.Popen(cmd)
            elif terminal == "osascript":  # macOS使用AppleScript
                applescript = f'''
                tell application "Terminal"
                    do script "{command}"
                    activate
                end tell
                '''
                cmd = " ".join(["osascript", "-e", applescript])
                process = subprocess.Popen()
            else:
                # 尝试通用方式
                term_cmd = os.environ.get('TERMINAL', 'xterm')
                cmd = " ".join([term_cmd, "-e", f"bash -c '{cmd}'"])
                process = subprocess.Popen()
        else:
            print_log(LogLevel.FATAL, self.log_title, f"异步Shell执行: Unsupported platform [{system}]")
            process = None
        
        
        print_log(LogLevel.DEBUG, self.log_title, f"异步Shell执行: [{cmd}]")
        # 保存进程引用，以便后续管理
        if process: 
            process_id = len(self.async_processes)
            self.async_processes[process_id] = process
        return process

    def _get_default_shell_terminal():
        """获取类Linux系统默认终端"""
        system = platform.system()
        
        if system == "Darwin":  # macOS
            return "osascript"
        
        # Linux系统检测可用终端
        terminals = [
            "gnome-terminal",  # GNOME
            "konsole",         # KDE
            "terminator",      # Terminator
            "xfce4-terminal",  # XFCE
            "mate-terminal",   # MATE
            "lxterminal",      # LXDE
            "xterm"            # 最基础的X终端
        ]
        
        for term in terminals:
            if subprocess.run(["which", term], capture_output=True).returncode == 0:
                return term
        
        return "xterm"  # 默认
    
    def set_device(self, device_sn: str) -> None:
        """设置当前设备"""
        self.device_sn = device_sn
    
    def get_current_device(self) -> str:
        """获取当前设备"""
        return self.device_sn
    
    def get_hdc_info(self) -> Dict[str, Any]:
        """获取HDC信息"""
        return self.execute(["--version"], timeout=2.0)
    
    def check_file_exists(self, remote_path: str) -> bool:
        """检查远程文件是否存在"""
        result = self.execute(["shell", "ls", remote_path])
        return result["success"] and "No such file or directory" not in result["stdout"]

# ==================== 服务端管理器 ====================
class ServerManager:
    """服务端管理器"""
    
    def __init__(self, manufacturer: str, hdc_executor: HDCCommandExecutor):
        self.hdc = hdc_executor
        self.server_process = None
        self.manufacturer = manufacturer
        self.log_title = "服务端管理器"
        
        # 获取资源文件的正确路径
        self.server_exe_file = self._get_resource_path("ohscrcpy_server", manufacturer)
        self.server_cfg_file = self._get_resource_path("ohscrcpy_server.cfg")
    
    def _get_resource_path(self, filename: str, manufacturer: str = "default"):
        """获取资源文件的正确路径（支持PyInstaller打包）"""
        try:
            # PyInstaller打包后
            if hasattr(sys, '_MEIPASS'):
                base_path = sys._MEIPASS
            else:
                # 开发环境
                base_path = os.path.dirname(os.path.abspath(__file__))
            
            if manufacturer != "default":
                base_path += os.sep + manufacturer + os.sep
            server_path = os.path.join(base_path, filename)
            print_log(LogLevel.DEBUG, self.log_title, f"待安装服务端可执行文件路径: {server_path}")
            return server_path
        except Exception as e:
            print_log(LogLevel.ERROR, self.log_title, f"获取资源路径失败: {e}")
            return filename  # 回退到原始相对路径
    
    def update_manufacturer(self, manufacturer: str):
        """更新设备制造商信息"""
        self.manufacturer = manufacturer
        # 获取资源文件的正确路径
        self.server_exe_file = self._get_resource_path("ohscrcpy_server", manufacturer)
        self.server_cfg_file = self._get_resource_path("ohscrcpy_server.cfg")
    
    def install_server(self) -> bool:
        """安装服务端"""
        print_log(LogLevel.INFO, self.log_title, f"开始安装...")
        
        # 1. 检查文件是否存在
        if not os.path.exists(self.server_exe_file):
            print_log(LogLevel.FATAL, self.log_title, f"错误: {self.server_exe_file} 文件不存在")
            return False
        
        if not os.path.exists(self.server_cfg_file):
            print_log(LogLevel.FATAL, self.log_title, f"错误: {self.server_cfg_file} 文件不存在")
            return False
        
        # 2. 重新挂载系统为读写模式
        print_log(LogLevel.DEBUG, self.log_title, f"挂载系统为读写模式...")
        result = self.hdc.execute(["target", "mount"])
        if not result["success"]:
            print_log(LogLevel.ERROR, self.log_title, f"挂载失败: {result.get('stderr', '未知错误')}")
        
        # 3. 推送可执行文件
        print_log(LogLevel.DEBUG, self.log_title, f"推送可执行文件...")
        result = self.hdc.execute(["file", "send", self.server_exe_file, "/system/bin/"])
        if not result["success"]:
            print_log(LogLevel.ERROR, self.log_title, f"推送 ohscrcpy_server 失败: {result.get('stderr', '未知错误')}")
            return False
        
        # 4. 设置可执行权限
        print_log(LogLevel.DEBUG, self.log_title, f"设置可执行权限...")
        result = self.hdc.execute(["shell", "chmod", "+x", "/system/bin/ohscrcpy_server"])
        if not result["success"]:
            print_log(LogLevel.ERROR, self.log_title, f"设置可执行权限失败: {result.get('stderr', '未知错误')}")
            return False
        
        # 5. 推送配置文件
        print_log(LogLevel.DEBUG, self.log_title, f"推送配置文件...")
        result = self.hdc.execute(["file", "send", self.server_cfg_file, "/system/etc/init/"])
        if not result["success"]:
            print_log(LogLevel.ERROR, self.log_title, f"推送 ohscrcpy_server.cfg 失败: {result.get('stderr', '未知错误')}")
            return False
        
        # 6. 准备设备环境
        self.prepare_server()
        
        print_log(LogLevel.INFO, self.log_title, f"安装完成")
        return True

    def uninstall_server(self) -> bool:
        """卸载服务端"""
        print_log(LogLevel.INFO, self.log_title, f"开始卸载...")
        
        # 停止运行的服务
        self.stop_server()
        
        # 1. 删除可执行文件
        result = self.hdc.execute(["shell", "rm", "-f", "/system/bin/ohscrcpy_server"])
        if not result["success"]:
            print_log(LogLevel.ERROR, self.log_title, f"删除 ohscrcpy_server 失败: {result.get('stderr', '未知错误')}")
        
        # 2. 删除配置文件
        result = self.hdc.execute(["shell", "rm", "-f", "/system/etc/init/ohscrcpy_server.cfg"])
        if not result["success"]:
            print_log(LogLevel.ERROR, self.log_title, f"删除 ohscrcpy_server.cfg 失败: {result.get('stderr', '未知错误')}")
        
        print_log(LogLevel.INFO, self.log_title, f"卸载完成")
        return True
    
    def start_server(self, port: int) -> bool:
        """启动服务端"""
        print_log(LogLevel.INFO, self.log_title, f"开始启动...")
        
        # 启动服务（异步执行）
        device_sn = self.hdc.get_current_device()
        #self.server_process = self.hdc.execute_async_in_process(["shell", "/system/bin/ohscrcpy_server", "-p", f"{port}"])
        self.server_process = self.hdc.execute_async_in_shell(["shell", "/system/bin/ohscrcpy_server", "-p", f"{port}"], title = f"ohscrcpy_server {device_sn}")
        
        if self.server_process:
            print_log(LogLevel.INFO, self.log_title, f"启动命令已执行")
            # 等待片刻检查服务是否启动成功
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
        
        # 停止本地异步进程
        if self.server_process:
            try:
                self.server_process.terminate()
                self.server_process.wait(timeout=1)
                print_log(LogLevel.INFO, self.log_title, f"服务进程已停止")
            except:
                try:
                    self.server_process.kill()
                except:
                    pass
            finally:
                self.server_process = None
        
        # 在设备上终止服务进程
        result = self.hdc.execute(["shell", "pkill", "-f", "ohscrcpy_server"])
        
        # 如果pkill失败，尝试使用killall
        if not result["success"]:
            result = self.hdc.execute(["shell", "killall", "ohscrcpy_server"])
        
        self.hdc.stop_async_processes()
        print_log(LogLevel.INFO, self.log_title, f"停止完成")
        return True
    
    def check_server_installed(self) -> bool:
        """检查服务端是否已安装"""
        # 检查可执行文件
        executable_exists = self.hdc.check_file_exists("/system/bin/ohscrcpy_server")
        
        # 检查配置文件
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
        
        # 1. 唤醒设备
        print_log(LogLevel.INFO, self.log_title, f"唤醒设备...")
        result = self.hdc.execute(["shell", "power-shell", "wakeup"])
        if not result["success"]:
            print_log(LogLevel.ERROR, self.log_title, f"唤醒设备失败，继续执行...")
        
        # 2. 解锁屏幕
        unlock_args = ["shell", "uinput", "-T", "-m", str(350), str(1100), str(350), str(500), str(200)]
        result = self.hdc.execute(unlock_args)
        if not result["success"]:
            print_log(LogLevel.ERROR, self.log_title, f"解锁设备屏幕失败，继续执行...")
        
        # 3. 设置显示模式
        print_log(LogLevel.INFO, self.log_title, f"设置屏幕常亮...")
        result = self.hdc.execute(["shell", "power-shell", "setmode", "602"])
        if not result["success"]:
            print_log(LogLevel.ERROR, self.log_title, f"设置屏幕常亮失败，继续执行...")
        
        return True

# ==================== 设备管理器 ====================
class DeviceManager:
    """设备管理器"""
    
    def __init__(self, hdc_executor: HDCCommandExecutor):
        self.hdc = hdc_executor
        self.devices: List[DeviceInfo] = []
        self.current_device: Optional[DeviceInfo] = None
        self.server_manager: Optional[ServerManager] = None
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
            devices.append(DeviceInfo(sn=sn, model=model,manufacturer=manufacturer))
        
        self.devices = devices
        if devices:
            self.current_device = devices[0]
            self.hdc.set_device(devices[0].sn)
            self.server_manager = ServerManager(devices[0].manufacturer, self.hdc)
        
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
        for device in self.devices:
            if device.sn == sn:
                self.current_device = device
                self.hdc.set_device(sn)
                if self.server_manager:
                    self.server_manager.update_manufacturer(device.manufacturer)
                return True
        return False
    
    def get_current_device(self) -> Optional[DeviceInfo]:
        """获取当前设备"""
        return self.current_device
    
    def reset_port_forwarding(self):
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
    
    def install_server(self) -> bool:
        """安装服务端"""
        if not self.server_manager:
            return False
        return self.server_manager.install_server()
    
    def uninstall_server(self) -> bool:
        """卸载服务端"""
        if not self.server_manager:
            return False
        return self.server_manager.uninstall_server()
    
    def start_server(self, port: int) -> bool:
        """启动服务端"""
        if not self.server_manager:
            return False
        return self.server_manager.start_server(port)
    
    def stop_server(self) -> bool:
        """停止服务端"""
        if not self.server_manager:
            return False
        return self.server_manager.stop_server()
        
    def check_server_installed(self) -> bool:
        """检查服务端是否已安装"""
        if not self.server_manager:
            return False
        return self.server_manager.check_server_installed()
        
    def check_server_running(self) -> bool:
        """检查服务端是否在运行"""
        if not self.server_manager:
            return False
        return self.server_manager.check_server_running()

# ==================== H.264解码器 ====================
class H264Decoder:
    """H.264解码器"""
    
    def __init__(self, config: VideoStreamConfig, debug: bool = False):
        self.config = config
        self.debug = debug
        self.log_title = "解码器"
        
        # 解码器上下文
        self.codec_ctx = None
        
        # SPS/PPS数据
        self.sps_data = None
        self.pps_data = None
        self.extradata = bytearray()
        
        # 解码状态
        self.frame_count = 0
        self.decode_success = 0
        self.decode_failure = 0
        self.last_decode_time = 0
        
        # 错误计数器
        self.consecutive_errors = 0
        self.max_consecutive_errors = 50
        
        print_log(LogLevel.INFO, self.log_title, f"创建解码器实例: {config.width}x{config.height}")

    def _init_codec(self):
        """初始化解码器"""
        try:
            # 释放现有解码器
            if self.codec_ctx is not None:
                self.codec_ctx = None
            
            # 创建解码器上下文
            import av
            self.codec_ctx = av.CodecContext.create('h264', 'r')
            
            # 设置解码器参数
            self.codec_ctx.width = self.config.width
            self.codec_ctx.height = self.config.height
            self.codec_ctx.pix_fmt = 'rgba'
            
            # 如果有extradata，设置它
            if self.extradata:
                try:
                    self.codec_ctx.extradata = self.extradata
                    print_log(LogLevel.DEBUG, self.log_title, f"设置extradata: {len(self.extradata)}字节")
                except Exception as e:
                    print_log(LogLevel.ERROR, self.log_title, f"设置extradata失败: {e}")
            
            print_log(LogLevel.INFO, self.log_title, f"CodecContext初始化成功")
            return True
            
        except Exception as e:
            print_log(LogLevel.ERROR, self.log_title, f"初始化失败: {e}")
            traceback.print_exc()
            return False

    def set_sps_pps(self, sps_data: bytes, pps_data: bytes):
        """设置SPS和PPS数据"""
        if not sps_data or not pps_data:
            return False
        
        self.sps_data = sps_data
        self.pps_data = pps_data
        
        # 创建AnnexB格式的extradata
        try:
            # 构建AnnexB格式的extradata：起始码 + SPS + 起始码 + PPS
            # 添加SPS
            if not self._has_start_code(self.sps_data):
                self.extradata.extend(b'\x00\x00\x00\x01')
            self.extradata.extend(self.sps_data)
            
            # 添加PPS
            if not self._has_start_code(self.pps_data):
                self.extradata.extend(b'\x00\x00\x00\x01')
            self.extradata.extend(self.pps_data)
            print_log(LogLevel.DEBUG, self.log_title, f"创建extradata: SPS={len(sps_data)}字节, PPS={len(pps_data)}字节")
            
            # 重新初始化解码器
            return self._init_codec()
                
        except Exception as e:
            print_log(LogLevel.ERROR, self.log_title, f"创建extradata失败: {e}")
            return False

    def _has_start_code(self, data: bytes) -> bool:
        """检查是否有起始码"""
        if len(data) < 4:
            return False
        return data[0:4] == b'\x00\x00\x00\x01' or data[0:3] == b'\x00\x00\x01'

    def decode_frame(self, frame_data: bytes, is_keyframe: bool = False) -> Optional[np.ndarray]:
        """解码视频帧"""
        if not frame_data or len(frame_data) == 0:
            print_log(LogLevel.WARN, self.log_title, f"空帧数据")
            return None
        
        # 如果没有解码器上下文，尝试初始化
        if self.codec_ctx is None:
            if not self._init_codec():
                return None
        
        self.frame_count += 1
        current_time = time.time()
        
        try:
            # 确保数据有起始码
            if not self._has_start_code(frame_data):
                frame_data = b'\x00\x00\x00\x01' + frame_data
            
            # 如果是关键帧且还没有extradata，尝试重新初始化
            if is_keyframe and self.extradata and self.codec_ctx.extradata != self.extradata:
                try:
                    self.codec_ctx.extradata = self.extradata
                    print_log(LogLevel.INFO, self.log_title, f"关键帧中重新设置extradata")
                except:
                    pass
            
            # 解析数据包
            try:
                import av
                packets = self.codec_ctx.parse(frame_data)
                if len(packets) == 0:
                    packets = self.codec_ctx.parse(frame_data)
            except Exception as parse_error:
                print_log(LogLevel.ERROR, self.log_title, f"解析数据失败: {parse_error}")
                self.consecutive_errors += 1
                return None
            
            # 解码数据包
            decoded_frame = None
            for packet in packets:
                if packet is not None:
                    try:
                        frames = self.codec_ctx.decode(packet)
                        
                        for frame in frames:
                            if isinstance(frame, av.VideoFrame):
                                # 使用正确的颜色空间转换
                                rgb_array = frame.to_ndarray(format='rgb24')
                                
                                if rgb_array is not None:
                                    self.decode_success += 1
                                    self.consecutive_errors = 0
                                    self.last_decode_time = current_time
                                    decoded_frame = rgb_array
                                    break
                    except Exception as decode_error:
                        print_log(LogLevel.ERROR, self.log_title, f"解码数据包失败: {decode_error}")
                        self.consecutive_errors += 1
            
            if decoded_frame is not None:
                return decoded_frame
            else:
                self.decode_failure += 1
                
                # 如果连续解码失败，重置解码器
                if self.consecutive_errors >= self.max_consecutive_errors:
                    print_log(LogLevel.ERROR, self.log_title, f"连续解码失败 {self.consecutive_errors} 次，重置解码器")
                    self._init_codec()
                    self.consecutive_errors = 0
                return None
            
        except Exception as e:
            print_log(LogLevel.ERROR, self.log_title, f"解码失败: {e}")
            self.decode_failure += 1
            self.consecutive_errors += 1
            return None
    
    def cleanup(self):
        """清理解码器资源"""
        print_log(LogLevel.INFO, self.log_title, f"清理资源...")
        self.codec_ctx = None
        self.sps_data = None
        self.pps_data = None
        self.extradata = None

# ==================== 视频流客户端 ====================
class VideoStreamClient:
    """视频流客户端 - 优化数据包处理"""
    
    def __init__(self, device_manager: DeviceManager, on_frame_decoded: Optional[Callable] = None, debug: bool = False):
        self.socket = None
        self.is_connected = False
        self.is_streaming = False
        self.config = VideoStreamConfig()
        self.device_manager = device_manager
        
        # 解码器
        self.decoder = None
        self.sps_received = False
        self.pps_received = False
        self.sps_data = None
        self.pps_data = None
        
        # 数据队列 - 使用线程安全队列
        self.frame_queue = queue.Queue(maxsize=50)
        
        # 回调函数
        self.on_frame_decoded = on_frame_decoded
        
        # 统计信息
        self.frame_count = 0
        self.total_bytes = 0
        self.last_data_time = 0
        self.last_heartbeat_time = 0
        self.last_frame_time = 0
        self.last_print_frame_count = 0
        
        # 接收缓冲区
        self.recv_buffer = bytearray()
        
        # 线程控制
        self._stop_event = threading.Event()
        
        # 心跳相关
        self.heartbeat_thread = None
        self.monitor_thread = None
        
        # 性能监控
        self.fps_counter = 0
        self.last_fps_check = time.time()
        
        # 包处理统计
        self.packet_count = 0
        self.bad_packet_bytes = 0
        
        # 调试
        self.debug = debug
        self.log_title = "视频客户端"
        print_log(LogLevel.INFO, self.log_title, f"初始化完成")

    def connect(self, host: str, port: int, timeout: float = 5.0) -> bool:
        """连接视频流服务器"""
        try:
            print_log(LogLevel.INFO, self.log_title, f"连接服务器 {host}:{port}...")
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(timeout)
            
            # 设置socket选项
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            
            self.socket.connect((host, port))
            print_log(LogLevel.INFO, self.log_title, f"TCP连接成功，等待服务端配置...")
            
            # 接收配置信息
            if self._receive_config():
                print_log(LogLevel.INFO, self.log_title, f"配置接收成功: {self.config.width}x{self.config.height}@{self.config.fps}fps")
                self.is_connected = True
                
                # 记录初始时间
                self.last_data_time = time.time()
                self.last_heartbeat_time = time.time()
                self.last_frame_time = time.time()
                
                # 创建解码器（但不立即初始化）
                self.decoder = H264Decoder(self.config, debug=self.debug)
                
                # 重置SPS/PPS状态
                self.sps_received = False
                self.pps_received = False
                self.sps_data = None
                self.pps_data = None
                
                # 启动工作线程
                self._start_workers()
                print_log(LogLevel.INFO, self.log_title, f"连接成功")
                return True
            
        except Exception as e:
            print_log(LogLevel.ERROR, self.log_title, f"连接失败: {e}")
            traceback.print_exc()
        
        self.disconnect()
        return False

    def _receive_config(self) -> bool:
        """接收服务器配置信息"""
        try:
            if not self.socket:
                return False
            
            self.socket.settimeout(5.0)
            
            # 接收配置信息
            buffer = b""
            start_time = time.time()
            
            while time.time() - start_time < 5.0:
                try:
                    chunk = self.socket.recv(1024)
                    if not chunk:
                        continue
                    
                    buffer += chunk
                    
                    if b'\n' in buffer:
                        config_line, remaining = buffer.split(b'\n', 1)
                        config_str = config_line.decode('utf-8', errors='ignore').strip()
                        
                        if config_str.startswith("SCREEN_INFO:"):
                            print_log(LogLevel.DEBUG, self.log_title, f"接收到配置: [{config_str}]")
                            parts = config_str.split(':')
                            if len(parts) >= 6:
                                self.config.width = int(parts[1])
                                self.config.height = int(parts[2])
                                self.config.fps = int(parts[3])
                                self.config.bitrate = int(parts[4])
                                self.config.codec = parts[5] if len(parts) > 5 else "h264"
                                print_log(LogLevel.INFO, self.log_title, f"解析配置:"
                                      f" {self.config.width}x{self.config.height}@{self.config.fps}fps"
                                      f" bitrate:{self.config.bitrate} codec:{self.config.codec}")
                                
                                # 发送配置确认应答
                                ack_msg ="CONFIG_ACK\n"
                                self.socket.sendall(ack_msg.encode())
                                
                                # 设置剩余数据为缓冲区
                                self.recv_buffer = bytearray(remaining)
                                return True
                        
                        break
                    
                except socket.timeout:
                    continue
            
            print_log(LogLevel.ERROR, self.log_title, f"等待接收配置超时！")
            return False
            
        except Exception as e:
            print_log(LogLevel.ERROR, self.log_title, f"接收配置失败: {e}")
            return False

    def _start_workers(self):
        """启动工作线程"""
        self._stop_event.clear()
        self.is_streaming = True
        
        # 接收线程
        recv_thread = threading.Thread(target=self._receive_thread_func, daemon=True)
        recv_thread.start()
        
        # 处理线程
        process_thread = threading.Thread(target=self._process_thread_func, daemon=True)
        process_thread.start()
        
        # 心跳线程
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_thread_func, daemon=True)
        self.heartbeat_thread.start()
        
        # 监控线程（检查超时）
        self.monitor_thread = threading.Thread(target=self._monitor_thread_func, daemon=True)
        self.monitor_thread.start()
        
        print_log(LogLevel.INFO, self.log_title, f"工作线程已启动")

    def _heartbeat_thread_func(self):
        """心跳线程"""
        print_log(LogLevel.INFO, self.log_title, f"心跳线程启动")
        
        while not self._stop_event.is_set() and self.is_connected:
            try:
                # 发送心跳包
                if self.socket:
                    heartbeat_packet = struct.pack('>II', PacketType.PACKET_HEARTBEAT, 0)
                    self.socket.sendall(heartbeat_packet)
                    if self.debug:
                        print_log(LogLevel.DEBUG, self.log_title, f"发送心跳包")
                
                # 等待下一次心跳
                for _ in range(int(HEARTBEAT_INTERVAL * 10)):
                    if self._stop_event.is_set():
                        break
                    time.sleep(0.5)
                    
            except Exception as e:
                if not self._stop_event.is_set():
                    print_log(LogLevel.WARN, self.log_title, f"心跳发送失败: {e}")
                break
        
        print_log(LogLevel.INFO, self.log_title, f"心跳线程结束")

    def _monitor_thread_func(self):
        """监控线程，检查超时"""
        print_log(LogLevel.INFO, self.log_title, f"监控线程启动")
        
        while not self._stop_event.is_set() and self.is_connected:
            try:
                # 检查心跳超时
                current_time = time.time()
                time_since_last_data = current_time - self.last_data_time
                
                if time_since_last_data > HEARTBEAT_TIMEOUT:
                    print_log(LogLevel.ERROR, self.log_title, f"心跳超时 ({time_since_last_data:.1f}秒)，断开连接")
                    self.disconnect()
                    break
                
                # 检查是否长时间没有收到帧
                time_since_last_frame = current_time - self.last_frame_time
                if self.debug and time_since_last_frame > 10.0 and self.frame_count > 0:
                    print_log(LogLevel.WARN, self.log_title, f"警告: {time_since_last_frame:.1f}秒无新帧")
                
                # 每1秒检查一次
                time.sleep(1)
                    
            except Exception as e:
                if not self._stop_event.is_set():
                    print_log(LogLevel.ERROR, self.log_title, f"监控线程异常: {e}")
        
        print_log(LogLevel.INFO, self.log_title, f"监控线程结束")

    def _receive_thread_func(self):
        """接收线程"""
        print_log(LogLevel.INFO, self.log_title, f"接收线程启动")
        
        self.recv_buffer = bytearray()
        self.last_data_time = time.time()
        
        try:
            while not self._stop_event.is_set() and self.socket and self.is_connected:
                try:
                    self.socket.settimeout(0.1)
                    data = self.socket.recv(1024 * 1024)
                    
                    if not data:
                        continue
                    
                    self.last_data_time = time.time()
                    self.total_bytes += len(data)
                    
                    # 添加到缓冲区
                    self.recv_buffer.extend(data)
                    
                    # 立即处理数据
                    self._process_received_data()
                    
                except socket.timeout:
                    continue
                except (ConnectionResetError, ConnectionAbortedError):
                    print_log(LogLevel.ERROR, self.log_title, f"连接被重置")
                    break
                except Exception as e:
                    if not self._stop_event.is_set():
                        print_log(LogLevel.ERROR, self.log_title, f"接收数据异常: {e}")
                    break
        finally:
            self.is_streaming = False
            print_log(LogLevel.INFO, self.log_title, f"接收线程结束")
    
    def _process_received_data(self):
        """处理接收到的数据"""
        processed_count = 0
        max_process_per_cycle = 100

        while len(self.recv_buffer) >= PACKET_HEADER_SIZE and processed_count < max_process_per_cycle:
            try:
                # 1. 尝试读取包头
                packet_type = struct.unpack('>I', self.recv_buffer[0:4])[0]
                data_len = struct.unpack('>I', self.recv_buffer[4:8])[0]

                # 2. 验证包头有效性
                valid_types = [PacketType.PACKET_HEARTBEAT, PacketType.PACKET_SPS, PacketType.PACKET_PPS,
                               PacketType.PACKET_KEYFRAME, PacketType.PACKET_FRAME, PacketType.PACKET_CONFIG]
                if packet_type not in valid_types:
                    # 严重错误，丢弃第一个字节，尝试重新寻找同步点
                    del self.recv_buffer[0:1]
                    self.bad_packet_bytes += 1
                    continue  # 跳出本次循环，重新尝试
                
                if self.bad_packet_bytes > 0:
                    print_log(LogLevel.WARN, self.log_title, f"错误: 无效包类型, 重新同步(丢弃 {self.bad_packet_bytes} 字节坏数据...)")
                    self.bad_packet_bytes = 0
                
                # 3. 检查数据长度是否在合理范围内
                MAX_ALLOWED_SIZE = 10 * 1024 * 1024  # 10MB
                if data_len < 0 or data_len > MAX_ALLOWED_SIZE:
                    print_log(LogLevel.WARN, self.log_title, f"错误: 异常数据长度 {data_len}，包类型={packet_type}，尝试重新同步...")
                    # 遇到异常长度，说明彻底失步了，不能只丢弃包头。
                    # 策略：在缓冲区中搜索下一个看起来像合法包头的位置（0x0000000?）
                    sync_found = False
                    for i in range(1, len(self.recv_buffer) - 1):
                        if i + 8 > len(self.recv_buffer):
                            break
                        
                        potential_type = struct.unpack('>I', self.recv_buffer[i:i+4])[0]
                        potential_len = struct.unpack('>I', self.recv_buffer[i+4:i+8])[0]
                        if (potential_type in valid_types and 
                            0 <= potential_len <= MAX_ALLOWED_SIZE):
                            print_log(LogLevel.INFO, self.log_title, f"找到同步点，丢弃 {i} 字节坏数据...")
                            del self.recv_buffer[0:i]
                            sync_found = True
                            break
                    
                    if not sync_found:
                        # 没找到，清空整个缓冲区，从头开始
                        print_log(LogLevel.WARN, self.log_title, f"未找到同步点，清空整个接收缓冲区！！！")
                        self.recv_buffer.clear()
                    continue  # 同步后，重新开始循环

                # 4. 检查是否有一个完整的数据包
                if len(self.recv_buffer) >= PACKET_HEADER_SIZE + data_len:
                    # 提取完整数据包
                    packet_data = bytes(self.recv_buffer[PACKET_HEADER_SIZE:PACKET_HEADER_SIZE + data_len])
                    # 从缓冲区移除已处理的数据
                    del self.recv_buffer[:PACKET_HEADER_SIZE + data_len]
                    
                    # 4. 处理这个完整的数据包
                    self._handle_packet(packet_type, data_len, packet_data)
                    processed_count += 1
                    self.packet_count += 1
                else:
                    # 数据包不完整，保持缓冲区不动，等待更多数据
                    break

            except struct.error as e:
                print_log(LogLevel.ERROR, self.log_title, f"解析包头结构失败: {e}，丢弃 1 字节，尝试重新同步")
                if len(self.recv_buffer) > 0:
                    del self.recv_buffer[0:1]
                    print_log(LogLevel.WARN, self.log_title, f"丢弃 1 字节，尝试重新同步")
                    self.bad_packet_bytes += 1
                
                continue
            except Exception as e:
                print_log(LogLevel.ERROR, self.log_title, f"处理数据时发生未知异常: {e}，清空整个接收缓冲区！！！")
                # 发生未知异常，保守策略：清空缓冲区
                self.recv_buffer.clear()
                break
    
    def _handle_packet(self, packet_type: int, data_len: int, packet_data: bytes):
        """处理数据包"""
        self.last_data_time = time.time()
        
        # 记录包类型用于调试
        packet_type_names = {
            PacketType.PACKET_HEARTBEAT: "HEARTBEAT",
            PacketType.PACKET_SPS: "SPS",
            PacketType.PACKET_PPS: "PPS",
            PacketType.PACKET_KEYFRAME: "KEYFRAME", 
            PacketType.PACKET_FRAME: "FRAME",
            PacketType.PACKET_CONFIG: "CONFIG"
        }
        
        type_name = packet_type_names.get(packet_type, f"UNKNOWN({packet_type})")
        # === 零长度数据包处理 ===
        if data_len == 0:
            # 心跳包长度为0是正常的，其他类型则可能是错误
            if packet_type != PacketType.PACKET_HEARTBEAT:
                print_log(LogLevel.WARN, self.log_title, f"警告: 收到零长度的 {type_name} 包，可能为协议错误，直接忽略！")
            return
        
        # 详细日志输出
        if self.debug:
            need_print = True
        elif packet_type != PacketType.PACKET_HEARTBEAT and packet_type != PacketType.PACKET_FRAME:
            need_print = True
        else:
            need_print = False
        
        if need_print:
            print_log(LogLevel.DEBUG, self.log_title, f"收到包: {type_name}, 长度={data_len}字节")
        
        if packet_type == PacketType.PACKET_HEARTBEAT:
            self.last_heartbeat_time = time.time()
            return
        
        elif packet_type == PacketType.PACKET_CONFIG:
            return
        
        elif packet_type == PacketType.PACKET_SPS:
            self.sps_data = packet_data
            self.sps_received = True
            
            # 如果PPS也已经收到，初始化解码器
            if self.pps_received and self.sps_data and self.pps_data:
                print_log(LogLevel.INFO, self.log_title, f"SPS和PPS都已收到，初始化解码器")
                if self.decoder and self.decoder.set_sps_pps(self.sps_data, self.pps_data):
                    print_log(LogLevel.INFO, self.log_title, f"解码器初始化成功")
                else:
                    print_log(LogLevel.ERROR, self.log_title, f"解码器初始化失败")
            return
        
        elif packet_type == PacketType.PACKET_PPS:
            self.pps_data = packet_data
            self.pps_received = True
            
            # 如果SPS也已经收到，初始化解码器
            if self.sps_received and self.sps_data and self.pps_data:
                print_log(LogLevel.INFO, self.log_title, f"SPS和PPS都已收到，初始化解码器")
                if self.decoder and self.decoder.set_sps_pps(self.sps_data, self.pps_data):
                    print_log(LogLevel.INFO, self.log_title, f"解码器初始化成功")
                else:
                    print_log(LogLevel.ERROR, self.log_title, f"解码器初始化失败")
            return
        
        elif packet_type == PacketType.PACKET_KEYFRAME:
            is_keyframe = True
        
        elif packet_type == PacketType.PACKET_FRAME:
            is_keyframe = False
        
        else:
            print_log(LogLevel.WARN, self.log_title, f"警告！收到未知数据包类型: {packet_type}")
            return
        
        # 只有在解码器初始化成功后才尝试解码
        if self.decoder and self.sps_received and self.pps_received:
            rgb_array = self.decoder.decode_frame(packet_data, is_keyframe)
            
            if rgb_array is not None:
                self.frame_count += 1
                self.last_frame_time = time.time()
                
                if self.debug and self.frame_count % 100 == 0:
                    print_log(LogLevel.DEBUG, self.log_title, f"成功解码第{self.frame_count}帧")
                
                # 放入队列
                try:
                    self.frame_queue.put_nowait(rgb_array)
                    
                    if self.on_frame_decoded:
                        try:
                            self.on_frame_decoded(rgb_array)
                        except:
                            pass
                            
                except queue.Full:
                    try:
                        # 队列满时，丢弃最旧的帧
                        self.frame_queue.get_nowait()
                        self.frame_queue.put_nowait(rgb_array)
                    except:
                        pass
            else:
                print_log(LogLevel.ERROR, self.log_title, f"解码失败，包类型={type_name}")
        else:
            print_log(LogLevel.WARN, self.log_title, f"解码器未准备好，跳过帧 (SPS:{self.sps_received}, PPS:{self.pps_received})")
    
    def _process_thread_func(self):
        """处理线程"""
        print_log(LogLevel.INFO, self.log_title, f"处理线程启动")
        
        while not self._stop_event.is_set() and self.is_connected:
            try:
                # 定期打印统计信息
                current_time = time.time()
                if current_time - self.last_fps_check >= 10.0:
                    self.last_fps_check = current_time
                    if self.decoder:
                        if self.last_print_frame_count != self.frame_count:
                            self.last_print_frame_count = self.frame_count
                            print_log(LogLevel.DEBUG, self.log_title, f"统计: 总帧数={self.frame_count}, "
                                f"解码成功={self.decoder.decode_success}, "
                                f"解码失败={self.decoder.decode_failure}, "
                                f"队列大小={self.frame_queue.qsize()}, ")
                        if self.debug:
                            print_log(LogLevel.DEBUG, self.log_title, f"SPS状态: {self.sps_received}, PPS状态: {self.pps_received}")
                
                # 短暂休眠，避免占用过多CPU
                time.sleep(0.5)
                
            except Exception as e:
                if not self._stop_event.is_set():
                    print_log(LogLevel.ERROR, self.log_title, f"处理线程异常: {e}")
        
        print_log(LogLevel.INFO, self.log_title, f"处理线程结束")

    def get_current_frame(self, timeout: float = 0.001) -> Optional[np.ndarray]:
        """获取当前显示帧"""
        try:
            return self.frame_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def disconnect(self):
        """断开连接"""
        def disconnect_async():
            print_log(LogLevel.INFO, self.log_title, f"断开连接...")
            # 停止服务端
            self.device_manager.stop_server()
            # 移除端口转发
            port = self.device_manager.get_port_forwarding()
            if port > 0:
                self.device_manager.remove_port_forwarding(port, port)
                self.device_manager.reset_port_forwarding()
            
            self._stop_event.set()
            
            self.is_streaming = False
            self.is_connected = False
            
            # 清理解码器
            if self.decoder:
                self.decoder.cleanup()
                self.decoder = None
            
            if self.socket:
                try:
                    self.socket.close()
                except:
                    pass
                self.socket = None
            
            # 等待线程结束
            if self.heartbeat_thread and self.heartbeat_thread.is_alive():
                self.heartbeat_thread.join(timeout=1.0)
            
            if self.monitor_thread and self.monitor_thread.is_alive():
                self.monitor_thread.join(timeout=1.0)
            
            # 清空队列
            while not self.frame_queue.empty():
                try:
                    self.frame_queue.get_nowait()
                except:
                    break
            
            print_log(LogLevel.INFO, self.log_title, f"断开连接已完成")
        
        threading.Thread(target=disconnect_async, daemon=True).start()

# ==================== 设备控制器 ====================
class DeviceController:
    """设备控制器"""
    
    KEY_MAPPINGS = {
        "home": 1,
        "back": 2,
        "volume_up": 16,
        "volume_down": 17,
        "power": 18,
        "camera": 19,
    }
    
    def __init__(self, hdc_executor: HDCCommandExecutor):
        self.hdc = hdc_executor
        self.display_width = 0
        self.display_height = 0
        self.display_ratio = 0.0
        self.left = 0
        self.right = 0
        self.top = 0
        self.bottom = 0
        self.video_canvas = None
        self.drag_start = None
        self.log_title = "设备控制器"
    
    def set_display_resolution(self, width: int, height: int, ratio: float):
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
    
    def bind_video_canvas(self, canvas):
        """绑定视频画布"""
        self.video_canvas = canvas
        
        # 绑定鼠标事件
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
    
    def _on_mouse_down(self, event):
        """鼠标按下"""
        if self.left <= event.x <= self.right and self.top <= event.y <= self.bottom:
            self.drag_start = (event.x, event.y)
    
    def _on_mouse_drag(self, event):
        """鼠标拖动"""
        pass  # 实时预览可以在这里实现
    
    def _on_mouse_up(self, event):
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

# ==================== 主GUI界面 ====================
class OHScrcpyGUI:
    """主GUI界面"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"OHScrcpy - OpenHarmony投屏工具 {VERSION}    （作者: {AUTHOR}）")
        self.root.geometry("1200x800")
        
        # 状态变量
        self.is_connected = False
        self.current_frame = None
        self.tk_image = None
        self.last_display_time = 0
        self.log_title = "GUI"
        self.server_deploy_lock = threading.Lock()
        self.server_deploy_state = ServerDeployState.IDLE
        
        # 视频配置
        self.video_width = 0
        self.video_height = 0
        self.video_ratio = 0.0
        self.display_width = 0
        self.display_height = 0
        self.canvas_width = 800
        self.canvas_height = 600
        
        # 性能统计
        self.fps = 0
        self.frame_counter = 0
        self.last_fps_time = time.time()
        self.displayed_frames = 0
        self.last_print_frames = 0
        
        # 显示配置
        self.video_canvas = None
        self.status_text_id = None
        self.running_status_text_id = None
        
        # 内存管理
        self.last_gc_time = time.time()
        self.image_refs = []
        
        # 设置UI
        self.setup_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.bind('<Configure>', self.on_window_resize)
        
        # 初始化组件
        def init_component_async():
            self.hdc_executor = HDCCommandExecutor()
            self.device_manager = DeviceManager(self.hdc_executor)
            self.device_controller = None
            self.video_client = VideoStreamClient(device_manager=self.device_manager, on_frame_decoded=self._on_frame_decoded, debug=False)
            self.refresh_devices()
        threading.Thread(target=init_component_async, daemon=True).start()
        
        print_log(LogLevel.INFO, self.log_title, f"初始化完成")
    
    def open_project_url(self, event=None):
        """打开项目地址"""
        webbrowser.open(PROJECT_URL)
    
    def show_about_dialog(self):
        """显示关于对话框"""
        about_window = tk.Toplevel(self.root)
        about_window.title("关于 OHScrcpy")
        about_window.resizable(False, False)
        about_window.transient(self.root)
        about_window.grab_set()
        
        # 居中计算
        root_x = self.root.winfo_rootx()
        root_y = self.root.winfo_rooty()
        root_w = self.root.winfo_width()
        root_h = self.root.winfo_height()
        win_w = 420
        win_h = 260
        x = root_x + (root_w - win_w) // 2
        y = root_y + (root_h - win_h) // 2
        about_window.geometry(f"{win_w}x{win_h}+{x}+{y}")

        # 主容器（使用 pack 布局）
        main_frame = tk.Frame(about_window, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 软件名称
        app_name_label = tk.Label(
            main_frame,
            text="OHScrcpy - OpenHarmony投屏工具",
            font=("Microsoft YaHei", 12, "bold"),
            anchor="center"
        )
        app_name_label.pack(pady=(0, 15))

        content_frame = tk.Frame(main_frame)
        content_frame.pack(fill=tk.X, anchor="w")

        # 版本信息
        version_label = tk.Label(
            content_frame,
            text=f"版本: {VERSION}",
            font=("Microsoft YaHei", 10),
            anchor="w"
        )
        version_label.pack(anchor="w", padx=10, pady=2)

        # 作者
        author_label = tk.Label(
            content_frame,
            text=f"作者: {AUTHOR}",
            font=("Microsoft YaHei", 10),
            anchor="w"
        )
        author_label.pack(anchor="w", padx=10, pady=2)

        # 项目地址
        project_label = tk.Label(
            content_frame,
            text="项目地址:",
            font=("Microsoft YaHei", 10),
            anchor="w"
        )
        project_label.pack(anchor="w", padx=10, pady=2)

        # 项目地址超链接
        url_label = tk.Label(
            content_frame,
            text=PROJECT_URL,
            font=("Microsoft YaHei", 10),
            fg="blue",
            cursor="hand2",
            anchor="w",
            justify="left"
        )
        url_label.pack(anchor="w", padx=10, pady=2)
        url_label.bind("<Button-1>", self.open_project_url)

        # 关闭按钮
        close_button = tk.Button(
            main_frame,
            text="关闭",
            command=about_window.destroy,
            font=("Microsoft YaHei", 9),
            width=10
        )
        close_button.pack(pady=(20, 0))
        close_button.focus_set()
    
    def setup_ui(self):
        """设置UI"""
        # 标题栏
        title_frame = tk.Frame(self.root, height=30, bg="#2c3e50")
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)
        
        # 左侧：应用标题和作者信息
        left_frame = tk.Frame(title_frame, bg="#2c3e50")
        left_frame.pack(side=tk.LEFT, padx=10, pady=5)
        
        # 应用标题
        app_title_label = tk.Label(left_frame, text="OHScrcpy - OpenHarmony投屏工具", 
                                  font=("Microsoft YaHei", 12), fg="white", bg="#2c3e50")
        app_title_label.pack(side=tk.LEFT)
        
        # 右侧：设备状态和关于按钮
        right_frame = tk.Frame(title_frame, bg="#2c3e50")
        right_frame.pack(side=tk.RIGHT, padx=10, pady=5)
        
        # 关于按钮 - 与标题栏同色
        about_button = tk.Button(right_frame, text="关于", 
                                font=("Microsoft YaHei", 9), 
                                bg="#2c3e50", fg="white",
                                relief=tk.FLAT, width=6,
                                command=self.show_about_dialog)
        about_button.pack(side=tk.RIGHT, padx=(10, 0))
        
        self.device_status_label = tk.Label(
            right_frame, text="设备: 未连接", font=("Microsoft YaHei", 9),
            fg="#ecf0f1", bg="#2c3e50"
        )
        self.device_status_label.pack(side=tk.RIGHT, padx=(0, 10))
        
        # 主内容区
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 视频区域
        video_frame = tk.LabelFrame(main_frame, text="视频显示", font=("Microsoft YaHei", 10))
        video_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # 使用Canvas显示视频
        self.video_canvas = tk.Canvas(video_frame, bg="#1a1a2e", highlightthickness=1)
        self.video_canvas.pack(fill=tk.BOTH, expand=True)
        
        # 控制面板
        control_frame = tk.Frame(main_frame, width=300)
        control_frame.pack(side=tk.RIGHT, fill=tk.Y)
        control_frame.pack_propagate(False)
        
        self.create_device_panel(control_frame)
        self.create_control_panel(control_frame)
        self.create_info_panel(control_frame)
        
        # 状态栏
        status_frame = tk.Frame(self.root, height=25, bg="#34495e")
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        status_frame.pack_propagate(False)
        
        self.status_label = tk.Label(
            status_frame, text="就绪", font=("Microsoft YaHei", 9),
            fg="white", bg="#34495e", anchor=tk.W
        )
        self.status_label.pack(side=tk.LEFT, padx=10)
        
        self.connection_status_label = tk.Label(
            status_frame, text="未连接", font=("Microsoft YaHei", 9),
            fg="#e74c3c", bg="#34495e", anchor=tk.E
        )
        self.connection_status_label.pack(side=tk.RIGHT, padx=10)
        
        self.performance_label = tk.Label(
            status_frame, text="FPS: 0 | 帧数: 0", font=("Microsoft YaHei", 9),
            fg="#3498db", bg="#34495e"
        )
        self.performance_label.pack(side=tk.RIGHT, padx=20)
        
        # 初始显示等待画面
        self._show_waiting_screen()
    
    def create_device_panel(self, parent):
        """创建设备面板"""
        frame = tk.LabelFrame(parent, text="设备选择", font=("Microsoft YaHei", 10))
        frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        self.device_var = tk.StringVar()
        self.device_combo = ttk.Combobox(frame, textvariable=self.device_var, state="readonly")
        self.device_combo.bind("<<ComboboxSelected>>", self.on_combobox_select)
        self.device_combo.pack(fill=tk.X, padx=10, pady=(0, 5))
        
        btn_frame = tk.Frame(frame)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Button(btn_frame, text="刷新", command=self.refresh_devices,
                 font=("Microsoft YaHei", 9), bg="#3498db", fg="white", width=8
                 ).pack(side=tk.LEFT, padx=(0, 5))
        
        self.connect_btn = tk.Button(
            btn_frame, text="连接", command=self.trigger_connection,
            font=("Microsoft YaHei", 9), bg="#2ecc71", fg="white", width=8
        )
        self.connect_btn.pack(side=tk.RIGHT)
    
    def create_control_panel(self, parent):
        """创建控制面板"""
        frame = tk.LabelFrame(parent, text="设备控制", font=("Microsoft YaHei", 10))
        frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        controls = [
            ("电源", self.power_key, "#e74c3c"),
            ("主页", self.home_key, "#2ecc71"),
            ("返回", self.back_key, "#3498db"),
            ("解锁", self.unlock_screen, "#3498db"),
            ("音量+", self.volume_up, "#9b59b6"),
            ("音量-", self.volume_down, "#9b59b6"),
        ]
        
        for i, (text, command, color) in enumerate(controls):
            btn = tk.Button(frame, text=text, command=command, bg=color, fg="white", height=2, width=8)
            row, col = divmod(i, 2)
            btn.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
        
        for i in range(2):
            frame.grid_columnconfigure(i, weight=1)
    
    def create_info_panel(self, parent):
        """创建信息面板"""
        frame = tk.LabelFrame(parent, text="操作说明", font=("Microsoft YaHei", 10))
        frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        instructions = """
            在视频区域：
            • 点击 → 设备点击
            • 拖动 → 设备滑动

            快捷键：
            • F5：刷新设备列表
            • F6：截图
            • F8：显示调试信息
            • F9：强制垃圾回收

            注意：
            1. 确保设备已连接并启用USB调试
            2. 首次连接可能需要授权
            3. 确保HDC工具可用"""
        
        tk.Label(
            frame, 
            text=instructions, 
            justify=tk.LEFT, 
            padx=10,
            pady=10, 
            font=("Microsoft YaHei", 9)
        ).pack()
    
    def _on_frame_decoded(self, frame):
        """帧解码回调"""
        self.current_frame = frame
        self.frame_counter += 1
        
        # 计算fps
        current_time = time.time()
        if current_time - self.last_fps_time >= 1.0:
            self.fps = self.frame_counter
            self.frame_counter = 0
            self.last_fps_time = current_time
            self.performance_label.config(text=f"FPS: {self.fps} | 帧数: {self.video_client.frame_count}")
    
    def _update_video_display(self):
        """更新视频显示"""
        current_time = time.time()
        
        # 定期垃圾回收
        if current_time - self.last_gc_time > 15.0:
            self.last_gc_time = current_time
            if len(self.image_refs) > 10:
                self.image_refs = self.image_refs[-5:]
        
        # 检查心跳超时
        if self.is_connected and hasattr(self.video_client, 'last_data_time'):
            time_since_last_data = current_time - self.video_client.last_data_time
            if time_since_last_data > HEARTBEAT_TIMEOUT:
                print_log(LogLevel.WARN, self.log_title, f"检测到心跳超时 ({time_since_last_data:.1f}秒)，断开连接")
                self.disconnect_device()
                return
        
        # 限制显示频率，最多30fps
        if current_time - self.last_display_time < 0.033:
            self.root.after(10, self._update_video_display)
            return
        
        self.last_display_time = current_time
        
        if not self.is_connected:
            self.root.after(100, self._update_video_display)
            return
        
        try:
            # 获取最新帧
            import numpy as np
            frame = self.video_client.get_current_frame(timeout=0.001)
            if frame is None:
                # 没有新帧，使用最后解码的帧
                frame = self.current_frame
            
            if frame is not None:
                self.displayed_frames += 1
                
                # 每100帧打印一次状态
                if self.last_print_frames != self.displayed_frames and self.displayed_frames % 100 == 0:
                    self.last_print_frames = self.displayed_frames
                    print_log(LogLevel.DEBUG, self.log_title, f"已显示 {self.displayed_frames} 帧，队列大小: {self.video_client.frame_queue.qsize()}")
                
                # 转换为PIL图像
                try:
                    from PIL import Image
                    pil_img = Image.fromarray(frame, 'RGB')
                except Exception as e:
                    print_log(LogLevel.ERROR, self.log_title, f"创建PIL图像失败: {e}")
                    self.root.after(10, self._update_video_display)
                    return
                
                # 获取原始视频尺寸
                if self.video_width <= 0 or self.video_height <= 0:
                    self.video_width = pil_img.width
                    self.video_height = pil_img.height
                    print_log(LogLevel.DEBUG, self.log_title, f"原始视频尺寸: {self.video_width}x{self.video_height}")
                
                # 缩放图像，保持原始比例，适应Canvas
                img_width, img_height = pil_img.size
                if self.video_ratio == 0.0:
                    self.canvas_width = self.video_canvas.winfo_width()
                    self.canvas_height = self.video_canvas.winfo_height()
                    print_log(LogLevel.DEBUG, self.log_title, f"画布尺寸: {self.canvas_width}x{self.canvas_height}")
                    if self.canvas_width <= 10 or self.canvas_height <= 10:
                        self.canvas_width = 800
                        self.canvas_height = 600
                    
                    # 计算适合Canvas的最大尺寸（保持宽高比）
                    if img_width > 0 and img_height > 0:
                        width_ratio = self.canvas_width / img_width
                        height_ratio = self.canvas_height / img_height
                        self.video_ratio = min(width_ratio, height_ratio)
                        # 计算显示尺寸
                        self.display_width = int(img_width * self.video_ratio)
                        self.display_height = int(img_height * self.video_ratio)
                        
                        # 向设备控制器设置分辨率
                        self.device_controller.set_display_resolution(self.display_width, self.display_height, self.video_ratio)
                
                # 缩放图像
                if self.display_width != img_width or self.display_height != img_height:
                    try:
                        pil_img_resized = pil_img.resize((self.display_width, self.display_height), 
                                                         Image.Resampling.LANCZOS)
                    except Exception as e:
                        print_log(LogLevel.ERROR, self.log_title, f"缩放图像失败: {e}")
                        pil_img_resized = pil_img
                else:
                    pil_img_resized = pil_img
                
                # 计算居中位置
                x_offset = (self.canvas_width - self.display_width) // 2
                y_offset = (self.canvas_height - self.display_height) // 2
                
                # 转换为Tkinter图像
                try:
                    from PIL import ImageTk
                    self.tk_image = ImageTk.PhotoImage(pil_img_resized)
                    # 保持引用，防止被垃圾回收
                    self.image_refs.append(self.tk_image)
                    
                    # 限制引用的图像数量
                    if len(self.image_refs) > 10:
                        self.image_refs = self.image_refs[-5:]
                except Exception as e:
                    print_log(LogLevel.ERROR, self.log_title, f"创建Tkinter图像失败: {e}")
                    self.root.after(10, self._update_video_display)
                    return
                
                # 清除画布并显示新图像
                self.video_canvas.delete("all")
                
                # 创建图像
                self.video_canvas.create_image(
                    x_offset, y_offset,
                    anchor=tk.NW,
                    image=self.tk_image
                )
                
                # 更新状态文本
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
                
                # 强制更新显示
                self.video_canvas.update_idletasks()
            
        except Exception as e:
            if self.is_connected:
                print_log(LogLevel.ERROR, self.log_title, f"显示错误: {e}")
        
        # 继续更新
        self.root.after(10, self._update_video_display)
    
    def _show_waiting_screen(self):
        """显示等待画面"""
        # 清除画布
        self.video_canvas.delete("all")
        
        # 设置深色背景
        self.video_canvas.config(bg="#1a1a2e")
        
        # 获取Canvas尺寸
        canvas_width = self.video_canvas.winfo_width()
        canvas_height = self.video_canvas.winfo_height()
        
        if canvas_width <= 10 or canvas_height <= 10:
            canvas_width = 800
            canvas_height = 600
        
        # 显示提示文字
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
        
        # 清除状态文本ID
        self.status_text_id = None
    
    def update_running_status(self, content: str):
        self.video_canvas.itemconfig(self.running_status_text_id, text=content)
    
    def refresh_devices(self):
        """刷新设备"""
        self.update_device_status("正在扫描设备...")
        devices = self.device_manager.discover_devices()
        
        if devices:
            display_names = [d.display_name() for d in devices]
            self.device_combo['values'] = display_names
            if display_names:
                self.device_combo.set(display_names[0])
            self.update_device_status(f"发现 {len(devices)} 个设备")
            self.on_combobox_select(None)
        else:
            self.device_combo['values'] = []
            self.update_device_status("未发现设备")
    
    def trigger_connection(self):
        """连接/断开设备"""
        if not self.is_connected:
            self.connect_device()
        else:
            self.disconnect_device()
    
    def set_server_deploy_state(self, state: ServerDeployState):
        with self.server_deploy_lock:
            self.server_deploy_state = state
    
    def get_server_deploy_state(self) -> ServerDeployState:
        with self.server_deploy_lock:
            return self.server_deploy_state
    
    def on_combobox_select(self, event):
        print_log(LogLevel.INFO, self.log_title, "-"*60)
        print_log(LogLevel.INFO, self.log_title, f"用户选择设备: {self.device_combo.get()}")
        print_log(LogLevel.INFO, self.log_title, f"投屏准备: 开始安装和启动服务端...")
        threading.Thread(target=self.install_and_start_server_async, daemon=True).start()
    
    def on_server_deploy_finish(self, succ: bool, msg: str):
        if not succ:
            messagebox.showerror("错误", f"{msg}")
    
    def install_and_start_server_async(self):
        self.video_client.disconnect()
        selected = self.device_var.get()
        if not selected:
            print_log(LogLevel.WARN, self.log_title, f"用户选择设备为空")
            return
        
        target_device = None
        for device in self.device_manager.devices:
            if device.display_name() == selected:
                target_device = device
                break
        
        if not target_device or not self.device_manager.select_device(target_device.sn):
            self.update_device_status("设备选择失败")
            return
        
        self.update_running_status(f"[预安装] 正在获取可用转发端口，请稍等...")
        port = self.device_manager.get_port_forwarding()
        if port == -1:
            print_log(LogLevel.ERROR, self.log_title, f"获取可用转发端口失败！")
            self.root.after(0, self.on_server_deploy_finish, False, "获取可用转发端口失败！")
            return
        
        # 1. 检查服务端是否已安装
        self.update_running_status(f"[预安装] 正在安装服务端，请稍等...")
        print_log(LogLevel.INFO, self.log_title, f"检查服务端安装状态...")
        if not self.device_manager.check_server_installed():
            print_log(LogLevel.INFO, self.log_title, f"服务端未安装，开始安装...")
            
            # 安装服务端
            if not self.device_manager.install_server():
                print_log(LogLevel.ERROR, self.log_title, f"服务端安装失败！")
                self.root.after(0, self.on_server_deploy_finish, False, "服务端安装失败！")
                return
        else:
            print_log(LogLevel.INFO, self.log_title, f"服务端已安装")
        
        # 2. 检查服务端是否在运行
        self.update_running_status(f"[预安装] 正在启动服务端，请稍等...")
        print_log(LogLevel.INFO, self.log_title, f"检查服务端运行状态...")
        if not self.device_manager.check_server_running():
            print_log(LogLevel.INFO, self.log_title, f"启动服务端...")
            if not self.device_manager.start_server(port):
                print_log(LogLevel.ERROR, self.log_title, f"服务端启动失败！")
                self.update_running_status(f"[预安装] 启动服务端失败！")
                self.root.after(0, self.on_server_deploy_finish, False, "服务端启动失败！")
                return
            
            # 等待服务端完全启动
            print_log(LogLevel.INFO, self.log_title, f"等待服务端就绪...")
            time.sleep(1)
        else:
            print_log(LogLevel.INFO, self.log_title, f"服务端已在运行")
        self.update_running_status(f"[预安装] 服务端已就绪，可随时点击[连接]开始投屏！")
    
    def install_and_start_server(self, port: int) -> bool:
        # 1. 检查服务端是否已安装
        print_log(LogLevel.INFO, self.log_title, f"检查服务端安装状态...")
        if not self.device_manager.check_server_installed():
            print_log(LogLevel.INFO, self.log_title, f"服务端未安装，开始安装...")
            
            # 安装服务端
            if not self.device_manager.install_server():
                messagebox.showerror("错误", "服务端安装失败！")
                print_log(LogLevel.ERROR, self.log_title, f"服务端安装失败")
                return False
        else:
            print_log(LogLevel.INFO, self.log_title, f"服务端已安装")
        
        # 2. 检查服务端是否在运行
        print_log(LogLevel.INFO, self.log_title, f"检查服务端运行状态...")
        if not self.device_manager.check_server_running():
            print_log(LogLevel.INFO, self.log_title, f"启动服务端...")
            if not self.device_manager.start_server(port):
                messagebox.showerror("错误", f"服务端启动失败！")
                print_log(LogLevel.ERROR, self.log_title, f"服务端启动失败")
                return False
            
            # 等待服务端完全启动
            print_log(LogLevel.INFO, self.log_title, f"等待服务端就绪...")
            time.sleep(1)
        else:
            print_log(LogLevel.INFO, self.log_title, f"服务端已在运行")
        return True
        
    def connect_device(self):
        """连接设备"""
        selected = self.device_var.get()
        if not selected:
            messagebox.showwarning("警告", "请先选择设备")
            return
        
        target_device = None
        for device in self.device_manager.devices:
            if device.display_name() == selected:
                target_device = device
                break
        
        if not target_device or not self.device_manager.select_device(target_device.sn):
            self.update_device_status("设备选择失败")
            return
        
        def connect_device_async():
            port = self.device_manager.get_port_forwarding()
            if port == -1:
                print_log(LogLevel.ERROR, self.log_title, f"获取可用转发端口失败")
                return
            
            # 安装并启动服务端
            if not self.install_and_start_server(port):
                return

            # 设置端口转发
            print_log(LogLevel.INFO, self.log_title, f"设置端口转发...")
            if not self.device_manager.setup_port_forwarding(port, port):
                print_log(LogLevel.ERROR, self.log_title, f"端口转发失败，请尝试重新连接...")
                return

            try:
                device = self.device_manager.get_current_device()
                self.update_device_status(f"正在连接设备: {device.sn}...")
            
                # 连接视频流
                print_log(LogLevel.DEBUG, self.log_title, f"连接视频流服务器...")
                if self.video_client.connect(HOST, port):
                    # 获取视频配置
                    config = self.video_client.config
                    
                    # 设置设备控制器
                    self.device_controller = DeviceController(self.hdc_executor)
                    self.device_controller.bind_video_canvas(self.video_canvas)
                    
                    # 更新UI状态
                    self.is_connected = True
                    self.connect_btn.config(text="断开", bg="#e74c3c")
                    self.connection_status_label.config(text="已连接", fg="#2ecc71")
                    self.device_status_label.config(text=f"设备: {device.sn}")
                    
                    # 重置显示计数器
                    self.displayed_frames = 0
                    self.frame_counter = 0
                    self.last_fps_time = time.time()
                    self.last_print_frames = 0
                    
                    # 清除等待画面
                    self.video_canvas.delete("all")
                    self.video_canvas.config(bg="black")
                    
                    # 启动视频显示
                    self._update_video_display()
                    
                    self.update_device_status(f"连接成功！分辨率: {config.width}x{config.height}")
                    
                    # 添加调试快捷键
                    self.root.bind('<F5>', lambda e: self._print_debug_info())
                    self.root.bind('<F6>', lambda e: self._save_debug_frame())
                    self.root.bind('<F8>', lambda e: self._show_debug_window())
                    self.root.bind('<F9>', lambda e: self._force_garbage_collection())
                else:
                    self.update_device_status("连接失败")
                    self.disconnect_device()
                    messagebox.showinfo("连接失败",
                        "无法连接到服务端！请检查:\n"
                        "1. 服务端是否在设备上运行\n"
                        "2. 服务端口是否正确")
                    return
                
            except Exception as e:
                self.update_device_status(f"连接失败: {str(e)}")
                traceback.print_exc()
                self.disconnect_device()
                return
        
        threading.Thread(target=connect_device_async, daemon=True).start()
        self.connect_btn.config(text="连接中", bg="#e74c3c")
    
    def disconnect_device(self):
        """断开设备"""
        self.is_connected = False
        self.video_client.disconnect()
        
        # 清理图像引用
        self.image_refs.clear()
        
        # 显示等待画面
        self._show_waiting_screen()
        
        # 更新UI状态
        self.connect_btn.config(text="连接", bg="#2ecc71")
        self.connection_status_label.config(text="未连接", fg="#e74c3c")
        self.device_status_label.config(text="设备: 未连接")
        self.performance_label.config(text="FPS: 0 | 帧数: 0")
        
        # 重置视频尺寸
        self.video_width = 0
        self.video_height = 0
        self.video_ratio = 0.0
        self.display_width = 0
        self.display_height = 0
        self.canvas_width = 800
        self.canvas_height = 600
        
        # 强制垃圾回收
        self._force_garbage_collection()
        self.update_device_status("设备已断开")
        print_log(LogLevel.INFO, self.log_title, "-"*60)
    
    def power_key(self):
        if self.is_connected and self.device_controller:
            self.device_controller.power_key()
            print_log(LogLevel.INFO, self.log_title, f"发送电源键")
    
    def home_key(self):
        if self.is_connected and self.device_controller:
            self.device_controller.home_key()
            print_log(LogLevel.INFO, self.log_title, f"发送Home键")
    
    def back_key(self):
        if self.is_connected and self.device_controller:
            self.device_controller.back_key()
            print_log(LogLevel.INFO, self.log_title, f"发送返回键")
    
    def unlock_screen(self):
        if self.is_connected and self.device_controller:
            self.device_controller.unlock_screen()
            print_log(LogLevel.INFO, self.log_title, f"发送解锁屏幕")
    
    def volume_up(self):
        if self.is_connected and self.device_controller:
            self.device_controller.volume_up()
            print_log(LogLevel.INFO, self.log_title, f"发送音量+")
    
    def volume_down(self):
        if self.is_connected and self.device_controller:
            self.device_controller.volume_down()
            print_log(LogLevel.INFO, self.log_title, f"发送音量-")
    
    def _print_debug_info(self):
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
            
            if self.video_client.decoder:
                decoder = self.video_client.decoder
                print_log(LogLevel.INFO, debug_info_title, f"解码统计: 成功={decoder.decode_success}, 失败={decoder.decode_failure}")
                print_log(LogLevel.INFO, debug_info_title, f"解码器状态: initialized={decoder.codec_ctx is not None}")
        
        # 内存信息
        import psutil
        process = psutil.Process()
        mem_info = process.memory_info()
        print_log(LogLevel.INFO, debug_info_title, f"内存使用: RSS={mem_info.rss / 1024 / 1024:.1f}MB, VMS={mem_info.vms / 1024 / 1024:.1f}MB")
        print_log(LogLevel.INFO, debug_info_title, f"==========================\n")
    
    def _save_debug_frame(self):
        """保存当前帧用于调试"""
        debug_frame_title = "保存调试帧"
        if self.current_frame is not None:
            try:
                from PIL import Image
                debug_dir = "debug_frames"
                os.makedirs(debug_dir, exist_ok=True)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = os.path.join(debug_dir, f"debug_{timestamp}.png")
                
                pil_img = Image.fromarray(self.current_frame, 'RGB')
                pil_img.save(filename)
                
                print_log(LogLevel.INFO, debug_frame_title, f"调试帧保存在: {filename}")
                print_log(LogLevel.INFO, debug_frame_title, f"图像尺寸: {pil_img.size}")
            except Exception as e:
                print_log(LogLevel.ERROR, debug_frame_title, f"保存调试帧失败: {e}")
    
    def _show_debug_window(self):
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
            
            if self.video_client.decoder:
                decoder = self.video_client.decoder
                debug_info.append(f"解码成功: {decoder.decode_success}")
                debug_info.append(f"解码失败: {decoder.decode_failure}")
            
            if hasattr(self.video_client, 'last_data_time'):
                time_since_last_data = time.time() - self.video_client.last_data_time
                debug_info.append(f"心跳状态: {time_since_last_data:.1f}秒前收到数据")
        
        text_widget.insert(tk.END, "\n".join(debug_info))
        text_widget.config(state=tk.DISABLED)
    
    def _force_garbage_collection(self):
        """强制垃圾回收"""
        def _async_garbage_collection_func():
            """异步垃圾回收"""
            print_log(LogLevel.INFO, self.log_title, f"强制垃圾回收...")
            collected = gc.collect()
            print_log(LogLevel.INFO, self.log_title, f"回收了 {collected} 个对象")
        
        threading.Thread(target=_async_garbage_collection_func, daemon=True).start()
    
    def update_device_status(self, message: str):
        """更新状态"""
        self.status_label.config(text=message)
        print_log(LogLevel.INFO, "GUI设备状态更新", f"{message}")
    
    def on_closing(self):
        if self.is_connected:
            if messagebox.askokcancel("退出", "设备仍处于连接状态，确定要退出吗？"):
                self.disconnect_device()
                self.root.destroy()
        else:
            self.video_client.disconnect()
            self.root.destroy()
    
    def on_window_resize(self, event):
        print_log(LogLevel.DEBUG, self.log_title, f"窗口大小变化: {event.width}x{event.height}")
        # 触发重新计算视频缩放率和显示区域
        self.video_ratio = 0.0
    
    def run(self):
        self.root.mainloop()

# ==================== 主程序入口 ====================
def main():
    print("="*84)
    print(" "*15, f"OpenHarmony_Scrcpy Client - {VERSION} (author: luodh0157)", " "*15)
    print("="*84)
    
    # 启动GUI
    try:
        app = OHScrcpyGUI()
        app.run()
    except Exception as e:
        print_log(LogLevel.ERROR, "主函数", f"GUI启动失败: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()