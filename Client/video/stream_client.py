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
OpenHarmony_Scrcpy 视频流客户端
"""

import socket
import threading
import queue
import time
import struct
import traceback
from typing import Optional, Callable, Tuple, Any

from core.constants import HOST, HEARTBEAT_TIMEOUT, HEARTBEAT_INTERVAL, PACKET_HEADER_SIZE, PacketType, LogLevel
from core.logger import print_log
from core.device_manager import DeviceManager
from .config import VideoStreamConfig
from .decoder import VideoDecoder


class VideoStreamClient:
    """视频流客户端 - 优化数据包处理"""
    
    def __init__(self, device_manager: DeviceManager, on_frame_decoded: Optional[Callable] = None, debug: bool = False) -> None:
        self.socket: Optional[socket.socket] = None
        self.is_connected: bool = False
        self.is_streaming: bool = False
        self.config: VideoStreamConfig = VideoStreamConfig()
        self.device_manager: DeviceManager = device_manager
        
        self.decoder: Optional[VideoDecoder] = None
        self.sps_received: bool = False
        self.pps_received: bool = False
        self.vps_received: bool = False
        self.sps_data: Optional[bytes] = None
        self.pps_data: Optional[bytes] = None
        self.vps_data: Optional[bytes] = None
        
        self.raw_frame_queue: queue.Queue[Tuple[bytes, bool, int]] = queue.Queue(maxsize=100)
        self.frame_queue: queue.Queue = queue.Queue(maxsize=50)
        
        self.on_frame_decoded: Optional[Callable] = on_frame_decoded
        
        self.frame_count: int = 0
        self.total_bytes: int = 0
        self.decode_failure: int = 0
        self.last_data_time: float = 0
        self.last_heartbeat_time: float = 0
        self.last_frame_time: float = 0
        self.last_print_frame_count: int = 0
        
        self.recv_buffer: bytearray = bytearray()
        
        self._stop_event: threading.Event = threading.Event()
        
        self.heartbeat_thread: Optional[threading.Thread] = None
        self.monitor_thread: Optional[threading.Thread] = None
        self.decode_thread: Optional[threading.Thread] = None
        
        self.fps_counter: int = 0
        self.last_fps_check: float = time.time()
        
        self.queue_threshold: int = 35
        
        self.packet_count: int = 0
        self.bad_packet_bytes: int = 0
        
        self.debug: bool = debug
        self.log_title: str = "视频客户端"
        print_log(LogLevel.INFO, self.log_title, f"初始化完成")

    def connect(self, host: str, port: int, timeout: float = 5.0, 
                max_retries: int = 3, retry_interval: float = 1.0) -> bool:
        """连接视频流服务器（支持重试）"""
        for retry in range(max_retries):
            if retry > 0:
                print_log(LogLevel.INFO, self.log_title, f"连接失败，第{retry}次重试...")
                time.sleep(retry_interval)
            
            if self._try_connect(host, port, timeout):
                return True
        
        print_log(LogLevel.ERROR, self.log_title, f"连接失败，已重试{max_retries}次")
        return False
    
    def _try_connect(self, host: str, port: int, timeout: float) -> bool:
        """单次连接尝试"""
        try:
            print_log(LogLevel.INFO, self.log_title, f"连接服务器 {host}:{port}...")
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(timeout)
            
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            
            self.socket.connect((host, port))
            print_log(LogLevel.INFO, self.log_title, f"TCP连接成功，等待服务端配置...")
            
            if self._receive_config():
                print_log(LogLevel.INFO, self.log_title, f"配置接收成功: {self.config.width}x{self.config.height}@{self.config.fps}fps")
                self.is_connected = True
                
                self.last_data_time = time.time()
                self.last_heartbeat_time = time.time()
                self.last_frame_time = time.time()
                
                self.decoder = VideoDecoder(self.config, debug=self.debug)
                
                self.sps_received = False
                self.pps_received = False
                self.vps_received = False
                self.sps_data = None
                self.pps_data = None
                self.vps_data = None
                
                self._start_workers()
                print_log(LogLevel.INFO, self.log_title, f"连接成功")
                return True
            
        except Exception as e:
            print_log(LogLevel.WARN, self.log_title, f"连接尝试失败: {e}")
        
        self._cleanup_socket()
        return False
    
    def _cleanup_socket(self) -> None:
        """清理socket资源"""
        if self.socket:
            try:
                self.socket.close()
            except OSError:
                pass
            self.socket = None

    def _receive_config(self) -> bool:
        """接收服务器配置信息"""
        try:
            if not self.socket:
                return False
            
            self.socket.settimeout(5.0)
            
            # 接收配置信息
            buffer = b""
            start_time = time.time()
            
            while time.time() - start_time < 5.0:
                try:
                    chunk = self.socket.recv(1024)
                    if not chunk:
                        continue
                    
                    buffer += chunk
                    
                    if b'\n' in buffer:
                        config_line, remaining = buffer.split(b'\n', 1)
                        config_str = config_line.decode('utf-8', errors='ignore').strip()
                        
                        if config_str.startswith("SCREEN_INFO:"):
                            print_log(LogLevel.DEBUG, self.log_title, f"接收到配置: [{config_str}]")
                            parts = config_str.split(':')
                            if len(parts) >= 6:
                                self.config.width = int(parts[1])
                                self.config.height = int(parts[2])
                                self.config.fps = int(parts[3])
                                self.config.bitrate = int(parts[4])
                                self.config.codec = parts[5] if len(parts) > 5 else "h264"
                                print_log(LogLevel.INFO, self.log_title, f"解析配置:"
                                      f" {self.config.width}x{self.config.height}@{self.config.fps}fps"
                                      f" bitrate:{self.config.bitrate} codec:{self.config.codec}")
                                
                                # 发送配置确认应答
                                ack_msg ="CONFIG_ACK\n"
                                self.socket.sendall(ack_msg.encode())
                                
                                # 设置剩余数据为缓冲区
                                self.recv_buffer = bytearray(remaining)
                                return True
                        
                        break
                    
                except socket.timeout:
                    continue
            
            print_log(LogLevel.ERROR, self.log_title, f"等待接收配置超时！")
            return False
            
        except Exception as e:
            print_log(LogLevel.ERROR, self.log_title, f"接收配置失败: {e}")
            return False

    def _start_workers(self) -> None:
        """启动工作线程"""
        self._stop_event.clear()
        self.is_streaming = True
        
        recv_thread = threading.Thread(target=self._receive_thread_func, daemon=True)
        recv_thread.start()
        
        self.decode_thread = threading.Thread(target=self._decode_thread_func, daemon=True)
        self.decode_thread.start()
        
        process_thread = threading.Thread(target=self._process_thread_func, daemon=True)
        process_thread.start()
        
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_thread_func, daemon=True)
        self.heartbeat_thread.start()
        
        self.monitor_thread = threading.Thread(target=self._monitor_thread_func, daemon=True)
        self.monitor_thread.start()
        
        print_log(LogLevel.INFO, self.log_title, f"工作线程已启动")

    def _heartbeat_thread_func(self) -> None:
        """心跳线程"""
        print_log(LogLevel.INFO, self.log_title, f"心跳线程启动")
        
        while not self._stop_event.is_set() and self.is_connected:
            try:
                # 发送心跳包
                if self.socket:
                    heartbeat_packet = struct.pack('>II', PacketType.PACKET_HEARTBEAT, 0)
                    self.socket.sendall(heartbeat_packet)
                    if self.debug:
                        print_log(LogLevel.DEBUG, self.log_title, f"发送心跳包")
                
                # 等待下一次心跳
                for _ in range(int(HEARTBEAT_INTERVAL * 10)):
                    if self._stop_event.is_set():
                        break
                    time.sleep(0.5)
                    
            except Exception as e:
                if not self._stop_event.is_set():
                    print_log(LogLevel.WARN, self.log_title, f"心跳发送失败: {e}")
                break
        
        print_log(LogLevel.INFO, self.log_title, f"心跳线程结束")

    def _monitor_thread_func(self) -> None:
        """监控线程，检查超时"""
        print_log(LogLevel.INFO, self.log_title, f"监控线程启动")
        
        while not self._stop_event.is_set() and self.is_connected:
            try:
                # 检查心跳超时
                current_time = time.time()
                time_since_last_data = current_time - self.last_data_time
                
                if time_since_last_data > HEARTBEAT_TIMEOUT:
                    print_log(LogLevel.ERROR, self.log_title, f"心跳超时 ({time_since_last_data:.1f}秒)，断开连接")
                    self.disconnect()
                    break
                
                # 检查是否长时间没有收到帧
                time_since_last_frame = current_time - self.last_frame_time
                if self.debug and time_since_last_frame > 10.0 and self.frame_count > 0:
                    print_log(LogLevel.WARN, self.log_title, f"警告: {time_since_last_frame:.1f}秒无新帧")
                
                # 每1秒检查一次
                time.sleep(1)
                    
            except Exception as e:
                if not self._stop_event.is_set():
                    print_log(LogLevel.ERROR, self.log_title, f"监控线程异常: {e}")
        
        print_log(LogLevel.INFO, self.log_title, f"监控线程结束")

    def _receive_thread_func(self) -> None:
        """接收线程"""
        print_log(LogLevel.INFO, self.log_title, f"接收线程启动")
        
        self.recv_buffer = bytearray()
        self.last_data_time = time.time()
        
        try:
            while not self._stop_event.is_set() and self.socket and self.is_connected:
                try:
                    self.socket.settimeout(0.1)
                    data = self.socket.recv(1024 * 1024)
                    
                    if not data:
                        continue
                    
                    self.last_data_time = time.time()
                    self.total_bytes += len(data)
                    
                    # 添加到缓冲区
                    self.recv_buffer.extend(data)
                    
                    # 立即处理数据
                    self._process_received_data()
                    
                except socket.timeout:
                    continue
                except (ConnectionResetError, ConnectionAbortedError):
                    print_log(LogLevel.ERROR, self.log_title, f"连接被重置")
                    break
                except Exception as e:
                    if not self._stop_event.is_set():
                        print_log(LogLevel.ERROR, self.log_title, f"接收数据异常: {e}")
                    break
        finally:
            self.is_streaming = False
            print_log(LogLevel.INFO, self.log_title, f"接收线程结束")
    
    def _process_received_data(self) -> None:
        """处理接收到的数据"""
        processed_count = 0
        max_process_per_cycle = 100

        while len(self.recv_buffer) >= PACKET_HEADER_SIZE and processed_count < max_process_per_cycle:
            try:
                packet_type = struct.unpack('>I', self.recv_buffer[0:4])[0]
                data_len = struct.unpack('>I', self.recv_buffer[4:8])[0]

                valid_types = [PacketType.PACKET_HEARTBEAT, PacketType.PACKET_SPS, PacketType.PACKET_PPS,
                               PacketType.PACKET_KEYFRAME, PacketType.PACKET_FRAME, PacketType.PACKET_CONFIG,
                               PacketType.PACKET_VPS]
                if packet_type not in valid_types:
                    del self.recv_buffer[0:1]
                    self.bad_packet_bytes += 1
                    continue
                
                if self.bad_packet_bytes > 0:
                    print_log(LogLevel.WARN, self.log_title, f"错误: 无效包类型, 重新同步(丢弃 {self.bad_packet_bytes} 字节坏数据...)")
                    self.bad_packet_bytes = 0
                
                MAX_ALLOWED_SIZE = 10 * 1024 * 1024
                if data_len < 0 or data_len > MAX_ALLOWED_SIZE:
                    print_log(LogLevel.WARN, self.log_title, f"错误: 异常数据长度 {data_len}，包类型={packet_type}，尝试重新同步...")
                    sync_found = False
                    buf_len = len(self.recv_buffer)
                    for i in range(1, buf_len - 7):
                        potential_type = struct.unpack('>I', self.recv_buffer[i:i+4])[0]
                        potential_len = struct.unpack('>I', self.recv_buffer[i+4:i+8])[0]
                        if (potential_type in valid_types and 
                            0 <= potential_len <= MAX_ALLOWED_SIZE):
                            print_log(LogLevel.INFO, self.log_title, f"找到同步点，丢弃 {i} 字节坏数据...")
                            del self.recv_buffer[0:i]
                            sync_found = True
                            break
                    
                    if not sync_found:
                        print_log(LogLevel.WARN, self.log_title, f"未找到同步点，清空整个接收缓冲区！！！")
                        self.recv_buffer.clear()
                    continue

                if len(self.recv_buffer) >= PACKET_HEADER_SIZE + data_len:
                    packet_data = bytes(self.recv_buffer[PACKET_HEADER_SIZE:PACKET_HEADER_SIZE + data_len])
                    del self.recv_buffer[:PACKET_HEADER_SIZE + data_len]
                    
                    self._handle_packet(packet_type, data_len, packet_data)
                    processed_count += 1
                    self.packet_count += 1
                else:
                    break

            except struct.error as e:
                print_log(LogLevel.ERROR, self.log_title, f"解析包头结构失败: {e}，丢弃 1 字节，尝试重新同步")
                if len(self.recv_buffer) > 0:
                    del self.recv_buffer[0:1]
                    self.bad_packet_bytes += 1
                continue
            except Exception as e:
                print_log(LogLevel.ERROR, self.log_title, f"处理数据时发生未知异常: {e}，清空整个接收缓冲区！！！")
                self.recv_buffer.clear()
                break
    
    def _handle_packet(self, packet_type: int, data_len: int, packet_data: bytes) -> None:
        """处理数据包"""
        self.last_data_time = time.time()
        
        packet_type_names = {
            PacketType.PACKET_HEARTBEAT: "HEARTBEAT",
            PacketType.PACKET_SPS: "SPS",
            PacketType.PACKET_PPS: "PPS",
            PacketType.PACKET_KEYFRAME: "KEYFRAME", 
            PacketType.PACKET_FRAME: "FRAME",
            PacketType.PACKET_CONFIG: "CONFIG",
            PacketType.PACKET_VPS: "VPS"
        }
        
        type_name = packet_type_names.get(packet_type, f"UNKNOWN({packet_type})")
        if data_len == 0:
            if packet_type != PacketType.PACKET_HEARTBEAT:
                print_log(LogLevel.WARN, self.log_title, f"警告: 收到零长度的 {type_name} 包，可能为协议错误，直接忽略！")
            return
        
        if self.debug:
            need_print = True
        elif packet_type != PacketType.PACKET_HEARTBEAT and packet_type != PacketType.PACKET_FRAME:
            need_print = True
        else:
            need_print = False
        
        if need_print:
            print_log(LogLevel.DEBUG, self.log_title, f"收到包: {type_name}, 长度={data_len}字节")
        
        if packet_type == PacketType.PACKET_HEARTBEAT:
            self.last_heartbeat_time = time.time()
            return
        
        elif packet_type == PacketType.PACKET_CONFIG:
            config_msg = struct.unpack('>I I I I', packet_data[0:16])
            self.config.width = config_msg[0]
            self.config.height = config_msg[1]
            self.config.fps = config_msg[2]
            self.config.bitrate = config_msg[3]
            if self.decoder:
                self.decoder.update_resolution(config_msg[0], config_msg[1])
            print_log(LogLevel.INFO, self.log_title, f"收到配置消息: {config_msg[0]}x{config_msg[1]}@{config_msg[2]}fps bitrate:{config_msg[3]}")
            return
        
        elif packet_type == PacketType.PACKET_VPS:
            self.vps_data = packet_data
            self.vps_received = True
            print_log(LogLevel.DEBUG, self.log_title, f"收到VPS: {len(packet_data)}字节")
            if self.decoder:
                self.decoder.set_vps(packet_data)
            return
        
        elif packet_type == PacketType.PACKET_SPS:
            self.sps_data = packet_data
            self.sps_received = True
            print_log(LogLevel.DEBUG, self.log_title, f"收到SPS: {len(packet_data)}字节")
            if self.decoder:
                self.decoder.set_sps(packet_data)
            return
        
        elif packet_type == PacketType.PACKET_PPS:
            self.pps_data = packet_data
            self.pps_received = True
            print_log(LogLevel.DEBUG, self.log_title, f"收到PPS: {len(packet_data)}字节")
            if self.decoder:
                self.decoder.set_pps(packet_data)
            return
        
        elif packet_type == PacketType.PACKET_KEYFRAME:
            is_keyframe = True
            if self.frame_count == 0:
                print_log(LogLevel.INFO, self.log_title, f"收到第一个关键帧: {data_len}字节")
        
        elif packet_type == PacketType.PACKET_FRAME:
            is_keyframe = False
        
        else:
            print_log(LogLevel.WARN, self.log_title, f"警告！收到未知数据包类型: {packet_type}")
            return
        
        try:
            self.raw_frame_queue.put_nowait((packet_data, is_keyframe, data_len))
        except queue.Full:
            if is_keyframe:
                try:
                    while not self.raw_frame_queue.empty():
                        self.raw_frame_queue.get_nowait()
                    self.raw_frame_queue.put_nowait((packet_data, is_keyframe, data_len))
                except queue.Empty:
                    pass
    
    def _process_thread_func(self) -> None:
        """处理线程"""
        print_log(LogLevel.INFO, self.log_title, f"处理线程启动")
        
        while not self._stop_event.is_set() and self.is_connected:
            try:
                # 定期打印统计信息
                current_time = time.time()
                if current_time - self.last_fps_check >= 10.0:
                    self.last_fps_check = current_time
                    if self.decoder:
                        if self.last_print_frame_count != self.frame_count:
                            self.last_print_frame_count = self.frame_count
                            print_log(LogLevel.DEBUG, self.log_title, f"统计: 总帧数={self.frame_count}, "
                                f"解码成功={self.decoder.decode_success}, "
                                f"解码失败={self.decoder.decode_failure}, "
                                f"队列大小={self.frame_queue.qsize()}, ")
                        if self.debug:
                            print_log(LogLevel.DEBUG, self.log_title, f"VPS状态: {self.vps_received}, SPS状态: {self.sps_received}, PPS状态: {self.pps_received}")
                
                # 短暂休眠，避免占用过多CPU
                time.sleep(0.5)
                
            except Exception as e:
                if not self._stop_event.is_set():
                    print_log(LogLevel.ERROR, self.log_title, f"处理线程异常: {e}")
        
        print_log(LogLevel.INFO, self.log_title, f"处理线程结束")
    
    def _decode_thread_func(self) -> None:
        """解码线程 - 从raw_frame_queue取原始帧数据，解码后放入frame_queue"""
        print_log(LogLevel.INFO, self.log_title, f"解码线程启动")
        
        while not self._stop_event.is_set():
            try:
                raw_frame = self.raw_frame_queue.get(timeout=0.1)
                if raw_frame is None:
                    continue
                
                packet_data, is_keyframe, data_len = raw_frame
                
                if self.decoder and self.decoder.is_ready():
                    if self.decoder.waiting_for_keyframe and not is_keyframe:
                        continue
                    
                    rgb_array = self.decoder.decode_frame(packet_data, is_keyframe)
                    
                    if rgb_array is not None:
                        self.frame_count += 1
                        self.last_frame_time = time.time()
                        
                        if self.frame_count % 300 == 0:
                            queue_size = self.frame_queue.qsize()
                            print_log(LogLevel.INFO, self.log_title, f"解码进度: 第{self.frame_count}帧, 队列={queue_size}, "
                                f"成功={self.decoder.decode_success}, 失败={self.decoder.decode_failure}")
                        
                        try:
                            self.frame_queue.put_nowait(rgb_array)
                            
                            if self.on_frame_decoded:
                                try:
                                    self.on_frame_decoded(rgb_array)
                                except Exception:
                                    pass
                                    
                        except queue.Full:
                            try:
                                self.frame_queue.get_nowait()
                                self.frame_queue.put_nowait(rgb_array)
                            except queue.Empty:
                                pass
                    else:
                        self.decode_failure += 1
                        if is_keyframe:
                            print_log(LogLevel.ERROR, self.log_title, f"关键帧解码失败！(帧数据={data_len}字节)")
                            while not self.frame_queue.empty():
                                try:
                                    self.frame_queue.get_nowait()
                                except queue.Empty:
                                    break
                        elif self.decode_failure % 50 == 0:
                            print_log(LogLevel.WARN, self.log_title, f"P帧解码失败累计={self.decode_failure}")
                else:
                    if self.frame_count == 0:
                        print_log(LogLevel.WARN, self.log_title, f"解码器未就绪，跳过帧 (VPS:{self.vps_received}, SPS:{self.sps_received}, PPS:{self.pps_received}, codec_ctx:{self.decoder.codec_ctx is not None if self.decoder else False})")
                
            except queue.Empty:
                continue
            except Exception as e:
                if not self._stop_event.is_set():
                    print_log(LogLevel.ERROR, self.log_title, f"解码线程异常: {e}")
        
        print_log(LogLevel.INFO, self.log_title, f"解码线程结束")

    def get_current_frame(self, timeout: float = 0.001):
        """获取当前显示帧"""
        try:
            return self.frame_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def disconnect(self) -> None:
        """断开连接（仅清理自身资源：socket、解码器、队列、线程）"""
        self._stop_event.set()
        self.is_connected = False
        self.is_streaming = False
        
        self.frame_count: int = 0
        self.total_bytes: int = 0
        self.decode_failure: int = 0
        self.last_data_time: float = 0
        self.last_heartbeat_time: float = 0
        self.last_frame_time: float = 0
        self.last_print_frame_count: int = 0
        self.packet_count: int = 0
        self.bad_packet_bytes: int = 0
        
        def disconnect_async() -> None:
            print_log(LogLevel.INFO, self.log_title, f"断开连接...")
            
            self._stop_event.set()
            
            # 清理解码器
            if self.decoder:
                self.decoder.cleanup()
                self.decoder = None
            
            if self.socket:
                try:
                    self.socket.close()
                except OSError:
                    pass
                self.socket = None
            
            # 等待线程结束
            if self.heartbeat_thread and self.heartbeat_thread.is_alive():
                self.heartbeat_thread.join(timeout=1.0)
            
            if self.monitor_thread and self.monitor_thread.is_alive():
                self.monitor_thread.join(timeout=1.0)
            
            if self.decode_thread and self.decode_thread.is_alive():
                self.decode_thread.join(timeout=1.0)
            
            # 清空队列
            while not self.raw_frame_queue.empty():
                try:
                    self.raw_frame_queue.get_nowait()
                except queue.Empty:
                    break
            
            while not self.frame_queue.empty():
                try:
                    self.frame_queue.get_nowait()
                except queue.Empty:
                    break
            
            self.recv_buffer.clear()
            
            print_log(LogLevel.INFO, self.log_title, f"断开连接已完成")
        
        threading.Thread(target=disconnect_async, daemon=True).start()


__all__ = ["VideoStreamClient"]
