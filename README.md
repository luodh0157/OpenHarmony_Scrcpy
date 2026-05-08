# OHScrcpy - OpenHarmony投屏工具

   OHScrcpy是一款为OpenHarmony系统设计的投屏工具软件，功能类似Android平台的scrcpy投屏工具。它能够将OpenHarmony设备的屏幕实时镜像到计算机，并提供设备控制功能。

## 实现原理框图
- **计算机侧（客户端）**：基于Python跨平台实现
- **OpenHarmony设备侧（服务端）**：基于OpenHarmony系统C-API实现

![系统架构图.png](./系统架构图.png '系统架构图.png')

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
- **网络**：支持USB hdc连接

### OpenHarmony设备侧
- **系统版本**：OpenHarmony 5.0或更高版本（**root版本**）
- **权限**：需要USB调试权限

## 开发指南

### 项目结构
```
OpenHarmony_Scrcpy/
├── Client/                       # 客户端目录
│   ├── core/                     # 核心模块
│   ├── video/                    # 视频模块
│   ├── gui/                      # GUI模块
│   ├── utils/                    # 工具模块
│   ├── config/                   # 配置目录
│   ├── hdc/                      # 各平台HDC工具
│   ├── main.py                   # 程序入口
│   └── README.md                 # 客户端说明文档
├── Server/                       # 服务端目录
│   ├── include/                  # 头文件目录
│   ├── src/                      # 源文件目录
│   ├── bin/                      # 预置二进制可执行文件目录
│   ├── BUILD.gn                  # OpenHarmony编译配置脚本
│   ├── build_ohscrcpy_server.sh  # 服务端编译脚本
│   ├── install_ohscrcpy_server.bat # 服务端安装脚本（Windows）
│   ├── install_ohscrcpy_server.sh  # 服务端安装脚本（Linux）
│   ├── ohscrcpy_server.cfg       # 运行权限配置
│   ├── ohscrcpy_server.patch     # 嵌入编译配置补丁
│   ├── README.md                 # 服务端说明文档
│   ├── start_ohscrcpy_server.bat # 服务端启动脚本（Windows）
│   └── start_ohscrcpy_server.sh  # 服务端启动脚本（Linux）
├── Package/                      # 打包工具
│   ├── Executer/                 # 自解压打包工具
│   ├── Installer/                # 安装包打包工具
│   └── 打包工具使用说明.md        # 打包使用说明
├── tests/                        # 测试目录
│   ├── conftest.py               # pytest配置
│   ├── fixtures/                 # 测试数据目录
│   ├── requirements-test.txt     # 测试依赖
│   ├── run_tests.sh              # Linux/Mac测试脚本
│   ├── run_tests.bat             # Windows测试脚本
│   ├── test_hdc_executor.py      # HDC执行器测试
│   ├── test_device_manager.py    # 设备管理器测试
│   ├── test_decoder.py           # H264/H265解码器测试
│   ├── test_fixtures.py          # fixtures验证测试
│   ├── test_protocol.py          # 协议解析测试
│   ├── test_server_manager.py    # 服务端管理器测试
│   └── test_stream_client.py     # 视频流客户端测试
├── CHANGELOG.txt                 # 版本修改记录
├── LICENSE                       # LICENSE说明
└── README.md                     # 说明文档
```

### 核心模块

#### 服务端
   1. **NetworkStreamer**：网络传输模块
   2. **VideoEncoder**：视频编码模块
   3. **ScreenCapturer**：屏幕捕获模块
   4. **OHScrcpyServer**：主服务模块

#### 客户端
   1. **HDCCommandExecutor**：HDC命令执行器
   2. **ServerManager**：服务端管理器
   3. **DeviceManager**：设备管理器
   4. **VideoDecoder**：H.265/H.264视频解码器
   5. **VideoStreamClient**：视频流客户端
   6. **DeviceController**：设备控制器
   7. **OHScrcpyGUI**：图形用户界面

### 协议说明
   程序使用自定义TCP协议进行通信：
- **数据包格式**：4字节包类型 + 4字节数据长度 + 数据内容
- **包类型**：心跳、SPS、PPS、VPS、关键帧、普通帧、配置信息

### 编译步骤
   客户端是python实现，不涉及编译，只有服务端涉及编译。服务端编译方法如下：
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

### 测试

#### 生成测试数据
测试fixtures数据已自动生成，位于`tests/fixtures/`目录：
- **H264测试数据**：`sample_sps_h264.bin`、`sample_pps_h264.bin`、`sample_frame_h264.bin`
- **H265测试数据**：`sample_vps_h265.bin`、`sample_sps_h265.bin`、`sample_pps_h265.bin`、`sample_frame_h265.bin`
- **其他数据**：`sample_config_packet.bin`、`sample_device_list.txt`

如需重新生成测试数据：
```bash
cd tests/fixtures
python generate_fixtures.py
```

#### 安装测试依赖
```bash
pip install -r tests/requirements-test.txt
```

#### 执行测试
- **Linux/Mac**：
  ```bash
  cd tests
  ./run_tests.sh
  ```
- **Windows**：
  ```cmd
  cd tests
  run_tests.bat
  ```
#### 手动执行
  ```bash
  pytest tests/ -v
  ```

#### 测试说明
- **test_fixtures.py**：验证测试数据文件正确性（9个测试）
- **test_decoder.py**：使用fixtures数据测试H264/H265解码器
- **test_protocol.py**：使用fixtures数据测试协议解析
- **其他测试**：Mock测试设备管理、服务管理等功能

## 安装步骤

### OpenHarmony设备侧安装
   无需手动安装，客户端（计算机侧）发起投屏时会自动安装服务端（OpenHarmony设备侧）

### 计算机侧安装
   运行安装包，根据提示安装即可完成安装。
- **特别说明**：请勿将工具安装在中文路径下（hdc工具不支持中文路径）


## 使用方法

### 1. 连接设备
   1. **USB连接**：
      - 使用USB数据线连接OpenHarmony设备到计算机
      - 在设备上启用USB调试模式
      - 首次连接时，需要在设备上授权调试权限
   2. **网线/Wi-Fi连接**：
      - 确保设备和计算机在同一局域网（有线/无线）或者用网线将设备和计算机直连

### 2. 启动OpenHarmony设备侧服务
   无需手动启动，客户端（计算机侧）发起投屏时会自动拉起服务端（OpenHarmony设备侧）

### 3. 启动计算机端GUI程序
   Windows系统双击`OHScrcpy.exe`，Linux/macOS系统命令行执行`OHScrcpy`，即可运行程序
   
   **说明**：OpenHarmony设备侧服务端会自动安装+启动，无需用户手动启动。
   1. 运行程序后，主界面将显示
   2. 点击`刷新`按钮扫描可用设备
   3. 从`设备列表`中选择要连接的设备
   4. 点击`连接`按钮开始投屏

![客户端启动GUI.png](./Client/客户端启动GUI.png '客户端启动GUI.png')
![客户端投屏GUI.png](./Client/客户端投屏GUI.png '客户端投屏GUI.png')

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
- **分辨率**：设备默认分辨率
- **帧率**：30 fps
- **码率**：1.5 Mbps
- **编码格式**：H.265/H.264

### 网络配置
- **默认端口**：27183
- **心跳间隔**：1秒
- **心跳超时**：5秒

## 日志系统

### 日志配置
本项目内置完整的日志系统，方便问题排查和调试。

#### 客户端日志
- **配置文件**：`Client/config/log_config.json`
- **默认启用**：`log_to_file=true`（自动记录日志到文件）
- **日志位置**：`logs/client_YYYYMMDD_HHMMSS.log`（根目录下logs子目录）
- **双输出**：控制台（简化格式）+ 文件（完整格式）

#### 服务端日志
- **启用方式**：客户端启动服务端时自动添加`--log`参数
- **日志位置**：`/data/local/tmp/server_PID_YYYYMMDD_HHMMSS.log`
- **命名规则**：包含PID，支持多客户端并发场景精确识别

### 日志拉取

服务端日志位于设备端`/data/local/tmp/`目录，可通过日志管理脚本拉取到本地。

#### 步骤1：获取服务端PID
客户端启动服务端后会自动输出PID：
```
[INFO][服务端管理器] 服务正在运行，PID: 12345
```

#### 步骤2：拉取日志

**Linux/Mac平台**：
```bash
# 精确拉取（指定PID）
./fetch_server_logs.sh 12345

# 批量拉取（所有日志）
./fetch_server_logs.sh
```

**Windows平台**：
```cmd
# 精确拉取（指定PID）
fetch_server_logs.bat 12345

# 批量拉取（所有日志）
fetch_server_logs.bat
```

**说明**：
- 拉取后日志保存在本地`logs/`目录
- 不会删除设备上的日志文件（安全优先）
- 脚本优先使用内置hdc工具，其次使用系统PATH中的hdc

### 日志删除

如需清理设备上的服务端日志：

**Linux/Mac平台**：
```bash
# 精确删除（指定PID，无需确认）
./delete_server_logs.sh 12345

# 批量删除（所有日志，需确认）
./delete_server_logs.sh
```

**Windows平台**：
```cmd
# 精确删除（指定PID，无需确认）
delete_server_logs.bat 12345

# 批量删除（所有日志，需确认）
delete_server_logs.bat
```

**注意**：删除前请确保服务端进程已停止。

### 日志管理脚本位置

打包后的工具中，日志管理脚本位于根目录：
- `fetch_server_logs.sh/bat` - 拉取日志
- `delete_server_logs.sh/bat` - 删除日志
- `fetch_and_delete_server_logs.sh/bat` - 二合一日志管理脚本

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

#### 3. 服务端启动失败
- 工具安装路径不能有中文，hdc工具不支持
- 非root版本，无法安装和运行服务端程序
- 服务端闪退，可执行文件和当前OpenHarmony系统不配套，需要重新源码编译
- 服务端启动报错，基本上是编码器配置不匹配，需要查看服务端日志，分析确认具体不匹配的配置参数，然后修改参数并重新编译

#### 4. 视频卡顿
- 降低视频分辨率设置
- 检查网络连接质量
- 关闭不必要的后台程序

#### 5. 解码错误
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
