# OHScrcpy_Client - OpenHarmony投屏工具客户端

   OHScrcpy是一款为OpenHarmony系统设计的投屏工具软件，功能类似Android平台的scrcpy投屏工具。它能够将OpenHarmony设备的屏幕实时镜像到计算机，并提供设备控制功能。

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

### 核心模块
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


## 使用方法

### 1. 连接设备
   1. **USB连接**：
      - 使用USB数据线连接OpenHarmony设备到计算机
      - 在设备上启用USB调试模式
      - 首次连接时，需要在设备上授权调试权限
   2. **网线/Wi-Fi连接**：
      - 确保设备和计算机在同一局域网（有线/无线）或者用网线将设备和计算机直连

### 2. 启动客户端GUI程序
- **前置条件**：本地新建一个目录`OpenHarmony_Scrcpy`，将`Client`目录下的`所有目录` 和 `main.py`、`Server\bin\rk3568`目录下的`ohscrcpy_server`、`Server\`目录下的`ohscrcpy_server.cfg`拷贝到本地`OpenHarmony_Scrcpy`目录；如果是HarmonyOS设备，还需要在本地`OpenHarmony_Scrcpy`目录下新建一个名为`HUAWEI`的目录，然后将`Server\bin\harmonyos`目录下的`ohscrcpy_server`拷贝到本地`HUAWEI`目录下的。

- 系统控制台（命令行环境）启动客户端
```bash
python main.py
```
   1. 运行程序后，主界面将显示
   2. 点击`刷新`按钮扫描可用设备
   3. 从`设备列表`中选择要连接的设备
   4. 点击`连接`按钮开始投屏

![客户端启动GUI.png](./客户端启动GUI.png '客户端启动GUI.png')
![客户端投屏GUI.png](./客户端投屏GUI.png '客户端投屏GUI.png')

### 3. 基本操作

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
- **编码格式**：H.265/H.264

### 网络配置
- **默认端口**：27183
- **心跳间隔**：1秒
- **心跳超时**：5秒

## 日志系统

### 客户端日志配置
- **配置文件**：`config/log_config.json`
- **默认启用**：`log_to_file=true`（自动记录日志到文件）
- **日志位置**：`logs/client_YYYYMMDD_HHMMSS.log`（根目录下logs子目录）
- **双输出模式**：控制台输出（简化格式）+ 文件记录（完整格式）

**配置文件字段说明**：
```json
{
  "log_level": "INFO",         // 日志级别：DEBUG/INFO/WARN/ERROR/FATAL
  "log_to_file": true,         // 是否启用日志文件记录
  "log_dir": "logs",           // 日志目录（相对于可执行文件所在目录）
  "log_file": null,            // 日志文件名（null表示自动生成）
  "max_log_size_mb": 10,       // 最大日志文件大小（MB）
  "backup_count": 5            // 备份日志文件数量
}
```

### 服务端日志拉取

服务端日志位于设备端`/data/local/tmp/`目录，可通过日志管理脚本拉取到本地。

#### 获取服务端PID
客户端启动服务端后会自动输出PID：
```
[INFO][服务端管理器] 服务正在运行，PID: 12345
```

#### 拉取日志命令

**Linux/Mac**：
```bash
./fetch_fetch_and_delete_server_logs.sh 12345  # 精确拉取
./fetch_fetch_and_delete_server_logs.sh        # 批量拉取
```

**Windows**：
```cmd
fetch_fetch_and_delete_server_logs.bat 12345   # 精确拉取
fetch_fetch_and_delete_server_logs.bat         # 批量拉取
```

**说明**：
- 拉取后日志保存在本地`logs/`目录
- 不删除设备上的日志文件
- 脚本优先使用内置hdc，其次使用系统PATH中的hdc

### 日志清理

**Linux/Mac**：
```bash
./delete_fetch_and_delete_server_logs.sh 12345  # 精确删除（无需确认）
./delete_fetch_and_delete_server_logs.sh        # 批量删除（需确认）
```

**Windows**：
```cmd
delete_fetch_and_delete_server_logs.bat 12345   # 精确删除（无需确认）
delete_fetch_and_delete_server_logs.bat         # 批量删除（需确认）
```

**注意**：删除前请确保服务端进程已停止。

## 故障排除

### 常见问题

#### 1. 无法发现设备
- 检查USB连接是否正常
- 确保设备已启用USB调试模式
- 尝试重新插拔USB线缆
- 运行 `hdc list targets` 检查设备识别情况

#### 2. 连接失败
- 工具安装路径不能有中文，hdc工具不支持中文路径
- 检查默认端口`27183`是否被占用
- 确保设备端服务端程序已运行
- 检查防火墙设置

#### 3. 服务端启动失败
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

## 免责声明
   本工具仅供学习和研究使用，请勿用于非法用途。使用本工具造成的任何后果，开发者概不负责。

---
