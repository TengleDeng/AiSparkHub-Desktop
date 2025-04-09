#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
AI视图组件
负责管理AI对话页面，包含多个AI网页视图
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QSplitter
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView
import qtawesome as qta

from app.config import DEFAULT_AI_PROVIDERS, JS_FILL_PROMPT_TEMPLATE

class AIWebView(QWebEngineView):
    """单个AI网页视图"""
    
    def __init__(self, ai_name, ai_url, input_selector, submit_selector):
        super().__init__()
        self.ai_name = ai_name
        self.ai_url = ai_url
        self.input_selector = input_selector
        self.submit_selector = submit_selector
        
        # 加载网页
        self.load(QUrl(ai_url))
        
        # 设置加载状态监听
        self.loadFinished.connect(self.on_load_finished)
    
    def on_load_finished(self, success):
        """网页加载完成后的处理"""
        if success:
            print(f"{self.ai_name} 已加载")
        else:
            print(f"{self.ai_name} 加载失败")
    
    def fill_prompt(self, prompt_text):
        """填充提示词并提交
        
        Args:
            prompt_text (str): 提示词文本
        """
        # 准备JS脚本
        js_script = JS_FILL_PROMPT_TEMPLATE.format(
            input_selector=self.input_selector,
            submit_selector=self.submit_selector,
            prompt=prompt_text
        )
        
        # 运行JS脚本
        self.page().runJavaScript(js_script)

class AIView(QWidget):
    """AI对话页面，管理多个AI网页视图"""
    
    def __init__(self):
        super().__init__()
        
        # 创建布局
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # 创建分割器，用于调整各AI视图的宽度比例
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.layout.addWidget(self.splitter)
        
        # 存储AI网页视图
        self.ai_web_views = {}
    
    def add_ai_web_view(self, ai_name, ai_url, input_selector=None, submit_selector=None):
        """添加AI网页视图
        
        Args:
            ai_name (str): AI名称
            ai_url (str): AI网页URL
            input_selector (str): 输入框选择器
            submit_selector (str): 提交按钮选择器
        """
        # 如果未提供选择器，尝试从默认配置中获取
        if not input_selector or not submit_selector:
            for provider in DEFAULT_AI_PROVIDERS:
                if provider["name"] == ai_name:
                    input_selector = provider.get("input_selector")
                    submit_selector = provider.get("submit_selector")
                    break
        
        # 创建容器和标题
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        
        # 添加标题栏
        title_bar = QWidget()
        title_bar_layout = QHBoxLayout(title_bar)
        title_bar_layout.setContentsMargins(8, 4, 8, 4)
        
        # 添加图标和标题
        if ai_name == "ChatGPT":
            icon = qta.icon("fa5s.comment-dots", color="#10a37f")
        elif ai_name == "DeepSeek":
            icon = qta.icon("fa5s.brain", color="#3b5fff")
        else:
            icon = qta.icon("fa5s.robot", color="#88C0D0")
        
        title_label = QLabel(f" {ai_name}")
        title_label.setStyleSheet("font-weight: bold;")
        
        title_bar_layout.addWidget(QLabel(""))
        title_bar_layout.addWidget(title_label)
        title_bar_layout.addWidget(QLabel(""))
        
        # 创建AI网页视图
        web_view = AIWebView(ai_name, ai_url, input_selector, submit_selector)
        
        # 添加到容器
        container_layout.addWidget(title_bar)
        container_layout.addWidget(web_view)
        
        # 添加到分割器
        self.splitter.addWidget(container)
        
        # 存储网页视图
        self.ai_web_views[ai_name] = web_view
        
        # 调整分割器各部分的宽度比例
        self.adjust_splitter_sizes()
        
        return web_view
    
    def adjust_splitter_sizes(self):
        """调整分割器各部分的宽度比例"""
        count = self.splitter.count()
        if count > 0:
            width = self.width()
            sizes = [width // count] * count
            self.splitter.setSizes(sizes)
    
    def fill_prompt(self, prompt_text):
        """向所有AI网页填充提示词
        
        Args:
            prompt_text (str): 提示词文本
        """
        for web_view in self.ai_web_views.values():
            web_view.fill_prompt(prompt_text)
    
    def resizeEvent(self, event):
        """窗口大小变化时调整分割器各部分的宽度比例"""
        super().resizeEvent(event)
        self.adjust_splitter_sizes() 