#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTextEdit, QPushButton, 
                           QHBoxLayout, QToolBar, QFileDialog, QMessageBox,
                           QFontComboBox, QComboBox, QSpinBox, QStackedWidget)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QTextCharFormat, QFont, QTextCursor, QColor, QAction
import qtawesome as qta
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from app.controllers.theme_manager import ThemeManager
import os
import re
import markdown
from markdown.extensions.tables import TableExtension
from markdown.extensions.fenced_code import FencedCodeExtension
from PyQt6.QtWebEngineWidgets import QWebEngineView

class MarkdownEditor(QWidget):
    """Markdown编辑器组件，用于编辑和提交Markdown格式的提示词"""
    
    # 定义信号
    prompt_submitted = pyqtSignal(str)  # 提示词提交信号
    text_changed = pyqtSignal()  # 文本变更信号
    
    def __init__(self, parent=None, db_manager=None):
        super().__init__(parent)
        self.db_manager = db_manager  # 数据库管理器
        self.current_file_path = None  # 当前文件路径
        self.is_modified = False  # 文件是否被修改
        
        # 获取 ThemeManager 并连接信号
        self.theme_manager = None
        app = QApplication.instance()
        if hasattr(app, 'theme_manager') and isinstance(app.theme_manager, ThemeManager):
            self.theme_manager = app.theme_manager
            self.theme_manager.theme_changed.connect(self._update_icons)
            QTimer.singleShot(0, self._update_icons)  # 设置初始图标
        else:
            print("警告：无法在 MarkdownEditor 中获取 ThemeManager 实例")
            QTimer.singleShot(0, self._update_icons)  # 尝试用默认色
            
        self.setup_ui()
        
    def setup_ui(self):
        """设置UI界面"""
        # 创建主布局
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # 创建工具栏
        self.toolbar = QToolBar("Markdown工具栏")
        self.toolbar.setIconSize(QSize(18, 18))
        self.toolbar.setMovable(False)
        self.layout.addWidget(self.toolbar)
        
        # 添加工具栏按钮和功能
        self._setup_toolbar()
        
        # 创建堆叠部件，用于切换编辑和预览模式
        self.stacked_widget = QStackedWidget()
        
        # 创建文本输入框
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("在此输入Markdown格式的提示词...")
        self.text_edit.setAcceptRichText(False)  # 只接受纯文本
        self.text_edit.textChanged.connect(self._on_text_changed)
        
        # 设置编辑器字体
        font = QFont("Consolas", 11)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.text_edit.setFont(font)
        
        # 创建预览视图
        self.preview_view = QWebEngineView()
        
        # 设置预览视图样式
        self.preview_view.setStyleSheet("""
            QWebEngineView {
                background-color: #ECEFF4;
                border: none;
                padding: 10px;
            }
        """)
        
        # 添加到堆叠部件
        self.stacked_widget.addWidget(self.text_edit)
        self.stacked_widget.addWidget(self.preview_view)
        
        # 默认显示编辑模式
        self.stacked_widget.setCurrentIndex(0)
        self.is_preview_mode = False
        
        self.layout.addWidget(self.stacked_widget, 1)  # 1表示拉伸因子
        
        # 设置快捷键
        self.text_edit.installEventFilter(self)
        
        # 自动保存定时器
        self.auto_save_timer = QTimer(self)
        self.auto_save_timer.setInterval(60000)  # 60秒
        self.auto_save_timer.timeout.connect(self._auto_save)
        self.auto_save_timer.start()
        
    def _setup_toolbar(self):
        """设置Markdown工具栏"""
        # 文件操作按钮
        self.new_action = QAction(self)
        self.new_action.setToolTip("新建Markdown文档")
        self.new_action.triggered.connect(self.new_file)
        self.toolbar.addAction(self.new_action)
        
        self.open_action = QAction(self)
        self.open_action.setToolTip("打开Markdown文档")
        self.open_action.triggered.connect(self.open_file)
        self.toolbar.addAction(self.open_action)
        
        self.save_action = QAction(self)
        self.save_action.setToolTip("保存Markdown文档")
        self.save_action.triggered.connect(self.save_file)
        self.toolbar.addAction(self.save_action)
        
        # 添加分隔符
        self.toolbar.addSeparator()
        
        # 标题格式
        self.heading_combo = QComboBox()
        self.heading_combo.addItems(["普通文本", "# 一级标题", "## 二级标题", "### 三级标题", "#### 四级标题", "##### 五级标题", "###### 六级标题"])
        self.heading_combo.setToolTip("设置标题级别")
        self.heading_combo.currentIndexChanged.connect(self._apply_heading)
        self.toolbar.addWidget(self.heading_combo)
        
        self.toolbar.addSeparator()
        
        # 字体相关
        # 粗体
        self.bold_action = QAction(self)
        self.bold_action.setToolTip("粗体 (Ctrl+B)")
        self.bold_action.triggered.connect(lambda: self._format_text('**', '**'))
        self.toolbar.addAction(self.bold_action)
        
        # 斜体
        self.italic_action = QAction(self)
        self.italic_action.setToolTip("斜体 (Ctrl+I)")
        self.italic_action.triggered.connect(lambda: self._format_text('*', '*'))
        self.toolbar.addAction(self.italic_action)
        
        # 下划线
        self.underline_action = QAction(self)
        self.underline_action.setToolTip("下划线")
        self.underline_action.triggered.connect(lambda: self._format_text('<u>', '</u>'))
        self.toolbar.addAction(self.underline_action)
        
        # 删除线
        self.strikethrough_action = QAction(self)
        self.strikethrough_action.setToolTip("删除线")
        self.strikethrough_action.triggered.connect(lambda: self._format_text('~~', '~~'))
        self.toolbar.addAction(self.strikethrough_action)
        
        # 高亮
        self.highlight_action = QAction(self)
        self.highlight_action.setToolTip("高亮")
        self.highlight_action.triggered.connect(lambda: self._format_text('==', '=='))
        self.toolbar.addAction(self.highlight_action)
        
        self.toolbar.addSeparator()
        
        # 列表
        # 无序列表
        self.bullet_list_action = QAction(self)
        self.bullet_list_action.setToolTip("无序列表")
        self.bullet_list_action.triggered.connect(self._insert_bullet_list)
        self.toolbar.addAction(self.bullet_list_action)
        
        # 有序列表
        self.ordered_list_action = QAction(self)
        self.ordered_list_action.setToolTip("有序列表")
        self.ordered_list_action.triggered.connect(self._insert_ordered_list)
        self.toolbar.addAction(self.ordered_list_action)
        
        # 任务列表
        self.task_list_action = QAction(self)
        self.task_list_action.setToolTip("任务列表")
        self.task_list_action.triggered.connect(self._insert_task_list)
        self.toolbar.addAction(self.task_list_action)
        
        self.toolbar.addSeparator()
        
        # 链接
        self.link_action = QAction(self)
        self.link_action.setToolTip("插入链接")
        self.link_action.triggered.connect(lambda: self._format_text('[', '](http://example.com)'))
        self.toolbar.addAction(self.link_action)
        
        # 图片
        self.image_action = QAction(self)
        self.image_action.setToolTip("插入图片")
        self.image_action.triggered.connect(lambda: self._format_text('![图片描述](', ')'))
        self.toolbar.addAction(self.image_action)
        
        # 代码
        self.code_action = QAction(self)
        self.code_action.setToolTip("行内代码")
        self.code_action.triggered.connect(lambda: self._format_text('`', '`'))
        self.toolbar.addAction(self.code_action)
        
        # 代码块
        self.code_block_action = QAction(self)
        self.code_block_action.setToolTip("代码块")
        self.code_block_action.triggered.connect(self._insert_code_block)
        self.toolbar.addAction(self.code_block_action)
        
        self.toolbar.addSeparator()
        
        # 引用
        self.quote_action = QAction(self)
        self.quote_action.setToolTip("引用")
        self.quote_action.triggered.connect(self._insert_quote)
        self.toolbar.addAction(self.quote_action)
        
        # 水平线
        self.horizontal_rule_action = QAction(self)
        self.horizontal_rule_action.setToolTip("水平线")
        self.horizontal_rule_action.triggered.connect(self._insert_horizontal_rule)
        self.toolbar.addAction(self.horizontal_rule_action)
        
        # 表格
        self.table_action = QAction(self)
        self.table_action.setToolTip("插入表格")
        self.table_action.triggered.connect(self._insert_table)
        self.toolbar.addAction(self.table_action)
        
        # 添加一个分隔符
        self.toolbar.addSeparator()
        
        # 添加预览/编辑切换按钮
        self.preview_toggle_action = QAction(self)
        self.preview_toggle_action.setToolTip("切换预览/编辑模式")
        self.preview_toggle_action.triggered.connect(self._toggle_preview_mode)
        self.toolbar.addAction(self.preview_toggle_action)
    
    def _update_icons(self):
        """更新图标颜色"""
        # 获取当前主题颜色
        icon_color = '#88C0D0'  # 默认强调色
        button_bg = '#2E3440'   # 默认按钮背景色
        
        if self.theme_manager:
            theme_colors = self.theme_manager.get_current_theme_colors()
            icon_color = theme_colors.get('accent', icon_color)
            button_bg = theme_colors.get('secondary_bg', button_bg)
        
        # 文件操作图标
        self.new_action.setIcon(qta.icon("fa5s.file", color=icon_color))
        self.open_action.setIcon(qta.icon("fa5s.folder-open", color=icon_color))
        self.save_action.setIcon(qta.icon("fa5s.save", color=icon_color))
        
        # 工具栏图标
        self.bold_action.setIcon(qta.icon("fa5s.bold", color=icon_color))
        self.italic_action.setIcon(qta.icon("fa5s.italic", color=icon_color))
        self.underline_action.setIcon(qta.icon("fa5s.underline", color=icon_color))
        self.strikethrough_action.setIcon(qta.icon("fa5s.strikethrough", color=icon_color))
        self.highlight_action.setIcon(qta.icon("fa5s.highlighter", color=icon_color))
        
        self.bullet_list_action.setIcon(qta.icon("fa5s.list-ul", color=icon_color))
        self.ordered_list_action.setIcon(qta.icon("fa5s.list-ol", color=icon_color))
        self.task_list_action.setIcon(qta.icon("fa5s.tasks", color=icon_color))
        
        self.link_action.setIcon(qta.icon("fa5s.link", color=icon_color))
        self.image_action.setIcon(qta.icon("fa5s.image", color=icon_color))
        self.code_action.setIcon(qta.icon("fa5s.code", color=icon_color))
        self.code_block_action.setIcon(qta.icon("fa5s.file-code", color=icon_color))
        
        self.quote_action.setIcon(qta.icon("fa5s.quote-right", color=icon_color))
        self.horizontal_rule_action.setIcon(qta.icon("fa5s.minus", color=icon_color))
        self.table_action.setIcon(qta.icon("fa5s.table", color=icon_color))
        
        # 预览/编辑切换按钮图标
        if self.is_preview_mode:
            self.preview_toggle_action.setIcon(qta.icon("fa5s.edit", color=icon_color))
            self.preview_toggle_action.setToolTip("切换到编辑模式")
        else:
            self.preview_toggle_action.setIcon(qta.icon("fa5s.eye", color=icon_color))
            self.preview_toggle_action.setToolTip("切换到预览模式")
    
    def _on_text_changed(self):
        """文本内容变更处理"""
        self.is_modified = True
        self.text_changed.emit()
        
        # 如果在预览模式，更新预览内容
        if self.is_preview_mode:
            self._update_preview()
    
    def _apply_heading(self, index):
        """应用标题格式"""
        cursor = self.text_edit.textCursor()
        
        # 获取当前行文本
        cursor.select(QTextCursor.SelectionType.LineUnderCursor)
        line_text = cursor.selectedText()
        
        # 移除已有的标题符号
        clean_text = re.sub(r'^#+ ', '', line_text)
        
        # 添加新的标题符号(如果不是普通文本)
        if index > 0:
            prefix = "#" * index + " "
            new_text = prefix + clean_text
        else:
            new_text = clean_text
            
        # 替换当前行
        cursor.removeSelectedText()
        cursor.insertText(new_text)
        
        # 恢复标题下拉框为默认(普通文本)
        self.heading_combo.setCurrentIndex(0)
    
    def _format_text(self, prefix, suffix):
        """格式化选中的文本"""
        cursor = self.text_edit.textCursor()
        
        if cursor.hasSelection():
            start = cursor.selectionStart()
            end = cursor.selectionEnd()
            selected_text = cursor.selectedText()
            
            # 应用格式
            formatted_text = prefix + selected_text + suffix
            
            # 替换选中的文本
            cursor.removeSelectedText()
            cursor.insertText(formatted_text)
            
            # 重新选中格式化后的文本(包括标记)
            cursor.setPosition(start)
            cursor.setPosition(start + len(formatted_text), QTextCursor.MoveMode.KeepAnchor)
            self.text_edit.setTextCursor(cursor)
        else:
            # 如果没有选择文本，只插入标记，并将光标定位在中间
            cursor.insertText(prefix + suffix)
            
            # 将光标移到标记中间
            new_position = cursor.position() - len(suffix)
            cursor.setPosition(new_position)
            self.text_edit.setTextCursor(cursor)
    
    def _insert_bullet_list(self):
        """插入无序列表"""
        cursor = self.text_edit.textCursor()
        if cursor.hasSelection():
            # 将选择的多行文本转换为无序列表
            selected_text = cursor.selectedText()
            lines = selected_text.split('\u2029')  # Qt使用\u2029作为行分隔符
            
            formatted_lines = []
            for line in lines:
                # 移除已有的列表标记
                clean_line = re.sub(r'^[\*\-\+]\s+', '', line)
                clean_line = re.sub(r'^\d+\.\s+', '', clean_line)
                clean_line = re.sub(r'^- \[ \] ', '', clean_line)
                clean_line = re.sub(r'^- \[x\] ', '', clean_line)
                
                formatted_lines.append("- " + clean_line)
            
            formatted_text = "\n".join(formatted_lines)
            cursor.removeSelectedText()
            cursor.insertText(formatted_text)
        else:
            # 在当前行插入无序列表标记
            cursor.insertText("- ")
    
    def _insert_ordered_list(self):
        """插入有序列表"""
        cursor = self.text_edit.textCursor()
        if cursor.hasSelection():
            # 将选择的多行文本转换为有序列表
            selected_text = cursor.selectedText()
            lines = selected_text.split('\u2029')  # Qt使用\u2029作为行分隔符
            
            formatted_lines = []
            for i, line in enumerate(lines, 1):
                # 移除已有的列表标记
                clean_line = re.sub(r'^[\*\-\+]\s+', '', line)
                clean_line = re.sub(r'^\d+\.\s+', '', clean_line)
                clean_line = re.sub(r'^- \[ \] ', '', clean_line)
                clean_line = re.sub(r'^- \[x\] ', '', clean_line)
                
                formatted_lines.append(f"{i}. {clean_line}")
            
            formatted_text = "\n".join(formatted_lines)
            cursor.removeSelectedText()
            cursor.insertText(formatted_text)
        else:
            # 在当前行插入有序列表标记
            cursor.insertText("1. ")
    
    def _insert_task_list(self):
        """插入任务列表"""
        cursor = self.text_edit.textCursor()
        if cursor.hasSelection():
            # 将选择的多行文本转换为任务列表
            selected_text = cursor.selectedText()
            lines = selected_text.split('\u2029')  # Qt使用\u2029作为行分隔符
            
            formatted_lines = []
            for line in lines:
                # 移除已有的列表标记
                clean_line = re.sub(r'^[\*\-\+]\s+', '', line)
                clean_line = re.sub(r'^\d+\.\s+', '', clean_line)
                clean_line = re.sub(r'^- \[ \] ', '', clean_line)
                clean_line = re.sub(r'^- \[x\] ', '', clean_line)
                
                formatted_lines.append(f"- [ ] {clean_line}")
            
            formatted_text = "\n".join(formatted_lines)
            cursor.removeSelectedText()
            cursor.insertText(formatted_text)
        else:
            # 在当前行插入任务列表标记
            cursor.insertText("- [ ] ")
    
    def _insert_code_block(self):
        """插入代码块"""
        self.text_edit.insertPlainText("```\n\n```")
        
        # 将光标移动到代码块中间
        cursor = self.text_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.MoveAnchor, 4)
        self.text_edit.setTextCursor(cursor)
    
    def _insert_quote(self):
        """插入引用"""
        cursor = self.text_edit.textCursor()
        if cursor.hasSelection():
            # 将选择的多行文本转换为引用
            selected_text = cursor.selectedText()
            lines = selected_text.split('\u2029')  # Qt使用\u2029作为行分隔符
            
            formatted_lines = []
            for line in lines:
                # 移除已有的引用标记
                clean_line = re.sub(r'^>\s+', '', line)
                formatted_lines.append(f"> {clean_line}")
            
            formatted_text = "\n".join(formatted_lines)
            cursor.removeSelectedText()
            cursor.insertText(formatted_text)
        else:
            # 在当前行插入引用标记
            cursor.insertText("> ")
    
    def _insert_horizontal_rule(self):
        """插入水平线"""
        # 先插入一个换行(如果当前行不是空行)
        cursor = self.text_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
        cursor.movePosition(QTextCursor.MoveOperation.EndOfLine, QTextCursor.MoveMode.KeepAnchor)
        line_text = cursor.selectedText()
        
        if line_text.strip():
            self.text_edit.insertPlainText("\n\n---\n")
        else:
            self.text_edit.insertPlainText("\n---\n")
    
    def _insert_table(self):
        """插入表格"""
        table_template = """
| 列1 | 列2 | 列3 |
| --- | --- | --- |
| 内容1 | 内容2 | 内容3 |
| 内容4 | 内容5 | 内容6 |
"""
        self.text_edit.insertPlainText(table_template)
    
    def _auto_save(self):
        """自动保存功能"""
        if self.is_modified and self.current_file_path:
            self.save_file(self.current_file_path)
    
    def new_file(self):
        """新建文件"""
        if self.is_modified:
            reply = QMessageBox.question(self, '保存变更', 
                                        '当前文档有未保存的变更，是否保存？',
                                        QMessageBox.StandardButton.Save | 
                                        QMessageBox.StandardButton.Discard | 
                                        QMessageBox.StandardButton.Cancel)
            
            if reply == QMessageBox.StandardButton.Save:
                if not self.save_file():
                    # 如果保存取消，则中止新建
                    return
            elif reply == QMessageBox.StandardButton.Cancel:
                # 取消新建
                return
        
        # 清空编辑器
        self.text_edit.clear()
        self.current_file_path = None
        self.is_modified = False
    
    def open_file(self):
        """打开文件"""
        if self.is_modified:
            reply = QMessageBox.question(self, '保存变更', 
                                        '当前文档有未保存的变更，是否保存？',
                                        QMessageBox.StandardButton.Save | 
                                        QMessageBox.StandardButton.Discard | 
                                        QMessageBox.StandardButton.Cancel)
            
            if reply == QMessageBox.StandardButton.Save:
                if not self.save_file():
                    # 如果保存取消，则中止打开
                    return
            elif reply == QMessageBox.StandardButton.Cancel:
                # 取消打开
                return
        
        # 弹出文件选择对话框
        options = QFileDialog.Option.ReadOnly
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开Markdown文件", "", 
            "Markdown Files (*.md *.markdown);;All Files (*)", 
            options=options
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                self.text_edit.setPlainText(content)
                self.current_file_path = file_path
                self.is_modified = False
            except Exception as e:
                QMessageBox.critical(self, "打开文件错误", f"无法打开文件: {str(e)}")
    
    def save_file(self, file_path=None):
        """保存文件"""
        # 如果没有提供文件路径且没有当前文件路径，则弹出保存对话框
        if not file_path and not self.current_file_path:
            options = QFileDialog.Option.ReadOnly
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存Markdown文件", "", 
                "Markdown Files (*.md);;All Files (*)", 
                options=options
            )
            
            if not file_path:
                return False  # 用户取消了保存
            
            # 确保文件有.md扩展名
            if not file_path.lower().endswith(('.md', '.markdown')):
                file_path += '.md'
        
        # 使用提供的路径或当前路径
        save_path = file_path or self.current_file_path
        
        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(self.text_edit.toPlainText())
            
            self.current_file_path = save_path
            self.is_modified = False
            return True
        except Exception as e:
            QMessageBox.critical(self, "保存文件错误", f"无法保存文件: {str(e)}")
            return False
    
    def set_text(self, text):
        """设置编辑器文本"""
        self.text_edit.setPlainText(text)
        self.is_modified = False  # 重置修改状态
    
    def get_text(self):
        """获取编辑器文本"""
        return self.text_edit.toPlainText()
    
    def clear(self):
        """清空编辑器"""
        self.text_edit.clear()
        self.is_modified = False
    
    def submit_prompt(self):
        """提交提示词"""
        text = self.text_edit.toPlainText().strip()
        
        if not text:
            # 提示词为空不发送
            return
        
        # 发送提示词信号
        self.prompt_submitted.emit(text)
        # 不再清空输入框
    
    def submit_current_paragraph(self):
        """提交当前段落的提示词"""
        cursor = self.text_edit.textCursor()
        
        # 获取当前位置
        current_position = cursor.position()
        text = self.text_edit.toPlainText()
        
        if not text:
            return
            
        # 找到当前段落的开始和结束
        # 向前查找段落开始（上一个换行符之后）
        start = current_position
        while start > 0 and text[start-1] != '\n':
            start -= 1
            
        # 向后查找段落结束（下一个换行符之前）
        end = current_position
        while end < len(text) and text[end] != '\n':
            end += 1
            
        # 提取当前段落文本
        paragraph_text = text[start:end].strip()
        
        if not paragraph_text:
            return
            
        # 发送当前段落文本
        self.prompt_submitted.emit(paragraph_text)
    
    def eventFilter(self, obj, event):
        """事件过滤器，处理快捷键"""
        if obj == self.text_edit and event.type() == event.Type.KeyPress:
            # Ctrl+Enter 发送当前段落提示词
            if event.key() == Qt.Key.Key_Return and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                self.submit_current_paragraph()
                return True
                
            # Ctrl+B 粗体
            elif event.key() == Qt.Key.Key_B and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                self._format_text('**', '**')
                return True
                
            # Ctrl+I 斜体
            elif event.key() == Qt.Key.Key_I and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                self._format_text('*', '*')
                return True
                
            # Ctrl+S 保存
            elif event.key() == Qt.Key.Key_S and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                self.save_file()
                return True
                
            # Ctrl+O 打开
            elif event.key() == Qt.Key.Key_O and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                self.open_file()
                return True
                
            # Ctrl+N 新建
            elif event.key() == Qt.Key.Key_N and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                self.new_file()
                return True
        
        return super().eventFilter(obj, event)
    
    def _toggle_preview_mode(self):
        """切换预览模式和编辑模式"""
        self.is_preview_mode = not self.is_preview_mode
        
        if self.is_preview_mode:
            # 切换到预览模式
            self._update_preview()
            self.stacked_widget.setCurrentIndex(1)  # 显示预览视图
        else:
            # 切换到编辑模式
            self.stacked_widget.setCurrentIndex(0)  # 显示编辑器
        
        # 更新按钮图标
        self._update_icons()
    
    def _update_preview(self):
        """更新预览内容"""
        md_text = self.text_edit.toPlainText()
        html_content = self._markdown_to_html(md_text)
        self.preview_view.setHtml(html_content)
    
    def _markdown_to_html(self, md_text):
        """将Markdown文本转换为HTML"""
        try:
            # 使用Python-Markdown库将Markdown转换为HTML
            extensions = [
                'tables',               # 启用表格支持
                'fenced_code',          # 启用围栏代码块
            ]
            
            # 转换Markdown为HTML
            html_body = markdown.markdown(md_text, extensions=extensions)
            
            # 包装在完整的HTML文档中
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
                        line-height: 1.6;
                        padding: 20px;
                        max-width: 900px;
                        margin: 0 auto;
                        color: #2E3440;
                        background-color: #ECEFF4;
                    }}
                    
                    h1, h2, h3, h4, h5, h6 {{
                        margin-top: 24px;
                        margin-bottom: 16px;
                        font-weight: 600;
                        color: #2E3440;
                    }}
                    
                    h1 {{ font-size: 2em; border-bottom: 1px solid #D8DEE9; padding-bottom: 0.3em; }}
                    h2 {{ font-size: 1.5em; border-bottom: 1px solid #D8DEE9; padding-bottom: 0.3em; }}
                    h3 {{ font-size: 1.25em; }}
                    h4 {{ font-size: 1em; }}
                    
                    a {{ color: #5E81AC; text-decoration: none; }}
                    a:hover {{ text-decoration: underline; }}
                    
                    code {{
                        font-family: SFMono-Regular, Consolas, 'Liberation Mono', Menlo, monospace;
                        background-color: #E5E9F0;
                        padding: 0.2em 0.4em;
                        border-radius: 3px;
                        font-size: 85%;
                    }}
                    
                    pre {{
                        background-color: #E5E9F0;
                        border-radius: 3px;
                        padding: 16px;
                        overflow: auto;
                        font-size: 85%;
                    }}
                    
                    pre code {{
                        background-color: transparent;
                        padding: 0;
                    }}
                    
                    blockquote {{
                        padding: 0 1em;
                        color: #4C566A;
                        border-left: 0.25em solid #D8DEE9;
                        margin: 0 0 16px 0;
                    }}
                    
                    table {{
                        border-collapse: collapse;
                        border-spacing: 0;
                        width: 100%;
                        overflow: auto;
                        margin-bottom: 16px;
                    }}
                    
                    table th, table td {{
                        padding: 6px 13px;
                        border: 1px solid #D8DEE9;
                    }}
                    
                    table tr {{
                        background-color: #ECEFF4;
                        border-top: 1px solid #D8DEE9;
                    }}
                    
                    table tr:nth-child(2n) {{
                        background-color: #E5E9F0;
                    }}
                    
                    img {{
                        max-width: 100%;
                        height: auto;
                    }}
                    
                    hr {{
                        height: 1px;
                        padding: 0;
                        margin: 24px 0;
                        background-color: #D8DEE9;
                        border: 0;
                    }}
                    
                    ul, ol {{
                        padding-left: 2em;
                    }}
                    
                    li {{
                        margin-bottom: 0.25em;
                    }}
                    
                    /* 暗模式支持 (可以通过JS动态切换) */
                    @media (prefers-color-scheme: dark) {{
                        body {{
                            color: #ECEFF4;
                            background-color: #2E3440;
                        }}
                        
                        h1, h2, h3, h4, h5, h6 {{
                            color: #ECEFF4;
                        }}
                        
                        h1, h2 {{
                            border-bottom: 1px solid #4C566A;
                        }}
                        
                        a {{
                            color: #88C0D0;
                        }}
                        
                        code {{
                            background-color: #3B4252;
                        }}
                        
                        pre {{
                            background-color: #3B4252;
                        }}
                        
                        blockquote {{
                            color: #D8DEE9;
                            border-left: 0.25em solid #4C566A;
                        }}
                        
                        table th, table td {{
                            border: 1px solid #4C566A;
                        }}
                        
                        table tr {{
                            background-color: #2E3440;
                            border-top: 1px solid #4C566A;
                        }}
                        
                        table tr:nth-child(2n) {{
                            background-color: #3B4252;
                        }}
                        
                        hr {{
                            background-color: #4C566A;
                        }}
                    }}
                </style>
            </head>
            <body>
                {html_body}
            </body>
            </html>
            """
            
            return html
        except Exception as e:
            # 显示错误信息
            error_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: sans-serif; padding: 20px; color: #721c24; background-color: #f8d7da; }}
                    .error {{ padding: 15px; border: 1px solid #f5c6cb; border-radius: 4px; }}
                </style>
            </head>
            <body>
                <div class="error">
                    <h3>Markdown 渲染错误</h3>
                    <p>{str(e)}</p>
                </div>
            </body>
            </html>
            """
            return error_html 