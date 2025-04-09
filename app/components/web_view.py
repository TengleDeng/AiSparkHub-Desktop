#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QPushButton, QHBoxLayout
from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtWebEngineWidgets import QWebEngineView
import qtawesome as qta

class WebView(QWidget):
    """网页浏览视图组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI界面"""
        # 创建布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 创建工具栏
        toolbar = QWidget()
        toolbar.setMaximumHeight(38) # 设置最大高度
        toolbar.setObjectName("addressToolbar")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(8, 4, 8, 4)
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
        
        # 创建网页视图
        self.web_view = QWebEngineView()
        self.web_view.urlChanged.connect(self.url_changed)
        self.web_view.loadFinished.connect(self.load_finished)
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
                padding: 4px;
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
                padding: 4px 8px;
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
        else:
            self.refresh_button.setIcon(qta.icon("fa5s.exclamation-triangle"))
    
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