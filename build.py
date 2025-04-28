#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import shutil
import subprocess
import platform
import argparse
from pathlib import Path

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='构建AiSparkHub桌面应用')
    parser.add_argument('app_name', nargs='?', default="AiSparkHub", help='应用名称')
    parser.add_argument('app_version', nargs='?', default="1.0.0", help='应用版本号')
    parser.add_argument('--skip-clean', action='store_true', help='跳过清理构建文件夹')
    parser.add_argument('--skip-installer', action='store_true', help='跳过生成安装包')
    parser.add_argument('--icon', help='自定义图标路径')
    return parser.parse_args()

# 解析命令行参数
args = parse_arguments()

# 应用程序信息
APP_NAME = args.app_name
APP_VERSION = args.app_version
APP_PUBLISHER = "Tengle Deng"
APP_URL = "https://github.com/your-username/AiSparkHub-Desktop"
APP_EXE_NAME = f"{APP_NAME}.exe"

# 图标优先级：命令行参数 > icons\app.ico > app/resources/icon.ico
if args.icon:
    APP_ICON = args.icon
elif os.path.exists("icons/app.ico"):
    APP_ICON = "icons/app.ico"
elif os.path.exists("app/resources/icon.ico"):
    APP_ICON = "app/resources/icon.ico"
else:
    APP_ICON = ""
    
APP_ID = "com.aisparkhub.desktop"

# 目录配置
DIST_DIR = "dist"
BUILD_DIR = "build"
OUTPUT_DIR = os.path.join(DIST_DIR, APP_NAME)
INSTALLER_DIR = "installer"

def clean_build_folders():
    """清理构建文件夹"""
    if args.skip_clean:
        print("跳过清理构建文件夹...")
        return
        
    folders_to_clean = [BUILD_DIR, DIST_DIR]
    for folder in folders_to_clean:
        if os.path.exists(folder):
            print(f"清理 {folder} 文件夹...")
            try:
                shutil.rmtree(folder)
            except PermissionError as e:
                print(f"无法删除 {folder}，可能有文件被占用: {e}")
                print("请关闭所有可能使用这些文件的程序，如编辑器或文件浏览器")
                sys.exit(1)
            except Exception as e:
                print(f"清理 {folder} 时发生错误: {e}")
                sys.exit(1)
    
    # 确保安装包输出目录存在
    if not os.path.exists(INSTALLER_DIR):
        try:
            os.makedirs(INSTALLER_DIR)
        except Exception as e:
            print(f"创建 {INSTALLER_DIR} 目录失败: {e}")
            sys.exit(1)

def check_environment():
    """检查构建环境"""
    print("检查构建环境...")
    
    # 检查必要的模块
    required_modules = ["PyQt6", "qtawesome", "PyInstaller", "pynput"]
    missing_modules = []
    
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)
    
    if missing_modules:
        print(f"错误: 缺少以下必要模块: {', '.join(missing_modules)}")
        print(f"请使用以下命令安装: pip install {' '.join(missing_modules)}")
        sys.exit(1)
    
    # 检查pathlib冲突
    try:
        try:
            # 如果能导入pathlib中的abc，说明是标准库的pathlib
            from pathlib import abc
        except ImportError:
            import pathlib
            if not hasattr(pathlib, "__file__") or "site-packages" in pathlib.__file__:
                print("警告: 检测到可能与PyInstaller不兼容的pathlib包")
                print("如果打包失败，请尝试: conda remove pathlib")
    except ImportError:
        # 没有安装pathlib包，没有潜在冲突
        pass
    
    print("环境检查完成")

def run_pyinstaller():
    """运行PyInstaller打包应用"""
    print("开始使用PyInstaller打包应用...")
    
    # 图标参数，如果图标文件存在则使用
    if APP_ICON and os.path.exists(APP_ICON):
        icon_param = f"--icon={APP_ICON}"
        print(f"使用图标: {APP_ICON}")
        
        # 验证图标文件
        try:
            from PIL import Image
            with Image.open(APP_ICON) as img:
                print(f"图标尺寸信息: {img.info}")
                if hasattr(img, 'n_frames'):
                    print(f"图标包含 {img.n_frames} 个尺寸变体")
        except ImportError:
            print("警告: 未安装Pillow库，无法验证图标文件")
        except Exception as e:
            print(f"警告: 验证图标文件时出错: {e}")
    else:
        icon_param = ""
        print("警告: 未找到有效的图标文件")
    
    # 版本文件参数
    version_file_param = []
    if os.path.exists("version.txt"):
        version_file_param = ["--version-file", "version.txt"]
        print(f"使用版本信息文件: version.txt")
    else:
        print("警告: 未找到版本信息文件 version.txt")
    
    # 根据操作系统选择合适的路径分隔符
    path_sep = ";" if platform.system() == "Windows" else ":"
    
    # PyInstaller命令
    cmd = [
        "python", "-m", "PyInstaller",
        "--name", APP_NAME,
        "--windowed",  # 使用GUI模式
        "--noconfirm",  # 不询问确认
        "--clean",  # 清理临时文件
        "--log-level", "INFO",
        "--onedir",  # 生成文件夹模式，不是单文件
        # 使用uac-admin确保管理员权限，这可能有助于保持资源完整性
        "--uac-admin",
    ]
    
    # 添加版本文件参数（如果存在）
    if version_file_param:
        cmd.extend(version_file_param)
    
    # 添加图标参数（如果存在）
    if icon_param:
        cmd.append(icon_param)
    
    # 继续添加其他参数
    cmd.extend([
        # 添加所需的数据文件
        "--add-data", f"app/resources{path_sep}app/resources",
        "--add-data", f"app/static{path_sep}app/static",
        "--add-data", f"app/search{path_sep}app/search",
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
        "--hidden-import", "pynput",
        "--hidden-import", "pynput.keyboard",
        "--hidden-import", "pynput.keyboard._win32",
        "--hidden-import", "pynput.mouse",
        "--hidden-import", "pynput.mouse._win32",
        "--collect-all", "qtawesome",
        "--collect-all", "pynput",
        # 添加主脚本
        "main.py"
    ])
    
    # 过滤掉None值和空字符串
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
        try:
            os.makedirs(db_dir)
            print(f"创建数据库目录: {db_dir}")
        except Exception as e:
            print(f"创建数据库目录失败: {e}")
            return False
    
    # 复制额外的文件和配置
    try:
        # 创建目标data目录
        data_dir = os.path.join(OUTPUT_DIR, "data")
        if not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok=True)
            print(f"创建data目录: {data_dir}")
        
        # 创建数据库目录
        db_dir = os.path.join(data_dir, "database")
        if not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            print(f"创建数据库目录: {db_dir}")
        
        # 复制数据库文件(如果存在)
        if os.path.exists("database"):
            for file in os.listdir("database"):
                if file.endswith(".db"):
                    src = os.path.join("database", file)
                    dst = os.path.join(db_dir, file)
                    shutil.copy2(src, dst)
                    print(f"复制数据库文件: {src} -> {dst}")
        
        # 确保搜索目录存在
        search_dir = os.path.join(OUTPUT_DIR, "_internal", "app", "search")
        if not os.path.exists(search_dir):
            os.makedirs(search_dir, exist_ok=True)
            print(f"创建搜索目录: {search_dir}")
            
        # 复制搜索相关文件
        src_search_dir = "app/search"
        if os.path.exists(src_search_dir):
            for file in os.listdir(src_search_dir):
                src = os.path.join(src_search_dir, file)
                dst = os.path.join(search_dir, file)
                if os.path.isfile(src):
                    shutil.copy2(src, dst)
                    print(f"复制搜索文件: {src} -> {dst}")
        
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
    
    # 确定安装程序图标路径
    if APP_ICON and os.path.exists(APP_ICON):
        setup_icon = APP_ICON.replace("\\", "/")  # 确保使用正斜杠
        print(f"使用安装程序图标: {setup_icon}")
    else:
        setup_icon = ""
        print("注意: 未指定安装程序图标")
    
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
; 设置图标
SetupIconFile={setup_icon}
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
; 确保图标文件被复制
Source: "{APP_ICON}"; DestDir: "{{app}}\\icons"; Flags: ignoreversion

[Icons]
Name: "{{group}}\\{{#MyAppName}}"; Filename: "{{app}}\\{{#MyAppExeName}}"; IconFilename: "{{app}}\\icons\\app.ico"
Name: "{{group}}\\卸载 {{#MyAppName}}"; Filename: "{{uninstallexe}}"
Name: "{{commondesktop}}\\{{#MyAppName}}"; Filename: "{{app}}\\{{#MyAppExeName}}"; IconFilename: "{{app}}\\icons\\app.ico"; Tasks: desktopicon

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
    try:
        with open(inno_script_path, "w", encoding="utf-8") as f:
            f.write(script_content)
        print(f"Inno Setup脚本已创建: {inno_script_path}")
        return inno_script_path
    except Exception as e:
        print(f"创建Inno Setup脚本失败: {e}")
        return None

def compile_installer(script_path=None):
    """编译Inno Setup安装包"""
    if args.skip_installer:
        print("跳过生成安装包...")
        return True
    
    # 直接使用现有的installer_script.iss文件
    script_path = "installer_script.iss"
    if not os.path.exists(script_path):
        print("错误: 无法找到Inno Setup脚本文件")
        return False
        
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
        subprocess.check_call(cmd)
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
    print(f"开始构建 {APP_NAME} v{APP_VERSION}")
    
    # 检查环境
    check_environment()
    
    # 清理之前的构建
    clean_build_folders()
    
    # 使用PyInstaller打包应用
    if not run_pyinstaller():
        print("打包失败，终止后续操作")
        sys.exit(1)
    
    # 编译安装包
    if not compile_installer() and not args.skip_installer:
        print("安装包生成失败")
        sys.exit(1)
        
    print(f"{APP_NAME} v{APP_VERSION} 构建完成!")
    print(f"可执行文件位于: {OUTPUT_DIR}")
    if not args.skip_installer:
        print(f"安装包位于: {INSTALLER_DIR}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n构建过程被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"构建过程中发生未预期的错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 