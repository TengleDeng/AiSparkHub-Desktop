#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTreeView, QHeaderView, 
                           QToolBar, QFileDialog, QPushButton, QHBoxLayout, 
                           QListWidget, QStackedWidget, QSplitter, QLabel,
                           QMenu, QTabWidget)
from PyQt6.QtCore import Qt, QDir, QModelIndex, pyqtSignal, QSettings, QSize, QTimer
from PyQt6.QtGui import QFileSystemModel, QIcon, QAction
import os
import json

class FileExplorer(QWidget):
    """文件浏览器组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.root_paths = []
        self.settings = QSettings("AiSparkHub", "AiSparkHub-Desktop")
        self.load_settings()
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI界面"""
        # 创建布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 创建工具栏
        self.toolbar = QToolBar()
        self.toolbar.setIconSize(QSize(16, 16))
        self.toolbar.setMovable(False)
        
        # 添加工具栏按钮
        self.add_folder_action = QAction(QIcon.fromTheme("folder-new", QIcon(":/icons/folder-add.png")), "添加文件夹", self)
        self.add_folder_action.triggered.connect(self.add_folder)
        self.toolbar.addAction(self.add_folder_action)
        
        main_layout.addWidget(self.toolbar)
        
        # 创建选项卡控件，每个文件夹一个选项卡
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.remove_tab)
        self.tab_widget.setDocumentMode(True)
        self.tab_widget.setMovable(True)
        main_layout.addWidget(self.tab_widget)
        
        # 如果没有保存的目录，默认添加当前工作目录
        if not self.root_paths:
            self.root_paths.append(os.path.normpath(os.getcwd()))
        
        # 使用简单延迟加载，避免启动时阻塞界面
        QTimer.singleShot(100, self.init_tabs)
        
        # 设置样式
        self.setStyleSheet("""
            QToolBar {
                background-color: #2E3440;
                border: none;
                spacing: 4px;
                padding: 4px;
            }
            QToolBar QToolButton {
                background-color: #3B4252;
                border: none;
                border-radius: 4px;
                color: #D8DEE9;
                padding: 4px;
            }
            QToolBar QToolButton:hover {
                background-color: #4C566A;
            }
            QTabWidget::pane {
                border: none;
                background-color: #2E3440;
            }
            QTabBar::tab {
                background-color: #3B4252;
                color: #D8DEE9;
                padding: 5px 10px;
                border: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #4C566A;
                color: #ECEFF4;
            }
            QTabBar::tab:hover:!selected {
                background-color: #434C5E;
            }
            QTabBar::close-button {
                image: url(:/icons/close.png);
                subcontrol-position: right;
            }
            QTabBar::close-button:hover {
                background-color: #BF616A;
                border-radius: 2px;
            }
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
        """)
    
    def init_tabs(self):
        """初始化所有文件夹选项卡"""
        for i, path in enumerate(self.root_paths):
            # 每个选项卡之间间隔200毫秒加载，避免同时加载多个文件夹
            QTimer.singleShot(i * 200, lambda p=path: self.add_folder_tab(p))
    
    def add_folder_tab(self, path):
        """为指定路径添加一个选项卡"""
        if not os.path.exists(path):
            return False
        
        # 创建树形视图
        tree_view = QTreeView()
        
        # 添加到选项卡
        folder_name = os.path.basename(path) or path
        tab_index = self.tab_widget.addTab(tree_view, folder_name)
        self.tab_widget.setTabToolTip(tab_index, path)
        self.tab_widget.setCurrentIndex(tab_index)
        
        # 延迟加载文件系统模型，避免界面卡住
        QTimer.singleShot(50, lambda: self.setup_model(tree_view, path))
        
        return True
    
    def setup_model(self, tree_view, path):
        """设置树形视图的文件系统模型"""
        # 创建文件系统模型
        model = QFileSystemModel()
        # 减少文件系统监视以提高性能
        model.setOption(QFileSystemModel.Option.DontWatchForChanges, True)
        model.setRootPath(path)
        model.setFilter(QDir.AllEntries | QDir.NoDotAndDotDot)
        
        # 设置视图的模型
        tree_view.setModel(model)
        tree_view.setRootIndex(model.index(path))
        
        # 设置视图属性
        tree_view.setAnimated(True)
        tree_view.setIndentation(20)
        tree_view.setSortingEnabled(True)
        tree_view.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        
        # 隐藏不必要的列
        tree_view.setHeaderHidden(True)
        for i in range(1, model.columnCount()):
            tree_view.hideColumn(i)
    
    def add_folder(self):
        """添加新文件夹到浏览器"""
        folder_path = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder_path:
            # 规范化路径
            folder_path = os.path.normpath(folder_path)
            
            # 检查是否已存在该文件夹
            if folder_path not in self.root_paths:
                if self.add_folder_tab(folder_path):
                    self.root_paths.append(folder_path)
                    self.save_settings()
    
    def remove_tab(self, index):
        """移除指定的选项卡"""
        # 获取该选项卡对应的路径
        path = self.tab_widget.tabToolTip(index)
        
        # 从选项卡栏移除
        self.tab_widget.removeTab(index)
        
        # 从根路径列表中移除
        if path in self.root_paths:
            self.root_paths.remove(path)
            
        # 保存设置
        self.save_settings()
        
        # 如果没有任何选项卡，恢复默认行为
        if self.tab_widget.count() == 0 and os.path.exists(os.getcwd()):
            self.root_paths.append(os.getcwd())
            self.add_folder_tab(os.getcwd())
            self.save_settings()
    
    def load_settings(self):
        """加载保存的根目录列表"""
        saved_paths = self.settings.value("file_explorer/root_paths")
        if saved_paths:
            # 过滤出有效的路径
            self.root_paths = [path for path in saved_paths if os.path.exists(path)]
    
    def save_settings(self):
        """保存根目录列表"""
        self.settings.setValue("file_explorer/root_paths", self.root_paths) 