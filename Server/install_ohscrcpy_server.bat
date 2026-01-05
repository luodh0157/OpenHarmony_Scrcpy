set cur_path=%~dp0
hdc shell mount -o rw,remount /
hdc file send %cur_path%/bin/rk3568/ohscrcpy_server /system/bin/
hdc shell chmod +x /system/bin/ohscrcpy_server
hdc file send %cur_path%/ohscrcpy_server.cfg /system/etc/init/

::hdc shell reboot