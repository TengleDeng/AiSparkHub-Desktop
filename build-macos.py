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
    parser.add_argument('--icon', help='自定义图标路径')
    return parser.parse_args()

# 解析命令行参数
args = parse_arguments()

# 应用程序信息
APP_NAME = args.app_name
APP_VERSION = args.app_version
APP_PUBLISHER = "Tengle.deng@gmail.com"
APP_URL = "https://github.com/TengleDeng/AiSparkHub/"
APP_EXE_NAME = f"{APP_NAME}.exe"

# 图标优先级：命令行参数 > icons/app.icns
if args.icon:
    APP_ICON = args.icon
elif os.path.exists("icons/app.icns"):
    APP_ICON = "icons/app.icns"
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
    
    # 创建 Info.plist 模板添加环境变量设置
    info_plist_template = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\" \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\">
<plist version=\"1.0\">
<dict>
    <key>CFBundleDisplayName</key>
    <string>{app_name}</string>
    <key>CFBundleExecutable</key>
    <string>{app_name}</string>
    <key>CFBundleIconFile</key>
    <string>app.icns</string>
    <key>CFBundleIdentifier</key>
    <string>{app_id}</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>{app_name}</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>{app_version}</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>LSEnvironment</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
        <key>PYTHONHOME</key>
        <string>.</string>
        <key>QT_QPA_PLATFORM</key>
        <string>cocoa</string>
    </dict>
</dict>
</plist>
"""

    # 生成 Info.plist 文件
    info_plist_content = info_plist_template.format(
        app_name=APP_NAME,
        app_version=APP_VERSION,
        app_id=APP_ID
    )

    info_plist_path = "Info.plist"
    with open(info_plist_path, "w") as f:
        f.write(info_plist_content)
    print(f"已创建 Info.plist 模板，添加了环境变量设置")

    # 图标参数，只用.icns
    icon_param = f"--icon={APP_ICON}" if APP_ICON else ""
    
    # 版本文件参数
    version_file_param = []
    if os.path.exists("version.txt"):
        version_file_param = ["--version-file", "version.txt"]
        print(f"使用版本信息文件: version.txt")
    else:
        print("警告: 未找到版本信息文件 version.txt")
    
    # macOS下路径分隔符
    path_sep = ":"
    
    # PyInstaller命令（不加--onedir，生成.app包）
    cmd = [
        "python", "-m", "PyInstaller",
        "--name", APP_NAME,
        "--windowed",
        "--noconfirm",
        "--clean",
        "--log-level", "INFO",
        "--osx-bundle-identifier", "com.aisparkhub.desktop",
    ]
    # 添加 --osx-info-plist 参数
    if os.path.exists(info_plist_path):
        cmd.append(f"--osx-info-plist={info_plist_path}")
    if icon_param:
        cmd.append(icon_param)
    if version_file_param:
        cmd.extend(version_file_param)
    cmd.extend([
        "--add-data", f"app/resources{path_sep}app/resources",
        "--add-data", f"app/static{path_sep}app/static",
        "--add-data", f"app/search{path_sep}app/search",
        "--add-data", f"icons{path_sep}icons",
        "--hidden-import", "PyQt6.QtCore",
        "--hidden-import", "PyQt6.QtWidgets",
        "--hidden-import", "PyQt6.QtGui",
        "--hidden-import", "PyQt6.QtWebEngineWidgets",
        "--hidden-import", "PyQt6.QtWebEngineCore",
        "--hidden-import", "qtawesome",
        "--hidden-import", "qtpy",
        "--hidden-import", "sqlite3",
        "--hidden-import", "pynput",
        "--hidden-import", "pynput.keyboard._darwin",
        "--hidden-import", "pynput.mouse._darwin",
        "--collect-all", "qtawesome",
        "--collect-all", "pynput",
        "main.py"
    ])
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

def create_dmg():
    # 优先查找 dist/AiSparkHub.app
    app_bundle = os.path.join(DIST_DIR, f"{APP_NAME}.app")
    if not os.path.exists(app_bundle):
        # 兼容 PyInstaller 可能输出 dist/AiSparkHub/AiSparkHub.app
        app_bundle = os.path.join(DIST_DIR, APP_NAME, f"{APP_NAME}.app")
        if not os.path.exists(app_bundle):
            print(f"未找到 .app 包: {app_bundle}")
            return
    dmg_name = f"{APP_NAME}_v{APP_VERSION}.dmg"
    dmg_path = os.path.join(INSTALLER_DIR, dmg_name)
    print(f"创建DMG安装包: {dmg_path}")
    try:
        # 只将 .app 包目录作为 DMG 内容源
        subprocess.check_call([
            "create-dmg",
            "--volname", f"{APP_NAME} Installer",
            "--volicon", APP_ICON if APP_ICON else "icons/app.icns",
            "--window-pos", "200", "100",
            "--window-size", "800", "400",
            "--icon-size", "100",
            "--icon", f"{APP_NAME}.app", "200", "200",
            "--hide-extension", f"{APP_NAME}.app",
            "--app-drop-link", "600", "200",
            dmg_path,
            app_bundle
        ])
        print(f"DMG创建成功: {dmg_path}")
    except Exception as e:
        print(f"DMG创建失败: {e}")

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
    
    # 创建DMG安装包
    create_dmg()
        
    print(f"{APP_NAME} v{APP_VERSION} 构建完成!")
    print(f".app 位于: {DIST_DIR}/{APP_NAME}.app 或 {DIST_DIR}/{APP_NAME}/{APP_NAME}.app")

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