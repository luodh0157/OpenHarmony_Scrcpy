# OHScrcpy_Server - OpenHarmony投屏工具服务端

   OHScrcpy是一款为OpenHarmony系统设计的投屏工具软件，功能类似Android平台的scrcpy投屏工具。它能够将OpenHarmony设备的屏幕实时镜像到计算机，并提供设备控制功能。

## 特性

- 🖥️ **实时屏幕镜像**：低延迟显示OpenHarmony设备屏幕
- 📱 **多设备管理**：支持同时连接多个设备并切换
- 🎨 **自适应分辨率**：自动调整显示尺寸，保持原始比例

## 系统要求
- **系统版本**：OpenHarmony 5.0或更高版本
- **权限**：需要USB调试权限

## 开发指南

### 核心模块
   1. **NetworkStreamer**：网络传输模块
   2. **VideoEncoder**：视频编码模块
   3. **ScreenCapturer**：屏幕捕获模块
   4. **OHScrcpyServer**：主服务模块

### 协议说明
   程序使用自定义TCP协议进行通信：
- 数据包格式：4字节包类型 + 4字节数据长度 + 数据内容
- 包类型：心跳、SPS、PPS、关键帧、普通帧、配置信息

### 编译步骤
   1. 下载OpenHarmony全量代码，下载命令如下：
   ```bash
   repo init -u git@gitcode.com:openharmony/manifest.git -b master --no-repo-verify
   repo sync -c --no-tags -j`nproc`
   ```
   2. 在**foundation/multimedia/player_framework/**目录下新建**OHScrcpy_Server**目录
   3. 将本项目**Server**目录中的**BUILD.gn ohscrcpy_server.cpp ohscrcpy_server.cfg**拷贝至上一步新建的**OHScrcpy_Server**目录下
   4. 将本项目**Server**目录中的**ohscrcpy_server.patch** 拷贝至 **foundation/multimedia/player_framework/**目录下
   5. 在**foundation/multimedia/player_framework/**目录下执行**git apply ohscrcpy_server.patch**，打上编译配置补丁
   6. 在OpenHarmony全仓代码的根目录下，执行如下编译命令：
   ```bash
   ./build.sh --product-name rk3568 --build-target ohscrcpy_server
   ```
   7. 编译产物位于**out/rk3568/multimedia/player_framework/**目录下的**ohscrcpy_server**

### 安装步骤
   1. 将编译产物**ohscrcpy_server**拷贝至本项目**Server/bin/**目录下对应的芯片平台子目录**rk3568**下
      （说明：本项目已自带rockchip rk3568芯片平台的编译产物，如果芯片平台和OpenHarmony系统版本一致，可跳过**编译步骤**和当前步骤）
   2. 执行**Server**目录下的**install_ohscrcpy_server**脚本即可完成安装，Windows平台使用**install_ohscrcpy_server.bat**，Linux平台使用**install_ohscrcpy_server.sh**
      （说明：非**rk3568**芯片平台，需要修改**install_ohscrcpy_server**脚本中的路径，当然也可以共用同一个路径）

### 启动方法
   执行**Server**目录下的**start_ohscrcpy_server**脚本即可完成安装，Windows平台使用**start_ohscrcpy_server.bat**，Linux平台使用**start_ohscrcpy_server.sh**

## 免责声明
本工具仅供学习和研究使用，请勿用于非法用途。使用本工具造成的任何后果，开发者概不负责。

---

**注意**：本软件需要与OpenHarmony设备端的对应服务端程序配合使用。请确保设备端已正确安装并运行服务端程序。