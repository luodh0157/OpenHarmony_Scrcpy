# OHScrcpy_Server - OpenHarmony投屏工具服务端

   OHScrcpy是一款为OpenHarmony系统设计的投屏工具软件，功能类似Android平台的scrcpy投屏工具。它能够将OpenHarmony设备的屏幕实时镜像到计算机，并提供设备控制功能。

## 特性

- **实时屏幕镜像**：低延迟显示OpenHarmony设备屏幕
- **多设备管理**：支持同时连接多个设备并切换
- **自适应分辨率**：自动调整显示尺寸，保持原始比例

## 系统要求
- **系统版本**：OpenHarmony 5.0或更高版本（**root版本**）
- **权限**：需要USB调试权限

## 开发指南

### 目录结构
```
Server/
├── bin/                      # 预置二进制可执行文件目录
├── include/                  # 头文件目录
├── src/                      # 源文件目录
├── BUILD.gn                  # OpenHarmony编译配置脚本
├── build_ohscrcpy_server.sh  # 服务端编译脚本
├── install_ohscrcpy_server.bat # 服务端安装脚本（Windows）
├── install_ohscrcpy_server.sh  # 服务端安装脚本（Linux）
├── ohscrcpy_server.cfg       # 服务端运行权限配置
├── ohscrcpy_server.patch     # 服务端嵌入编译配置补丁
├── start_ohscrcpy_server.bat # 服务端启动脚本（Windows）
├── start_ohscrcpy_server.sh  # 服务端启动脚本（Linux）
├── uninstall_ohscrcpy_server.bat # 服务端卸载脚本（Windows）
├── uninstall_ohscrcpy_server.sh  # 服务端卸载脚本（Linux）
└── README.md                 # 本说明文档
```

### 核心模块
   1. **NetworkStreamer**：网络传输模块
   2. **VideoEncoder**：视频编码模块
   3. **ScreenCapturer**：屏幕捕获模块
   4. **OHScrcpyServer**：主服务模块

### 协议说明
   程序使用自定义TCP协议进行通信：
- 数据包格式：4字节包类型 + 4字节数据长度 + 数据内容
- 包类型：心跳、SPS、PPS、VPS、关键帧、普通帧、配置信息

### 编译步骤
   1. 下载OpenHarmony全量代码，下载命令如下：
   ```bash
   repo init -u git@gitcode.com:openharmony/manifest.git -b master --no-repo-verify
   repo sync -c --no-tags -j`nproc`
   ```
   2. 在`foundation/multimedia/player_framework/`目录下新建`OHScrcpy_Server`目录
   3. 将本项目`Server`目录中的`BUILD.gn`、`include/`、`src/`、`ohscrcpy_server.cfg`拷贝至上一步新建的`OHScrcpy_Server`目录下
   4. 将本项目`Server`目录中的`ohscrcpy_server.patch`拷贝至`foundation/multimedia/player_framework/`目录下
   5. 在`foundation/multimedia/player_framework/`目录下执行`git apply ohscrcpy_server.patch`，打上编译配置补丁
   6. 在OpenHarmony全仓代码的根目录下，执行如下编译命令：
   ```bash
   ./build.sh --product-name rk3568 --build-target ohscrcpy_server
   ./build.sh --product-name rk3568 --build-target ohscrcpy_server --fast-rebuild （`--fast-rebuild`是快速编译参数，没有修改BUILD.gn和bundle.json时可用）
   ```
   7. 编译产物位于`out/rk3568/multimedia/player_framework/`目录下的`ohscrcpy_server`

### 安装步骤
   1. 将编译产物`ohscrcpy_server`拷贝至本项目`Server/bin/`目录下对应的芯片平台子目录`rk3568`下
      （说明：本项目已自带rockchip rk3568芯片平台的编译产物，如果芯片平台和OpenHarmony系统版本一致，可跳过`编译步骤`和当前步骤）
   2. 执行`Server`目录下的`install_ohscrcpy_server`脚本即可完成安装，Windows平台使用`install_ohscrcpy_server.bat`，Linux平台使用`install_ohscrcpy_server.sh`
      （说明：非`rk3568`芯片平台，需要修改`install_ohscrcpy_server`脚本中的路径，当然也可以共用同一个路径）

### 启动方法
   执行`Server`目录下的`start_ohscrcpy_server`脚本即可启动，Windows平台使用`start_ohscrcpy_server.bat`，Linux平台使用`start_ohscrcpy_server.sh`

## 日志系统

### 服务端日志功能

服务端支持日志记录功能，便于问题排查和调试。

#### 启用日志
- **自动启用**：客户端启动服务端时自动添加`--log`参数
- **手动启用**：
  ```bash
  hdc shell /system/bin/ohscrcpy_server -p 27183 --log
  ```

#### 日志配置
- **日志位置**：`/data/local/tmp/server_PID_YYYYMMDD_HHMMSS.log`
- **命名规则**：包含进程PID，支持多客户端并发场景精确识别
- **日志内容**：编码器状态、网络传输、错误信息等关键信息

#### 拉取日志到本地
使用客户端提供的日志管理脚本拉取服务端日志：

**Linux/Mac**：
```bash
./fetch_server_logs.sh 12345  # 精确拉取（指定PID）
./fetch_server_logs.sh        # 批量拉取（所有日志）
```

**Windows**：
```cmd
fetch_server_logs.bat 12345   # 精确拉取（指定PID）
fetch_server_logs.bat         # 批量拉取（所有日志）
```

**说明**：
- 日志拉取到本地`logs/`目录
- 不删除设备上的原始日志文件
- 脚本优先使用内置hdc工具

#### 清理日志

**Linux/Mac**：
```bash
./delete_server_logs.sh 12345  # 精确删除（无需确认）
./delete_server_logs.sh        # 批量删除（需确认）
```

**Windows**：
```cmd
delete_server_logs.bat 12345   # 精确删除（无需确认）
delete_server_logs.bat         # 批量删除（需确认）
```

**注意**：删除前请确保服务端进程已停止。

## 免责声明
本工具仅供学习和研究使用，请勿用于非法用途。使用本工具造成的任何后果，开发者概不负责。

---

**注意**：本软件需要与OpenHarmony设备端的对应服务端程序配合使用。请确保设备端已正确安装并运行服务端程序。