#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTreeView, QHeaderView, 
                           QToolBar, QFileDialog, QPushButton, QHBoxLayout, 
                           QListWidget, QStackedWidget, QSplitter, QLabel,
                           QMenu, QTabWidget, QAbstractItemView, QScrollBar, QFrame, QSizePolicy,
                           QMessageBox, QTableWidget, QTableWidgetItem, QGroupBox, QDialog, QCheckBox, QTextEdit,
                           QProgressBar, QLineEdit, QGridLayout)
from PyQt6.QtCore import Qt, QDir, QModelIndex, pyqtSignal, QSettings, QSize, QTimer, QUrl, QMimeData, QThread
from PyQt6.QtGui import QFileSystemModel, QIcon, QAction, QDrag, QColor
import qtawesome as qta
import os
import json
from PyQt6.QtWidgets import QApplication
from app.controllers.theme_manager import ThemeManager
import sqlite3
from app.models.database import DatabaseManager

# 文件扫描线程
class ScanThread(QThread):
    scan_complete = pyqtSignal(dict)
    progress_update = pyqtSignal(int, int)  # 当前进度、总数
    
    def __init__(self, pkm_folders=None):
        super().__init__()
        # 接收单个文件夹或文件夹列表
        if isinstance(pkm_folders, str):
            self.pkm_folders = [pkm_folders]
        elif isinstance(pkm_folders, list):
            self.pkm_folders = pkm_folders
        else:
            self.pkm_folders = []
        
    def run(self):
        # 在线程内创建新的数据库管理器实例
        db_manager = DatabaseManager()
        
        # 设置进度回调函数
        def progress_callback(stats_data):
            # 新版本回调接收一个包含完整统计信息的字典
            if isinstance(stats_data, dict):
                current = stats_data.get('progress', 0)
                total = 100  # 进度总是相对于100%
                
                # 保存当前正在扫描的文件名（如果有）
                if 'current_file' in stats_data:
                    self._current_scanning_file = stats_data['current_file']
                
                # 发送进度更新信号
                self.progress_update.emit(current, total)
                
                # 如果已完成，发送完成信号
                if current >= 100 or 'summary' in stats_data:
                    self.scan_complete.emit(stats_data)
            elif isinstance(stats_data, tuple) and len(stats_data) == 2:
                # 兼容旧版本回调
                self.progress_update.emit(stats_data[0], stats_data[1])
                
        # 执行数据库扫描
        result = db_manager.scan_pkm_folder(callback=progress_callback)
        
        # 确保扫描完成信号被发送（如果回调中没有发送）
        if not isinstance(result, dict) or 'progress' not in result or result['progress'] < 100:
            self.scan_complete.emit(result)

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
        self.pkm_db_action = None
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
        
        # 添加PKM数据库按钮
        self.pkm_db_action = QAction(qta.icon('fa5s.brain'), "PKM数据库", self)
        self.pkm_db_action.setToolTip("PKM文件数据库")
        self.pkm_db_action.triggered.connect(self.show_pkm_database)
        self.bottom_toolbar.addAction(self.pkm_db_action)
        
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
        # 允许监视文件系统变化，以便自动更新视图
        # model.setOption(QFileSystemModel.Option.DontWatchForChanges, True)
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
            
        # 保存model引用到tree_view中，以便后续访问
        tree_view.setProperty("file_model", model)
    
    def refresh_current_view(self):
        """刷新当前活动的文件视图"""
        if self.tab_widget.count() == 0 or self.tab_widget.currentIndex() == self.plus_tab_index:
            return
            
        current_tree_view = self.tab_widget.currentWidget()
        if not isinstance(current_tree_view, QTreeView):
            return
            
        # 获取模型并刷新
        model = current_tree_view.model()
        if isinstance(model, QFileSystemModel):
            current_path = model.rootPath()
            model.setRootPath("")  # 重置路径
            model.setRootPath(current_path)  # 重新设置路径，触发刷新
            print(f"已刷新文件视图: {current_path}")

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
        
        # 添加"使用默认应用打开"选项
        open_action = menu.addAction("使用默认应用打开")
        open_action.triggered.connect(lambda: self.open_with_default_app(file_path))
        
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
        show_action = menu.addAction("在系统资源管理器中显示")
        show_action.triggered.connect(lambda: self.open_in_explorer(file_path))
        
        # 添加"重命名"选项
        rename_action = menu.addAction("重命名")
        rename_action.triggered.connect(lambda: self.rename_file(file_path, tree_view, index))
        
        # 添加"删除"选项
        delete_action = menu.addAction("删除")
        delete_action.triggered.connect(lambda: self.delete_file(file_path))
        
        if menu.actions():
            menu.exec(tree_view.viewport().mapToGlobal(position))
    
    def open_with_default_app(self, path):
        """使用系统默认应用打开文件"""
        import subprocess
        import platform
        
        try:
            if platform.system() == "Windows":
                os.startfile(path)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(['open', path])
            else:  # Linux
                subprocess.run(['xdg-open', path])
                
            print(f"已使用默认应用打开: {path}")
        except Exception as e:
            print(f"无法打开文件: {str(e)}")
            QMessageBox.warning(self, "打开失败", f"无法使用默认应用打开文件: {str(e)}")
            
    def open_in_explorer(self, path):
        """在系统文件管理器中打开指定路径"""
        import subprocess
        import platform
        
        try:
            path = os.path.normpath(path)  # 规范化路径
            print(f"尝试在文件资源管理器中打开: {path}")
            
            if platform.system() == "Windows":
                # Windows系统
                if os.path.isfile(path):
                    # 如果是文件，打开所在文件夹并选中该文件
                    # 注意这里/select,后面不应该有空格，且路径需要完整的字符串形式
                    subprocess.Popen(f'explorer /select,"{path}"')
                else:
                    # 如果是文件夹，直接打开
                    subprocess.Popen(f'explorer "{path}"')
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
        except Exception as e:
            print(f"打开文件资源管理器失败: {e}")
            QMessageBox.warning(self, "错误", f"无法在文件资源管理器中显示: {str(e)}")
    
    def rename_file(self, file_path, tree_view, index):
        """重命名文件或文件夹"""
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "错误", "文件或文件夹不存在")
            return
            
        # 获取文件名和路径
        file_name = os.path.basename(file_path)
        dir_path = os.path.dirname(file_path)
        
        # 弹出重命名对话框
        from PyQt6.QtWidgets import QInputDialog
        new_name, ok = QInputDialog.getText(
            self, "重命名", "请输入新名称:", text=file_name
        )
        
        if ok and new_name and new_name != file_name:
            new_path = os.path.join(dir_path, new_name)
            
            # 检查新名称的文件是否已存在
            if os.path.exists(new_path):
                QMessageBox.warning(self, "错误", f"文件 '{new_name}' 已存在")
                return
                
            try:
                # 重命名文件
                os.rename(file_path, new_path)
                
                # 刷新视图
                model = tree_view.model()
                if isinstance(model, QFileSystemModel):
                    # 强制刷新当前目录
                    parent_dir = os.path.dirname(file_path)
                    model.setRootPath("")
                    model.setRootPath(model.rootPath())
                    
                    # 获取父目录的索引并刷新
                    parent_index = model.index(parent_dir)
                    if parent_index.isValid():
                        # 通知模型数据已更改
                        model.directoryLoaded.emit(parent_dir)
                
                print(f"已重命名: {file_path} -> {new_path}")
            except Exception as e:
                QMessageBox.warning(self, "重命名失败", f"无法重命名文件: {str(e)}")
                
    def delete_file(self, file_path):
        """删除文件或文件夹"""
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "错误", "文件或文件夹不存在")
            return
            
        # 确认对话框
        msg_text = "文件夹" if os.path.isdir(file_path) else "文件"
        reply = QMessageBox.question(
            self, "确认删除", 
            f"确定要删除此{msg_text}吗?\n{os.path.basename(file_path)}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # 保存父目录路径以便之后刷新
                parent_dir = os.path.dirname(file_path)
                
                if os.path.isdir(file_path):
                    import shutil
                    shutil.rmtree(file_path)
                else:
                    os.remove(file_path)
                
                # 刷新当前视图
                self.refresh_current_view()
                
                print(f"已删除: {file_path}")
            except Exception as e:
                QMessageBox.warning(self, "删除失败", f"无法删除{msg_text}: {str(e)}")
    
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
        """更新工具栏图标"""
        # 获取当前主题的颜色
        icon_color = '#D8DEE9'  # 默认颜色
        toolbar_bg = '#3B4252'  # 默认背景色
        toolbar_hover_bg = '#4C566A'  # 默认悬停背景色
        
        if self.theme_manager:
            theme_colors = self.theme_manager.get_current_theme_colors()
            icon_color = theme_colors.get('foreground', icon_color)
            toolbar_bg = theme_colors.get('secondary_bg', toolbar_bg)
            toolbar_hover_bg = theme_colors.get('tertiary_bg', toolbar_hover_bg)
        
        # 更新PKM数据库按钮图标
        if hasattr(self, 'pkm_db_action') and self.pkm_db_action:
            self.pkm_db_action.setIcon(qta.icon('fa5s.brain', color=icon_color))
        
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
                
    def show_pkm_database(self):
        """显示PKM数据库设置和管理界面"""
        try:
            # 创建设置对话框
            dialog = QDialog(self)
            dialog.setWindowTitle("PKM数据库设置")
            dialog.resize(800, 600)  # 降低初始高度
            
            # 创建对话框布局
            layout = QVBoxLayout(dialog)
            layout.setSpacing(10)  # 减少垂直间距
            
            # 创建数据库管理器实例
            db_manager = DatabaseManager()
            
            # ======== 文件夹设置部分 ========
            folder_group = QGroupBox("文件夹设置")
            folder_layout = QVBoxLayout()
            folder_layout.setSpacing(5)  # 减少内部间距
            
            # 添加文件夹列表标签和监控开关到同一行
            folder_header_layout = QHBoxLayout()
            folder_header_layout.addWidget(QLabel("监控文件夹列表:"))
            
            # 添加监控开关
            monitor_checkbox = QCheckBox("启用实时文件监控")
            monitor_checkbox.setChecked(True)  # 默认启用
            monitor_checkbox.setToolTip("启用后，会自动监控文件变化并更新数据库")
            # 连接监控开关信号
            monitor_checkbox.stateChanged.connect(
                lambda state: self._toggle_file_monitoring(state, db_manager, status_text)
            )
            folder_header_layout.addWidget(monitor_checkbox)
            
            # 添加空白间隔，确保两个元素分散在两端
            folder_header_layout.addStretch(1)
            
            folder_layout.addLayout(folder_header_layout)
            
            # 创建文件夹列表控件
            folders_list = QListWidget()
            folders_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
            folders_list.setAlternatingRowColors(True)
            
            # 填充现有文件夹列表
            if db_manager.pkm_folders:
                for folder in db_manager.pkm_folders:
                    folders_list.addItem(folder)
            
            # 动态计算理想高度 - 每行25像素，最小高度80，最大高度150
            folder_count = folders_list.count() or 1  # 至少1行的高度
            ideal_height = min(max(folder_count * 25 + 10, 80), 150)
            folders_list.setFixedHeight(ideal_height)
            
            folder_layout.addWidget(folders_list)
            
            # 添加文件夹操作按钮组
            folder_btns_layout = QHBoxLayout()
            
            # 添加文件夹按钮
            add_folder_btn = QPushButton("添加文件夹")
            add_folder_btn.clicked.connect(lambda: self._add_pkm_folder(folders_list, db_manager))
            folder_btns_layout.addWidget(add_folder_btn)
            
            # 移除文件夹按钮
            remove_folder_btn = QPushButton("移除文件夹")
            remove_folder_btn.clicked.connect(lambda: self._remove_pkm_folder(folders_list, db_manager))
            folder_btns_layout.addWidget(remove_folder_btn)
            
            folder_layout.addLayout(folder_btns_layout)
            folder_group.setLayout(folder_layout)
            layout.addWidget(folder_group)
            
            # ======== 文件统计表格 ========
            stats_group = QGroupBox("文件统计")
            stats_layout = QVBoxLayout()
            stats_layout.setSpacing(5)  # 减少内部间距
            
            # 创建统计表格
            stats_table = QTableWidget()
            stats_table.setColumnCount(4)  # 文件夹, 文件类型, 文件系统数量, 数据库数量
            stats_table.setHorizontalHeaderLabels(["文件夹", "文件类型", "文件系统数量", "数据库数量"])
            stats_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            stats_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
            stats_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
            stats_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
            stats_table.setAlternatingRowColors(True)
            stats_table.setFixedHeight(150)  # 固定高度
            
            stats_layout.addWidget(stats_table)
            
            # 添加刷新按钮
            refresh_stats_btn = QPushButton("刷新统计")
            refresh_stats_btn.clicked.connect(
                lambda: self._refresh_file_stats(stats_table, db_manager)
            )
            stats_layout.addWidget(refresh_stats_btn)
            
            stats_group.setLayout(stats_layout)
            layout.addWidget(stats_group)
            
            # 初始加载统计数据
            # self._refresh_file_stats(stats_table, db_manager)  # 移除立即加载
            
            # 显示正在加载的提示
            loading_row = stats_table.rowCount()
            stats_table.insertRow(loading_row)
            loading_item = QTableWidgetItem("正在加载统计数据...")
            loading_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            stats_table.setSpan(loading_row, 0, 1, 4)  # 合并单元格
            stats_table.setItem(loading_row, 0, loading_item)
            
            # 使用QTimer延迟加载统计数据，让UI先打开
            QTimer.singleShot(100, lambda: self._delayed_load_stats(stats_table, db_manager))
            
            # ======== 文件格式设置部分 ========
            format_group = QGroupBox("文件格式设置")
            format_layout = QGridLayout()  # 使用网格布局
            format_layout.setSpacing(5)    # 减少间距
            
            # 创建文件格式复选框
            format_checkboxes = {}
            
            if hasattr(db_manager, 'supported_file_formats'):
                row, col = 0, 0
                max_cols = 3  # 每行显示3个选项
                
                for format_name, format_config in db_manager.supported_file_formats.items():
                    checkbox = QCheckBox(f"{format_config['description']} ({', '.join(format_config['extensions'])})")
                    checkbox.setChecked(format_config['enabled'])
                    format_checkboxes[format_name] = checkbox
                    
                    format_layout.addWidget(checkbox, row, col)
                    col += 1
                    if col >= max_cols:
                        col = 0
                        row += 1
            
            format_group.setLayout(format_layout)
            format_group.setMaximumHeight(120)  # 限制最大高度
            layout.addWidget(format_group)
            
            # ======== 扫描和操作部分 ========
            operation_group = QGroupBox("操作")
            operation_layout = QVBoxLayout()
            operation_layout.setSpacing(5)  # 减少间距
            
            # 添加扫描按钮和状态显示
            scan_layout = QHBoxLayout()
            scan_button = QPushButton("扫描文件夹")
            scan_button.clicked.connect(lambda: self._scan_pkm_folder(db_manager, status_text, progress_bar, scan_button, lambda: self._refresh_file_stats(stats_table, db_manager)))
            scan_layout.addWidget(scan_button)
            
            progress_bar = QProgressBar()
            progress_bar.setTextVisible(True)
            progress_bar.setRange(0, 100)
            progress_bar.setValue(0)
            scan_layout.addWidget(progress_bar)
            
            operation_layout.addLayout(scan_layout)
            
            operation_group.setLayout(operation_layout)
            layout.addWidget(operation_group)
            
            # 添加状态文本显示区域
            status_text = QTextEdit()
            status_text.setReadOnly(True)
            status_text.setPlaceholderText("操作结果将显示在这里...")
            status_text.setFixedHeight(100)  # 限制高度
            layout.addWidget(status_text)
            
            # 连接文件监控器的信号到状态显示
            if hasattr(db_manager, 'file_watcher'):
                # 先确保数据库处理函数连接正常
                if hasattr(db_manager.file_watcher, 'reconnect_signals'):
                    db_manager.file_watcher.reconnect_signals()
                
                # 连接UI信号 - 这些连接只在对话框打开时有效，关闭时会断开
                db_manager.file_watcher.file_added.connect(
                    lambda path: self._handle_file_change(path, "添加", status_text, lambda: self._refresh_file_stats(stats_table, db_manager))
                )
                db_manager.file_watcher.file_modified.connect(
                    lambda path: self._handle_file_change(path, "更新", status_text, None)
                )
                db_manager.file_watcher.file_deleted.connect(
                    lambda path: self._handle_file_change(path, "删除", status_text, lambda: self._refresh_file_stats(stats_table, db_manager))
                )
                db_manager.file_watcher.scan_completed.connect(
                    lambda result: self._handle_scan_result(result, status_text, progress_bar, scan_button, lambda: self._refresh_file_stats(stats_table, db_manager))
                )
            
            # ======== 底部按钮部分 ========
            buttons_layout = QHBoxLayout()
            
            # 添加保存按钮
            save_button = QPushButton("保存设置")
            save_button.clicked.connect(lambda: self._save_pkm_settings(folders_list, format_checkboxes, db_manager, dialog))
            buttons_layout.addWidget(save_button)
            
            # 添加关闭按钮
            close_button = QPushButton("关闭")
            close_button.clicked.connect(dialog.accept)
            buttons_layout.addWidget(close_button)
            
            layout.addLayout(buttons_layout)
            
            # 定义对话框关闭处理
            def on_dialog_closed():
                # 停止任何正在运行的扫描线程
                if hasattr(self, 'scan_thread') and self.scan_thread.isRunning():
                    self.scan_thread.terminate()
                    self.scan_thread.wait()
                    print("对话框关闭，扫描线程已终止")
                
                # 断开所有连接到UI组件的信号
                if hasattr(db_manager, 'file_watcher'):
                    try:
                        # 断开所有连接到UI组件的信号
                        try:
                            # 断开UI更新相关的所有信号连接
                            db_manager.file_watcher.file_added.disconnect()
                            db_manager.file_watcher.file_modified.disconnect()
                            db_manager.file_watcher.file_deleted.disconnect()
                            db_manager.file_watcher.scan_completed.disconnect()
                            print("已断开所有UI信号连接")
                        except (TypeError, RuntimeError):
                            # 如果信号未连接或已断开，忽略错误
                            pass
                            
                        # 确保数据库操作函数在关闭UI后仍然连接
                        # 注意：现在我们需要重新连接数据库处理函数，因为我们断开了所有信号
                        if hasattr(db_manager.file_watcher, 'reconnect_signals'):
                            db_manager.file_watcher.reconnect_signals()
                            print("已重新连接数据库处理函数")
                    except Exception as e:
                        # 捕获所有可能的异常
                        print(f"对话框关闭时处理信号连接出错: {e}")
            
            # 连接对话框关闭信号
            dialog.finished.connect(on_dialog_closed)
            
            # 显示对话框
            dialog.exec()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开PKM数据库设置出错: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def _refresh_file_stats(self, table, db_manager):
        """刷新文件统计表格数据"""
        try:
            # 导入必要的模块
            from PyQt6.QtCore import Qt
            from PyQt6.QtGui import QColor
            import sqlite3
            
            # 清空表格
            table.setRowCount(0)
            
            # 设置表格列宽
            table.setColumnWidth(0, 300)  # 文件夹列宽度限制
            table.setColumnWidth(1, 100)  # 文件类型宽度
            table.setColumnWidth(2, 100)  # 文件系统数量
            table.setColumnWidth(3, 100)  # 数据库数量
            
            # 检查是否有文件夹
            if not db_manager.pkm_folders:
                return
            
            # 获取每个文件夹中的文件统计
            row_index = 0
            total_fs_files = {}
            total_db_files = {}
            
            # 获取数据库中的文件统计
            db_stats = self._get_db_file_stats(db_manager)
            
            # 获取当前主题的颜色
            is_dark_theme = False
            foreground_color = QColor("#000000")  # 默认前景色黑色
            
            if self.theme_manager:
                theme_colors = self.theme_manager.get_current_theme_colors()
                # 获取前景色，用于判断当前主题是否为深色
                foreground_color = QColor(theme_colors.get('foreground', '#000000'))
                # 判断是否为深色主题 - 如果前景色较亮则是深色主题
                is_dark_theme = foreground_color.lightness() > 128
                
            # 根据主题设置表格颜色
            if is_dark_theme:
                # 深色主题配色方案
                header_bg = QColor("#3B4252")    # 深色主题头行背景
                alternate_bg = QColor("#2E3440") # 深色主题普通行背景1
                normal_bg = QColor("#434C5E")    # 深色主题普通行背景2
                total_bg = QColor("#4C566A")     # 深色主题总计行背景
                foreground_color = QColor("#ECEFF4")  # 深色主题前景色
                error_color = QColor("#BF616A")       # 深色主题错误色
            else:
                # 浅色主题配色方案
                header_bg = QColor("#E5E9F0")    # 浅色主题头行背景
                alternate_bg = QColor("#ECEFF4") # 浅色主题普通行背景1
                normal_bg = QColor("#FFFFFF")    # 浅色主题普通行背景2
                total_bg = QColor("#D8DEE9")     # 浅色主题总计行背景
                foreground_color = QColor("#2E3440")  # 浅色主题前景色
                error_color = QColor("#BF616A")       # 浅色主题错误色
            
            # 设置表格整体样式
            table.setStyleSheet(f"""
                QTableWidget {{
                    background-color: {alternate_bg.name()};
                    color: {foreground_color.name()};
                    gridline-color: {header_bg.name()};
                }}
                QHeaderView::section {{
                    background-color: {header_bg.name()};
                    color: {foreground_color.name()};
                    padding: 4px;
                    border: 1px solid {header_bg.name()};
                }}
            """)
            
            # 统计文件系统中的文件
            for folder in db_manager.pkm_folders:
                if not os.path.exists(folder):
                    continue
                
                # 获取文件夹中各类型文件的数量
                fs_stats = self._count_files_in_folder(folder, db_manager)
                
                # 添加文件夹统计行
                table.insertRow(row_index)
                folder_item = QTableWidgetItem(folder)
                folder_item.setToolTip(folder)  # 添加工具提示，显示完整路径
                table.setItem(row_index, 0, folder_item)
                table.setItem(row_index, 1, QTableWidgetItem("总计"))
                
                # 计算此文件夹的总文件数
                folder_fs_total = sum(fs_stats.values())
                folder_db_total = 0
                for format_name in fs_stats:
                    # 累加数据库中该文件夹对应格式的文件数
                    if folder in db_stats and format_name in db_stats[folder]:
                        folder_db_total += db_stats[folder][format_name]
                
                table.setItem(row_index, 2, QTableWidgetItem(str(folder_fs_total)))
                table.setItem(row_index, 3, QTableWidgetItem(str(folder_db_total)))
                
                # 设置文件夹行背景色和字体（粗体）
                for col in range(4):
                    item = table.item(row_index, col)
                    if item:
                        item.setBackground(header_bg)
                        item.setForeground(foreground_color)
                        font = item.font()
                        font.setBold(True)
                        item.setFont(font)
                
                row_index += 1
                
                # 为每种文件类型添加行
                for format_name, count in fs_stats.items():
                    # 更新总计
                    if format_name not in total_fs_files:
                        total_fs_files[format_name] = 0
                    total_fs_files[format_name] += count
                    
                    # 获取数据库中对应的数量
                    db_count = 0
                    if folder in db_stats and format_name in db_stats[folder]:
                        db_count = db_stats[folder][format_name]
                        # 更新总计
                        if format_name not in total_db_files:
                            total_db_files[format_name] = 0
                        total_db_files[format_name] += db_count
                    
                    # 添加行
                    table.insertRow(row_index)
                    table.setItem(row_index, 0, QTableWidgetItem(""))  # 留空，不重复显示文件夹
                    table.setItem(row_index, 1, QTableWidgetItem(format_name))
                    
                    fs_item = QTableWidgetItem(str(count))
                    db_item = QTableWidgetItem(str(db_count))
                    
                    # 如果有差异，使用错误色前景色
                    if count != db_count:
                        fs_item.setForeground(error_color)
                        db_item.setForeground(error_color)
                    else:
                        fs_item.setForeground(foreground_color)
                        db_item.setForeground(foreground_color)
                    
                    table.setItem(row_index, 2, fs_item)
                    table.setItem(row_index, 3, db_item)
                    
                    # 设置交替行背景色
                    row_bg = alternate_bg if row_index % 2 == 0 else normal_bg
                    for col in range(4):
                        item = table.item(row_index, col)
                        if item:
                            item.setBackground(row_bg)
                            if not item.foreground().color().isValid():
                                item.setForeground(foreground_color)
                    
                    row_index += 1
            
            # 添加总计行
            table.insertRow(row_index)
            total_item = QTableWidgetItem("所有文件夹")
            total_item.setFont(table.font())
            total_item.setBackground(total_bg)
            total_item.setForeground(foreground_color)
            table.setItem(row_index, 0, total_item)
            
            total_label = QTableWidgetItem("总计")
            total_label.setBackground(total_bg)
            total_label.setForeground(foreground_color)
            font = total_label.font()
            font.setBold(True)
            total_label.setFont(font)
            table.setItem(row_index, 1, total_label)
            
            # 总文件系统文件数
            total_fs = sum(total_fs_files.values())
            total_fs_item = QTableWidgetItem(str(total_fs))
            total_fs_item.setBackground(total_bg)
            total_fs_item.setForeground(foreground_color)
            total_fs_item.setFont(font)
            table.setItem(row_index, 2, total_fs_item)
            
            # 总数据库文件数
            total_db = sum(total_db_files.values())
            total_db_item = QTableWidgetItem(str(total_db))
            total_db_item.setBackground(total_bg)
            total_db_item.setForeground(foreground_color)
            total_db_item.setFont(font)
            table.setItem(row_index, 3, total_db_item)
            
            # 如果总数有差异，标记为错误色
            if total_fs != total_db:
                total_fs_item.setForeground(error_color)
                total_db_item.setForeground(error_color)
            
            # 调整行高以提高可读性
            for i in range(table.rowCount()):
                table.setRowHeight(i, 22)  # 稍微减小行高
            
        except Exception as e:
            print(f"刷新文件统计出错: {e}")
            import traceback
            traceback.print_exc()
    
    def _count_files_in_folder(self, folder, db_manager):
        """统计文件夹中各种类型文件的数量"""
        result = {}
        
        try:
            # 获取所有启用的文件格式
            for format_name, format_config in db_manager.supported_file_formats.items():
                # 初始化计数
                result[format_name] = 0
                
                # 如果格式未启用，跳过
                if not format_config['enabled']:
                    continue
                
                # 获取此格式的扩展名
                extensions = format_config['extensions']
                
                # 遍历文件夹寻找匹配的文件
                for root, _, files in os.walk(folder):
                    for file in files:
                        # 获取文件扩展名
                        _, ext = os.path.splitext(file.lower())
                        if ext in extensions:
                            result[format_name] += 1
        except Exception as e:
            print(f"统计文件夹文件出错 ({folder}): {e}")
        
        return result
    
    def _get_db_file_stats(self, db_manager):
        """获取数据库中各文件夹各类型文件的统计信息"""
        result = {}
        
        try:
            if not db_manager.conn:
                return result
                
            cursor = db_manager.conn.cursor()
            
            # 获取所有文件记录
            cursor.execute("SELECT file_path, file_format FROM pkm_files")
            rows = cursor.fetchall()
            
            # 按文件夹和格式分组统计
            for row in rows:
                # 确保row是一个字典，避免索引错误
                if isinstance(row, sqlite3.Row):
                    row_dict = dict(row)
                else:
                    row_dict = row
                
                file_path = row_dict.get('file_path', '')
                if not file_path:
                    continue
                    
                # 使用db_manager的标准化路径函数
                if hasattr(db_manager, '_normalize_path'):
                    file_path = db_manager._normalize_path(file_path)
                
                # 获取文件格式
                file_format = row_dict.get('file_format', '')
                if not file_format or file_format == 'unknown':
                    # 如果数据库中没有格式信息，从文件扩展名判断
                    file_format = db_manager.get_format_for_extension(file_path) or "unknown"
                
                # 确定文件所属的文件夹
                parent_folder = None
                for folder in db_manager.pkm_folders:
                    normalized_folder = folder
                    if hasattr(db_manager, '_normalize_path'):
                        normalized_folder = db_manager._normalize_path(folder)
                    
                    if file_path.startswith(normalized_folder):
                        parent_folder = normalized_folder
                        break
                
                # 如果找不到父文件夹，可能是孤立文件或路径格式不一致
                if not parent_folder:
                    # 尝试直接在字符串层面判断
                    for folder in db_manager.pkm_folders:
                        if folder.replace('\\', '/') in file_path.replace('\\', '/'):
                            parent_folder = folder
                            break
                
                if not parent_folder:
                    # 尝试再次使用os.path.dirname递归查找
                    test_path = file_path
                    while test_path and test_path != '/':
                        if test_path in db_manager.pkm_folders:
                            parent_folder = test_path
                            break
                        test_path = os.path.dirname(test_path)
                
                # 如果仍然找不到，添加到"其他"分类
                if not parent_folder:
                    parent_folder = "其他"
                
                # 更新统计
                if parent_folder not in result:
                    result[parent_folder] = {}
                
                if file_format not in result[parent_folder]:
                    result[parent_folder][file_format] = 0
                
                result[parent_folder][file_format] += 1
                
            # 输出统计结果日志
            print(f"数据库文件统计: {result}")
                
        except Exception as e:
            print(f"获取数据库文件统计出错: {e}")
            import traceback
            traceback.print_exc()
        
        return result
    
    def _handle_file_change(self, file_path, change_type, status_text, update_callback=None):
        """处理文件变更，并根据需要更新统计"""
        try:
            status_text.append(f"文件{change_type}: {os.path.basename(file_path)}")
            
            # 如果需要更新统计
            if update_callback:
                # 使用QTimer延迟更新，避免频繁刷新
                QTimer.singleShot(500, update_callback)
                
        except Exception as e:
            print(f"处理文件变更出错: {e}")
    
    def _handle_scan_result(self, result, status_text, progress_bar, scan_button, update_callback=None):
        """处理扫描结果，更新后刷新文件统计"""
        try:
            # 先执行原来的处理逻辑
            self._handle_original_scan_result(result, status_text, progress_bar, scan_button)
            
            # 更新文件统计
            if update_callback:
                update_callback()
                
        except Exception as e:
            print(f"处理扫描结果出错: {e}")
    
    def _handle_original_scan_result(self, result, status_text, progress_bar, scan_button):
        """原始的扫描结果处理逻辑"""
        try:
            # 检查UI组件是否仍然有效
            if not progress_bar or not progress_bar.isVisible() or not status_text or not scan_button:
                print("UI组件已关闭，无法显示结果")
                return
                
            # 恢复进度条状态
            progress_bar.setRange(0, 100)
            progress_bar.setValue(100)
            
            # 清空状态文本，避免显示重复内容
            status_text.clear()
            
            # 显示扫描结果
            if isinstance(result, dict) and ('error' in result or result.get('status') == 'error'):
                error_msg = result.get('error') or result.get('message', '未知错误')
                status_text.append(f"扫描失败: {error_msg}")
            else:
                # 获取按文件格式分类的结果
                format_stats = result.get('format_stats', {})
                
                # 如果有扫描摘要，首先显示它
                if 'summary' in result:
                    status_text.append(f"{result['summary']}")
                else:
                    status_text.append("扫描完成:")
                    status_text.append(f"- 添加了 {result.get('added_files', 0)} 个文件")
                    status_text.append(f"- 更新了 {result.get('updated_files', 0)} 个文件")
                    status_text.append(f"- 删除了 {result.get('deleted_files', 0)} 个文件")
                    status_text.append(f"- 未变更 {result.get('unchanged_files', 0)} 个文件")
                    status_text.append(f"- 跳过 {result.get('skipped_files', 0)} 个文件")
                
                # 显示按格式统计的结果
                if format_stats:
                    status_text.append("\n按格式统计:")
                    for format_name, count in format_stats.items():
                        status_text.append(f"- {format_name}: {count} 个文件")
                
                # 显示文件变更详情
                self._show_file_changes(result, status_text)
                
            # 重新启用扫描按钮
            scan_button.setEnabled(True)
        except Exception as e:
            print(f"处理原始扫描结果出错: {e}")
            import traceback
            traceback.print_exc()
            scan_button.setEnabled(True)
    
    def _show_file_changes(self, result, status_text):
        """显示文件变更的详情"""
        try:
            # 添加文件变更详情，最多显示20个文件，避免界面过长
            max_files_to_show = 20
            
            # 显示新增的文件
            added_paths = result.get('added_paths', [])
            if added_paths:
                count = len(added_paths)
                display_count = min(count, max_files_to_show)
                
                status_text.append(f"\n新增的文件({count}个):")
                for i, path in enumerate(added_paths[:display_count]):
                    status_text.append(f"  + {os.path.basename(path)}")
                if count > max_files_to_show:
                    status_text.append(f"  ... 以及其他 {count - max_files_to_show} 个文件")
            
            # 显示更新的文件
            updated_paths = result.get('updated_paths', [])
            if updated_paths:
                count = len(updated_paths)
                display_count = min(count, max_files_to_show)
                
                status_text.append(f"\n更新的文件({count}个):")
                for i, path in enumerate(updated_paths[:display_count]):
                    status_text.append(f"  ~ {os.path.basename(path)}")
                if count > max_files_to_show:
                    status_text.append(f"  ... 以及其他 {count - max_files_to_show} 个文件")
            
            # 显示删除的文件
            deleted_paths = result.get('deleted_paths', [])
            if deleted_paths:
                count = len(deleted_paths)
                display_count = min(count, max_files_to_show)
                
                status_text.append(f"\n删除的文件({count}个):")
                for i, path in enumerate(deleted_paths[:display_count]):
                    status_text.append(f"  - {os.path.basename(path)}")
                if count > max_files_to_show:
                    status_text.append(f"  ... 以及其他 {count - max_files_to_show} 个文件")
            
            # 显示失败的文件
            failed_paths = result.get('failed_paths', [])
            if failed_paths:
                count = len(failed_paths)
                display_count = min(count, max_files_to_show)
                
                status_text.append(f"\n处理失败的文件({count}个):")
                for i, path in enumerate(failed_paths[:display_count]):
                    status_text.append(f"  ! {os.path.basename(path)}")
                if count > max_files_to_show:
                    status_text.append(f"  ... 以及其他 {count - max_files_to_show} 个文件")
                    
        except Exception as e:
            print(f"显示文件变更详情出错: {e}")
            import traceback
            traceback.print_exc()
    
    def _scan_pkm_folder(self, db_manager, status_text, progress_bar, scan_button, update_callback=None):
        """扫描PKM文件夹，更新数据库，完成后更新文件统计"""
        try:
            # 检查是否已设置文件夹
            if not db_manager.pkm_folders:
                QMessageBox.warning(self, "警告", "请先添加至少一个PKM文件夹")
                return
                
            # 检查是否有启用的文件格式
            enabled_formats = [format_name for format_name, config in db_manager.supported_file_formats.items() 
                              if config.get('enabled', False)]
            if not enabled_formats:
                QMessageBox.warning(self, "警告", "请先启用至少一种文件格式")
                return
                
            # 禁用扫描按钮，避免重复点击
            scan_button.setEnabled(False)
            
            # 重置进度条和状态
            progress_bar.setValue(0)
            status_text.clear()
            status_text.append("开始扫描文件夹...")
            status_text.append(f"扫描的文件夹: {len(db_manager.pkm_folders)}个")
            status_text.append(f"启用的文件格式: {', '.join(enabled_formats)}")
            
            # 创建线程实例 - 因为现在支持多文件夹，这里传递第一个作为兼容处理
            # 实际扫描将通过数据库管理器处理多个文件夹
            first_folder = db_manager.pkm_folders[0] if db_manager.pkm_folders else ""
            self.scan_thread = ScanThread(first_folder)
            
            # 连接进度更新信号
            self.scan_thread.progress_update.connect(
                lambda current, total: self._update_scan_progress(current, total, progress_bar, status_text)
            )
            
            # 连接完成信号
            self.scan_thread.scan_complete.connect(
                lambda result: self._handle_scan_result(result, status_text, progress_bar, scan_button, update_callback)
            )
            
            # 设置进度条初始值
            progress_bar.setRange(0, 100)
            progress_bar.setValue(0)
            
            # 启动线程
            self.scan_thread.start()
            
        except Exception as e:
            scan_button.setEnabled(True)
            progress_bar.setRange(0, 100)
            progress_bar.setValue(0)
            status_text.append(f"扫描出错: {str(e)}")
            QMessageBox.critical(self, "错误", f"扫描PKM文件夹出错: {str(e)}")
    
    def _update_scan_progress(self, current, total, progress_bar, status_text):
        """更新扫描进度"""
        try:
            if not progress_bar or not progress_bar.isVisible():
                return
                
            if total <= 0:
                progress_bar.setValue(0)
                return
                
            # 计算百分比并更新进度条
            percent = min(int(current * 100 / total), 100)
            progress_bar.setValue(percent)
            
            # 获取当前扫描的文件名（如果可用）
            current_file = getattr(self, '_current_scanning_file', '')
            
            # 更新状态文本
            if current == 0:
                status_text.append(f"准备扫描文件...")
            elif current == total:
                status_text.append(f"已完成所有文件扫描 (100%)")
            elif current % 20 == 0 or current == 1:  # 第一个文件和每20个文件更新一次信息
                if current_file:
                    status_text.append(f"正在扫描: {current}/{total} 文件 ({percent}%) - {os.path.basename(current_file)}")
                else:
                    status_text.append(f"正在扫描: {current}/{total} 文件 ({percent}%)")
                # 确保滚动到底部
                status_text.verticalScrollBar().setValue(status_text.verticalScrollBar().maximum())
                
            # 处理QT事件，确保UI响应
            QApplication.processEvents()
                
        except Exception as e:
            print(f"更新进度条出错: {e}")
    
    def _toggle_file_monitoring(self, state, db_manager, status_text):
        """切换文件监控状态"""
        try:
            if not hasattr(db_manager, 'file_watcher') or not db_manager.pkm_folders:
                status_text.append("请先设置PKM文件夹")
                return
                
            if state:  # 启用监控
                # 过滤出存在的文件夹
                existing_folders = [folder for folder in db_manager.pkm_folders if os.path.exists(folder)]
                
                if not existing_folders:
                    status_text.append("没有可用的文件夹路径，请检查文件夹设置")
                    return
                
                # 一次性启动对所有文件夹的监控
                success = db_manager.file_watcher.start_monitoring(existing_folders)
                
                # 确保数据库操作信号连接正常
                if hasattr(db_manager.file_watcher, 'reconnect_signals'):
                    db_manager.file_watcher.reconnect_signals()
                    status_text.append("已重新连接文件监控信号")
                
                if success:
                    enabled_formats = [format_name for format_name, config in db_manager.supported_file_formats.items() 
                                       if config.get('enabled', False)]
                    formats_text = "、".join(enabled_formats) if enabled_formats else "无"
                    status_text.append(f"已启用{len(existing_folders)}个文件夹的监控")
                    status_text.append(f"监控的文件格式: {formats_text}")
                else:
                    status_text.append("启用文件监控失败")
            else:  # 禁用监控
                db_manager.file_watcher.stop_monitoring()
                status_text.append("已禁用文件监控")
        except Exception as e:
            status_text.append(f"切换监控状态出错: {str(e)}")
    
    def _save_pkm_settings(self, folders_list, format_checkboxes, db_manager, dialog):
        """保存PKM设置，包括文件夹和文件格式设置"""
        try:
            # 获取所有文件夹
            folders = []
            for i in range(folders_list.count()):
                folders.append(folders_list.item(i).text())
                
            # 获取文件格式设置
            file_formats = {}
            for format_name, checkbox in format_checkboxes.items():
                file_formats[format_name] = {
                    "enabled": checkbox.isChecked()
                }
                
            # 保存设置
            if db_manager.save_pkm_settings(folders, file_formats):
                QMessageBox.information(self, "成功", "PKM设置已保存")
                dialog.accept()
            else:
                QMessageBox.warning(self, "警告", "无法保存PKM设置")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存PKM设置出错: {str(e)}")
            
    def _add_pkm_folder(self, folders_list, db_manager):
        """添加PKM文件夹"""
        try:
            # 打开文件夹选择对话框
            folder_path = QFileDialog.getExistingDirectory(self, "选择PKM文件夹")
            
            if not folder_path:
                return  # 用户取消了选择
                
            # 检查文件夹是否已存在
            for i in range(folders_list.count()):
                if folders_list.item(i).text() == folder_path:
                    QMessageBox.information(self, "提示", "该文件夹已在监控列表中")
                    return
                    
            # 添加文件夹到列表
            folders_list.addItem(folder_path)
            
            # 更新列表高度
            self._update_folders_list_height(folders_list)
            
            # 临时添加到db_manager.pkm_folders中，方便后续操作
            if not hasattr(db_manager, 'pkm_folders') or db_manager.pkm_folders is None:
                db_manager.pkm_folders = []
                
            if folder_path not in db_manager.pkm_folders:
                db_manager.pkm_folders.append(folder_path)
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"添加文件夹失败: {str(e)}")
    
    def _remove_pkm_folder(self, folders_list, db_manager):
        """移除PKM文件夹"""
        try:
            # 获取当前选中的项
            current_item = folders_list.currentItem()
            if not current_item:
                QMessageBox.information(self, "提示", "请先选择要移除的文件夹")
                return
                
            # 获取文件夹路径
            folder_path = current_item.text()
            
            # 确认对话框
            reply = QMessageBox.question(
                self, "确认删除", 
                f"确定要从监控列表中移除此文件夹吗?\n{folder_path}",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # 从列表中移除
                row = folders_list.row(current_item)
                folders_list.takeItem(row)
                
                # 更新列表高度
                self._update_folders_list_height(folders_list)
                
                # 从db_manager.pkm_folders中移除
                if hasattr(db_manager, 'pkm_folders') and folder_path in db_manager.pkm_folders:
                    db_manager.pkm_folders.remove(folder_path)
                    
        except Exception as e:
            QMessageBox.critical(self, "错误", f"移除文件夹失败: {str(e)}")
    
    def _update_folders_list_height(self, folders_list):
        """动态更新文件夹列表高度"""
        # 计算理想高度 - 每行25像素，最小高度80，最大高度150
        folder_count = folders_list.count() or 1  # 至少1行的高度
        ideal_height = min(max(folder_count * 25 + 10, 80), 150)
        folders_list.setFixedHeight(ideal_height)
    
    def _delayed_load_stats(self, table, db_manager):
        """延迟加载统计数据的方法"""
        try:
            # 检查表格是否还存在
            if not table or not table.isVisible():
                return
                
            # 调用刷新统计方法
            self._refresh_file_stats(table, db_manager)
            
        except Exception as e:
            print(f"延迟加载统计数据出错: {e}")
            # 清除加载提示
            if table and table.rowCount() > 0:
                table.setRowCount(0)
            