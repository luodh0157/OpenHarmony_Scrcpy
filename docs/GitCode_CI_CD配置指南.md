# GitCode CI/CD 配置指南

> 本文档说明 GitCode CI/CD（基于 GitLab CI）配置方案，用于 OpenHarmony Scrcpy 跨平台自动化构建。

---

## 目录

1. [概述](#1-概述)
2. [文件结构](#2-文件结构)
3. [构建 Job 说明](#3-构建-job-说明)
4. [触发方式](#4-触发方式)
5. [构建产物](#5-构建产物)
6. [Runner 配置](#6-runner-配置)
7. [关键技术点](#7-关键技术点)
8. [常见问题](#8-常见问题)

---

## 1. 概述

### 为什么选择 GitCode CI/CD？

| 对比项 | GitCode CI/CD | GitHub Actions |
|--------|---------------|----------------|
| **国内访问** | ✅ 快速稳定 | ⚠️ 可能较慢 |
| **免费额度** | ✅ 公开仓库免费 | ✅ 公开仓库免费 |
| **macOS arm64** | ❌ 需自建 Runner | ✅ 内置 M1/M2/M3 |
| **Windows** | ⚠️ 需自建 Runner | ✅ 内置 |
| **法律合规** | ✅ 国内合规 | ✅ 完全合规 |

### 构建平台矩阵

| Runner Tags | 操作系统 | 架构 | 说明 |
|-------------|---------|------|------|
| `docker` | Linux | x64 | Linux Executer + Installer + 单元测试 |
| `windows`, `python` | Windows | x64 | Windows Executer + Installer |
| `macos`, `x64` | macOS | x64 (Intel) | macOS x64 Executer + Installer |

> **注意**：macOS arm64 (M1/M2/M3) 需要在 GitHub Actions 上构建，或自建 GitCode Runner。

### 打包类型

| 类型 | 说明 | 输出格式 |
|------|------|---------|
| **Executer** | 单文件可执行程序，无需安装 | ZIP 包（包含可执行文件） |
| **Installer** | 安装包，需要安装后使用 | Windows: EXE，Linux/macOS: ZIP（含安装脚本） |

---

## 2. 文件结构

```
.gitlab-ci.yml           # GitLab CI 主配置文件

.github/
└── workflows/
    ├── test.yml         # GitHub Actions 测试（备用）
    └── build.yml        # GitHub Actions 构建（备用）

Client/
└── requirements.txt     # Python 依赖列表
```

---

## 3. 构建 Job 说明

### 3.1 测试阶段

| Job | Runner | 说明 |
|-----|--------|------|
| `test:linux` | docker | pytest 单元测试 + mypy 类型检查 |

### 3.2 构建阶段

**Linux (Docker Runner)**：

| Job | 类型 | 依赖脚本 |
|-----|------|---------|
| `build:linux:executer` | Executer | `build_executer.sh` |
| `build:linux:installer` | Installer | `build_installer.sh` |

**Windows (需自建 Runner)**：

| Job | 类型 | 依赖脚本 |
|-----|------|---------|
| `build:windows:executer` | Executer | `build_executer.bat` |
| `build:windows:installer` | Installer | `build_installer.bat` + Inno Setup |

**macOS x64 (需自建 Runner)**：

| Job | 类型 | 依赖脚本 |
|-----|------|---------|
| `build:macos:executer` | Executer | `build_executer.sh` |
| `build:macos:installer` | Installer | `build_installer.sh` |

### 3.3 发布阶段

| Job | 说明 |
|-----|------|
| `release` | 汇总所有构建产物，仅在 tag 时触发 |

---

## 4. 触发方式

### 4.1 日常开发测试

```bash
git push origin main
```

效果：运行单元测试，不构建不发布

### 4.2 正式发布

```bash
# 创建 tag 并推送
git tag v2.2.0
git push origin v2.2.0

# 或一步完成
git tag v2.2.0 && git push origin v2.2.0
```

效果：测试 → 构建 → 测试可执行文件 → 发布 Release Artifacts

---

## 5. 构建产物

### 5.1 Artifacts 下载

构建成功后，在 **CI/CD → Pipelines → 对应运行 → Artifacts** 区域下载：

| Artifact | 类型 | 平台 | 架构 |
|----------|------|------|------|
| `Package/Executer/output/Linux/x64/` | Executer | Linux | x64 |
| `Package/Installer/output/Linux/x64/` | Installer | Linux | x64 |
| `Package/Executer/output/Windows/x64/` | Executer | Windows | x64 |
| `Package/Installer/output/Windows/x64/` | Installer | Windows | x64 |
| `Package/Executer/output/macOS/x64/` | Executer | macOS | x64 |
| `Package/Installer/output/macOS/x64/` | Installer | macOS | x64 |

**保留时间**：
- 普通构建：30 天
- Release（tag 构建）：永久

---

## 6. Runner 配置

### 6.1 Docker Runner (Linux)

GitCode 通常提供共享 Docker Runner，标签为 `docker`。

### 6.2 Windows Runner

需自建 Runner，配置步骤：

1. **安装 GitLab Runner**：
   ```powershell
   # 下载
   Invoke-WebRequest -Uri "https://gitlab-runner-downloads.s3.amazonaws.com/latest/binaries/gitlab-runner-windows-amd64.exe" -OutFile "gitlab-runner.exe"
   
   # 注册
   .\gitlab-runner.exe register
   ```

2. **配置标签**：
   - Tags: `windows, python`
   - Executor: `shell`

3. **安装依赖**：
   ```powershell
   # Python 3.11
   # FFmpeg (添加到 PATH)
   # Inno Setup (choco install innosetup -y)
   ```

### 6.3 macOS Runner

需自建 Runner，配置步骤：

1. **安装 GitLab Runner**：
   ```bash
   # 下载
   sudo curl -L --output /usr/local/bin/gitlab-runner https://gitlab-runner-downloads.s3.amazonaws.com/latest/binaries/gitlab-runner-darwin-amd64
   
   # 授权
   sudo chmod +x /usr/local/bin/gitlab-runner
   
   # 注册
   gitlab-runner register
   ```

2. **配置标签**：
   - Tags: `macos, x64`
   - Executor: `shell`

3. **安装依赖**：
   ```bash
   # Python 3.11
   brew install python@3.11
   
   # FFmpeg
   brew install ffmpeg
   ```

### 6.4 macOS arm64 (M1/M2/M3)

**方案 1：使用 GitHub Actions**

推送 tag 到 GitHub，使用 GitHub Actions 构建 macOS arm64 产物。

**方案 2：自建 GitCode Runner**

需要在 M1/M2/M3 Mac 上配置 GitLab Runner，标签为 `macos, arm64`。

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
```bash
# Linux
sudo apt-get install -y ffmpeg libavcodec-dev libavformat-dev

# macOS
brew install ffmpeg
```

### Q2: Windows/macOS Runner 没有？

**说明**：GitCode 共享 Runner 通常只提供 Linux。需要自建 Windows/macOS Runner。

**解决**：
1. 参考 [6. Runner 配置](#6-runner-配置) 自建 Runner
2. 或使用 GitHub Actions 构建 Windows/macOS 产物

### Q3: 如何获取 macOS arm64 构建？

**方案**：
1. 推送代码到 GitHub，使用 GitHub Actions（推荐）
2. 自建 GitCode Runner on M1/M2/M3 Mac

### Q4: 构建产物在哪里下载？

**方法**：
1. GitCode → CI/CD → Pipelines → 选择成功的运行
2. Artifacts 区域 → 点击下载

### Q5: Release 发布失败？

**检查**：
- 确认 tag 格式为 `v*`（如 `v2.2.0`）
- 确认所有构建 job 成功
- 检查 Runner 是否在线

### Q6: 如何跳过某个平台构建？

**方法**：在 `.gitlab-ci.yml` 中注释或删除对应的 job。

### Q7: GitHub Actions 和 GitCode CI/CD 冲突？

**说明**：两者独立运行，不冲突。

**建议**：
- GitCode CI/CD：Linux 构建（共享 Runner）
- GitHub Actions：Windows/macOS 构建（共享 Runner）
- 最终产物可手动合并

---

## 参考链接

- GitLab CI 文档：https://docs.gitlab.com/ee/ci/
- GitLab Runner 安装：https://docs.gitlab.com/runner/install/
- PyInstaller 文档：https://pyinstaller.org/
- GitHub Actions 文档（备用）：见 `docs/GitHub_Actions_CI_CD配置指南.md`

---

> **文档版本：** v1.0
> **最后更新：** 2026-05-12
> **适用项目：** OpenHarmony_Scrcpy
> **作者：** luodh0157