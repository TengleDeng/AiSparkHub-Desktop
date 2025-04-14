#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTextEdit, QPushButton, 
                           QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem, 
                           QLabel, QFrame, QComboBox)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QColor
import qtawesome as qta
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from app.controllers.theme_manager import ThemeManager
import os

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
        
        # 添加搜索范围选择下拉框
        self.search_scope_combo = QComboBox()
        self.search_scope_combo.addItems(["搜索: 全部", "搜索: 提示词", "搜索: PKM"])
        self.search_scope_combo.setToolTip("选择搜索范围")
        search_layout.addWidget(self.search_scope_combo)
        
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
        search_query = self.search_input.text().strip()
        
        if not text:
            # 提示词为空不发送
            return
        
        if search_query:
            # 搜索框有内容，整合搜索结果与提示词
            try:
                # 获取选择的搜索范围
                scope_text = self.search_scope_combo.currentText()
                if scope_text == "搜索: 提示词":
                    scope = 'prompts'
                elif scope_text == "搜索: PKM":
                    scope = 'pkm'
                else:  # 默认为全部
                    scope = 'all'
                
                # 获取搜索结果(10条)
                search_results = self.db_manager.search_combined(search_query, scope=scope, limit=10)
                
                # 首先构建问题部分
                final_prompt = f"{text}\n\n"
                final_prompt += f"以下是与问题相关的本地知识库资料(关键词:{search_query})，请参考这些资料回答上述问题。如果资料与问题无关，请使用你自己的知识回答。\n\n"
                
                # 构建搜索结果部分(不限单个文档长度，但总长度限制)
                search_content = ""
                for i, result in enumerate(search_results, 1):
                    result_type = result.get('type', 'unknown')
                    
                    if result_type == 'pkm':
                        # 获取PKM文件内容
                        file_id = result.get('id')
                        if file_id:
                            pkm_data = self.db_manager.get_pkm_file_content(file_id)
                            if pkm_data and 'content' in pkm_data:
                                title = pkm_data.get('title', pkm_data.get('file_name', '未命名文档'))
                                content = pkm_data.get('content', '')
                                # 移除多余空行
                                content = "\n".join([line for line in content.split("\n") if line.strip()])
                                search_content += f"【参考资料{i}】{title}\n{content}\n\n"
                    
                    elif result_type == 'prompt':
                        # 添加提示词和AI回复
                        prompt = result.get('prompt', '')
                        # 移除多余空行
                        prompt = "\n".join([line for line in prompt.split("\n") if line.strip()])
                        search_content += f"【历史问题{i}】{prompt}\n"
                        
                        # 添加AI回复
                        replies = []
                        for webview in result.get('webviews', []):
                            reply = webview.get('reply', '')
                            if reply:
                                # 移除多余空行
                                reply = "\n".join([line for line in reply.split("\n") if line.strip()])
                                replies.append(reply)
                        
                        if replies:
                            search_content += f"【历史回答】{''.join(replies)}\n\n"
                
                # 计算总长度并限制在18000字符以内
                max_chars = 18000
                current_length = len(final_prompt)
                remaining_chars = max_chars - current_length
                
                if len(search_content) > remaining_chars:
                    # 如果搜索内容超过剩余字符数，则截断
                    search_content = search_content[:remaining_chars-100] + "\n\n...(由于内容过长，部分资料已省略)"
                
                # 合并最终提示词
                final_prompt += search_content
                
                # 发送整合后的提示词
                self.prompt_submitted.emit(final_prompt)
                
            except Exception as e:
                print(f"整合搜索结果时出错: {e}")
                # 如果出错，仍然发送原始提示词
                self.prompt_submitted.emit(text)
        else:
            # 搜索框为空，直接发送提示词
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
            
        # 获取选择的搜索范围
        scope_text = self.search_scope_combo.currentText()
        if scope_text == "搜索: 提示词":
            scope = 'prompts'
        elif scope_text == "搜索: PKM":
            scope = 'pkm'
        else: # 默认为全部
            scope = 'all'
            
        # 执行组合搜索
        try:
            results = self.db_manager.search_combined(search_text, scope=scope)
            
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
            count_item = QListWidgetItem(f"在 [{scope_text.replace('搜索: ', '')}] 中找到 {result_count} 条匹配结果")
            count_item.setFlags(Qt.ItemFlag.NoItemFlags)  # 设置为不可选
            count_item.setBackground(QColor(header_bg))
            count_item.setForeground(QColor(text_color))
            # 使标题文本居中
            count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.search_results.addItem(count_item)
            
            if results:
                for i, result in enumerate(results):
                    item = QListWidgetItem()
                    
                    # 设置项目样式 - 根据主题设置交替背景色
                    if i % 2 == 0:
                        item.setBackground(QColor(item_bg_1))
                    else:
                        item.setBackground(QColor(item_bg_2))
                    
                    # 根据结果类型显示不同内容
                    result_type = result.get('type', 'unknown')
                    display_text = f"{i+1}. "
                    
                    if result_type == 'prompt':
                        prompt = result.get('prompt', '')
                        if len(prompt) > 60:
                            display_text += "[提示] " + prompt[:60] + "..."
                        else:
                            display_text += "[提示] " + prompt
                        
                        # 查找匹配的回复片段 (保持不变)
                        match_reply = ""
                        for webview in result.get('webviews', []):
                            reply = webview.get('reply', '')
                            if reply and search_text.lower() in reply.lower():
                                idx = reply.lower().find(search_text.lower())
                                start = max(0, idx - 20)
                                end = min(len(reply), idx + len(search_text) + 20)
                                match_reply = "..." + reply[start:end] + "..."
                                break
                        if match_reply:
                            display_text += f"\n匹配回复: {match_reply}"
                            
                    elif result_type == 'pkm':
                        title = result.get('title', result.get('file_name', '未知标题'))
                        if len(title) > 60:
                            display_text += "[PKM] " + title[:60] + "..."
                        else:
                            display_text += "[PKM] " + title
                        
                        # 显示文件路径
                        file_path = result.get('file_path', '')
                        if file_path:
                            display_text += f"\n路径: ...{os.path.basename(os.path.dirname(file_path))}{os.sep}{os.path.basename(file_path)}" # 简化路径显示
                            
                    else: # 未知类型
                        display_text += f"[未知类型] {str(result)[:60]}..."
                    
                    item.setText(display_text)
                    item.setData(Qt.ItemDataRole.UserRole, result) # 存储完整数据，包含type
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
        if data:
            result_type = data.get('type')
            if result_type == 'prompt':
                self.text_edit.setText(data.get('prompt', ''))
            elif result_type == 'pkm':
                # 对于PKM结果，获取文件内容并填入输入框
                file_id = data.get('id')
                if file_id and self.db_manager:
                    try:
                        pkm_data = self.db_manager.get_pkm_file_content(file_id)
                        if pkm_data and 'content' in pkm_data:
                            self.text_edit.setText(pkm_data['content'])
                        else:
                            self.text_edit.setText(f"错误：无法获取PKM文件内容 (ID: {file_id})")
                            print(f"无法获取PKM文件内容 (ID: {file_id})")
                    except Exception as e:
                        self.text_edit.setText(f"错误：获取PKM内容时出错: {str(e)}")
                        print(f"获取PKM内容时出错: {e}")
                else:
                    self.text_edit.setText("错误：无法识别PKM文件ID或缺少数据库管理器")
                    print("无法识别PKM文件ID或缺少数据库管理器")
            else:
                 self.text_edit.setText(f"未知类型结果: {str(data)}")
            
            # 隐藏搜索结果，清空搜索框等 (保持不变)
            self.search_results.setVisible(False)
            self.search_input.clear()
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