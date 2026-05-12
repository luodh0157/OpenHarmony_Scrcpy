# GitHub Actions CI/CD 配置指南

> 本文档归档 GitHub Actions CI/CD 配置方案，用于 OpenHarmony Scrcpy 跨平台自动化构建。

---

## 目录

1. [概述](#1-概述)
2. [文件结构](#2-文件结构)
3. [工作流说明](#3-工作流说明)
4. [触发方式](#4-触发方式)
5. [构建产物](#5-构建产物)
6. [发布 Release](#6-发布-release)
7. [关键技术点](#7-关键技术点)
8. [常见问题](#8-常见问题)

---

## 1. 概述

### 为什么选择 GitHub Actions？

| 对比项 | GitHub Actions | VMware 虚拟机 | Gitee Go |
|--------|---------------|--------------|----------|
| **免费额度** | 公开仓库无限 | 硬件投入 | 仅企业版付费 |
| **macOS arm64 支持** | ✅ M1/M2/M3 真机 | ❌ 不支持 | ❌ 不支持 |
| **法律合规** | ✅ 完全合规 | ❌ 违反 Apple EULA | ✅ 国内合规 |
| **自动化** | ✅ 触发式自动构建 | ❌ 手动操作 | ✅ 支持 |

### 构建平台矩阵

| Runner | 操作系统 | 架构 | 说明 |
|--------|---------|------|------|
| `windows-latest` | Windows Server 2022 | x64 | Windows Executer + Installer |
| `ubuntu-latest` | Ubuntu 22.04 | x64 | Linux Executer + Installer + 单元测试 |
| `macos-latest` | macOS 14 | arm64 (M1) | macOS arm64 Executer + Installer |
| `macos-13` | macOS 13 | x64 (Intel) | macOS x64 Executer + Installer |

### 打包类型

| 类型 | 说明 | 输出格式 |
|------|------|---------|
| **Executer** | 单文件可执行程序，无需安装 | ZIP 包（包含可执行文件） |
| **Installer** | 安装包，需要安装后使用 | Windows: EXE，Linux/macOS: ZIP（含安装脚本） |

---

## 2. 文件结构

```
.github/
└── workflows/
    ├── test.yml          # 单元测试工作流
    └── build.yml         # 主构建工作流（全平台）

Client/
└── requirements.txt      # Python 依赖列表
```

---

## 3. 工作流说明

### 3.1 test.yml - 单元测试

**触发条件**：
- push 到 main/master
- Pull Request
- 被 build.yml 调用

**执行内容**：
- pytest 单元测试
- mypy 类型检查（可选）

**运行环境**：ubuntu-latest

### 3.2 build.yml - 主构建

**触发条件**：
- push 到 main/master（测试 + 构建，不发布）
- push tag `v*`（测试 + 构建 + 发布 Release）
- Pull Request（测试 + 构建，不发布）
- 手动触发（workflow_dispatch）

**构建流程**：

```
┌──────────────────────────────────────────────────────────────┐
│                    Push / PR / Tag 触发                       │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│                  test.yml: pytest + mypy                      │
│                  (Linux Runner, 单元测试)                      │
└──────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┴─────────────────────┐
        │                                           │
        ▼                                           ▼
┌───────────────────────────┐           ┌───────────────────────────┐
│     Executer 构建          │           │     Installer 构建        │
│  (单文件可执行程序)         │           │  (安装包)                 │
└───────────────────────────┘           └───────────────────────────┘
        │                                           │
        ├─ Windows x64 (build_executer.bat)        ├─ Windows x64 (build_installer.bat)
        ├─ Linux x64 (build_executer.sh)          ├─ Linux x64 (build_installer.sh)
        ├─ macOS arm64 (build_executer.sh)        ├─ macOS arm64 (build_installer.sh)
        └─ macOS x64 (build_executer.sh)          └─ macOS x64 (build_installer.sh)
        │                                           │
        ├─ 自动生成 .icns (macOS)                  ├─ 安装 Inno Setup (Windows)
        ├─ 测试可执行文件运行                       ├─ 自动生成 .icns (macOS)
        └─ 上传 Artifacts                          ├─ 测试可执行文件运行
                                                    └ 上传 Artifacts
        │                                           │
        └─────────────────────┬─────────────────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │  上传 Artifacts     │
                    │  (8个构建产物)      │
                    │  (保留 30 天)       │
                    └─────────────────────┘
                              │
                              ▼ (仅 refs/tags/v* 时)
                    ┌─────────────────────┐
                    │  创建 GitHub        │
                    │  Release            │
                    │  (包含所有产物)     │
                    └─────────────────────┘
```

**构建 Job 清单**（共 8 个）：

| Job 名称 | 平台 | 类型 | 依赖脚本 |
|---------|------|------|---------|
| `build-windows-executer` | Windows x64 | Executer | `build_executer.bat` |
| `build-windows-installer` | Windows x64 | Installer | `build_installer.bat` + Inno Setup |
| `build-linux-executer` | Linux x64 | Executer | `build_executer.sh` |
| `build-linux-installer` | Linux x64 | Installer | `build_installer.sh` |
| `build-macos-arm64-executer` | macOS arm64 | Executer | `build_executer.sh` |
| `build-macos-arm64-installer` | macOS arm64 | Installer | `build_installer.sh` |
| `build-macos-x64-executer` | macOS x64 | Executer | `build_executer.sh` |
| `build-macos-x64-installer` | macOS x64 | Installer | `build_installer.sh` |

---

## 4. 触发方式

### 4.1 日常开发测试

```bash
git push origin main
```

效果：运行单元测试，不构建不发布

### 4.2 Pull Request 检查

创建 PR 时自动运行测试。

### 4.3 正式发布

```bash
# 创建 tag 并推送
git tag v2.2.0
git push origin v2.2.0

# 或一步完成
git tag v2.2.0 && git push origin v2.2.0
```

效果：测试 → 构建 → 测试可执行文件 → 发布 GitHub Release

### 4.4 手动触发

1. 打开 GitHub 仓库
2. 点击 **Actions**
3. 选择 **Build OHScrcpy Multi-Platform**
4. 点击 **Run workflow**

---

## 5. 构建产物

### 5.1 Artifacts 下载

构建成功后，在 **Actions → 对应运行 → Artifacts** 区域下载：

| Artifact | 类型 | 平台 | 架构 |
|----------|------|------|------|
| `OHScrcpy-Executer-Windows-x64` | Executer | Windows | x64 |
| `OHScrcpy-Installer-Windows-x64` | Installer | Windows | x64 |
| `OHScrcpy-Executer-Linux-x64` | Executer | Linux | x64 |
| `OHScrcpy-Installer-Linux-x64` | Installer | Linux | x64 |
| `OHScrcpy-Executer-macOS-arm64` | Executer | macOS | arm64 (M1/M2/M3) |
| `OHScrcpy-Installer-macOS-arm64` | Installer | macOS | arm64 |
| `OHScrcpy-Executer-macOS-x64` | Executer | macOS | x64 (Intel) |
| `OHScrcpy-Installer-macOS-x64` | Installer | macOS | x64 |

**保留时间**：30 天

### 5.2 Release 下载

tag 发布后，在 **Releases** 页面下载：

**Executer（单文件可执行程序）**：
```
OHScrcpy_Exec_Windows_x64_v2.2.0.zip
OHScrcpy_Exec_Linux_x64_v2.2.0.zip
OHScrcpy_Exec_macOS_arm64_v2.2.0.zip
OHScrcpy_Exec_macOS_x64_v2.2.0.zip
```

**Installer（安装包）**：
```
OHScrcpy_Setup_Windows_x64_v2.2.0.exe    # Windows 安装程序
OHScrcpy_Setup_Linux_x64_v2.2.0.zip      # Linux 安装包（含安装脚本）
OHScrcpy_Setup_macOS_arm64_v2.2.0.zip    # macOS arm64 安装包
OHScrcpy_Setup_macOS_x64_v2.2.0.zip      # macOS x64 安装包
````

---

## 6. 发布 Release

### 条件

仅当 `refs/tags/v*` 时触发发布。

### Release 内容

- 8 个构建产物（Executer + Installer，各 4 个平台）
- 哈希校验文件
- 自动生成的 Release Notes

### Release Body 示例

```markdown
## OpenHarmony Scrcpy v2.2.0

### Downloads

| Type | Platform | Architecture | File |
|------|----------|-------------|------|
| Executer | Windows | x64 | OHScrcpy_Exec_Windows_x64_*.zip |
| Executer | Linux | x64 | OHScrcpy_Exec_Linux_x64_*.zip |
| Executer | macOS | arm64 (M1/M2/M3) | OHScrcpy_Exec_macOS_arm64_*.zip |
| Executer | macOS | x64 (Intel) | OHScrcpy_Exec_macOS_x64_*.zip |
| Installer | Windows | x64 | OHScrcpy_Setup_Windows_x64_*.exe |
| Installer | Linux | x64 | OHScrcpy_Setup_Linux_x64_*.zip |
| Installer | macOS | arm64 | OHScrcpy_Setup_macOS_arm64_*.zip |
| Installer | macOS | x64 | OHScrcpy_Setup_macOS_x64_*.zip |

### Executer (单文件)

Portable executable, no installation required:
1. Download and extract the ZIP
2. Run `OHScrcpy` directly

### Installer (安装包)

Installation required:
1. Windows: Double-click `OHScrcpy_Setup_*.exe`
2. Linux/macOS: Extract ZIP, run `install_ohscrcpy.sh`
```

### Downloads

| Platform | Architecture | File |
|----------|-------------|------|
| Windows | x64 | OHScrcpy-Windows-x64.zip |
| Linux | x64 | OHScrcpy-Linux-x64.zip |
| macOS | arm64 (M1/M2/M3) | OHScrcpy-macOS-arm64.zip |
| macOS | x64 (Intel) | OHScrcpy-macOS-x64.zip |

### Usage

1. Download the ZIP for your platform
2. Extract to any directory
3. Run `OHScrcpy` (Windows: `OHScrcpy.exe`)
```

---

## 7. 关键技术点

### 7.1 macOS .icns 自动生成

由于项目只有 `app.ico`，macOS 构建时需要自动生成 `.icns`：

```bash
# 步骤 1：使用 PIL 从 .ico 提取 PNG
python3 -c "from PIL import Image; img = Image.open('app.ico'); img.save('icon_512.png', 'PNG')"

# 步骤 2：使用 sips 生成多尺寸 PNG
mkdir -p icon.iconset
sips -z 16 16 icon_512.png --out icon.iconset/icon_16x16.png
sips -z 32 32 icon_512.png --out icon.iconset/icon_16x16@2x.png
# ... 其他尺寸

# 步骤 3：使用 iconutil 生成 .icns
iconutil -c icns icon.iconset -o app.icns
```

### 7.2 清华镜像源加速

所有 `pip install` 命令添加镜像源：

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 7.3 一键脚本调用

使用 `Package/build_executer.sh` 和 `Package/build_executer.bat`：

- 自动调用 prepare → make → clear
- 内置 `NO_PAUSE=1` 禁用交互暂停
- 完整错误处理

### 7.4 可执行文件测试

由于是 GUI 程序但有命令行日志输出：

```bash
# Linux/macOS
./OHScrcpy --help 2>&1 | head -10

# Windows PowerShell
& OHScrcpy.exe --help 2>&1 | Select-Object -First 10
```

---

## 8. 常见问题

### Q1: PyAV 安装失败？

**原因**：缺少 FFmpeg

**解决**：
```yaml
# Linux
sudo apt-get install -y ffmpeg libavcodec-dev libavformat-dev

# macOS
brew install ffmpeg
```

### Q2: Windows 构建脚本的 pause 影响 CI？

**说明**：CI 环境中 `pause` 自动跳过，不影响构建。脚本最后的 `pause` 不需要修改。

### Q3: macOS arm64 构建产物位置？

**位置**：`Package/Executer/output/macOS/arm64/`

### Q4: 如何下载特定构建产物？

**方法**：
1. GitHub → Actions → 选择成功的运行
2. Artifacts 区域 → 点击下载

### Q5: Release 发布失败？

**检查**：
- 确认 tag 格式为 `v*`（如 `v2.2.0`）
- 确认所有构建 job 成功
- 检查 `GITHUB_TOKEN` 权限

### Q6: 如何更新版本号？

版本号跟随 Git tag，无需修改代码。

---

## 参考链接

- GitHub Actions 文档：https://docs.github.com/en/actions
- Runner 类型说明：https://docs.github.com/en/actions/using-github-hosted-runners/about-github-hosted-runners
- PyInstaller 文档：https://pyinstaller.org/

---

> **文档版本：** v1.0
> **最后更新：** 2026-05-12
> **适用项目：** OpenHarmony_Scrcpy
> **作者：** luodh0157