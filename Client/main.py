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
OpenHarmony_Scrcpy 客户端入口
"""

import traceback
from typing import NoReturn

from core import VERSION, LogLevel, print_log, init_logger, get_log_file
from gui import MainWindow


def main() -> NoReturn:
    init_logger()
    
    print("="*84)
    print(" "*15, f"OpenHarmony_Scrcpy Client - {VERSION} (author: luodh0157)", " "*15)
    print("="*84)
    
    log_file = get_log_file()
    if log_file:
        print_log(LogLevel.INFO, "主函数", f"日志文件: {log_file}")
    
    try:
        app = MainWindow()
        app.run()
    except Exception as e:
        print_log(LogLevel.ERROR, "主函数", f"GUI启动失败: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()