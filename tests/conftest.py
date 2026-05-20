#!/usr/bin/env python

"""
测试配置 - 将Client目录添加到Python路径
"""

import sys
from unittest.mock import MagicMock

# 将 tkinter 和 ttk 整个模块替换为 MagicMock
sys.modules['_tkinter'] = MagicMock()
sys.modules['tkinter'] = MagicMock()
sys.modules['tkinter.ttk'] = MagicMock()

import os
import pytest

# 获取项目根目录
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
client_dir = os.path.join(root_dir, 'Client')

# 添加Client目录到Python路径
if client_dir not in sys.path:
    sys.path.insert(0, client_dir)