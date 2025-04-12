#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QHBoxLayout, QPushButton, QApplication
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon
import qtawesome as qta

from app.components.tab_manager import TabManager
from app.components.ai_view import AIView
from app.components.web_view import WebView

class MainWindow(QMainWindow):
    """主窗口类 - 管理多标签页和AI对话界面"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AiSparkHub - 多AI对话桌面应用")
        self.setMinimumSize(1000, 600)
        
        # 设置无边框窗口
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        
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
        
        # 设置按钮样式
        button_style = """
            QPushButton {
                background: transparent;
                border: none;
                padding: 8px 12px;
                margin: 0;
            }
            QPushButton:hover {
                background: #3B4252;
            }
        """
        
        self.close_button.setStyleSheet(button_style + """
            QPushButton:hover {
                background: #BF616A;
            }
        """)
        
        self.minimize_button.setStyleSheet(button_style)
        self.maximize_button.setStyleSheet(button_style)
        self.theme_button.setStyleSheet(button_style)
        
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
            self.maximize_button.setIcon(qta.icon('fa5s.window-maximize'))
        else:
            self.showMaximized()
            self.maximize_button.setIcon(qta.icon('fa5s.window-restore'))
    
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
                
            self._update_theme_icon()
        except Exception as e:
            print(f"切换主题出错: {e}")
    
    def _update_theme_icon(self):
        """根据当前主题更新主题切换按钮图标"""
        # 获取当前应用程序实例
        app = QApplication.instance()
        
        if hasattr(app, 'theme_manager'):
            is_dark = app.theme_manager.current_theme == "dark"
            # 深色模式显示月亮图标，浅色模式显示太阳图标
            self.theme_button.setIcon(qta.icon('fa5s.moon') if is_dark else qta.icon('fa5s.sun'))
            self.theme_button.setToolTip("切换到浅色主题" if is_dark else "切换到深色主题") 
    
    def update_tab_style(self):
        """更新标签样式以匹配当前主题"""
        # 这里可以调用tab_manager的update_style方法
        if hasattr(self, 'tab_manager'):
            self.tab_manager.update_style()

    def _update_theme_icon(self):
        """根据当前主题更新主题切换按钮图标"""
        # 获取当前应用程序实例
        app = QApplication.instance()
        
        if hasattr(app, 'theme_manager'):
            is_dark = app.theme_manager.current_theme == "dark"
            # 深色模式显示月亮图标，浅色模式显示太阳图标
            self.theme_button.setIcon(qta.icon('fa5s.moon') if is_dark else qta.icon('fa5s.sun'))
            self.theme_button.setToolTip("切换到浅色主题" if is_dark else "切换到深色主题") 