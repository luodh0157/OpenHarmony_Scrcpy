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
OpenHarmony_Scrcpy 核心模块
"""

from .constants import (
    AUTHOR,
    PROJECT_URL,
    VERSION,
    DEFAULT_PORT,
    HOST,
    HEARTBEAT_TIMEOUT,
    HEARTBEAT_INTERVAL,
    PACKET_HEADER_SIZE,
    PacketType,
    LogLevel,
    ServerDeployState,
    ENABLE_LOG_LEVEL,
)

from .logger import print_log, set_log_file, get_log_file, init_logger, Logger
from .hdc_executor import HDCCommandExecutor
from .server_manager import ServerManager
from .device_manager import DeviceInfo, DeviceManager
from .exceptions import (
    OHScrcpyError,
    DeviceNotFoundError,
    StreamConnectError,
    ServerDeployError,
    VideoDecodeError,
    ProtocolError,
    ConfigError,
)

__all__ = [
    "AUTHOR",
    "PROJECT_URL",
    "VERSION",
    "DEFAULT_PORT",
    "HOST",
    "HEARTBEAT_TIMEOUT",
    "HEARTBEAT_INTERVAL",
    "PACKET_HEADER_SIZE",
    "PacketType",
    "LogLevel",
    "ServerDeployState",
    "ENABLE_LOG_LEVEL",
    "print_log",
    "set_log_file",
    "get_log_file",
    "init_logger",
    "Logger",
    "HDCCommandExecutor",
    "ServerManager",
    "DeviceInfo",
    "DeviceManager",
    "OHScrcpyError",
    "DeviceNotFoundError",
    "StreamConnectError",
    "ServerDeployError",
    "VideoDecodeError",
    "ProtocolError",
    "ConfigError",
]