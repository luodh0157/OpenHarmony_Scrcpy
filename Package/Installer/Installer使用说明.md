# OpenHarmony_OHScrcpy Installer打包工具使用说明
**Installer打包工具**通过pyinstaller工具把整个OpenHarmony_OHScrcpy运行时需要的所有部件（python运行时/python依赖库/ohscrcpy_client/ohscrcpy_server）打包到一个没有任何依赖的可执行文件和依赖目录，并将可执行文件和依赖目录打包成各平台的安装包，便于用户便捷分发和使用。

## 安装程序制作原理
- **Windows平台**：使用Inno Steup制作安装程序
- **Linux/macOS平台**：使用直接打包ZIP压缩包+安装脚本的方式制作安装程序

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
  将`Client/ohscrcpy_client.py`、`Server/bin/rk3568/ohscrcpy_server`、`Server/ohscrcpy_server.cfg`三个文件拷贝到`Package/Installer`目录下，将`Server/bin/harmonyos/ohscrcpy_server`拷贝到`Package/Installer/HUAWEI`目录下。

### 2. 运行打包脚本
  在`Package/Installer`目录下，运行`make_ohscrcpy_executer_onedir`打包脚本，开始自动进行可执行文件打包。
  
  说明：Windows平台使用`make_ohscrcpy_executer_onedir.bat`脚本，Linux/macOS平台使用`make_ohscrcpy_executer_onedir.sh`。

### 3. 运行安装包制作脚本
  `make_ohscrcpy_executer_onedir`打包脚本执行成功后，运行`make_ohscrcpy_installer`脚本，开始自动进行安装包制作。
  
  **注意**：
  
  (1) Windows平台使用**Inno Setup免签名**方式制作安装包，制做安装包和安装过程中会被杀毒软件误认为是病毒而拦截，请执行该脚本前暂时**关闭杀毒软件**。
  
  (2) Windows平台脚本执行过程中会自动拉起Inno Setup安装包制作工具的GUI操作界面，需要**用户点击**`开始`按钮，开始自动制作；另外，制作完成后会自动拉起试安装GUI界面，用于调试安装向导，按照指引一步步完成操作即可。
  
  ![InnoSetup工具界面操作.png](InnoSetup工具界面操作.png 'InnoSetup工具界面操作.png')
  
  ![OHScrcpy安装向导.png](OHScrcpy安装向导.png 'OHScrcpy安装向导.png')

### 4. 打包输出路径
  `make_ohscrcpy_installer`打包脚本执行成功后，安装包文件`OHScrcpy_Setup_[{平台名}]_{版本号}`及其对应的hash文件`OHScrcpy_setup_[{平台名}]_hash.txt`会保存在`output`目录下对应的平台目录中。
