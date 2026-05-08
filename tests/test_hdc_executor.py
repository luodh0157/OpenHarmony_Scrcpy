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
HDC执行器单元测试
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from core.hdc_executor import HDCCommandExecutor
from core.constants import LogLevel


class TestHDCCommandExecutor:
    
    def test_init_without_device(self):
        """测试无设备初始化"""
        executor = HDCCommandExecutor()
        assert executor.device_sn is None
        assert executor.hdc_path is not None
    
    def test_init_with_device(self):
        """测试带设备初始化"""
        executor = HDCCommandExecutor(device_sn="test_device_sn")
        assert executor.device_sn == "test_device_sn"
    
    def test_assemble_command_with_sn(self):
        """测试带SN的命令组装"""
        executor = HDCCommandExecutor(device_sn="test_sn")
        executor.hdc_path = "/path/to/hdc"
        
        cmd = executor.assemble_command(["shell", "ls"])
        assert "/path/to/hdc" in cmd
        assert "-t" in cmd
        assert "test_sn" in cmd
        assert "shell" in cmd
        assert "ls" in cmd
    
    def test_assemble_command_without_sn(self):
        """测试不带SN的命令组装"""
        executor = HDCCommandExecutor(device_sn="test_sn")
        executor.hdc_path = "/path/to/hdc"
        
        cmd = executor.assemble_command(["list", "targets"], need_sn=False)
        assert "/path/to/hdc" in cmd
        assert "-t" not in cmd
    
    @patch('subprocess.Popen')
    def test_execute_success(self, mock_popen):
        """测试命令执行成功"""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = ("output", "")
        mock_popen.return_value = mock_process
        
        executor = HDCCommandExecutor(device_sn="test_sn")
        executor.hdc_path = "/path/to/hdc"
        
        result = executor.execute(["shell", "ls"])
        assert result["success"] == True
        assert result["stdout"] == "output"
    
    @patch('subprocess.Popen')
    def test_execute_failure(self, mock_popen):
        """测试命令执行失败"""
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.communicate.return_value = ("", "error message")
        mock_popen.return_value = mock_process
        
        executor = HDCCommandExecutor(device_sn="test_sn")
        executor.hdc_path = "/path/to/hdc"
        
        result = executor.execute(["shell", "invalid"])
        assert result["success"] == False
        assert result["returncode"] == 1
    
    def test_set_device(self):
        """测试设置设备"""
        executor = HDCCommandExecutor()
        executor.set_device("new_device_sn")
        assert executor.device_sn == "new_device_sn"
    
    def test_get_current_device(self):
        """测试获取当前设备"""
        executor = HDCCommandExecutor(device_sn="test_sn")
        assert executor.get_current_device() == "test_sn"