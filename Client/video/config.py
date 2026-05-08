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
OpenHarmony_Scrcpy 视频流配置
"""

from dataclasses import dataclass


@dataclass  
class VideoStreamConfig:
    """视频流配置"""
    width: int = 720
    height: int = 1280
    fps: int = 30
    bitrate: int = 1500000
    codec: str = "h264"


__all__ = ["VideoStreamConfig"]