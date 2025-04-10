#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from PyQt6.QtWidgets import QApplication
from app.components.main_window import MainWindow
from app.components.auxiliary_window import AuxiliaryWindow
from app.controllers.window_manager import WindowManager
from app.controllers.theme_manager import ThemeManager
from app.controllers.web_profile_manager import WebProfileManager
from app.controllers.settings_manager import SettingsManager
from app.models.database import DatabaseManager

def main():
    """应用主入口函数"""
    # 创建应用实例
    app = QApplication(sys.argv)
    
    # 应用主题设置
    theme_manager = ThemeManager()
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