#!/usr/bin/env python
# -*- coding: utf-8 -*-

# auxiliary_window.py: 定义 AuxiliaryWindow 类
# 该窗口作为辅助窗口，包含文件浏览器、提示词输入框和提示词历史记录。
# 用于管理和同步提示词到主窗口的 AI 对话页面。

from PyQt6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QPushButton, QVBoxLayout, QLabel, QSplitter, QFrame, QToolBar, QStackedWidget, QTabWidget, QApplication, QMessageBox
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QIcon
import qtawesome as qta
import os

from app.components.file_explorer import FileExplorer
from app.components.prompt_input import PromptInput
from app.components.prompt_history import PromptHistory
from app.components.file_viewer import FileViewer  # 导入文件查看器组件
from app.controllers.prompt_sync import PromptSync

class RibbonToolBar(QToolBar):
    """垂直工具栏，类似Obsidian的ribbon"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setOrientation(Qt.Orientation.Vertical)
        self.setMovable(False)
        self.setIconSize(QSize(22, 22))
        self.setObjectName("ribbonToolBar")
        
        # 设置样式
        self.setStyleSheet("""
            #ribbonToolBar {
                background-color: #2E3440;
                border-right: 1px solid #4C566A;
                padding: 5px 2px;
                spacing: 8px;
            }
            QToolButton {
                background-color: transparent;
                border: none;
                border-radius: 3px;
                padding: 5px;
            }
            QToolButton:hover {
                background-color: #3B4252;
            }
            QToolButton:pressed {
                background-color: #434C5E;
            }
        """)

class PanelWidget(QWidget):
    """面板组件，包含标题和内容区域"""
    
    def __init__(self, title, content_widget, window=None, is_control_panel=False, custom_titlebar=None):
        super().__init__()
        self.window = window
        self.is_control_panel = is_control_panel
        
        # 创建垂直布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        if custom_titlebar:
            # 使用自定义标题栏
            self.title_bar = custom_titlebar
        else:
            # 创建标题区域
            self.title_bar = QWidget()
            self.title_bar.setFixedHeight(38)
            self.title_bar.setObjectName("panelTitleBar")
            title_layout = QHBoxLayout(self.title_bar)
            title_layout.setContentsMargins(8, 0, 8, 0)
            
            # 创建标题标签
            title_label = QLabel(title)
            title_label.setStyleSheet("color: #D8DEE9; font-weight: bold;")
            
            # 添加标题到布局
            title_layout.addWidget(title_label)
        
        # 如果是控制面板，添加窗口控制按钮
        if is_control_panel and window:
            # 获取标题栏的布局
            if not hasattr(self.title_bar, 'layout'):
                # 如果没有布局（自定义标题栏可能已有布局），创建一个
                title_layout = QHBoxLayout(self.title_bar)
                title_layout.setContentsMargins(8, 0, 8, 0)
            else:
                title_layout = self.title_bar.layout()
            
            # 添加伸缩空间
            title_layout.addStretch(1)
            
            # 创建窗口控制按钮
            # 最小化按钮
            minimize_button = QPushButton()
            minimize_button.setIcon(qta.icon('fa5s.window-minimize'))
            minimize_button.clicked.connect(window.showMinimized)
            
            # 最大化/还原按钮
            maximize_button = QPushButton()
            maximize_button.setIcon(qta.icon('fa5s.window-maximize'))
            maximize_button.clicked.connect(window.toggle_maximize)
            
            # 关闭按钮
            close_button = QPushButton()
            close_button.setIcon(qta.icon('fa5s.times'))
            close_button.clicked.connect(window.close)
            
            # 设置按钮样式
            button_style = """
                QPushButton {
                    background: transparent;
                    border: none;
                    padding: 6px 8px;
                    margin: 0;
                }
                QPushButton:hover {
                    background: #3B4252;
                }
            """
            close_button_style = button_style + """
                QPushButton:hover {
                    background: #BF616A;
                }
            """
            minimize_button.setStyleSheet(button_style)
            maximize_button.setStyleSheet(button_style)
            close_button.setStyleSheet(close_button_style)
            
            # 添加按钮到标题栏
            title_layout.addWidget(minimize_button)
            title_layout.addWidget(maximize_button)
            title_layout.addWidget(close_button)
            
            # 保存按钮引用便于后续访问
            window.minimize_button = minimize_button
            window.maximize_button = maximize_button
        
        # 创建分隔线（设置为非常细的线条）
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Plain)
        separator.setLineWidth(0)
        separator.setMidLineWidth(0)  # 将中线宽度设为0以获得更细的线条
        separator.setFixedHeight(1)  # 将高度固定为1px
        separator.setStyleSheet("background-color: #3B4252;")  # 使用与中间标签栏一致的颜色
        
        # 添加标题栏和分隔线到主布局
        layout.addWidget(self.title_bar)
        layout.addWidget(separator)
        
        # 添加内容区域
        layout.addWidget(content_widget, 1)  # 使内容区域拉伸填充
        
        # 设置样式
        self.title_bar.setStyleSheet("""
            #panelTitleBar {
                background-color: #2E3440;
            }
        """)
        
        # 标记标题栏用于拖动窗口
        self.title_bar.installEventFilter(self)
    
    def eventFilter(self, obj, event):
        """事件过滤器，用于处理标题栏的鼠标事件"""
        if obj == self.title_bar:
            # 标题栏鼠标按下事件，用于拖动窗口
            if event.type() == event.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                if self.window:
                    self.window._drag_pos = event.globalPosition().toPoint()
                
            # 双击标题栏，触发窗口最大化/还原
            elif event.type() == event.Type.MouseButtonDblClick and event.button() == Qt.MouseButton.LeftButton:
                if self.window:
                    self.window.toggle_maximize()
                    return True
        
        return super().eventFilter(obj, event)

class AuxiliaryWindow(QMainWindow):
    """辅助窗口类 - 包含文件浏览、提示词输入和历史记录"""
    
    # 信号：请求打开主窗口
    request_open_main_window = pyqtSignal()
    
    def __init__(self, db_manager):
        super().__init__()
        self.setWindowTitle("AiSparkHub - 提示词管理")
        self.setMinimumSize(1000, 300)
        
        # 设置无边框窗口
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        
        # 设置图标 (虽然无边框，但任务栏可能需要)
        self.setWindowIcon(qta.icon('fa5s.keyboard', color='#88C0D0'))
        
        # 创建主容器和主水平布局
        main_container = QWidget()
        self.main_layout = QHBoxLayout(main_container)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # 创建左侧垂直工具栏（Ribbon）
        self.ribbon = RibbonToolBar()
        self.main_layout.addWidget(self.ribbon)
        
        # 添加"打开主窗口"按钮
        self.open_main_window_action = self.ribbon.addAction(qta.icon('fa5s.window-maximize'), "打开主窗口")
        self.open_main_window_action.triggered.connect(self.on_open_main_window)
        
        # 内容区域垂直布局容器
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # 创建分割器
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        # 设置分割器样式
        self.splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #4C566A;
                width: 1px;
            }
        """)
        
        # 初始化组件
        self.db_manager = db_manager
        self.init_components()
        
        # 将分割器添加到内容布局
        content_layout.addWidget(self.splitter, 1)
        
        # 将内容容器添加到主布局
        self.main_layout.addWidget(content_container, 1)
        
        # 设置主容器为中央部件
        self.setCentralWidget(main_container)
        
        # 用于窗口拖动
        self._drag_pos = None
        
        # 创建同步控制器
        self.prompt_sync = PromptSync()
        # 设置数据库管理器
        self.prompt_sync.set_db_manager(self.db_manager)
        
        # 连接响应收集信号
        self.prompt_sync.response_collected.connect(self.on_response_collected)
    
    def init_components(self):
        """初始化窗口组件"""
        # 设置全局滚动条样式
        self.setStyleSheet("""
            QScrollBar:vertical {
                background: #2E3440;
                width: 14px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #4C566A;
                min-height: 20px;
                border-radius: 7px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
            QScrollBar:horizontal {
                background: #2E3440;
                height: 14px;
                margin: 0px;
            }
            QScrollBar::handle:horizontal {
                background: #4C566A;
                min-width: 20px;
                border-radius: 7px;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
            }
        """)
        
        # 文件浏览器
        self.file_explorer = FileExplorer()
        
        # 添加特殊样式使标签页顶部没有边框
        self.file_explorer.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border-top: none;
                background-color: #2E3440;
            }
        """)
        
        # 创建自定义标题栏
        title_bar = QWidget()
        title_bar.setFixedHeight(38)
        title_bar.setObjectName("panelTitleBar")
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(8, 0, 8, 0)
        
        # 添加文件夹按钮 - 靠左显示
        add_folder_btn = QPushButton()
        add_folder_btn.setIcon(qta.icon('fa5s.folder-plus'))
        add_folder_btn.setToolTip("添加文件夹")
        add_folder_btn.clicked.connect(self.file_explorer.add_folder)
        
        # 设置按钮样式
        button_style = """
            QPushButton {
                background: transparent;
                border: none;
                padding: 6px 8px;
                margin: 0;
                color: #D8DEE9;
            }
            QPushButton:hover {
                background: #3B4252;
            }
        """
        add_folder_btn.setStyleSheet(button_style)
        
        # 添加按钮到标题栏（靠左）
        title_layout.addWidget(add_folder_btn)
        # 添加伸缩空间在按钮之后，使其余空间填充到右侧
        title_layout.addStretch(1)
        
        file_panel = PanelWidget("", self.file_explorer, self, custom_titlebar=title_bar)
        
        # 创建标签页控件
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        self.tabs.setDocumentMode(True)  # 使标签页更现代化
        
        # 标签页控件增加事件过滤器，用于实现拖拽窗口的功能
        self.tabs.tabBar().installEventFilter(self)
        
        # 自定义标签页样式，使其更像标题栏
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border-top: 1px solid #3B4252;
                background-color: #2E3440;
            }
            QTabWidget::tab-bar {
                alignment: left;
                background-color: #2E3440;
            }
            QTabBar {
                background-color: #2E3440;
                qproperty-drawBase: 0;
            }
            QTabBar::tab {
                background: #3B4252;
                color: #D8DEE9;
                padding: 0px 12px;
                border: none;
                margin-right: 2px;
                min-width: 10ex;
                height: 38px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background: #4C566A;
                color: #ECEFF4;
            }
            QTabBar::tab:hover:!selected {
                background: #434C5E;
            }
            QTabBar::close-button {
                image: none;
                background: transparent;
                border: none;
                margin: 0px;
                padding: 0px;
            }
            QTabBar::close-button:hover {
                background: #BF616A;
                border-radius: 2px;
            }
            /* 添加滚动条样式 */
            QScrollBar:vertical {
                background: #2E3440;
                width: 14px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #4C566A;
                min-height: 20px;
                border-radius: 7px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
            QScrollBar:horizontal {
                background: #2E3440;
                height: 14px;
                margin: 0px;
            }
            QScrollBar::handle:horizontal {
                background: #4C566A;
                min-width: 20px;
                border-radius: 7px;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
            }
        """)
        
        # 自定义标签页关闭按钮为qtawesome图标
        close_icon = qta.icon('fa5s.times', color='#D8DEE9')
        for i in range(self.tabs.count()):
            # 为已有标签页设置关闭图标
            if self.tabs.tabBar().tabButton(i, QTabWidget.ButtonPosition.RightSide):
                close_button = self.tabs.tabBar().tabButton(i, QTabWidget.ButtonPosition.RightSide)
                close_button.setIcon(close_icon)
        
        # 监听标签页添加事件，为新标签页设置关闭图标
        self.tabs.tabBarClicked.connect(self._check_tab_close_buttons)
        # 监听标签页添加事件
        self.tabs.currentChanged.connect(self._check_tab_close_buttons)
        
        # 创建提示词输入
        self.prompt_input = PromptInput()
        
        # 添加提示词标签页（不可关闭）
        prompt_idx = self.tabs.addTab(self.prompt_input, qta.icon('fa5s.keyboard', color='#81A1C1'), "提示词")
        
        # 设置提示词标签页不可关闭
        self.tabs.tabBar().setTabButton(prompt_idx, self.tabs.tabBar().ButtonPosition.RightSide, None)
        
        # 创建中间面板容器
        middle_container = QWidget()
        middle_container.setStyleSheet("background-color: #2E3440;")
        
        # 只设置一个垂直布局，不使用PanelWidget
        middle_layout = QVBoxLayout(middle_container)
        middle_layout.setContentsMargins(0, 0, 0, 0)
        middle_layout.setSpacing(0)
        
        # 将标签页直接添加到布局，它会成为"标题栏"
        middle_layout.addWidget(self.tabs)
        
        # 提示词历史记录（设置为控制面板，移回窗口控制按钮）
        self.prompt_history = PromptHistory(self.db_manager)
        history_panel = PanelWidget("历史记录", self.prompt_history, self, is_control_panel=True)
        
        # 添加面板到分割器
        self.splitter.addWidget(file_panel)
        self.splitter.addWidget(middle_container)  # 直接添加容器，不使用PanelWidget包装
        self.splitter.addWidget(history_panel)
        
        # 设置初始比例 (3:4:3)
        self.splitter.setSizes([300, 400, 300])
        
        # 连接信号
        self.prompt_input.prompt_submitted.connect(self.on_prompt_submitted)
        
        # 连接历史记录的选择信号
        self.prompt_history.prompt_selected.connect(self.prompt_input.set_text)
        
        # 连接历史记录的收藏切换信号
        self.prompt_history.favorite_toggled.connect(self.on_favorite_toggled)
        
        # 连接文件浏览器的fileOpenRequest信号到打开文件方法
        self.file_explorer.fileOpenRequest.connect(self.open_file)
        
        # 连接历史记录的open_urls信号到处理方法
        self.prompt_history.open_urls.connect(self.on_open_urls)
        
        # 连接历史记录的提示词设置请求信号
        self.prompt_history.request_set_prompt.connect(self.on_request_set_prompt)
    
    def on_prompt_submitted(self, prompt_text):
        """处理提示词提交事件"""
        # 不再使用旧的历史表保存方法
        # self.db_manager.add_prompt(prompt_text, ["ChatGPT", "DeepSeek"])
        
        # 直接同步提示词到主窗口的AI网页
        # prompt_sync.sync_prompt会处理存储到prompt_details表
        self.prompt_sync.sync_prompt(prompt_text)
        
        # 刷新历史记录
        self.prompt_history.refresh_history()
        
        # 清空输入框
        self.prompt_input.clear()
    
    def on_open_main_window(self):
        """处理打开主窗口的请求"""
        # 发射信号通知应用程序打开主窗口
        self.request_open_main_window.emit()
    
    def closeEvent(self, event):
        """处理窗口关闭事件"""
        super().closeEvent(event)

    # --- 窗口控制方法 ---
    def toggle_maximize(self):
        """切换窗口最大化状态"""
        if self.isMaximized():
            self.showNormal()
            self.maximize_button.setIcon(qta.icon('fa5s.window-maximize'))
        else:
            self.showMaximized()
            self.maximize_button.setIcon(qta.icon('fa5s.window-restore'))

    def mouseMoveEvent(self, event):
        """处理鼠标移动事件，用于窗口拖动"""
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos is not None:
            diff = event.globalPosition().toPoint() - self._drag_pos
            self.move(self.pos() + diff)
            self._drag_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        """处理鼠标释放事件"""
        self._drag_pos = None

    def open_file(self, file_path, file_type):
        """在新标签页中打开文件
        
        Args:
            file_path (str): 文件路径
            file_type (str): 文件类型
        """
        # 获取文件名
        file_name = os.path.basename(file_path)
        
        # 检查文件是否已经打开
        for i in range(self.tabs.count()):
            if self.tabs.tabText(i) == file_name:
                # 如果已打开，切换到对应标签
                self.tabs.setCurrentIndex(i)
                return
        
        # 创建文件查看器
        file_viewer = FileViewer()
        
        # 打开文件
        file_viewer.open_file(file_path, file_type)
        
        # 连接文件内容复制到提示词的信号
        file_viewer.file_content_to_prompt.connect(self.on_file_content_to_prompt)
        
        # 添加到标签页
        file_icon = self._get_file_icon(file_type)
        idx = self.tabs.addTab(file_viewer, file_icon, file_name)
        
        # 设置文件路径作为工具提示
        self.tabs.setTabToolTip(idx, file_path)
        
        # 切换到新标签页
        self.tabs.setCurrentIndex(idx)
    
    def close_tab(self, index):
        """关闭标签页
        
        Args:
            index (int): 标签页索引
        """
        # 不关闭提示词标签页（索引0）
        if index == 0:
            return
            
        # 关闭标签页
        self.tabs.removeTab(index)
    
    def _get_file_icon(self, file_type):
        """根据文件类型获取图标
        
        Args:
            file_type (str): 文件类型
            
        Returns:
            QIcon: 文件图标
        """
        icons = {
            'html': qta.icon('fa5s.file-code', color='#EBCB8B'),
            'markdown': qta.icon('fa5s.file-alt', color='#A3BE8C'),
            'text': qta.icon('fa5s.file-alt', color='#81A1C1'),
            'docx': qta.icon('fa5s.file-word', color='#5E81AC'),
            'powerpoint': qta.icon('fa5s.file-powerpoint', color='#D08770'),
            'excel': qta.icon('fa5s.file-excel', color='#A3BE8C'),
            'pdf': qta.icon('fa5s.file-pdf', color='#BF616A')
        }
        
        return icons.get(file_type, qta.icon('fa5s.file', color='#D8DEE9'))

    def on_file_content_to_prompt(self, content):
        """处理文件内容复制到提示词
        
        Args:
            content (str): 文件内容
        """
        # 设置提示词输入的内容
        self.prompt_input.set_text(content)
        
        # 切换到提示词标签页
        self.tabs.setCurrentIndex(0)

    def eventFilter(self, obj, event):
        """事件过滤器，处理标签栏的拖拽和双击事件"""
        try:
            # 如果是标签栏的事件
            if hasattr(self, 'tabs') and self.tabs and obj == self.tabs.tabBar():
                # 处理鼠标按下事件，用于拖动窗口
                if event.type() == event.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                    self._drag_pos = event.globalPosition().toPoint()
                    return False  # 继续处理事件
                    
                # 处理鼠标移动事件，实现拖动
                elif event.type() == event.Type.MouseMove and event.buttons() & Qt.MouseButton.LeftButton and self._drag_pos is not None:
                    diff = event.globalPosition().toPoint() - self._drag_pos
                    self.move(self.pos() + diff)
                    self._drag_pos = event.globalPosition().toPoint()
                    return True  # 事件已处理
                    
                # 处理鼠标释放事件
                elif event.type() == event.Type.MouseButtonRelease:
                    self._drag_pos = None
                    
                # 处理双击事件，实现最大化/还原
                elif event.type() == event.Type.MouseButtonDblClick and event.button() == Qt.MouseButton.LeftButton:
                    self.toggle_maximize()
                    return True  # 事件已处理
        except RuntimeError as e:
            # 捕获C++对象已删除异常
            print(f"事件过滤器错误: {e}")
            return False
        
        # 调用父类的事件过滤器
        return super().eventFilter(obj, event)

    def _check_tab_close_buttons(self, index):
        """检查并设置标签页关闭按钮图标"""
        try:
            # 为标签页设置qtawesome图标
            close_icon = qta.icon('fa5s.times', color='#D8DEE9')
            
            # 遍历所有标签页，检查是否有未设置图标的关闭按钮
            for i in range(self.tabs.count()):
                close_button = self.tabs.tabBar().tabButton(i, self.tabs.tabBar().ButtonPosition.RightSide)
                if close_button and close_button.icon().isNull():
                    close_button.setIcon(close_icon)
                    close_button.setText("")  # 移除文本，只显示图标
                    close_button.setIconSize(QSize(12, 12))  # 设置合适的图标大小
        except (RuntimeError, AttributeError) as e:
            # 捕获可能的运行时错误
            print(f"设置标签页关闭按钮时出错: {e}")

    def on_response_collected(self, prompt_id, responses):
        """处理收集到的AI回复
        
        Args:
            prompt_id (str): 提示词ID
            responses (list): 响应信息列表
        """
        print(f"收集到AI回复，ID: {prompt_id}, 共{len(responses)}个回复")
        # 收集完成后，刷新历史记录区域
        self.prompt_history.refresh_history()

    def on_favorite_toggled(self, prompt_id, is_favorite):
        """处理提示词收藏状态切换
        
        Args:
            prompt_id (str): 提示词ID
            is_favorite (bool): 新的收藏状态
        """
        # 可以在这里添加额外的操作，如通知或UI更新
        favorite_status = "收藏" if is_favorite else "取消收藏"
        print(f"提示词 {prompt_id} 已{favorite_status}") 

    def on_open_urls(self, urls):
        """处理打开多个URL的请求
        
        Args:
            urls (list): 要打开的URL列表
        """
        if not urls:
            print("没有URL可以打开")
            return
            
        print(f"辅助窗口收到打开URLs请求: {urls}")
        
        # 获取主窗口
        main_window = None
        for window in QApplication.topLevelWidgets():
            if window.__class__.__name__ == "MainWindow":
                main_window = window
                break
                
        if not main_window:
            print("找不到主窗口，无法打开URLs")
            return
            
        # 获取主窗口中的AI视图
        ai_view = main_window.get_ai_view()
        if not ai_view:
            print("找不到AI视图，无法打开URLs")
            return
            
        # 如果窗口没有显示，则显示它，但不要改变其位置和大小
        if not main_window.isVisible():
            main_window.show()
            main_window.activateWindow()
        elif main_window.isMinimized():
            # 如果窗口最小化了，只恢复它，不要最大化
            main_window.showNormal()
            main_window.activateWindow()
        else:
            # 窗口已经可见，只需要激活它
            main_window.activateWindow()
            
        # 请求AI视图打开所有URL
        ai_view.open_multiple_urls(urls) 

    def on_request_set_prompt(self, prompt_text):
        """处理设置提示词内容的请求
        
        Args:
            prompt_text (str): 要设置的提示词文本
        """
        # 检查当前提示词输入区是否有内容
        current_text = self.prompt_input.get_text()
        
        if current_text and current_text.strip():
            # 如果已有内容，弹出确认对话框
            msg_box = QMessageBox()
            msg_box.setWindowTitle("确认替换")
            msg_box.setText("提示词输入区已有内容。")
            msg_box.setInformativeText("是否要用历史记录中的内容替换当前内容？")
            msg_box.setIcon(QMessageBox.Icon.Question)
            msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            msg_box.setDefaultButton(QMessageBox.StandardButton.No)
            
            # 设置对话框样式
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #2E3440;
                    color: #D8DEE9;
                }
                QLabel {
                    color: #E5E9F0;
                }
                QPushButton {
                    background-color: #4C566A;
                    color: #E5E9F0;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 12px;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #5E81AC;
                }
                QPushButton:pressed {
                    background-color: #81A1C1;
                }
            """)
            
            # 显示对话框并获取用户选择
            response = msg_box.exec()
            
            # 如果用户选择"否"，则不替换
            if response == QMessageBox.StandardButton.No:
                return
        
        # 设置提示词内容
        self.prompt_input.set_text(prompt_text)
        
        # 切换到提示词标签页
        self.tabs.setCurrentIndex(0) 