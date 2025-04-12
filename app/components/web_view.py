#!/usr/bin/env python
# -*- coding: utf-8 -*-

# web_view.py: 定义 WebView 组件
# 该组件用于"新标签页"功能，提供通用的网页浏览视图，包含地址栏、导航按钮等。

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QPushButton, QHBoxLayout, QTabWidget
from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage
import qtawesome as qta

from app.controllers.web_profile_manager import WebProfileManager

class WebView(QWidget):
    """网页浏览视图组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 获取Web配置管理器
        self.profile_manager = WebProfileManager()
        
        # 设置UI界面
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI界面"""
        # 创建布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 创建工具栏
        toolbar = QWidget()
        toolbar.setMaximumHeight(30) # 设置最大高度
        toolbar.setObjectName("addressToolbar")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(8, 0, 8, 0)
        toolbar_layout.setSpacing(4)
        
        # 后退按钮
        self.back_button = QPushButton()
        self.back_button.setIcon(qta.icon("fa5s.arrow-left"))
        self.back_button.clicked.connect(self.go_back)
        toolbar_layout.addWidget(self.back_button)
        
        # 前进按钮
        self.forward_button = QPushButton()
        self.forward_button.setIcon(qta.icon("fa5s.arrow-right"))
        self.forward_button.clicked.connect(self.go_forward)
        toolbar_layout.addWidget(self.forward_button)
        
        # 刷新按钮
        self.refresh_button = QPushButton()
        self.refresh_button.setIcon(qta.icon("fa5s.sync"))
        self.refresh_button.clicked.connect(self.refresh)
        toolbar_layout.addWidget(self.refresh_button)
        
        # 地址栏
        self.url_input = QLineEdit()
        self.url_input.returnPressed.connect(self.load_url)
        self.url_input.installEventFilter(self) # 安装事件过滤器
        toolbar_layout.addWidget(self.url_input)
        
        # 添加工具栏到主布局
        layout.addWidget(toolbar)
        
        # 创建网页视图，使用共享的profile
        self.web_view = QWebEngineView()
        
        # 使用共享的profile创建页面
        shared_profile = self.profile_manager.get_profile()
        web_page = QWebEnginePage(shared_profile, self.web_view)
        self.web_view.setPage(web_page)
        
        self.web_view.urlChanged.connect(self.url_changed)
        self.web_view.loadFinished.connect(self.load_finished)
        
        # 连接标题变更信号
        self.web_view.titleChanged.connect(self.title_changed)
        # 连接图标变更信号
        self.web_view.iconChanged.connect(self.icon_changed)
        
        layout.addWidget(self.web_view)
        
        # 加载空白页
        self.web_view.setUrl(QUrl("about:blank"))
        
        # 设置样式
        self.setStyleSheet("""
            #addressToolbar {
                background: #2E3440;
            }
            QPushButton {
                background: transparent;
                border: none;
                padding: 2px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #3B4252;
            }
            QPushButton:pressed {
                background: #434C5E;
            }
            QLineEdit {
                background: #3B4252;
                color: #D8DEE9;
                border: 1px solid #434C5E;
                border-radius: 4px;
                padding: 2px 8px;
            }
        """)
    
    def load_url(self):
        """加载URL"""
        url = self.url_input.text()
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        self.web_view.setUrl(QUrl(url))
    
    def url_changed(self, url):
        """URL变化时更新地址栏"""
        self.url_input.setText(url.toString())
        
        # 更新导航按钮状态
        self.back_button.setEnabled(self.web_view.history().canGoBack())
        self.forward_button.setEnabled(self.web_view.history().canGoForward())
    
    def load_finished(self, success):
        """页面加载完成时的处理"""
        if success:
            self.refresh_button.setIcon(qta.icon("fa5s.sync"))
            
            # 获取页面标题
            title = self.web_view.title()
            if title:
                self.update_tab_title(title)
        else:
            self.refresh_button.setIcon(qta.icon("fa5s.exclamation-triangle"))
    
    def title_changed(self, title):
        """网页标题变更时更新标签页标题"""
        if title:
            if title == "about:blank":
                # 重置为"新标签页"
                self.update_tab_title("新标签页")
            else:
                self.update_tab_title(title)
    
    def icon_changed(self, icon):
        """网页图标变更时更新标签页图标"""
        # 只有当图标不为空时更新
        if not icon.isNull():
            self.update_tab_icon(icon)
    
    def update_tab_title(self, title):
        """更新所在标签页的标题"""
        # 查找父标签容器
        tab_widget = self.find_parent_tab_widget()
        if tab_widget:
            # 找到当前标签页的索引
            index = tab_widget.indexOf(self)
            if index != -1:
                tab_widget.setTabText(index, title)
    
    def update_tab_icon(self, icon):
        """更新所在标签页的图标"""
        tab_widget = self.find_parent_tab_widget()
        if tab_widget:
            index = tab_widget.indexOf(self)
            if index != -1:
                tab_widget.setTabIcon(index, icon)
    
    def find_parent_tab_widget(self):
        """查找父TabWidget组件"""
        parent = self.parent()
        while parent:
            if isinstance(parent, QTabWidget):
                return parent
            parent = parent.parent()
        return None
    
    def go_back(self):
        """后退"""
        self.web_view.back()
    
    def go_forward(self):
        """前进"""
        self.web_view.forward()
    
    def refresh(self):
        """刷新"""
        self.web_view.reload()
        
    def eventFilter(self, obj, event):
        """事件过滤器，处理地址栏快捷键"""
        if obj == self.url_input and event.type() == event.Type.KeyPress:
            # Ctrl+Enter 自动补全 www. .com 并加载
            if event.key() == Qt.Key.Key_Return and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                text = self.url_input.text().strip()
                if text and '.' not in text:
                    url = f"www.{text}.com"
                    self.url_input.setText(url)
                    self.load_url() # 调用加载方法
                    return True # 事件已处理
            
        return super().eventFilter(obj, event) 