#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import shutil
import subprocess
import platform
from pathlib import Path

# 应用程序信息
APP_NAME = "AiSparkHub"
APP_VERSION = "1.0.0"
APP_PUBLISHER = "AiSparkHub Team"
APP_URL = "https://github.com/your-username/AiSparkHub-Desktop"
APP_EXE_NAME = "AiSparkHub.exe"
APP_ICON = "app/resources/icon.ico" if os.path.exists("app/resources/icon.ico") else ""
APP_ID = "com.aisparkhub.desktop"

# 目录配置
DIST_DIR = "dist"
BUILD_DIR = "build"
OUTPUT_DIR = os.path.join(DIST_DIR, APP_NAME)
INSTALLER_DIR = "installer"

def clean_build_folders():
    """清理构建文件夹"""
    folders_to_clean = [BUILD_DIR, DIST_DIR]
    for folder in folders_to_clean:
        if os.path.exists(folder):
            print(f"清理 {folder} 文件夹...")
            shutil.rmtree(folder)
    
    # 确保安装包输出目录存在
    if not os.path.exists(INSTALLER_DIR):
        os.makedirs(INSTALLER_DIR)

def run_pyinstaller():
    """运行PyInstaller打包应用"""
    print("开始使用PyInstaller打包应用...")
    
    # 图标参数，如果图标文件存在则使用
    icon_param = f"--icon={APP_ICON}" if APP_ICON else ""
    
    # 根据操作系统选择合适的路径分隔符
    path_sep = ";" if platform.system() == "Windows" else ":"
    
    # PyInstaller命令 - 使用python -m PyInstaller替代直接调用
    cmd = [
        "python", "-m", "PyInstaller",
        "--name", APP_NAME,
        "--windowed",  # 使用GUI模式
        "--noconfirm",  # 不询问确认
        "--clean",  # 清理临时文件
        "--log-level", "INFO",
        "--onedir",  # 生成文件夹模式，不是单文件
        icon_param,
        # 添加所需的数据文件
        "--add-data", f"app/resources{path_sep}app/resources",
        "--add-data", f"app/static{path_sep}app/static",
        "--add-data", f"icons{path_sep}icons",
        # 添加所需的隐藏导入模块
        "--hidden-import", "PyQt6.QtCore",
        "--hidden-import", "PyQt6.QtWidgets",
        "--hidden-import", "PyQt6.QtGui",
        "--hidden-import", "PyQt6.QtWebEngineWidgets",
        "--hidden-import", "PyQt6.QtWebEngineCore",
        "--hidden-import", "qtawesome",
        "--hidden-import", "qtpy",
        "--hidden-import", "sqlite3",
        "--collect-all", "qtawesome",
        # 添加主脚本
        "main.py"
    ]
    
    # 过滤掉空字符串
    cmd = [item for item in cmd if item]
    
    print(f"执行命令: {' '.join(cmd)}")
    
    # 运行PyInstaller
    try:
        # 使用subprocess.check_call捕获更多错误信息
        subprocess.check_call(cmd)
        print(f"PyInstaller打包完成，输出目录: {OUTPUT_DIR}")
    except subprocess.CalledProcessError as e:
        print(f"PyInstaller打包失败，错误代码: {e.returncode}")
        print(f"错误信息: {e}")
        return False
    except FileNotFoundError as e:
        print(f"找不到PyInstaller，请确保已安装: {e}")
        print("尝试运行: pip install pyinstaller")
        return False
    
    # 只有在打包成功时继续执行后续步骤
    # 确保数据库目录存在
    db_dir = os.path.join(OUTPUT_DIR, "database")
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
        print(f"创建数据库目录: {db_dir}")
    
    # 复制额外的文件和配置
    try:
        # 复制数据库文件(如果存在)
        if os.path.exists("database"):
            for file in os.listdir("database"):
                if file.endswith(".db"):
                    src = os.path.join("database", file)
                    dst = os.path.join(db_dir, file)
                    shutil.copy2(src, dst)
                    print(f"复制数据库文件: {src} -> {dst}")
        
        # 确保图标目录存在
        icons_dir = os.path.join(OUTPUT_DIR, "icons")
        if not os.path.exists(icons_dir) and os.path.exists("icons"):
            os.makedirs(icons_dir, exist_ok=True)
            # 复制所有图标文件
            for file in os.listdir("icons"):
                if file.endswith((".ico", ".png")):
                    src = os.path.join("icons", file)
                    dst = os.path.join(icons_dir, file)
                    shutil.copy2(src, dst)
                    print(f"复制图标文件: {src} -> {dst}")
        
        # 复制README和LICENSE等文件
        extra_files = ["README.md", "LICENSE"]
        for file in extra_files:
            if os.path.exists(file):
                dst = os.path.join(OUTPUT_DIR, file)
                shutil.copy2(file, dst)
                print(f"复制文件: {file} -> {dst}")
    
    except Exception as e:
        print(f"复制额外文件时出错: {e}")
        
    return True

def create_inno_setup_script():
    """创建Inno Setup脚本"""
    print("创建Inno Setup脚本...")
    
    # 由于Inno Setup将大括号视为常量标记，我们需要对APP_ID进行特殊处理
    # 在Inno Setup脚本中大括号使用双大括号转义
    app_id_escaped = APP_ID.replace("{", "{{").replace("}", "}}")
    
    script_content = f"""
#define MyAppName "{APP_NAME}"
#define MyAppVersion "{APP_VERSION}"
#define MyAppPublisher "{APP_PUBLISHER}"
#define MyAppURL "{APP_URL}"
#define MyAppExeName "{APP_EXE_NAME}"
#define MyAppId "{app_id_escaped}"

[Setup]
; 基本安装程序设置
AppId={{#MyAppId}}
AppName={{#MyAppName}}
AppVersion={{#MyAppVersion}}
AppPublisher={{#MyAppPublisher}}
AppPublisherURL={{#MyAppURL}}
AppSupportURL={{#MyAppURL}}
AppUpdatesURL={{#MyAppURL}}
DefaultDirName={{autopf}}\\{{#MyAppName}}
DefaultGroupName={{#MyAppName}}
AllowNoIcons=yes
; 如果存在，使用图标
SetupIconFile={APP_ICON if APP_ICON else ""}
UninstallDisplayIcon={{app}}\\{{#MyAppExeName}}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
; 需要管理员权限安装
PrivilegesRequiredOverridesAllowed=dialog
OutputDir={INSTALLER_DIR}
OutputBaseFilename={APP_NAME}_Setup_v{APP_VERSION}
; 创建应用程序目录
DisableDirPage=no
DisableProgramGroupPage=no

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面图标"; GroupDescription: "附加图标:"; Flags: unchecked

[Files]
; 导入所有程序文件
Source: "{OUTPUT_DIR}\\*"; DestDir: "{{app}}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{{group}}\\{{#MyAppName}}"; Filename: "{{app}}\\{{#MyAppExeName}}"
Name: "{{group}}\\卸载 {{#MyAppName}}"; Filename: "{{uninstallexe}}"
Name: "{{commondesktop}}\\{{#MyAppName}}"; Filename: "{{app}}\\{{#MyAppExeName}}"; Tasks: desktopicon

[Run]
Filename: "{{app}}\\{{#MyAppExeName}}"; Description: "{{cm:LaunchProgram,{{#StringChange(MyAppName, '&', '&&')}}}}"; Flags: nowait postinstall skipifsilent

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
      DelTree(ExpandConstant('{{localappdata}}\\{APP_NAME}'), True, True, True);
    end;
  end;
end;
    """
    
    # 写入脚本文件
    inno_script_path = "installer_script.iss"
    with open(inno_script_path, "w", encoding="utf-8") as f:
        f.write(script_content)
    
    print(f"Inno Setup脚本已创建: {inno_script_path}")
    return inno_script_path

def compile_installer(script_path):
    """编译Inno Setup安装包"""
    print("使用Inno Setup编译安装包...")
    
    # 检查Inno Setup是否安装
    inno_compiler = ""
    
    # 用户指定的Inno Setup路径
    user_path = r"C:\Program Files (x86)\Inno Setup 6"
    
    # 添加用户指定的路径到查找列表的最前面
    possible_paths = [
        os.path.join(user_path, "ISCC.exe"),
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
        r"C:\Program Files\Inno Setup 5\ISCC.exe"
    ]
    
    # 查找编译器
    for path in possible_paths:
        if os.path.exists(path):
            inno_compiler = path
            print(f"找到Inno Setup编译器: {path}")
            break
    
    if not inno_compiler:
        print("错误: 无法找到Inno Setup编译器。请先安装Inno Setup。")
        print("您可以从此处下载: https://jrsoftware.org/isdl.php")
        print(f"脚本已生成，请手动编译: {script_path}")
        return False
    
    # 编译安装包
    print(f"使用编译器: {inno_compiler}")
    cmd = [inno_compiler, script_path]
    
    try:
        # 使用subprocess.check_call捕获更多错误信息
        result = subprocess.check_call(cmd)
        print(f"安装包已成功编译，保存在 {INSTALLER_DIR} 文件夹中")
        return True
    except subprocess.CalledProcessError as e:
        print(f"编译安装包时出错，错误代码: {e.returncode}")
        print(f"错误信息: {e}")
        return False
    except FileNotFoundError as e:
        print(f"找不到Inno Setup编译器: {e}")
        print("您可以从此处下载: https://jrsoftware.org/isdl.php")
        return False

def main():
    """主函数"""
    # 清理之前的构建
    clean_build_folders()
    
    # 使用PyInstaller打包应用
    if not run_pyinstaller():
        print("打包失败，终止后续操作")
        return
    
    # 创建Inno Setup脚本
    inno_script = create_inno_setup_script()
    
    # 编译安装包
    compile_installer(inno_script)

if __name__ == "__main__":
    main() 