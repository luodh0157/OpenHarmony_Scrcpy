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
设备管理器单元测试
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from core.hdc_executor import HDCCommandExecutor
from core.device_manager import DeviceManager, DeviceInfo


class TestDeviceInfo:
    
    def test_device_info_creation(self):
        """测试设备信息创建"""
        device = DeviceInfo(sn="1234567890abcdef", model="TestModel", manufacturer="HUAWEI")
        assert device.sn == "1234567890abcdef"
        assert device.model == "TestModel"
        assert device.manufacturer == "HUAWEI"
    
    def test_display_name(self):
        """测试显示名称生成"""
        device = DeviceInfo(sn="1234567890abcdef12345678", model="ohos")
        display_name = device.display_name()
        assert "12345678" in display_name
        assert "****" in display_name
        assert "ohos" in display_name


class TestDeviceManager:
    
    def test_init(self):
        """测试初始化"""
        mock_hdc = Mock()
        manager = DeviceManager(mock_hdc)
        assert manager.hdc == mock_hdc
        assert manager.devices == []
        assert manager.current_device is None
    
    @patch.object(HDCCommandExecutor, 'execute')
    def test_discover_devices_empty(self, mock_execute):
        """测试发现设备（空列表）"""
        mock_execute.return_value = {"success": True, "stdout": "[Empty]"}
        
        mock_hdc = Mock()
        mock_hdc.execute = mock_execute
        
        manager = DeviceManager(mock_hdc)
        devices = manager.discover_devices()
        assert devices == []
    
    @patch.object(HDCCommandExecutor, 'execute')
    def test_discover_devices_success(self, mock_execute):
        """测试发现设备成功"""
        mock_execute.side_effect = [
            {"success": True, "stdout": "device_sn_1\ndevice_sn_2"},
            {"success": True, "stdout": "model1"},
            {"success": True, "stdout": "HUAWEI"},
            {"success": True, "stdout": "model2"},
            {"success": True, "stdout": "default"},
        ]
        
        mock_hdc = Mock()
        mock_hdc.execute = mock_execute
        mock_hdc.set_device = Mock()
        
        manager = DeviceManager(mock_hdc)
        devices = manager.discover_devices()
        assert len(devices) == 2
    
    def test_select_device(self):
        """测试选择设备"""
        mock_hdc = Mock()
        manager = DeviceManager(mock_hdc)
        
        device1 = DeviceInfo(sn="sn1", model="model1", manufacturer="HUAWEI")
        device2 = DeviceInfo(sn="sn2", model="model2", manufacturer="default")
        manager.devices = [device1, device2]
        
        result = manager.select_device("sn2")
        assert result == True
        assert manager.current_device == device2
    
    def test_select_device_not_found(self):
        """测试选择不存在设备"""
        mock_hdc = Mock()
        manager = DeviceManager(mock_hdc)
        manager.devices = [DeviceInfo(sn="sn1", model="model1")]
        
        result = manager.select_device("unknown_sn")
        assert result == False
    
    def test_get_current_device(self):
        """测试获取当前设备"""
        mock_hdc = Mock()
        manager = DeviceManager(mock_hdc)
        device = DeviceInfo(sn="sn1", model="model1")
        manager.current_device = device
        
        assert manager.get_current_device() == device
    
    def test_reset_port_forwarding(self):
        """测试重置端口转发"""
        mock_hdc = Mock()
        manager = DeviceManager(mock_hdc)
        manager.port_forwarding = 27183
        
        manager.reset_port_forwarding()
        assert manager.port_forwarding == -1