#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import QMainWindow, QWidget, QHBoxLayout
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
        
        # 设置图标
        self.setWindowIcon(qta.icon('fa5s.keyboard', color='#88C0D0'))
        
        # 创建中央窗口部件
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # 创建主布局
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # 初始化组件
        self.db_manager = db_manager
        self.init_components()
        
        # 设置状态栏
        self.statusBar().showMessage("就绪")
    
    def init_components(self):
        """初始化窗口组件"""
        # 文件浏览器 (左侧 30%)
        self.file_explorer = FileExplorer()
        self.main_layout.addWidget(self.file_explorer, 30)
        
        # 提示词输入区 (中间 40%)
        self.prompt_input = PromptInput()
        self.main_layout.addWidget(self.prompt_input, 40)
        
        # 提示词历史记录 (右侧 30%)
        self.prompt_history = PromptHistory(self.db_manager)
        self.main_layout.addWidget(self.prompt_history, 30)
        
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