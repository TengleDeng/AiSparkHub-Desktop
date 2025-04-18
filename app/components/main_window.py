#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
主窗口模块 - MainWindow

功能概述:
1. 主窗口框架管理
   - 无边框窗口设计（支持拖动/最大化/最小化）
   - 多标签页容器（TabManager）
   - 自定义标题栏控制按钮（最小化/最大化/关闭/主题切换）

2. 核心功能模块
   - AI对话视图（AIView）管理
   - Web视图（WebView）集成
   - 主题系统集成（深色/浅色模式切换）
   - 窗口状态管理（正常/最大化/多屏幕适配）

3. 主要交互功能
   - 鼠标事件处理（拖动/双击最大化）
   - 键盘事件透传
   - 系统主题变化响应
   - 窗口控制按钮状态同步

设计特点:
- 采用Model-View-Controller模式分离界面与逻辑
- 通过信号槽机制实现模块间通信
- 支持动态主题切换（图标/颜色实时更新）

依赖组件:
- TabManager: 标签页管理
- AIView/WebView: 内容视图
- ThemeManager: 主题管理
- WindowManager: 窗口状态管理

作者: Tengle
维护记录:
- 2025-04-18 添加窗口控制按钮防抖机制
- 2025-04-15 实现动态主题切换
- 2025-04-10 初始版本
"""

from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QHBoxLayout, QPushButton, QApplication
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QIcon
import qtawesome as qta
import logging

from app.components.tab_manager import TabManager
from app.components.ai_view import AIView
from app.components.web_view import WebView
from app.controllers.settings_manager import SettingsManager
from app.controllers.theme_manager import ThemeManager
from app.controllers.window_manager import WindowManager

class MainWindow(QMainWindow):
    """主窗口类 - 管理多标签页和AI对话界面"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AiSparkHub - 多AI对话桌面应用")
        self.setMinimumSize(1000, 600)
        
        # 设置无边框窗口
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        
        # 设置图标
        self.setWindowIcon(qta.icon('fa5s.robot', color='#88C0D0'))
        
        # 创建中央窗口部件
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # 创建主布局
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # 创建标签页管理器
        self.tab_manager = TabManager(self)
        
        # 创建窗口控制按钮
        self.minimize_button = QPushButton()
        self.minimize_button.setIcon(qta.icon('fa5s.window-minimize'))
        self.minimize_button.clicked.connect(self.showMinimized)
        self.minimize_button.setObjectName("minimizeButton")
        
        self.maximize_button = QPushButton()
        self.maximize_button.setIcon(qta.icon('fa5s.window-maximize'))
        self.maximize_button.clicked.connect(self.toggle_maximize)
        self.maximize_button.setObjectName("maximizeButton")
        
        # 添加主题切换按钮
        self.theme_button = QPushButton()
        self.theme_button.setIcon(qta.icon('fa5s.moon'))  # 深色模式默认显示月亮图标
        self.theme_button.setToolTip("切换明暗主题")
        self.theme_button.clicked.connect(self.toggle_theme)
        self.theme_button.setObjectName("themeButton")
        
        self.close_button = QPushButton()
        self.close_button.setIcon(qta.icon('fa5s.times'))
        self.close_button.clicked.connect(self.close)
        self.close_button.setObjectName("closeButton")
        
        # 将窗口控制按钮添加到标签页右上角
        buttons_widget = QWidget()
        buttons_layout = QHBoxLayout(buttons_widget)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(0)
        buttons_layout.addWidget(self.minimize_button)
        buttons_layout.addWidget(self.maximize_button)
        buttons_layout.addWidget(self.theme_button)
        buttons_layout.addWidget(self.close_button)
        
        # 设置为标签页右上角的部件
        self.tab_manager.setCornerWidget(buttons_widget, Qt.Corner.TopRightCorner)
        
        # 添加标签页管理器到主布局
        self.main_layout.addWidget(self.tab_manager)
        
        # 创建默认的AI对话页面
        self.create_default_ai_tab()
        
        # 设置状态栏
        self.statusBar().showMessage("就绪")
        
        # 用于窗口拖动
        self._drag_pos = None
        
        # 在__init__或初始化部分添加连接
        app = QApplication.instance()
        if hasattr(app, 'theme_manager'):
            app.theme_manager.theme_changed.connect(self.update_tab_style)
        
        self.theme_manager = app.theme_manager

        # 连接主题变化信号，用于更新窗口控制按钮图标
        if self.theme_manager:
            self.theme_manager.theme_changed.connect(self._update_window_control_icons)

        self._icon_update_timer = QTimer()
        self._icon_update_timer.setSingleShot(True)
        self._icon_update_timer.setInterval(100)  # 100ms防抖窗口
        self._icon_update_timer.timeout.connect(self._real_update_icons)

    def create_default_ai_tab(self):
        """创建默认的AI对话标签页"""
        # 创建AI视图
        ai_view = AIView()
        
        # 添加到标签页（不可关闭）
        self.tab_manager.add_ai_view_tab(ai_view, "AiSparkHub")
        
        # 直接添加"+"标签页
        self.tab_manager.add_plus_tab()
        
        # 不默认创建新标签页，用户可以通过点击"+"号创建
    
    def keyPressEvent(self, event):
        """处理键盘事件"""
        super().keyPressEvent(event)
    
    def closeEvent(self, event):
        """处理窗口关闭事件"""
        super().closeEvent(event)
    
    def toggle_maximize(self):
        """切换窗口最大化状态"""
        if self.isMaximized():
            self.showNormal()
            self.maximize_button.setIcon(qta.icon('fa5s.window-restore'))
        else:
            self.showMaximized()
            self.maximize_button.setIcon(qta.icon('fa5s.window-maximize'))
    
    def mousePressEvent(self, event):
        """处理鼠标按下事件，用于窗口拖动"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()
    
    def mouseMoveEvent(self, event):
        """处理鼠标移动事件，用于窗口拖动"""
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos is not None:
            diff = event.globalPosition().toPoint() - self._drag_pos
            self.move(self.pos() + diff)
            self._drag_pos = event.globalPosition().toPoint()
    
    def mouseReleaseEvent(self, event):
        """处理鼠标释放事件"""
        self._drag_pos = None
    
    def get_ai_view(self):
        """获取当前的AI视图实例
        
        Returns:
            AIView: 当前的AI视图实例，如果不存在则返回None
        """
        # 如果还没有创建标签页，返回None
        if not hasattr(self, 'tab_manager'):
            return None
            
        # 遍历所有标签页，找到AIView类型的实例
        for i in range(self.tab_manager.count()):
            widget = self.tab_manager.widget(i)
            if hasattr(widget, '__class__') and widget.__class__.__name__ == 'AIView':
                return widget
                
        # 如果没有找到AIView，返回None
        return None
        
    def mouseDoubleClickEvent(self, event):
        """处理鼠标双击事件，用于最大化/还原窗口"""
        # 检查双击是否在标题栏区域 (标签栏高度范围内)
        if event.button() == Qt.MouseButton.LeftButton:
            tab_bar_height = self.tab_manager.tabBar().height()
            if event.position().toPoint().y() <= tab_bar_height:
                self.toggle_maximize()
            else:
                super().mouseDoubleClickEvent(event)
        else:
            super().mouseDoubleClickEvent(event)
    
    def toggle_theme(self):
        """切换应用主题"""
        try:
            # 尝试使用window_manager切换主题
            if hasattr(self, 'window_manager') and self.window_manager:
                self.window_manager.toggle_theme()
            # 备用方案：直接使用QApplication实例的theme_manager
            elif hasattr(QApplication.instance(), 'theme_manager'):
                app = QApplication.instance()
                current_theme = app.theme_manager.current_theme
                new_theme = "light" if current_theme == "dark" else "dark"
                app.theme_manager.apply_theme(app, new_theme)
                print(f"已切换主题: {new_theme}")
            else:
                print("无法访问主题管理器")
                
            self._update_window_control_icons()
        except Exception as e:
            print(f"Error toggling theme: {e}")
    
    def _update_window_control_icons(self):
        """外部调用的入口"""
        self._icon_update_timer.start()

    def _real_update_icons(self):
        """实际的图标更新逻辑"""
        logger = logging.getLogger("AiSparkHub")
        logger.debug("实际执行图标更新...")
        if not self.theme_manager:
            logger.warning("ThemeManager未初始化，无法更新窗口控制按钮图标")
            return
            
        theme_colors = self.theme_manager.get_current_theme_colors()
        icon_color = theme_colors.get('foreground', '#D8DEE9')
        logger.debug(f"当前主题图标颜色: {icon_color}")
        
        if hasattr(self, 'minimize_button'):
            self.minimize_button.setIcon(qta.icon("fa5s.window-minimize", color=icon_color))
            
        if hasattr(self, 'maximize_button'):
            if self.isMaximized():
                self.maximize_button.setIcon(qta.icon("fa5s.window-restore", color=icon_color))
            else:
                self.maximize_button.setIcon(qta.icon("fa5s.window-maximize", color=icon_color))
        
        if hasattr(self, 'theme_button'):
            if self.theme_manager.current_theme == "dark":
                self.theme_button.setIcon(qta.icon("fa5s.moon", color=icon_color))
            else:
                self.theme_button.setIcon(qta.icon("fa5s.sun", color=icon_color))
                
        if hasattr(self, 'close_button'):
             self.close_button.setIcon(qta.icon("fa5s.times", color=icon_color))
             
        logger.debug("窗口控制按钮图标更新完成")
    
    def update_tab_style(self):
        """更新标签样式以匹配当前主题"""
        # 这里可以调用tab_manager的update_style方法
        if hasattr(self, 'tab_manager'):
            self.tab_manager.update_style()

    def _init_title_bar(self):
        """初始化自定义标题栏"""
        self.showMaximized()
        
        # 更新最大化/恢复按钮的图标
        self._update_window_control_icons()
        
    def resizeEvent(self, event):
        """窗口大小调整事件，用于更新按钮图标"""
        super().resizeEvent(event)
        # 更新最大化/恢复按钮图标（包含颜色）
        self._update_window_control_icons()