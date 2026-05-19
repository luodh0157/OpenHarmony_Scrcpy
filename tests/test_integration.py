#!/usr/bin/env python

"""
集成测试 - 测试组件间的真实交互（不 Mock 核心依赖）
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch, MagicMock

from core import HDCCommandExecutor, DeviceManager, DeviceInfo, ServerDeployState
from core.exceptions import StreamConnectError
from gui.device_controller import DeviceController
from gui.connection_manager import ConnectionManager, ConnectionState
from gui.video_display import VideoDisplay
from gui.server_deployer import ServerDeployer


class TestDeviceManagerServerManagerIntegration:
    """测试 DeviceManager 和 ServerManager 的解耦交互"""
    
    @pytest.fixture
    def hdc_executor(self):
        """创建真实的 HDCCommandExecutor（Mock execute 方法避免真实调用）"""
        executor = HDCCommandExecutor()
        executor.execute = Mock(return_value={"success": True, "stdout": "", "stderr": ""})
        return executor
    
    @pytest.fixture
    def device_manager(self, hdc_executor):
        """创建真实的 DeviceManager"""
        return DeviceManager(hdc_executor)
    
    def test_create_server_manager(self, device_manager, hdc_executor):
        """测试创建 ServerManager"""
        sm = device_manager.create_server_manager("default")
        assert sm is not None
        assert sm.manufacturer == "default"
        assert sm.hdc == hdc_executor
    
    def test_server_manager_reuse_via_connection_manager(self, device_manager, hdc_executor):
        """测试通过 ConnectionManager 复用 ServerManager"""
        cm = ConnectionManager(
            device_manager=device_manager,
            hdc_executor=hdc_executor,
            on_frame_decoded=Mock(),
        )
        
        # 第一次设置
        sm1 = device_manager.create_server_manager("huawei")
        cm.set_server_manager(sm1)
        assert cm.get_server_manager().manufacturer == "huawei"
        
        # 第二次设置不同 manufacturer，应该复用已有实例
        sm2 = device_manager.create_server_manager("default")
        cm.set_server_manager(sm2)
        # 应该还是同一个对象，只更新了 manufacturer
        assert cm.get_server_manager() is sm1
        assert cm.get_server_manager().manufacturer == "default"
    
    def test_ensure_server_manager_creates_new(self, device_manager, hdc_executor):
        """测试 ensure_server_manager 首次创建"""
        cm = ConnectionManager(
            device_manager=device_manager,
            hdc_executor=hdc_executor,
            on_frame_decoded=Mock(),
        )
        
        assert cm.get_server_manager() is None
        cm.ensure_server_manager("default", hdc_executor)
        assert cm.get_server_manager() is not None
        assert cm.get_server_manager().manufacturer == "default"
    
    def test_ensure_server_manager_reuses_existing(self, device_manager, hdc_executor):
        """测试 ensure_server_manager 复用已有实例"""
        cm = ConnectionManager(
            device_manager=device_manager,
            hdc_executor=hdc_executor,
            on_frame_decoded=Mock(),
        )
        
        # 首次创建
        cm.ensure_server_manager("huawei", hdc_executor)
        first_sm = cm.get_server_manager()
        
        # 再次调用，应该复用
        cm.ensure_server_manager("default", hdc_executor)
        second_sm = cm.get_server_manager()
        
        assert first_sm is second_sm
        assert second_sm.manufacturer == "default"


class TestDeviceControllerReuse:
    """测试 DeviceController 的复用和 reset"""
    
    @pytest.fixture
    def hdc_executor(self):
        executor = HDCCommandExecutor()
        executor.execute = Mock(return_value={"success": True, "stdout": "", "stderr": ""})
        return executor
    
    @pytest.fixture
    def controller(self, hdc_executor):
        return DeviceController(hdc_executor)
    
    def test_initial_state(self, controller):
        """测试初始状态"""
        assert controller.display_width == 0
        assert controller.display_height == 0
        assert controller.display_ratio == 0.0
        assert controller.left == 0
        assert controller.right == 0
        assert controller.top == 0
        assert controller.bottom == 0
        assert controller.drag_start is None
    
    def test_reset_clears_all_state(self, controller):
        """测试 reset 清除所有状态"""
        # 先设置一些值
        controller.display_width = 400
        controller.display_height = 712
        controller.display_ratio = 0.556
        controller.left = 100
        controller.right = 500
        controller.top = 50
        controller.bottom = 762
        controller.drag_start = (10, 20)
        
        controller.reset()
        
        assert controller.display_width == 0
        assert controller.display_height == 0
        assert controller.display_ratio == 0.0
        assert controller.left == 0
        assert controller.right == 0
        assert controller.top == 0
        assert controller.bottom == 0
        assert controller.drag_start is None
    
    def test_reset_does_not_unbind_canvas(self, controller):
        """测试 reset 不会解绑 canvas（避免事件丢失）"""
        mock_canvas = Mock()
        controller.bind_video_canvas(mock_canvas)
        
        # 验证绑定过
        assert mock_canvas.bind.call_count == 3
        
        controller.reset()
        
        # reset 不应该调用 unbind
        assert mock_canvas.unbind.call_count == 0
        # video_canvas 应该保持
        assert controller.video_canvas is mock_canvas
    
    def test_multiple_connect_disconnect_cycles(self, controller):
        """测试多次连接/断开循环"""
        mock_canvas = Mock()
        mock_canvas.winfo_width = Mock(return_value=800)
        mock_canvas.winfo_height = Mock(return_value=600)
        controller.bind_video_canvas(mock_canvas)
        
        for i in range(5):
            # 模拟连接
            controller.set_display_resolution(720, 1280, 800, 600)
            controller.drag_start = (10, 20)
            
            assert controller.display_width > 0
            assert controller.drag_start == (10, 20)
            
            # 模拟断开
            controller.reset()
            
            assert controller.display_width == 0
            assert controller.drag_start is None
        
        # canvas 应该只绑定了一次
        assert mock_canvas.bind.call_count == 3


class TestConnectionManagerLifecycle:
    """测试 ConnectionManager 的完整生命周期"""
    
    @pytest.fixture
    def hdc_executor(self):
        executor = HDCCommandExecutor()
        executor.execute = Mock(return_value={"success": True, "stdout": "", "stderr": ""})
        return executor
    
    @pytest.fixture
    def device_manager(self, hdc_executor):
        return DeviceManager(hdc_executor)
    
    @pytest.fixture
    def connection_manager(self, device_manager, hdc_executor):
        return ConnectionManager(
            device_manager=device_manager,
            hdc_executor=hdc_executor,
            on_frame_decoded=Mock(),
            on_state_changed=Mock(),
        )
    
    def test_initial_state(self, connection_manager):
        """测试初始状态"""
        assert connection_manager.state == ConnectionState.DISCONNECTED
        assert connection_manager.is_connected == False
        assert connection_manager.get_server_manager() is None
    
    def test_state_transitions(self, connection_manager):
        """测试状态转换"""
        assert connection_manager.state == ConnectionState.DISCONNECTED
        
        # 模拟连接中
        connection_manager._set_state(ConnectionState.CONNECTING)
        assert connection_manager.state == ConnectionState.CONNECTING
        
        # 模拟已连接
        connection_manager._set_state(ConnectionState.CONNECTED)
        assert connection_manager.is_connected == True
        
        # 模拟断开中
        connection_manager._set_state(ConnectionState.DISCONNECTING)
        assert connection_manager.state == ConnectionState.DISCONNECTING
        
        # 模拟已断开
        connection_manager._set_state(ConnectionState.DISCONNECTED)
        assert connection_manager.is_connected == False
    
    def test_disconnect_without_connect(self, connection_manager):
        """测试未连接时断开不应报错"""
        connection_manager.disconnect()
        assert connection_manager.state == ConnectionState.DISCONNECTED


class TestVideoDisplayReset:
    """测试 VideoDisplay 的 reset 功能"""
    
    @pytest.fixture
    def video_display(self):
        mock_root = Mock()
        mock_canvas = Mock()
        mock_canvas.winfo_width = Mock(return_value=800)
        mock_canvas.winfo_height = Mock(return_value=600)
        mock_device_controller = Mock()
        mock_performance_label = Mock()
        return VideoDisplay(
            root=mock_root,
            canvas=mock_canvas,
            device_controller=mock_device_controller,
            performance_label=mock_performance_label
        )
    
    def test_reset_clears_display_state(self, video_display):
        """测试 reset 清除显示状态"""
        video_display.video_width = 720
        video_display.video_height = 1280
        video_display.video_ratio = 0.556
        video_display.display_width = 400
        video_display.display_height = 712
        video_display.displayed_frames = 1000
        video_display.frame_counter = 50
        video_display.current_frame = "some_frame"
        video_display.tk_image = "some_image"
        video_display.image_refs = ["ref1", "ref2"]
        video_display._render_scheduled = True
        
        video_display.reset()
        
        assert video_display.video_width == 0
        assert video_display.video_height == 0
        assert video_display.video_ratio == 0.0
        assert video_display.display_width == 0
        assert video_display.display_height == 0
        assert video_display.displayed_frames == 0
        assert video_display.frame_counter == 0
        assert video_display.current_frame is None
        assert video_display.tk_image is None
        assert video_display.image_refs == []
        assert video_display._render_scheduled == False


class TestFullIntegrationScenario:
    """完整集成场景测试"""
    
    @pytest.fixture
    def hdc_executor(self):
        executor = HDCCommandExecutor()
        executor.execute = Mock(return_value={"success": True, "stdout": "", "stderr": ""})
        return executor
    
    @pytest.fixture
    def device_manager(self, hdc_executor):
        return DeviceManager(hdc_executor)
    
    def test_device_switch_scenario(self, hdc_executor, device_manager):
        """模拟设备切换场景：连接设备A -> 断开 -> 连接设备B"""
        # 初始化组件
        cm = ConnectionManager(
            device_manager=device_manager,
            hdc_executor=hdc_executor,
            on_frame_decoded=Mock(),
        )
        controller = DeviceController(hdc_executor)
        mock_canvas = Mock()
        mock_canvas.winfo_width = Mock(return_value=800)
        mock_canvas.winfo_height = Mock(return_value=600)
        controller.bind_video_canvas(mock_canvas)
        
        # 第一次连接设备A
        cm.ensure_server_manager("huawei", hdc_executor)
        controller.set_display_resolution(720, 1280, 800, 600)
        cm._set_state(ConnectionState.CONNECTED)
        
        assert cm.get_server_manager().manufacturer == "huawei"
        assert controller.display_width > 0
        assert cm.is_connected == True
        
        # 断开连接
        controller.reset()
        cm._set_state(ConnectionState.DISCONNECTED)
        
        assert controller.display_width == 0
        assert controller.video_canvas is mock_canvas  # canvas 未解绑
        assert cm.is_connected == False
        
        # 第二次连接设备B（复用组件）
        cm.ensure_server_manager("default", hdc_executor)
        controller.set_display_resolution(1080, 1920, 800, 600)
        cm._set_state(ConnectionState.CONNECTED)
        
        assert cm.get_server_manager().manufacturer == "default"
        assert controller.display_width > 0
        assert cm.is_connected == True
        assert controller.video_canvas is mock_canvas  # 同一个 canvas
        
        # 验证 canvas 只绑定了一次
        assert mock_canvas.bind.call_count == 3
    
    def test_multiple_device_switches_no_leak(self, hdc_executor, device_manager):
        """测试多次设备切换无资源泄漏"""
        cm = ConnectionManager(
            device_manager=device_manager,
            hdc_executor=hdc_executor,
            on_frame_decoded=Mock(),
        )
        controller = DeviceController(hdc_executor)
        mock_canvas = Mock()
        mock_canvas.winfo_width = Mock(return_value=800)
        mock_canvas.winfo_height = Mock(return_value=600)
        controller.bind_video_canvas(mock_canvas)
        
        manufacturers = ["huawei", "default", "xiaomi", "oppo", "vivo"]
        
        for i, manu in enumerate(manufacturers):
            # 断开
            controller.reset()
            cm._set_state(ConnectionState.DISCONNECTED)
            
            # 连接新设备
            cm.ensure_server_manager(manu, hdc_executor)
            controller.set_display_resolution(720 + i, 1280 + i, 800, 600)
            cm._set_state(ConnectionState.CONNECTED)
            
            assert cm.get_server_manager().manufacturer == manu
            assert controller.display_width > 0
            assert cm.is_connected == True
        
        # 验证 canvas 始终只绑定了一次
        assert mock_canvas.bind.call_count == 3
        # 验证 ServerManager 始终是同一个对象
        assert cm.get_server_manager() is not None
