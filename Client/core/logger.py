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
OpenHarmony_Scrcpy 日志模块 - 支持配置文件和双输出
"""

import os
import sys
import json
from datetime import datetime
from typing import Optional, Dict, Any

from .constants import LogLevel


class Logger:
    """日志管理器 - 支持配置文件和双输出（控制台+文件）"""
    
    _instance: Optional['Logger'] = None
    _log_file: Optional[str] = None
    _log_dir: Optional[str] = None
    _config: Dict[str, Any] = {}
    _initialized: bool = False
    
    def __new__(cls) -> 'Logger':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def get_instance(cls) -> 'Logger':
        return cls() if cls._instance is None else cls._instance
    
    @classmethod
    def init_from_config(cls, config_path: Optional[str] = None) -> None:
        """从配置文件初始化日志"""
        instance = cls.get_instance()
        
        if config_path is None:
            # 默认配置文件路径
            if hasattr(sys, '_MEIPASS'):
                config_path = os.path.join(sys._MEIPASS, 'config', 'log_config.json')
            else:
                config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                          'config', 'log_config.json')
        
        # 加载配置
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    instance._config = json.load(f)
        except Exception:
            instance._config = {}
        
        # 设置默认值
        log_level_str = instance._config.get('log_level', 'INFO')
        log_dir = instance._config.get('log_dir', 'logs')
        log_to_file = instance._config.get('log_to_file', True)
        
        # 设置日志级别
        from .constants import ENABLE_LOG_LEVEL
        level_map = {
            'DEBUG': LogLevel.DEBUG,
            'INFO': LogLevel.INFO,
            'WARN': LogLevel.WARN,
            'ERROR': LogLevel.ERROR,
            'FATAL': LogLevel.FATAL,
        }
        import core.constants as constants
        constants.ENABLE_LOG_LEVEL = level_map.get(log_level_str, LogLevel.INFO)
        
        # 设置日志文件
        if log_to_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = f"client_{timestamp}.log"
            cls.set_log_file(log_file, log_dir)
        
        instance._initialized = True
    
    @classmethod
    def set_log_file(cls, log_file: Optional[str] = None, log_dir: Optional[str] = None) -> None:
        """设置日志文件"""
        instance = cls.get_instance()
        instance._log_dir = log_dir
        instance._log_file = log_file
        
        if log_dir and not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir)
            except Exception:
                pass
    
    @classmethod
    def get_log_file(cls) -> Optional[str]:
        instance = cls.get_instance()
        if instance._log_file and instance._log_dir:
            return os.path.join(instance._log_dir, instance._log_file)
        return None
    
    def _format_level(self, level: LogLevel) -> str:
        """格式化日志级别"""
        level_names = {
            LogLevel.DEBUG: "DEBUG",
            LogLevel.INFO: "INFO",
            LogLevel.WARN: "WARN",
            LogLevel.ERROR: "ERROR",
            LogLevel.FATAL: "FATAL",
        }
        return level_names.get(level, "UNKNOWN")
    
    def _write_log(self, level: LogLevel, title: str, content: str) -> None:
        """写入日志 - 同时输出到控制台和文件"""
        from .constants import ENABLE_LOG_LEVEL
        if level < ENABLE_LOG_LEVEL:
            return
        
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        level_name = self._format_level(level)
        log_line = f"[{timestamp}][{level_name}][{title}] {content}"
        
        # 控制台输出（简化格式）
        print(log_line)
        
        # 文件输出（完整格式带日期）
        log_file = self.get_log_file()
        if log_file:
            try:
                full_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                full_log_line = f"[{full_timestamp}][{level_name}][{title}] {content}"
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write(full_log_line + '\n')
            except Exception:
                pass


def init_logger(config_path: Optional[str] = None) -> None:
    """初始化日志系统"""
    Logger.init_from_config(config_path)


def print_log(level: LogLevel, title: str, content: str) -> None:
    """打印日志（兼容接口）"""
    Logger.get_instance()._write_log(level, title, content)


def set_log_file(log_file: Optional[str] = None, log_dir: Optional[str] = None) -> None:
    """设置日志文件"""
    Logger.set_log_file(log_file, log_dir)


def get_log_file() -> Optional[str]:
    """获取当前日志文件路径"""
    return Logger.get_log_file()


__all__ = ["Logger", "init_logger", "print_log", "set_log_file", "get_log_file"]