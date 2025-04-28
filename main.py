#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AiSparkHub 桌面应用主入口模块

功能:
1. 初始化应用目录结构和日志系统
2. 设置系统托盘图标和全局快捷键
3. 管理主窗口(AI窗口)和辅助窗口(提示词窗口)
4. 处理多屏幕环境下的窗口布局
5. 应用主题和用户设置管理

作者: Tengle
日期: 2025-04-18
"""

import sys
import os
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QSplashScreen, QMessageBox, QStyleFactory
from PyQt6.QtCore import Qt, QTimer, QDir, QCoreApplication, QThread, QTranslator, QSettings
from PyQt6.QtGui import QIcon, QAction, QPixmap, QFontDatabase
import qtawesome as qta

from app.components.main_window import MainWindow
from app.components.auxiliary_window import AuxiliaryWindow
from app.components.shortcut_settings_dialog import ShortcutSettingsDialog
from app.controllers.window_manager import WindowManager
from app.controllers.theme_manager import ThemeManager
from app.controllers.web_profile_manager import WebProfileManager
from app.controllers.settings_manager import SettingsManager
from app.models.database import DatabaseManager
from app.utils.logger import setup_logger

# 全局logger对象
logger = None

# pynput 用于全局快捷键
try:
    from pynput import keyboard
except ImportError:
    keyboard = None
    print("无法导入pynput库，全局快捷键功能将不可用")

def configure_logging(data_dir):
    """配置应用程序日志系统"""
    global logger
    
    # 创建logger
    logger = logging.getLogger("AiSparkHub")
    logger.setLevel(logging.DEBUG)
    
    # 防止重复配置
    if logger.handlers:
        return logger
        
    # 设置日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(name)s - %(filename)s:%(lineno)d - %(message)s'
    )
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)  # 控制台只显示INFO及以上
    console_formatter = logging.Formatter('%(message)s')  # 简化控制台输出格式
    console_handler.setFormatter(console_formatter)
    
    # 文件处理器
    log_file = os.path.join(data_dir, "logs", "app.log")
    file_handler = RotatingFileHandler(
        log_file, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    # 添加处理器
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    logger.info("日志系统初始化完成")
    logger.info(f"日志文件保存在: {log_file}")
    return logger

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
    try:
        os.makedirs(data_dir, exist_ok=True)
        print(f"确保主数据目录存在: {data_dir}")  # 保留这个print，因为logger尚未初始化
    except PermissionError as e:
        print(f"警告: 无法创建数据目录 '{data_dir}': {e}")
        # 尝试回退到用户临时目录
        import tempfile
        data_dir = os.path.join(tempfile.gettempdir(), app_name)
        os.makedirs(data_dir, exist_ok=True)
        print(f"已回退到临时目录: {data_dir}")
    
    # 创建各种子目录
    subdirs = ["database", "cache", "webdata", "temp", "logs"]
    for subdir in subdirs:
        subdir_path = os.path.join(data_dir, subdir)
        try:
            os.makedirs(subdir_path, exist_ok=True)
            print(f"确保子目录存在: {subdir_path}")  # 保留这个print，因为logger尚未初始化
        except Exception as e:
            print(f"创建子目录 {subdir_path} 时出错: {e}")
    
    # 确保search目录创建并复制文件 - 在打包环境下
    if getattr(sys, 'frozen', False):
        try:
            # 确定_internal/app/search目录
            if sys.platform == 'win32':
                # 获取可执行文件所在目录
                exe_dir = os.path.dirname(sys.executable)
                internal_app_dir = os.path.join(exe_dir, "_internal", "app")
                search_dest_dir = os.path.join(internal_app_dir, "search")
                
                # 创建search目录
                os.makedirs(search_dest_dir, exist_ok=True)
                print(f"确保搜索目录存在: {search_dest_dir}")
                
                # 源搜索文件目录
                search_src_dir = os.path.join(internal_app_dir, "resources", "app", "search")
                if os.path.exists(search_src_dir):
                    import shutil
                    # 复制所有搜索相关文件
                    search_files = ["index.html", "styles.css", "script.js", "README.md"]
                    for file in search_files:
                        src_file = os.path.join(search_src_dir, file)
                        dest_file = os.path.join(search_dest_dir, file)
                        if os.path.exists(src_file):
                            try:
                                shutil.copy2(src_file, dest_file)
                                print(f"已复制搜索文件: {file}")
                            except Exception as e:
                                print(f"复制搜索文件 {file} 时出错: {e}")
                else:
                    print(f"警告: 搜索源文件目录不存在: {search_src_dir}")
        except Exception as e:
            print(f"处理搜索目录时出错: {e}")
    
    return data_dir

def setup_tray_icon(app, main_window, auxiliary_window):
    """设置系统托盘图标和菜单"""
    # 优先使用应用程序图标
    if hasattr(app, 'windowIcon') and not app.windowIcon().isNull():
        tray_icon = QSystemTrayIcon(app.windowIcon(), app)
        logger.info("系统托盘使用应用程序图标")
    else:
        # 后备使用FA图标
        tray_icon = QSystemTrayIcon(qta.icon('fa5s.robot', color='#1D0BE3'), app)
        logger.info("系统托盘使用备用图标")
    
    # 创建托盘菜单
    tray_menu = QMenu()
    
    # 添加显示/隐藏主窗口菜单项
    show_main_action = QAction("显示/隐藏AI窗口", app)
    show_main_action.triggered.connect(lambda: toggle_window_visibility(main_window))
    tray_menu.addAction(show_main_action)
    
    # 添加显示/隐藏辅助窗口菜单项
    show_aux_action = QAction("显示/隐藏提示词窗口", app)
    show_aux_action.triggered.connect(lambda: toggle_window_visibility(auxiliary_window))
    tray_menu.addAction(show_aux_action)
    
    # 添加分隔线
    tray_menu.addSeparator()
    
    # 添加退出菜单项
    exit_action = QAction("退出", app)
    exit_action.triggered.connect(app.quit)
    tray_menu.addAction(exit_action)
    
    # 设置托盘图标的上下文菜单
    tray_icon.setContextMenu(tray_menu)
    
    # 托盘图标点击事件
    tray_icon.activated.connect(lambda reason: tray_icon_activated(reason, main_window, tray_icon))
    
    # 显示托盘图标
    tray_icon.show()
    
    logger.info("系统托盘图标已设置")
    return tray_icon

def toggle_window_visibility(window):
    """切换窗口显示/隐藏状态"""
    try:
        # 详细记录窗口当前状态
        window_state = window.windowState()
        is_visible = window.isVisible()
        is_active = window.isActiveWindow()
        is_minimized = bool(window_state & Qt.WindowState.WindowMinimized)
        
        logger.debug(f"窗口详细状态: 可见={is_visible}, 激活={is_active}, 最小化={is_minimized}, 标题={window.windowTitle()}")
        
        if is_visible and not is_minimized:
            # 如果窗口可见且未最小化,则隐藏
            logger.info(f"执行隐藏窗口: {window.windowTitle()}")
            window.hide()
        else:
            # 否则显示并激活窗口
            logger.info(f"执行显示窗口: {window.windowTitle()}")
            # 先恢复窗口状态(如果最小化)
            if is_minimized:
                window.setWindowState(window_state & ~Qt.WindowState.WindowMinimized)
            
            window.show()
            window.raise_()
            window.activateWindow()
            # 强制窗口获得焦点
            window.setFocus(Qt.FocusReason.OtherFocusReason)
        
        # 验证操作结果
        logger.debug(f"操作后窗口状态 - 可见: {window.isVisible()}, 激活: {window.isActiveWindow()}, 标题: {window.windowTitle()}")
    except Exception as e:
        logger.error(f"切换窗口可见性时出错: {e}", exc_info=True)

def tray_icon_activated(reason, window, tray_icon):
    """处理托盘图标点击事件"""
    if reason == QSystemTrayIcon.ActivationReason.Trigger:  # 单击
        toggle_window_visibility(window)

def setup_global_shortcuts(app, main_window, auxiliary_window):
    """使用pynput设置全局快捷键"""
    # 记录按键状态
    alt_pressed = False
    ctrl_pressed = False
    shift_pressed = False
    meta_pressed = False
    
    # 从设置读取自定义快捷键
    settings = QSettings("AiSparkHub", "GlobalShortcuts")
    
    # 默认快捷键配置
    default_shortcuts = {
        "main_window": "Alt+X",
        "auxiliary_window": "Alt+C"
    }
    
    # 加载自定义快捷键
    shortcuts = {}
    for name, default_value in default_shortcuts.items():
        shortcuts[name] = settings.value(name, default_value)
    
    logger.info(f"已加载全局快捷键配置: {shortcuts}")
    
    # 解析快捷键配置
    parsed_shortcuts = {}
    for name, shortcut in shortcuts.items():
        # 分解快捷键字符串为组合键列表
        key_parts = shortcut.split("+")
        modifiers = [part.lower() for part in key_parts[:-1]]  # 修饰键部分
        key = key_parts[-1].lower() if key_parts else ""       # 主键部分
        
        parsed_shortcuts[name] = {
            "modifiers": modifiers,
            "key": key
        }
    
    # 窗口显示状态强制切换函数
    def force_toggle_window(window):
        try:
            window_state = window.windowState()
            is_visible = window.isVisible()
            is_minimized = bool(window_state & Qt.WindowState.WindowMinimized)
            
            logger.debug(f"窗口当前状态: 可见={is_visible}, 最小化={is_minimized}, 标题={window.windowTitle()}")
            
            # 如果窗口可见，则强制隐藏
            if is_visible:
                logger.info(f"强制隐藏窗口: {window.windowTitle()}")
                # 直接写入应用状态变量，确保正确记录
                window.setProperty("_visible_before_hide", True)
                window.hide()
                logger.debug(f"窗口隐藏后状态: 可见={window.isVisible()}")
            else:
                # 窗口不可见，则强制显示
                logger.info(f"强制显示窗口: {window.windowTitle()}")
                # 如果窗口最小化，先还原
                if is_minimized:
                    window.setWindowState(window_state & ~Qt.WindowState.WindowMinimized)
                # 使用强制显示序列
                window.show()
                window.raise_()
                window.activateWindow()
                window.setFocus(Qt.FocusReason.OtherFocusReason)
                # 设置窗口为激活状态
                window.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, False)
                logger.debug(f"窗口显示后状态: 可见={window.isVisible()}, 激活={window.isActiveWindow()}")
        except Exception as e:
            logger.error(f"切换窗口状态出错: {e}", exc_info=True)
    
    # 保持一个对窗口的强引用和处理函数的引用
    window_actions = {
        'main_window': lambda: force_toggle_window(main_window),
        'auxiliary_window': lambda: force_toggle_window(auxiliary_window)
    }
    
    # 创建用于消息传递的事件处理器
    from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
    
    class WindowToggleHandler(QObject):
        # 定义信号
        toggle_main_window = pyqtSignal()
        toggle_aux_window = pyqtSignal()
        
        @pyqtSlot()
        def _toggle_main(self):
            logger.info("执行主窗口切换")
            force_toggle_window(main_window)
        
        @pyqtSlot()
        def _toggle_aux(self):
            logger.info("执行辅助窗口切换")
            force_toggle_window(auxiliary_window)
    
    # 创建事件处理器实例并连接信号
    handler = WindowToggleHandler()
    handler.toggle_main_window.connect(handler._toggle_main)
    handler.toggle_aux_window.connect(handler._toggle_aux)
    
    # 保存到应用实例以防被垃圾回收
    app._window_toggle_handler = handler
    
    def on_press(key):
        """按键按下事件处理"""
        nonlocal alt_pressed, ctrl_pressed, shift_pressed, meta_pressed
        
        try:
            # 检测修饰键
            if key == keyboard.Key.alt or key == keyboard.Key.alt_l or key == keyboard.Key.alt_r:
                alt_pressed = True
            elif key == keyboard.Key.ctrl or key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
                ctrl_pressed = True
            elif key == keyboard.Key.shift or key == keyboard.Key.shift_l or key == keyboard.Key.shift_r:
                shift_pressed = True
            elif key == keyboard.Key.cmd:
                meta_pressed = True
            else:
                # 获取按键字符
                key_char = None
                if hasattr(key, 'char'):
                    key_char = key.char
                elif isinstance(key, keyboard.KeyCode) and key.char:
                    key_char = key.char
                    
                # 如果是字母按键，转为小写处理
                if key_char:
                    key_char = key_char.lower()
                    
                    # 检查当前按键组合是否匹配任何配置的快捷键
                    current_modifiers = []
                    if alt_pressed:
                        current_modifiers.append("alt")
                    if ctrl_pressed:
                        current_modifiers.append("ctrl") 
                    if shift_pressed:
                        current_modifiers.append("shift")
                    if meta_pressed:
                        current_modifiers.append("meta")
                    
                    # 检查每个配置的快捷键
                    for name, shortcut_info in parsed_shortcuts.items():
                        shortcut_modifiers = set(shortcut_info["modifiers"])
                        shortcut_key = shortcut_info["key"].lower()
                        
                        # 检查主键和修饰键是否都匹配
                        if (key_char == shortcut_key.lower() and 
                            set(current_modifiers) == shortcut_modifiers):
                            
                            logger.info(f"触发自定义快捷键: {'+'.join(current_modifiers)}+{key_char} ({name})")
                            
                            # 触发相应的动作
                            if name == "main_window":
                                handler.toggle_main_window.emit()
                            elif name == "auxiliary_window":
                                handler.toggle_aux_window.emit()
        except Exception as e:
            logger.error(f"快捷键处理出错: {e}", exc_info=True)
    
    def on_release(key):
        """按键释放事件处理"""
        nonlocal alt_pressed, ctrl_pressed, shift_pressed, meta_pressed
        
        try:
            # 检测修饰键释放
            if key == keyboard.Key.alt or key == keyboard.Key.alt_l or key == keyboard.Key.alt_r:
                alt_pressed = False
            elif key == keyboard.Key.ctrl or key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
                ctrl_pressed = False
            elif key == keyboard.Key.shift or key == keyboard.Key.shift_l or key == keyboard.Key.shift_r:
                shift_pressed = False
            elif key == keyboard.Key.cmd:
                meta_pressed = False
        except Exception as e:
            logger.error(f"按键释放处理出错: {e}")
    
    # 创建键盘监听器
    def start_listener():
        try:
            # 启动监听器，设置为守护线程
            listener = keyboard.Listener(on_press=on_press, on_release=on_release, daemon=True)
            listener.start()
            logger.info("全局快捷键监听器已启动")
            return listener
        except Exception as e:
            logger.error(f"启动键盘监听器出错: {e}", exc_info=True)
            return None
    
    # 立即启动监听器
    listener = start_listener()
    # 保存引用到app对象防止被垃圾回收
    app._keyboard_listener = listener
    
    # 定义清理函数
    def cleanup_listener():
        if hasattr(app, '_keyboard_listener'):
            try:
                app._keyboard_listener.stop()
                logger.info("键盘监听器已停止")
            except Exception as e:
                logger.error(f"停止键盘监听器时出错: {e}")
    
    # 返回清理函数
    return cleanup_listener

def main():
    """应用主入口函数"""
    # 首先确保所有必要的目录都已创建
    data_dir = ensure_app_directories()
    
    # 配置日志系统
    global logger
    logger = configure_logging(data_dir)
    logger.info(f"应用数据目录: {data_dir}")
    
    # 创建应用实例
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # 关闭所有窗口时不退出应用
    
    # 设置应用程序图标
    app_icon_path = ""
    if getattr(sys, 'frozen', False):
        # 打包环境
        exe_dir = os.path.dirname(sys.executable)
        possible_icon_paths = [
            os.path.join(exe_dir, "icons", "app.ico"),
            os.path.join(exe_dir, "app.ico")
        ]
        for path in possible_icon_paths:
            if os.path.exists(path):
                app_icon_path = path
                break
    else:
        # 开发环境
        possible_icon_paths = [
            os.path.join("icons", "app.ico"),
            os.path.join("app", "resources", "icon.ico")
        ]
        for path in possible_icon_paths:
            if os.path.exists(path):
                app_icon_path = path
                break
    
    if app_icon_path:
        app_icon = QIcon(app_icon_path)
        app.setWindowIcon(app_icon)
        logger.info(f"已设置应用程序图标: {app_icon_path}")
    else:
        logger.warning("未找到应用程序图标文件")
    
    # 应用主题设置
    theme_manager = ThemeManager()
    app.theme_manager = theme_manager
    theme_manager.apply_theme(app)
    logger.info("应用主题已应用")
    
    # 初始化数据库
    db_manager = DatabaseManager()
    app.db_manager = db_manager  # 将数据库管理器添加到app对象中
    logger.info("数据库管理器已初始化")
    
    # 初始化Web配置管理器
    web_profile_manager = WebProfileManager()
    logger.info("Web配置管理器已初始化")
    
    # 初始化用户设置管理器
    settings_manager = SettingsManager()
    logger.info("用户设置管理器已初始化")
    
    # 创建主窗口和辅助窗口
    main_window = MainWindow()
    auxiliary_window = AuxiliaryWindow(db_manager)
    logger.info("应用窗口已创建")
    
    # 初始化窗口管理器
    window_manager = WindowManager(main_window, auxiliary_window)
    
    # 设置主窗口和辅助窗口的window_manager属性
    main_window.window_manager = window_manager
    auxiliary_window.window_manager = window_manager
    
    # 检测屏幕数量，根据情况选择显示模式
    screens = app.screens()
    logger.info(f"检测到 {len(screens)} 个屏幕")
    if len(screens) > 1:
        logger.info("启用双屏幕模式")
        window_manager.set_dual_screen_mode()
    else:
        logger.info("使用初始显示模式")
        window_manager.set_initial_display_mode()
    
    # 设置系统托盘图标
    tray_icon = setup_tray_icon(app, main_window, auxiliary_window)
    
    # 设置全局快捷键并获取清理函数
    cleanup_shortcuts = setup_global_shortcuts(app, main_window, auxiliary_window)
    
    # 应用退出时执行清理操作
    app.aboutToQuit.connect(db_manager.close_connection)
    app.aboutToQuit.connect(cleanup_shortcuts)
    
    # 显示窗口
    main_window.show()
    auxiliary_window.show()
    
    logger.info("应用程序启动完成")
    
    # 运行应用
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 