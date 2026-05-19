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
OpenHarmony_Scrcpy HDC命令执行器
"""

import sys
import os
import platform
import shutil
import subprocess
import threading
from typing import Optional, List, Dict, Any

from .constants import LogLevel
from .logger import print_log
from utils import get_default_shell_terminal


class HDCCommandExecutor:
    """HDC命令执行器"""
    
    def __init__(self, device_sn: Optional[str] = None) -> None:
        self.device_sn = device_sn
        self.log_title = "设备命令执行器"
        self.hdc_path = self._find_hdc_path()
        self.async_processes: Dict[int, subprocess.Popen] = {}
    
    def _get_arch_name(self) -> str:
        """获取当前系统的 CPU 架构"""
        machine = platform.machine().lower()
        if machine in ('i386', 'i686', 'x86'):
            return 'x86'
        elif machine in ('x86_64', 'amd64'):
            return 'x64'
        elif machine in ('aarch64', 'arm64'):
            return 'arm64'
        else:
            print_log(LogLevel.WARN, self.log_title, f"未知的CPU架构: [{machine}]")
            return ""
    
    def _get_self_hdc_relpath(self) -> str:
        """获取当前程序自带的hdc工具相对路径"""
        arch = self._get_arch_name()
        system = platform.system()
        if system == 'Windows':
            return os.path.join('hdc', system, arch, 'hdc.exe')
        elif system in ('Linux', 'Darwin'):
            return os.path.join('hdc', system, arch, 'hdc')
        else:
            print_log(LogLevel.WARN, self.log_title, f"未知的OS平台: [{system}]")
            return 'hdc'
    
    def _get_hdc_filename(self) -> str:
        """获取当hdc工具名称"""
        system = platform.system()
        if system == 'Windows':
            return 'hdc.exe'
        elif system in ('Linux', 'Darwin'):
            return 'hdc'
        else:
            print_log(LogLevel.WARN, self.log_title, f"未知的OS平台: [{system}]")
            return 'hdc'
    
    def _get_self_hdc_abspath(self) -> str:
        """获取当前程序自带的hdc工具绝对路径"""
        if hasattr(sys, '_MEIPASS'):
            abspath = sys._MEIPASS
            abspath += os.sep + self._get_hdc_filename()
        else:
            # 开发环境 - 获取 Client 目录（父目录）
            current_dir = os.path.dirname(os.path.abspath(__file__))
            base_path = os.path.dirname(current_dir)  # 从 core/ 向上到 Client/
            relpath = self._get_self_hdc_relpath()
            abspath = os.path.join(base_path, relpath)
        return abspath
    
    def _find_hdc_path(self) -> str:
        """获取hdc工具路径（支持PyInstaller打包）"""
        filepath = self._get_self_hdc_abspath()
        if os.path.isfile(filepath):
            print_log(LogLevel.INFO, self.log_title, f"程序自带hdc工具: [{filepath}]")
            return os.path.abspath(filepath)

        hdc_in_path = shutil.which("hdc")
        if hdc_in_path:
            print_log(LogLevel.INFO, self.log_title, f"系统自带hdc工具: [{hdc_in_path}]")
            return os.path.abspath(hdc_in_path)

        print_log(LogLevel.WARN, self.log_title, f"hdc工具不存在")
        return ""
    
    def assemble_command(self, args: List[str], need_sn: bool = True) -> List[str]:
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
                print_log(LogLevel.DEBUG, self.log_title, f"执行结果: stdout: [{stdout.strip()}], stderr: [{stderr.strip()}]")
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
        """新开进程异步执行hdc命令"""
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
            
            process_id = len(self.async_processes)
            self.async_processes[process_id] = process
            
            threading.Thread(
                target=self._trigger_async_process,
                args=(process_id, process),
                daemon=True
            ).start()
            
            return process
        except Exception as e:
            print_log(LogLevel.ERROR, self.log_title, f"异步执行命令失败: {e}")
            return None
    
    def _trigger_async_process(self, process_id: int, process: subprocess.Popen) -> None:
        """监控异步进程的输出"""
        try:
            stdout, stderr = process.communicate()
            print_log(LogLevel.DEBUG, self.log_title, f"[异步进程 {process_id}] 输出: \n{stdout}")
            if stderr:
                print_log(LogLevel.ERROR, self.log_title, f"[异步进程 {process_id}] 错误: {stderr}")
        except Exception as e:
            print_log(LogLevel.ERROR, self.log_title, f"[异步进程 {process_id}] 监控异常: {e}")
        finally:
            if process_id in self.async_processes:
                del self.async_processes[process_id]
    
    def stop_async_processes(self) -> None:
        """停止所有异步进程"""
        for process_id, process in list(self.async_processes.items()):
            try:
                process.terminate()
                process.wait(timeout=1)
            except (OSError, subprocess.SubprocessError):
                try:
                    process.kill()
                except (OSError, subprocess.SubprocessError):
                    pass
            finally:
                if process_id in self.async_processes:
                    del self.async_processes[process_id]
    
    def execute_async_in_shell(self, args: List[str], need_sn: bool = True, title: str = "Command Output", keep_open: bool = False) -> Optional[subprocess.Popen]:
        """新开终端窗口异步执行hdc命令"""
        hdc_cmd = self.assemble_command(args, need_sn)
        
        system = platform.system()
        if system == "Windows":
            if keep_open:
                shell_cmd = ["start", f"{title}", "cmd", "/k"]
                shell_cmd.extend(hdc_cmd)
            else:
                shell_cmd = ["start", f"{title}", "cmd", "/c"]
                shell_cmd.extend(hdc_cmd)
            process = subprocess.Popen(shell_cmd, shell=True)
            
        elif system == "Linux" or system == "Darwin":
            terminal = get_default_shell_terminal()
            
            if keep_open:
                shell_cmd = f"{hdc_cmd}; echo 'Press Enter to exit...'; read"
            else:
                shell_cmd = hdc_cmd
                
            if terminal == "gnome-terminal":
                shell_cmd = " ".join(["gnome-terminal", "--title", title, "--", "bash", "-c", shell_cmd])
                process = subprocess.Popen(shell_cmd)
            elif terminal == "konsole":
                shell_cmd = " ".join(["konsole", "--title", title, "-e", "bash", "-c", shell_cmd])
                process = subprocess.Popen(shell_cmd)
            elif terminal == "xterm":
                shell_cmd = " ".join(["xterm", "-title", title, "-e", f"bash -c '{shell_cmd}'"])
                process = subprocess.Popen(shell_cmd)
            elif terminal == "terminator":
                shell_cmd = " ".join(["terminator", "-T", title, "-e", f"bash -c '{shell_cmd}'"])
                process = subprocess.Popen(shell_cmd)
            elif terminal == "osascript":
                applescript = f'''
                tell application "Terminal"
                    do script "{shell_cmd}"
                    activate
                end tell
                '''
                process = subprocess.Popen(["osascript", "-e", applescript])
            else:
                term_cmd = os.environ.get('TERMINAL', 'xterm')
                shell_cmd = " ".join([term_cmd, "-e", f"bash -c '{shell_cmd}'"])
                process = subprocess.Popen(shell_cmd)
        else:
            print_log(LogLevel.FATAL, self.log_title, f"异步Shell执行: Unsupported platform [{system}]")
            process = None
        
        print_log(LogLevel.DEBUG, self.log_title, f"异步Shell执行: [{shell_cmd}]")
        if process: 
            process_id = len(self.async_processes)
            self.async_processes[process_id] = process
        return process

    def set_device(self, device_sn: str) -> None:
        """设置当前设备"""
        self.device_sn = device_sn
        print_log(LogLevel.INFO, self.log_title, f"设置设备: [{device_sn}]")
    
    def get_current_device(self) -> Optional[str]:
        """获取当前设备"""
        return self.device_sn
    
    def get_hdc_info(self) -> Dict[str, Any]:
        """获取HDC信息"""
        return self.execute(["--version"], timeout=2.0)
    
    def check_file_exists(self, remote_path: str) -> bool:
        """检查远程文件是否存在"""
        result = self.execute(["shell", "ls", remote_path])
        return result["success"] and "No such file or directory" not in result["stdout"]


__all__ = ["HDCCommandExecutor"]