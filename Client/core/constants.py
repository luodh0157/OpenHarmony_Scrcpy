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
OpenHarmony_Scrcpy 常量与枚举定义
"""

from enum import IntEnum, auto

# ==================== 项目信息 ====================
AUTHOR = "luodh0157"
PROJECT_URL = "https://gitcode.com/luodh0157/OpenHarmony_Scrcpy"
VERSION = "v2.1.0"

# ==================== 网络配置 ====================
DEFAULT_PORT = 27183
HOST = "127.0.0.1"

# ==================== 心跳配置 ====================
HEARTBEAT_TIMEOUT = 5.0  # 心跳超时时间（秒）
HEARTBEAT_INTERVAL = 1.0  # 心跳发送间隔（秒）

# ==================== 数据包配置 ====================
PACKET_HEADER_SIZE = 8

# ==================== 数据包类型定义 ====================
class PacketType(IntEnum):
    PACKET_HEARTBEAT = 0
    PACKET_SPS = 1
    PACKET_PPS = 2
    PACKET_KEYFRAME = 3
    PACKET_FRAME = 4
    PACKET_CONFIG = 5
    PACKET_VPS = 6
    PACKET_LOG = 7

# ==================== 日志级别定义 ====================
class LogLevel(IntEnum):
    DEBUG = auto()
    INFO = auto()
    WARN = auto()
    ERROR = auto()
    FATAL = auto()

# ==================== 服务部署状态定义 ====================
class ServerDeployState(IntEnum):
    IDLE = auto()
    INSTALLING = auto()
    STARTING = auto()
    FINISHED = auto()

# ==================== 默认日志级别 ====================
ENABLE_LOG_LEVEL = LogLevel.INFO