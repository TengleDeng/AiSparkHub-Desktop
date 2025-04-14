#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTextEdit, QPushButton, 
                           QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem, 
                           QLabel, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QColor
import qtawesome as qta
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from app.controllers.theme_manager import ThemeManager

class PromptInput(QWidget):
    """提示词输入组件"""
    
    # 定义信号
    prompt_submitted = pyqtSignal(str)  # 提示词提交信号
    
    def __init__(self, parent=None, db_manager=None):
        super().__init__(parent)
        self.db_manager = db_manager  # 数据库管理器
        self.setup_ui()
        
        # 获取 ThemeManager 并连接信号
        self.theme_manager = None
        app = QApplication.instance()
        if hasattr(app, 'theme_manager') and isinstance(app.theme_manager, ThemeManager):
            self.theme_manager = app.theme_manager
            self.theme_manager.theme_changed.connect(self._update_icons)
            QTimer.singleShot(0, self._update_icons) # 设置初始图标
        else:
            print("警告：无法在 PromptInput 中获取 ThemeManager 实例")
            QTimer.singleShot(0, self._update_icons) # 尝试用默认色
    
    def setup_ui(self):
        """设置UI界面"""
        # 创建主布局
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(8)
        
        # 创建文本输入框
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("在此输入提示词...")
        self.text_edit.setAcceptRichText(False)  # 只接受纯文本
        self.layout.addWidget(self.text_edit)
        
        # 创建搜索框区域
        search_layout = QHBoxLayout()
        search_layout.setContentsMargins(0, 5, 0, 5)
        search_layout.setSpacing(8)
        
        # 添加搜索框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索提示词和AI回复...")
        self.search_input.returnPressed.connect(self.search_prompts)
        search_layout.addWidget(self.search_input, 1)  # 1表示拉伸因子
        
        # 创建按钮容器 (搜索和发送)
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(8)
        
        # 添加搜索按钮
        self.search_button = QPushButton()
        self.search_button.setToolTip("搜索提示词和AI回复")
        self.search_button.clicked.connect(self.search_prompts)
        button_layout.addWidget(self.search_button)
        
        # 添加发送按钮
        self.send_button = QPushButton("发送")
        self.send_button.clicked.connect(self.submit_prompt)
        button_layout.addWidget(self.send_button)
        
        # 将按钮布局添加到搜索布局
        search_layout.addLayout(button_layout)
        
        # 将搜索布局添加到主布局
        self.layout.addLayout(search_layout)
        
        # 添加搜索结果列表
        self.search_results = QListWidget()
        self.search_results.setMaximumHeight(300)  # 增加最大高度
        self.search_results.setMinimumHeight(200)  # 设置最小高度
        self.search_results.setVisible(False)  # 初始隐藏
        self.search_results.itemClicked.connect(self.on_search_result_selected)
        self.search_results.setFrameShape(QFrame.Shape.StyledPanel)
        self.search_results.setFrameShadow(QFrame.Shadow.Sunken)
        self.search_results.setStyleSheet("""
            QListWidget {
                border: 1px solid #4C566A;
                border-radius: 4px;
                padding: 2px;
            }
            QListWidget::item {
                border-bottom: 1px solid #3B4252;
                padding: 5px;
            }
            QListWidget::item:selected {
                background-color: #5E81AC;
                color: #ECEFF4;
            }
        """)
        self.layout.addWidget(self.search_results)
        
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
        # 隐藏搜索结果
        self.search_results.setVisible(False)
    
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
    
    def search_prompts(self):
        """搜索提示词和AI回复"""
        if not self.db_manager:
            print("错误：未设置数据库管理器，无法进行搜索")
            return
            
        search_text = self.search_input.text().strip()
        if not search_text:
            self.search_results.clear()
            self.search_results.setVisible(False)
            return
            
        # 执行搜索
        try:
            results = self.db_manager.search_prompt_details(search_text)
            
            # 清空并填充结果列表
            self.search_results.clear()
            
            # 获取当前主题颜色
            header_bg = '#2E3440'  # 深色主题默认颜色
            item_bg_1 = '#3B4252'
            item_bg_2 = '#434C5E'
            text_color = '#D8DEE9'
            
            if self.theme_manager and self.theme_manager.current_theme == "light":
                header_bg = '#D8DEE9'  # 浅色主题颜色
                item_bg_1 = '#E5E9F0'
                item_bg_2 = '#ECEFF4'
                text_color = '#2E3440'
            
            # 添加搜索结果统计信息
            result_count = len(results)
            count_item = QListWidgetItem(f"找到 {result_count} 条匹配结果")
            count_item.setFlags(Qt.ItemFlag.NoItemFlags)  # 设置为不可选
            count_item.setBackground(QColor(header_bg))
            count_item.setForeground(QColor(text_color))
            # 使标题文本居中
            count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.search_results.addItem(count_item)
            
            if results:
                for i, result in enumerate(results):
                    # 创建列表项
                    item = QListWidgetItem()
                    
                    # 设置项目样式 - 根据主题设置交替背景色
                    if i % 2 == 0:
                        item.setBackground(QColor(item_bg_1))
                    else:
                        item.setBackground(QColor(item_bg_2))
                    
                    # 限制显示长度
                    prompt = result['prompt']
                    if len(prompt) > 60:
                        display_text = prompt[:60] + "..."
                    else:
                        display_text = prompt
                        
                    # 添加序号
                    display_text = f"{i+1}. {display_text}"
                        
                    # 可能的匹配回复片段
                    match_reply = ""
                    for webview in result['webviews']:
                        reply = webview.get('reply', '')
                        if reply and search_text.lower() in reply.lower():
                            # 从匹配部分附近提取一小段文本
                            idx = reply.lower().find(search_text.lower())
                            start = max(0, idx - 20)
                            end = min(len(reply), idx + len(search_text) + 20)
                            match_reply = "..." + reply[start:end] + "..."
                            break
                            
                    # 如果在回复中找到匹配，添加到显示文本
                    if match_reply:
                        display_text += f"\n匹配回复: {match_reply}"
                    
                    item.setText(display_text)
                    item.setData(Qt.ItemDataRole.UserRole, result)  # 存储完整数据
                    self.search_results.addItem(item)
                
                self.search_results.setVisible(True)
            else:
                # 添加"无结果"提示
                item = QListWidgetItem("没有找到匹配的结果")
                item.setFlags(Qt.ItemFlag.NoItemFlags)  # 使项目不可选
                item.setBackground(QColor(item_bg_1))
                item.setForeground(QColor(text_color))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.search_results.addItem(item)
                self.search_results.setVisible(True)
                
        except Exception as e:
            print(f"搜索出错: {e}")
            # 添加错误提示
            self.search_results.clear()
            item = QListWidgetItem(f"搜索时出错: {str(e)}")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            item.setBackground(QColor("#BF616A"))  # 使用主题的红色
            item.setForeground(QColor("#ECEFF4"))  # 白色文字
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.search_results.addItem(item)
            self.search_results.setVisible(True)
    
    def on_search_result_selected(self, item):
        """处理搜索结果选择"""
        data = item.data(Qt.ItemDataRole.UserRole)
        if data and 'prompt' in data:
            # 设置提示词内容
            self.text_edit.setText(data['prompt'])
            # 隐藏搜索结果
            self.search_results.setVisible(False)
            # 清空搜索框
            self.search_input.clear()
            # 设置焦点到文本框
            self.text_edit.setFocus()
        
    # 更新图标颜色
    def _update_icons(self):
        print("PromptInput: 更新图标颜色...")
        # 获取当前主题颜色
        icon_color = '#88C0D0'  # 默认强调色
        button_bg = '#2E3440'   # 默认按钮背景色
        
        if self.theme_manager:
            theme_colors = self.theme_manager.get_current_theme_colors()
            icon_color = theme_colors.get('accent', icon_color)
            button_bg = theme_colors.get('secondary_bg', button_bg)
        
        # 更新发送按钮图标
        if hasattr(self, 'send_button'):
            try:
                self.send_button.setIcon(qta.icon("fa5s.paper-plane", color=icon_color))
            except Exception as e:
                print(f"更新发送按钮图标出错: {e}")
                
        # 更新搜索按钮图标
        if hasattr(self, 'search_button'):
            try:
                self.search_button.setIcon(qta.icon("fa5s.search", color=icon_color))
            except Exception as e:
                print(f"更新搜索按钮图标出错: {e}")
                
        print("PromptInput: 图标颜色更新完成") 