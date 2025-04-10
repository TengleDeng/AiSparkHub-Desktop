#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTreeView, QLabel, QHeaderView
from PyQt6.QtCore import Qt, QDir, QModelIndex
from PyQt6.QtGui import QFileSystemModel
import os

class FileExplorer(QWidget):
    """文件浏览器组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.root_path = os.getcwd()
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI界面"""
        # 创建布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # 创建文件系统模型
        self.model = QFileSystemModel()
        # 设置根目录为系统根目录，以显示完整的文件系统树
        self.model.setRootPath("")  # 使用空字符串表示文件系统根目录
        # 设置过滤器以显示目录和文件
        self.model.setFilter(QDir.AllEntries | QDir.NoDotAndDotDot)
        
        # 创建树形视图
        self.tree_view = QTreeView()
        self.tree_view.setModel(self.model)
        # 设置初始显示的索引为根目录，但不限制仅显示该目录下内容
        self.tree_view.setRootIndex(self.model.index(""))
        
        # 展开到当前工作目录
        current_index = self.model.index(self.root_path)
        self.tree_view.scrollTo(current_index)
        self.tree_view.setCurrentIndex(current_index)
        # 展开到当前工作目录
        self.expand_to_path(self.root_path)
        
        # 设置视图属性
        self.tree_view.setAnimated(True)  # 启用动画效果更好
        self.tree_view.setIndentation(20)
        self.tree_view.setSortingEnabled(True)
        self.tree_view.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        
        # 只显示文件名列,隐藏其他列
        self.tree_view.setHeaderHidden(True)
        for i in range(1, self.model.columnCount()):
            self.tree_view.hideColumn(i)
        
        layout.addWidget(self.tree_view)
        
        # 设置样式
        self.setStyleSheet("""
            QTreeView {
                background-color: #2E3440;
                border: none;
                outline: none;
            }
            QTreeView::item {
                padding: 4px;
            }
            QTreeView::item:hover {
                background-color: #3B4252;
            }
            QTreeView::item:selected {
                background-color: #4C566A;
            }
            QTreeView::branch {
                background-color: #2E3440;
            }
            QTreeView::branch:selected {
                background-color: #4C566A;
            }
            QTreeView::branch:has-siblings:!adjoins-item {
                border-image: url(branch-vline.png) 0;
            }
            QTreeView::branch:has-siblings:adjoins-item {
                border-image: url(branch-more.png) 0;
            }
            QTreeView::branch:!has-children:!has-siblings:adjoins-item {
                border-image: url(branch-end.png) 0;
            }
            QTreeView::branch:has-children:!has-siblings:closed,
            QTreeView::branch:closed:has-children:has-siblings {
                border-image: none;
                image: url(branch-closed.png);
            }
            QTreeView::branch:open:has-children:!has-siblings,
            QTreeView::branch:open:has-children:has-siblings {
                border-image: none;
                image: url(branch-open.png);
            }
        """)
    
    def expand_to_path(self, path):
        """展开到指定路径"""
        if not path:
            return
            
        # 获取路径的每一部分
        parts = []
        temp_path = path
        while temp_path:
            parts.insert(0, temp_path)
            parent = os.path.dirname(temp_path)
            if parent == temp_path:  # 已到达根目录
                break
            temp_path = parent
            
        # 逐级展开目录
        for part in parts:
            index = self.model.index(part)
            if index.isValid():
                self.tree_view.expand(index)
    
    def set_root_path(self, path):
        """设置根目录路径并展开到该路径"""
        self.root_path = path
        current_index = self.model.index(path)
        # 滚动到该位置并选中
        self.tree_view.scrollTo(current_index)
        self.tree_view.setCurrentIndex(current_index)
        # 展开该路径
        self.expand_to_path(path) 