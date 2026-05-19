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
OpenHarmony_Scrcpy 视频解码器（支持H.264和H.265）
"""

import time
import traceback
from typing import Optional, Any

from core.constants import LogLevel
from core.logger import print_log
from .config import VideoStreamConfig


class VideoDecoder:
    """通用视频解码器（支持H.264和H.265）"""
    
    def __init__(self, config: VideoStreamConfig, debug: bool = False) -> None:
        self.config = config
        self.codec_name = config.codec
        self.debug = debug
        self.log_title = "解码器"
        
        self.codec_ctx: Optional[Any] = None
        
        self.sps_data: Optional[bytes] = None
        self.pps_data: Optional[bytes] = None
        self.vps_data: Optional[bytes] = None
        
        self.extradata: bytearray = bytearray()
        
        self.vps_received: bool = False
        self.sps_received: bool = False
        self.pps_received: bool = False
        
        self.frame_count: int = 0
        self.decode_success: int = 0
        self.decode_failure: int = 0
        self.last_decode_time: float = 0
        
        self.consecutive_errors: int = 0
        self.max_consecutive_errors: int = 25
        
        self.waiting_for_keyframe: bool = False
        self.last_extradata_hash: Optional[str] = None
        self.keyframe_decode_failed: bool = False
        
        print_log(LogLevel.INFO, self.log_title, f"创建解码器实例: {config.width}x{config.height}, codec: {config.codec}")

    def update_resolution(self, width: int, height: int) -> None:
        self.config.width = width
        self.config.height = height

    def _get_codec_type(self) -> str:
        """获取PyAV解码器类型字符串"""
        if self.codec_name == "h265":
            return 'hevc'
        return 'h264'

    def _init_codec(self) -> bool:
        """初始化解码器"""
        try:
            if self.codec_ctx is not None:
                self.codec_ctx = None
            
            import av
            codec_type = self._get_codec_type()
            self.codec_ctx = av.CodecContext.create(codec_type, 'r')
            
            self.codec_ctx.width = self.config.width
            self.codec_ctx.height = self.config.height
            self.codec_ctx.pix_fmt = 'rgba'
            
            if self.extradata:
                try:
                    self.codec_ctx.extradata = self.extradata
                    print_log(LogLevel.DEBUG, self.log_title, f"设置extradata: {len(self.extradata)}字节")
                except Exception as e:
                    print_log(LogLevel.ERROR, self.log_title, f"设置extradata失败: {e}")
            
            print_log(LogLevel.INFO, self.log_title, f"CodecContext初始化成功: {codec_type}, {self.codec_ctx.width}x{self.codec_ctx.height}")
            return True
            
        except Exception as e:
            print_log(LogLevel.ERROR, self.log_title, f"初始化失败: {e}")
            traceback.print_exc()
            return False

    def is_ready(self) -> bool:
        """检查解码器是否就绪"""
        if not self.codec_ctx:
            return False
        if self.codec_name == "h265":
            return self.vps_received and self.sps_received and self.pps_received
        else:
            return self.sps_received and self.pps_received

    def set_vps(self, vps_data: bytes) -> bool:
        """设置VPS（H.265）"""
        if not vps_data:
            return False
        self.vps_data = vps_data
        self.vps_received = True
        print_log(LogLevel.DEBUG, self.log_title, f"接收VPS: {len(vps_data)}字节")
        return self._try_build_extradata()

    def set_sps(self, sps_data: bytes) -> bool:
        """设置SPS"""
        if not sps_data:
            return False
        self.sps_data = sps_data
        self.sps_received = True
        print_log(LogLevel.DEBUG, self.log_title, f"接收SPS: {len(sps_data)}字节")
        return self._try_build_extradata()

    def set_pps(self, pps_data: bytes) -> bool:
        """设置PPS"""
        if not pps_data:
            return False
        self.pps_data = pps_data
        self.pps_received = True
        print_log(LogLevel.DEBUG, self.log_title, f"接收PPS: {len(pps_data)}字节")
        return self._try_build_extradata()

    def _try_build_extradata(self) -> bool:
        """尝试构建extradata"""
        if not self._all_params_received():
            return False
        
        new_extradata = bytearray()
        
        if self.codec_name == "h265":
            if self.vps_data:
                if not self._has_start_code(self.vps_data):
                    new_extradata.extend(b'\x00\x00\x00\x01')
                new_extradata.extend(self.vps_data)
        
        if self.sps_data:
            if not self._has_start_code(self.sps_data):
                new_extradata.extend(b'\x00\x00\x00\x01')
            new_extradata.extend(self.sps_data)
        
        if self.pps_data:
            if not self._has_start_code(self.pps_data):
                new_extradata.extend(b'\x00\x00\x00\x01')
            new_extradata.extend(self.pps_data)
        
        import hashlib
        new_hash = hashlib.md5(bytes(new_extradata)).hexdigest()
        
        if self.last_extradata_hash != new_hash:
            self.extradata = new_extradata
            self.last_extradata_hash = new_hash
            print_log(LogLevel.INFO, self.log_title, f"extradata已更新: {len(self.extradata)}字节 (hash={new_hash[:8]})")
            return self._init_codec()
        else:
            print_log(LogLevel.DEBUG, self.log_title, f"extradata未变化，跳过重新初始化")
            return True

    def _all_params_received(self) -> bool:
        """检查是否已接收所有必要参数集"""
        if self.codec_name == "h265":
            return self.vps_received and self.sps_received and self.pps_received
        else:
            return self.sps_received and self.pps_received

    def _has_start_code(self, data: bytes) -> bool:
        """检查是否有起始码"""
        if len(data) < 4:
            return False
        return data[0:4] == b'\x00\x00\x00\x01' or data[0:3] == b'\x00\x00\x01'

    def decode_frame(self, frame_data: bytes, is_keyframe: bool = False):
        """解码视频帧"""
        if not frame_data or len(frame_data) == 0:
            print_log(LogLevel.WARN, self.log_title, f"空帧数据")
            return None
        
        if self.codec_ctx is None:
            print_log(LogLevel.ERROR, self.log_title, f"codec_ctx未初始化，无法解码")
            return None
        
        if self.waiting_for_keyframe and not is_keyframe:
            return None
        
        if is_keyframe:
            if self.waiting_for_keyframe:
                print_log(LogLevel.INFO, self.log_title, f"收到关键帧，恢复正常解码")
            self.waiting_for_keyframe = False
            self.keyframe_decode_failed = False
            self.consecutive_errors = 0
        
        self.frame_count += 1
        current_time = time.time()
        
        try:
            processed_data = frame_data
            
            if is_keyframe and self.extradata and len(self.extradata) > 0:
                if not self._has_start_code(processed_data):
                    processed_data = self.extradata + b'\x00\x00\x00\x01' + frame_data
                elif not processed_data.startswith(self.extradata):
                    processed_data = self.extradata + processed_data
            
            if not self._has_start_code(processed_data):
                processed_data = b'\x00\x00\x00\x01' + processed_data
            
            if self.frame_count <= 3:
                print_log(LogLevel.DEBUG, self.log_title, f"帧数据前16字节: {processed_data[:16].hex()}")
            
            try:
                import av
                packets = self.codec_ctx.parse(processed_data)
                
                if len(packets) == 0:
                    if is_keyframe:
                        print_log(LogLevel.DEBUG, self.log_title, f"parse返回空，尝试直接decode")
                        packets = [av.Packet(processed_data)]
                    else:
                        self.consecutive_errors += 1
                        self.decode_failure += 1
                        if self.consecutive_errors >= self.max_consecutive_errors:
                            print_log(LogLevel.ERROR, self.log_title, f"连续解析失败{self.consecutive_errors}次，等待关键帧")
                            self.waiting_for_keyframe = True
                            self.consecutive_errors = 0
                        return None
            except Exception as parse_error:
                self.consecutive_errors += 1
                self.decode_failure += 1
                if is_keyframe:
                    print_log(LogLevel.ERROR, self.log_title, f"关键帧解析异常: {parse_error}, 数据前16字节: {processed_data[:16].hex()}")
                    self.keyframe_decode_failed = True
                    self.waiting_for_keyframe = True
                elif self.consecutive_errors >= self.max_consecutive_errors:
                    print_log(LogLevel.ERROR, self.log_title, f"连续解析异常{self.consecutive_errors}次，等待关键帧")
                    self.waiting_for_keyframe = True
                    self.consecutive_errors = 0
                return None
            
            decoded_frame = None
            for packet in packets:
                if packet is not None:
                    try:
                        frames = self.codec_ctx.decode(packet)
                        
                        for frame in frames:
                            if isinstance(frame, av.VideoFrame):
                                rgb_array = frame.to_ndarray(format='rgb24')
                                
                                if rgb_array is not None:
                                    self.decode_success += 1
                                    self.consecutive_errors = 0
                                    self.keyframe_decode_failed = False
                                    self.last_decode_time = current_time
                                    decoded_frame = rgb_array
                                    break
                    except Exception as decode_error:
                        self.consecutive_errors += 1
                        self.decode_failure += 1
            
            if decoded_frame is not None:
                return decoded_frame
            else:
                self.decode_failure += 1
                if is_keyframe:
                    print_log(LogLevel.ERROR, self.log_title, f"关键帧解码失败！数据长度={len(processed_data)}字节")
                    self.keyframe_decode_failed = True
                    self.waiting_for_keyframe = True
                elif self.consecutive_errors >= self.max_consecutive_errors:
                    print_log(LogLevel.ERROR, self.log_title, f"连续解码失败{self.consecutive_errors}次，等待关键帧")
                    self.waiting_for_keyframe = True
                    self.consecutive_errors = 0
                return None
            
        except Exception as e:
            print_log(LogLevel.ERROR, self.log_title, f"解码异常: {e}")
            self.decode_failure += 1
            self.consecutive_errors += 1
            if is_keyframe:
                self.keyframe_decode_failed = True
                self.waiting_for_keyframe = True
                print_log(LogLevel.ERROR, self.log_title, f"关键帧解码异常！")
            elif self.consecutive_errors >= self.max_consecutive_errors:
                self.waiting_for_keyframe = True
                self.consecutive_errors = 0
            return None
    
    def cleanup(self) -> None:
        """清理解码器资源"""
        print_log(LogLevel.INFO, self.log_title, f"清理资源...")
        self.codec_ctx = None
        self.sps_data = None
        self.pps_data = None
        self.vps_data = None
        self.extradata = None
        self.waiting_for_keyframe = False
        self.keyframe_decode_failed = False
        self.last_extradata_hash = None
        self.consecutive_errors = 0


__all__ = ["VideoDecoder"]