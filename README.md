# OHScrcpy - OpenHarmony投屏工具

   OHScrcpy是一款为OpenHarmony系统设计的投屏工具软件，功能类似Android平台的scrcpy投屏工具。它能够将OpenHarmony设备的屏幕实时镜像到计算机，并提供设备控制功能。

## 实现原理框图
- **计算机侧（客户端）**：基于Python跨平台实现
- **OpenHarmony设备侧（服务端）**：基于OpenHarmony系统C-API实现

![系统架构图.png](https://raw.gitcode.com/user-images/assets/8887101/1dc7141a-783b-47af-aef9-8d46674e45f5/系统架构图.png '系统架构图.png')

## 特性

- **实时屏幕镜像**：低延迟显示OpenHarmony设备屏幕
- **设备控制**：支持点击、滑动、按键等操作
- **多种连接方式**：支持USB连接和网络连接
- **多设备管理**：支持同时连接多个设备并切换
- **自适应分辨率**：自动调整显示尺寸，保持原始比例
- **性能监控**：实时显示FPS、网络状态等统计信息
- **调试功能**：内置调试工具，便于问题排查
- **服务自动安装和启动**：服务端自动安装和启动

## 系统要求

### 计算机侧
- **操作系统**：Windows/Linux/macOS
- **Python版本**：Python 3.7或更高版本
- **依赖库**：
   - `numpy`
   - `pillow`
   - `av` (PyAV)
   - `tkinter` (通常Python自带)
- **网络**：支持TCP/IP连接

### OpenHarmony设备侧
- **系统版本**：OpenHarmony 5.0或更高版本
- **权限**：需要USB调试权限
- **服务端**：需要运行对应的投屏服务端程序

## 开发指南

### 项目结构
```
OpenHarmony_Scrcpy/
├── Client/              # 客户端目录
├──── ohscrcpy_client.py # 客户端程序入口
├──── README.md  # 客户端说明文档
├── Server/                       # 服务端目录
├──── bin/                        # 预置二进制可执行文件目录
├──── BUILD.gn                    # 服务端在OpenHarmony系统下的编译配置脚本
├──── build_ohscrcpy_server.sh    # 服务端编译脚本
├──── install_ohscrcpy_server.bat # 服务端安装脚本（Windows）
├──── install_ohscrcpy_server.sh  # 服务端安装脚本（Linux）
├──── ohscrcpy_server.cfg         # 服务端在OpenHarmony系统下的运行权限配置
├──── ohscrcpy_server.cpp         # 服务端实现源码
├──── ohscrcpy_server.patch       # 服务端嵌入编译配置补丁
├──── README.md                   # 服务端说明文档
├──── start_ohscrcpy_server.bat   # 服务端启动脚本（Windows）
├──── start_ohscrcpy_server.sh    # 服务端启动脚本（Linux）
├── LICENSE    # LICENSE说明
└── README.md  # 说明文档
```

### 核心模块

#### 服务端
   1. **NetworkStreamer**：网络传输模块
   2. **VideoEncoder**：视频编码模块
   3. **ScreenCapturer**：屏幕捕获模块
   4. **OHScrcpyServer**：主服务模块

#### 客户端
   1. **HDCCommandExecutor**：HDC命令执行器
   2. **DeviceManager**：设备管理器
   3. **H264Decoder**：H.264视频解码器
   4. **VideoStreamClient**：视频流客户端
   5. **DeviceController**：设备控制器
   6. **OHScrcpyGUI**：图形用户界面

### 协议说明
   程序使用自定义TCP协议进行通信：
- 数据包格式：4字节包类型 + 4字节数据长度 + 数据内容
- 包类型：心跳、SPS、PPS、关键帧、普通帧、配置信息

### 编译步骤
   客户端是python实现，不涉及编译，只有服务端涉及编译。服务端编译方法如下：
   1. 下载OpenHarmony全量代码，下载命令如下：
   ```bash
   repo init -u git@gitcode.com:openharmony/manifest.git -b master --no-repo-verify
   repo sync -c --no-tags -j`nproc`
   ```
   2. 在`foundation/multimedia/player_framework/`目录下新建`OHScrcpy_Server`目录
   3. 将本项目`Server`目录中的`BUILD.gn ohscrcpy_server.cpp ohscrcpy_server.cfg`拷贝至上一步新建的`OHScrcpy_Server`目录下
   4. 将本项目`Server`目录中的`ohscrcpy_server.patch`拷贝至`foundation/multimedia/player_framework/`目录下
   5. 在`foundation/multimedia/player_framework/`目录下执行`git apply ohscrcpy_server.patch`，打上编译配置补丁
   6. 在OpenHarmony全仓代码的根目录下，执行如下编译命令：
   ```bash
   ./build.sh --product-name rk3568 --build-target ohscrcpy_server
   ```
   7. 编译产物位于`out/rk3568/multimedia/player_framework/`目录下的`ohscrcpy_server`

## 安装步骤

### OpenHarmony设备侧安装
   无需手动安装，客户端（计算机侧）发起投屏时会自动安装服务端（OpenHarmony设备侧）

### 计算机侧安装

#### 1. 安装Python依赖
```bash
pip install numpy pillow av
```

#### 2. 安装HDC工具
   确保HDC（HarmonyOS Device Connector）工具已安装并添加到系统PATH

##### Windows
   1. 从OpenHarmony官网下载HDC工具
   2. 将hdc.exe所在目录添加到系统PATH

##### Linux/macOS
   通常已包含在OpenHarmony SDK中，或着从官网下载并安装

## 使用方法

### 1. 连接设备
   1. **USB连接**：
      - 使用USB数据线连接OpenHarmony设备到计算机
      - 在设备上启用USB调试模式
      - 首次连接时，需要在设备上授权调试权限
   2. **Wi-Fi连接**：
      - 确保设备和计算机在同一局域网或者用网线将设备和计算机直连

### 2. 启动OpenHarmony设备侧服务
   无需手动启动，客户端（计算机侧）发起投屏时会自动拉起服务端（OpenHarmony设备侧）

### 3. 启动计算机端GUI程序
```bash
python ohscrcpy_client.py
```
   1. 运行程序后，主界面将显示
   2. 点击`刷新`按钮扫描可用设备
   3. 从`设备列表`中选择要连接的设备
   4. 点击`连接`按钮开始投屏

![alt text](./Client/客户端启动GUI.png)
![alt text](./Client/客户端投屏GUI.png)

### 4. 基本操作

#### 屏幕控制
- **点击**：在视频区域`单击鼠标左键`
- **滑动**：在视频区域`按住鼠标左键并拖动`
- **缩放**：程序自动适应窗口大小，保持原始比例

#### 按键控制
- **电源键**：点击**电源**按钮，唤醒/关闭屏幕显示
- **主页键**：点击**主页**按钮，从前台应用返回桌面
- **返回键**：点击**返回**按钮，返回上一UI页面
- **解锁键**：点击**解锁**按钮，解锁屏幕
- **音量+**：点击<strong>音量+</strong>按钮，增大音量
- **音量-**：点击<strong>音量-</strong>按钮，减小音量

### 5. 快捷键

| 快捷键 | 功能 |
|--------|------|
| F5 | 刷新设备列表 |
| F6 | 保存当前帧为调试图像 |
| F8 | 显示调试信息窗口 |
| F9 | 强制垃圾回收 |

## 配置说明

### 视频流配置
   程序默认使用以下配置：
- **分辨率**：设备原始分辨率
- **帧率**：30 fps
- **码率**：1.5 Mbps
- **编码格式**：H.264

### 网络配置
- **默认端口**：27183
- **心跳间隔**：1秒
- **心跳超时**：5秒

## 故障排除

### 常见问题

#### 1. 无法发现设备
- 检查USB连接是否正常
- 确保设备已启用USB调试模式
- 尝试重新插拔USB线缆
- 运行 `hdc list targets` 检查设备识别情况

#### 2. 连接失败
- 检查默认端口`27183`是否被占用
- 确保设备端服务端程序已运行
- 检查防火墙设置

#### 3. 视频卡顿
- 降低视频分辨率设置
- 检查网络连接质量
- 关闭不必要的后台程序

#### 4. 解码错误
- 确保已安装所有Python依赖
- 检查`PyAV`库是否正确安装
- 尝试重启程序

### 调试模式
   启用客户端调试模式获取详细信息：
```python
self.video_client = VideoStreamClient(on_frame_decoded=self._on_frame_decoded, debug=True)
```

## 安全注意事项

1. **权限管理**：仅在授权的情况下访问设备
2. **数据安全**：视频流仅在本地网络传输
3. **隐私保护**：不记录或传输敏感信息

## 贡献指南

欢迎提交Issue和Pull Request来改进本项目：

1. Fork本仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

## 许可证

本项目采用Apache 2.0许可证，详见LICENSE文件。

## 支持与反馈

- 问题反馈：[OpenHarmony_Scrcpy Issues](https://gitcode.com/luodh0157/OpenHarmony_Scrcpy/issues)
- 功能建议：通过Issue提交
- 技术支持：查看Wiki文档或联系开发者

## 免责声明

本工具仅供学习和研究使用，请勿用于非法用途。使用本工具造成的任何后果，开发者概不负责。

---

**注意**：本软件需要与OpenHarmony设备端的对应服务端程序配合使用。请确保设备端已正确安装并运行服务端程序。