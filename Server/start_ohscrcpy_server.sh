#!/bin/bash

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

clear
export LANG=en_US.UTF-8
last_exit_code=0

start_scrcpy_server() {
    local device="$1"
    hdc -t "$device" power-shell wakeup
    hdc -t "$device" power-shell timeout -o 86400000
    hdc -t "$device" power-shell setmode 602
    hdc -t "$device" uinput -T -m 350 1100 350 500 200
    hdc -t "$device" hidumper -s 3301 -a -t
    hdc -t "$device" /system/bin/ohscrcpy_server
    return $?
}

while IFS= read -r line; do
    if echo "$line" | grep -q "Empty"; then
        continue
    else
        start_scrcpy_server "$line"
        last_exit_code=$?
    fi
done < <(hdc list targets)

if [ "$last_exit_code" -eq 0 ]; then
    read -n 1 -s -r -p "Press any key to continue..."
    echo
fi

exit 0