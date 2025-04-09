#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
AI视图组件
负责管理AI对话页面，包含多个AI网页视图
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QSplitter
from PyQt6.QtCore import Qt, QUrl, QFile, QIODevice
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage
from PyQt6.QtGui import QPixmap, QIcon
import os
import qtawesome as qta

from app.config import SUPPORTED_AI_PLATFORMS
from app.controllers.web_profile_manager import WebProfileManager
from app.controllers.settings_manager import SettingsManager

# 图标文件夹路径
ICON_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "icons")
# 注入脚本路径
INJECTOR_SCRIPT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "js", "prompt_injector.js")

class AIWebView(QWebEngineView):
    """单个AI网页视图"""
    
    def __init__(self, ai_config):
        """初始化AI网页视图
        
        Args:
            ai_config (dict): AI平台配置字典
        """
        super().__init__()
        self.ai_name = ai_config["name"]
        self.ai_url = ai_config["url"]
        self.input_selector = ai_config["input_selector"]
        self.submit_selector = ai_config["submit_selector"]
        self.script_injected = False
        
        # 使用共享的profile，保存登录信息
        self.profile_manager = WebProfileManager()
        shared_profile = self.profile_manager.get_profile()
        web_page = QWebEnginePage(shared_profile, self)
        self.setPage(web_page)
        
        # 设置页面样式
        self.setStyleSheet("""
            QWebEngineView {
                background: #2E3440;
            }
        """)
        
        # 设置最小高度
        self.setMinimumHeight(30)
        
        # 加载网页
        self.load(QUrl(self.ai_url))
        
        # 设置加载状态监听
        self.loadFinished.connect(self.on_load_finished)
    
    def on_load_finished(self, success):
        """网页加载完成后的处理"""
        if success:
            print(f"{self.ai_name} 已加载")
            # 注入提示词注入脚本
            self.inject_script()
        else:
            print(f"{self.ai_name} 加载失败")
    
    def inject_script(self):
        """注入提示词注入脚本"""
        if self.script_injected:
            return
            
        try:
            # 读取脚本文件
            script_file = QFile(INJECTOR_SCRIPT_PATH)
            
            if script_file.open(QIODevice.ReadOnly | QIODevice.Text):
                script_content = script_file.readAll().data().decode('utf-8')
                script_file.close()
                
                # 注入脚本，简单执行不使用JavaScriptFeature
                self.page().runJavaScript(script_content)
                self.script_injected = True
                print(f"已向 {self.ai_name} 注入提示词脚本")
            else:
                print(f"无法打开脚本文件: {INJECTOR_SCRIPT_PATH}")
        except Exception as e:
            print(f"注入脚本时出错: {e}")
    
    def fill_prompt(self, prompt_text):
        """填充提示词并提交
        
        Args:
            prompt_text (str): 提示词文本
        """
        # 确保脚本已注入
        if not self.script_injected:
            self.inject_script()
            
        # 转义特殊字符
        escaped_prompt = prompt_text.replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n').replace('\r', '\\r')
            
        # 使用新的注入方法
        js_code = f"window.AiSparkHub.injectPrompt('{escaped_prompt}')"
        self.page().runJavaScript(js_code)

class AIView(QWidget):
    """AI对话页面，管理多个AI网页视图"""
    
    def __init__(self):
        super().__init__()
        
        # 获取设置管理器
        self.settings_manager = SettingsManager()
        
        # 创建布局
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # 创建分割器，用于调整各AI视图的宽度比例
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.layout.addWidget(self.splitter)
        
        # 存储AI网页视图
        self.ai_web_views = {}
        
        # 加载用户配置的AI平台
        self.load_ai_platforms()
    
    def load_ai_platforms(self):
        """根据用户设置加载AI平台"""
        # 获取用户启用的AI平台
        enabled_platforms = self.settings_manager.get_enabled_ai_platforms()
        
        # 清空现有视图
        for i in range(self.splitter.count()):
            widget = self.splitter.widget(0)
            widget.setParent(None)
        
        self.ai_web_views.clear()
        
        # 加载新视图
        for platform in enabled_platforms:
            self.add_ai_web_view_from_config(platform)
    
    def add_ai_web_view_from_config(self, ai_config):
        """从配置添加AI网页视图
        
        Args:
            ai_config (dict): AI平台配置
        
        Returns:
            AIWebView: 创建的AI网页视图
        """
        # 创建容器和标题
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建标题栏
        title_widget = QWidget()
        title_widget.setMaximumHeight(30)
        title_widget.setObjectName("aiTitleBar")
        title_layout = QHBoxLayout(title_widget)
        title_layout.setContentsMargins(8, 2, 8, 2)
        
        # 创建标题图标和文本
        icon_label = QLabel()
        
        # 尝试加载本地图标
        # 先尝试PNG格式
        icon_path = os.path.join(ICON_DIR, f"{ai_config['key']}.png")
        # 如果PNG不存在，尝试ICO格式
        if not os.path.exists(icon_path):
            icon_path = os.path.join(ICON_DIR, f"{ai_config['key']}.ico")
        
        if os.path.exists(icon_path):
            if icon_path.endswith('.ico'):
                # 加载ICO图标
                icon = QIcon(icon_path)
                icon_label.setPixmap(icon.pixmap(16, 16))
            else:
                # 加载PNG等其他格式图标
                icon_pixmap = QPixmap(icon_path).scaled(16, 16, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                icon_label.setPixmap(icon_pixmap)
        else:
            # 如果本地图标不存在，使用默认图标
            try:
                default_icon = qta.icon("fa5s.comment")
                icon_label.setPixmap(default_icon.pixmap(16, 16))
            except Exception:
                # 如果qtawesome图标也失败，使用空白图标
                icon_label.setText("")
        
        title_label = QLabel(ai_config["name"])
        title_label.setStyleSheet("color: #D8DEE9; font-weight: bold;")
        
        # 创建居中容器
        center_widget = QWidget()
        center_layout = QHBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(4)
        
        # 将图标和标题添加到居中容器
        center_layout.addWidget(icon_label)
        center_layout.addWidget(title_label)
        
        # 在标题栏中添加居中对齐的容器
        title_layout.addStretch(1)
        title_layout.addWidget(center_widget)
        title_layout.addStretch(1)
        
        # 添加标题栏到容器
        container_layout.addWidget(title_widget)
        
        # 创建AI网页视图
        web_view = AIWebView(ai_config)
        
        # 添加到容器
        container_layout.addWidget(web_view)
        
        # 设置容器样式
        container.setStyleSheet("""
            #aiTitleBar {
                background: #3B4252;
                border-bottom: 1px solid #4C566A;
            }
        """)
        
        # 添加到分割器
        self.splitter.addWidget(container)
        
        # 存储网页视图
        self.ai_web_views[ai_config["key"]] = web_view
        
        # 调整分割器各部分的宽度比例
        self.adjust_splitter_sizes()
        
        return web_view
    
    def add_ai_web_view(self, ai_name, ai_url, input_selector=None, submit_selector=None):
        """添加AI网页视图 (兼容旧接口)
        
        Args:
            ai_name (str): AI名称
            ai_url (str): AI网页URL
            input_selector (str): 输入框选择器
            submit_selector (str): 提交按钮选择器
        """
        # 查找匹配的AI平台配置
        ai_config = None
        for key, config in SUPPORTED_AI_PLATFORMS.items():
            if config["name"] == ai_name:
                ai_config = config.copy()
                break
        
        # 如果没有找到匹配的配置，创建一个新的
        if not ai_config:
            ai_config = {
                "key": ai_name.lower(),
                "name": ai_name,
                "url": ai_url,
                "input_selector": input_selector,
                "submit_selector": submit_selector,
                "response_selector": ""
            }
        
        # 使用自定义选择器覆盖默认值
        if input_selector:
            ai_config["input_selector"] = input_selector
        if submit_selector:
            ai_config["submit_selector"] = submit_selector
        
        return self.add_ai_web_view_from_config(ai_config)
    
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