#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
提示词同步控制器
负责将提示词从辅助窗口同步到主窗口的AI视图
"""

from PyQt6.QtCore import QObject, pyqtSignal

from app.config import JS_FILL_PROMPT_TEMPLATE

class PromptSync(QObject):
    """提示词同步管理器，负责将提示词从输入区同步到AI视图"""
    
    prompt_synced = pyqtSignal(str)  # 提示词同步成功信号
    
    def __init__(self):
        super().__init__()
        self.ai_views = []  # 存储AI视图引用
    
    def register_ai_view(self, ai_view):
        """注册AI视图实例
        
        Args:
            ai_view: AIView实例，用于接收提示词
        """
        if ai_view not in self.ai_views:
            self.ai_views.append(ai_view)
    
    def unregister_ai_view(self, ai_view):
        """取消注册AI视图实例
        
        Args:
            ai_view: 要移除的AIView实例
        """
        if ai_view in self.ai_views:
            self.ai_views.remove(ai_view)
    
    def sync_prompt(self, prompt_text):
        """将提示词同步到所有注册的AI视图
        
        Args:
            prompt_text (str): 提示词文本
        
        Returns:
            bool: 同步是否成功
        """
        if not self.ai_views:
            return False
        
        # 转义JavaScript中的特殊字符
        escaped_prompt = prompt_text.replace("'", "\\'").replace("\n", "\\n")
        
        # 向所有AI视图发送提示词
        for ai_view in self.ai_views:
            ai_view.fill_prompt(escaped_prompt)
        
        # 发送同步成功信号
        self.prompt_synced.emit(prompt_text)
        
        return True 