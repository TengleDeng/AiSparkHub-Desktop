#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QHBoxLayout, QPushButton
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
        
        self.maximize_button = QPushButton()
        self.maximize_button.setIcon(qta.icon('fa5s.window-maximize'))
        self.maximize_button.clicked.connect(self.toggle_maximize)
        
        self.close_button = QPushButton()
        self.close_button.setIcon(qta.icon('fa5s.times'))
        self.close_button.clicked.connect(self.close)
        
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
        
        # 将窗口控制按钮添加到标签页右上角
        buttons_widget = QWidget()
        buttons_layout = QHBoxLayout(buttons_widget)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(0)
        buttons_layout.addWidget(self.minimize_button)
        buttons_layout.addWidget(self.maximize_button)
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
    
    def create_default_ai_tab(self):
        """创建默认的AI对话标签页"""
        # 创建AI视图
        ai_view = AIView()
        
        # 加载默认的AI网页
        ai_view.add_ai_web_view("ChatGPT", "https://chat.openai.com/")
        ai_view.add_ai_web_view("DeepSeek", "https://chat.deepseek.com/")
        
        # 添加到标签页
        self.tab_manager.add_tab(ai_view, "AI对话", "fa5s.comments")
        
        # 添加一个空的Web标签页
        web_view = WebView()
        self.tab_manager.add_tab(web_view, "新标签页", "fa5s.globe")
    
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