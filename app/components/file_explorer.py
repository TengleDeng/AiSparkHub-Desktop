#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTreeView, QHeaderView, 
                           QToolBar, QFileDialog, QPushButton, QHBoxLayout, 
                           QListWidget, QStackedWidget, QSplitter, QLabel,
                           QMenu, QTabWidget, QAbstractItemView, QScrollBar, QFrame, QSizePolicy)
from PyQt6.QtCore import Qt, QDir, QModelIndex, pyqtSignal, QSettings, QSize, QTimer, QUrl, QMimeData
from PyQt6.QtGui import QFileSystemModel, QIcon, QAction, QDrag
import qtawesome as qta
import os
import json
from PyQt6.QtWidgets import QApplication
from app.controllers.theme_manager import ThemeManager

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
        
        # 定义支持编辑的文件类型
        self.editable_file_types = ['.md', '.markdown', '.txt']
        
        # 初始化UI组件变量
        self.bottom_toolbar = None
        self.settings_action = None
        self.plus_tab_index = -1
        
        self.load_settings()
        self.setup_ui()
        
        # 获取 ThemeManager 并连接信号
        self.theme_manager = None
        app = QApplication.instance()
        if hasattr(app, 'theme_manager') and isinstance(app.theme_manager, ThemeManager):
            self.theme_manager = app.theme_manager
            self.theme_manager.theme_changed.connect(self._update_icons)
            # 初始化时调用一次图标检查以设置颜色
            QTimer.singleShot(200, lambda: self._check_tab_close_buttons(-1))
            # 初始化工具栏图标
            QTimer.singleShot(200, self._update_toolbar_icons)
        else:
            print("警告：无法在 FileExplorer 中获取 ThemeManager 实例")
            QTimer.singleShot(200, lambda: self._check_tab_close_buttons(-1)) # 即使没有Manager也尝试用默认色设置
            QTimer.singleShot(200, self._update_toolbar_icons) # 同样初始化工具栏图标
        
        # 在theme_manager设置后更新文件夹按钮图标
        QTimer.singleShot(200, self._update_add_folder_icon)
            
    def setup_ui(self):
        """设置UI界面"""
        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 创建选项卡控件，每个文件夹一个选项卡
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.remove_tab)
        self.tab_widget.setDocumentMode(True)
        self.tab_widget.setMovable(True)
        
        # 设置标签页高度
        self.tab_widget.setStyleSheet("QTabBar::tab { height: 30px; }")
        
        main_layout.addWidget(self.tab_widget, 1)  # 让标签页占据更多空间
        
        # 创建底部工具栏
        self.bottom_toolbar = QToolBar()
        self.bottom_toolbar.setIconSize(QSize(16, 16))
        self.bottom_toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.bottom_toolbar.setMovable(False)
        
        # 添加设置按钮
        self.settings_action = QAction(qta.icon('fa5s.cog'), "设置", self)
        self.settings_action.setToolTip("文件浏览器设置")
        self.settings_action.triggered.connect(self.show_settings)
        self.bottom_toolbar.addAction(self.settings_action)
        
        # 添加空白间隔填充工具栏右侧
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.bottom_toolbar.addWidget(spacer)
        
        # 添加底部工具栏到主布局
        main_layout.addWidget(self.bottom_toolbar)
        
        # 如果没有保存的目录，默认添加当前工作目录
        if not self.root_paths:
            self.root_paths.append(os.path.normpath(os.getcwd()))
        
        # 使用简单延迟加载，避免启动时阻塞界面
        QTimer.singleShot(100, self.init_tabs)
        
        # 监听标签页添加事件，为新标签页设置关闭图标
        self.tab_widget.tabBarClicked.connect(self._check_tab_close_buttons)
        self.tab_widget.currentChanged.connect(self._check_tab_close_buttons)
        
        # 监听标签页切换事件
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        
        # 记录当前是否有"+"标签页
        self.plus_tab_index = -1
    
    def _check_tab_close_buttons(self, index):
        """检查并设置标签页关闭按钮图标"""
        # 为标签页设置qtawesome图标
        icon_color = '#D8DEE9' # Default color
        if self.theme_manager:
            theme_colors = self.theme_manager.get_current_theme_colors()
            icon_color = theme_colors.get('foreground', icon_color)
            
        close_icon = qta.icon('fa5s.times', color=icon_color)
        
        # 遍历所有标签页，检查是否有未设置图标的关闭按钮
        for i in range(self.tab_widget.count()):
            close_button = self.tab_widget.tabBar().tabButton(i, self.tab_widget.tabBar().ButtonPosition.RightSide)
            if close_button and close_button.icon().isNull():
                close_button.setIcon(close_icon)
                close_button.setText("")  # 移除文本，只显示图标
                close_button.setIconSize(QSize(12, 12))  # 设置合适的图标大小
    
    def init_tabs(self):
        """初始化所有文件夹选项卡"""
        for i, path in enumerate(self.root_paths):
            # 每个选项卡之间间隔200毫秒加载，避免同时加载多个文件夹
            QTimer.singleShot(i * 200, lambda p=path: self.add_folder_tab(p))
            
        # 添加"+"标签页
        QTimer.singleShot((len(self.root_paths) + 1) * 200, self.add_plus_tab)
    
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
                # 如果有"+"标签页，先移除它
                if self.plus_tab_index >= 0:
                    self.tab_widget.removeTab(self.plus_tab_index)
                    self.plus_tab_index = -1
                
                # 添加新文件夹标签页
                if self.add_folder_tab(folder_path):
                    self.root_paths.append(folder_path)
                    self.save_settings()
                    
                # 重新添加"+"标签页
                self.add_plus_tab()
    
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
                
                # 对于可编辑的文件类型，添加"编辑文件"选项
                if ext in self.editable_file_types:
                    edit_action = menu.addAction("编辑文件")
                    edit_action.triggered.connect(
                        lambda checked=False, path=file_path, type=file_type: 
                        self.fileOpenRequest.emit(path, type + ":edit"))
                
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
        # 如果要移除的是"+"标签页，不执行任何操作
        if index == self.plus_tab_index:
            return
            
        # 获取该选项卡对应的路径
        path = self.tab_widget.tabToolTip(index)
        
        # 调整plus_tab_index，如果被删除的标签在"+"标签页之前
        if self.plus_tab_index > index:
            self.plus_tab_index -= 1
        
        # 从选项卡栏移除
        self.tab_widget.removeTab(index)
        
        # 从根路径列表中移除
        if path in self.root_paths:
            self.root_paths.remove(path)
            
        # 保存设置
        self.save_settings()
        
        # 如果没有任何常规标签页，恢复默认行为
        if self.tab_widget.count() == 1 and self.plus_tab_index == 0:  # 只剩下"+"标签页
            self.root_paths.append(os.getcwd())
            
            # 移除"+"标签页后再添加文件夹标签页
            self.tab_widget.removeTab(0)
            self.plus_tab_index = -1
            
            self.add_folder_tab(os.getcwd())
            self.save_settings()
            
            # 重新添加"+"标签页
            self.add_plus_tab()
    
    def load_settings(self):
        """加载保存的根目录列表"""
        saved_paths = self.settings.value("file_explorer/root_paths")
        if saved_paths:
            # 过滤出有效的路径
            self.root_paths = [path for path in saved_paths if os.path.exists(path)]
    
    def save_settings(self):
        """保存根目录列表"""
        self.settings.setValue("file_explorer/root_paths", self.root_paths)
    
    # 新增方法：更新图标颜色以响应主题变化
    def _update_icons(self):
        """更新所有图标颜色以响应主题变化"""
        print("FileExplorer: 接收到主题变化信号，正在更新图标...")
        # 更新添加文件夹按钮的图标
        self._update_add_folder_icon()
        # 重新检查所有标签页关闭按钮的图标颜色
        self._check_tab_close_buttons(-1)
        # 更新底部工具栏图标
        self._update_toolbar_icons()
        
    def _update_add_folder_icon(self):
        """更新添加文件夹按钮的图标，包含防御性检查"""
        # 由于我们已移除添加文件夹按钮，此方法仅作为兼容保留
        print("FileExplorer: 添加文件夹按钮已被移除，不需要更新图标")
        return 

    def _update_toolbar_icons(self):
        """更新底部工具栏的图标和样式"""
        if not hasattr(self, 'bottom_toolbar') or not self.bottom_toolbar:
            return
            
        # 获取当前主题的颜色
        icon_color = '#D8DEE9'  # 默认颜色
        toolbar_bg = '#3B4252'  # 默认背景色
        toolbar_hover_bg = '#4C566A'  # 默认悬停背景色
        
        if self.theme_manager:
            theme_colors = self.theme_manager.get_current_theme_colors()
            icon_color = theme_colors.get('foreground', icon_color)
            toolbar_bg = theme_colors.get('secondary_bg', toolbar_bg)
            toolbar_hover_bg = theme_colors.get('tertiary_bg', toolbar_hover_bg)
        
        # 更新设置按钮图标
        if hasattr(self, 'settings_action') and self.settings_action:
            self.settings_action.setIcon(qta.icon('fa5s.cog', color=icon_color))
        
        # 更新工具栏样式
        self.bottom_toolbar.setStyleSheet(f"""
            QToolBar {{
                background-color: {toolbar_bg};
                border: none;
                spacing: 5px;
                padding: 2px;
            }}
            QToolButton {{
                background-color: transparent;
                border: none;
                border-radius: 4px;
                padding: 5px;
                color: {icon_color};
            }}
            QToolButton:hover {{
                background-color: {toolbar_hover_bg};
            }}
        """)

    def add_plus_tab(self):
        """添加"+"标签页用于添加新文件夹"""
        # 创建空白Widget用于"+"标签页
        empty_widget = QWidget()
        
        # 添加"+"标签页
        self.plus_tab_index = self.tab_widget.addTab(empty_widget, "+")
        
        # 设置标签页不可关闭
        self.tab_widget.tabBar().setTabButton(self.plus_tab_index, self.tab_widget.tabBar().ButtonPosition.RightSide, None)
        
        # 设置工具提示
        self.tab_widget.setTabToolTip(self.plus_tab_index, "添加新文件夹")
        
    def on_tab_changed(self, index):
        """处理标签页切换事件"""
        # 如果点击的是"+"标签页
        if index == self.plus_tab_index:
            # 打开文件夹选择对话框
            self.add_folder()
            
            # 如果之前选中了其他标签页，切换回去
            if self.tab_widget.count() > 1:
                # 选中上一个标签页（不是"+"标签页）
                self.tab_widget.setCurrentIndex(self.plus_tab_index - 1)
                
    def show_settings(self):
        """显示文件浏览器设置对话框"""
        # 目前仅显示一个消息，后续可实现具体的设置功能
        print("显示文件浏览器设置对话框")
        # TODO: 实现设置对话框 