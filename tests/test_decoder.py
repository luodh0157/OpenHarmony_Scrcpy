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
视频解码器单元测试
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from video.decoder import VideoDecoder
from video.config import VideoStreamConfig


class TestVideoDecoder:
    
    def test_init_h264(self):
        """测试H264解码器初始化"""
        config = VideoStreamConfig(width=720, height=1280, codec="h264")
        decoder = VideoDecoder(config)
        assert decoder.codec_name == "h264"
        assert decoder.config.width == 720
        assert decoder.config.height == 1280
    
    def test_init_h265(self):
        """测试H265解码器初始化"""
        config = VideoStreamConfig(width=720, height=1280, codec="h265")
        decoder = VideoDecoder(config)
        assert decoder.codec_name == "h265"
    
    def test_update_resolution(self):
        """测试更新分辨率"""
        config = VideoStreamConfig(width=720, height=1280)
        decoder = VideoDecoder(config)
        
        decoder.update_resolution(1080, 1920)
        assert decoder.config.width == 1080
        assert decoder.config.height == 1920
    
    def test_get_codec_type_h264(self):
        """测试获取H264 codec类型"""
        config = VideoStreamConfig(codec="h264")
        decoder = VideoDecoder(config)
        
        codec_type = decoder._get_codec_type()
        assert codec_type == "h264"
    
    def test_get_codec_type_h265(self):
        """测试获取H265 codec类型"""
        config = VideoStreamConfig(codec="h265")
        decoder = VideoDecoder(config)
        
        codec_type = decoder._get_codec_type()
        assert codec_type == "hevc"
    
    def test_is_ready_h264(self):
        """测试H264就绪状态"""
        config = VideoStreamConfig(codec="h264")
        decoder = VideoDecoder(config)
        
        # 未接收SPS/PPS，未就绪
        assert decoder.is_ready() == False
        
        # 接收SPS
        decoder.sps_received = True
        decoder.sps_data = b"test_sps"
        assert decoder.is_ready() == False
        
        # 接收PPS
        decoder.pps_received = True
        decoder.pps_data = b"test_pps"
        decoder.codec_ctx = Mock()  # 模拟已初始化
        assert decoder.is_ready() == True
    
    def test_is_ready_h265(self):
        """测试H265就绪状态"""
        config = VideoStreamConfig(codec="h265")
        decoder = VideoDecoder(config)
        
        # 未接收VPS/SPS/PPS，未就绪
        assert decoder.is_ready() == False
        
        # 仅接收SPS/PPS，未就绪（缺少VPS）
        decoder.sps_received = True
        decoder.pps_received = True
        assert decoder.is_ready() == False
        
        # 接收VPS
        decoder.vps_received = True
        decoder.codec_ctx = Mock()
        assert decoder.is_ready() == True
    
    def test_set_sps(self):
        """测试设置SPS"""
        config = VideoStreamConfig()
        decoder = VideoDecoder(config)
        
        sps_data = b"\x00\x00\x00\x01\x67"  # 模拟SPS数据
        result = decoder.set_sps(sps_data)
        
        assert decoder.sps_data == sps_data
        assert decoder.sps_received == True
    
    def test_set_pps(self):
        """测试设置PPS"""
        config = VideoStreamConfig()
        decoder = VideoDecoder(config)
        
        pps_data = b"\x00\x00\x00\x01\x68"  # 模拟PPS数据
        result = decoder.set_pps(pps_data)
        
        assert decoder.pps_data == pps_data
        assert decoder.pps_received == True
    
    def test_set_vps(self):
        """测试设置VPS"""
        config = VideoStreamConfig(codec="h265")
        decoder = VideoDecoder(config)
        
        vps_data = b"\x00\x00\x00\x01\x40"  # 模拟VPS数据
        result = decoder.set_vps(vps_data)
        
        assert decoder.vps_data == vps_data
        assert decoder.vps_received == True
    
    def test_has_start_code_true(self):
        """测试检测起始码（存在）"""
        config = VideoStreamConfig()
        decoder = VideoDecoder(config)
        
        data_with_start_code = b"\x00\x00\x00\x01\x65"
        assert decoder._has_start_code(data_with_start_code) == True
    
    def test_has_start_code_false(self):
        """测试检测起始码（不存在）"""
        config = VideoStreamConfig()
        decoder = VideoDecoder(config)
        
        data_without_start_code = b"\x65\x00\x00\x00"
        assert decoder._has_start_code(data_without_start_code) == False
    
    def test_has_start_code_short_data(self):
        """测试检测起始码（数据过短）"""
        config = VideoStreamConfig()
        decoder = VideoDecoder(config)
        
        short_data = b"\x00"
        assert decoder._has_start_code(short_data) == False
    
    def test_cleanup(self):
        """测试清理资源"""
        config = VideoStreamConfig()
        decoder = VideoDecoder(config)
        decoder.codec_ctx = Mock()
        decoder.sps_data = b"test"
        decoder.pps_data = b"test"
        
        decoder.cleanup()
        
        assert decoder.codec_ctx is None
        assert decoder.sps_data is None
        assert decoder.pps_data is None
    
    def test_all_params_received_h264(self):
        """测试H264参数集接收完成检查"""
        config = VideoStreamConfig(codec="h264")
        decoder = VideoDecoder(config)
        
        # 未接收
        assert decoder._all_params_received() == False
        
        # 仅SPS
        decoder.sps_received = True
        assert decoder._all_params_received() == False
        
        # SPS+PPS
        decoder.pps_received = True
        assert decoder._all_params_received() == True
    
    def test_all_params_received_h265(self):
        """测试H265参数集接收完成检查"""
        config = VideoStreamConfig(codec="h265")
        decoder = VideoDecoder(config)
        
        # 未接收
        assert decoder._all_params_received() == False
        
        # 仅SPS+PPS（缺少VPS）
        decoder.sps_received = True
        decoder.pps_received = True
        assert decoder._all_params_received() == False
        
        # VPS+SPS+PPS
        decoder.vps_received = True
        assert decoder._all_params_received() == True