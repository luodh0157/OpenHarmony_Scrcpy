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
测试fixtures数据可用性验证
"""

import pytest
import os
import struct


class TestFixturesData:
    """验证生成的测试fixtures数据"""
    
    @pytest.fixture
    def fixtures_dir(self):
        """获取fixtures目录路径"""
        return os.path.join(os.path.dirname(__file__), 'fixtures')
    
    def test_h264_sps_valid(self, fixtures_dir):
        """验证H264 SPS数据有效"""
        filepath = os.path.join(fixtures_dir, 'sample_sps_h264.bin')
        assert os.path.exists(filepath)
        
        with open(filepath, 'rb') as f:
            data = f.read()
        
        # 验证起始码
        assert data[:4] == b'\x00\x00\x00\x01'
        
        # 验证NAL类型 (SPS = 7)
        nal_type = data[4] & 0x1F
        assert nal_type == 7
    
    def test_h264_pps_valid(self, fixtures_dir):
        """验证H264 PPS数据有效"""
        filepath = os.path.join(fixtures_dir, 'sample_pps_h264.bin')
        assert os.path.exists(filepath)
        
        with open(filepath, 'rb') as f:
            data = f.read()
        
        assert data[:4] == b'\x00\x00\x00\x01'
        
        # 验证NAL类型 (PPS = 8)
        nal_type = data[4] & 0x1F
        assert nal_type == 8
    
    def test_h265_vps_valid(self, fixtures_dir):
        """验证H265 VPS数据有效"""
        filepath = os.path.join(fixtures_dir, 'sample_vps_h265.bin')
        assert os.path.exists(filepath)
        
        with open(filepath, 'rb') as f:
            data = f.read()
        
        assert data[:4] == b'\x00\x00\x00\x01'
        
        # 验证NAL类型 (VPS = 32)
        nal_type = (data[4] >> 1) & 0x3F
        assert nal_type == 32
    
    def test_h265_sps_valid(self, fixtures_dir):
        """验证H265 SPS数据有效"""
        filepath = os.path.join(fixtures_dir, 'sample_sps_h265.bin')
        assert os.path.exists(filepath)
        
        with open(filepath, 'rb') as f:
            data = f.read()
        
        assert data[:4] == b'\x00\x00\x00\x01'
        
        # 验证NAL类型 (SPS = 33)
        nal_type = (data[4] >> 1) & 0x3F
        assert nal_type == 33
    
    def test_h265_pps_valid(self, fixtures_dir):
        """验证H265 PPS数据有效"""
        filepath = os.path.join(fixtures_dir, 'sample_pps_h265.bin')
        assert os.path.exists(filepath)
        
        with open(filepath, 'rb') as f:
            data = f.read()
        
        assert data[:4] == b'\x00\x00\x00\x01'
        
        # 验证NAL类型 (PPS = 34)
        nal_type = (data[4] >> 1) & 0x3F
        assert nal_type == 34
    
    def test_h264_frame_valid(self, fixtures_dir):
        """验证H264帧数据有效"""
        filepath = os.path.join(fixtures_dir, 'sample_frame_h264.bin')
        assert os.path.exists(filepath)
        
        with open(filepath, 'rb') as f:
            data = f.read()
        
        assert len(data) > 0
        assert data[:4] == b'\x00\x00\x00\x01'
        
        # 验证是关键帧 (IDR = 5)
        nal_type = data[4] & 0x1F
        assert nal_type == 5
    
    def test_h265_frame_valid(self, fixtures_dir):
        """验证H265帧数据有效"""
        filepath = os.path.join(fixtures_dir, 'sample_frame_h265.bin')
        assert os.path.exists(filepath)
        
        with open(filepath, 'rb') as f:
            data = f.read()
        
        assert len(data) > 0
        assert data[:4] == b'\x00\x00\x00\x01'
        
        # 验证是关键帧 (IDR_W_RADL = 19)
        nal_type = (data[4] >> 1) & 0x3F
        assert nal_type == 19
    
    def test_device_list_valid(self, fixtures_dir):
        """验证设备列表数据有效"""
        filepath = os.path.join(fixtures_dir, 'sample_device_list.txt')
        assert os.path.exists(filepath)
        
        with open(filepath, 'r') as f:
            content = f.read()
        
        # 验证有设备数据
        assert len(content) > 0
        assert 'ohos' in content
    
    def test_config_packet_valid(self, fixtures_dir):
        """验证配置包数据有效"""
        filepath = os.path.join(fixtures_dir, 'sample_config_packet.bin')
        assert os.path.exists(filepath)
        
        with open(filepath, 'rb') as f:
            data = f.read()
        
        # 验证数据大小 (4个int32 = 16字节)
        assert len(data) == 16
        
        # 解析配置
        width, height, fps, bitrate = struct.unpack('>I I I I', data)
        
        # 验证配置值
        assert width == 720
        assert height == 1280
        assert fps == 30
        assert bitrate == 1500000