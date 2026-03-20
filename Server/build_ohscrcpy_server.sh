# 编译服务端（在OpenHarmony源码根目录下执行）

# 首次编译（或者涉及BUILD.gn修改）
./build.sh --product-name rk3568 --build-target ohscrcpy_server

# 快速编译（不涉及BUILD.gn修改）
./build.sh --product-name rk3568 --build-target ohscrcpy_server --fast-rebuild
