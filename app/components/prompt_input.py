#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTextEdit, QPushButton, 
                           QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem, 
                           QLabel, QFrame, QComboBox, QStackedWidget)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QColor, QTextCharFormat, QFont
import qtawesome as qta
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from app.controllers.theme_manager import ThemeManager
import os
import re
from app.components.markdown_editor import MarkdownEditor
# 导入新创建的模板模块
from app.components.prompt_template import PromptTemplate

class PromptInput(MarkdownEditor):
    """提示词输入组件，带Markdown编辑功能和搜索能力"""
    
    # 定义信号
    prompt_submitted = pyqtSignal(str)  # 提示词提交信号
    
    def __init__(self, parent=None, db_manager=None):
        super().__init__(parent, db_manager)
        
        # 确保使用Fusion样式，便于自定义按钮样式
        app = QApplication.instance()
        if app:
            app.setStyle("Fusion")
        
        # 删除固定最小高度设置
        self.setMinimumHeight(0)
        
        # 创建模式切换容器（堆叠窗口）
        self.input_stack = QStackedWidget()
        
        # 创建模板组件
        self.template_component = PromptTemplate()
        self.template_component.template_content_updated.connect(self.on_template_content_updated)
        
        # 重要修改: 不再直接操作text_edit和stacked_widget
        # 而是创建一个新容器承载MarkdownEditor的功能
        self.markdown_container = QWidget()
        markdown_layout = QVBoxLayout(self.markdown_container)
        markdown_layout.setContentsMargins(0, 0, 0, 0)
        markdown_layout.setSpacing(0)
        
        # 将原始stacked_widget添加到新容器
        markdown_layout.addWidget(self.stacked_widget)
        
        # 将markdown容器和模板组件添加到input_stack
        self.input_stack.addWidget(self.markdown_container)
        self.input_stack.addWidget(self.template_component)
        
        # 重新组织布局
        # 找到原始布局中stacked_widget的位置
        stacked_index = self.layout.indexOf(self.stacked_widget)
        if stacked_index >= 0:
            # 从原始布局中移除stacked_widget
            self.layout.removeWidget(self.stacked_widget)
            # 在同样的位置加入input_stack
            self.layout.insertWidget(stacked_index, self.input_stack, 3)
        else:
            # 如果未找到，直接添加
            self.layout.addWidget(self.input_stack, 3)
        
        # 设置UI
        self.setup_tools_toolbar()  # 添加工具栏
        self.setup_search_ui()      # 添加搜索UI
        
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
            
        # 确保默认显示文本编辑器并设置焦点
        self.input_stack.setCurrentIndex(0)
        # 使用延迟设置焦点，确保在UI完全初始化后执行
        QTimer.singleShot(100, self.text_edit.setFocus)
        
    def on_template_content_updated(self, content):
        """处理模板内容更新"""
        if not content:  # 如果是空内容，表示选择了"直接输入"
            # 切换到直接输入模式
            self.input_stack.setCurrentIndex(0)  # 显示Markdown编辑器容器
            
            # 确保模板相关组件都隐藏
            self.template_component.variables_container.setVisible(False)
            self.template_component.preview_container.setVisible(False)
            
            # 如果之前在预览模式，现在也应保持预览模式
            # stacked_widget的控制不变，让预览/编辑切换按钮功能正常
            
            # 延迟设置焦点到文本编辑器(仅在编辑模式下)
            if not self.is_preview_mode:
                QTimer.singleShot(100, self.text_edit.setFocus)
        else:
            # 设置文本编辑器内容(这样在切回直接输入模式时能看到内容)
            self.text_edit.setPlainText(content)
            
            # 切换到模板视图
            self.input_stack.setCurrentIndex(1)  # 显示模板视图
            
            # 确保模板相关组件可见
            self.template_component.variables_container.setVisible(True)
            self.template_component.preview_container.setVisible(True)
            
            # 更新变量UI
            QTimer.singleShot(100, self.template_component.update_variables_ui)
    
    def get_text(self):
        """获取当前文本内容，重写以支持模板模式"""
        # 从当前活动的输入源获取文本
        current_index = self.input_stack.currentIndex()
        if current_index == 0:
            # 使用父类方法获取文本编辑器内容
            return super().get_text()
        else:
            # 从模板组件获取处理后的内容
            return self.template_component.get_processed_template()
    
    def set_text(self, text):
        """设置文本内容，重写以支持模板模式"""
        # 切换到直接输入模式，并设置文本
        self.input_stack.setCurrentIndex(0)  # 显示文本编辑器
        self.template_component.template_combo.setCurrentIndex(0)  # 选择"直接输入"选项
        super().set_text(text)
    
    def setup_search_ui(self):
        """设置搜索UI界面"""
        # 创建搜索框区域
        search_layout = QHBoxLayout()
        search_layout.setContentsMargins(0, 5, 0, 5)
        search_layout.setSpacing(8)
        
        # 添加搜索范围选择下拉框
        self.search_scope_combo = QComboBox()
        self.search_scope_combo.addItems(["搜索: 全部", "搜索: 提示词", "搜索: PKM"])
        self.search_scope_combo.setToolTip("选择搜索范围")
        search_layout.addWidget(self.search_scope_combo)
        
        # 添加搜索模式选择
        self.search_mode_combo = QComboBox()
        self.search_mode_combo.addItems(["匹配方式: 全部包含(AND)", "匹配方式: 任一包含(OR)", "匹配方式: 精确匹配"])
        self.search_mode_combo.setToolTip("选择搜索词处理方式")
        search_layout.addWidget(self.search_mode_combo)
        
        # 添加搜索框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索提示词和AI回复... (支持引号精确匹配\"精确词\"和排除词-排除)")
        self.search_input.returnPressed.connect(self.search_prompts)
        search_layout.addWidget(self.search_input, 1)  # 1表示拉伸因子
        
        # 添加搜索按钮
        self.search_button = QPushButton()
        self.search_button.setToolTip("搜索提示词和AI回复")
        self.search_button.clicked.connect(self.search_prompts)
        search_layout.addWidget(self.search_button)
        
        # 添加发送按钮到搜索布局中
        self.send_button = QPushButton("发送")
        self.send_button.setToolTip("发送提示词")
        self.send_button.clicked.connect(self.submit_prompt)
        search_layout.addWidget(self.send_button)
        
        # 创建搜索结果列表
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
        
        # 创建一个垂直布局用于组织底部元素
        bottom_container = QVBoxLayout()
        bottom_container.setContentsMargins(0, 0, 0, 0)
        bottom_container.setSpacing(5)
        
        # 添加搜索框布局到底部容器
        bottom_container.addLayout(search_layout)
        
        # 添加搜索结果到底部容器
        bottom_container.addWidget(self.search_results)
        
        # 将底部容器添加到主布局的底部
        self.layout.addLayout(bottom_container)
        
        # 更新图标
        self._update_icons()
    
    def setup_tools_toolbar(self):
        """设置工具工具栏，添加特殊功能按钮和模板选择"""
        # 创建工具栏容器
        tools_layout = QHBoxLayout()
        tools_layout.setContentsMargins(0, 5, 0, 5)
        tools_layout.setSpacing(8)
        
        # 添加模板选择下拉框
        template_label = QLabel("选择模板:")
        tools_layout.addWidget(template_label)
        
        # 使用模板组件的下拉框
        tools_layout.addWidget(self.template_component.template_combo)
        
        # 添加模板目录和刷新按钮
        tools_layout.addWidget(self.template_component.template_dir_button)
        tools_layout.addWidget(self.template_component.refresh_button)
        
        # 添加"每日内参"按钮
        self.daily_briefing_button = QPushButton("今日内参")
        self.daily_briefing_button.setToolTip("生成当天更新文章的内参日报")
        self.daily_briefing_button.clicked.connect(lambda: self.generate_briefing(0))  # 0表示当天
        tools_layout.addWidget(self.daily_briefing_button)
        
        # 添加"昨日内参"按钮
        self.yesterday_briefing_button = QPushButton("昨日内参")
        self.yesterday_briefing_button.setToolTip("生成昨天更新文章的内参日报")
        self.yesterday_briefing_button.clicked.connect(lambda: self.generate_briefing(1))  # 1表示昨天
        tools_layout.addWidget(self.yesterday_briefing_button)
        
        # 添加弹性空间
        tools_layout.addStretch(1)
        
        # 将工具栏添加到主布局中，位于编辑器的上方、搜索栏的下方
        self.layout.insertLayout(1, tools_layout)
    
    def process_search_query(self, query):
        """处理搜索查询，支持高级搜索语法
        
        支持的语法：
        - 引号包围的精确匹配: "精确词组"
        - 排除词: -排除的词
        - 空格分隔: 根据搜索模式决定是AND还是OR关系
        
        Returns:
            dict: 包含处理后的搜索条件
        """
        # 存储处理后的查询条件
        processed_terms = []
        exact_matches = []
        excluded_terms = []
        
        # 提取引号中的精确匹配
        exact_pattern = r'"([^"]+)"'
        exact_matches = re.findall(exact_pattern, query)
        
        # 移除引号部分，处理剩余内容
        query_without_quotes = re.sub(exact_pattern, '', query)
        
        # 拆分剩余词语
        terms = query_without_quotes.split()
        
        # 处理排除词和普通词
        for term in terms:
            if term.startswith('-') and len(term) > 1:
                excluded_terms.append(term[1:])
            elif term:  # 确保非空
                processed_terms.append(term)
                
        # 获取搜索模式
        search_mode = self.search_mode_combo.currentText()
        
        return {
            'terms': processed_terms,        # 普通搜索词
            'exact': exact_matches,          # 精确匹配词
            'excluded': excluded_terms,      # 排除词
            'mode': search_mode              # 搜索模式
        }

    def highlight_match(self, text, search_term, context_chars=100):
        """高亮显示搜索结果并显示上下文
        
        Args:
            text (str): 要搜索的文本
            search_term (str): 搜索词
            context_chars (int): 上下文字符数
            
        Returns:
            dict: 包含高亮匹配信息的字典
        """
        if not text or not search_term:
            return None
            
        search_term_lower = search_term.lower()
        text_lower = text.lower()
        
        # 查找匹配位置
        index = text_lower.find(search_term_lower)
        if index == -1:
            return None
            
        # 计算上下文范围
        context_start = max(0, index - context_chars)
        context_end = min(len(text), index + len(search_term) + context_chars)
        
        # 提取上下文
        before = text[context_start:index]
        match = text[index:index + len(search_term)]
        after = text[index + len(search_term):context_end]
        
        # 添加省略号表示截断
        if context_start > 0:
            before = "..." + before
        if context_end < len(text):
            after = after + "..."
            
        return {
            'before': before,
            'match': match,
            'after': after,
            'position': index
        }

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
            
        # 解析搜索查询
        search_params = self.process_search_query(search_text)
        
        # 输出处理后的搜索参数
        print("\n======== 搜索参数处理结果 ========")
        print(f"原始搜索文本: '{search_text}'")
        print(f"普通搜索词: {search_params['terms']}")
        print(f"精确匹配词: {search_params['exact']}")
        print(f"排除词: {search_params['excluded']}")
        print(f"搜索模式: {search_params['mode']}")
        print("==================================\n")
        
        # 获取选择的搜索范围
        scope_text = self.search_scope_combo.currentText()
        if scope_text == "搜索: 提示词":
            scope = 'prompts'
        elif scope_text == "搜索: PKM":
            scope = 'pkm'
        else: # 默认为全部
            scope = 'all'
            
        print(f"搜索范围: {scope_text} ({scope})")
        print(f"即将调用: db_manager.search_combined(search_text='{search_text}', scope='{scope}', search_params=<处理后的参数>)")
        
        # 执行组合搜索，传递高级搜索参数
        try:
            # 开始计时
            import time
            start_time = time.time()
            
            results = self.db_manager.search_combined(search_text, scope=scope, search_params=search_params)
            
            # 计算搜索耗时
            search_time = time.time() - start_time
            print(f"\n搜索完成，耗时: {search_time:.3f}秒，找到 {len(results)} 条结果")
            
            # 清空并填充结果列表
            self.search_results.clear()
            
            # 获取当前主题颜色
            header_bg = '#2E3440'  # 深色主题默认颜色
            item_bg_1 = '#3B4252'
            item_bg_2 = '#434C5E'
            text_color = '#D8DEE9'
            highlight_color = '#EBCB8B'  # 高亮颜色
            
            if self.theme_manager and self.theme_manager.current_theme == "light":
                header_bg = '#D8DEE9'  # 浅色主题颜色
                item_bg_1 = '#E5E9F0'
                item_bg_2 = '#ECEFF4'
                text_color = '#2E3440'
                highlight_color = '#5E81AC'  # 浅色主题高亮颜色
            
            # 添加搜索结果统计信息
            result_count = len(results)
            
            # 显示高级搜索条件
            search_info = f"在 [{scope_text.replace('搜索: ', '')}] 中找到 {result_count} 条匹配结果"
            if search_params['exact']:
                search_info += f" | 精确匹配: {', '.join(search_params['exact'])}"
            if search_params['excluded']:
                search_info += f" | 排除: {', '.join(search_params['excluded'])}"
            if search_params['mode']:
                search_info += f" | {search_params['mode'].split(':')[1].strip()}"
                
            count_item = QListWidgetItem(search_info)
            count_item.setFlags(Qt.ItemFlag.NoItemFlags)  # 设置为不可选
            count_item.setBackground(QColor(header_bg))
            count_item.setForeground(QColor(text_color))
            # 使标题文本居中
            count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.search_results.addItem(count_item)
            
            if results:
                print("\n搜索结果预览:")
                preview_count = min(3, len(results))
                
                for i, result in enumerate(results):
                    item = QListWidgetItem()
                    
                    # 输出前3条结果预览
                    if i < preview_count:
                        result_type = result.get('type', 'unknown')
                        print(f"结果 #{i+1} [{result_type}]: {str(result)[:100]}...")
                    
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
                        display_text += "[提示] " + prompt[:60]
                        if len(prompt) > 60:
                            display_text += "..."
                        
                        # 查找匹配的回复片段并高亮显示
                        for webview in result.get('webviews', []):
                            reply = webview.get('reply', '')
                            # 对每个搜索词进行高亮
                            for term in (search_params['terms'] + search_params['exact']):
                                highlight = self.highlight_match(reply, term, context_chars=100)
                                if highlight:
                                    display_text += f"\n匹配回复: {highlight['before']}<b style='color:{highlight_color};'>{highlight['match']}</b>{highlight['after']}"
                                    break
                            
                    elif result_type == 'pkm':
                        title = result.get('title', result.get('file_name', '未知标题'))
                        display_text += "[PKM] " + title
                        if len(title) > 60:
                            display_text += "..."
                        
                        # 显示完整文件路径
                        file_path = result.get('file_path', '')
                        if file_path:
                            display_text += f"\n路径: {file_path}"
                            
                        # 获取内容并高亮显示匹配
                        # 需要获取完整内容
                        file_id = result.get('id')
                        if file_id:
                            try:
                                content_data = self.db_manager.get_pkm_file_content(file_id)
                                if content_data and 'content' in content_data:
                                    content = content_data.get('content', '')
                                    # 对每个搜索词进行高亮
                                    for term in (search_params['terms'] + search_params['exact']):
                                        highlight = self.highlight_match(content, term, context_chars=100)
                                        if highlight:
                                            display_text += f"\n匹配内容: {highlight['before']}<b style='color:{highlight_color};'>{highlight['match']}</b>{highlight['after']}"
                                            break
                            except Exception as e:
                                print(f"获取PKM内容出错: {e}")
                            
                    else: # 未知类型
                        display_text += f"[未知类型] {str(result)[:60]}..."
                    
                    item.setText(display_text)
                    item.setData(Qt.ItemDataRole.UserRole, result) # 存储完整数据，包含type
                    self.search_results.addItem(item)
                
                self.search_results.setVisible(True)
            else:
                print("\n没有找到匹配的结果")
                # 添加"无结果"提示
                item = QListWidgetItem("没有找到匹配的结果")
                item.setFlags(Qt.ItemFlag.NoItemFlags)  # 使项目不可选
                item.setBackground(QColor(item_bg_1))
                item.setForeground(QColor(text_color))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.search_results.addItem(item)
                self.search_results.setVisible(True)
            
            print("==================================\n")
                
        except Exception as e:
            print(f"搜索出错: {e}")
            import traceback
            traceback.print_exc()
            # 添加错误提示
            self.search_results.clear()
            item = QListWidgetItem(f"搜索时出错: {str(e)}")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            item.setBackground(QColor("#BF616A"))  # 使用主题的红色
            item.setForeground(QColor("#ECEFF4"))  # 白色文字
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.search_results.addItem(item)
            self.search_results.setVisible(True)
    
    def submit_prompt(self):
        """提交提示词，支持整合搜索结果"""
        text = self.get_text().strip()
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
                
                # 解析搜索查询
                search_params = self.process_search_query(search_query)
                
                # 获取搜索结果(10条)，传递高级搜索参数
                search_results = self.db_manager.search_combined(search_query, scope=scope, limit=10, search_params=search_params)
                
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
                                
                                # 高亮展示匹配内容
                                highlighted_parts = []
                                for term in (search_params['terms'] + search_params['exact']):
                                    highlight = self.highlight_match(content, term, context_chars=100)
                                    if highlight:
                                        highlighted_parts.append(f"{highlight['before']}{highlight['match']}{highlight['after']}")
                                
                                search_content += f"【参考资料{i}】{title}\n"
                                
                                # 如果有高亮内容，优先展示，否则显示全文
                                if highlighted_parts:
                                    search_content += "\n".join(highlighted_parts[:3]) + "\n\n"  # 最多显示3个高亮片段
                                else:
                                    search_content += content + "\n\n"
                    
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
                                # 高亮展示匹配内容
                                highlighted_parts = []
                                for term in (search_params['terms'] + search_params['exact']):
                                    highlight = self.highlight_match(reply, term, context_chars=100)
                                    if highlight:
                                        highlighted_parts.append(f"{highlight['before']}{highlight['match']}{highlight['after']}")
                                
                                # 如果有高亮内容，优先展示，否则显示全文
                                if highlighted_parts:
                                    replies.append("\n".join(highlighted_parts[:2]))  # 最多显示2个高亮片段
                                else:
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
            # 没有搜索内容，直接发送提示词
            self.prompt_submitted.emit(text)
    
    def on_search_result_selected(self, item):
        """处理搜索结果选择"""
        data = item.data(Qt.ItemDataRole.UserRole)
        if data:
            result_type = data.get('type')
            if result_type == 'prompt':
                self.set_text(data.get('prompt', ''))
            elif result_type == 'pkm':
                # 对于PKM结果，获取文件内容并填入输入框
                file_id = data.get('id')
                if file_id and self.db_manager:
                    try:
                        pkm_data = self.db_manager.get_pkm_file_content(file_id)
                        if pkm_data and 'content' in pkm_data:
                            self.set_text(pkm_data['content'])
                        else:
                            self.set_text(f"错误：无法获取PKM文件内容 (ID: {file_id})")
                            print(f"无法获取PKM文件内容 (ID: {file_id})")
                    except Exception as e:
                        self.set_text(f"错误：获取PKM内容时出错: {str(e)}")
                        print(f"获取PKM内容时出错: {e}")
                else:
                    self.set_text("错误：无法识别PKM文件ID或缺少数据库管理器")
                    print("无法识别PKM文件ID或缺少数据库管理器")
            else:
                 self.set_text(f"未知类型结果: {str(data)}")
            
            # 隐藏搜索结果，清空搜索框
            self.search_results.setVisible(False)
            self.search_input.clear()
            self.text_edit.setFocus()
    
    def generate_briefing(self, days_ago=0):
        """
        生成内参日报
        
        Args:
            days_ago (int): 0表示今天，1表示昨天，以此类推
        """
        if not self.db_manager:
            print("错误：数据库管理器未初始化，无法生成内参")
            return
            
        try:
            import time
            from datetime import datetime, timedelta
            
            # 计算目标日期的时间戳范围
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            target_date = today - timedelta(days=days_ago)
            start_timestamp = int(target_date.timestamp())
            end_timestamp = int((target_date + timedelta(days=1)).timestamp()) - 1
            
            date_str = target_date.strftime('%Y年%m月%d日')
            
            # 查询数据库获取该日期范围内的文章
            cursor = self.db_manager.conn.cursor()
            
            # 查询当天创建或修改的PKM文件
            # 优先使用原始文件的创建时间(created_at)和修改时间(last_modified)，不使用数据库更新时间(updated_at)
            cursor.execute("""
                SELECT id, file_path, file_name, title, content, last_modified, created_at
                FROM pkm_files
                WHERE (created_at BETWEEN ? AND ?) OR (last_modified BETWEEN ? AND ?)
                ORDER BY 
                    CASE WHEN created_at BETWEEN ? AND ? THEN 0 ELSE 1 END,  -- 优先显示新创建的文章
                    last_modified DESC  -- 其次按文件修改时间降序
            """, (
                start_timestamp, end_timestamp,  # created_at范围
                start_timestamp, end_timestamp,  # last_modified范围
                start_timestamp, end_timestamp   # 用于CASE判断的范围
            ))
            
            articles = cursor.fetchall()
            
            if not articles:
                print(f"未找到{date_str}创建或修改的文章")
                # 在输入框中提示用户
                self.set_text(f"未找到{date_str}创建或修改的文章，请尝试查询其他日期。")
                return
                
            # 构建提示词
            prompt = f"# {date_str}内参日报\n\n"
            prompt += "请对以下今日创建和修改的文章内容进行综合分析和总结，生成一份内参日报。内参日报应包含：\n"
            prompt += "1. 今日重要内容概述\n"
            prompt += "2. 各文章的核心观点和主要信息\n"
            prompt += "3. 对这些信息的见解和分析\n"
            prompt += "4. 可能的行动建议或应用价值\n\n"
            prompt += "以下是今日文章内容：\n\n"
            
            # 添加文章内容
            article_count = 0
            for i, article in enumerate(articles):
                article_id, file_path, file_name, title, content, last_modified, created_at = article
                
                # 使用文件名作为标题（如果title为空）
                article_title = title or file_name
                
                # 文章是新创建的还是修改的
                status = "新创建" if created_at >= start_timestamp and created_at <= end_timestamp else "修改"
                
                # 格式化时间戳 - 使用last_modified而不是updated_at
                modify_time = datetime.fromtimestamp(last_modified).strftime('%H:%M:%S')
                
                # 截取内容（限制每篇文章的长度，避免整体提示词过长）
                max_content_length = 5000  # 每篇文章最多5000字符
                if content and len(content) > max_content_length:
                    content = content[:max_content_length] + "...(内容过长已截断)"
                
                # 只有当内容不为空时才添加文章
                if content:
                    prompt += f"## 文章{i+1}: {article_title} ({status}于{modify_time})\n\n"
                    prompt += f"{content}\n\n"
                    prompt += "---\n\n"
                    article_count += 1
                
                # 限制文章数量，避免提示词过长
                if article_count >= 10:
                    prompt += f"(共有{len(articles)}篇文章，由于长度限制只显示前10篇)\n\n"
                    break
            
            # 最终指示
            prompt += f"\n请根据以上{article_count}篇文章，生成一份全面、深入且有见解的{date_str}内参日报。内容应该是高度概括的，突出重点信息和价值观点。"
            
            # 填充到编辑器
            self.set_text(prompt)
            
            # 自动发送到AI平台
            self.prompt_submitted.emit(prompt)
            
            print(f"已生成{date_str}内参日报，共包含{article_count}篇文章")
            
        except Exception as e:
            import traceback
            print(f"生成内参日报时出错: {e}")
            traceback.print_exc()
            self.set_text(f"生成内参日报时出错: {str(e)}")
    
    def _update_icons(self):
        """更新图标颜色"""
        # 调用父类方法更新编辑器图标
        super()._update_icons()
        
        print("更新按钮样式和图标...")
        
        # 获取当前主题颜色
        icon_color = '#88C0D0'  # 默认强调色
        btn_fg_color = '#FFFFFF'  # 默认暗色模式白色
        
        if self.theme_manager:
            theme_colors = self.theme_manager.get_current_theme_colors()
            icon_color = theme_colors.get('accent', icon_color)
            btn_fg_color = '#FFFFFF' if theme_colors.get('is_dark', True) else '#2E3440'
            
            print(f"当前主题: {'深色' if theme_colors.get('is_dark', True) else '浅色'}")
            print(f"按钮前景色: {btn_fg_color}")
            
            # 确保连接主题变化信号（避免重复连接）
            try:
                self.theme_manager.theme_changed.disconnect(self._update_icons)
            except:
                pass
            self.theme_manager.theme_changed.connect(self._update_icons)
        
        # 如果处于模板模式，强制设置预览图标为编辑图标
        if self.input_stack.currentIndex() == 1:
            # 在模板模式下，显示"编辑"图标
            self.preview_toggle_action.setIcon(qta.icon("fa5s.edit", color=icon_color))
            self.preview_toggle_action.setToolTip("切换到编辑模式")
        
        # 更新搜索按钮图标
        if hasattr(self, 'search_button'):
            try:
                self.search_button.setIcon(qta.icon("fa5s.search", color=btn_fg_color))
            except Exception as e:
                print(f"更新搜索按钮图标出错: {e}")
                
        # 更新发送按钮图标
        if hasattr(self, 'send_button'):
            try:
                self.send_button.setIcon(qta.icon("fa5s.paper-plane", color=btn_fg_color))
            except Exception as e:
                print(f"更新发送按钮图标出错: {e}")
                
        # 更新内参按钮图标
        if hasattr(self, 'daily_briefing_button'):
            try:
                self.daily_briefing_button.setIcon(qta.icon("fa5s.newspaper", color=btn_fg_color))
            except Exception as e:
                print(f"更新每日内参按钮图标出错: {e}")
                
        if hasattr(self, 'yesterday_briefing_button'):
            try:
                self.yesterday_briefing_button.setIcon(qta.icon("fa5s.history", color=btn_fg_color))
            except Exception as e:
                print(f"更新昨日内参按钮图标出错: {e}")
        
        # 统一设置只有图标的按钮样式
        icon_buttons = [
            self.template_component.template_dir_button,
            self.template_component.refresh_button,
        ]
        
        # 统一设置带文本的按钮样式
        text_buttons = [
            self.daily_briefing_button,
            self.yesterday_briefing_button,
            self.search_button,
            self.send_button
        ]
        
        # 为图标按钮设置样式
        for btn in icon_buttons:
            if btn:
                btn.setFlat(True)
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent;
                        border: none;
                        color: {btn_fg_color};
                        padding: 4px 8px;
                    }}
                    QPushButton:hover {{
                        background: rgba(136,192,208,0.08);
                    }}
                    QPushButton:pressed {{
                        background: rgba(136,192,208,0.15);
                    }}
                """)
        
        # 为带文本的按钮设置不同的样式
        for btn in text_buttons:
            if btn:
                btn.setFlat(True)
                # 直接将颜色设置为主题色
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent;
                        border: none;
                        color: {btn_fg_color};
                        padding: 4px 8px;
                    }}
                    QPushButton:hover {{
                        background: rgba(136,192,208,0.08);
                    }}
                    QPushButton:pressed {{
                        background: rgba(136,192,208,0.15);
                    }}
                """)
    
    def _toggle_preview_mode(self):
        """重写父类的预览切换方法，确保与input_stack配合"""
        # 判断当前是否在直接输入模式
        if self.input_stack.currentIndex() == 0:
            # 在直接输入模式，可以切换预览/编辑状态
            # 调用父类方法处理预览逻辑
            super()._toggle_preview_mode()
        else:
            # 在模板模式，不进行任何切换，因为模板模式有自己的预览
            # 但我们可以更新图标状态，使图标显示正确
            self._update_icons()
    
    def submit_current_paragraph_with_search(self):
        """
        提交当前段落的提示词，如果搜索框有内容则先执行搜索再组合结果后发送
        """
        # 获取当前段落文本
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
        
        # 获取搜索框内容
        search_query = self.search_input.text().strip()
        
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
                
                # 解析搜索查询
                search_params = self.process_search_query(search_query)
                
                # 获取搜索结果(10条)，传递高级搜索参数
                search_results = self.db_manager.search_combined(search_query, scope=scope, limit=10, search_params=search_params)
                
                # 首先构建问题部分
                final_prompt = f"{paragraph_text}\n\n"
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
                                
                                # 高亮展示匹配内容
                                highlighted_parts = []
                                for term in (search_params['terms'] + search_params['exact']):
                                    highlight = self.highlight_match(content, term, context_chars=100)
                                    if highlight:
                                        highlighted_parts.append(f"{highlight['before']}{highlight['match']}{highlight['after']}")
                                
                                search_content += f"【参考资料{i}】{title}\n"
                                
                                # 如果有高亮内容，优先展示，否则显示全文
                                if highlighted_parts:
                                    search_content += "\n".join(highlighted_parts[:3]) + "\n\n"  # 最多显示3个高亮片段
                                else:
                                    search_content += content + "\n\n"
                    
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
                                # 高亮展示匹配内容
                                highlighted_parts = []
                                for term in (search_params['terms'] + search_params['exact']):
                                    highlight = self.highlight_match(reply, term, context_chars=100)
                                    if highlight:
                                        highlighted_parts.append(f"{highlight['before']}{highlight['match']}{highlight['after']}")
                                
                                # 如果有高亮内容，优先展示，否则显示全文
                                if highlighted_parts:
                                    replies.append("\n".join(highlighted_parts[:2]))  # 最多显示2个高亮片段
                                else:
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
                print(f"发送当前段落 + 搜索结果: {len(final_prompt)}字符")
                self.prompt_submitted.emit(final_prompt)
                
            except Exception as e:
                print(f"整合搜索结果时出错: {e}")
                # 如果出错，仍然发送原始段落文本
                self.prompt_submitted.emit(paragraph_text)
        else:
            # 没有搜索内容，直接发送当前段落文本
            self.prompt_submitted.emit(paragraph_text) 