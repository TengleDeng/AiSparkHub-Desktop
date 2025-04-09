#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import QTabWidget, QPushButton
from PyQt6.QtCore import Qt
import qtawesome as qta

class TabManager(QTabWidget):
    """标签页管理器组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI界面"""
        # 设置标签可关闭
        self.setTabsClosable(True)
        
        # 设置标签可移动
        self.setMovable(True)
        
        # 添加新标签页按钮
        self.add_tab_button = QPushButton("+")
        self.add_tab_button.setFixedSize(24, 24)
        self.add_tab_button.clicked.connect(self.add_new_tab)
        self.setCornerWidget(self.add_tab_button, Qt.Corner.TopRightCorner)
        
        # 连接关闭标签信号
        self.tabCloseRequested.connect(self.close_tab)
        
        # 设置样式
        self.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background: #2E3440;
            }
            QTabWidget::tab-bar {
                alignment: left;
            }
            QTabBar::tab {
                background: #3B4252;
                color: #D8DEE9;
                padding: 8px 12px;
                border: none;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: #4C566A;
            }
            QTabBar::tab:hover {
                background: #434C5E;
            }
            QPushButton {
                background: #3B4252;
                color: #D8DEE9;
                border: none;
                border-radius: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #434C5E;
            }
        """)
    
    def add_tab(self, widget, title, icon_name=None):
        """添加新标签页
        
        Args:
            widget: 标签页内容组件
            title (str): 标签页标题
            icon_name (str): 图标名称
        """
        index = self.addTab(widget, title)
        if icon_name:
            self.setTabIcon(index, qta.icon(icon_name))
        return index
    
    def add_new_tab(self):
        """添加新的空白标签页"""
        from app.components.web_view import WebView
        web_view = WebView()
        self.add_tab(web_view, "新标签页", "fa5s.globe")
    
    def close_tab(self, index):
        """关闭标签页
        
        Args:
            index (int): 标签页索引
        """
        # 不允许关闭最后一个标签页
        if self.count() > 1:
            self.removeTab(index) 