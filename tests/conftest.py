#!/usr/bin/env python

"""
测试配置 - 将Client目录添加到Python路径
"""

import sys
import os
import pytest

@pytest.fixture(autouse=True)
def mock_tkinter(monkeypatch):
    # 如果 _tkinter 不存在，就模拟一个假的模块
    if '_tkinter' not in sys.modules:
        monkeypatch.setitem(sys.modules, '_tkinter', type(sys)('_tkinter'))
        monkeypatch.setitem(sys.modules, 'tkinter', type(sys)('tkinter'))

# 获取项目根目录
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
client_dir = os.path.join(root_dir, 'Client')

# 添加Client目录到Python路径
if client_dir not in sys.path:
    sys.path.insert(0, client_dir)