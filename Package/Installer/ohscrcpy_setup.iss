; ======================================================
;   OpenHarmony OHScrcpy 安装程序配置（无代码签名版本）
; ======================================================

; --- 基本设置 ---
[Setup]
; 应用程序信息
AppName=OpenHarmony OHScrcpy
AppVersion=1.6.0
AppVerName=OHScrcpy v1.6.0
AppPublisher=OHScrcpy开源项目组
AppPublisherURL=https://gitcode.com/luodh0157/OpenHarmony_Scrcpy
AppSupportURL=https://gitcode.com/luodh0157/OpenHarmony_Scrcpy/issues
AppUpdatesURL=https://gitcode.com/luodh0157/OpenHarmony_Scrcpy/releases
AppCopyright=版权所有 © 2026 luodh0157
AppContact=https://gitcode.com/luodh0157/OpenHarmony_Scrcpy/issues

; 安装目录设置
DefaultDirName={autopf}\OpenHarmony OHScrcpy
DefaultGroupName=OpenHarmony OHScrcpy
AllowNoIcons=yes
DisableDirPage=no
DisableProgramGroupPage=no
DisableWelcomePage=no
DisableReadyPage=no
DisableFinishedPage=no
AlwaysShowDirOnReadyPage=yes
AlwaysShowGroupOnReadyPage=yes

; 输出设置
outputDir=.\output\Windows\
outputBaseFilename=OHScrcpy_Setup_v1.6.0
SetupIconFile=.\resources\app.ico
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes
LZMADictionarySize=65536

; 安装程序外观
WizardStyle=modern
WizardImageFile=.\resources\ohcrcpy_wizard.bmp
WizardSmallImageFile=.\resources\ohcrcpy_wizard.bmp
WizardImageStretch=no

; 权限设置
; 如果不需要管理员权限，使用下面这行：
PrivilegesRequired=lowest

; 版本信息
VersionInfoVersion=1.6.0.0
VersionInfoCompany=OHScrcpy开源项目组
VersionInfoDescription=OpenHarmony屏幕镜像工具
VersionInfoCopyright=基于GPLv3协议开源
VersionInfoProductName=OpenHarmony OHScrcpy
VersionInfoProductVersion=1.6.0.0
VersionInfoProductTextVersion=v1.6.0

; 安装模式
UninstallDisplayIcon={app}\OHScrcpy.exe
CreateUninstallRegKey=yes
Uninstallable=yes

; 其他设置
ChangesAssociations=no
UsePreviousAppDir=yes
UsePreviousGroup=yes
UsePreviousSetupType=yes
UsePreviousTasks=yes
UsePreviousLanguage=yes

; --- 语言设置 ---
[Languages]
; 简体中文
Name: "chinesesimp"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

; --- 自定义消息（可选） ---
[Messages]
chinesesimp.BeveledLabel=OpenHarmony OHScrcpy - OpenHarmony屏幕镜像工具

chinesesimp.SetupWindowTitle=OpenHarmony OHScrcpy 安装程序

chinesesimp.WelcomeLabel1=欢迎使用 OpenHarmony OHScrcpy 安装向导

chinesesimp.WelcomeLabel2=此程序将安装 OpenHarmony OHScrcpy 到您的计算机。%n%n请注意：由于这是开源免费软件，未购买代码签名证书，Windows可能会显示安全警告。这是正常现象。

; --- 任务设置 ---
[Tasks]
; 创建桌面快捷方式
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce
; 创建快速启动栏快捷方式（Windows 7及以下）
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1
; 创建开始菜单文件夹
Name: "startmenufolder"; Description: "在开始菜单创建快捷方式"; GroupDescription: "快捷方式设置"; Flags: checkedonce
; 添加到PATH环境变量（可选）
Name: "addtopath"; Description: "添加到PATH环境变量"; GroupDescription: "系统设置"; Flags: unchecked
; 创建卸载程序快捷方式
Name: "uninstallicon"; Description: "创建卸载程序快捷方式"; GroupDescription: "快捷方式设置"; Flags: checkedonce

; --- 文件配置 ---
[Files]
; 主程序文件及其他依赖文件
Source: ".\dist\OHScrcpy\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "*.py,*.pyc,*.pyo"
; 许可证文件
Source: ".\docs\LICENSE.txt"; DestDir: "{app}"; Flags: ignoreversion
; 说明文档
Source: ".\docs\README.md"; DestDir: "{app}"; Flags: ignoreversion isreadme
Source: ".\docs\CHANGELOG.txt"; DestDir: "{app}"; Flags: ignoreversion

; --- 目录配置 ---
[Dirs]
; 创建数据目录
Name: "{app}\logs"; Flags: uninsalwaysuninstall

; --- 图标配置 ---
[Icons]
; 开始菜单图标
Name: "{group}\OpenHarmony OHScrcpy"; Filename: "{app}\OHScrcpy.exe"; Tasks: startmenufolder
Name: "{group}\卸载OpenHarmony OHScrcpy"; Filename: "{uninstallexe}"; Tasks: uninstallicon

; 桌面图标
Name: "{autodesktop}\OpenHarmony OHScrcpy"; Filename: "{app}\OHScrcpy.exe"; Tasks: desktopicon

; 快速启动栏图标（Windows 7及以下）
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\OpenHarmony OHScrcpy"; Filename: "{app}\OHScrcpy.exe"; Tasks: quicklaunchicon
    
; --- 注册表配置 ---
[Registry]
; 添加到PATH环境变量
Root: HKLM; Subkey: "SYSTEM\CurrentControlSet\Control\Session Manager\Environment"; ValueType: expandsz; ValueName: "Path"; ValueData: "{olddata};{app}"; Check: NeedsAddPath('{app}'); Tasks: addtopath

; --- 运行配置 ---
[Run]
; 安装完成后运行程序
Filename: "{app}\OHScrcpy.exe"; Description: "{cm:LaunchProgram,OpenHarmony OHScrcpy}"; Flags: nowait postinstall skipifsilent unchecked
; 安装完成后打开用户手册
Filename: "{app}\README.md"; Description: "打开用户手册"; Flags: postinstall shellexec skipifsilent unchecked
; 安装完成后打开许可证
Filename: "{app}\LICENSE.txt"; Description: "查看软件许可证"; Flags: postinstall shellexec skipifsilent unchecked

; --- 卸载配置 ---
[UninstallDelete]
Type: filesandordirs; Name: "{app}\logs"
Type: files; Name: "{app}\*.log"

; ============================================
; 自定义代码段 - 处理无代码签名的安全警告
; ============================================
[Code]
// 定义全局变量
var
  SecurityWarningPage: TWizardPage;
  SecurityAccepted: Boolean;

// 检查是否需要添加到PATH
function NeedsAddPath(Param: string): boolean;
var
  OrigPath: string;
begin
  if not RegQueryStringValue(HKEY_LOCAL_MACHINE,
    'SYSTEM\CurrentControlSet\Control\Session Manager\Environment',
    'Path', OrigPath)
  then begin
    Result := True;
    exit;
  end;
  
  Result := Pos(';' + Uppercase(Param) + ';', ';' + Uppercase(OrigPath) + ';') = 0;
end;


// 复选框点击事件
procedure SecurityCheckBoxClick(Sender: TObject);
begin
  SecurityAccepted := TNewCheckBox(Sender).Checked;
  WizardForm.NextButton.Enabled := SecurityAccepted;
end;

// 创建安全警告页面
procedure CreateSecurityWarningPage;
var
  TitleLabel: TLabel;
  InfoLabel: TLabel;
  Memo: TNewMemo;
  CheckBox: TNewCheckBox;
  LinkLabel: TLabel;
begin
  SecurityWarningPage := CreateCustomPage(wpWelcome, '安全警告说明', 
    '由于这是开源软件，未进行代码签名，安装时可能会遇到安全警告');
  
  // 标题
  TitleLabel := TLabel.Create(SecurityWarningPage);
  TitleLabel.Parent := SecurityWarningPage.Surface;
  TitleLabel.Caption := '⚠️ 重要安全说明 ⚠️';
  TitleLabel.Font.Style := [fsBold];
  TitleLabel.Font.Size := 12;
  TitleLabel.Top := 0;
  TitleLabel.AutoSize := True;
  
  // 主要说明
  InfoLabel := TLabel.Create(SecurityWarningPage);
  InfoLabel.Parent := SecurityWarningPage.Surface;
  InfoLabel.Caption := 
    'OpenHarmony OHScrcpy 是一个开源免费的OpenHarmony系统屏幕镜像工具。由于未购买昂贵的代码签名证书，' +
    'Windows可能会显示安全警告。' + #13#10#13#10 +
    '这不是病毒或恶意软件！这是开源软件的常见现象。' + #13#10#13#10 +
    '请仔细阅读以下说明以确保安全安装：';
  InfoLabel.WordWrap := True;
  InfoLabel.AutoSize := True;
  InfoLabel.Top := TitleLabel.Top + TitleLabel.Height + 6;
  InfoLabel.Width := SecurityWarningPage.SurfaceWidth;
  
  // 详细信息文本框
  Memo := TNewMemo.Create(SecurityWarningPage);
  Memo.Parent := SecurityWarningPage.Surface;
  Memo.Left := 0;
  Memo.Top := InfoLabel.Top + InfoLabel.Height + 6;
  Memo.Width := SecurityWarningPage.SurfaceWidth;
  Memo.Height := 150;
  Memo.ScrollBars := ssVertical;
  Memo.ReadOnly := True;
  Memo.Text := 
    '为什么会出现安全警告？' + #13#10 +
    '--------------------------------------------------------------------------------' + #13#10 +
    '1. 代码签名证书价格昂贵' + #13#10 +
    '2. OpenHarmony OHScrcpy是开源免费软件，无资金购买证书' + #13#10 +
    '3. Windows要求所有软件必须有数字签名' + #13#10#13#10 +
    '遇到安全警告怎么办？' + #13#10 +
    '--------------------------------------------------------------------------------' + #13#10 +
    '情况1: "Windows 已保护你的电脑"' + #13#10 +
    '       点击 → [更多信息] → [仍要运行]' + #13#10#13#10 +
    '情况2: "发布者: 未知"' + #13#10 +
    '       点击 → [是] 或 [运行]' + #13#10#13#10 +
    '如何验证软件安全性？' + #13#10 +
    '--------------------------------------------------------------------------------' + #13#10 +
    '✓ 验证文件哈希值（见安装目录下的hash.txt）' + #13#10 +
    '✓ 查看开源代码: https://gitcode.com/luodh0157/OpenHarmony_Scrcpy' + #13#10 +
    '官方下载渠道：' + #13#10 +
    '--------------------------------------------------------------------------------' + #13#10 +
    'GitCode Releases: https://gitcode.com/luodh0157/OpenHarmony_Scrcpy/releases';
  
  // 确认复选框
  CheckBox := TNewCheckBox.Create(SecurityWarningPage);
  CheckBox.Parent := SecurityWarningPage.Surface;
  CheckBox.Top := Memo.Top + Memo.Height + 16;
  CheckBox.Width := SecurityWarningPage.SurfaceWidth;
  CheckBox.Caption := '我已阅读并理解上述说明，知道如何解决安全警告，并自愿继续安装。';
  CheckBox.Checked := False;
  CheckBox.OnClick := @SecurityCheckBoxClick;
end;

// 初始化安装向导
procedure InitializeWizard;
begin
  // 创建安全警告页面
  CreateSecurityWarningPage;
  
  // 自定义欢迎页面文本
  WizardForm.WelcomeLabel2.Caption := 
    '此程序将安装OpenHarmony OHScrcpy v1.6.0 到您的计算机。' + #13#10#13#10 +
    'OpenHarmony OHScrcpy 是一个开源的OpenHarmony系统屏幕镜像工具' + #13#10#13#10 +
    '安装前请注意：' + #13#10 +
    '• 确保OpenHarmony设备已启用USB调试' + #13#10 +
    '• 关闭其他屏幕镜像软件' + #13#10 +
    '• 由于是开源软件，未进行代码签名' + #13#10 +
    '• 系统可能会显示安全警告（正常现象）';
  
  // 自定义完成页面
  WizardForm.FinishedLabel.Caption :=
    'OpenHarmony OHScrcpy 已成功安装到您的计算机。' + #13#10#13#10 +
    '您可以：' + #13#10 +
    '• 双击桌面快捷方式启动程序' + #13#10 +
    '• 通过开始菜单找到OpenHarmony OHScrcpy' + #13#10 +
    '• 查看安装目录下的文档了解更多信息' + #13#10#13#10 +
    '首次使用前，请确保：' + #13#10 +
    '1. OpenHarmony设备开启USB调试' + #13#10 +
    '2. 使用USB数据线连接设备' + #13#10 +
    '3. 在设备上允许USB调试' + #13#10#13#10 +
    '遇到问题？请查看 docs 文件夹中的文档。';
end;

// 下一步按钮点击事件
function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  
  // 在安全警告页面检查是否已确认
  if CurPageID = SecurityWarningPage.ID then
  begin
    Result := SecurityAccepted;
    if not Result then
      MsgBox('请阅读安全警告并勾选确认框以继续安装。', mbError, MB_OK);
  end;
end;

// 安装步骤变更事件
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // 安装完成后生成哈希文件
  end;
end;

// 卸载步骤变更事件
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ResultCode: Integer;
begin
  if CurUninstallStep = usUninstall then
  begin
    // 卸载前停止运行的程序
      Exec('taskkill', '/f /im OHScrcpy.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
      Exec('taskkill', '/f /im ohscrcpy_server', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end;
end;

// 准备卸载页面
procedure InitializeUninstallProgressForm();
begin
  // 自定义卸载页面
  UninstallProgressForm.PageDescriptionLabel.Caption := 
    '正在卸载 OpenHarmony OHScrcpy...' + #13#10 +
    '这将移除程序文件、快捷方式和注册表项。';
end;