# GitCode CI/CD 配置指南

> 本文档说明 GitCode 流水线配置方案，用于 OpenHarmony Scrcpy 自动化构建。
> GitCode 流水线采用类似 GitHub Actions 的 YAML 格式。

---

## 目录

1. [概述](#1-概述)
2. [文件结构](#2-文件结构)
3. [构建 Job 说明](#3-构建-job-说明)
4. [触发方式](#4-触发方式)
5. [构建产物](#5-构建产物)
6. [关键技术点](#6-关键技术点)
7. [常见问题](#7-常见问题)

---

## 1. 概述

### GitCode 流水线特点

| 对比项 | GitCode 流水线 | GitHub Actions |
|--------|---------------|----------------|
| **国内访问** | ✅ 快速稳定 | ⚠️ 可能较慢 |
| **配置格式** | 类似 GitHub Actions | GitHub Actions |
| **文件位置** | `.gitcode/workflows/` | `.github/workflows/` |
| **默认 Runner** | EulerOS (Linux) | Windows/Linux/macOS |
| **macOS arm64** | ❌ 不支持 | ✅ 内置 M1/M2/M3 |
| **Windows** | ❌ 不支持 | ✅ 内置 |

### Runner 类型

| Runner | 操作系统 | 架构 | 说明 |
|--------|---------|------|------|
| `euleros-2.10.1` | EulerOS 2.10.1 | x64 | GitCode 默认提供的 Linux Runner |

> **重要**：GitCode 目前只提供 EulerOS (Linux) 共享 Runner。Windows 和 macOS 构建需使用 GitHub Actions。

### 打包类型

| 类型 | 说明 | 输出格式 |
|------|------|---------|
| **Executer** | 单文件可执行程序，无需安装 | ZIP 包（包含可执行文件） |
| **Installer** | 安装包，需要安装后使用 | ZIP（含安装脚本） |

---

## 2. 文件结构

```
.gitcode/
└── workflows/
    ├── test.yml           # 单元测试流水线
    └── build.yml          # Linux 构建流水线

.github/
└── workflows/
    ├── test.yml           # GitHub Actions 测试（备用）
    └── build.yml          # GitHub Actions 全平台构建（Windows/macOS）

Client/
└── requirements.txt       # Python 依赖列表
```

---

## 3. 构建 Job 说明

### 3.1 test.yml - 单元测试

```yaml
name: Test OHScrcpy

on:
  push:
    branches: [ "main", "master" ]
  pull_request:
    branches: [ "main", "master" ]

jobs:
  test:
    runs-on: euleros-2.10.1
    steps:
      - uses: checkout-action@0.0.1
      
      - name: Setup Python
        uses: setup-python@0.0.1
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          cd repo_workspace
          pip install --upgrade pip
          pip install -r Client/requirements.txt
          pip install pytest mypy
      
      - name: Run tests
        run: |
          cd repo_workspace
          pytest tests/ -v
```

### 3.2 build.yml - Linux 构建

| Job | 类型 | 说明 |
|-----|------|------|
| `build-executer` | Executer | Linux x64 单文件可执行程序 |
| `build-installer` | Installer | Linux x64 安装包 |

---

## 4. 触发方式

### 4.1 日常开发测试

```bash
git push origin main
```

效果：运行单元测试

### 4.2 构建测试

```bash
git push origin main
```

效果：运行单元测试 + Linux 构建

### 4.3 正式发布

```bash
git tag v2.2.0
git push origin v2.2.0
```

效果：
- GitCode：Linux 构建
- GitHub（如果推送）：Windows/macOS 全平台构建

---

## 5. 构建产物

### 5.1 GitCode Artifacts

构建成功后，在 **流水线 → 对应运行 → Artifacts** 区域下载：

| Artifact | 类型 | 平台 |
|----------|------|------|
| `OHScrcpy-Executer-Linux-x64` | Executer | Linux x64 |
| `OHScrcpy-Installer-Linux-x64` | Installer | Linux x64 |

**保留时间**：30 天

### 5.2 GitHub Artifacts（全平台）

如果同时使用 GitHub Actions，可获得：

| Artifact | 类型 | 平台 |
|----------|------|------|
| `OHScrcpy-Executer-Windows-x64` | Executer | Windows x64 |
| `OHScrcpy-Installer-Windows-x64` | Installer | Windows x64 |
| `OHScrcpy-Executer-macOS-arm64` | Executer | macOS arm64 |
| `OHScrcpy-Installer-macOS-arm64` | Installer | macOS arm64 |
| `OHScrcpy-Executer-macOS-x64` | Executer | macOS x64 |
| `OHScrcpy-Installer-macOS-x64` | Installer | macOS x64 |

---

## 6. 关键技术点

### 6.1 工作目录

GitCode 流水线中，项目代码位于 `repo_workspace/` 目录：

```yaml
run: |
  cd repo_workspace
  pip install -r Client/requirements.txt
```

### 6.2 内置 Actions

GitCode 提供以下内置 Actions：

| Action | 版本 | 说明 |
|--------|------|------|
| `checkout-action` | `0.0.1` | 拉取代码 |
| `setup-python` | `0.0.1` | 配置 Python 环境 |
| `setup-node` | `0.0.1` | 配置 Node.js 环境 |
| `setup-java` | `0.0.1` | 配置 Java 环境 |
| `setup-go` | `0.0.1` | 配置 Go 环境 |
| `upload-artifact` | `0.0.1` | 上传构建产物 |

### 6.3 EulerOS 包管理

EulerOS 使用 `yum` 安装系统依赖：

```yaml
run: |
  yum install -y ffmpeg ffmpeg-devel
```

### 6.4 清华镜像源加速

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 6.5 一键脚本调用

使用 `Package/build_executer.sh` 和 `Package/build_installer.sh`：

```yaml
run: |
  cd repo_workspace/Package
  chmod +x build_executer.sh
  ./build_executer.sh
```

---

## 7. 常见问题

### Q1: GitCode 支持 Windows/macOS 吗？

**不支持**。GitCode 目前只提供 EulerOS (Linux) 共享 Runner。

**解决方案**：使用 GitHub Actions 构建 Windows/macOS 产物。

### Q2: 如何获取全平台构建？

**方案**：
1. 推送代码到 GitCode → Linux 构建
2. 同时推送代码到 GitHub → Windows/macOS 构建
3. 手动合并两个平台的产物

### Q3: PyAV 安装失败？

**原因**：EulerOS 缺少 FFmpeg

**解决**：
```yaml
run: |
  yum install -y ffmpeg ffmpeg-devel
```

### Q4: `repo_workspace` 是什么？

**说明**：GitCode 流水线将项目代码 checkout 到 `repo_workspace/` 目录，所有操作需要先 `cd repo_workspace`。

### Q5: 构建产物在哪里下载？

**方法**：
1. GitCode → 流水线 → 选择成功的运行
2. Artifacts 区域 → 点击下载

### Q6: 如何跳过构建？

**方法**：修改 `.gitcode/workflows/build.yml` 的触发条件，或暂时删除该文件。

---

## 参考链接

- GitCode 流水线文档：https://docs.gitcode.com/docs/help/home/org_project/pipeline/pipeline-intro1
- GitHub Actions 文档：见 `docs/GitHub_Actions_CI_CD配置指南.md`

---

> **文档版本：** v2.0
> **最后更新：** 2026-05-12
> **适用项目：** OpenHarmony_Scrcpy
> **作者：** luodh0157