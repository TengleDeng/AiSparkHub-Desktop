#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QWidget
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
        
        # 设置图标
        self.setWindowIcon(qta.icon('fa5s.robot', color='#88C0D0'))
        
        # 创建中央窗口部件
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # 创建主布局
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # 初始化标签页管理器
        self.tab_manager = TabManager(self)
        self.main_layout.addWidget(self.tab_manager)
        
        # 创建默认的AI对话页面
        self.create_default_ai_tab()
        
        # 设置状态栏
        self.statusBar().showMessage("就绪")
    
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