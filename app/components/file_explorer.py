#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTreeView, QHeaderView, 
                           QToolBar, QFileDialog, QPushButton, QHBoxLayout, 
                           QListWidget, QStackedWidget, QSplitter, QLabel,
                           QMenu, QTabWidget, QAbstractItemView, QScrollBar, QFrame, QSizePolicy,
                           QMessageBox)
from PyQt6.QtCore import Qt, QDir, QModelIndex, pyqtSignal, QSettings, QSize, QTimer, QUrl, QMimeData, QThread
from PyQt6.QtGui import QFileSystemModel, QIcon, QAction, QDrag
import qtawesome as qta
import os
import json
from PyQt6.QtWidgets import QApplication
from app.controllers.theme_manager import ThemeManager

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
        from app.models.database import DatabaseManager
        db_manager = DatabaseManager()
        
        # 设置进度回调函数
        def progress_callback(data):
            if isinstance(data, dict) and 'current' in data:
                # 新版本进度回调
                self.progress_update.emit(data.get('current', 0), data.get('total', 100))
            elif isinstance(data, tuple) and len(data) == 2:
                # 兼容旧版本回调
                self.progress_update.emit(data[0], data[1])
                
        # 执行数据库扫描
        result = db_manager.scan_pkm_folder(callback=progress_callback)
        
        # 转换结果以兼容旧版本UI
        compat_result = {
            'added': result.get('added_files', 0),
            'updated': result.get('updated_files', 0),
            'deleted': result.get('deleted_files', 0),
            'error': result.get('message', None) if result.get('status') == 'error' else None
        }
        
        self.scan_complete.emit(compat_result)

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
        self.index_action = None
        self.kbflow_action = None
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
        
        # 添加知识库按钮
        self.kbflow_action = QAction(qta.icon('fa5s.book'), "知识库", self)
        self.kbflow_action.setToolTip("知识库工具")
        self.kbflow_action.triggered.connect(self.show_kbflow)
        self.bottom_toolbar.addAction(self.kbflow_action)
        
        # 添加索引按钮
        self.index_action = QAction(qta.icon('fa5s.database'), "索引", self)
        self.index_action.setToolTip("文件索引")
        self.index_action.triggered.connect(self.show_index)
        self.bottom_toolbar.addAction(self.index_action)
        
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
        
        # 更新按钮图标
        if hasattr(self, 'index_action') and self.index_action:
            self.index_action.setIcon(qta.icon('fa5s.search', color=icon_color))
            
        if hasattr(self, 'kbflow_action') and self.kbflow_action:
            self.kbflow_action.setIcon(qta.icon('fa5s.book', color=icon_color))
        
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
                
    def show_index(self):
        """显示本地索引工具"""
        try:
            # 使用嵌入式集成方案
            from app.local_index_tool.gui.main_window import MainWindow
            
            # 获取当前活动标签页的路径
            current_path = None
            if self.tab_widget.count() > 0 and self.tab_widget.currentIndex() != self.plus_tab_index:
                current_path = self.tab_widget.tabToolTip(self.tab_widget.currentIndex())
            
            # 创建并显示MainWindow，传递所需参数
            self.index_tool_window = MainWindow(parent=self)
            self.index_tool_window.setWindowModality(Qt.WindowModality.ApplicationModal)
            
            # 如果MainWindow支持这些参数，可以取消注释以下代码
            # if hasattr(self.index_tool_window, 'set_initial_path') and current_path:
            #     self.index_tool_window.set_initial_path(current_path)
            
            self.index_tool_window.show()
            print("成功启动本地索引工具")
        except ImportError as e:
            print(f"导入本地索引工具失败: {e}")
            # 如果导入失败，退回到子进程方式
            self._start_with_subprocess()
        except Exception as e:
            print(f"启动本地索引工具失败: {e}")
            # 如果启动失败，退回到子进程方式
            self._start_with_subprocess()

    def _start_with_subprocess(self):
        """使用子进程方式启动本地索引工具"""
        try:
            import subprocess
            import os
            import sys
            
            # 尝试从不同位置找到local_index_tool
            # 首先检查app/local_index_tool路径
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            tool_path = os.path.join(base_dir, "local_index_tool", "main.py")
            
            if not os.path.exists(tool_path):
                # 检查项目根目录下的local_index_tool
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                tool_path = os.path.join(base_dir, "local_index_tool", "main.py")
                
                if not os.path.exists(tool_path):
                    # 特定路径测试
                    tool_path = r"D:\OneDrive\01.事业工作\编程\Tengle's Projects\AiSparkHub\local_index_tool\main.py"
                    if not os.path.exists(tool_path):
                        raise FileNotFoundError(f"找不到本地索引工具: {tool_path}")
            
            # 启动子进程
            subprocess.Popen([sys.executable, tool_path])
            print(f"启动本地索引工具: {tool_path}")
        except Exception as e:
            print(f"启动本地索引工具失败: {e}")

    def show_kbflow(self):
        """显示知识库工具"""
        try:
            # 使用嵌入式集成方案
            # IDE可能无法识别此导入，但运行时可能正常
            # type: ignore
            from app.kbflow.main import MainWindow
            
            # 获取当前活动标签页的路径
            current_path = None
            if self.tab_widget.count() > 0 and self.tab_widget.currentIndex() != self.plus_tab_index:
                current_path = self.tab_widget.tabToolTip(self.tab_widget.currentIndex())
            
            # 创建并显示MainWindow，传递所需参数
            self.kbflow_window = MainWindow(parent=self)
            self.kbflow_window.setWindowModality(Qt.WindowModality.ApplicationModal)
            
            # 如果MainWindow支持设置初始路径
            if hasattr(self.kbflow_window, 'set_initial_path') and current_path:
                self.kbflow_window.set_initial_path(current_path)
            
            self.kbflow_window.show()
            print("成功启动知识库工具")
        except ImportError as e:
            print(f"导入知识库工具失败: {e}")
            # 如果导入失败，退回到子进程方式
            self._start_kbflow_subprocess()
        except Exception as e:
            print(f"启动知识库工具失败: {e}")
            # 如果启动失败，退回到子进程方式
            self._start_kbflow_subprocess()
            
    def _start_kbflow_subprocess(self):
        """使用子进程方式启动知识库工具"""
        try:
            import subprocess
            import os
            import sys
            
            # 尝试从不同位置找到kbflow
            # 首先检查app/kbflow路径
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            tool_path = os.path.join(base_dir, "kbflow", "main.py")
            
            if not os.path.exists(tool_path):
                # 检查项目根目录下的kbflow
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                tool_path = os.path.join(base_dir, "kbflow", "main.py")
                
                if not os.path.exists(tool_path):
                    raise FileNotFoundError(f"找不到知识库工具: {tool_path}")
            
            # 启动子进程
            subprocess.Popen([sys.executable, tool_path])
            print(f"启动知识库工具: {tool_path}")
        except Exception as e:
            print(f"启动知识库工具失败: {e}")

    def show_pkm_database(self):
        """显示PKM数据库设置和管理界面"""
        try:
            # 导入数据库管理器
            from app.models.database import DatabaseManager
            from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                                        QPushButton, QFileDialog, QProgressBar, 
                                        QLineEdit, QTextEdit, QCheckBox, QListWidget,
                                        QToolButton, QMenu, QGroupBox)
            # QAction应从QtGui导入，而不是QtWidgets
            from PyQt6.QtCore import QThread, pyqtSignal, Qt
            
            # 创建设置对话框
            dialog = QDialog(self)
            dialog.setWindowTitle("PKM数据库设置")
            dialog.resize(650, 600)
            
            # 创建对话框布局
            layout = QVBoxLayout(dialog)
            
            # 创建数据库管理器实例
            db_manager = DatabaseManager()
            
            # ======== 文件夹设置部分 ========
            folder_group = QGroupBox("文件夹设置")
            folder_layout = QVBoxLayout()
            
            # 添加文件夹列表显示区域
            folder_layout.addWidget(QLabel("监控文件夹列表:"))
            
            # 创建文件夹列表控件
            folders_list = QListWidget()
            folders_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
            folders_list.setAlternatingRowColors(True)
            folders_list.setMinimumHeight(150)
            
            # 填充现有文件夹列表
            if db_manager.pkm_folders:
                for folder in db_manager.pkm_folders:
                    folders_list.addItem(folder)
            
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
            
            # ======== 文件格式设置部分 ========
            format_group = QGroupBox("文件格式设置")
            format_layout = QVBoxLayout()
            
            # 创建文件格式复选框
            format_checkboxes = {}
            
            if hasattr(db_manager, 'supported_file_formats'):
                for format_name, format_config in db_manager.supported_file_formats.items():
                    checkbox = QCheckBox(f"{format_config['description']} ({', '.join(format_config['extensions'])})")
                    checkbox.setChecked(format_config['enabled'])
                    format_checkboxes[format_name] = checkbox
                    format_layout.addWidget(checkbox)
            
            format_group.setLayout(format_layout)
            layout.addWidget(format_group)
            
            # ======== 监控设置部分 ========
            # 添加监控开关
            monitor_layout = QHBoxLayout()
            monitor_checkbox = QCheckBox("启用实时文件监控")
            monitor_checkbox.setChecked(True)  # 默认启用
            monitor_checkbox.setToolTip("启用后，会自动监控文件变化并更新数据库")
            
            # 连接监控开关信号
            monitor_checkbox.stateChanged.connect(
                lambda state: self._toggle_file_monitoring(state, db_manager, status_text)
            )
            
            monitor_layout.addWidget(monitor_checkbox)
            
            # 添加测试监控状态按钮
            test_monitor_btn = QPushButton("测试监控状态")
            test_monitor_btn.setToolTip("检查文件监控状态是否正常工作")
            test_monitor_btn.clicked.connect(
                lambda: self._test_monitoring(db_manager)
            )
            monitor_layout.addWidget(test_monitor_btn)
            
            layout.addLayout(monitor_layout)
            
            # ======== 扫描和操作部分 ========
            # 添加扫描按钮和状态显示
            scan_layout = QHBoxLayout()
            scan_button = QPushButton("扫描文件夹")
            scan_button.clicked.connect(lambda: self._scan_pkm_folder(db_manager, status_text, progress_bar, scan_button))
            scan_layout.addWidget(scan_button)
            
            progress_bar = QProgressBar()
            progress_bar.setTextVisible(True)
            progress_bar.setRange(0, 100)
            progress_bar.setValue(0)
            scan_layout.addWidget(progress_bar)
            
            layout.addLayout(scan_layout)
            
            # 添加搜索功能
            search_layout = QHBoxLayout()
            search_layout.addWidget(QLabel("搜索:"))
            
            search_input = QLineEdit()
            search_input.setPlaceholderText("输入搜索内容...")
            search_layout.addWidget(search_input, 1)
            
            search_button = QPushButton("搜索")
            search_button.clicked.connect(
                lambda: self._search_pkm_files(db_manager, search_input.text(), status_text)
            )
            search_layout.addWidget(search_button)
            
            layout.addLayout(search_layout)
            
            # 添加状态文本显示区域
            status_text = QTextEdit()
            status_text.setReadOnly(True)
            status_text.setPlaceholderText("操作结果将显示在这里...")
            layout.addWidget(status_text)
            
            # 连接文件监控器的信号到状态显示
            if hasattr(db_manager, 'file_watcher'):
                # 先确保数据库处理函数连接正常
                if hasattr(db_manager.file_watcher, 'reconnect_signals'):
                    db_manager.file_watcher.reconnect_signals()
                
                # 连接UI信号 - 这些连接只在对话框打开时有效，关闭时会断开
                db_manager.file_watcher.file_added.connect(
                    lambda path: status_text.append(f"文件已添加: {os.path.basename(path)}")
                )
                db_manager.file_watcher.file_modified.connect(
                    lambda path: status_text.append(f"文件已更新: {os.path.basename(path)}")
                )
                db_manager.file_watcher.file_deleted.connect(
                    lambda path: status_text.append(f"文件已删除: {os.path.basename(path)}")
                )
                db_manager.file_watcher.scan_completed.connect(
                    lambda result: self._handle_scan_result(result, status_text, progress_bar, scan_button)
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
            
    def _add_pkm_folder(self, folders_list, db_manager):
        """添加PKM监控文件夹"""
        try:
            # 获取当前已有的文件夹列表
            current_folders = [folders_list.item(i).text() for i in range(folders_list.count())]
            
            # 打开文件夹选择对话框
            start_dir = current_folders[0] if current_folders else ""
            folder = QFileDialog.getExistingDirectory(
                self, "选择PKM文件夹", start_dir,
                QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks
            )
            
            # 如果用户选择了文件夹，并且不在当前列表中，添加到列表
            if folder and folder not in current_folders:
                folders_list.addItem(folder)
                # 添加成功后提示用户点击"保存设置"按钮
                QMessageBox.information(self, "提示", "文件夹已添加到列表，请点击'保存设置'按钮保存更改")
            elif folder in current_folders:
                QMessageBox.information(self, "提示", "该文件夹已在监控列表中")
                    
        except Exception as e:
            QMessageBox.critical(self, "错误", f"添加PKM文件夹出错: {str(e)}")
    
    def _remove_pkm_folder(self, folders_list, db_manager):
        """移除PKM监控文件夹"""
        try:
            # 获取当前选中的项
            selected_items = folders_list.selectedItems()
            if not selected_items:
                QMessageBox.information(self, "提示", "请先选择要移除的文件夹")
                return
                
            # 从列表中移除选中的文件夹
            for item in selected_items:
                row = folders_list.row(item)
                folders_list.takeItem(row)
            
            # 移除成功后提示用户点击"保存设置"按钮
            QMessageBox.information(self, "提示", "文件夹已从列表移除，请点击'保存设置'按钮保存更改")
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"移除PKM文件夹出错: {str(e)}")
    
    def _select_pkm_folder(self, folder_path_field, db_manager):
        """选择PKM文件夹 (旧版本兼容方法)"""
        try:
            # 获取当前设置的文件夹（如果有）
            start_dir = db_manager.pkm_folder if db_manager.pkm_folder else ""
            
            # 打开文件夹选择对话框
            folder = QFileDialog.getExistingDirectory(
                self, "选择PKM文件夹", start_dir,
                QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks
            )
            
            # 如果用户选择了文件夹，更新设置
            if folder:
                # 保存设置
                if db_manager.save_pkm_settings([folder]):
                    folder_path_field.setText(folder)
                    QMessageBox.information(self, "成功", "PKM文件夹设置已保存")
                else:
                    QMessageBox.warning(self, "警告", "无法保存PKM文件夹设置")
                    
        except Exception as e:
            QMessageBox.critical(self, "错误", f"选择PKM文件夹出错: {str(e)}")
    
    def _scan_pkm_folder(self, db_manager, status_text, progress_bar, scan_button):
        """扫描PKM文件夹，更新数据库"""
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
                lambda result: self._handle_scan_result(result, status_text, progress_bar, scan_button)
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
            
            # 更新状态文本
            if current == 0:
                status_text.append(f"准备扫描 {total} 个文件...")
            elif current == total:
                status_text.append(f"已完成所有 {total} 个文件扫描 (100%)")
            elif current % 20 == 0 or current == 1:  # 第一个文件和每20个文件更新一次信息
                status_text.append(f"正在扫描: {current}/{total} 文件 ({percent}%)")
                # 确保滚动到底部
                status_text.verticalScrollBar().setValue(status_text.verticalScrollBar().maximum())
                
            # 处理QT事件，确保UI响应
            QApplication.processEvents()
                
        except Exception as e:
            print(f"更新进度条出错: {e}")
    
    def _handle_scan_result(self, result, status_text, progress_bar, scan_button):
        """处理扫描结果"""
        try:
            # 检查UI组件是否仍然有效
            if not progress_bar or not progress_bar.isVisible() or not status_text or not scan_button:
                print("UI组件已关闭，无法显示结果")
                return
                
            # 恢复进度条状态
            progress_bar.setRange(0, 100)
            progress_bar.setValue(100)
            
            # 显示扫描结果
            if 'error' in result and result['error']:
                status_text.append(f"扫描失败: {result['error']}")
            else:
                # 获取按文件格式分类的结果（如果有的话）
                format_stats = result.get('format_stats', {})
                
                status_text.append("扫描完成:")
                status_text.append(f"- 添加了 {result['added']} 个文件")
                status_text.append(f"- 更新了 {result['updated']} 个文件")
                status_text.append(f"- 删除了 {result.get('deleted', 0)} 个文件")
                status_text.append(f"- 未变更 {result.get('unchanged', 0)} 个文件")
                status_text.append(f"- 跳过 {result.get('skipped', 0)} 个文件")
                
                # 显示按格式统计的结果
                if format_stats:
                    status_text.append("\n按格式统计:")
                    for format_name, count in format_stats.items():
                        status_text.append(f"- {format_name}: {count} 个文件")
                
            # 重新启用扫描按钮
            scan_button.setEnabled(True)
        except RuntimeError:
            # 捕获C++对象已删除错误
            print("UI组件已被销毁，无法更新界面")
        except Exception as e:
            print(f"处理扫描结果出错: {e}")
    
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
    
    def _search_pkm_files(self, db_manager, query, status_text):
        """搜索PKM文件"""
        try:
            if not query:
                status_text.append("请输入搜索关键词")
                return
                
            status_text.clear()
            status_text.append(f"正在搜索: {query}")
            
            # 检查是否有启用的文件格式
            enabled_formats = [format_name for format_name, config in db_manager.supported_file_formats.items() 
                              if config.get('enabled', False)]
            if enabled_formats:
                status_text.append(f"搜索范围: {', '.join(enabled_formats)}")
            
            # 执行搜索
            results = db_manager.search_pkm_files(query)
            
            if not results:
                status_text.append("未找到匹配的文件")
                return
                
            # 按文件格式分组结果
            format_results = {}
            for result in results:
                # 安全地获取文件路径
                file_path = result.get('file_path', '')
                if not file_path:
                    continue
                
                # 尝试从结果中获取文件格式，如果没有则从文件扩展名判断
                format_name = None
                if 'file_format' in result:
                    format_name = result.get('file_format')
                if not format_name:
                    format_name = db_manager.get_format_for_extension(file_path) or "其他"
                
                if format_name not in format_results:
                    format_results[format_name] = []
                format_results[format_name].append(result)
            
            # 显示总结果数
            status_text.append(f"找到 {len(results)} 个匹配文件:")
            
            # 按文件格式显示结果
            for format_name, files in format_results.items():
                status_text.append(f"\n{format_name} ({len(files)}个):")
                for result in files:
                    # 安全地获取标题和文件名
                    title = result.get('title') or result.get('file_name') or '未知标题'
                    file_name = os.path.basename(result.get('file_path', ''))
                    last_modified = result.get('last_modified', 0)
                    
                    if last_modified > 0:
                        import datetime
                        modified_date = datetime.datetime.fromtimestamp(last_modified).strftime('%Y-%m-%d %H:%M')
                        status_text.append(f"- {title} ({file_name}) [修改于: {modified_date}]")
                    else:
                        status_text.append(f"- {title} ({file_name})")
                
        except Exception as e:
            status_text.append(f"搜索出错: {str(e)}")
            import traceback
            traceback.print_exc()
    
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
            
    def _test_monitoring(self, db_manager):
        """测试文件监控功能"""
        try:
            if not hasattr(db_manager, 'file_watcher'):
                QMessageBox.warning(self, "警告", "文件监控器未初始化")
                return
                
            # 检查是否有文件夹正在监控
            is_monitoring = bool(db_manager.file_watcher.watcher.directories() or db_manager.file_watcher.watcher.files())
            if not is_monitoring:
                QMessageBox.warning(self, "警告", "文件监控未启动，请先启用监控")
                return
                
            # 检查信号连接状态并尝试重新连接
            has_signals_connected = getattr(db_manager.file_watcher, '_signals_connected', False)
            if not has_signals_connected and hasattr(db_manager.file_watcher, 'reconnect_signals'):
                db_manager.file_watcher.reconnect_signals()
                has_signals_connected = getattr(db_manager.file_watcher, '_signals_connected', False)
                
            if not has_signals_connected:
                QMessageBox.warning(self, "警告", "文件监控信号未连接，请重启应用")
                return
            
            # 显示监控状态信息
            monitoring_stats = (
                f"监控状态: 正在监控\n"
                f"监控文件夹数量: {len(db_manager.file_watcher.watcher.directories())}\n"
                f"监控文件数量: {len(db_manager.file_watcher.watcher.files())}\n"
                f"已知Markdown文件: {len(db_manager.file_watcher.known_files)}\n"
                f"数据库连接状态: {'已连接' if db_manager.conn else '未连接'}\n"
                f"信号连接状态: {'已连接' if has_signals_connected else '未连接'}\n\n"
                f"监控的文件夹:\n"
            )
            
            # 添加监控的文件夹列表
            folder_list = ""
            for i, folder in enumerate(db_manager.pkm_folders, 1):
                folder_exists = "存在" if os.path.exists(folder) else "不存在或无法访问"
                folder_list += f"{i}. {folder} ({folder_exists})\n"
            
            # 测试说明
            test_instructions = (
                "\n测试方法:\n"
                "1. 在任意受监控的文件夹中创建一个新的.md文件\n"
                "2. 然后打开控制台查看是否输出「文件添加: xxx」的信息\n"
                "3. 如果看到此消息，说明监控正常工作并更新了数据库\n"
                "4. 您也可以修改或删除一个已存在的.md文件来测试"
            )
            
            QMessageBox.information(self, "文件监控状态", monitoring_stats + folder_list + test_instructions)
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"测试文件监控出错: {str(e)}")
            