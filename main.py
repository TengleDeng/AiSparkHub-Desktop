#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
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

# pynput 用于全局快捷键
try:
    from pynput import keyboard
except ImportError:
    keyboard = None
    print("无法导入pynput库，全局快捷键功能将不可用")

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

def setup_tray_icon(app, main_window, auxiliary_window):
    """设置系统托盘图标和菜单"""
    # 创建托盘图标
    tray_icon = QSystemTrayIcon(qta.icon('fa5s.robot', color='#1D0BE3'), app)
    
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
    
    return tray_icon

def toggle_window_visibility(window):
    """切换窗口显示/隐藏状态"""
    try:
        # 详细记录窗口当前状态
        window_state = window.windowState()
        is_visible = window.isVisible()
        is_active = window.isActiveWindow()
        is_minimized = bool(window_state & Qt.WindowState.WindowMinimized)
        
        print(f"窗口详细状态: 可见={is_visible}, 激活={is_active}, 最小化={is_minimized}, 标题={window.windowTitle()}")
        
        if is_visible and not is_minimized:
            # 如果窗口可见且未最小化,则隐藏
            print(f"执行隐藏窗口: {window.windowTitle()}")
            window.hide()
        else:
            # 否则显示并激活窗口
            print(f"执行显示窗口: {window.windowTitle()}")
            # 先恢复窗口状态(如果最小化)
            if is_minimized:
                window.setWindowState(window_state & ~Qt.WindowState.WindowMinimized)
            
            window.show()
            window.raise_()
            window.activateWindow()
            # 强制窗口获得焦点
            window.setFocus(Qt.FocusReason.OtherFocusReason)
        
        # 验证操作结果
        print(f"操作后窗口状态 - 可见: {window.isVisible()}, 激活: {window.isActiveWindow()}, 标题: {window.windowTitle()}")
    except Exception as e:
        print(f"切换窗口可见性时出错: {e}")
        import traceback
        traceback.print_exc()

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
    
    print(f"已加载全局快捷键配置: {shortcuts}")
    
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
            
            print(f"窗口当前状态: 可见={is_visible}, 最小化={is_minimized}, 标题={window.windowTitle()}")
            
            # 如果窗口可见，则强制隐藏
            if is_visible:
                print(f"强制隐藏窗口: {window.windowTitle()}")
                # 直接写入应用状态变量，确保正确记录
                window.setProperty("_visible_before_hide", True)
                window.hide()
                print(f"窗口隐藏后状态: 可见={window.isVisible()}")
            else:
                # 窗口不可见，则强制显示
                print(f"强制显示窗口: {window.windowTitle()}")
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
                print(f"窗口显示后状态: 可见={window.isVisible()}, 激活={window.isActiveWindow()}")
        except Exception as e:
            print(f"切换窗口状态出错: {e}")
            import traceback
            traceback.print_exc()
    
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
            print("执行主窗口切换")
            force_toggle_window(main_window)
        
        @pyqtSlot()
        def _toggle_aux(self):
            print("执行辅助窗口切换")
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
                            
                            print(f"触发自定义快捷键: {'+'.join(current_modifiers)}+{key_char} ({name})")
                            
                            # 触发相应的动作
                            if name == "main_window":
                                handler.toggle_main_window.emit()
                            elif name == "auxiliary_window":
                                handler.toggle_aux_window.emit()
        except Exception as e:
            print(f"快捷键处理出错: {e}")
            import traceback
            traceback.print_exc()
    
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
            print(f"按键释放处理出错: {e}")
    
    # 创建键盘监听器
    def start_listener():
        try:
            # 启动监听器，设置为守护线程
            listener = keyboard.Listener(on_press=on_press, on_release=on_release, daemon=True)
            listener.start()
            print("全局快捷键监听器已启动")
            return listener
        except Exception as e:
            print(f"启动键盘监听器出错: {e}")
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
                print("键盘监听器已停止")
            except:
                pass
    
    # 返回清理函数
    return cleanup_listener

def main():
    """应用主入口函数"""
    # 首先确保所有必要的目录都已创建
    data_dir = ensure_app_directories()
    print(f"应用数据目录: {data_dir}")
    
    # 创建应用实例
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # 关闭所有窗口时不退出应用
    
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
    
    # 运行应用
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 