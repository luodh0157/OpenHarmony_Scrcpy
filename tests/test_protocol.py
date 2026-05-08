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
协议解析单元测试
"""

import pytest
import struct

from core.constants import PacketType, PACKET_HEADER_SIZE


class TestPacketType:
    
    def test_packet_type_values(self):
        """测试数据包类型值"""
        assert PacketType.PACKET_HEARTBEAT == 0
        assert PacketType.PACKET_SPS == 1
        assert PacketType.PACKET_PPS == 2
        assert PacketType.PACKET_KEYFRAME == 3
        assert PacketType.PACKET_FRAME == 4
        assert PacketType.PACKET_CONFIG == 5
        assert PacketType.PACKET_VPS == 6
    
    def test_packet_header_size(self):
        """测试包头大小"""
        assert PACKET_HEADER_SIZE == 8


class TestProtocolParsing:
    
    def test_parse_heartbeat_packet(self):
        """测试解析心跳包"""
        packet_type = PacketType.PACKET_HEARTBEAT
        payload_size = 0
        
        header = struct.pack('>II', packet_type, payload_size)
        parsed_type, parsed_size = struct.unpack('>II', header)
        
        assert parsed_type == PacketType.PACKET_HEARTBEAT
        assert parsed_size == 0
    
    def test_parse_sps_packet(self):
        """测试解析SPS包"""
        packet_type = PacketType.PACKET_SPS
        payload_size = 27  # SPS数据大小
        
        header = struct.pack('>II', packet_type, payload_size)
        parsed_type, parsed_size = struct.unpack('>II', header)
        
        assert parsed_type == PacketType.PACKET_SPS
        assert parsed_size == 27
    
    def test_parse_vps_packet(self):
        """测试解析VPS包（H265）"""
        packet_type = PacketType.PACKET_VPS
        payload_size = 32
        
        header = struct.pack('>II', packet_type, payload_size)
        parsed_type, parsed_size = struct.unpack('>II', header)
        
        assert parsed_type == PacketType.PACKET_VPS
        assert parsed_size == 32
    
    def test_parse_keyframe_packet(self):
        """测试解析关键帧包"""
        packet_type = PacketType.PACKET_KEYFRAME
        payload_size = 5000
        
        header = struct.pack('>II', packet_type, payload_size)
        parsed_type, parsed_size = struct.unpack('>II', header)
        
        assert parsed_type == PacketType.PACKET_KEYFRAME
        assert parsed_size == 5000
    
    def test_parse_frame_packet(self):
        """测试解析普通帧包"""
        packet_type = PacketType.PACKET_FRAME
        payload_size = 3000
        
        header = struct.pack('>II', packet_type, payload_size)
        parsed_type, parsed_size = struct.unpack('>II', header)
        
        assert parsed_type == PacketType.PACKET_FRAME
        assert parsed_size == 3000
    
    def test_parse_config_packet(self):
        """测试解析配置包"""
        packet_type = PacketType.PACKET_CONFIG
        payload_size = 100
        
        header = struct.pack('>II', packet_type, payload_size)
        parsed_type, parsed_size = struct.unpack('>II', header)
        
        assert parsed_type == PacketType.PACKET_CONFIG
        assert parsed_size == 100
    
    def test_full_packet_structure(self):
        """测试完整数据包结构"""
        packet_type = PacketType.PACKET_KEYFRAME
        payload_data = b"\x00\x00\x00\x01\x65" + b"\x00" * 100
        
        header = struct.pack('>II', packet_type, len(payload_data))
        full_packet = header + payload_data
        
        # 解析
        parsed_type, parsed_size = struct.unpack('>II', full_packet[:PACKET_HEADER_SIZE])
        parsed_payload = full_packet[PACKET_HEADER_SIZE:PACKET_HEADER_SIZE + parsed_size]
        
        assert parsed_type == PacketType.PACKET_KEYFRAME
        assert parsed_size == len(payload_data)
        assert parsed_payload == payload_data