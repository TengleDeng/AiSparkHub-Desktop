#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal
import qtawesome as qta
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from app.controllers.theme_manager import ThemeManager

class PromptInput(QWidget):
    """提示词输入组件"""
    
    # 定义信号
    prompt_submitted = pyqtSignal(str)  # 提示词提交信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
        # 获取 ThemeManager 并连接信号
        self.theme_manager = None
        app = QApplication.instance()
        if hasattr(app, 'theme_manager') and isinstance(app.theme_manager, ThemeManager):
            self.theme_manager = app.theme_manager
            self.theme_manager.theme_changed.connect(self._update_button_icon)
            QTimer.singleShot(0, self._update_button_icon) # 设置初始图标
        else:
            print("警告：无法在 PromptInput 中获取 ThemeManager 实例")
            QTimer.singleShot(0, self._update_button_icon) # 尝试用默认色
    
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
        self.send_button.clicked.connect(self.submit_prompt)
        layout.addWidget(self.send_button)
        
        # 设置快捷键
        self.text_edit.installEventFilter(self)
    
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
    
    def get_text(self):
        """获取输入框文本
        
        Returns:
            str: 当前输入框的文本内容
        """
        return self.text_edit.toPlainText()
    
    def eventFilter(self, obj, event):
        """事件过滤器，处理快捷键"""
        if obj == self.text_edit and event.type() == event.Type.KeyPress:
            # Ctrl+Enter 发送提示词
            if event.key() == Qt.Key.Key_Return and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                self.submit_prompt()
                return True
        return super().eventFilter(obj, event)
        
    # 新增方法：更新发送按钮图标颜色
    def _update_button_icon(self):
        print("PromptInput: 更新发送按钮图标颜色...")
        icon_color = '#88C0D0' # Default accent color
        if self.theme_manager:
            theme_colors = self.theme_manager.get_current_theme_colors()
            icon_color = theme_colors.get('accent', icon_color) # 使用 accent 颜色
        else:
            # Fallback for light theme if no manager
             app = QApplication.instance()
             if hasattr(app, 'palette') and app.palette().window().color().lightnessF() > 0.5: # 检查全局调色板
                 icon_color = '#5E81AC' # Darker accent for light mode
                 
        if hasattr(self, 'send_button'):
            try:
                self.send_button.setIcon(qta.icon("fa5s.paper-plane", color=icon_color))
                print("PromptInput: 发送按钮图标颜色更新完成")
            except Exception as e:
                print(f"PromptInput: 更新图标时出错 - {e}")
        else:
             print("PromptInput: send_button 尚未初始化") 