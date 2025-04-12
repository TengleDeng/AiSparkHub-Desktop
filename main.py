#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from app.components.main_window import MainWindow
from app.components.auxiliary_window import AuxiliaryWindow
from app.controllers.window_manager import WindowManager
from app.controllers.theme_manager import ThemeManager
from app.controllers.web_profile_manager import WebProfileManager
from app.controllers.settings_manager import SettingsManager
from app.models.database import DatabaseManager

def ensure_app_directories():
    """确保应用所需的所有目录都已创建"""
    # 应用名称
    app_name = "AiSparkHub"
    
    # 确定数据存储路径
    if getattr(sys, 'frozen', False):
        # PyInstaller打包环境
        if sys.platform == 'win32':
            # Windows: %APPDATA%\AiSparkHub
            base_dir = os.environ.get('APPDATA', '')
            data_dir = os.path.join(base_dir, app_name)
        elif sys.platform == 'darwin':
            # macOS: ~/Library/Application Support/AiSparkHub
            data_dir = os.path.join(str(Path.home()), "Library", "Application Support", app_name)
        else:
            # Linux: ~/.local/share/AiSparkHub
            data_dir = os.path.join(str(Path.home()), ".local", "share", app_name)
    else:
        # 开发环境直接使用项目目录下的data文件夹
        data_dir = os.path.abspath("data")
    
    # 创建主数据目录
    os.makedirs(data_dir, exist_ok=True)
    print(f"确保主数据目录存在: {data_dir}")
    
    # 创建各种子目录
    subdirs = ["database", "cache", "webdata", "temp", "logs"]
    for subdir in subdirs:
        subdir_path = os.path.join(data_dir, subdir)
        os.makedirs(subdir_path, exist_ok=True)
        print(f"确保子目录存在: {subdir_path}")
    
    return data_dir

def main():
    """应用主入口函数"""
    # 首先确保所有必要的目录都已创建
    data_dir = ensure_app_directories()
    print(f"应用数据目录: {data_dir}")
    
    # 创建应用实例
    app = QApplication(sys.argv)
    
    # 应用主题设置
    theme_manager = ThemeManager()
    app.theme_manager = theme_manager
    theme_manager.apply_theme(app)
    
    # 初始化数据库
    db_manager = DatabaseManager()
    
    # 初始化Web配置管理器
    web_profile_manager = WebProfileManager()
    
    # 初始化用户设置管理器
    settings_manager = SettingsManager()
    
    # 创建主窗口和辅助窗口
    main_window = MainWindow()
    auxiliary_window = AuxiliaryWindow(db_manager)
    
    # 初始化窗口管理器
    window_manager = WindowManager(main_window, auxiliary_window)
    
    # 设置主窗口和辅助窗口的window_manager属性
    main_window.window_manager = window_manager
    auxiliary_window.window_manager = window_manager
    
    # 检测屏幕数量，根据情况选择显示模式
    screens = app.screens()
    print(f"检测到 {len(screens)} 个屏幕")
    if len(screens) > 1:
        print("检测到多个屏幕，启用双屏幕模式")
        window_manager.set_dual_screen_mode()
    else:
        print("检测到单个屏幕，使用初始显示模式")
        window_manager.set_initial_display_mode()
    
    # 应用退出时执行清理操作
    app.aboutToQuit.connect(db_manager.close_connection)
    
    # 显示窗口
    main_window.show()
    auxiliary_window.show()
    
    # 运行应用
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 