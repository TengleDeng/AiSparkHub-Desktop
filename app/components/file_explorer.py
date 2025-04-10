#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTreeView, QHeaderView, 
                           QToolBar, QFileDialog, QPushButton, QHBoxLayout, 
                           QListWidget, QStackedWidget, QSplitter, QLabel,
                           QMenu, QTabWidget, QAbstractItemView)
from PyQt6.QtCore import Qt, QDir, QModelIndex, pyqtSignal, QSettings, QSize, QTimer, QUrl, QMimeData
from PyQt6.QtGui import QFileSystemModel, QIcon, QAction, QDrag
import os
import json

class DraggableTreeView(QTreeView):
    """支持拖动的树形视图"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # 设置拖放模式，启用拖动但禁用放置
        self.setDragEnabled(True)
        self.setAcceptDrops(False)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
        self.setDefaultDropAction(Qt.DropAction.CopyAction)
        
    def startDrag(self, supportedActions):
        """开始拖动操作"""
        # 获取所选项的索引
        indexes = self.selectedIndexes()
        if not indexes:
            return
            
        # 只处理文件名列（第一列）的拖动
        indexes = [index for index in indexes if index.column() == 0]
        if not indexes:
            return
            
        # 获取文件系统模型
        model = self.model()
        if not isinstance(model, QFileSystemModel):
            return
            
        # 准备MIME数据
        mime_data = QMimeData()
        
        # 获取文件的完整路径列表
        urls = []
        for index in indexes:
            file_path = model.filePath(index)
            if os.path.exists(file_path):
                urls.append(QUrl.fromLocalFile(file_path))
                
        # 设置URL列表（这是标准的拖放格式）
        if urls:
            mime_data.setUrls(urls)
            
            # 创建拖动对象
            drag = QDrag(self)
            drag.setMimeData(mime_data)
            
            # 执行拖动操作
            drag.exec(supportedActions)

class FileExplorer(QWidget):
    """文件浏览器组件"""
    
    # 添加文件打开请求信号，发送文件路径和文件类型
    fileOpenRequest = pyqtSignal(str, str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.root_paths = []
        self.settings = QSettings("AiSparkHub", "AiSparkHub-Desktop")
        
        # 定义支持查看的文件类型
        self.viewable_file_types = {
            '.html': 'html',
            '.htm': 'html',
            '.md': 'markdown',
            '.markdown': 'markdown',
            '.txt': 'text',
            '.docx': 'docx',
            '.doc': 'docx',
            '.pptx': 'powerpoint',
            '.ppt': 'powerpoint',
            '.xlsx': 'excel',
            '.xls': 'excel',
            '.pdf': 'pdf'
        }
        
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
        
        # 创建支持拖动的树形视图
        tree_view = DraggableTreeView()
        
        # 连接双击信号
        tree_view.doubleClicked.connect(self.on_item_double_clicked)
        
        # 添加到选项卡
        folder_name = os.path.basename(path) or path
        tab_index = self.tab_widget.addTab(tree_view, folder_name)
        self.tab_widget.setTabToolTip(tab_index, path)
        self.tab_widget.setCurrentIndex(tab_index)
        
        # 为树形视图添加右键菜单
        tree_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        tree_view.customContextMenuRequested.connect(
            lambda pos, tv=tree_view: self.show_context_menu(pos, tv))
        
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
    
    def on_item_double_clicked(self, index):
        """处理项目双击事件"""
        if not index.isValid():
            return
            
        model = self.get_file_system_model(index)
        file_path = self.get_file_path(index, model)
        
        if not file_path or not os.path.exists(file_path):
            return
            
        # 如果是文件，检查是否为可查看的文件类型
        if os.path.isfile(file_path):
            # 获取文件扩展名
            _, ext = os.path.splitext(file_path.lower())
            
            # 检查是否为可查看的文件类型
            if ext in self.viewable_file_types:
                file_type = self.viewable_file_types[ext]
                # 发送文件打开请求信号
                self.fileOpenRequest.emit(file_path, file_type)
                
    def get_file_system_model(self, index):
        """获取文件系统模型，处理代理模型的情况"""
        model = index.model()
        if not model:
            return None
            
        # 如果是代理模型，获取源模型
        if hasattr(model, 'sourceModel'):
            return model.sourceModel()
        return model
        
    def get_file_path(self, index, model):
        """获取文件路径，处理代理模型的情况"""
        if not model or not isinstance(model, QFileSystemModel):
            return None
            
        # 如果是代理模型的索引，需要映射到源模型
        source_index = index
        if hasattr(index.model(), 'mapToSource'):
            source_index = index.model().mapToSource(index)
            
        return model.filePath(source_index)
    
    def show_context_menu(self, position, tree_view):
        """显示右键菜单"""
        index = tree_view.indexAt(position)
        if not index.isValid():
            return
            
        model = self.get_file_system_model(index)
        file_path = self.get_file_path(index, model)
        
        if not file_path or not os.path.exists(file_path):
            return
            
        menu = QMenu()
        
        # 对于可查看的文件类型，添加"查看文件"选项
        if os.path.isfile(file_path):
            _, ext = os.path.splitext(file_path.lower())
            if ext in self.viewable_file_types:
                view_action = menu.addAction("查看文件")
                file_type = self.viewable_file_types[ext]
                view_action.triggered.connect(
                    lambda checked=False, path=file_path, type=file_type: 
                    self.fileOpenRequest.emit(path, type))
                menu.addSeparator()
        
        # 添加"在资源管理器中显示"选项
        show_action = menu.addAction("在文件资源管理器中显示")
        show_action.triggered.connect(lambda: self.open_in_explorer(file_path))
        
        if menu.actions():
            menu.exec(tree_view.viewport().mapToGlobal(position))
    
    def open_in_explorer(self, path):
        """在系统文件管理器中打开指定路径"""
        import subprocess
        import platform
        
        if platform.system() == "Windows":
            # Windows系统
            if os.path.isfile(path):
                # 如果是文件，打开所在文件夹并选中该文件
                subprocess.run(['explorer', '/select,', path])
            else:
                # 如果是文件夹，直接打开
                subprocess.run(['explorer', path])
        elif platform.system() == "Darwin":
            # macOS系统
            subprocess.run(['open', '-R', path])
        else:
            # Linux系统，尝试使用xdg-open
            try:
                if os.path.isfile(path):
                    subprocess.run(['xdg-open', os.path.dirname(path)])
                else:
                    subprocess.run(['xdg-open', path])
            except FileNotFoundError:
                pass
    
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