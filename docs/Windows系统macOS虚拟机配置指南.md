# Windows 系统 macOS 虚拟机配置指南

> 本指南适用于需要在 Windows 电脑上搭建 macOS 虚拟环境进行开发和打包的用户。
> 硬件要求：32GB+ 内存，NVMe SSD，支持虚拟化的 CPU（Intel VT-x / AMD-V）

---

## 目录

1. [环境准备](#1-环境准备)
2. [安装 VMware Workstation Pro](#2-安装-vmware-workstation-pro)
3. [安装 Unlocker（解锁 macOS 选项）](#3-安装-unlocker解锁-macos-选项)
4. [获取 macOS 镜像](#4-获取-macos-镜像)
5. [创建 macOS 虚拟机](#5-创建-macos-虚拟机)
6. [优化虚拟机配置](#6-优化虚拟机配置)
7. [安装 macOS 系统](#7-安装-macos-系统)
8. [配置 macOS 开发环境](#8-配置-macos-开发环境)
9. [配置共享文件夹](#9-配置共享文件夹)
10. [项目打包](#10-项目打包)
11. [常见问题排查](#11-常见问题排查)
12. [性能优化建议](#12-性能优化建议)

---

## 1. 环境准备

### 1.1 硬件要求检查

| 组件 | 最低要求 | 推荐配置 | 检查方法 |
|------|---------|---------|---------|
| CPU | 支持 VT-x/AMD-V 的 4 核 | 8 核以上 | 任务管理器 → 性能 → CPU → 虚拟化：已启用 |
| 内存 | 16GB | 32GB+ | 任务管理器 → 性能 → 内存 |
| 存储 | 100GB SSD | 500GB NVMe SSD | 此电脑 → 查看磁盘类型 |
| 显卡 | 核显即可 | 独显（VM 中无法使用） | 设备管理器 → 显示适配器 |

### 1.2 开启 CPU 虚拟化

**如果任务管理器显示"虚拟化：已禁用"，需要进入 BIOS 开启：**

```
1. 重启电脑，开机时按 F2/Del/F10（根据主板品牌不同）
2. 找到 CPU Configuration 或 Advanced 选项
3. 找到以下选项并设置为 Enabled：
   - Intel VT-x / AMD-V
   - EPT (Extended Page Tables)
4. 保存并退出（F10）
```

### 1.3 所需软件清单

| 软件 | 版本 | 用途 | 下载地址 |
|------|------|------|---------|
| VMware Workstation Pro | 17.x（个人免费） | 虚拟机平台 | https://www.vmware.com/products/workstation-pro.html |
| Unlocker | 4.x | 解锁 macOS 选项 | https://github.com/DrDonk/unlocker |
| macOS 镜像 | Ventura 13 / Sonoma 14 | 操作系统 | 见第 4 节 |
| Python | 3.11+ | 开发环境 | https://www.python.org/downloads/ |
| 7-Zip | 最新版 | 解压镜像文件 | https://www.7-zip.org/ |

---

## 2. 安装 VMware Workstation Pro

### 2.1 下载

```
官网
1. 访问：https://www.vmware.com/products/workstation-pro/workstation-pro-evaluation.html
2. 点击"Download Now"下载 Windows 版本
3. 文件名类似：VMware-workstation-full-17.x.x-xxxxxx.exe
```
```
三方
https://www.downkuai.com/soft/123409.html
https://www.nruan.com/6079.html

```

### 2.2 安装

```
1. 双击安装包
2. 点击"下一步"
3. 接受许可协议
4. 选择安装路径（建议 D:\Program Files\VMware\）
5. 勾选"增强型键盘驱动程序"（可选）
6. 取消勾选"启动时检查产品更新"和"加入客户体验改善计划"
7. 点击"安装"
8. 安装完成后点击"完成"（无需重启）
```

### 2.3 验证安装

```
1. 打开 VMware Workstation
2. 帮助 → 关于 VMware Workstation
3. 确认版本号为 17.x
4. 个人使用免费，无需激活
```

---

## 3. 安装 Unlocker（解锁 macOS 选项）

### 3.1 下载 Unlocker

**方法一：使用 Git（推荐）**

```powershell
# 打开 PowerShell（普通权限即可）
cd $env:USERPROFILE\Downloads
git clone https://github.com/DrDonk/unlocker.git
```

**方法二：手动下载**

```
1. 访问：https://github.com/DrDonk/unlocker
2. 点击"Code" → "Download ZIP"
3. 解压到：C:\Users\你的用户名\Downloads\unlocker
```

### 3.2 安装 Unlocker

```powershell
# 1. 关闭 VMware Workstation（必须关闭！）
# 2. 以管理员身份打开 PowerShell
#    开始菜单 → 搜索"PowerShell" → 右键 → 以管理员身份运行

# 3. 进入 unlocker 目录
cd $env:USERPROFILE\Downloads\unlocker

# 4. 运行安装脚本（右键以管理员身份运行）
.\win-install.cmd
```

**安装过程输出示例：**

```
[*] VMware Workstation detected
[*] Installing VMware tools...
[*] Patching vmware-vmx.exe...
[*] Patching vmware-vmx-debug.exe...
[*] Patching vmware-vmx-stats.exe...
[*] Creating gettools.exe...
[*] Downloading Darwin tools...
[+] Unlocker installed successfully!
```

### 3.3 验证解锁

```
1. 打开 VMware Workstation
2. 文件 → 新建虚拟机 → 自定义
3. 在"客户机操作系统"列表中，应该能看到：
   ✓ Apple Mac OS X
4. 版本下拉菜单中应该有：
   ✓ macOS 13
   ✓ macOS 14
   ✓ macOS 12 等
```

**如果看不到 macOS 选项：**
- 确保 VMware 已完全关闭后重新运行 win-install.cmd
- 以管理员身份运行
- 检查杀毒软件是否拦截

---

## 4. 获取 macOS 镜像

### 方式一：GitHub 直接下载（推荐，最简单）

#### 4.1.1 下载镜像

```
1. 访问：https://github.com/thenickdude/KVM-Opencore/releases
2. 找到最新 Release（如 vXX.X）
3. 下载以下文件之一：
   - macOS-Ventura.zip（约15GB，推荐，稳定）
   - macOS-Sonoma.zip（约16GB，较新）
   - macOS-Monterey.zip（约14GB，稳定）
4. 等待下载完成（建议用迅雷或 IDM 加速）
```

苹果系统之家
https://macoshome.com/macos
https://pan.baidu.com/s/1GoE3ZVWkUIXpIz0aAunllA

MacOS 镜像资源
https://www.kdocs.cn/l/cbuxk54UgVWD

#### 4.1.2 解压文件

```powershell
# 创建工作目录
mkdir D:\VMs\macOS

# 使用 7-Zip 解压（推荐）
# 右键下载的 zip 文件 → 7-Zip → 提取到 "D:\VMs\macOS\"

# 或使用 PowerShell（较慢）
Expand-Archive -Path "D:\Downloads\macOS-Ventura.zip" -DestinationPath "D:\VMs\macOS"
```

#### 4.1.3 验证文件

```powershell
# 检查文件大小（应约15GB）
Get-Item "D:\VMs\macOS\macOS.vmdk" | Select-Object Name, Length

# 计算 SHA256 哈希
Get-FileHash -Path "D:\VMs\macOS\macOS.vmdk" -Algorithm SHA256
```

**解压后应包含：**
```
D:\VMs\macOS\
├── macOS.vmdk          # 虚拟磁盘文件（核心文件）
├── OpenCore.qcow2      # OpenCore引导（可选）
└── README.md           # 使用说明
```

---

### 方式二：macrecovery 脚本下载（官方来源，更安全）

#### 4.2.1 准备环境

```powershell
# Windows PowerShell（管理员）

# 安装 Git（如果没有）
winget install Git.Git

# 安装 Python 3.11（如果没有）
winget install Python.Python.3.11

# 验证安装
git --version
python --version
```

#### 4.2.2 下载 OpenCore 工具

```powershell
# 创建工作目录
mkdir D:\macOS_Dev
cd D:\macOS_Dev

# 克隆 OpenCore 工具
git clone https://github.com/acidanthera/OpenCorePkg.git
cd OpenCorePkg\Utilities\macrecovery
```

#### 4.2.3 下载 macOS Recovery 镜像

```powershell
# 下载 macOS Ventura 13 Recovery
python macrecovery.py -b Mac-FFE5EF870D7BA81A -m 00000000000000000 download

# 其他版本 Board ID：
# macOS Sonoma 14:    Mac-827FAC58A8FDFA22
# macOS Monterey 12:  Mac-937A206F2EE63C01
# macOS Big Sur 11:   Mac-2BD1B31983FE1663
```

**下载过程：**
```
运行后会显示进度：
Downloading...
[======>                     ] 25%
[=============>              ] 50%
...

下载完成后生成：
- BaseSystem.dmg（约800MB）
- BaseSystem.chunklist
```

#### 4.2.4 配置 OpenCore 引导

```powershell
# 1. 下载 OpenCore 完整包
cd D:\macOS_Dev
git clone https://github.com/thenickdude/KVM-Opencore.git

# 2. 复制 Recovery 镜像到 OpenCore 目录
copy OpenCorePkg\Utilities\macrecovery\BaseSystem.dmg KVM-Opencore\

# 3. 按照 KVM-Opencore 的 README 配置 EFI 分区
cd KVM-Opencore
# 阅读 README.md，按照说明配置
```

#### 4.2.5 启动安装

```
1. 在 VMware 中创建新虚拟机（100GB NVMe 磁盘）
2. 挂载 OpenCore 引导
3. 启动虚拟机，进入 Recovery 模式
4. 使用磁盘工具格式化虚拟磁盘（APFS 格式）
5. 选择"重新安装 macOS"
6. 连接网络，从 Apple 服务器下载完整系统
   （约 30-60 分钟，取决于网速）
```

---

### 两种方式对比

| 特性 | GitHub 镜像 | macrecovery |
|------|------------|-------------|
| 下载速度 | 快（一次性下载） | 慢（需二次下载） |
| 文件大小 | ~15GB | ~800MB + 在线下载 ~12GB |
| 安全性 | 社区验证 | Apple 官方来源 |
| 配置难度 | 简单 | 中等 |
| 推荐度 | ★★★★★ | ★★★★ |

**推荐：** 追求简单快速选方式一，追求安全可靠选方式二。

---

## 5. 创建 macOS 虚拟机

### 5.1 新建虚拟机

```
1. 打开 VMware Workstation
2. 文件 → 新建虚拟机 → 自定义(高级)
3. 点击"下一步"
```

### 5.2 硬件兼容性

```
硬件兼容性：Workstation 17.x（默认）
点击"下一步"
```

### 5.3 安装来源

```
选择"稍后安装操作系统"
点击"下一步"
```

### 5.4 选择操作系统

```
客户机操作系统：Apple Mac OS X
版本：macOS 13.x（根据下载的镜像版本选择）
点击"下一步"
```

### 5.5 命名虚拟机

```
虚拟机名称：macOS_Dev（或自定义）
位置：D:\VMs\macOS_Dev（建议 NVMe SSD）
点击"下一步"
```

### 5.6 处理器配置

```
处理器数量：1
每个处理器的核心数量：6
勾选"虚拟化 Intel VT-x/EPT 或 AMD-V/RVI"
点击"下一步"
```

### 5.7 内存配置

```
此虚拟机的内存：12GB（32GB 总内存的 37.5%）
点击"下一步"
```

### 5.8 网络类型

```
网络连接类型：NAT 模式
点击"下一步"
```

### 5.9 I/O 控制器类型

```
I/O 控制器类型：LSI Logic（默认）
点击"下一步"
```

### 5.10 磁盘类型

```
磁盘类型：NVMe（关键！不要选 SCSI 或 SATA）
点击"下一步"
```

### 5.11 选择磁盘

**方式一（使用现有镜像）：**
```
选择"使用现有虚拟磁盘"
浏览选择：D:\VMs\macOS\macOS.vmdk
点击"下一步"
```

**方式二（创建新磁盘）：**
```
选择"创建新虚拟磁盘"
最大磁盘大小：100GB
勾选"将虚拟磁盘拆分成多个文件"
点击"下一步"
```

### 5.12 完成

```
点击"完成"
```

---

## 6. 优化虚拟机配置

### 6.1 编辑 .vmx 文件

```
1. 关闭 VMware Workstation
2. 打开虚拟机目录：D:\VMs\macOS_Dev\
3. 找到 macOS_Dev.vmx 文件
4. 右键 → 打开方式 → 记事本
```

### 6.2 添加优化参数

**在文件末尾添加以下内容：**

```ini
smc.version = "0"
cpuid.0.eax = "0000:0000:0000:0000:0000:0000:0000:1010"
cpuid.0.ebx = "0111:0101:0110:1110:0110:0101:0100:0111"
cpuid.0.ecx = "0110:1100:0110:0101:0111:0100:0110:1110"
cpuid.0.edx = "0100:1001:0110:0101:0110:1110:0110:1001"
cpuid.1.eax = "0000:0000:0000:0001:0000:0110:0111:0001"
cpuid.1.ebx = "0000:0010:0000:0001:0000:1000:0000:0000"
cpuid.1.ecx = "1000:0010:1001:1000:0010:0010:0000:0011"
cpuid.1.edx = "0000:0111:1000:1011:1111:1011:1111:1111"
vhv.enable = "FALSE"
vpmc.enable = "FALSE"
usb.vbluetooth.startconn = "TRUE"
```

### 6.3 保存并关闭

```
Ctrl + S 保存
关闭记事本
```

---

## 7. 安装 macOS 系统

### 7.1 首次启动

```
1. 打开 VMware Workstation
2. 选择 macOS_Dev 虚拟机
3. 点击"开启此虚拟机"
```

### 7.2 OpenCore 引导（如适用）

```
1. 如果看到 OpenCore 引导菜单
2. 使用方向键选择"macOS"或"Install macOS"
3. 按回车
```

### 7.3 磁盘格式化（新磁盘需要）

```
1. 进入 macOS 恢复模式后
2. 选择"磁盘工具" → 继续
3. 选择左侧的"VMware Virtual NVMe Disk"
4. 点击"抹掉"
5. 名称：Macintosh HD
6. 格式：APFS
7. 方案：GUID 分区图
8. 点击"抹掉"
9. 完成后关闭磁盘工具
```

### 7.4 安装 macOS

```
1. 选择"重新安装 macOS" → 继续
2. 接受软件许可协议
3. 选择"Macintosh HD" → 继续
4. 等待安装完成（约 30-45 分钟，期间会重启几次）
```

### 7.5 初始设置

```
1. 选择国家/地区：中国 → 继续
2. 键盘布局：简体中文 → 继续
3. 迁移助理：现在不传输任何信息 → 继续
4. Apple ID：跳过（可稍后设置）
5. 创建电脑账户：
   - 全名：Developer
   - 账户名称：developer
   - 密码：（设置一个简单密码）
6. 关闭"允许在 iCloud 中存储文件"
7. 关闭"查找我的 Mac"
8. 关闭"分析"
9. 完成设置
```

### 7.6 创建快照（重要！）

```
1. 虚拟机 → 快照 → 拍摄快照
2. 名称：Clean Install
3. 描述：macOS 初始安装完成
4. 点击"拍摄"
```

**以后如果系统出现问题，可以随时恢复到此快照。**

---

## 8. 配置 macOS 开发环境

### 8.1 打开终端

```
1. 启动台 → 其他 → 终端
2. 或按 Command + 空格，搜索"终端"
```

### 8.2 安装 Xcode Command Line Tools

```bash
xcode-select --install
```

**弹出安装窗口后点击"安装"，等待完成（约 5-10 分钟）。**

### 8.3 安装 Homebrew

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

**安装完成后执行：**

```bash
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"
```

### 8.4 安装 Python 和开发工具

```bash
brew install python@3.11 git wget zip
```

### 8.5 配置 Python pip 镜像（加速下载）

```bash
mkdir -p ~/.pip
cat > ~/.pip/pip.conf << 'EOF'
[global]
index-url = https://pypi.tuna.tsinghua.edu.cn/simple
trusted-host = pypi.tuna.tsinghua.edu.cn
EOF
```

### 8.6 创建 Python 虚拟环境

```bash
python3 -m venv ~/venv_ohscrcpy
source ~/venv_ohscrcpy/bin/activate
```

### 8.7 安装项目依赖

```bash
pip install av numpy pillow psutil pyinstaller
```

### 8.8 验证安装

```bash
python3 --version    # 应显示 Python 3.11.x
pip list             # 应列出已安装的包
```

### 8.9 优化系统设置

```bash
# 关闭不必要的动画
defaults write NSGlobalDomain NSAutomaticWindowAnimationsEnabled -bool false
defaults write com.apple.finder DisableAllAnimations -bool true

# 关闭 Spotlight 索引（减少磁盘 IO）
sudo mdutil -a -i off

# 减少透明效果
defaults write com.apple.universalaccess reduceTransparency -bool true
```

---

## 9. 配置共享文件夹

### 9.1 VMware 设置

```
1. 虚拟机 → 设置
2. 选项 → 共享文件夹
3. 选择"始终启用"
4. 点击"添加"
5. 下一步
6. 主机路径：D:\Projects\OpenHarmony_Scrcpy（你的项目路径）
7. 名称：OpenHarmony_Scrcpy
8. 勾选"启用此共享"
9. 完成 → 确定
```

### 9.2 macOS 中访问

```bash
# 共享文件夹挂载点
cd "/Volumes/VMware Shared Folders/OpenHarmony_Scrcpy"

# 查看文件
ls -la
```

### 9.3 拷贝到本地（推荐，性能更好）

```bash
# 创建项目目录
mkdir -p ~/Projects

# 拷贝项目到本地
cp -r "/Volumes/VMware Shared Folders/OpenHarmony_Scrcpy" ~/Projects/

# 进入项目目录
cd ~/Projects/OpenHarmony_Scrcpy
```

### 9.4 自动同步脚本（可选）

```bash
# 安装 fswatch
brew install fswatch

# 创建同步脚本
cat > ~/sync_project.sh << 'EOF'
#!/bin/bash
# 从 Windows 同步到 macOS
rsync -avz --delete "/Volumes/VMware Shared Folders/OpenHarmony_Scrcpy/" ~/Projects/OpenHarmony_Scrcpy/
echo "同步完成: $(date)"
EOF

chmod +x ~/sync_project.sh

# 设置自动同步（后台运行）
nohup fswatch -o "/Volumes/VMware Shared Folders/OpenHarmony_Scrcpy" | while read; do
    rsync -avz "/Volumes/VMware Shared Folders/OpenHarmony_Scrcpy/" ~/Projects/OpenHarmony_Scrcpy/
    echo "同步完成: $(date)"
done > ~/sync.log 2>&1 &
```

---

## 10. 项目打包

### 10.1 进入项目目录

```bash
cd ~/Projects/OpenHarmony_Scrcpy/Package/Executer
```

### 10.2 激活虚拟环境

```bash
source ~/venv_ohscrcpy/bin/activate
```

### 10.3 运行打包脚本

```bash
./make_ohscrcpy_executer.sh
```

**如果提示权限不足：**

```bash
chmod +x make_ohscrcpy_executer.sh
./make_ohscrcpy_executer.sh
```

### 10.4 打包过程

```
脚本会自动：
1. 检查 Python 和依赖
2. 清理旧构建文件
3. 安装 Python 依赖
4. 运行 PyInstaller 打包
5. 生成文件哈希
6. 创建 ZIP 发布包
```

### 10.5 打包结果

```
输出位置：output/macOS/arm64/ 或 output/macOS/x64/
包含文件：
- OHScrcpy                  # 可执行文件
- OHScrcpy_hash.txt         # 哈希校验文件
- OHScrcpy_Exec_macOS_arm64_v2.1.0.zip  # ZIP 发布包
```

### 10.6 测试可执行文件

```bash
# 运行测试
./output/macOS/arm64/OHScrcpy --help

# 或双击运行
open ./output/macOS/arm64/OHScrcpy
```

---

## 11. 常见问题排查

### 11.1 VM 启动黑屏

**原因：** Unlocker 未正确安装

**解决：**
```
1. 关闭 VMware Workstation
2. 以管理员身份重新运行 win-install.cmd
3. 重新启动 VMware
```

### 11.2 macOS 安装卡顿

**原因：** CPU 核心数不足

**解决：**
```
1. 关闭虚拟机
2. 虚拟机 → 设置 → 处理器
3. 增加核心数到 6 或 8
4. 重新启动
```

### 11.3 网络不通

**原因：** NAT 服务未启动

**解决：**
```powershell
# Windows PowerShell（管理员）
Restart-Service VMnetDHCP
Restart-Service "VMware NAT Service"
```

### 11.4 共享文件夹不显示

**原因：** VMware Tools 未安装

**解决：**
```
1. 虚拟机 → 安装 VMware Tools
2. macOS 中会挂载 VMware Tools 光盘
3. 双击安装 VMware Tools.pkg
4. 安装完成后重启虚拟机
```

### 11.5 Python 安装慢

**原因：** 网络问题

**解决：**
```bash
# 使用清华镜像源
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple <包名>
```

### 11.6 PyInstaller 打包失败

**原因：** 缺少依赖

**解决：**
```bash
# 确保激活虚拟环境
source ~/venv_ohscrcpy/bin/activate

# 重新安装依赖
pip install --upgrade av numpy pillow psutil pyinstaller
```

### 11.7 打包后无法运行

**原因：** 缺少动态库

**解决：**
```bash
# 检查依赖库
otool -L ./dist/OHScrcpy

# 查看缺失的库
# 如果有 @not_found 标记，需要安装对应库
```

### 11.8 虚拟机无法启动（Unlocker 问题）

```powershell
# 完全卸载 Unlocker
cd $env:USERPROFILE\Downloads\unlocker
.\win-uninstall.cmd

# 重新安装
.\win-install.cmd
```

### 11.9 macOS 时间不正确

```bash
# 在 macOS 终端中执行
sudo sntp -sS time.apple.com
```

### 11.10 磁盘空间不足

```bash
# 清理缓存
rm -rf ~/Library/Caches/*
rm -rf ~/.Trash/*

# 清理 Homebrew 缓存
brew cleanup
```

---

## 12. 性能优化建议

### 12.1 VMware 设置优化

```
1. 编辑 → 首选项 → 内存
   - 勾选"允许交换大部分虚拟机内存"
   
2. 虚拟机设置 → 显示器
   - 关闭"加速 3D 图形"（macOS 不支持）
   
3. 虚拟机设置 → 硬盘
   - 勾选"预分配磁盘空间"（性能更好）
   
4. 虚拟机设置 → 处理器
   - 勾选"虚拟化 Intel VT-x/EPT"
```

### 12.2 macOS 内部优化

```bash
# 关闭视觉效果
defaults write NSGlobalDomain NSAutomaticWindowAnimationsEnabled -bool false
defaults write com.apple.finder DisableAllAnimations -bool true
defaults write com.apple.dock expose-animation-duration -float 0.1
killall Dock

# 关闭 Spotlight 索引
sudo mdutil -a -i off

# 关闭 Time Machine 本地快照
sudo tmutil disablelocal

# 减少透明效果
defaults write com.apple.universalaccess reduceTransparency -bool true

# 关闭自动更新
sudo softwareupdate --schedule off
```

### 12.3 资源分配建议

| 资源 | 分配给 macOS | 留给 Windows | 说明 |
|------|-------------|-------------|------|
| CPU | 6 核 | 剩余核心 | 不要超过物理核心数的 75% |
| 内存 | 12GB | 20GB | 32GB 总内存的 37.5% |
| 磁盘 | 100GB | 剩余空间 | NVMe SSD，预分配空间 |

### 12.4 定期维护

```bash
# 每周清理一次
brew cleanup
rm -rf ~/Library/Caches/*
pip cache purge

# 每月整理一次虚拟机快照
# 虚拟机 → 快照管理器 → 删除旧快照
```

---

## 附录 A：完整时间线

### 第 1 天：环境准备（约 2 小时）

```
□ 检查硬件要求（5 分钟）
□ 开启 CPU 虚拟化（如需，10 分钟）
□ 下载并安装 VMware Workstation Pro（15 分钟）
□ 下载并运行 Unlocker（10 分钟）
□ 下载 macOS 镜像（1-2 小时，可后台）
□ 验证镜像完整性（5 分钟）
```

### 第 2 天：VM 安装配置（约 1.5 小时）

```
□ 创建虚拟机（15 分钟）
□ 优化 .vmx 配置文件（5 分钟）
□ 启动并安装 macOS（45 分钟）
□ 完成初始设置（15 分钟）
□ 安装 VMware Tools（10 分钟）
□ 创建快照（5 分钟）
```

### 第 3 天：开发环境配置（约 1 小时）

```
□ 安装 Xcode Command Line Tools（10 分钟）
□ 安装 Homebrew（10 分钟）
□ 安装 Python 和开发工具（10 分钟）
□ 配置 pip 镜像（5 分钟）
□ 创建虚拟环境并安装依赖（15 分钟）
□ 配置共享文件夹（10 分钟）
```

### 第 4 天：打包测试（约 30 分钟）

```
□ 拷贝项目到 macOS（5 分钟）
□ 运行打包脚本（15 分钟）
□ 测试生成的可执行文件（10 分钟）
```

---

## 附录 B：常用命令速查

### Windows PowerShell

```powershell
# 检查虚拟化是否开启
Get-ComputerInfo | Select-Object HyperVisorPresent

# 计算文件哈希
Get-FileHash -Path "文件路径" -Algorithm SHA256

# 重启 VMware 服务
Restart-Service VMnetDHCP
Restart-Service "VMware NAT Service"

# 查看虚拟机进程
Get-Process vmware-vmx
```

### macOS Terminal

```bash
# 激活虚拟环境
source ~/venv_ohscrcpy/bin/activate

# 查看 Python 版本
python3 --version

# 查看已安装包
pip list

# 查看系统信息
sw_vers
uname -a

# 查看磁盘使用
df -h

# 查看内存使用
vm_stat

# 查看 CPU 信息
sysctl -n machdep.cpu.brand_string
sysctl -n hw.ncpu
```

---

## 附录 C：重要文件路径

### Windows 端

```
VMware 安装目录：
C:\Program Files (x86)\VMware\VMware Workstation\

Unlocker 目录：
C:\Users\你的用户名\Downloads\unlocker\

虚拟机目录：
D:\VMs\macOS_Dev\

.vmx 配置文件：
D:\VMs\macOS_Dev\macOS_Dev.vmx

虚拟磁盘文件：
D:\VMs\macOS\macOS.vmdk
```

### macOS 端

```
共享文件夹：
/Volumes/VMware Shared Folders/

项目目录：
~/Projects/OpenHarmony_Scrcpy/

虚拟环境：
~/venv_ohscrcpy/

Homebrew 安装：
/opt/homebrew/

Python 安装：
/opt/homebrew/bin/python3

pip 配置：
~/.pip/pip.conf

打包输出：
~/Projects/OpenHarmony_Scrcpy/Package/Executer/output/
```

---

## 附录 D：安全注意事项

```
1. 镜像来源：仅从可信来源下载 macOS 镜像
2. 哈希校验：下载后务必校验文件完整性
3. Apple 许可：macOS 仅在 Apple 硬件上运行符合 EULA，虚拟机违反许可
4. 网络隔离：开发环境建议使用 NAT 模式，不暴露到公网
5. 快照备份：定期创建快照，防止系统损坏
6. 密码安全：不要使用弱密码，但也不要忘记（虚拟机恢复较麻烦）
```

---

## 附录 E：参考链接

```
VMware Workstation Pro:
https://www.vmware.com/products/workstation-pro.html

Unlocker:
https://github.com/DrDonk/unlocker

KVM-Opencore:
https://github.com/thenickdude/KVM-Opencore

OpenCorePkg:
https://github.com/acidanthera/OpenCorePkg

Homebrew:
https://brew.sh/

Python:
https://www.python.org/

PyInstaller:
https://pyinstaller.org/
```

---

> **文档版本：** v1.0
> **最后更新：** 2026-05-08
> **适用项目：** OpenHarmony_Scrcpy
> **作者：** luodh0157
