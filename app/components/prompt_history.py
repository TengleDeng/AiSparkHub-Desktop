#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QListWidget, QListWidgetItem,
                           QLineEdit, QLabel, QHBoxLayout, QPushButton, QMenu,
                           QScrollArea, QFrame, QToolButton, QSizePolicy,
                           QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QColor, QAction, QPalette, QFont, QPixmap
import qtawesome as qta
from datetime import datetime
import webbrowser
from urllib.parse import urlparse
import os
import sys

class PromptItemWidget(QWidget):
    """自定义提示词历史记录小部件"""
    
    copied = pyqtSignal(str)  # 复制提示词信号
    favorite_toggled = pyqtSignal(str, bool)  # 收藏切换信号
    deleted = pyqtSignal(str)  # 删除信号
    open_all_urls = pyqtSignal(list)  # 打开所有链接信号
    prompt_text_selected = pyqtSignal(str)  # 双击选择提示词信号
    
    def __init__(self, prompt_data, parent=None):
        super().__init__(parent)
        self.prompt_data = prompt_data
        # 获取图标目录路径（与AI_view一致）
        # 图标文件夹路径 - 考虑打包环境和开发环境
        self.icon_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "icons")
        if not os.path.exists(self.icon_dir) and getattr(sys, 'frozen', False):
            # 打包环境下可能路径不同，尝试相对于可执行文件的路径
            base_dir = os.path.dirname(sys.executable)
            self.icon_dir = os.path.join(base_dir, "icons")
            
        # 列出图标目录中的所有文件，帮助调试
        try:
            if os.path.exists(self.icon_dir):
                files = os.listdir(self.icon_dir)
                print(f"图标目录中的文件: {files}")
            else:
                print(f"图标目录不存在: {self.icon_dir}")
        except Exception as e:
            print(f"列出图标目录内容出错: {e}")
            
        self.setup_ui()
        self.update_data(prompt_data)
        
    def setup_ui(self):
        """设置UI界面"""
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)
        
        # 头部布局（时间和操作按钮）
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        
        # 时间标签
        self.time_label = QLabel()
        self.time_label.setStyleSheet("""
            color: #81A1C1;
            font-size: 12px;
            text-align: left;
            padding: 0;
        """)
        self.time_label.setFixedWidth(70)  # 减小宽度，因为现在是两行显示
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)  # 文本左对齐
        header_layout.addWidget(self.time_label)
        
        # 添加一个水平框架作为图标容器
        self.icons_frame = QFrame()
        self.icons_frame.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
                padding: 0px;
            }
        """)
        self.icons_frame.setFixedHeight(20)  # 设置为20px高度
        self.icons_layout = QHBoxLayout(self.icons_frame)
        self.icons_layout.setContentsMargins(0, 0, 0, 0)
        self.icons_layout.setSpacing(4)  # 减小间距
        self.icons_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.icons_frame)
        
        # 添加弹簧
        header_layout.addStretch()
        
        # 编辑按钮
        self.edit_btn = QToolButton()
        self.edit_btn.setIcon(qta.icon('fa5s.edit', color='#D8DEE9'))
        self.edit_btn.setToolTip("编辑提示词")
        self.edit_btn.setStyleSheet(self.get_button_style())
        self.edit_btn.setFixedSize(QSize(20, 20))
        self.edit_btn.setIconSize(QSize(16, 16))
        header_layout.addWidget(self.edit_btn)
        
        # 收藏按钮 - 使用自定义图标
        self.favorite_btn = QToolButton()
        self.favorite_btn.setToolTip("收藏提示词")
        self.favorite_btn.setStyleSheet(self.get_button_style())
        self.favorite_btn.setFixedSize(QSize(20, 20))
        self.favorite_btn.setIconSize(QSize(16, 16))
        self.favorite_btn.clicked.connect(self.toggle_favorite)
        
        # 创建图标并存储以便重复使用
        self.star_filled_icon = qta.icon('fa5s.star', color='#EBCB8B')
        
        # 尝试创建空星图标
        try:
            self.star_empty_icon = qta.icon('fa.star-o', color='#D8DEE9')
        except Exception:
            try:
                self.star_empty_icon = qta.icon('mdi.star-outline', color='#D8DEE9')
            except Exception:
                # 如果qtawesome无法提供空星图标，使用带不同颜色的实心星星
                self.star_empty_icon = qta.icon('fa5s.star', color='#4C566A')
        
        # 默认设置空星图标
        self.favorite_btn.setIcon(self.star_empty_icon)
        header_layout.addWidget(self.favorite_btn)
        
        # 删除按钮
        self.delete_btn = QToolButton()
        self.delete_btn.setIcon(qta.icon('fa5s.trash-alt', color='#BF616A'))
        self.delete_btn.setToolTip("删除提示词")
        self.delete_btn.setStyleSheet(self.get_button_style())
        self.delete_btn.setFixedSize(QSize(20, 20))
        self.delete_btn.setIconSize(QSize(16, 16))
        self.delete_btn.clicked.connect(self.delete_prompt)
        header_layout.addWidget(self.delete_btn)
        
        main_layout.addLayout(header_layout)
        
        # 提示词内容
        self.content_label = QLabel()
        self.content_label.setWordWrap(True)
        self.content_label.setStyleSheet("""
            color: #E5E9F0;
            background-color: #3B4252;
            border-radius: 6px;
            padding: 8px;
            font-size: 13px;
        """)
        self.content_label.setTextFormat(Qt.TextFormat.PlainText)
        self.content_label.setMaximumHeight(66)  # 约3行文本高度
        self.content_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        main_layout.addWidget(self.content_label)
        
        # 设置容器样式
        self.setStyleSheet("""
            QWidget {
                background-color: #2E3440;
                border-radius: 8px;
            }
        """)
        self.setMinimumHeight(110)
        self.setMaximumHeight(140)
        
    def get_button_style(self):
        """获取按钮样式"""
        return """
            QToolButton {
                background-color: #3B4252;
                border-radius: 10px;
                padding: 2px;
                border: none;
            }
            QToolButton:hover {
                background-color: #4C566A;
            }
            QToolButton:pressed {
                background-color: #5E81AC;
            }
        """
    
    def create_ai_link_button(self, url):
        """创建AI链接按钮"""
        btn = QToolButton()
        
        # 提取域名以显示图标
        domain = urlparse(url).netloc
        if domain.startswith('www.'):
            domain = domain[4:]
            
        # 设置默认图标
        icon = None
        
        # 尝试根据域名获取合适的AI平台标识
        ai_key = None
        
        # URL到平台标识的映射(保持与prompt_injector.js的一致性)
        url_to_platform = {
            'chat.openai.com': 'chatgpt',
            'chatgpt.com': 'chatgpt',
            'kimi.moonshot.cn': 'kimi',
            'www.doubao.com': 'doubao',
            'doubao.com': 'doubao',
            'www.perplexity.ai': 'perplexity',
            'perplexity.ai': 'perplexity',
            'n.cn': 'n',
            'metaso.cn': 'metaso',
            'www.metaso.cn': 'metaso',
            'chatglm.cn': 'chatglm',
            'www.chatglm.cn': 'chatglm',
            'yuanbao.tencent.com': 'yuanbao',
            'www.biji.com': 'biji',
            'biji.com': 'biji',
            'x.com': 'grok',
            'grok.com': 'grok',
            'www.grok.com': 'grok',
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
        
        print(f"为URL: {url} 尝试加载图标: {ai_key}")
        
        # 先尝试加载本地图标文件
        if ai_key:
            # 使用小写的key与文件名保持一致
            lowercase_key = ai_key.lower()
            icon_path = os.path.join(self.icon_dir, f"{lowercase_key}.png")  # 先尝试png
            print(f"尝试加载PNG图标: {icon_path}")
            if not os.path.exists(icon_path):
                icon_path = os.path.join(self.icon_dir, f"{lowercase_key}.ico")  # 再尝试ico
                print(f"PNG图标不存在，尝试加载ICO图标: {icon_path}")
            
            if os.path.exists(icon_path):
                # 加载图标
                try:
                    print(f"图标文件存在，开始加载: {icon_path}")
                    if icon_path.endswith('.ico'):
                        icon = QIcon(icon_path)
                    else:
                        icon = QIcon(QPixmap(icon_path))
                    print(f"成功加载本地图标: {icon_path}")
                except Exception as e:
                    print(f"加载图标失败: {e}")
                    icon = None  # 加载失败，继续使用qtawesome
            else:
                print(f"找不到本地图标文件: {icon_path}")
        
        # 如果本地图标加载失败，使用qtawesome
        if icon is None:
            # 根据AI平台选择合适的图标
            icon_map = {
                "chatgpt": "fa5b.chrome",      # ChatGPT使用Chrome图标
                "claude": "fa5s.robot",        # Claude使用机器人图标
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
                "bing": "fa5b.microsoft",      # Bing用微软图标
                "spark": "fa5s.comment-alt",   # 讯飞星火用评论图标
                "biji": "fa5s.sticky-note",    # 笔记用便签图标
                "n": "fa5s.yin-yang",          # N用特殊图标
                "deepseek": "fa5s.power-off"   # DeepSeek用电源图标
            }
            
            # 获取该平台对应的图标名，如果没有指定则使用全局图标
            icon_name = icon_map.get(ai_key.lower() if ai_key else "", "fa5s.globe")
            try:
                print(f"尝试使用qtawesome图标: {icon_name}")
                icon = qta.icon(icon_name, color='#88C0D0')
                print(f"成功加载qtawesome图标: {icon_name}")
            except Exception as e:
                # 如果依然失败，使用最安全的图标
                print(f"qtawesome图标加载失败: {e}")
                icon = qta.icon("fa5s.globe", color='#88C0D0')
                print("回退到默认图标: fa5s.globe")
        
        btn.setIcon(icon)
        btn.setToolTip(f"打开链接: {url}")
        
        # 使用与其他按钮相同的样式
        btn.setStyleSheet(self.get_button_style())
        
        # 使用与其他按钮相同的大小
        btn.setFixedSize(QSize(20, 20))
        
        # 使用适当的图标尺寸
        btn.setIconSize(QSize(16, 16))
        
        # 将URL存储在按钮中，以便点击时打开
        btn.setProperty("url", url)
        btn.clicked.connect(lambda: self.open_url(url))
        
        return btn
    
    def open_url(self, url):
        """打开URL链接"""
        # 将单个URL打包成列表发送给AI视图
        urls = [url]
        print(f"准备在AI视图中打开单个链接: {url}")
        self.open_all_urls.emit(urls)
    
    def update_data(self, prompt_data):
        """更新显示数据"""
        self.prompt_data = prompt_data
        
        # 调试信息：输出记录ID和提示词内容的一部分
        record_id = prompt_data.get('id', '无ID')
        prompt_text = prompt_data.get('prompt_text', '无提示词内容')
        print(f"\n调试 - 记录ID: {record_id}")
        print(f"调试 - 提示词: {prompt_text[:30]}...")
        
        # 更新时间标签
        try:
            if isinstance(prompt_data.get('timestamp'), str):
                try:
                    time_obj = datetime.fromisoformat(prompt_data['timestamp'])
                except ValueError:
                    time_obj = datetime.now()
            elif isinstance(prompt_data.get('timestamp'), (int, float)):
                time_obj = datetime.fromtimestamp(prompt_data['timestamp'])
            else:
                time_obj = datetime.now()
                
            # 分别格式化日期和时间，使用HTML实现两行显示
            date_str = time_obj.strftime("%Y-%m-%d")
            time_str = time_obj.strftime("%H:%M")
            self.time_label.setText(f"{date_str}<br>{time_str}")
            self.time_label.setTextFormat(Qt.TextFormat.RichText)  # 启用HTML格式
        except:
            self.time_label.setText("未知时间")
        
        # 更新提示词内容
        # 限制显示的文本长度，大约3行左右
        max_chars = 150
        if len(prompt_text) > max_chars:
            display_text = prompt_text[:max_chars] + "..."
        else:
            display_text = prompt_text
        self.content_label.setText(display_text)
        self.content_label.setToolTip(prompt_text)
        
        # 清除所有现有图标
        self.clear_ai_icons()
        
        # 调试信息：输出URL键及其值
        all_keys = set(prompt_data.keys())
        url_keys = [k for k in all_keys if k.startswith('ai') and k.endswith('_url')]
        print(f"调试 - 数据中的所有键: {all_keys}")
        print(f"调试 - 找到URL键: {url_keys}")
        
        # 添加AI链接按钮
        url_count = 0
        for i in range(1, 7):
            url_key = f"ai{i}_url"
            if url_key in prompt_data and prompt_data[url_key] and prompt_data[url_key].strip():
                url = prompt_data[url_key]
                print(f"调试 - {url_key}: {url}")
                btn = self.create_ai_link_button(url)
                self.icons_layout.addWidget(btn)
                url_count += 1
        
        # 如果有链接，添加"打开所有"按钮
        if url_count > 0:
            self.add_open_all_button()
            
        print(f"调试 - 总共添加了 {url_count} 个链接按钮")
        
        # 更新收藏按钮状态
        is_favorite = prompt_data.get('favorite', False)
        if is_favorite:
            self.favorite_btn.setIcon(self.star_filled_icon)
        else:
            self.favorite_btn.setIcon(self.star_empty_icon)
    
    def add_open_all_button(self):
        """添加打开所有链接的按钮"""
        btn = QToolButton()
        btn.setIcon(qta.icon('fa5s.external-link-alt', color='#88C0D0'))
        btn.setToolTip("在AI视图中打开所有链接")
        btn.setStyleSheet(self.get_button_style())
        btn.setFixedSize(QSize(20, 20))
        btn.setIconSize(QSize(16, 16))
        btn.clicked.connect(self.open_all_links)
        self.icons_layout.addWidget(btn)
        
    def open_all_links(self):
        """收集并打开所有链接"""
        urls = []
        for i in range(1, 7):
            url_key = f"ai{i}_url"
            if url_key in self.prompt_data and self.prompt_data[url_key] and self.prompt_data[url_key].strip():
                urls.append(self.prompt_data[url_key])
        
        if urls:
            print(f"准备打开 {len(urls)} 个链接: {urls}")
            self.open_all_urls.emit(urls)
    
    def clear_ai_icons(self):
        """清除所有AI图标"""
        # 删除图标布局中的所有小部件
        while self.icons_layout.count():
            item = self.icons_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def toggle_favorite(self):
        """切换收藏状态"""
        prompt_id = self.prompt_data.get('id')
        if not prompt_id:
            return
            
        # 更新当前显示状态（实际数据库更新在PromptHistory中处理）
        is_favorite = self.prompt_data.get('favorite', False)
        self.prompt_data['favorite'] = not is_favorite
        
        # 更新图标
        if self.prompt_data['favorite']:
            self.favorite_btn.setIcon(self.star_filled_icon)
        else:
            self.favorite_btn.setIcon(self.star_empty_icon)
        
        # 发射信号
        self.favorite_toggled.emit(prompt_id, self.prompt_data['favorite'])
    
    def delete_prompt(self):
        """删除提示词"""
        prompt_id = self.prompt_data.get('id')
        if not prompt_id:
            return
        
        # 显示删除确认对话框
        msg_box = QMessageBox()
        msg_box.setWindowTitle("确认删除")
        msg_box.setText("您确定要删除这条提示词记录吗？")
        msg_box.setInformativeText("此操作不可撤销。")
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
        
        # 如果用户确认删除
        if response == QMessageBox.StandardButton.Yes:
            # 发送删除信号
            self.deleted.emit(prompt_id)

    def mouseDoubleClickEvent(self, event):
        """双击事件处理"""
        prompt_text = self.prompt_data.get('prompt_text', '')
        if prompt_text:
            # 发送提示词文本给父组件
            self.prompt_text_selected.emit(prompt_text)
        super().mouseDoubleClickEvent(event)


class PromptHistory(QWidget):
    """提示词历史记录组件"""
    
    # 定义信号
    prompt_selected = pyqtSignal(str)  # 提示词选中信号
    favorite_toggled = pyqtSignal(str, bool)  # 收藏状态切换信号，参数: prompt_id, is_favorite
    open_urls = pyqtSignal(list)  # 打开URLs信号，用于传递给AI视图
    request_set_prompt = pyqtSignal(str)  # 请求设置提示词内容，需要检查现有内容
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setup_ui()
        self.refresh_history()
    
    def setup_ui(self):
        """设置UI界面"""
        # 创建布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # 创建顶部工具栏
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setSpacing(8)
        
        # 创建搜索框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索历史记录...")
        self.search_input.textChanged.connect(self.search_history)
        toolbar.addWidget(self.search_input, 1)  # 搜索框占据大部分空间
        
        # 添加收藏过滤按钮 - 使用自定义图标
        self.favorite_filter_btn = QPushButton(self)
        
        # 创建星形图标
        self.filter_star_normal = qta.icon('fa5s.star', color='#D8DEE9')  # 普通状态
        self.filter_star_active = qta.icon('fa5s.star', color='#EBCB8B')  # 激活状态（黄色）
        
        self.favorite_filter_btn.setIcon(self.filter_star_normal)
        self.favorite_filter_btn.setToolTip("显示收藏的提示词")
        self.favorite_filter_btn.setCheckable(True)
        self.favorite_filter_btn.clicked.connect(self.toggle_favorite_filter)
        self.favorite_filter_btn.setStyleSheet("""
            QPushButton {
                background-color: #2E3440;
                border: 1px solid #3B4252;
                border-radius: 4px;
                padding: 4px;
            }
            QPushButton:checked {
                background-color: #5E81AC;
            }
            QPushButton:hover {
                background-color: #3B4252;
            }
        """)
        toolbar.addWidget(self.favorite_filter_btn)
        
        # 添加刷新按钮
        refresh_btn = QPushButton(self)
        refresh_btn.setIcon(qta.icon('fa5s.sync'))
        refresh_btn.setToolTip("刷新历史记录")
        refresh_btn.clicked.connect(self.refresh_history)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #2E3440;
                border: 1px solid #3B4252;
                border-radius: 4px;
                padding: 4px;
            }
            QPushButton:hover {
                background-color: #3B4252;
            }
        """)
        toolbar.addWidget(refresh_btn)
        
        # 添加工具栏到主布局
        layout.addLayout(toolbar)
        
        # 创建滚动区域和内容容器
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # 创建容器小部件用于存放历史记录项
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(10, 10, 10, 10)
        self.content_layout.setSpacing(8)  # 设置条目之间的间距
        self.content_layout.addStretch()  # 添加弹簧，使条目靠上排列
        
        self.scroll_area.setWidget(self.content_widget)
        layout.addWidget(self.scroll_area)
        
        # 设置样式
        self.setStyleSheet("""
            QLineEdit {
                background-color: #2E3440;
                color: #D8DEE9;
                border: 1px solid #3B4252;
                border-radius: 4px;
                padding: 8px;
            }
            QScrollArea {
                background-color: #2E3440;
                border: none;
            }
            QWidget#content_widget {
                background-color: #2E3440;
            }
        """)
        self.content_widget.setObjectName("content_widget")
        
        # 初始化记录收藏过滤状态
        self.show_favorites_only = False
    
    def refresh_history(self):
        """刷新历史记录"""
        # 清除旧的历史记录项
        self.clear_history_items()
        
        try:
            print("\n尝试直接从数据库查询数据")
            # 使用数据库连接直接查询数据
            cursor = self.db_manager.conn.cursor()
            
            if self.show_favorites_only:
                # 收藏记录
                cursor.execute(
                    """SELECT id, prompt, timestamp, favorite, 
                        ai1_url, ai2_url, ai3_url, ai4_url, ai5_url, ai6_url 
                        FROM prompt_details 
                        WHERE favorite = 1 
                        ORDER BY timestamp DESC LIMIT 50"""
                )
            else:
                # 所有记录
                cursor.execute(
                    """SELECT id, prompt, timestamp, favorite, 
                        ai1_url, ai2_url, ai3_url, ai4_url, ai5_url, ai6_url 
                        FROM prompt_details 
                        ORDER BY timestamp DESC LIMIT 50"""
                )
            
            rows = cursor.fetchall()
            print(f"直接查询到 {len(rows)} 条记录")
            
            if rows and len(rows) > 0:
                # 检查第一条记录的所有键
                first_row = rows[0]
                print(f"第一条记录的键: {list(first_row.keys())}")
                
                # 检查是否包含URL字段
                for i in range(1, 7):
                    key = f"ai{i}_url"
                    if key in first_row:
                        print(f"{key} 存在于记录中，值: {first_row[key] or '空'}")
            
            # 将查询结果直接转换为字典，不做任何处理
            history = []
            for row in rows:
                # 直接复制原始行数据，确保所有字段都包含
                record = dict(row)
                
                # 添加ai_targets字段（为了兼容性）
                record['ai_targets'] = []
                
                # 从URL提取ai_targets
                for i in range(1, 7):
                    url_key = f"ai{i}_url"
                    if url_key in record and record[url_key]:
                        try:
                            domain = urlparse(record[url_key]).netloc
                            if domain.startswith('www.'):
                                domain = domain[4:]
                            if domain and domain not in record['ai_targets']:
                                record['ai_targets'].append(domain)
                        except:
                            pass
                
                # 如果没有找到任何ai_targets，添加默认值
                if not record['ai_targets']:
                    record['ai_targets'] = ["未知AI"]
                
                # 将prompt重命名为prompt_text (为了兼容性)
                record['prompt_text'] = record.pop('prompt')
                
                history.append(record)
                
            # 检查第一条记录
            if history and len(history) > 0:
                first_record = history[0]
                print(f"转换后的第一条记录键: {list(first_record.keys())}")
                for key in first_record.keys():
                    if key.startswith('ai') and key.endswith('_url'):
                        print(f"转换后 {key}: {first_record.get(key) or '空'}")
                
        except Exception as e:
            print(f"直接查询数据库出错: {e}")
            # 发生错误时回退到原来的方法
            if self.show_favorites_only:
                history = self.get_favorite_prompts()
            else:
                history = self.db_manager.get_prompt_history()
        
        # 添加历史记录项到UI
        for prompt_data in history:
            self.add_history_item(prompt_data)
    
    def clear_history_items(self):
        """清除所有历史记录项"""
        while self.content_layout.count() > 1:  # 保留最后的弹簧
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def add_history_item(self, prompt_data):
        """添加一个历史记录项"""
        item_widget = PromptItemWidget(prompt_data)
        # 连接信号
        item_widget.favorite_toggled.connect(self.on_favorite_toggled)
        item_widget.deleted.connect(self.delete_prompt)
        item_widget.copied.connect(self.copy_prompt_to_clipboard)
        item_widget.open_all_urls.connect(self.on_open_all_urls)
        item_widget.prompt_text_selected.connect(self.on_prompt_text_selected)
        
        # 添加到布局中，在弹簧之前
        self.content_layout.insertWidget(self.content_layout.count() - 1, item_widget)
    
    def get_favorite_prompts(self, limit=50):
        """获取收藏的提示词记录
        
        Args:
            limit (int): 最大记录数
            
        Returns:
            list: 收藏记录列表
        """
        # 这里假设db_manager提供了查询收藏记录的方法，如果没有，可以在这里直接执行查询
        try:
            # 直接从数据库查询收藏记录
            cursor = self.db_manager.conn.cursor()
            cursor.execute(
                """SELECT id, prompt, timestamp, favorite, 
                    ai1_url, ai2_url, ai3_url, ai4_url, ai5_url, ai6_url 
                    FROM prompt_details 
                    WHERE favorite = 1 
                    ORDER BY timestamp DESC LIMIT ?""",
                (limit,)
            )
            
            results = []
            for row in cursor.fetchall():
                # 构建与标准格式兼容的记录
                ai_targets = []
                
                # 查询当前记录的所有webview信息
                for i in range(1, 7):
                    url_key = f"ai{i}_url"
                    if url_key in row and row[url_key]:
                        # 简单提取域名
                        try:
                            domain = urlparse(row[url_key]).netloc
                            if domain.startswith('www.'):
                                domain = domain[4:]
                            if domain and domain not in ai_targets:
                                ai_targets.append(domain)
                        except:
                            ai_targets.append(f"AI{i}")
                
                # 如果没有解析到任何AI，添加一个默认值
                if not ai_targets:
                    ai_targets = ["未知AI"]
                
                # 安全处理时间戳
                try:
                    if isinstance(row['timestamp'], int) and 0 <= row['timestamp'] <= 32503680000:  # 合理的时间戳范围(1970-3000年)
                        timestamp_str = datetime.fromtimestamp(row['timestamp']).isoformat()
                    elif isinstance(row['timestamp'], str):
                        # 如果已经是字符串，直接使用
                        timestamp_str = row['timestamp']
                    else:
                        # 其他情况使用当前时间
                        timestamp_str = datetime.now().isoformat()
                except (ValueError, OSError, OverflowError) as e:
                    print(f"时间戳转换错误: {row['timestamp']}, {e}")
                    # 发生错误时使用当前时间
                    timestamp_str = datetime.now().isoformat()
                
                # 创建完整记录（包含所有URL字段）
                record = {
                    'id': row['id'],
                    'prompt_text': row['prompt'],
                    'timestamp': timestamp_str,
                    'ai_targets': ai_targets,
                    'favorite': bool(row['favorite'])
                }
                
                # 添加URL字段
                for i in range(1, 7):
                    url_key = f"ai{i}_url"
                    if url_key in row:
                        record[url_key] = row[url_key]
                
                results.append(record)
            
            return results
        except Exception as e:
            print(f"获取收藏记录失败: {e}")
            return []
    
    def search_history(self, text):
        """搜索历史记录"""
        if not text and not self.show_favorites_only:
            self.refresh_history()
            return
        
        self.clear_history_items()
        
        # 结合搜索文本和收藏过滤条件
        if self.show_favorites_only:
            # 在收藏记录中搜索
            favorites = self.get_favorite_prompts()
            results = [item for item in favorites if text.lower() in item['prompt_text'].lower()]
        else:
            # 在所有记录中搜索
            results = self.db_manager.search_prompts(text)
            
        for prompt_data in results:
            self.add_history_item(prompt_data)
    
    def toggle_favorite_filter(self, checked):
        """切换收藏过滤状态"""
        self.show_favorites_only = checked
        
        # 根据状态切换图标颜色
        if checked:
            self.favorite_filter_btn.setIcon(self.filter_star_active)
        else:
            self.favorite_filter_btn.setIcon(self.filter_star_normal)
            
        self.refresh_history()
    
    def on_favorite_toggled(self, prompt_id, is_favorite):
        """处理收藏状态变化"""
        if not prompt_id:
            return
            
        # 获取当前数据库中的收藏状态
        current_favorite_state = False
        try:
            # 从数据库查询当前收藏状态
            cursor = self.db_manager.conn.cursor()
            cursor.execute(
                "SELECT favorite FROM prompt_details WHERE id = ?",
                (prompt_id,)
            )
            row = cursor.fetchone()
            if row:
                current_favorite_state = bool(row['favorite'])
        except Exception as e:
            print(f"获取收藏状态出错: {e}")
            
        # 只有当需要切换状态时才调用toggle方法
        if current_favorite_state != is_favorite:
            # 切换数据库中的收藏状态
            self.db_manager.toggle_prompt_favorite(prompt_id)
        
        # 发射信号通知状态变化
        self.favorite_toggled.emit(prompt_id, is_favorite)
    
    def delete_prompt(self, prompt_id):
        """删除提示词记录"""
        if not prompt_id:
            return
            
        try:
            # 直接执行SQL删除语句
            cursor = self.db_manager.conn.cursor()
            cursor.execute("DELETE FROM prompt_details WHERE id = ?", (prompt_id,))
            self.db_manager.conn.commit()
            print(f"已删除提示词记录，ID: {prompt_id}")
            
            # 刷新显示
            self.refresh_history()
        except Exception as e:
            print(f"删除提示词记录失败: {e}")
            # 显示错误信息
            QMessageBox.critical(self, "删除失败", f"无法删除提示词记录：{str(e)}")
    
    def copy_prompt_to_clipboard(self, text):
        """复制提示词到剪贴板"""
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(text)
    
    def on_open_all_urls(self, urls):
        """处理打开所有链接请求"""
        if urls:
            print(f"PromptHistory: 转发打开 {len(urls)} 个链接的请求")
            self.open_urls.emit(urls)

    def on_prompt_text_selected(self, prompt_text):
        """处理提示词文本被选中
        
        Args:
            prompt_text (str): 被选中的提示词文本
        """
        if prompt_text:
            # 将请求转发给AuxiliaryWindow处理，确保检查现有内容
            self.request_set_prompt.emit(prompt_text)