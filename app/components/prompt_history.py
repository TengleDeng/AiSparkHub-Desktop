#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QListWidget, QListWidgetItem,
                           QLineEdit, QLabel)
from PyQt6.QtCore import Qt, pyqtSignal
import qtawesome as qta
from datetime import datetime

class PromptHistoryItem(QListWidgetItem):
    """提示词历史记录项"""
    
    def __init__(self, prompt_data):
        super().__init__()
        self.prompt_data = prompt_data
        self.setup_display()
    
    def setup_display(self):
        """设置显示内容"""
        # 获取时间戳
        timestamp = datetime.fromisoformat(self.prompt_data['timestamp'])
        time_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        
        # 设置显示文本
        display_text = f"{time_str}\n{self.prompt_data['prompt_text'][:100]}..."
        self.setText(display_text)
        
        # 设置工具提示
        tooltip = f"目标AI: {', '.join(self.prompt_data['ai_targets'])}\n"
        tooltip += f"完整内容:\n{self.prompt_data['prompt_text']}"
        self.setToolTip(tooltip)

class PromptHistory(QWidget):
    """提示词历史记录组件"""
    
    # 定义信号
    prompt_selected = pyqtSignal(str)  # 提示词选中信号
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setup_ui()
        self.refresh_history()
    
    def setup_ui(self):
        """设置UI界面"""
        # 创建布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # 创建搜索框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索历史记录...")
        self.search_input.textChanged.connect(self.search_history)
        layout.addWidget(self.search_input)
        
        # 创建列表
        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self.on_item_double_clicked)
        layout.addWidget(self.list_widget)
        
        # 设置样式
        self.setStyleSheet("""
            QLineEdit {
                background-color: #2E3440;
                color: #D8DEE9;
                border: 1px solid #3B4252;
                border-radius: 4px;
                padding: 8px;
            }
            QListWidget {
                background-color: #2E3440;
                color: #D8DEE9;
                border: 1px solid #3B4252;
                border-radius: 4px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #3B4252;
            }
            QListWidget::item:hover {
                background-color: #3B4252;
            }
            QListWidget::item:selected {
                background-color: #4C566A;
            }
        """)
    
    def refresh_history(self):
        """刷新历史记录"""
        self.list_widget.clear()
        history = self.db_manager.get_prompt_history()
        for prompt_data in history:
            item = PromptHistoryItem(prompt_data)
            self.list_widget.addItem(item)
    
    def search_history(self, text):
        """搜索历史记录"""
        if not text:
            self.refresh_history()
            return
        
        self.list_widget.clear()
        results = self.db_manager.search_prompts(text)
        for prompt_data in results:
            item = PromptHistoryItem(prompt_data)
            self.list_widget.addItem(item)
    
    def on_item_double_clicked(self, item):
        """处理项目双击事件"""
        if isinstance(item, PromptHistoryItem):
            self.prompt_selected.emit(item.prompt_data['prompt_text']) 