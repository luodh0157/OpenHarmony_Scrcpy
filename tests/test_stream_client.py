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
视频流客户端单元测试
"""

import pytest
import socket
import struct
import queue
from unittest.mock import Mock, patch, MagicMock, create_autospec

from video.stream_client import VideoStreamClient
from video.config import VideoStreamConfig
from core.constants import PacketType, LogLevel


class TestVideoStreamClientInit:
    
    @pytest.fixture
    def mock_device_manager(self):
        """创建模拟的设备管理器"""
        manager = Mock()
        manager.log_title = "MockDeviceManager"
        manager.get_current_device = Mock(return_value="test_device")
        manager.get_port_forwarding = Mock(return_value=27183)
        manager.remove_port_forwarding = Mock()
        manager.stop_server = Mock()
        return manager
    
    def test_init(self, mock_device_manager):
        """测试初始化"""
        client = VideoStreamClient(device_manager=mock_device_manager)
        assert client.device_manager == mock_device_manager
        assert client.socket is None
        assert client.is_connected == False
        assert client.is_streaming == False
        assert client.frame_queue.maxsize == 50
    
    def test_init_with_callback(self, mock_device_manager):
        """测试带回调初始化"""
        callback = Mock()
        client = VideoStreamClient(device_manager=mock_device_manager, on_frame_decoded=callback)
        assert client.on_frame_decoded == callback
    
    def test_init_with_debug(self, mock_device_manager):
        """测试带调试模式初始化"""
        client = VideoStreamClient(device_manager=mock_device_manager, debug=True)
        assert client.debug == True


class TestVideoStreamClientQueue:
    
    @pytest.fixture
    def client(self):
        """创建客户端实例"""
        manager = Mock()
        manager.log_title = "Mock"
        manager.stop_server = Mock()
        manager.get_port_forwarding = Mock(return_value=0)
        manager.remove_port_forwarding = Mock()
        return VideoStreamClient(device_manager=manager)
    
    def test_frame_queue_size(self, client):
        """测试帧队列大小限制"""
        assert client.frame_queue.maxsize == 50
    
    def test_get_current_frame_empty(self, client):
        """测试空队列获取帧"""
        frame = client.get_current_frame(timeout=0.001)
        assert frame is None
    
    def test_put_frame_to_queue(self, client):
        """测试帧入队"""
        import numpy as np
        test_frame = np.zeros((100, 100, 3), dtype=np.uint8)
        client.frame_queue.put_nowait(test_frame)
        assert client.frame_queue.qsize() == 1
        
        retrieved = client.get_current_frame(timeout=0.001)
        assert retrieved is not None
        assert retrieved.shape == (100, 100, 3)


class TestVideoStreamClientConfig:
    
    @pytest.fixture
    def client(self):
        """创建客户端实例"""
        manager = Mock()
        manager.log_title = "Mock"
        manager.stop_server = Mock()
        manager.get_port_forwarding = Mock(return_value=0)
        manager.remove_port_forwarding = Mock()
        return VideoStreamClient(device_manager=manager)
    
    def test_config_defaults(self, client):
        """测试默认配置"""
        assert client.config.width > 0
        assert client.config.height > 0
        assert client.config.fps > 0
    
    def test_queue_threshold(self, client):
        """测试队列阈值"""
        assert client.queue_threshold == 35


class TestVideoStreamClientPacketHandling:
    
    @pytest.fixture
    def client_with_decoder(self):
        """创建带解码器的客户端"""
        manager = Mock()
        manager.log_title = "Mock"
        manager.stop_server = Mock()
        manager.get_port_forwarding = Mock(return_value=0)
        manager.remove_port_forwarding = Mock()
        
        client = VideoStreamClient(device_manager=manager)
        client.decoder = Mock()
        client.decoder.is_ready = Mock(return_value=True)
        client.decoder.waiting_for_keyframe = False
        client.decoder.decode_frame = Mock(return_value=None)
        client.vps_received = True
        client.sps_received = True
        client.pps_received = True
        return client
    
    def test_handle_heartbeat_packet(self, client_with_decoder):
        """测试心跳包处理"""
        packet_data = b''
        client_with_decoder._handle_packet(PacketType.PACKET_HEARTBEAT, 0, packet_data)
        assert client_with_decoder.last_heartbeat_time > 0
    
    def test_handle_config_packet(self, client_with_decoder):
        """测试配置包处理"""
        config_data = struct.pack('>I I I I', 720, 1280, 30, 1500000)
        client_with_decoder._handle_packet(PacketType.PACKET_CONFIG, 16, config_data)
        assert client_with_decoder.config.width == 720
        assert client_with_decoder.config.height == 1280
    
    def test_handle_vps_packet(self, client_with_decoder):
        """测试VPS包处理"""
        vps_data = b'\x00\x00\x00\x01\x40\x01'
        client_with_decoder._handle_packet(PacketType.PACKET_VPS, len(vps_data), vps_data)
        client_with_decoder.decoder.set_vps.assert_called_once()
    
    def test_handle_sps_packet(self, client_with_decoder):
        """测试SPS包处理"""
        sps_data = b'\x00\x00\x00\x01\x42\x01'
        client_with_decoder._handle_packet(PacketType.PACKET_SPS, len(sps_data), sps_data)
        client_with_decoder.decoder.set_sps.assert_called_once()
    
    def test_handle_pps_packet(self, client_with_decoder):
        """测试PPS包处理"""
        pps_data = b'\x00\x00\x00\x01\x44\x01'
        client_with_decoder._handle_packet(PacketType.PACKET_PPS, len(pps_data), pps_data)
        client_with_decoder.decoder.set_pps.assert_called_once()


class TestVideoStreamClientDisconnect:
    
    @pytest.fixture
    def connected_client(self):
        """创建已连接的客户端"""
        manager = Mock()
        manager.log_title = "Mock"
        manager.stop_server = Mock()
        manager.get_port_forwarding = Mock(return_value=27183)
        manager.remove_port_forwarding = Mock()
        
        client = VideoStreamClient(device_manager=manager)
        client.is_connected = True
        client.is_streaming = True
        client.socket = Mock()
        client.socket.close = Mock()
        client.decoder = Mock()
        client.decoder.cleanup = Mock()
        client.heartbeat_thread = Mock()
        client.heartbeat_thread.is_alive = Mock(return_value=False)
        client.monitor_thread = Mock()
        client.monitor_thread.is_alive = Mock(return_value=False)
        return client
    
    def test_disconnect_sets_flags(self, connected_client):
        """测试断开连接设置标志"""
        connected_client.disconnect()
        assert connected_client.is_connected == False
        assert connected_client.is_streaming == False
    
    def test_disconnect_calls_cleanup(self, connected_client):
        """测试断开连接调用清理"""
        connected_client.disconnect()
        connected_client.decoder.cleanup.assert_called()
    
    def test_disconnect_clears_socket(self, connected_client):
        """测试断开连接清理socket"""
        connected_client.disconnect()
        assert connected_client.socket is None


class TestVideoStreamClientStatistics:
    
    @pytest.fixture
    def client(self):
        """创建客户端实例"""
        manager = Mock()
        manager.log_title = "Mock"
        manager.stop_server = Mock()
        manager.get_port_forwarding = Mock(return_value=0)
        manager.remove_port_forwarding = Mock()
        return VideoStreamClient(device_manager=manager)
    
    def test_initial_statistics(self, client):
        """测试初始统计值"""
        assert client.frame_count == 0
        assert client.total_bytes == 0
        assert client.decode_failure == 0
    
    def test_statistics_counters(self, client):
        """测试统计计数器"""
        client.frame_count = 100
        client.total_bytes = 1024
        client.decode_failure = 5
        assert client.frame_count == 100
        assert client.total_bytes == 1024
        assert client.decode_failure == 5