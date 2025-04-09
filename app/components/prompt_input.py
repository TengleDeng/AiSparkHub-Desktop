#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal
import qtawesome as qta

class PromptInput(QWidget):
    """提示词输入组件"""
    
    # 定义信号
    prompt_submitted = pyqtSignal(str)  # 提示词提交信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI界面"""
        # 创建布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # 创建文本输入框
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("在此输入提示词...")
        self.text_edit.setAcceptRichText(False)  # 只接受纯文本
        layout.addWidget(self.text_edit)
        
        # 创建发送按钮
        self.send_button = QPushButton("发送")
        self.send_button.setIcon(qta.icon("fa5s.paper-plane", color="#88C0D0"))
        self.send_button.clicked.connect(self.submit_prompt)
        layout.addWidget(self.send_button)
        
        # 设置快捷键
        self.text_edit.installEventFilter(self)
        
        # 设置样式
        self.setStyleSheet("""
            QTextEdit {
                background-color: #2E3440;
                color: #D8DEE9;
                border: 1px solid #3B4252;
                border-radius: 4px;
                padding: 8px;
            }
            QPushButton {
                background-color: #5E81AC;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #81A1C1;
            }
            QPushButton:pressed {
                background-color: #4C566A;
            }
        """)
    
    def submit_prompt(self):
        """提交提示词"""
        text = self.text_edit.toPlainText().strip()
        if text:
            self.prompt_submitted.emit(text)
    
    def clear(self):
        """清空输入框"""
        self.text_edit.clear()
    
    def set_text(self, text):
        """设置输入框文本"""
        self.text_edit.setPlainText(text)
    
    def eventFilter(self, obj, event):
        """事件过滤器，处理快捷键"""
        if obj == self.text_edit and event.type() == event.Type.KeyPress:
            # Ctrl+Enter 发送提示词
            if event.key() == Qt.Key.Key_Return and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                self.submit_prompt()
                return True
        return super().eventFilter(obj, event) 