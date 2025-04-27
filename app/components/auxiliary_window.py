#!/usr/bin/env python
# -*- coding: utf-8 -*-

# auxiliary_window.py: 定义 AuxiliaryWindow 类
# 该窗口作为辅助窗口，包含文件浏览器、提示词输入框和提示词历史记录。
# 用于管理和同步提示词到主窗口的 AI 对话页面。

from PyQt6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QPushButton, QVBoxLayout, QLabel, QSplitter, QFrame, QToolBar, QStackedWidget, QTabWidget, QApplication, QMessageBox, QSizePolicy
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QSize, QTimer, QUrl, QSettings
from PyQt6.QtGui import QIcon
import qtawesome as qta
import os
from datetime import datetime
import sqlite3
import http.server
import socketserver
import threading
import re
from app.controllers.theme_manager import ThemeManager # 导入ThemeManager
from app.components.shortcut_settings_dialog import ShortcutSettingsDialog

# 添加全局变量用于存储auxiliary_window引用
GLOBAL_AUXILIARY_WINDOW = None

from app.components.file_explorer import FileExplorer
from app.components.prompt_input import PromptInput
from app.components.prompt_history import PromptHistory
from app.components.file_viewer import FileViewer  # 导入文件查看器组件
from app.controllers.prompt_sync import PromptSync
from app.components.web_view import WebView  # 导入WebView组件

# 在CustomHTTPHandler类上方添加
_auxiliary_window_ref = None  # 类级别的引用

class RibbonToolBar(QToolBar):
    """垂直工具栏，类似Obsidian的ribbon"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setOrientation(Qt.Orientation.Vertical)
        self.setMovable(False)
        self.setIconSize(QSize(22, 22))
        self.setObjectName("ribbonToolBar")
        
        # 移除样式表
        # self.setStyleSheet(\"\"\" ... \"\"\")

class PanelWidget(QWidget):
    """面板组件，包含标题和内容区域"""
    
    def __init__(self, title, content_widget, window=None, is_control_panel=False, custom_titlebar=None):
        super().__init__()
        self.window = window
        self.is_control_panel = is_control_panel
        
        # 创建垂直布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        if custom_titlebar:
            # 使用自定义标题栏
            self.title_bar = custom_titlebar
        else:
            # 创建标题区域
            self.title_bar = QWidget()
            self.title_bar.setFixedHeight(30)
            self.title_bar.setObjectName("panelTitleBar")
            title_layout = QHBoxLayout(self.title_bar)
            title_layout.setContentsMargins(8, 0, 8, 0)
            
            # 创建标题标签
            title_label = QLabel(title)
            # 移除样式表
            # title_label.setStyleSheet("color: #D8DEE9; font-weight: bold;") 
            
            # 添加标题到布局
            title_layout.addWidget(title_label)
        
        # 如果是控制面板，添加窗口控制按钮
        if is_control_panel and window:
            # 获取标题栏的布局
            if not hasattr(self.title_bar, 'layout'):
                # 如果没有布局（自定义标题栏可能已有布局），创建一个
                title_layout = QHBoxLayout(self.title_bar)
                title_layout.setContentsMargins(8, 0, 8, 0)
            else:
                title_layout = self.title_bar.layout()
            
            # 添加伸缩空间
            title_layout.addStretch(1)
            
            # 创建窗口控制按钮
            # 最小化按钮
            minimize_button = QPushButton()
            minimize_button.setIcon(qta.icon('fa5s.window-minimize'))
            minimize_button.clicked.connect(window.showMinimized)
            minimize_button.setObjectName("minimizeButton")
            
            # 最大化/还原按钮
            maximize_button = QPushButton()
            maximize_button.setIcon(qta.icon('fa5s.window-maximize'))
            maximize_button.clicked.connect(window.toggle_maximize)
            maximize_button.setObjectName("maximizeButton")
            
            # 关闭按钮
            close_button = QPushButton()
            close_button.setIcon(qta.icon('fa5s.times'))
            close_button.clicked.connect(window.close)
            close_button.setObjectName("closeButton")
            
            # 添加按钮到标题栏
            title_layout.addWidget(minimize_button)
            title_layout.addWidget(maximize_button)
            title_layout.addWidget(close_button)
            
            # 保存按钮引用便于后续访问
            window.minimize_button = minimize_button
            window.maximize_button = maximize_button
            window.close_button = close_button


        
        # 创建分隔线（设置为非常细的线条）
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Plain)
        separator.setLineWidth(0)
        separator.setMidLineWidth(0)  # 将中线宽度设为0以获得更细的线条
        separator.setFixedHeight(1)  # 将高度固定为1px
        # 移除样式表
        # separator.setStyleSheet("background-color: #3B4252;")
        
        # 添加标题栏和分隔线到主布局
        layout.addWidget(self.title_bar)
        layout.addWidget(separator)
        
        # 添加内容区域
        layout.addWidget(content_widget, 1)  # 使内容区域拉伸填充
        
        # 移除样式表
        # self.title_bar.setStyleSheet(\"\"\" ... \"\"\")
        
        # 标记标题栏用于拖动窗口
        self.title_bar.installEventFilter(self)
    
    def eventFilter(self, obj, event):
        """事件过滤器，用于处理标题栏的鼠标事件"""
        if obj == self.title_bar:
            # 标题栏鼠标按下事件，用于拖动窗口
            if event.type() == event.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                if self.window:
                    self.window._drag_pos = event.globalPosition().toPoint()
                
            # 双击标题栏，触发窗口最大化/还原
            elif event.type() == event.Type.MouseButtonDblClick and event.button() == Qt.MouseButton.LeftButton:
                if self.window:
                    self.window.toggle_maximize()
                    return True
        
        return super().eventFilter(obj, event)

class AuxiliaryWindow(QMainWindow):
    """辅助窗口类 - 包含文件浏览、提示词输入和历史记录"""
    
    # 信号：请求打开主窗口
    request_open_main_window = pyqtSignal()
    
    # 新增信号：用于从HTTP线程传递提示词到主线程
    received_prompt_from_http = pyqtSignal(str)
    
    def __init__(self, db_manager):
        super().__init__()
        self.setWindowTitle("AiSparkHub - 提示词管理")
        self.setMinimumSize(1000, 300)
        
        # 设置无边框窗口
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        
        # 设置全局引用，确保HTTP处理器能访问到
        global GLOBAL_AUXILIARY_WINDOW
        GLOBAL_AUXILIARY_WINDOW = self
        print("已设置全局辅助窗口引用")
        
        # 设置图标 (虽然无边框，但任务栏可能需要)
        self.setWindowIcon(qta.icon('fa5s.keyboard', color='#88C0D0'))
        
        # 创建主容器和主水平布局
        main_container = QWidget()
        self.main_layout = QHBoxLayout(main_container)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # 创建左侧垂直工具栏（Ribbon）
        self.ribbon = RibbonToolBar()
        self.main_layout.addWidget(self.ribbon)
        
        # 添加"打开主窗口"按钮
        self.open_main_window_action = self.ribbon.addAction(qta.icon('fa5s.window-maximize'), "打开主窗口")
        self.open_main_window_action.triggered.connect(self.on_open_main_window)
        
        # 添加显示模式切换按钮
        self.display_mode_action = self.ribbon.addAction(qta.icon('fa5s.desktop'), "显示模式切换")
        self.display_mode_action.triggered.connect(self.toggle_display_mode)
        self.display_mode_action.setToolTip("在不同显示模式之间切换")

        # 添加快捷键设置按钮
        self.shortcut_settings_action = self.ribbon.addAction(qta.icon('fa5s.keyboard'), "快捷键设置")
        self.shortcut_settings_action.triggered.connect(self.open_shortcut_settings)
        self.shortcut_settings_action.setToolTip("自定义全局快捷键")
        
        # 内容区域垂直布局容器
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # 创建分割器
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        # 移除样式表
        # self.splitter.setStyleSheet(\"\"\" ... \"\"\")
        
        # 初始化组件
        self.db_manager = db_manager
        
        # 启动本地HTTP服务器（先启动服务器）
        self.start_local_server()
        
        # 初始化UI组件
        self.init_components()
        
        # 将分割器添加到内容布局
        content_layout.addWidget(self.splitter, 1)
        
        # 将内容容器添加到主布局
        self.main_layout.addWidget(content_container, 1)
        
        # 设置主容器为中央部件
        self.setCentralWidget(main_container)
        
        # 用于窗口拖动
        self._drag_pos = None
        
        # 创建同步控制器
        self.prompt_sync = PromptSync()
        # 设置数据库管理器
        self.prompt_sync.set_db_manager(self.db_manager)
        
        # 连接响应收集信号
        self.prompt_sync.response_collected.connect(self.on_response_collected)
        
        # 连接历史记录的总结AI回复请求信号
        self.prompt_history.request_summarize_responses.connect(self.on_request_summarize_responses)
        
        # 连接HTTP提示词接收信号到处理槽函数
        self.received_prompt_from_http.connect(self.on_received_prompt_from_http)
        
        # 获取 ThemeManager 并连接信号
        self.theme_manager = None
        app = QApplication.instance()
        if hasattr(app, 'theme_manager') and isinstance(app.theme_manager, ThemeManager):
            self.theme_manager = app.theme_manager
            self.theme_manager.theme_changed.connect(self._update_aux_window_icons)
            # 设置初始图标颜色 (需要在UI元素创建后调用)
            # QTimer.singleShot(0, self._update_aux_window_icons)
        else:
            print("警告：无法在 AuxiliaryWindow 中获取 ThemeManager 实例")
            
        # 使用定时器延迟加载搜索页面（确保服务器已启动）
        QTimer.singleShot(500, self.load_search_page)
        # 在 __init__ 末尾调用一次图标更新，确保初始状态正确
        QTimer.singleShot(0, self._update_aux_window_icons)
        
        # 加载存储的分割器位置
        QTimer.singleShot(300, self.load_splitter_sizes)
        
        # 监听分割器位置变化并保存
        self.splitter.splitterMoved.connect(self.save_splitter_sizes)
    
    def start_local_server(self):
        """启动本地HTTP服务器，以便加载本地HTML文件"""
        # 确定搜索页面所在目录
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        server_dir = os.path.join(current_dir, "search")
        if not os.path.exists(server_dir):
            os.makedirs(server_dir, exist_ok=True)
            
        # 确保index.html存在于搜索目录
        index_path = os.path.join(server_dir, "index.html")
        if not os.path.exists(index_path):
            # 如果搜索目录中不存在index.html，尝试从项目根目录复制
            app_dir = os.path.dirname(current_dir)
            src_index_path = os.path.join(app_dir, "app", "search", "index.html")
            if os.path.exists(src_index_path):
                import shutil
                try:
                    shutil.copy2(src_index_path, index_path)
                    print(f"已复制index.html到搜索目录: {index_path}")
                except Exception as e:
                    print(f"复制index.html时出错: {e}")
                    
        # 设置服务器目录
        os.chdir(server_dir)
        
        # 创建自定义的HTTP处理器，添加API支持
        class CustomHTTPHandler(http.server.SimpleHTTPRequestHandler):
            """自定义HTTP处理器，支持API请求处理"""
            
            def __init__(self, *args, **kwargs):
                # 存储对辅助窗口的引用，以便访问prompt_sync
                self.auxiliary_window = None
                super().__init__(*args, **kwargs)
            
            def do_POST(self):
                """处理POST请求"""
                # 处理提示词API
                if self.path == '/api/prompt':
                    content_length = int(self.headers['Content-Length'])
                    post_data = self.rfile.read(content_length)
                    
                    try:
                        # 解析JSON数据
                        import json
                        import traceback
                        print("\n" + "="*80)
                        print("【接收到网页提示词请求】")
                        print(f"收到原始POST数据: {post_data[:100]}...")
                        
                        try:
                            data = json.loads(post_data.decode('utf-8'))
                            print(f"解析JSON成功: {json.dumps(data, ensure_ascii=False)[:100]}...")
                        except Exception as json_err:
                            print(f"JSON解析错误: {str(json_err)}")
                            raise Exception(f"JSON解析失败: {str(json_err)}")
                            
                        prompt = data.get('prompt', '')
                        if not prompt:
                            print("警告: 提示词为空")
                        
                        # 输出完整提示词到控制台，分段显示以提高可读性
                        print("\n【完整提示词内容】")
                        print("-"*40)
                        # 将提示词分成多行输出，每行最多200个字符
                        for i in range(0, len(prompt), 200):
                            print(prompt[i:i+200])
                        print("-"*40)
                        
                        # 验证auxiliary_window引用
                        if not self.auxiliary_window:
                            print("警告: 实例级auxiliary_window引用不存在，尝试使用全局引用")
                            # 使用全局引用代替
                            global GLOBAL_AUXILIARY_WINDOW
                            self.auxiliary_window = GLOBAL_AUXILIARY_WINDOW
                            
                            if not self.auxiliary_window:
                                print("错误: 全局auxiliary_window引用也不存在")
                                raise Exception("服务器内部错误: auxiliary_window不可用")
                        
                        # 清理特殊字符并截断提示词到1000字符
                        original_length = len(prompt)
                        
                        # 清理特殊字符 - 先执行基本清理
                        cleaned_prompt = prompt
                        # 替换可能导致JavaScript错误的字符
                        cleaned_prompt = re.sub(r'[\\\'"]', ' ', cleaned_prompt)  # 移除引号和反斜杠
                        
                        # 截断到1000字符
                        if len(cleaned_prompt) > 1000:
                            truncated_prompt = cleaned_prompt[:1000]
                            print(f"\n【清理并截断提示词】原始长度: {original_length}字符，清理后长度: {len(cleaned_prompt)}字符，截断到1000字符")
                        else:
                            truncated_prompt = cleaned_prompt
                            print(f"\n【清理提示词】原始长度: {original_length}字符，清理后长度: {len(cleaned_prompt)}字符，无需截断")
                        
                        # 添加截断提示
                        if len(truncated_prompt) < len(prompt):
                            truncated_prompt += "\n\n[内容已截断，完整内容太长无法显示]"
                        
                        print("处理后内容前100字符:", truncated_prompt[:100])
                        
                        # 使用信号将完整提示词传递到主线程处理
                        print("\n【使用信号发送提示词到主线程】")
                        try:
                            # 获取原始完整提示词(未清理、未截断)
                            original_prompt = prompt  # 使用原始提示词，不是清理或截断的版本
                            
                            # 检查辅助窗口引用
                            if self.auxiliary_window:
                                # 使用信号发送提示词到主线程处理
                                print(f"发送提示词到主线程，长度: {len(original_prompt)}字符")
                                self.auxiliary_window.received_prompt_from_http.emit(original_prompt)
                                print("信号发送成功")
                            else:
                                print("错误: 无法发送信号，auxiliary_window引用不存在")
                        except Exception as e:
                            print(f"发送信号到主线程失败: {str(e)}")
                            print(traceback.format_exc())
                            
                        # 返回成功响应
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')  # 允许跨域
                        self.end_headers()
                        response = {'status': 'success', 'message': '提示词已成功发送到AI视图'}
                        self.wfile.write(json.dumps(response).encode('utf-8'))
                        print("HTTP响应: 200 成功")
                        print("="*80 + "\n")
                    except Exception as e:
                        # 详细记录错误
                        print(f"处理/api/prompt请求出错: {str(e)}")
                        print(traceback.format_exc())
                        
                        # 返回错误响应
                        self.send_response(500)  # 改为500错误以反映服务器问题
                        self.send_header('Content-type', 'application/json')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.end_headers()
                        error_detail = str(e)
                        response = {
                            'status': 'error', 
                            'message': f'处理提示词请求失败: {error_detail}'
                        }
                        self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))
                        print("HTTP响应: 500 错误")
                        print("="*80 + "\n")

            def do_GET(self):
                """处理GET请求"""
                # 处理URL参数方式的提示词API
                if self.path.startswith('/api/prompt-url'):
                    try:
                        # 解析URL参数
                        from urllib.parse import urlparse, parse_qs
                        query = parse_qs(urlparse(self.path).query)
                        prompt = query.get('prompt', [''])[0]
                        
                        if prompt:
                            print(f"收到URL参数提示词请求: {prompt[:50]}...")
                            
                            # 转发到prompt_sync
                            if self.auxiliary_window and hasattr(self.auxiliary_window, 'prompt_sync'):
                                self.auxiliary_window.prompt_sync.sync_prompt(prompt)
                                
                                # 返回成功响应
                                self.send_response(200)
                                self.send_header('Content-type', 'text/html; charset=utf-8')
                                self.end_headers()
                                response = """
                                <html>
                                <head>
                                <title>Prompt Sent</title>
                                <meta charset="utf-8">
                                </head>
                                <body>
                                <h1>Prompt has been sent to AI assistant</h1>
                                <p>You can close this page now.</p>
                                <script>
                                setTimeout(function() {
                                    window.close();
                                }, 2000);
                                </script>
                                </body>
                                </html>
                                """.encode('utf-8')
                                self.wfile.write(response)
                                return
                        
                        # 参数缺失或prompt_sync不可用
                        self.send_response(400)
                        self.send_header('Content-type', 'text/html')
                        self.end_headers()
                        self.wfile.write(b'Bad Request: Missing prompt parameter or prompt_sync not available')
                    except Exception as e:
                        # 返回错误响应
                        self.send_response(500)
                        self.send_header('Content-type', 'text/html')
                        self.end_headers()
                        self.wfile.write(f'Error: {str(e)}'.encode('utf-8'))
                else:
                    # 其他GET请求使用标准处理
                    super().do_GET()

            def do_OPTIONS(self):
                """处理OPTIONS请求，支持CORS"""
                self.send_response(200)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                self.end_headers()
        
        # 创建自定义处理器并设置对辅助窗口的引用
        handler_class = CustomHTTPHandler
        # 使用闭包传递self引用
        def handler_factory(*args, **kwargs):
            CustomHTTPHandler._auxiliary_window_ref = self  # 设置类级别引用
            handler = handler_class(*args, **kwargs)
            handler.auxiliary_window = self  # 仍然设置实例级别引用
            return handler
        
        # 尝试在8080端口启动服务器，如果被占用则尝试8081
        self.port = 8080
        self.server = None
        
        while self.port < 8090 and not self.server:
            try:
                self.server = socketserver.TCPServer(("", self.port), handler_factory)
                print(f"本地HTTP服务器已启动在端口 {self.port}")
                break
            except OSError:
                print(f"端口 {self.port} 已被占用，尝试下一个端口")
                self.port += 1
                
        if self.server:
            # 在后台线程中启动服务器
            self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.server_thread.start()
        else:
            print("无法启动本地HTTP服务器，所有尝试的端口都被占用")
            
    def init_components(self):
        """初始化窗口组件"""
        # 移除全局滚动条样式表
        # self.setStyleSheet(\"\"\" ... \"\"\")
        
        # 文件浏览器 - 使用文件浏览器作为完整的自包含组件
        self.file_explorer = FileExplorer()
        
        # 创建标签页控件
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        self.tabs.setDocumentMode(True)  # 使标签页更现代化
        
        # 标签页控件增加事件过滤器，用于实现拖拽窗口的功能
        self.tabs.tabBar().installEventFilter(self)
        
        # 监听标签页添加事件，为新标签页设置关闭图标
        self.tabs.tabBarClicked.connect(self._check_tab_close_buttons)
        # 监听标签页添加事件
        self.tabs.currentChanged.connect(self._check_tab_close_buttons)
        
        # 创建提示词输入
        self.prompt_input = PromptInput(self)
        # 传递数据库管理器
        self.prompt_input.db_manager = self.db_manager
        
        # 添加提示词标签页（不可关闭）
        prompt_idx = self.tabs.addTab(self.prompt_input, qta.icon('fa5s.keyboard', color='#81A1C1'), "提示词")
        
        # 设置提示词标签页不可关闭
        self.tabs.tabBar().setTabButton(prompt_idx, self.tabs.tabBar().ButtonPosition.RightSide, None)
        
        # 创建搜索视图
        self.search_view = WebView()
        
        # 添加搜索标签页（不可关闭）
        search_idx = self.tabs.addTab(self.search_view, qta.icon('fa5s.search', color='#88C0D0'), "搜索")
        
        # 设置搜索标签页不可关闭
        self.tabs.tabBar().setTabButton(search_idx, self.tabs.tabBar().ButtonPosition.RightSide, None)
        
        # 创建中间面板容器
        middle_container = QWidget()
        
        # 只设置一个垂直布局，不使用PanelWidget
        middle_layout = QVBoxLayout(middle_container)
        middle_layout.setContentsMargins(0, 0, 0, 0)
        middle_layout.setSpacing(0)
        
        # A将标签页直接添加到布局，它会成为"标题栏"
        middle_layout.addWidget(self.tabs)
        
        # 提示词历史记录
        self.prompt_history = PromptHistory(self.db_manager)
        
        # 创建历史记录容器
        history_container = QWidget()
        history_layout = QVBoxLayout(history_container)
        history_layout.setContentsMargins(0, 0, 0, 0)
        history_layout.setSpacing(0)
        
        # 创建自定义标题栏
        title_bar = QWidget()
        title_bar.setFixedHeight(30)
        title_bar.setObjectName("panelTitleBar")
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(8, 0, 8, 0)
        
        # 创建标签控件和连接
        tab_bar = QTabWidget()
        tab_bar.setObjectName("promptHistoryTabs")
        tab_bar.setTabPosition(QTabWidget.TabPosition.North)
        tab_bar.setDocumentMode(True)  # 使标签页更现代化
        tab_bar.setFixedHeight(28)  # 减小高度，使其更加紧凑
        tab_bar.setStyleSheet("""
            QTabBar::tab {
                min-width: 50px;
                max-width: 70px;
                padding: 4px 6px;
                margin-right: 2px;
                border-top-left-radius: 3px;
                border-top-right-radius: 3px;
            }
            QTabBar::tab:selected {
                background-color: #3B4252;
                border-bottom: 2px solid #81A1C1;
            }
            QTabBar::tab:!selected {
                background-color: #2E3440;
                margin-top: 2px;
            }
        """)  # 设置标签页样式，限制宽度
        tab_bar.tabBar().setExpanding(False)  # 不要扩展标签填充整个宽度
        tab_bar.addTab(QWidget(), "历史")  # 添加空的占位标签
        tab_bar.addTab(QWidget(), "统计")  # 添加空的占位标签
        
        # 标签控件添加到标题栏左侧
        title_layout.addWidget(tab_bar, 1)
        
        # 创建窗口控制按钮
        # 最小化按钮
        minimize_button = QPushButton()
        minimize_button.setIcon(qta.icon('fa5s.window-minimize'))
        minimize_button.clicked.connect(self.showMinimized)
        minimize_button.setObjectName("minimizeButton")
        minimize_button.setFixedSize(24, 24)
        
        # 最大化/还原按钮
        maximize_button = QPushButton()
        maximize_button.setIcon(qta.icon('fa5s.window-maximize'))
        maximize_button.clicked.connect(self.toggle_maximize)
        maximize_button.setObjectName("maximizeButton")
        maximize_button.setFixedSize(24, 24)
        
        # 关闭按钮
        close_button = QPushButton()
        close_button.setIcon(qta.icon('fa5s.times'))
        close_button.clicked.connect(self.close)
        close_button.setObjectName("closeButton")
        close_button.setFixedSize(24, 24)
        
        # 添加按钮到标题栏右侧
        title_layout.addWidget(minimize_button)
        title_layout.addWidget(maximize_button)
        title_layout.addWidget(close_button)
        
        # 保存按钮引用便于后续访问
        self.minimize_button = minimize_button
        self.maximize_button = maximize_button
        self.close_button = close_button
        self.history_tab_bar = tab_bar
        
        # 标记标题栏用于拖动窗口
        title_bar.installEventFilter(self)
        
        # 添加标题栏
        history_layout.addWidget(title_bar)
        
        # 直接添加PromptHistory到布局中（保留完整功能）
        history_layout.addWidget(self.prompt_history, 1)
        
        # 添加面板到分割器
        self.splitter.addWidget(self.file_explorer)
        self.splitter.addWidget(middle_container)
        self.splitter.addWidget(history_container)
        
        # 设置初始比例 (3:4:3)
        self.splitter.setSizes([300, 400, 300])
        
        # 添加主题切换按钮到ribbon条最底部
        # QToolBar不支持addStretch，添加一个QWidget作为空间填充
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self.ribbon.addWidget(spacer)  # 添加占位组件，将后续控件推到底部
        
        # 创建主题切换按钮
        self.theme_button = QPushButton()
        self.theme_button.setIcon(qta.icon('fa5s.moon'))  # 深色模式默认显示月亮图标
        self.theme_button.setToolTip("切换明暗主题")
        self.theme_button.clicked.connect(self.toggle_theme)
        self.theme_button.setObjectName("themeButton")
        
        # 添加主题切换按钮到ribbon
        self.ribbon.addWidget(self.theme_button)
        
        # 连接信号
        self.prompt_input.prompt_submitted.connect(self.on_prompt_submitted)
        
        # 连接历史记录的选择信号
        self.prompt_history.prompt_selected.connect(self.prompt_input.set_text)
        
        # 连接历史记录的收藏切换信号
        self.prompt_history.favorite_toggled.connect(self.on_favorite_toggled)
        
        # 连接文件浏览器的fileOpenRequest信号到打开文件方法
        self.file_explorer.fileOpenRequest.connect(self.open_file)
        
        # 连接历史记录的open_urls信号到处理方法
        self.prompt_history.open_urls.connect(self.on_open_urls)
        
        # 连接历史记录的提示词设置请求信号
        self.prompt_history.request_set_prompt.connect(self.on_request_set_prompt)
        
        # 连接历史记录的提示词直接发送请求信号
        self.prompt_history.request_send_prompt.connect(self.on_request_send_prompt)
        
        # 连接标签切换信号 - 相互同步
        tab_bar.currentChanged.connect(lambda index: self.sync_tab_selection(tab_bar, self.prompt_history.tab_widget, index))
        
        # 监听PromptHistory的标签变化
        self.prompt_history.tab_widget.currentChanged.connect(lambda index: self.sync_tab_selection(self.prompt_history.tab_widget, tab_bar, index))
        
        # 隐藏PromptHistory内部的选项卡，只显示自定义选项卡
        self.prompt_history.tab_widget.tabBar().hide()
    
    def load_search_page(self):
        """加载搜索页面"""
        # 检查HTTP服务器是否已启动
        if not hasattr(self, 'port') or not self.server:
            print("HTTP服务器未启动，无法加载搜索页面")
            return
            
        # 加载本地搜索页面
        self.search_view.web_view.load(QUrl(f"http://localhost:{self.port}/index.html"))
        print(f"正在加载本地搜索页面: http://localhost:{self.port}/index.html")

    def on_prompt_submitted(self, prompt_text):
        """处理提示词提交
        
        Args:
            prompt_text (str): 提示词文本
        """
        # 检查提示词是否为空
        if not prompt_text or prompt_text.strip() == "":
            return
            
        print(f"发送提示词: {prompt_text[:30]}...")
        
        # 直接同步提示词到主窗口的AI网页
        # prompt_sync.sync_prompt会处理存储到prompt_details表
        self.prompt_sync.sync_prompt(prompt_text)
        
        # 刷新历史记录
        self.prompt_history.refresh_history()
        
        # 不再清空输入框
        # self.prompt_input.clear()
    
    def on_open_main_window(self):
        """处理打开主窗口的请求"""
        # 发射信号通知应用程序打开主窗口
        self.request_open_main_window.emit()
    
    def closeEvent(self, event):
        """处理窗口关闭事件"""
        # 保存分割器位置
        self.save_splitter_sizes()
        
        # 关闭HTTP服务器
        if hasattr(self, 'server') and self.server:
            try:
                print("正在关闭本地HTTP服务器...")
                
                # 使用一个线程安全地关闭服务器，避免阻塞主线程
                def shutdown_server_thread():
                    try:
                        if self.server:
                            # 关闭服务器
                            self.server.shutdown()
                            print("HTTP服务器已关闭")
                            
                            # 确保套接字也被关闭
                            if hasattr(self.server, 'socket'):
                                self.server.socket.close()
                                print("服务器套接字已关闭")
                                
                            # 清空服务器引用
                            self.server = None
                    except Exception as e:
                        print(f"关闭HTTP服务器时出错: {e}")
                
                # 创建并启动关闭线程
                shutdown_thread = threading.Thread(target=shutdown_server_thread, name="ServerShutdownThread")
                shutdown_thread.daemon = True
                shutdown_thread.start()
                
                # 等待线程最多0.5秒，这个时间通常足够关闭服务器
                # 但又不至于让用户感觉到明显延迟
                shutdown_thread.join(timeout=0.5)
                
                # 无论线程是否完成，继续关闭窗口
                if shutdown_thread.is_alive():
                    print("服务器可能仍在关闭中，但继续执行窗口关闭流程")
                else:
                    print("服务器已成功关闭")
                
            except Exception as e:
                print(f"处理服务器关闭时出错: {e}")
        
        # 正常关闭窗口
        super().closeEvent(event)

    # --- 窗口控制方法 ---
    def toggle_maximize(self):
        """切换窗口最大化状态"""
        if self.isMaximized():
            self.showNormal()
            self.maximize_button.setIcon(qta.icon('fa5s.window-maximize'))
        else:
            self.showMaximized()
            self.maximize_button.setIcon(qta.icon('fa5s.window-restore'))

    def mouseMoveEvent(self, event):
        """处理鼠标移动事件，用于窗口拖动"""
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos is not None:
            diff = event.globalPosition().toPoint() - self._drag_pos
            self.move(self.pos() + diff)
            self._drag_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        """处理鼠标释放事件"""
        self._drag_pos = None

    def open_file(self, file_path, file_type):
        """在新标签页中打开文件
        
        Args:
            file_path (str): 文件路径
            file_type (str): 文件类型（可带":edit"后缀来指定编辑模式）
        """
        # 获取文件名
        file_name = os.path.basename(file_path)
        
        # 检查是否请求编辑模式
        edit_mode = False
        if ":" in file_type:
            file_type, mode = file_type.split(":", 1)
            edit_mode = (mode == "edit")
        
        # 检查文件是否已经打开
        for i in range(self.tabs.count()):
            if self.tabs.tabText(i) == file_name:
                # 如果已打开，切换到对应标签
                self.tabs.setCurrentIndex(i)
                
                # 如果请求编辑模式，尝试在已打开的标签中切换到编辑模式
                if edit_mode and file_type == 'markdown':
                    file_viewer = self.tabs.widget(i)
                    if hasattr(file_viewer, '_toggle_edit_mode'):
                        file_viewer._toggle_edit_mode()
                
                return
        
        # 创建文件查看器
        file_viewer = FileViewer()
        
        # 打开文件
        file_viewer.open_file(file_path, file_type)
        
        # 如果是可编辑文件类型且请求编辑模式，直接切换到编辑模式
        if edit_mode and file_type == 'markdown' and hasattr(file_viewer, '_toggle_edit_mode'):
            file_viewer._toggle_edit_mode()
        
        # 连接文件内容复制到提示词的信号
        file_viewer.file_content_to_prompt.connect(self.on_file_content_to_prompt)
        
        # 添加到标签页
        file_icon = self._get_file_icon(file_type)
        idx = self.tabs.addTab(file_viewer, file_icon, file_name)
        
        # 设置文件路径作为工具提示
        self.tabs.setTabToolTip(idx, file_path)
        
        # 切换到新标签页
        self.tabs.setCurrentIndex(idx)
    
    def close_tab(self, index):
        """关闭标签页
        
        Args:
            index (int): 标签页索引
        """
        # 不关闭提示词标签页（索引0）
        if index == 0:
            return
            
        # 关闭标签页
        self.tabs.removeTab(index)
    
    def _get_file_icon(self, file_type, icon_color='#D8DEE9'):
        """根据文件类型获取图标
        
        Args:
            file_type (str): 文件类型
            
        Returns:
            QIcon: 文件图标
        """
        icons = {
            'html': qta.icon('fa5s.file-code', color=icon_color),
            'markdown': qta.icon('fa5s.file-alt', color=icon_color),
            'text': qta.icon('fa5s.file-alt', color=icon_color),
            'docx': qta.icon('fa5s.file-word', color=icon_color),
            'powerpoint': qta.icon('fa5s.file-powerpoint', color=icon_color),
            'excel': qta.icon('fa5s.file-excel', color=icon_color),
            'pdf': qta.icon('fa5s.file-pdf', color=icon_color)
        }
        
        default_color = icon_color # 默认颜色使用传入的颜色
        color = icons.get(file_type, default_color)
        
        return icons.get(file_type, qta.icon('fa5s.file', color=default_color))

    def on_file_content_to_prompt(self, content):
        """处理文件内容复制到提示词
        
        Args:
            content (str): 文件内容
        """
        # 设置提示词输入的内容
        self.prompt_input.set_text(content)
        
        # 切换到提示词标签页
        self.tabs.setCurrentIndex(0)

    def eventFilter(self, obj, event):
        """事件过滤器，处理标签栏的拖拽和双击事件"""
        try:
            # 如果是标签栏的事件
            if hasattr(self, 'tabs') and self.tabs and obj == self.tabs.tabBar():
                # 处理鼠标按下事件，用于拖动窗口
                if event.type() == event.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                    self._drag_pos = event.globalPosition().toPoint()
                    return False  # 继续处理事件
                    
                # 处理鼠标移动事件，实现拖动
                elif event.type() == event.Type.MouseMove and event.buttons() & Qt.MouseButton.LeftButton and self._drag_pos is not None:
                    diff = event.globalPosition().toPoint() - self._drag_pos
                    self.move(self.pos() + diff)
                    self._drag_pos = event.globalPosition().toPoint()
                    return True  # 事件已处理
                    
                # 处理鼠标释放事件
                elif event.type() == event.Type.MouseButtonRelease:
                    self._drag_pos = None
                    
                # 处理双击事件，实现最大化/还原
                elif event.type() == event.Type.MouseButtonDblClick and event.button() == Qt.MouseButton.LeftButton:
                    self.toggle_maximize()
                    return True  # 事件已处理
        except RuntimeError as e:
            # 捕获C++对象已删除异常
            print(f"事件过滤器错误: {e}")
            return False
        
        # 调用父类的事件过滤器
        return super().eventFilter(obj, event)

    def _check_tab_close_buttons(self, index):
        """检查并设置标签页关闭按钮图标"""
        try:
            # 为标签页设置qtawesome图标
            close_icon = qta.icon('fa5s.times', color='#D8DEE9')
            
            # 遍历所有标签页，检查是否有未设置图标的关闭按钮
            for i in range(self.tabs.count()):
                close_button = self.tabs.tabBar().tabButton(i, self.tabs.tabBar().ButtonPosition.RightSide)
                if close_button and close_button.icon().isNull():
                    # 使用当前主题颜色
                    icon_color = '#D8DEE9' # Default
                    if self.theme_manager:
                        theme_colors = self.theme_manager.get_current_theme_colors()
                        icon_color = theme_colors.get('foreground', icon_color)
                    close_icon = qta.icon('fa5s.times', color=icon_color)
                    
                    close_button.setIcon(close_icon)
                    close_button.setText("")  # 移除文本，只显示图标
                    close_button.setIconSize(QSize(12, 12))  # 设置合适的图标大小
        except (RuntimeError, AttributeError) as e:
            # 捕获可能的运行时错误
            print(f"设置标签页关闭按钮时出错: {e}")

    def on_response_collected(self, prompt_id, responses):
        """处理收集到的AI回复
        
        Args:
            prompt_id (str): 提示词ID
            responses (list): 响应信息列表
        """
        print(f"收集到AI回复，ID: {prompt_id}, 共{len(responses)}个回复")
        # 收集完成后，刷新历史记录区域
        self.prompt_history.refresh_history()

    def on_favorite_toggled(self, prompt_id, is_favorite):
        """处理提示词收藏状态切换
        
        Args:
            prompt_id (str): 提示词ID
            is_favorite (bool): 新的收藏状态
        """
        # 可以在这里添加额外的操作，如通知或UI更新
        favorite_status = "收藏" if is_favorite else "取消收藏"
        print(f"提示词 {prompt_id} 已{favorite_status}") 

    def on_open_urls(self, urls):
        """处理打开多个URL的请求
        
        Args:
            urls (list): 要打开的URL列表
        """
        if not urls:
            print("没有URL可以打开")
            return
            
        print(f"辅助窗口收到打开URLs请求: {urls}")
        
        # 获取主窗口
        main_window = None
        for window in QApplication.topLevelWidgets():
            if window.__class__.__name__ == "MainWindow":
                main_window = window
                break
                
        if not main_window:
            print("找不到主窗口，无法打开URLs")
            return
            
        # 获取主窗口中的AI视图
        ai_view = main_window.get_ai_view()
        if not ai_view:
            print("找不到AI视图，无法打开URLs")
            return
            
        # 如果窗口没有显示，则显示它，但不要改变其位置和大小
        if not main_window.isVisible():
            main_window.show()
            main_window.activateWindow()
        elif main_window.isMinimized():
            # 如果窗口最小化了，只恢复它，不要最大化
            main_window.showNormal()
            main_window.activateWindow()
        else:
            # 窗口已经可见，只需要激活它
            main_window.activateWindow()
            
        # 请求AI视图打开所有URL
        ai_view.open_multiple_urls(urls) 

    def on_request_set_prompt(self, prompt_text):
        """处理设置提示词内容的请求
        
        Args:
            prompt_text (str): 要设置的提示词文本
        """
        # 检查当前提示词输入区是否有内容
        current_text = self.prompt_input.get_text()
        
        if current_text and current_text.strip():
            # 如果已有内容，弹出确认对话框
            msg_box = QMessageBox()
            msg_box.setWindowTitle("确认替换")
            msg_box.setText("提示词输入区已有内容。")
            msg_box.setInformativeText("是否要用历史记录中的内容替换当前内容？")
            msg_box.setIcon(QMessageBox.Icon.Question)
            msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            msg_box.setDefaultButton(QMessageBox.StandardButton.No)
            
            # 显示对话框并获取用户选择
            response = msg_box.exec()
            
            # 如果用户选择"否"，则不替换
            if response == QMessageBox.StandardButton.No:
                return
        
        # 设置提示词内容
        self.prompt_input.set_text(prompt_text)
        
        # 切换到提示词标签页
        self.tabs.setCurrentIndex(0)

    def on_request_send_prompt(self, prompt_text):
        """处理直接发送提示词的请求
        
        Args:
            prompt_text (str): 要发送的提示词文本
        """
        if not prompt_text or not prompt_text.strip():
            print("提示词为空，不执行发送操作")
            return
            
        print(f"直接发送原始提示词: {prompt_text[:30]}...")
        
        # 使用同步控制器直接发送提示词（复用现有的prompt_sync机制）
        self.prompt_sync.sync_prompt(prompt_text)
        
        # 刷新历史记录区域
        QTimer.singleShot(500, self.prompt_history.refresh_history)

    def on_request_summarize_responses(self, prompt_id):
        """处理总结AI回复的请求
        
        Args:
            prompt_id (str): 提示词ID
        """
        if not prompt_id:
            print("无效的提示词ID，无法总结AI回复")
            return
            
        print(f"\n====== 开始处理总结AI回复请求 ======")
        print(f"提示词ID: {prompt_id}")
        
        try:
            # 从数据库中获取原始提示词和各个平台的回复
            prompt_data = self.get_prompt_with_responses(prompt_id)
            if not prompt_data:
                print(f"找不到ID为 {prompt_id} 的提示词记录或记录获取失败")
                QMessageBox.warning(self, "总结失败", f"无法找到该提示词的记录或无法获取提示词数据")
                return
                
            # 检查是否有平台回复
            if not prompt_data.get('responses') or len(prompt_data['responses']) == 0:
                print(f"提示词ID为 {prompt_id} 的记录没有任何AI平台回复")
                QMessageBox.warning(self, "总结失败", f"该提示词没有任何AI平台的回复内容")
                return
                
            # 构建总结提示词
            summary_prompt = self.build_summary_prompt(prompt_data)
            
            # 显示总结提示词到文本框中
            if summary_prompt:
                print(f"总结提示词构建成功，长度: {len(summary_prompt)}")
                
                # 将总结提示词显示在提示词输入框中
                self.prompt_input.set_text(summary_prompt)
                
                # 切换到提示词标签页
                self.tabs.setCurrentIndex(0)
                
                # 显示提示消息
                QMessageBox.information(self, "总结完成", 
                    "已将总结提示词显示在文本框中，您可以根据需要编辑后手动发送。")
                
                print(f"总结提示词已显示在文本框中")
            else:
                print("无法构建总结提示词，返回值为None")
                QMessageBox.warning(self, "总结失败", "无法构建总结提示词，请检查该提示词是否有AI平台回复")
        except Exception as e:
            print(f"总结AI回复时出错: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self, "总结失败", f"无法总结AI回复: {str(e)}")
        finally:
            print(f"====== 总结AI回复请求处理结束 ======\n")
    
    def get_prompt_with_responses(self, prompt_id):
        """从数据库获取提示词及其所有AI平台回复
        
        Args:
            prompt_id (str): 提示词ID
            
        Returns:
            dict: 包含提示词和回复的数据字典
        """
        try:
            print(f"\n===== 开始从数据库获取提示词及回复 =====")
            print(f"查询提示词ID: {prompt_id}")
            
            # 检查数据库连接
            if not self.db_manager or not self.db_manager.conn:
                print("数据库管理器或连接不可用")
                return None
            
            # 获取sqlite3模块
            import sqlite3
            
            # 最直接的方式：使用数据库管理器自己的connection
            conn = self.db_manager.conn
            # 确保row_factory设置正确
            original_row_factory = conn.row_factory
            conn.row_factory = sqlite3.Row
            
            cursor = conn.cursor()
            
            # 查看数据库表结构
            cursor.execute("PRAGMA table_info(prompt_details)")
            columns = cursor.fetchall()
            column_names = [col['name'] for col in columns]
            print(f"数据库表结构: {column_names}")
            
            # 使用直接的SQL查询获取数据
            query = """
                SELECT 
                    id, prompt, timestamp,
                    ai1_url, ai1_reply,
                    ai2_url, ai2_reply,
                    ai3_url, ai3_reply,
                    ai4_url, ai4_reply,
                    ai5_url, ai5_reply,
                    ai6_url, ai6_reply
                FROM prompt_details 
                WHERE id = ?
            """
            
            cursor.execute(query, (prompt_id,))
            row = cursor.fetchone()
            
            if not row:
                print(f"找不到ID为 {prompt_id} 的提示词记录")
                # 恢复原始工厂方法
                conn.row_factory = original_row_factory
                return None
            
            # 打印行的类型和访问方法
            print(f"查询结果类型: {type(row)}")
            print(f"查询结果是否支持按键访问: {'keys' in dir(row)}")
            print(f"查询结果长度: {len(row)}")
            
            # 构造包含所有平台回复的数据字典
            prompt_data = {
                'id': prompt_id,
                'prompt_text': row['prompt'],
                'timestamp': row['timestamp'],
                'responses': []
            }
            
            # 直接检查ai*_url和ai*_reply字段
            print("\n检查AI平台回复字段内容:")
            for i in range(1, 7):
                url_key = f"ai{i}_url"
                reply_key = f"ai{i}_reply"
                
                url = row[url_key] if url_key in row else None
                reply = row[reply_key] if reply_key in row else None
                
                print(f"AI {i}:")
                print(f"  - URL({url_key}): {url}")
                print(f"  - 回复({reply_key}): {reply and len(reply)}")
                
                if url and reply and reply.strip():
                    preview = reply[:30] + "..." if len(reply) > 30 else reply
                    print(f"  - 回复预览: {preview}")
                    
                    platform = self.extract_platform_from_url(url)
                    prompt_data['responses'].append({
                        'platform': platform,
                        'url': url,
                        'response': reply
                    })
                    print(f"添加平台 {platform} 的回复，长度: {len(reply)}")
            
            # 如果没有找到任何回复，尝试使用索引访问
            if len(prompt_data['responses']) == 0:
                print("\n尝试使用索引访问:")
                
                # 创建列名到索引的映射
                column_indices = {name: i for i, name in enumerate(row.keys())}
                print(f"列名到索引映射: {column_indices}")
                
                for i in range(1, 7):
                    url_key = f"ai{i}_url"
                    reply_key = f"ai{i}_reply"
                    
                    if url_key in column_indices and reply_key in column_indices:
                        url_index = column_indices[url_key]
                        reply_index = column_indices[reply_key]
                        
                        try:
                            url = row[url_index]
                            reply = row[reply_index]
                            
                            print(f"AI {i} (索引方式):")
                            print(f"  - URL({url_key})[{url_index}]: {url}")
                            print(f"  - 回复({reply_key})[{reply_index}]: {reply and len(reply)}")
                            
                            if url and reply and reply.strip():
                                platform = self.extract_platform_from_url(url)
                                prompt_data['responses'].append({
                                    'platform': platform,
                                    'url': url,
                                    'response': reply
                                })
                                print(f"通过索引添加平台 {platform} 的回复，长度: {len(reply)}")
                        except Exception as e:
                            print(f"索引访问失败({url_index}, {reply_index}): {e}")
            
            # 最后的兜底方案：直接查询数据库
            if len(prompt_data['responses']) == 0:
                print("\n尝试使用裸SQL查询:")
                try:
                    # 创建新的独立连接，完全重新查询
                    import os
                    data_dir = os.path.join(os.path.abspath("data"), "database")
                    if not os.path.exists(data_dir):
                        # 尝试其它可能的路径
                        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                        data_dir = os.path.join(base_dir, "data", "database")
                    
                    db_path = os.path.join(data_dir, "prompts.db")
                    if os.path.exists(db_path):
                        print(f"找到数据库文件: {db_path}")
                        temp_conn = sqlite3.connect(db_path)
                        temp_cursor = temp_conn.cursor()
                        
                        # 直接查询
                        temp_cursor.execute("""
                            SELECT 
                                ai1_url, ai1_reply,
                                ai2_url, ai2_reply,
                                ai3_url, ai3_reply,
                                ai4_url, ai4_reply,
                                ai5_url, ai5_reply,
                                ai6_url, ai6_reply
                            FROM prompt_details WHERE id = ?
                        """, (prompt_id,))
                        
                        raw_row = temp_cursor.fetchone()
                        if raw_row:
                            print(f"原始查询返回类型: {type(raw_row)}")
                            print(f"原始查询返回长度: {len(raw_row)}")
                            
                            # 打印原始值，不使用索引
                            for i in range(0, len(raw_row), 2):
                                if i+1 < len(raw_row):
                                    url = raw_row[i]
                                    reply = raw_row[i+1]
                                    print(f"原始查询 字段{i}: URL={url}, 回复长度={reply and len(reply)}")
                                    
                                    if url and reply and reply.strip():
                                        platform = self.extract_platform_from_url(url)
                                        prompt_data['responses'].append({
                                            'platform': platform,
                                            'url': url,
                                            'response': reply
                                        })
                                        print(f"通过原始SQL添加平台 {platform} 的回复，长度: {len(reply)}")
                        
                        temp_conn.close()
                except Exception as e:
                    print(f"裸SQL查询失败: {e}")
            
            # 最后检查响应数量
            print(f"总共找到 {len(prompt_data['responses'])} 个平台的回复")
            if len(prompt_data['responses']) == 0:
                print("警告: 没有找到任何平台的回复!")
                
                # 一个临时的解决方案：添加一个占位符回复，让用户知道有问题
                prompt_data['responses'].append({
                    'platform': '系统消息',
                    'url': '',
                    'response': '无法从数据库中检索到任何AI平台的回复。这可能是因为数据库查询问题、数据格式不匹配或者这条记录没有任何AI回复内容。'
                })
            
            # 恢复原始工厂方法
            conn.row_factory = original_row_factory
            
            print(f"===== 提示词数据获取完成 =====\n")
            return prompt_data
            
        except Exception as e:
            print(f"获取提示词及回复时出错: {e}")
            import traceback
            traceback.print_exc()
            return None
            
    def extract_platform_from_url(self, url):
        """从URL提取平台名称
        
        Args:
            url (str): AI平台的URL
            
        Returns:
            str: 平台名称
        """
        from urllib.parse import urlparse
        
        # URL到平台名称的映射
        url_to_platform = {
            'chat.openai.com': 'ChatGPT',
            'chatgpt.com': 'ChatGPT',
            'kimi.moonshot.cn': 'Kimi',
            'www.doubao.com': 'DouBao',
            'doubao.com': 'DouBao',
            'www.perplexity.ai': 'Perplexity',
            'perplexity.ai': 'Perplexity',
            'n.cn': 'N',
            'metaso.cn': 'MetaSo',
            'www.metaso.cn': 'MetaSo',
            'chatglm.cn': 'ChatGLM',
            'www.chatglm.cn': 'ChatGLM',
            'yuanbao.tencent.com': 'YuanBao',
            'www.biji.com': 'BiJi',
            'biji.com': 'BiJi',
            'x.com': 'Grok',
            'grok.com': 'Grok',
            'www.grok.com': 'Grok',
            'yiyan.baidu.com': 'Yiyan',
            'tongyi.aliyun.com': 'Tongyi',
            'gemini.google.com': 'Gemini',
            'chat.deepseek.com': 'DeepSeek',
            'claude.ai': 'Claude',
            'anthropic.com': 'Claude',
            'bing.com': 'Bing',
            'spark.internxt.com': 'Spark'
        }
        
        try:
            # 提取域名
            domain = urlparse(url).netloc
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # 尝试精确匹配
            if domain in url_to_platform:
                return url_to_platform[domain]
            
            # 尝试部分匹配
            for host, platform in url_to_platform.items():
                if host in domain:
                    return platform
            
            # 如果无法识别，返回域名
            return domain or "未知平台"
        except:
            return "未知平台"
    
    def build_summary_prompt(self, prompt_data):
        """构建用于总结多个AI回复的提示词
        
        Args:
            prompt_data (dict): 包含原始提示词和各平台回复的数据
            
        Returns:
            str: 构建好的总结提示词，如果数据无效则返回None
        """
        if not prompt_data:
            print("构建总结提示词失败：数据为空")
            return None
            
        # 确保'responses'键存在且为列表
        if not isinstance(prompt_data.get('responses'), list):
            print(f"构建总结提示词失败：'responses'不是列表或不存在 ({type(prompt_data.get('responses'))})")
            return None
            
        # 确保至少有一个有效的响应
        valid_responses = [r for r in prompt_data['responses'] 
                          if isinstance(r, dict) and r.get('response') and r.get('platform')]
                          
        if not valid_responses:
            print("构建总结提示词失败：没有有效的响应")
            return None
            
        # 如果只有一个响应，且是系统消息（通常是错误信息），则不生成总结
        if len(valid_responses) == 1 and valid_responses[0].get('platform') == '系统消息':
            print("构建总结提示词失败：只有系统错误消息，没有实际AI回复")
            return None
            
        # 获取原始提示词文本
        original_prompt = prompt_data.get('prompt_text', '')
        if not original_prompt:
            print("构建总结提示词失败：原始提示词为空")
            return None
            
        # 构建总结提示词模板
        summary_prompt = f"""我需要你帮我总结以下几个AI平台对同一个问题的回复，并分析它们的异同点。
        
原始问题是：
{original_prompt}

各平台的回复内容如下：
"""
        
        # 添加各平台回复
        for i, response_data in enumerate(valid_responses, 1):
            platform = response_data.get('platform', f'未知平台{i}')
            response = response_data.get('response', '').strip()
            
            # 如果响应过长，截断它
            max_length = 6000  # 约2000个汉字
            if len(response) > max_length:
                response = response[:max_length] + f"\n...[内容过长，已截断，完整长度{len(response)}字符]"
                
            # 添加到总结提示词
            summary_prompt += f"\n【{platform}的回复】：\n{response}\n"
            
        # 添加总结要求
        summary_prompt += """
请你帮我完成以下任务：
1. 简要总结每个AI平台的回答要点（以要点列表形式）
2. 分析不同平台回答的共同点和差异点
3. 综合所有平台的回复，给出一个最全面、准确的答案
4. 评价哪个平台的回答质量最高，并说明理由

请注意，我需要一个全面但简洁的总结，重点突出有价值的信息和见解。"""

        print(f"总结提示词构建完成，长度: {len(summary_prompt)}")
        return summary_prompt 

    def on_received_prompt_from_http(self, prompt_text):
        """处理从HTTP服务器接收到的提示词
        
        Args:
            prompt_text (str): 从HTTP服务器接收到的提示词文本
        """
        print(f"\n===== 在主线程处理从HTTP接收到的提示词 =====")
        print(f"提示词长度: {len(prompt_text)}字符")
        
        # 在这里，我们已经在主线程中，可以安全地调用on_prompt_submitted或其他UI操作
        if prompt_text and prompt_text.strip():
            print("调用on_prompt_submitted处理提示词...")
            self.on_prompt_submitted(prompt_text)
            print("提示词处理完成")
        else:
            print("提示词为空，不处理")
        
        print(f"===== HTTP提示词处理结束 =====\n")
    
    def load_search_page(self):
        """加载搜索页面"""
        # 检查HTTP服务器是否已启动
        if not hasattr(self, 'port') or not self.server:
            print("HTTP服务器未启动，无法加载搜索页面")
            return
            
        # 加载本地搜索页面
        self.search_view.web_view.load(QUrl(f"http://localhost:{self.port}/index.html"))
        print(f"正在加载本地搜索页面: http://localhost:{self.port}/index.html")

    def toggle_theme(self):
        """切换应用主题"""
        try:
            # 尝试使用window_manager切换主题
            if hasattr(self, 'window_manager') and self.window_manager:
                self.window_manager.toggle_theme()
            # 备用方案：直接使用QApplication实例的theme_manager
            elif hasattr(QApplication.instance(), 'theme_manager'):
                app = QApplication.instance()
                # current_theme = app.theme_manager.current_theme
                # new_theme = "light" if current_theme == "dark" else "dark"
                # app.theme_manager.current_theme = new_theme
                # app.theme_manager.apply_theme(app)
                app.theme_manager.toggle_theme(app) # 直接调用 toggle_theme
                # print(f"已切换主题: {app.theme_manager.current_theme}") # ThemeManager 内部会打印
            else:
                print("无法访问主题管理器")
                
            # 不再需要手动调用，由信号触发
            # self._update_theme_icon()
        except Exception as e:
            print(f"切换主题出错: {e}")
    
    # 新增方法：更新所有辅助窗口相关的图标颜色
    def _update_aux_window_icons(self):
        print("AuxiliaryWindow: 接收到主题变化信号或初始调用，正在更新图标...")
        if not self.theme_manager:
            print("警告: ThemeManager 未初始化，无法更新辅助窗口图标")
            icon_color = '#D8DEE9' # 使用默认深色前景色
            is_dark = True
        else:
            theme_colors = self.theme_manager.get_current_theme_colors()
            icon_color = theme_colors.get('foreground', '#D8DEE9')
            is_dark = self.theme_manager.current_theme == "dark"
            print(f"AuxiliaryWindow: 当前主题图标颜色: {icon_color}")
            
            # 更新标签栏样式适应当前主题
            if hasattr(self, 'history_tab_bar'):
                if is_dark:
                    self.history_tab_bar.setStyleSheet("""
                        QTabBar::tab {
                            min-width: 50px;
                            max-width: 70px;
                            padding: 4px 6px;
                            margin-right: 2px;
                            border-top-left-radius: 3px;
                            border-top-right-radius: 3px;
                        }
                        QTabBar::tab:selected {
                            background-color: #3B4252;
                            border-bottom: 2px solid #81A1C1;
                        }
                        QTabBar::tab:!selected {
                            background-color: #2E3440;
                            margin-top: 2px;
                        }
                    """)
                else:
                    self.history_tab_bar.setStyleSheet("""
                        QTabBar::tab {
                            min-width: 50px;
                            max-width: 70px;
                            padding: 4px 6px;
                            margin-right: 2px;
                            border-top-left-radius: 3px;
                            border-top-right-radius: 3px;
                        }
                        QTabBar::tab:selected {
                            background-color: #E5E9F0;
                            border-bottom: 2px solid #5E81AC;
                        }
                        QTabBar::tab:!selected {
                            background-color: #ECEFF4;
                            margin-top: 2px;
                        }
                    """)

        # 1. 更新 Ribbon 工具栏图标
        if hasattr(self, 'open_main_window_action'):
             self.open_main_window_action.setIcon(qta.icon('fa5s.window-maximize', color=icon_color))
        
        # 更新显示模式切换按钮
        if hasattr(self, 'display_mode_action'):
             self.display_mode_action.setIcon(qta.icon('fa5s.desktop', color=icon_color))
        
        # 更新快捷键设置按钮
        if hasattr(self, 'shortcut_settings_action'):
             self.shortcut_settings_action.setIcon(qta.icon('fa5s.keyboard', color=icon_color))
        
        # 2. 更新主题切换按钮
        if hasattr(self, 'theme_button'):
             is_dark = self.theme_manager.current_theme == "dark" if self.theme_manager else True
             self.theme_button.setIcon(qta.icon('fa5s.moon' if is_dark else 'fa5s.sun', color=icon_color))
             self.theme_button.setToolTip("切换到浅色主题" if is_dark else "切换到深色主题")
             
        # 3. 更新 PanelWidget 中的窗口控制按钮 (最小化, 最大化, 关闭)
        if hasattr(self, 'minimize_button'):
            self.minimize_button.setIcon(qta.icon('fa5s.window-minimize', color=icon_color))
        if hasattr(self, 'maximize_button'):
             # 考虑窗口状态
             icon_name = 'fa5s.window-restore' if self.isMaximized() else 'fa5s.window-maximize'
             self.maximize_button.setIcon(qta.icon(icon_name, color=icon_color))
        if hasattr(self, 'close_button'):
             self.close_button.setIcon(qta.icon('fa5s.times', color=icon_color))
             
        # 4. 更新标签页关闭按钮图标
        # 触发一次检查，让它使用新的颜色
        self._check_tab_close_buttons(-1) # 传入无效索引以检查所有标签
        
        # 5. 更新固定标签页图标
        if hasattr(self, 'tabs'):
            try:
                 prompt_icon = qta.icon('fa5s.keyboard', color=icon_color)
                 search_icon = qta.icon('fa5s.search', color=icon_color)
                 # 假设提示词和搜索标签页总是在索引 0 和 1
                 if self.tabs.count() > 0:
                     self.tabs.setTabIcon(0, prompt_icon)
                 if self.tabs.count() > 1:
                     self.tabs.setTabIcon(1, search_icon)
                 print("AuxiliaryWindow: 固定标签页图标颜色更新完成")
            except Exception as e:
                 print(f"AuxiliaryWindow: 更新固定标签页图标时出错: {e}")

        # 6. 强制刷新 QTabWidget 样式
        if hasattr(self, 'tabs'):
            try:
                print("AuxiliaryWindow: 尝试强制刷新 QTabWidget 样式...")
                self.tabs.style().unpolish(self.tabs)
                self.tabs.style().polish(self.tabs)
                print("AuxiliaryWindow: QTabWidget 样式刷新完成")
            except Exception as e:
                print(f"AuxiliaryWindow: 刷新 QTabWidget 样式时出错: {e}")
        
        # 7. 强制刷新 PromptInput 样式 (保持之前的修改)
        if hasattr(self, 'prompt_input'):
            try:
                print("AuxiliaryWindow: 尝试强制刷新 PromptInput 样式...")
                self.prompt_input.style().unpolish(self.prompt_input)
                self.prompt_input.style().polish(self.prompt_input)
                # 也可以尝试更新整个 AuxiliaryWindow 的样式
                # self.style().unpolish(self)
                # self.style().polish(self)
                print("AuxiliaryWindow: PromptInput 样式刷新完成")
            except Exception as e:
                print(f"AuxiliaryWindow: 刷新 PromptInput 样式时出错: {e}")
        
        # 8. 强制刷新 FileExplorer 样式
        if hasattr(self, 'file_explorer'):
            try:
                print("AuxiliaryWindow: 尝试强制刷新 FileExplorer 样式...")
                self.file_explorer.style().unpolish(self.file_explorer)
                self.file_explorer.style().polish(self.file_explorer)
                # 如果FileExplorer内部有需要单独更新的，也应调用
                # self.file_explorer.update_theme() # 假设有这个方法
                print("AuxiliaryWindow: FileExplorer 样式刷新完成")
            except Exception as e:
                 print(f"AuxiliaryWindow: 刷新 FileExplorer 样式时出错: {e}")
                 
        # 9. 强制刷新 PromptHistory 样式
        if hasattr(self, 'prompt_history'):
            try:
                print("AuxiliaryWindow: 尝试强制刷新 PromptHistory 样式...")
                self.prompt_history.style().unpolish(self.prompt_history)
                self.prompt_history.style().polish(self.prompt_history)
                # 如果PromptHistory内部有需要单独更新的，也应调用
                # self.prompt_history.update_theme() # 假设有这个方法
                print("AuxiliaryWindow: PromptHistory 样式刷新完成")
            except Exception as e:
                 print(f"AuxiliaryWindow: 刷新 PromptHistory 样式时出错: {e}")
                 
        print("AuxiliaryWindow: 图标和样式更新完成。") 

    def load_splitter_sizes(self):
        """加载保存的分割器位置"""
        settings = QSettings("AiSparkHub", "AiSparkHub-Desktop")
        if settings.contains("auxiliary_window/splitter_sizes"):
            # 从设置中获取保存的尺寸
            sizes = settings.value("auxiliary_window/splitter_sizes")
            
            # 确保正确转换为整数列表
            if isinstance(sizes, list) and len(sizes) == 3:
                try:
                    # QSettings可能会将值存储为字符串或其他类型，确保转换为整数
                    int_sizes = [int(size) for size in sizes]
                    self.splitter.setSizes(int_sizes)
                    print(f"已加载分割器位置: {int_sizes}")
                except (ValueError, TypeError) as e:
                    print(f"转换分割器尺寸时出错: {e}")
    
    def save_splitter_sizes(self, pos=None, index=None):
        """保存分割器位置"""
        # 参数pos和index是splitterMoved信号传递的，但我们不需要它们
        sizes = self.splitter.sizes()
        
        # 只有当所有尺寸都合理时才保存
        if all(size > 0 for size in sizes):
            settings = QSettings("AiSparkHub", "AiSparkHub-Desktop")
            settings.setValue("auxiliary_window/splitter_sizes", sizes)
            print(f"已保存分割器位置: {sizes}") 

    def open_shortcut_settings(self):
        """打开快捷键设置对话框"""
        try:
            # 创建对话框
            dialog = ShortcutSettingsDialog(self)
            
            # 连接快捷键更改信号
            dialog.shortcuts_changed.connect(self.on_shortcuts_changed)
            
            # 显示对话框
            dialog.exec()
        except Exception as e:
            print(f"打开快捷键设置对话框出错: {e}")
            import traceback
            traceback.print_exc()

    def on_shortcuts_changed(self, shortcuts):
        """快捷键更改时的处理函数"""
        print(f"快捷键已更改: {shortcuts}")
        # 通知用户需要重启应用才能应用新的快捷键
        # 此处无需做其他操作，因为快捷键已保存到QSettings中，并在下次启动时生效
        
    def toggle_display_mode(self):
        """切换显示模式（全屏/窗口/双屏）"""
        try:
            # 检查是否有window_manager
            if not hasattr(self, 'window_manager') or not self.window_manager:
                print("无法切换显示模式：window_manager未初始化")
                return
                
            # 调用window_manager的循环显示模式方法
            self.window_manager.cycle_display_mode()
            print("已切换显示模式")
        except Exception as e:
            print(f"切换显示模式时出错: {e}")
            import traceback
            traceback.print_exc()

    def update_history_content(self, container, index):
        """更新历史记录内容，根据标签索引切换显示的内容
        
        Args:
            container (QWidget): 内容容器
            index (int): 标签索引
        """
        # 清除容器中的所有小部件
        layout = container.layout()
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
                
        # 根据索引添加相应的内容
        if index == 0:  # 历史标签
            layout.addWidget(self.prompt_history.history_tab)
        elif index == 1:  # 统计标签
            layout.addWidget(self.prompt_history.stats_tab)

    def switch_history_view(self, index):
        """根据标签切换历史记录视图
        
        Args:
            index (int): 标签索引
        """
        if not hasattr(self, 'prompt_history') or not self.prompt_history:
            return
            
        # 切换PromptHistory中的标签页
        if hasattr(self.prompt_history, 'tab_widget'):
            self.prompt_history.tab_widget.setCurrentIndex(index)
        print(f"已切换历史记录视图到索引: {index}")

    def sync_tab_selection(self, source_tab, target_tab, index):
        """同步标签页选择
        
        Args:
            source_tab (QTabWidget): 源标签控件
            target_tab (QTabWidget): 目标标签控件
            index (int): 标签索引
        """
        # 防止循环调用
        if hasattr(target_tab, 'blockSignals'):
            target_tab.blockSignals(True)
            
        if hasattr(target_tab, 'setCurrentIndex'):
            target_tab.setCurrentIndex(index)
            
        if hasattr(target_tab, 'blockSignals'):
            target_tab.blockSignals(False)
            
        print(f"标签选择已同步: {index}")