# OpenHarmony_OHScrcpy Executer打包工具使用说明
**Executer打包工具**通过pyinstaller工具把整个OpenHarmony_OHScrcpy运行时需要的所有部件（python运行时/python依赖库/ohscrcpy_client/ohscrcpy_server）打包到一个没有任何依赖的可执行文件中，便于用户便捷分发和使用。

## 系统要求
- **操作系统**：Windows/Linux/macOS
- **Python版本**：Python 3.7或更高版本
- **依赖库**：打包脚本会自动尝试安装这些依赖库
   - `av`
   - `numpy`
   - `pillow`
   - `psutil`
   - `pyinstaller`

## Executer打包方法

### 1. 准备依赖资源文件

**推荐方式**：使用自动化准备脚本（自动完成所有文件拷贝）
```bash
# Linux/macOS
./prepare_for_executer.sh

# Windows
prepare_for_executer.bat
```

**说明**：自动化脚本会自动拷贝所有必需文件到`Package/Executer`目录，无需手动操作。

**文件清单（供参考）**：
- `Client/main.py` + `Client/core/` + `Client/video/` + `Client/gui/` + `Client/utils/` + `Client/config/`
- `Client/hdc/` 目录（各平台HDC工具）
- `Server/bin/rk3568/ohscrcpy_server`
- `Server/ohscrcpy_server.cfg`
- `Server/bin/harmonyos/ohscrcpy_server` → `HUAWEI/` 子目录
- `scripts/` 目录（日志管理脚本）

### 2. 运行打包脚本
  在`Package/Executer`目录下，运行`make_ohscrcpy_executer`打包脚本，开始自动进行可执行文件打包。
  
  说明：Windows平台使用`make_ohscrcpy_executer.bat`脚本，Linux/macOS平台使用`make_ohscrcpy_executer.sh`。

### 3. 打包输出
  打包脚本执行成功后，会在`output/{平台}/{架构}/`目录下生成：
  - **可执行文件**：`OHScrcpy`
  - **分发zip包**：`OHScrcpy_Exec_{平台}_{架构}_v2.1.zip`（包含可执行文件、日志脚本、hash文件）
  - **Hash文件**：`OHScrcpy_Exec_{平台}_{架构}_hash.txt`

**说明**：自动化脚本会自动拷贝所有必需文件到`Package/Executer`目录，无需手动操作。

### 4. 清理资源文件

**推荐方式**：使用自动化清理脚本（自动完成所有文件清理）
```bash
# Linux/macOS
./clear_for_executer.sh

# Windows
clear_for_executer.bat
```

## 用户使用方法（解压zip包后）

```
解压后的目录/
├── OHScrcpy (可执行文件)
├── fetch_server_logs.sh/bat (日志拉取脚本)
├── delete_server_logs.sh/bat (日志删除脚本)
├── fetch_and_delete_server_logs.sh/bat (二合一日志管理脚本)
└── OHScrcpy_Exec_{平台}_{架构}_hash.txt
```

**使用方式**：
1. 运行OHScrcpy开始投屏
2. 需要拉取服务端日志：运行`fetch_server_logs.sh/bat`
3. 脚本会优先使用内置hdc，其次使用系统PATH中的hdc
