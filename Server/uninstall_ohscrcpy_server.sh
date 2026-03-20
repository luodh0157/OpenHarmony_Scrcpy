#!/bin/bash

clear
export LANG=en_US.UTF-8
last_exit_code=0

uninstall_scrcpy_server() {
    local device="$1"
    hdc -t "$device" target mount
    hdc -t "$device" shell pkill ohscrcpy_server
    hdc -t "$device" shell rm /system/bin/ohscrcpy_server
    hdc -t "$device" shell rm /system/etc/init/ohscrcpy_server.cfg
    return $?
}

while IFS= read -r line; do
    if echo "$line" | grep -q "Empty"; then
        continue
    else
        uninstall_scrcpy_server "$line"
        last_exit_code=$?
    fi
done < <(hdc list targets)

if [ "$last_exit_code" -eq 0 ]; then
    read -n 1 -s -r -p "Press any key to continue..."
    echo
fi

exit 0