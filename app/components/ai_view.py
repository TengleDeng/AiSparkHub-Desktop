#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
AI视图组件
负责管理AI对话页面，包含多个AI网页视图
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QSplitter, QComboBox, QPushButton, QApplication
from PyQt6.QtCore import Qt, QUrl, QFile, QIODevice, QTimer, QSize
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PyQt6.QtGui import QPixmap, QIcon
import os
import qtawesome as qta
import sys

from app.config import SUPPORTED_AI_PLATFORMS
from app.controllers.web_profile_manager import WebProfileManager
from app.controllers.settings_manager import SettingsManager
from app.controllers.theme_manager import ThemeManager

# 图标文件夹路径 - 考虑打包环境和开发环境
ICON_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "icons")
if not os.path.exists(ICON_DIR) and getattr(sys, 'frozen', False):
    # 打包环境下可能路径不同，尝试相对于可执行文件的路径
    base_dir = os.path.dirname(sys.executable)
    ICON_DIR = os.path.join(base_dir, "icons")

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
        self.response_selector = ai_config.get("response_selector", "")
        
        # 使用共享的profile，保存登录信息
        self.profile_manager = WebProfileManager()
        shared_profile = self.profile_manager.get_profile()
        web_page = QWebEnginePage(shared_profile, self)
        self.setPage(web_page)
        
        # 设置剪贴板权限
        settings = web_page.settings()
        
        # 设置权限 - 使用try/except以兼容不同版本的PyQt6
        # 剪贴板权限
        try:
            settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard, True)
            print(f"{self.ai_name}: 已启用JavascriptCanAccessClipboard")
        except (AttributeError, TypeError):
            print(f"{self.ai_name}: 警告: JavascriptCanAccessClipboard属性不可用")
        
        try:
            settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanPaste, True)
            print(f"{self.ai_name}: 已启用JavascriptCanPaste")
        except (AttributeError, TypeError):
            print(f"{self.ai_name}: 警告: JavascriptCanPaste属性不可用")
        
        # 其他权限
        try:
            settings.setAttribute(QWebEngineSettings.WebAttribute.FullScreenSupportEnabled, True)
            print(f"{self.ai_name}: 已启用FullScreenSupportEnabled")
        except (AttributeError, TypeError):
            print(f"{self.ai_name}: 警告: FullScreenSupportEnabled属性不可用")
        
        try:
            settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
            print(f"{self.ai_name}: 已启用LocalContentCanAccessRemoteUrls")
        except (AttributeError, TypeError):
            print(f"{self.ai_name}: 警告: LocalContentCanAccessRemoteUrls属性不可用")
            
        try:
            settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
            print(f"{self.ai_name}: 已启用LocalContentCanAccessFileUrls")
        except (AttributeError, TypeError):
            print(f"{self.ai_name}: 警告: LocalContentCanAccessFileUrls属性不可用")
        
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
            
            # 注入F12快捷键脚本，用于打开开发者工具
            try:
                debug_key_script = """
                document.addEventListener('keydown', function(e) {
                    if (e.key === 'F12') {
                        console.log('F12 pressed - attempting to open dev tools');
                        // 在PyQt6 6.9.0中，此操作可打开开发者工具
                    }
                });
                console.log('Debug key listener installed');
                """
                self.page().runJavaScript(debug_key_script)
            except Exception as e:
                print(f"注入F12快捷键脚本失败: {e}")
        else:
            print(f"{self.ai_name} 加载失败")
    
    def inject_script(self):
        """注入提示词注入脚本"""
        try:
            # 读取脚本文件
            script_file = QFile(INJECTOR_SCRIPT_PATH)
            
            if script_file.open(QIODevice.ReadOnly | QIODevice.Text):
                script_content = script_file.readAll().data().decode('utf-8')
                script_file.close()
                
                # 注入脚本 - 移除回调
                self.page().runJavaScript(script_content)
                print(f"已尝试向 {self.ai_name} 注入提示词脚本") # 更新日志信息
            else:
                print(f"无法打开脚本文件: {INJECTOR_SCRIPT_PATH}")
        except Exception as e:
            print(f"注入脚本时出错: {e}")
    
    def fill_prompt(self, prompt_text):
        """填充提示词并提交
        
        Args:
            prompt_text (str): 提示词文本
        """
        # 确保特殊字符的正确转义 (单引号、换行符、回车符和反斜杠)
        escaped_text = prompt_text.replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n').replace('\r', '\\r')
            
        # 调用注入方法 - 使用预先加载的脚本函数
        js_code = f"window.AiSparkHub.injectPrompt('{escaped_text}')"
        self.page().runJavaScript(js_code, self._handle_injection_result)
    
    def _handle_check_result(self, result):
        """处理脚本检查结果"""
        print(f"[{self.ai_name}] 脚本检查: {result}")
    
    def _handle_injection_result(self, result):
        """处理注入结果"""
        print(f"[{self.ai_name}] 注入结果: {result}")
    
    def get_current_url(self, callback):
        """获取当前页面URL
        
        Args:
            callback: 回调函数，接收URL字符串
        """
        self.page().runJavaScript("window.AiSparkHub.getCurrentPageUrl()", callback)
    
    def get_ai_response(self, callback):
        """获取AI回复内容
        
        Args:
            callback: 回调函数，接收回复内容字符串
        """
        self.page().runJavaScript("window.AiSparkHub.getLatestAIResponse()", callback)
    
    def get_prompt_response(self, callback):
        """获取提示词响应信息（URL和回复内容）
        
        Args:
            callback: 回调函数，接收包含url和reply的对象
        """
        self.page().runJavaScript("window.AiSparkHub.getPromptResponse()", callback)

class AIView(QWidget):
    """AI对话页面，管理多个AI网页视图"""
    
    def __init__(self):
        super().__init__()
        
        # 将 ThemeManager 初始化移到开头
        self.theme_manager = None
        app = QApplication.instance()
        if hasattr(app, 'theme_manager') and isinstance(app.theme_manager, ThemeManager):
            self.theme_manager = app.theme_manager
            self.theme_manager.theme_changed.connect(self._update_all_button_icons)
        else:
            print("警告：无法在 AIView 中获取 ThemeManager 实例")
            
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
        container_layout.setSpacing(0)  # 设置布局间距为0，消除标题栏与网页内容之间的空白
        
        # 创建标题栏
        title_widget = QWidget()
        title_widget.setMaximumHeight(30)
        title_widget.setObjectName("aiTitleBar")
        title_layout = QHBoxLayout(title_widget)
        title_layout.setContentsMargins(8, 2, 8, 2)
        
        # 创建AI选择下拉框
        ai_selector = QComboBox()
        ai_selector.setObjectName("aiSelector")
        ai_selector.setFixedHeight(24)
        
        # 获取所有支持的AI平台
        platforms = list(SUPPORTED_AI_PLATFORMS.items())
        
        # 为每个平台创建图标和添加到下拉菜单
        print(f"--- Populating dropdown for container expecting AI: {ai_config['name']} (key: {ai_config['key']}) ---")
        for i, (dict_key, platform_config) in enumerate(platforms):
            icon = None
            lowercase_key = platform_config["key"]
            
            # 先尝试加载本地图标文件
            icon_path = os.path.join(ICON_DIR, f"{lowercase_key}.png") # 先尝试png
            if not os.path.exists(icon_path):
                icon_path = os.path.join(ICON_DIR, f"{lowercase_key}.ico") # 再尝试ico
            
            if os.path.exists(icon_path):
                # 加载图标
                try:
                    if icon_path.endswith('.ico'):
                        icon = QIcon(icon_path)
                    else:
                        icon = QIcon(QPixmap(icon_path))
                except Exception as e:
                    print(f"  Error loading icon from {icon_path}: {e}")
                    icon = None  # 加载失败，设为None以便尝试qtawesome
            else:
                print(f"  Local icon not found for {lowercase_key}. Will try qtawesome.")
            
            # 如果本地图标加载失败，尝试使用qtawesome
            if icon is None:
                try:
                    # 根据AI平台选择合适的图标
                    icon_map = {
                        "chatgpt": "fa5b.chrome",      # ChatGPT使用Chrome图标
                        "kimi": "fa5s.robot",          # Kimi使用机器人图标
                        "doubao": "fa5s.comment",      # 其他平台使用通用对话图标
                        "yuanbao": "fa5s.comment-dots",
                        "perplexity": "fa5s.search",   # Perplexity用搜索图标
                        "metaso": "fa5s.search",       # 元搜索用搜索图标
                        "grok": "fa5b.twitter",        # Grok关联Twitter/X
                        "yiyan": "fa5b.baidu",         # 文心一言用百度图标
                        "gemini": "fa5b.google",       # Gemini用Google图标
                        "tongyi": "fa5b.alipay",       # 通义用阿里图标
                        "chatglm": "fa5s.brain",       # ChatGLM用脑图标
                        "biji": "fa5s.sticky-note",    # 笔记用便签图标
                        "n": "fa5s.yin-yang",          # N用特殊图标
                        "deepseek": "fa5s.power-off"   # DeepSeek用电源图标
                    }
                    
                    # 获取该平台对应的图标名，如果没有指定则使用评论图标
                    icon_name = icon_map.get(lowercase_key, "fa5s.comment")
                    icon = qta.icon(icon_name)
                except Exception as e:
                    print(f"  Error using qtawesome icon for {lowercase_key}: {e}")
                    # 如果qtawesome也失败，使用默认图标
                    icon = qta.icon("fa5s.comment")
                    print(f"  Falling back to default qtawesome icon: fa5s.comment")
            
            # 添加到下拉菜单，将平台 key (小写) 作为 userData 存储
            ai_selector.addItem(icon, platform_config["name"], userData=lowercase_key)
            
        # 手动查找目标索引
        target_key_to_find = ai_config["key"]
        found_index = -1
        for idx in range(ai_selector.count()):
            item_data = ai_selector.itemData(idx)
            # 确保比较的是同类型且值相等
            if isinstance(item_data, str) and item_data == target_key_to_find:
                found_index = idx
                break # 找到即停止
        
        # 设置当前选中的AI
        if found_index != -1:
            ai_selector.setCurrentIndex(found_index)
        else:
            print(f"!!! WARNING: Could not find index for UserData='{target_key_to_find}'. Defaulting to index 0.")
            ai_selector.setCurrentIndex(0) # 如果找不到，默认显示第一项
        
        # 连接选择变更信号
        ai_selector.currentIndexChanged.connect(lambda index, c=container, s=ai_selector: self.on_ai_changed(c, index, s))
        
        # 创建控制按钮的通用样式 - 添加 hover 和 pressed 样式
        button_style = """
            QPushButton {
                background-color: transparent;
                border: none;
                padding: 2px;
                border-radius: 3px;
                max-width: 22px;
                max-height: 22px;
            }
            QPushButton:hover {
                background-color: rgba(120, 120, 120, 0.2);
            }
            QPushButton:pressed {
                background-color: rgba(100, 100, 100, 0.3);
            }
        """
        
        # 创建控制按钮
        # 1. 向左移动按钮
        move_left_btn = QPushButton()
        move_left_btn.setIcon(qta.icon("fa5s.arrow-left"))
        move_left_btn.setToolTip("将此视图向左移动")
        move_left_btn.setStyleSheet(button_style)
        move_left_btn.setIconSize(QSize(14, 14))
        move_left_btn.clicked.connect(lambda _, c=container: self.move_view_left(c))
        
        # 2. 向右移动按钮
        move_right_btn = QPushButton()
        move_right_btn.setIcon(qta.icon("fa5s.arrow-right"))
        move_right_btn.setToolTip("将此视图向右移动")
        move_right_btn.setStyleSheet(button_style)
        move_right_btn.setIconSize(QSize(14, 14))
        move_right_btn.clicked.connect(lambda _, c=container: self.move_view_right(c))
        
        # 3. 刷新按钮
        refresh_btn = QPushButton()
        refresh_btn.setIcon(qta.icon("fa5s.sync"))
        refresh_btn.setToolTip("刷新此视图")
        refresh_btn.setStyleSheet(button_style)
        refresh_btn.setIconSize(QSize(14, 14))
        refresh_btn.clicked.connect(lambda _, c=container: self.refresh_view(c))
        
        # 4. 最大化/恢复按钮
        maximize_btn = QPushButton()
        maximize_btn.setIcon(qta.icon("fa5s.expand"))
        maximize_btn.setToolTip("最大化此视图")
        maximize_btn.setStyleSheet(button_style)
        maximize_btn.setIconSize(QSize(14, 14))
        maximize_btn.clicked.connect(lambda _, c=container, b=maximize_btn: self.toggle_maximize_view(c, b))
        
        # 5. 添加视图按钮
        add_btn = QPushButton()
        add_btn.setIcon(qta.icon("fa5s.plus"))
        add_btn.setToolTip("在右侧添加新视图")
        add_btn.setStyleSheet(button_style)
        add_btn.setIconSize(QSize(14, 14))
        add_btn.clicked.connect(lambda _, c=container: self.add_view_after(c))
        
        # 6. 关闭按钮
        close_btn = QPushButton()
        close_btn.setIcon(qta.icon("fa5s.times"))
        close_btn.setToolTip("关闭此视图")
        close_btn.setStyleSheet(button_style)
        close_btn.setIconSize(QSize(14, 14))
        close_btn.clicked.connect(lambda _, c=container: self.close_view(c))
        
        # 存储按钮引用，以便后续访问
        container.move_left_btn = move_left_btn
        container.move_right_btn = move_right_btn
        container.refresh_btn = refresh_btn
        container.maximize_btn = maximize_btn
        container.add_btn = add_btn
        container.close_btn = close_btn
        container.is_maximized = False  # 记录是否处于最大化状态
        
        # 设置按钮初始图标（带颜色）
        self._set_initial_button_icons(container)
        
        # 将下拉菜单添加到标题栏
        title_layout.addWidget(ai_selector)
        title_layout.addStretch(1)
        
        # 添加控制按钮到标题栏右侧
        title_layout.addWidget(move_left_btn)
        title_layout.addWidget(move_right_btn)
        title_layout.addWidget(refresh_btn)
        title_layout.addWidget(maximize_btn)
        title_layout.addWidget(add_btn)
        title_layout.addWidget(close_btn)
        
        # 添加标题栏到容器
        container_layout.addWidget(title_widget)
        
        # 创建AI网页视图
        web_view = AIWebView(ai_config)
        
        # 添加到容器并存储
        container_layout.addWidget(web_view)
        container.web_view = web_view  # 将web_view作为容器的属性存储
        container.ai_key = ai_config["key"]  # 存储当前加载的AI平台标识
        
        # 添加到分割器
        self.splitter.addWidget(container)
        
        # 存储网页视图 (确保key与存储时一致)
        self.ai_web_views[ai_config["key"]] = web_view
        
        # 调整分割器各部分的宽度比例
        self.adjust_splitter_sizes()
        
        # 更新导航按钮状态
        self.update_navigation_buttons()
        
        # 添加新方法：设置按钮初始图标
        self._set_initial_button_icons(container)
        
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
            
    def collect_all_responses(self, callback):
        """收集所有AI网页视图的响应信息
        
        收集每个WebView的URL和回复内容，并在完成后调用回调函数
        
        Args:
            callback: 回调函数，接收由各WebView返回的信息组成的列表
                     每项包含url和reply字段
        """
        responses = []
        pending_count = len(self.ai_web_views)
        
        if pending_count == 0:
            # 如果没有WebView，立即返回空列表
            callback([])
            return
        
        def response_collected(result, web_view_key):
            """单个响应收集完成的回调"""
            nonlocal responses, pending_count
            
            # 添加响应到列表
            if result:
                responses.append(result)
            else:
                # 如果获取失败，添加一个包含URL但没有回复的项
                web_view = self.ai_web_views[web_view_key]
                responses.append({
                    "url": web_view.url().toString(),
                    "reply": "无法获取回复内容"
                })
            
            # 减少待处理计数
            pending_count -= 1
            
            # 如果所有WebView都已处理完成，调用总回调
            if pending_count == 0:
                callback(responses)
        
        # 遍历所有WebView，获取响应
        for key, web_view in self.ai_web_views.items():
            web_view.get_prompt_response(lambda result, k=key: response_collected(result, k))
    
    def resizeEvent(self, event):
        """窗口大小变化时调整分割器各部分的宽度比例"""
        super().resizeEvent(event)
        self.adjust_splitter_sizes()
    
    def on_ai_changed(self, container, index, selector):
        """处理AI平台选择变更
        
        Args:
            container: 包含web_view的容器
            index: 选择的索引
            selector: 下拉菜单控件
        """
        # 获取选中的AI平台标识 (从 userData 获取)
        ai_key = selector.itemData(index) # userData 存储的是小写 key
        
        # 检查获取的 key 是否有效
        if not ai_key or not isinstance(ai_key, str):
             print(f"错误：从下拉菜单获取的 AI key 无效或类型错误 (index={index}, data={ai_key})")
             return
        
        print(f"--- AI Changed Signal Received: Index={index}, Selected Key='{ai_key}' ---")
        
        # 避免重复加载同一个平台
        if hasattr(container, 'ai_key') and container.ai_key == ai_key:
            print(f"  AI platform unchanged ('{ai_key}'), no switch needed.")
            return
        
        # 获取AI平台配置 (使用小写 key 从 SUPPORTED_AI_PLATFORMS 查找)
        # 注意：SUPPORTED_AI_PLATFORMS 的键是大写的，值里面的 'key' 是小写的
        ai_config = None
        for dict_key, platform_config in SUPPORTED_AI_PLATFORMS.items():
            if platform_config.get("key") == ai_key:
                ai_config = platform_config
                print(f"  Found matching config in SUPPORTED_AI_PLATFORMS using key '{ai_key}' (Original dict key: '{dict_key}')")
                break
        
        if not ai_config:
            print(f"!!! ERROR: Could not find AI platform config for key '{ai_key}' in SUPPORTED_AI_PLATFORMS.")
            return
        
        print(f"  Preparing to switch to AI platform: {ai_config['name']}")
        
        # 保存旧的web_view引用以便稍后删除
        old_web_view = None
        if hasattr(container, 'web_view'):
            old_web_view = container.web_view
            print(f"  Found old WebView instance: {old_web_view.ai_name}")
        
        # 创建新的web_view
        web_view = AIWebView(ai_config) # 使用找到的 config 创建
        
        # 替换容器中的web_view
        layout = container.layout()
        if old_web_view:
            # 移除旧的web_view
            layout.removeWidget(old_web_view)
            print(f"  Removed old WebView ({old_web_view.ai_name}) from layout.")
            old_web_view.setParent(None) # 解除父子关系，确保能被删除
            old_web_view.deleteLater()
            print(f"  Old WebView ({old_web_view.ai_name}) marked for deletion.")
            
            # 从字典中移除旧的引用 (使用旧的 key)
            old_key = container.ai_key # 获取旧的key
            if old_key in self.ai_web_views and self.ai_web_views[old_key] == old_web_view:
                del self.ai_web_views[old_key]
                print(f"  Removed old reference from ai_web_views dictionary (key: '{old_key}')")
            else:
                 print(f"  Warning: Could not find/remove old reference in ai_web_views for key '{old_key}'")
        else:
            print("  Warning: No old WebView reference found in container.")
        
        # 添加新的web_view
        layout.addWidget(web_view)
        print(f"  Added new WebView ({web_view.ai_name}) to layout.")
        
        # 更新容器的属性
        container.web_view = web_view
        container.ai_key = ai_key # 更新为新的小写 key
        print(f"  Container attributes updated to new platform (key: '{ai_key}')")
        
        # 更新web_view字典 (使用新的小写 key)
        self.ai_web_views[ai_key] = web_view
        print(f"  ai_web_views dictionary updated with new reference (key: '{ai_key}')")
        
        print(f"==> Successfully switched to AI platform: {ai_config['name']}")
    
    def move_view_left(self, container):
        """将视图向左移动一个位置
        
        Args:
            container: 包含web_view的容器
        """
        index = self.splitter.indexOf(container)
        if index > 0:  # 如果不是最左侧的视图
            # 获取左侧视图
            left_widget = self.splitter.widget(index - 1)
            
            # 记住当前的大小
            sizes = self.splitter.sizes()
            left_size = sizes[index - 1]
            current_size = sizes[index]
            
            # 移除并重新插入容器
            self.splitter.insertWidget(index - 1, container)
            
            # 恢复大小
            sizes[index - 1] = current_size
            sizes[index] = left_size
            self.splitter.setSizes(sizes)
            
            # 更新导航按钮状态
            self.update_navigation_buttons()
    
    def move_view_right(self, container):
        """将视图向右移动一个位置
        
        Args:
            container: 包含web_view的容器
        """
        index = self.splitter.indexOf(container)
        if index < self.splitter.count() - 1:  # 如果不是最右侧的视图
            # 获取右侧视图
            right_widget = self.splitter.widget(index + 1)
            
            # 记住当前的大小
            sizes = self.splitter.sizes()
            right_size = sizes[index + 1]
            current_size = sizes[index]
            
            # 移除并重新插入容器
            self.splitter.insertWidget(index + 1, container)
            
            # 恢复大小
            sizes[index] = right_size
            sizes[index + 1] = current_size
            self.splitter.setSizes(sizes)
            
            # 更新导航按钮状态
            self.update_navigation_buttons()
    
    def refresh_view(self, container):
        """刷新视图
        
        Args:
            container: 包含web_view的容器
        """
        if hasattr(container, 'web_view'):
            container.web_view.reload()
    
    def toggle_maximize_view(self, container, button):
        """切换视图的最大化/恢复状态
        
        Args:
            container: 包含web_view的容器
            button: 最大化/恢复按钮
        """
        # 获取所有视图容器
        containers = []
        for i in range(self.splitter.count()):
            containers.append(self.splitter.widget(i))
        
        theme_colors = self.theme_manager.get_current_theme_colors() if self.theme_manager else {}
        icon_color = theme_colors.get('foreground', '#D8DEE9') # 获取当前主题的前景色
            
        if not container.is_maximized:
            # 最大化：隐藏其他视图，调整当前视图为全宽
            for c in containers:
                if c != container:
                    c.hide()
            # 更新按钮图标为"恢复"
            button.setIcon(qta.icon("fa5s.compress", color=icon_color))
            button.setToolTip("恢复视图大小")
            container.is_maximized = True
        else:
            # 恢复：显示所有视图，重新调整宽度
            for c in containers:
                c.show()
            # 更新按钮图标为"最大化"
            button.setIcon(qta.icon("fa5s.expand", color=icon_color))
            button.setToolTip("最大化此视图")
            container.is_maximized = False
            # 重新调整所有视图大小
            self.adjust_splitter_sizes()
    
    def add_view_after(self, container):
        """在当前视图右侧添加新视图
        
        Args:
            container: 包含web_view的容器
        """
        index = self.splitter.indexOf(container)
        
        # 获取当前支持的AI平台列表
        enabled_platforms = self.settings_manager.get_enabled_ai_platforms()
        
        # 如果有可用的AI平台，则添加第一个
        if enabled_platforms:
            # 创建新视图
            new_view = self.add_ai_web_view_from_config(enabled_platforms[0])
            
            # 将新视图移动到当前视图右侧
            new_container = None
            for i in range(self.splitter.count()):
                widget = self.splitter.widget(i)
                if hasattr(widget, 'web_view') and widget.web_view == new_view:
                    new_container = widget
                    break
            
            if new_container:
                # 移动到当前视图右侧
                current_index = self.splitter.indexOf(new_container)
                if current_index != index + 1:
                    # 记住当前的大小
                    sizes = self.splitter.sizes()
                    
                    # 移除并重新插入
                    self.splitter.insertWidget(index + 1, new_container)
                    
                    # 重新调整大小
                    self.adjust_splitter_sizes()
                    
                    # 更新导航按钮状态
                    self.update_navigation_buttons()
    
    def close_view(self, container):
        """关闭视图
        
        Args:
            container: 包含web_view的容器
        """
        # 获取容器索引
        index = self.splitter.indexOf(container)
        if index == -1:
            return
        
        # 检查视图数量，保证至少保留一个视图
        if self.splitter.count() <= 1:
            return
        
        # 获取AI key，从字典中移除
        if hasattr(container, 'ai_key'):
            ai_key = container.ai_key
            if ai_key in self.ai_web_views:
                del self.ai_web_views[ai_key]
        
        # 从分割器中移除
        container.setParent(None)
        
        # 如果当前是最大化状态，恢复其他视图
        if hasattr(container, 'is_maximized') and container.is_maximized:
            for i in range(self.splitter.count()):
                self.splitter.widget(i).show()
        
        # 调整剩余视图的大小
        self.adjust_splitter_sizes()
        
        # 更新导航按钮状态
        self.update_navigation_buttons()
        
        # 标记为稍后删除
        container.deleteLater()
    
    def update_navigation_buttons(self):
        """更新所有容器的导航按钮状态（左右移动按钮）"""
        count = self.splitter.count()
        
        # 遍历所有容器
        for i in range(count):
            container = self.splitter.widget(i)
            
            # 对于最左侧的容器，隐藏向左按钮
            if hasattr(container, 'move_left_btn'):
                container.move_left_btn.setVisible(i > 0)
            
            # 对于最右侧的容器，隐藏向右按钮
            if hasattr(container, 'move_right_btn'):
                container.move_right_btn.setVisible(i < count - 1)
    
    def open_multiple_urls(self, urls):
        """打开多个URL到不同的AI网页视图
        
        Args:
            urls (list): 要打开的URL列表
        """
        if not urls:
            print("没有URL可以打开")
            return
            
        print(f"AI视图收到打开URLs请求: {urls}")
        
        # 清空现有视图
        for i in range(self.splitter.count()):
            widget = self.splitter.widget(0)
            widget.setParent(None)
        
        self.ai_web_views.clear()
        
        # 为每个URL创建一个新的网页视图
        for url in urls:
            # 从URL分析AI平台
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            if domain.startswith('www.'):
                domain = domain[4:]
                
            # URL到平台标识的映射
            url_to_platform = {
                'chat.openai.com': 'chatgpt',
                'chatgpt.com': 'chatgpt',
                'kimi.moonshot.cn': 'kimi',
                'doubao.com': 'doubao',
                'perplexity.ai': 'perplexity',
                'n.cn': 'n',
                'metaso.cn': 'metaso',
                'chatglm.cn': 'chatglm',
                'yuanbao.tencent.com': 'yuanbao',
                'biji.com': 'biji',
                'x.com': 'grok',
                'grok.com': 'grok',
                'yiyan.baidu.com': 'yiyan',
                'tongyi.aliyun.com': 'tongyi',
                'gemini.google.com': 'gemini',
                'chat.deepseek.com': 'deepseek',
                'claude.ai': 'claude',
                'anthropic.com': 'claude',
                'bing.com': 'bing'
            }
            
            # 根据域名获取平台标识
            ai_key = url_to_platform.get(domain)
            
            # 如果找不到精确匹配，尝试部分匹配
            if not ai_key:
                for host, key in url_to_platform.items():
                    if host in domain:
                        ai_key = key
                        break
            
            # 如果无法识别平台，使用通用配置
            if not ai_key:
                ai_key = "unknown"
                ai_name = "未知平台"
            else:
                # 查找匹配的AI平台配置
                ai_name = None
                for key, config in SUPPORTED_AI_PLATFORMS.items():
                    if config["key"] == ai_key:
                        ai_name = config["name"]
                        break
                
                if not ai_name:
                    ai_name = ai_key.capitalize()  # 如果找不到名称，使用key的首字母大写形式
            
            # 创建配置
            ai_config = {
                "key": ai_key,
                "name": ai_name,
                "url": url,
                "input_selector": "",  # 不需要输入选择器，只是查看
                "submit_selector": "",
                "response_selector": ""
            }
            
            # 添加网页视图
            self.add_ai_web_view_from_config(ai_config)
        
        # 调整视图大小
        self.adjust_splitter_sizes() 

    # 新增方法：设置容器按钮的初始图标和颜色
    def _set_initial_button_icons(self, container):
        if not self.theme_manager:
            print("警告: ThemeManager 未初始化，无法设置按钮图标颜色")
            # 可以设置一个默认颜色或无颜色
            icon_color = '#D8DEE9' # 默认深色前景色
        else:
            theme_colors = self.theme_manager.get_current_theme_colors()
            # 使用前景色作为图标颜色
            icon_color = theme_colors.get('foreground', '#D8DEE9') 
            
        # 检查按钮是否存在并设置图标
        if hasattr(container, 'move_left_btn'):
            container.move_left_btn.setIcon(qta.icon("fa5s.arrow-left", color=icon_color))
        if hasattr(container, 'move_right_btn'):
            container.move_right_btn.setIcon(qta.icon("fa5s.arrow-right", color=icon_color))
        if hasattr(container, 'refresh_btn'):
            container.refresh_btn.setIcon(qta.icon("fa5s.sync", color=icon_color))
        if hasattr(container, 'maximize_btn'):
            # 根据当前状态设置正确的图标
            icon_name = "fa5s.compress" if container.is_maximized else "fa5s.expand"
            container.maximize_btn.setIcon(qta.icon(icon_name, color=icon_color))
        if hasattr(container, 'add_btn'):
            container.add_btn.setIcon(qta.icon("fa5s.plus", color=icon_color))
        if hasattr(container, 'close_btn'):
            container.close_btn.setIcon(qta.icon("fa5s.times", color=icon_color))

    # 新增方法：更新所有容器按钮的图标颜色以响应主题变化
    def _update_all_button_icons(self):
        if not self.theme_manager:
            print("警告: ThemeManager 未初始化，无法更新按钮图标颜色")
            return
        
        print("AIView: 接收到主题变化信号，正在更新按钮图标...")
        theme_colors = self.theme_manager.get_current_theme_colors()
        icon_color = theme_colors.get('foreground', '#D8DEE9') # 获取当前主题的前景色
        print(f"AIView: 当前主题图标颜色: {icon_color}")

        # 遍历分割器中的所有容器
        for i in range(self.splitter.count()):
            container = self.splitter.widget(i)
            if container is None: # 添加检查以防万一
                continue
                
            print(f"AIView: 正在更新容器 {i} 的按钮图标...")
            # 检查按钮是否存在并更新图标颜色
            if hasattr(container, 'move_left_btn'):
                container.move_left_btn.setIcon(qta.icon("fa5s.arrow-left", color=icon_color))
            if hasattr(container, 'move_right_btn'):
                container.move_right_btn.setIcon(qta.icon("fa5s.arrow-right", color=icon_color))
            if hasattr(container, 'refresh_btn'):
                container.refresh_btn.setIcon(qta.icon("fa5s.sync", color=icon_color))
            if hasattr(container, 'maximize_btn'):
                icon_name = "fa5s.compress" if container.is_maximized else "fa5s.expand"
                container.maximize_btn.setIcon(qta.icon(icon_name, color=icon_color))
            if hasattr(container, 'add_btn'):
                container.add_btn.setIcon(qta.icon("fa5s.plus", color=icon_color))
            if hasattr(container, 'close_btn'):
                container.close_btn.setIcon(qta.icon("fa5s.times", color=icon_color))
            print(f"AIView: 容器 {i} 图标更新完成。") 