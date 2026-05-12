# OpenHarmony_OHScrcpy - OpenHarmony投屏工具软件

**OpenHarmony_OHScrcpy**是一款为**OpenHarmony系统**设计的投屏工具软件，功能类似于Android平台的scrcpy投屏工具。它能够将OpenHarmony设备的屏幕实时镜像到计算机，并提供设备控制功能。

## 实现原理框图
- **计算机侧（客户端）**：基于Python跨平台实现
- **OpenHarmony设备侧（服务端）**：基于OpenHarmony系统C-API实现
![在这里插入图片描述](https://i-blog.csdnimg.cn/direct/dc0656ead0474c1f901617489006c554.png#pic_center)
## 特性

- 🖥️ **实时屏幕镜像**：低延迟显示OpenHarmony设备屏幕
- 🎯 **设备控制**：支持点击、滑动、按键等操作
- 🔌 **多种连接方式**：支持USB连接和网络连接
- 📱 **多设备管理**：支持同时连接多个设备并切换
- 🎨 **自适应分辨率**：自动调整显示尺寸，保持原始比例
- 📊 **性能监控**：实时显示FPS、网络状态等统计信息
- 🛠️ **调试功能**：内置调试工具，便于问题排查
- ⚙️ **服务自动安装和启动**：服务端自动安装和启动
## 运行效果
```bash
Windows系统双击`OHScrcpy.exe`，Linux/macOS系统命令行执行`OHScrcpy`
```
**说明**：OpenHarmony设备侧服务端会自动安装+启动，无需用户手动启动。
   1. 运行程序后，主界面将显示
   2. 点击**刷新**按钮扫描可用设备
   3. 从**设备列表**中选择要连接的设备
   4. 点击**连接**按钮开始投屏
![在这里插入图片描述](https://i-blog.csdnimg.cn/direct/11f1a7d3ec4b44228a9f80c9d0c846ef.png#pic_center)
![在这里插入图片描述](https://i-blog.csdnimg.cn/direct/186c6ba4b65241d281e2c270e6aed2e6.png#pic_center)
## 基本操作
### 屏幕控制
- **点击**：在视频区域**单击鼠标左键**
- **滑动**：在视频区域**按住鼠标左键并拖动**
- **缩放**：程序自动适应窗口大小，保持原始比例

### 按键控制
- **电源键**：点击**电源**按钮，唤醒/关闭屏幕显示
- **主页键**：点击**主页**按钮，从前台应用返回桌面
- **返回键**：点击**返回**按钮，返回上一UI页面
- **解锁键**：点击**解锁**按钮，解锁屏幕
- **音量+**：点击<strong>音量+</strong>按钮，增大音量
- **音量-**：点击<strong>音量-</strong>按钮，减小音量

### 客户端快捷键

| 快捷键 | 功能 |
|--------|------|
| F5 | 刷新设备列表 |
| F6 | 保存当前帧为调试图像 |
| F8 | 显示调试信息窗口 |
| F9 | 强制垃圾回收 |

## 项目地址
[https://gitcode.com/luodh0157/OpenHarmony_Scrcpy](https://gitcode.com/luodh0157/OpenHarmony_Scrcpy)
[https://github.com/luodh0157/OpenHarmony_Scrcpy](https://github.com/luodh0157/OpenHarmony_Scrcpy)
[https://gitee.com/luodh0157/OpenHarmony_Scrcpy](https://gitee.com/luodh0157/OpenHarmony_Scrcpy)

## 安装包下载
[https://gitcode.com/luodh0157/OpenHarmony_Scrcpy/releases](https://gitcode.com/luodh0157/OpenHarmony_Scrcpy/releases)
---
**注意：本工具仅供学习和研究使用，请勿用于非法用途。使用本工具造成的任何后果，开发者概不负责。**

