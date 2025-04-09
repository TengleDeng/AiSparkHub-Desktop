#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QLabel
from PyQt6.QtCore import Qt
import os

class FileExplorer(QWidget):
    """文件浏览器组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI界面"""
        # 创建布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # 创建标题
        title = QLabel("文件浏览")
        title.setStyleSheet("font-weight: bold; color: #88C0D0; padding: 4px;")
        layout.addWidget(title)
        
        # 创建列表视图
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)
        
        # 设置样式
        self.setStyleSheet("""
            QListWidget {
                background-color: #2E3440;
                border: none;
            }
            QListWidget::item {
                padding: 4px;
            }
            QListWidget::item:hover {
                background-color: #3B4252;
            }
            QListWidget::item:selected {
                background-color: #4C566A;
            }
        """)
        
        # 加载当前目录
        self.load_directory(os.getcwd())
    
    def load_directory(self, path):
        """加载指定目录的内容
        
        Args:
            path (str): 要加载的目录路径
        """
        self.list_widget.clear()
        try:
            # 添加返回上级目录的选项
            self.list_widget.addItem("..")
            
            # 获取目录内容
            items = os.listdir(path)
            
            # 先添加文件夹
            for item in sorted(items):
                if os.path.isdir(os.path.join(path, item)):
                    self.list_widget.addItem(f"📁 {item}")
            
            # 再添加文件
            for item in sorted(items):
                if os.path.isfile(os.path.join(path, item)):
                    self.list_widget.addItem(f"📄 {item}")
                    
        except Exception as e:
            self.list_widget.addItem(f"Error: {str(e)}")
    
    def set_root_path(self, path):
        """设置根目录路径"""
        self.load_directory(path) 