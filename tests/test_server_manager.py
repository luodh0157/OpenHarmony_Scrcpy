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
服务端管理器单元测试
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock

from core.server_manager import ServerManager
from core.constants import LogLevel


class TestServerManager:
    
    @pytest.fixture
    def mock_hdc(self):
        """创建模拟的HDC执行器"""
        hdc = Mock()
        hdc.device_sn = "test_device"
        hdc.log_title = "MockHDC"
        hdc.hdc_path = "/mock/hdc"
        hdc.execute = Mock(return_value={"success": True, "output": "mock output", "error": ""})
        hdc.execute_async_in_shell = Mock(return_value=Mock())
        return hdc
    
    @pytest.fixture
    def server_manager(self, mock_hdc):
        """创建ServerManager实例"""
        with patch.object(ServerManager, '_get_resource_path', return_value='/mock/path/server'):
            manager = ServerManager(manufacturer="default", hdc_executor=mock_hdc)
            return manager
    
    def test_init(self, server_manager, mock_hdc):
        """测试初始化"""
        assert server_manager.hdc == mock_hdc
        assert server_manager.manufacturer == "default"
        assert server_manager.log_title == "服务端管理器"
    
    def test_update_manufacturer(self, server_manager):
        """测试更新制造商"""
        server_manager.update_manufacturer("HUAWEI")
        assert server_manager.manufacturer == "HUAWEI"
    
    def test_is_installed_true(self, server_manager, mock_hdc):
        """测试已安装状态"""
        mock_hdc.check_file_exists = Mock(return_value=True)
        result = server_manager.check_server_installed()
        assert result == True

    def test_is_installed_false(self, server_manager, mock_hdc):
        """测试未安装状态"""
        mock_hdc.check_file_exists = Mock(return_value=False)
        result = server_manager.check_server_installed()
        assert result == False

    def test_is_running_true(self, server_manager, mock_hdc):
        """测试正在运行状态"""
        mock_hdc.execute.return_value = {"success": True, "stdout": "12345", "stderr": ""}
        result = server_manager.check_server_running()
        assert result == True

    def test_is_running_false(self, server_manager, mock_hdc):
        """测试未运行状态"""
        mock_hdc.execute.return_value = {"success": True, "stdout": "", "stderr": ""}
        result = server_manager.check_server_running()
        assert result == False

    def test_stop(self, server_manager, mock_hdc):
        """测试停止服务"""
        mock_hdc.execute.return_value = {"success": True, "output": ""}
        server_manager.stop_server()
        mock_hdc.execute.assert_called()

    def test_get_server_state(self, server_manager):
        """测试获取服务状态"""
        assert hasattr(server_manager, 'check_server_installed')
        assert hasattr(server_manager, 'check_server_running')
        assert hasattr(server_manager, 'stop_server')


class TestServerManagerResourcePath:
    
    def test_get_resource_path_dev_env(self):
        """测试开发环境资源路径"""
        with patch('sys._MEIPASS', None, create=True):
            with patch('os.path.dirname') as mock_dir:
                mock_dir.return_value = '/mock/core'
                with patch('os.path.abspath') as mock_abs:
                    mock_abs.return_value = '/mock/core/__file__'
                    with patch('os.path.exists', return_value=True):
                        hdc = Mock()
                        hdc.hdc_path = "/mock/hdc"
                        manager = ServerManager(manufacturer="default", hdc_executor=hdc)
                        path = manager._get_resource_path("test_file")
                        assert "test_file" in path
    
    def test_get_resource_path_pyinstaller(self):
        """测试PyInstaller打包环境资源路径"""
        with patch('sys._MEIPASS', '/mock/_MEIPASS', create=True):
            hdc = Mock()
            hdc.hdc_path = "/mock/hdc"
            manager = ServerManager(manufacturer="default", hdc_executor=hdc)
            path = manager._get_resource_path("test_file")
            assert "test_file" in path


class TestServerManufacturerHandling:
    
    @pytest.fixture
    def mock_hdc(self):
        """创建模拟的HDC执行器"""
        hdc = Mock()
        hdc.device_sn = "test_device"
        hdc.hdc_path = "/mock/hdc"
        hdc.execute = Mock(return_value={"success": True, "output": "", "error": ""})
        return hdc
    
    def test_manufacturer_default(self, mock_hdc):
        """测试default制造商"""
        with patch.object(ServerManager, '_get_resource_path', return_value='/mock/default/server'):
            manager = ServerManager(manufacturer="default", hdc_executor=mock_hdc)
            assert manager.manufacturer == "default"
    
    def test_manufacturer_huawei(self, mock_hdc):
        """测试HUAWEI制造商"""
        with patch.object(ServerManager, '_get_resource_path', return_value='/mock/HUAWEI/server'):
            manager = ServerManager(manufacturer="HUAWEI", hdc_executor=mock_hdc)
            assert manager.manufacturer == "HUAWEI"