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
  将`Client/ohscrcpy_client.py`、`Server/bin/rk3568/ohscrcpy_server`、`Server/ohscrcpy_server.cfg`三个文件拷贝到`Package/Executer`目录下，将`Server/bin/harmonyos/ohscrcpy_server`拷贝到`Package/Executer/HUAWEI`目录下。

### 2. 运行打包脚本
  在`Package/Executer`目录下，运行`make_ohscrcpy_executer`打包脚本，开始自动进行可执行文件打包。
  
  说明：Windows平台使用`make_ohscrcpy_executer.bat`脚本，Linux/macOS平台使用`make_ohscrcpy_executer.sh`。

### 3. 打包输出路径
  `make_ohscrcpy_executer`打包脚本执行成功后，可执行文件`OHScrcpy`及其对应的hash文件`OHScrcpy_hash.txt`会保存在`output`目录下对应的平台目录中。