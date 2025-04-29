
#define MyAppName "AiSparkHub"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Tengle Deng"
#define MyAppURL "https://github.com/your-username/AiSparkHub-Desktop"
#define MyAppExeName "AiSparkHub.exe"
#define MyAppId "com.aisparkhub.desktop"

[Setup]
; 基本安装程序设置
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
; 设置图标
SetupIconFile=icons/app.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
; 需要管理员权限安装
PrivilegesRequired=admin
OutputDir=installer
OutputBaseFilename=AiSparkHub_Setup_v1.0.0
; 创建应用程序目录
DisableDirPage=no
DisableProgramGroupPage=no

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面图标"; GroupDescription: "附加图标:"; Flags: unchecked

[Files]
; 导入所有程序文件
Source: "dist\AiSparkHub\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; 确保图标文件被复制
Source: "icons/app.ico"; DestDir: "{app}\icons"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icons\app.ico"
Name: "{group}\卸载 {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icons\app.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent runasoriginaluser shellexec

[Code]
// 自定义卸载程序
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  mRes : Integer;
begin
  // 卸载完成后询问是否删除数据文件
  if CurUninstallStep = usPostUninstall then
  begin
    mRes := MsgBox('是否删除用户数据？这将删除您的所有设置和历史记录。', mbConfirmation, MB_YESNO or MB_DEFBUTTON2)
    if mRes = IDYES then
    begin
      DelTree(ExpandConstant('{localappdata}\AiSparkHub'), True, True, True);
    end;
  end;
end;
    