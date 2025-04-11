#!/usr/bin/env python
# -*- coding: utf-8 -*-

# auxiliary_window.py: 定义 AuxiliaryWindow 类
# 该窗口作为辅助窗口，包含文件浏览器、提示词输入框和提示词历史记录。
# 用于管理和同步提示词到主窗口的 AI 对话页面。

from PyQt6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QPushButton, QVBoxLayout, QLabel, QSplitter, QFrame, QToolBar, QStackedWidget, QTabWidget, QApplication, QMessageBox
from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QSize, QTimer, QUrl
from PyQt6.QtGui import QIcon
import qtawesome as qta
import os
from datetime import datetime
import sqlite3
import http.server
import socketserver
import threading
import re

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
        
        # 设置样式
        self.setStyleSheet("""
            #ribbonToolBar {
                background-color: #2E3440;
                border-right: 1px solid #4C566A;
                padding: 5px 2px;
                spacing: 8px;
            }
            QToolButton {
                background-color: transparent;
                border: none;
                border-radius: 3px;
                padding: 5px;
            }
            QToolButton:hover {
                background-color: #3B4252;
            }
            QToolButton:pressed {
                background-color: #434C5E;
            }
        """)

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
            self.title_bar.setFixedHeight(38)
            self.title_bar.setObjectName("panelTitleBar")
            title_layout = QHBoxLayout(self.title_bar)
            title_layout.setContentsMargins(8, 0, 8, 0)
            
            # 创建标题标签
            title_label = QLabel(title)
            title_label.setStyleSheet("color: #D8DEE9; font-weight: bold;")
            
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
            
            # 最大化/还原按钮
            maximize_button = QPushButton()
            maximize_button.setIcon(qta.icon('fa5s.window-maximize'))
            maximize_button.clicked.connect(window.toggle_maximize)
            
            # 关闭按钮
            close_button = QPushButton()
            close_button.setIcon(qta.icon('fa5s.times'))
            close_button.clicked.connect(window.close)
            
            # 设置按钮样式
            button_style = """
                QPushButton {
                    background: transparent;
                    border: none;
                    padding: 6px 8px;
                    margin: 0;
                }
                QPushButton:hover {
                    background: #3B4252;
                }
            """
            close_button_style = button_style + """
                QPushButton:hover {
                    background: #BF616A;
                }
            """
            minimize_button.setStyleSheet(button_style)
            maximize_button.setStyleSheet(button_style)
            close_button.setStyleSheet(close_button_style)
            
            # 添加按钮到标题栏
            title_layout.addWidget(minimize_button)
            title_layout.addWidget(maximize_button)
            title_layout.addWidget(close_button)
            
            # 保存按钮引用便于后续访问
            window.minimize_button = minimize_button
            window.maximize_button = maximize_button
        
        # 创建分隔线（设置为非常细的线条）
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Plain)
        separator.setLineWidth(0)
        separator.setMidLineWidth(0)  # 将中线宽度设为0以获得更细的线条
        separator.setFixedHeight(1)  # 将高度固定为1px
        separator.setStyleSheet("background-color: #3B4252;")  # 使用与中间标签栏一致的颜色
        
        # 添加标题栏和分隔线到主布局
        layout.addWidget(self.title_bar)
        layout.addWidget(separator)
        
        # 添加内容区域
        layout.addWidget(content_widget, 1)  # 使内容区域拉伸填充
        
        # 设置样式
        self.title_bar.setStyleSheet("""
            #panelTitleBar {
                background-color: #2E3440;
            }
        """)
        
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
        
        # 内容区域垂直布局容器
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # 创建分割器
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        # 设置分割器样式
        self.splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #4C566A;
                width: 1px;
            }
        """)
        
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
        
        # 使用定时器延迟加载搜索页面（确保服务器已启动）
        QTimer.singleShot(500, self.load_search_page)
    
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
        # 设置全局滚动条样式
        self.setStyleSheet("""
            QScrollBar:vertical {
                background: #2E3440;
                width: 14px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #4C566A;
                min-height: 20px;
                border-radius: 7px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
            QScrollBar:horizontal {
                background: #2E3440;
                height: 14px;
                margin: 0px;
            }
            QScrollBar::handle:horizontal {
                background: #4C566A;
                min-width: 20px;
                border-radius: 7px;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
            }
        """)
        
        # 文件浏览器
        self.file_explorer = FileExplorer()
        
        # 添加特殊样式使标签页顶部没有边框
        self.file_explorer.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border-top: none;
                background-color: #2E3440;
            }
        """)
        
        # 创建自定义标题栏
        title_bar = QWidget()
        title_bar.setFixedHeight(38)
        title_bar.setObjectName("panelTitleBar")
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(8, 0, 8, 0)
        
        # 添加文件夹按钮 - 靠左显示
        add_folder_btn = QPushButton()
        add_folder_btn.setIcon(qta.icon('fa5s.folder-plus'))
        add_folder_btn.setToolTip("添加文件夹")
        add_folder_btn.clicked.connect(self.file_explorer.add_folder)
        
        # 设置按钮样式
        button_style = """
            QPushButton {
                background: transparent;
                border: none;
                padding: 6px 8px;
                margin: 0;
                color: #D8DEE9;
            }
            QPushButton:hover {
                background: #3B4252;
            }
        """
        add_folder_btn.setStyleSheet(button_style)
        
        # 添加按钮到标题栏（靠左）
        title_layout.addWidget(add_folder_btn)
        # 添加伸缩空间在按钮之后，使其余空间填充到右侧
        title_layout.addStretch(1)
        
        file_panel = PanelWidget("", self.file_explorer, self, custom_titlebar=title_bar)
        
        # 创建标签页控件
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        self.tabs.setDocumentMode(True)  # 使标签页更现代化
        
        # 标签页控件增加事件过滤器，用于实现拖拽窗口的功能
        self.tabs.tabBar().installEventFilter(self)
        
        # 自定义标签页样式，使其更像标题栏
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border-top: 1px solid #3B4252;
                background-color: #2E3440;
            }
            QTabWidget::tab-bar {
                alignment: left;
                background-color: #2E3440;
            }
            QTabBar {
                background-color: #2E3440;
                qproperty-drawBase: 0;
            }
            QTabBar::tab {
                background: #3B4252;
                color: #D8DEE9;
                padding: 0px 12px;
                border: none;
                margin-right: 2px;
                min-width: 10ex;
                height: 38px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background: #4C566A;
                color: #ECEFF4;
            }
            QTabBar::tab:hover:!selected {
                background: #434C5E;
            }
            QTabBar::close-button {
                image: none;
                background: transparent;
                border: none;
                margin: 0px;
                padding: 0px;
            }
            QTabBar::close-button:hover {
                background: #BF616A;
                border-radius: 2px;
            }
            /* 添加滚动条样式 */
            QScrollBar:vertical {
                background: #2E3440;
                width: 14px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #4C566A;
                min-height: 20px;
                border-radius: 7px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
            QScrollBar:horizontal {
                background: #2E3440;
                height: 14px;
                margin: 0px;
            }
            QScrollBar::handle:horizontal {
                background: #4C566A;
                min-width: 20px;
                border-radius: 7px;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
            }
        """)
        
        # 自定义标签页关闭按钮为qtawesome图标
        close_icon = qta.icon('fa5s.times', color='#D8DEE9')
        for i in range(self.tabs.count()):
            # 为已有标签页设置关闭图标
            if self.tabs.tabBar().tabButton(i, QTabWidget.ButtonPosition.RightSide):
                close_button = self.tabs.tabBar().tabButton(i, QTabWidget.ButtonPosition.RightSide)
                close_button.setIcon(close_icon)
        
        # 监听标签页添加事件，为新标签页设置关闭图标
        self.tabs.tabBarClicked.connect(self._check_tab_close_buttons)
        # 监听标签页添加事件
        self.tabs.currentChanged.connect(self._check_tab_close_buttons)
        
        # 创建提示词输入
        self.prompt_input = PromptInput()
        
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
        middle_container.setStyleSheet("background-color: #2E3440;")
        
        # 只设置一个垂直布局，不使用PanelWidget
        middle_layout = QVBoxLayout(middle_container)
        middle_layout.setContentsMargins(0, 0, 0, 0)
        middle_layout.setSpacing(0)
        
        # 将标签页直接添加到布局，它会成为"标题栏"
        middle_layout.addWidget(self.tabs)
        
        # 提示词历史记录（设置为控制面板，移回窗口控制按钮）
        self.prompt_history = PromptHistory(self.db_manager)
        history_panel = PanelWidget("历史记录", self.prompt_history, self, is_control_panel=True)
        
        # 添加面板到分割器
        self.splitter.addWidget(file_panel)
        self.splitter.addWidget(middle_container)  # 直接添加容器，不使用PanelWidget包装
        self.splitter.addWidget(history_panel)
        
        # 设置初始比例 (3:4:3)
        self.splitter.setSizes([300, 400, 300])
        
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
        """处理提示词提交事件"""
        if not prompt_text or not prompt_text.strip():
            print("提示词为空，不执行发送操作")
            return
            
        print(f"发送提示词: {prompt_text[:30]}...")
        
        # 直接同步提示词到主窗口的AI网页
        # prompt_sync.sync_prompt会处理存储到prompt_details表
        self.prompt_sync.sync_prompt(prompt_text)
        
        # 刷新历史记录
        self.prompt_history.refresh_history()
        
        # 清空输入框
        self.prompt_input.clear()
    
    def on_open_main_window(self):
        """处理打开主窗口的请求"""
        # 发射信号通知应用程序打开主窗口
        self.request_open_main_window.emit()
    
    def closeEvent(self, event):
        """处理窗口关闭事件"""
        # 关闭HTTP服务器
        if hasattr(self, 'server') and self.server:
            try:
                self.server.shutdown()
                print("已关闭本地HTTP服务器")
            except Exception as e:
                print(f"关闭HTTP服务器时出错: {e}")
                
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
            file_type (str): 文件类型
        """
        # 获取文件名
        file_name = os.path.basename(file_path)
        
        # 检查文件是否已经打开
        for i in range(self.tabs.count()):
            if self.tabs.tabText(i) == file_name:
                # 如果已打开，切换到对应标签
                self.tabs.setCurrentIndex(i)
                return
        
        # 创建文件查看器
        file_viewer = FileViewer()
        
        # 打开文件
        file_viewer.open_file(file_path, file_type)
        
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
    
    def _get_file_icon(self, file_type):
        """根据文件类型获取图标
        
        Args:
            file_type (str): 文件类型
            
        Returns:
            QIcon: 文件图标
        """
        icons = {
            'html': qta.icon('fa5s.file-code', color='#EBCB8B'),
            'markdown': qta.icon('fa5s.file-alt', color='#A3BE8C'),
            'text': qta.icon('fa5s.file-alt', color='#81A1C1'),
            'docx': qta.icon('fa5s.file-word', color='#5E81AC'),
            'powerpoint': qta.icon('fa5s.file-powerpoint', color='#D08770'),
            'excel': qta.icon('fa5s.file-excel', color='#A3BE8C'),
            'pdf': qta.icon('fa5s.file-pdf', color='#BF616A')
        }
        
        return icons.get(file_type, qta.icon('fa5s.file', color='#D8DEE9'))

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
            
            # 设置对话框样式
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #2E3440;
                    color: #D8DEE9;
                }
                QLabel {
                    color: #E5E9F0;
                }
                QPushButton {
                    background-color: #4C566A;
                    color: #E5E9F0;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 12px;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #5E81AC;
                }
                QPushButton:pressed {
                    background-color: #81A1C1;
                }
            """)
            
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