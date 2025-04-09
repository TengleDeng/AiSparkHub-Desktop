#!/usr/bin/env python
# -*- coding: utf-8 -*-

# auxiliary_window.py: 定义 AuxiliaryWindow 类
# 该窗口作为辅助窗口，包含文件浏览器、提示词输入框和提示词历史记录。
# 用于管理和同步提示词到主窗口的 AI 对话页面。

from PyQt6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QPushButton, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt
import qtawesome as qta

from app.components.file_explorer import FileExplorer
from app.components.prompt_input import PromptInput
from app.components.prompt_history import PromptHistory
from app.controllers.prompt_sync import PromptSync

class AuxiliaryWindow(QMainWindow):
    """辅助窗口类 - 包含文件浏览、提示词输入和历史记录"""
    
    def __init__(self, db_manager):
        super().__init__()
        self.setWindowTitle("AiSparkHub - 提示词管理")
        self.setMinimumSize(1000, 300)
        
        # 设置无边框窗口
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        
        # 设置图标 (虽然无边框，但任务栏可能需要)
        self.setWindowIcon(qta.icon('fa5s.keyboard', color='#88C0D0'))
        
        # 创建主容器和主垂直布局
        main_container = QWidget()
        self.main_layout = QVBoxLayout(main_container)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # 创建标题栏
        self.title_bar = QWidget()
        self.title_bar.setFixedHeight(38) # 固定高度
        self.title_bar.setObjectName("auxiliaryTitleBar") # 添加对象名以便样式化
        title_bar_layout = QHBoxLayout(self.title_bar)
        title_bar_layout.setContentsMargins(8, 0, 0, 0) # 左边距8，右边距0
        title_bar_layout.setSpacing(8) # 控件间距

        # 创建并添加标题标签
        self.file_title = QLabel("文件浏览")
        self.prompt_title = QLabel("提示词输入")
        self.history_title = QLabel("历史记录")

        # 设置标题标签样式
        title_style = "QLabel { color: #D8DEE9; font-weight: bold; }"
        self.file_title.setStyleSheet(title_style)
        self.prompt_title.setStyleSheet(title_style)
        self.history_title.setStyleSheet(title_style)
        self.file_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.prompt_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.history_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 添加标题到布局，使用 addWidget 控制拉伸比例 (大致模拟 3:4:3)
        title_bar_layout.addWidget(self.file_title, 3)
        # title_bar_layout.addStretch(1) # 添加少量间隔
        title_bar_layout.addWidget(self.prompt_title, 4)
        # title_bar_layout.addStretch(1) # 添加少量间隔
        title_bar_layout.addWidget(self.history_title, 3)

        # title_bar_layout.addStretch() # 移除这个，让按钮紧跟最后一个标题

        # 创建窗口控制按钮
        self.minimize_button = QPushButton()
        self.minimize_button.setIcon(qta.icon('fa5s.window-minimize'))
        self.minimize_button.clicked.connect(self.showMinimized)
        
        self.maximize_button = QPushButton()
        self.maximize_button.setIcon(qta.icon('fa5s.window-maximize'))
        self.maximize_button.clicked.connect(self.toggle_maximize)
        
        self.close_button = QPushButton()
        self.close_button.setIcon(qta.icon('fa5s.times'))
        self.close_button.clicked.connect(self.close)
        
        # 设置按钮样式 (与 MainWindow 一致)
        button_style = """
            QPushButton {
                background: transparent;
                border: none;
                padding: 8px 12px;
                margin: 0;
            }
            QPushButton:hover {
                background: #3B4252;
            }
        """
        close_button_style = button_style + """
            QPushButton:hover {
                background: #BF616A; /* 红色悬停 */
            }
        """
        self.minimize_button.setStyleSheet(button_style)
        self.maximize_button.setStyleSheet(button_style)
        self.close_button.setStyleSheet(close_button_style)
        
        # 添加按钮到标题栏
        title_bar_layout.addWidget(self.minimize_button) # 不带拉伸比例
        title_bar_layout.addWidget(self.maximize_button)
        title_bar_layout.addWidget(self.close_button)

        # 设置标题栏背景色 (通过样式表)
        self.title_bar.setStyleSheet("""
            #auxiliaryTitleBar {
                background-color: #2E3440;
            }
        """ + title_style) # 合并样式

        # 将标题栏添加到主垂直布局
        self.main_layout.addWidget(self.title_bar)
        
        # --- 原有的内容部分 ---
        # 创建内容容器和水平布局
        content_widget = QWidget()
        self.content_layout = QHBoxLayout(content_widget) # 使用新的 content_layout
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        
        # 初始化组件 (将添加到 content_layout)
        self.db_manager = db_manager
        self.init_components() # 这个方法现在会将组件添加到 self.content_layout
        
        # 将内容容器添加到主垂直布局
        self.main_layout.addWidget(content_widget)
        # --- 内容部分结束 ---
        
        # 设置主容器为中央部件
        self.setCentralWidget(main_container)
        
        # 设置状态栏 (可选，无边框窗口通常不显示，但可以保留逻辑)
        # self.statusBar().showMessage("就绪")
        
        # 用于窗口拖动
        self._drag_pos = None
    
    def init_components(self):
        """初始化窗口组件 (添加到 content_layout)"""
        # 文件浏览器 (左侧 30%)
        self.file_explorer = FileExplorer()
        self.content_layout.addWidget(self.file_explorer, 30) # 注意是 content_layout
        
        # 提示词输入区 (中间 40%)
        self.prompt_input = PromptInput()
        self.content_layout.addWidget(self.prompt_input, 40) # 注意是 content_layout
        
        # 提示词历史记录 (右侧 30%)
        self.prompt_history = PromptHistory(self.db_manager)
        self.content_layout.addWidget(self.prompt_history, 30) # 注意是 content_layout
        
        # 初始化提示词同步管理器
        self.prompt_sync = PromptSync()
        
        # 连接信号和槽
        self.prompt_input.prompt_submitted.connect(self.on_prompt_submitted)
        self.prompt_history.prompt_selected.connect(self.prompt_input.set_text)
    
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
    
    def closeEvent(self, event):
        """处理窗口关闭事件"""
        super().closeEvent(event)

    # --- 添加与 MainWindow 类似的窗口控制方法 ---
    def toggle_maximize(self):
        """切换窗口最大化状态"""
        if self.isMaximized():
            self.showNormal()
            self.maximize_button.setIcon(qta.icon('fa5s.window-maximize'))
        else:
            self.showMaximized()
            self.maximize_button.setIcon(qta.icon('fa5s.window-restore'))

    def mousePressEvent(self, event):
        """处理鼠标按下事件，用于窗口拖动"""
        if event.button() == Qt.MouseButton.LeftButton:
            # 只有在标题栏区域按下才记录拖动位置
            if self.title_bar.geometry().contains(event.position().toPoint()):
                 self._drag_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        """处理鼠标移动事件，用于窗口拖动"""
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos is not None:
            diff = event.globalPosition().toPoint() - self._drag_pos
            self.move(self.pos() + diff)
            self._drag_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        """处理鼠标释放事件"""
        self._drag_pos = None

    def mouseDoubleClickEvent(self, event):
        """处理鼠标双击事件，用于最大化/还原窗口"""
        if event.button() == Qt.MouseButton.LeftButton:
            # 只有双击标题栏区域才触发
            if self.title_bar.geometry().contains(event.position().toPoint()):
                self.toggle_maximize()
            else:
                super().mouseDoubleClickEvent(event)
        else:
            super().mouseDoubleClickEvent(event) 