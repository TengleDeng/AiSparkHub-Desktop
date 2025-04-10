#!/usr/bin/env python
# -*- coding: utf-8 -*-

# auxiliary_window.py: 定义 AuxiliaryWindow 类
# 该窗口作为辅助窗口，包含文件浏览器、提示词输入框和提示词历史记录。
# 用于管理和同步提示词到主窗口的 AI 对话页面。

from PyQt6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QPushButton, QVBoxLayout, QLabel, QSplitter, QFrame, QToolBar, QStackedWidget
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QSize
import qtawesome as qta

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
    
    def __init__(self, title, content_widget, window=None, is_control_panel=False):
        super().__init__()
        self.window = window
        self.is_control_panel = is_control_panel
        
        # 创建垂直布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
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
            
        # 创建分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Plain)
        separator.setLineWidth(0)
        separator.setMidLineWidth(1)
        separator.setStyleSheet("color: #4C566A;")
        
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
    
    def init_components(self):
        """初始化窗口组件"""
        # 文件浏览器
        self.file_explorer = FileExplorer()
        file_panel = PanelWidget("文件浏览", self.file_explorer, self)
        
        # 创建中间面板 - 包含文件查看器和提示词输入
        middle_container = QWidget()
        middle_layout = QVBoxLayout(middle_container)
        middle_layout.setContentsMargins(0, 0, 0, 0)
        middle_layout.setSpacing(0)
        
        # 创建工具栏，用于在文件查看时提供返回按钮
        self.file_toolbar = QToolBar()
        self.file_toolbar.setIconSize(QSize(16, 16))
        self.file_toolbar.setStyleSheet("""
            QToolBar {
                background-color: #3B4252;
                border: none;
                spacing: 4px;
                padding: 4px;
            }
            QToolButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
                padding: 4px;
            }
            QToolButton:hover {
                background-color: #4C566A;
            }
        """)
        
        # 添加返回按钮
        self.back_to_prompt_action = self.file_toolbar.addAction(
            qta.icon('fa5s.arrow-left', color='#D8DEE9'), 
            "返回到提示词输入"
        )
        self.back_to_prompt_action.triggered.connect(self.switch_to_prompt_input)
        
        # 初始隐藏工具栏
        self.file_toolbar.setVisible(False)
        middle_layout.addWidget(self.file_toolbar)
        
        # 创建一个堆叠小部件，用于切换文件查看器和提示词输入
        self.middle_stack = QStackedWidget()
        
        # 创建文件查看器
        self.file_viewer = FileViewer()
        self.middle_stack.addWidget(self.file_viewer)
        
        # 创建提示词输入
        self.prompt_input = PromptInput()
        self.middle_stack.addWidget(self.prompt_input)
        
        # 默认显示提示词输入
        self.middle_stack.setCurrentWidget(self.prompt_input)
        
        # 添加堆叠小部件到中间布局
        middle_layout.addWidget(self.middle_stack)
        
        # 创建中间面板
        middle_panel = PanelWidget("提示词输入", middle_container, self)
        
        # 提示词历史记录 (作为控制面板，包含窗口控制按钮)
        self.prompt_history = PromptHistory(self.db_manager)
        history_panel = PanelWidget("历史记录", self.prompt_history, self, is_control_panel=True)
        
        # 添加面板到分割器
        self.splitter.addWidget(file_panel)
        self.splitter.addWidget(middle_panel)
        self.splitter.addWidget(history_panel)
        
        # 设置初始比例 (3:4:3)
        self.splitter.setSizes([300, 400, 300])
        
        # 连接信号
        self.prompt_input.prompt_submitted.connect(self.on_prompt_submitted)
        
        # 连接历史记录的选择信号
        self.prompt_history.prompt_selected.connect(self.prompt_input.set_text)
        
        # 连接文件浏览器的fileOpenRequest信号到打开文件方法
        self.file_explorer.fileOpenRequest.connect(self.open_file)
        
        # 连接文件查看器的file_content_to_prompt信号到提示词输入
        self.file_viewer.file_content_to_prompt.connect(self.on_file_content_to_prompt)
        
        # 创建同步控制器
        self.prompt_sync = PromptSync()
    
    def on_prompt_submitted(self, prompt_text):
        """处理提示词提交事件"""
        # 将提示词存储到数据库
        self.db_manager.add_prompt(prompt_text, ["ChatGPT", "DeepSeek"])
        
        # 同步提示词到主窗口的AI网页
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
        """打开文件
        
        Args:
            file_path (str): 文件路径
            file_type (str): 文件类型
        """
        # 打开文件到文件查看器
        self.file_viewer.open_file(file_path, file_type)
        
        # 切换到文件查看器
        self.middle_stack.setCurrentWidget(self.file_viewer)
        
        # 显示工具栏
        self.file_toolbar.setVisible(True)
        
        # 更新面板标题
        middle_panel = self.splitter.widget(1)  # 中间面板索引为1
        if isinstance(middle_panel, PanelWidget):
            title_label = middle_panel.title_bar.findChild(QLabel)
            if title_label:
                title_label.setText("文件查看")
                
    def switch_to_prompt_input(self):
        """切换到提示词输入"""
        self.middle_stack.setCurrentWidget(self.prompt_input)
        
        # 隐藏工具栏
        self.file_toolbar.setVisible(False)
        
        # 更新面板标题
        middle_panel = self.splitter.widget(1)  # 中间面板索引为1
        if isinstance(middle_panel, PanelWidget):
            title_label = middle_panel.title_bar.findChild(QLabel)
            if title_label:
                title_label.setText("提示词输入")
    
    def on_file_content_to_prompt(self, content):
        """处理文件内容复制到提示词
        
        Args:
            content (str): 文件内容
        """
        # 设置提示词输入的内容
        self.prompt_input.set_text(content)
        
        # 切换到提示词输入
        self.switch_to_prompt_input() 