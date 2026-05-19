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
OpenHarmony_Scrcpy 异常类定义
"""

from typing import Optional


class OHScrcpyError(Exception):
    """基础异常类"""
    
    def __init__(self, message: str, error_code: Optional[int] = None):
        self.error_code = error_code
        self.message = message
        super().__init__(message)


class DeviceNotFoundError(OHScrcpyError):
    """设备未找到"""
    
    def __init__(self, message: str = "Device not found"):
        super().__init__(message, error_code=1001)


class StreamConnectError(OHScrcpyError):
    """连接错误"""
    
    def __init__(self, message: str = "Connection failed"):
        super().__init__(message, error_code=1002)


class ServerDeployError(OHScrcpyError):
    """服务部署错误"""
    
    def __init__(self, message: str = "Server deployment failed"):
        super().__init__(message, error_code=1003)


class VideoDecodeError(OHScrcpyError):
    """视频解码错误"""
    
    def __init__(self, message: str = "Video decode failed"):
        super().__init__(message, error_code=2001)


class ProtocolError(OHScrcpyError):
    """协议解析错误"""
    
    def __init__(self, message: str = "Protocol parse error"):
        super().__init__(message, error_code=2002)


class ConfigError(OHScrcpyError):
    """配置错误"""
    
    def __init__(self, message: str = "Configuration error"):
        super().__init__(message, error_code=3001)


__all__ = [
    "OHScrcpyError",
    "DeviceNotFoundError",
    "StreamConnectError",
    "ServerDeployError",
    "VideoDecodeError",
    "ProtocolError",
    "ConfigError",
]