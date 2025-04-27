#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QListWidget, QListWidgetItem,
                           QLineEdit, QLabel, QHBoxLayout, QPushButton, QMenu,
                           QScrollArea, QFrame, QToolButton, QSizePolicy,
                           QMessageBox, QApplication, QTabWidget)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QIcon, QColor, QAction, QPalette, QFont, QPixmap, QImage
import qtawesome as qta
from datetime import datetime
import webbrowser
from urllib.parse import urlparse
import os
import sys
from app.controllers.theme_manager import ThemeManager
import re
import json
import time
import jieba  # 用于中文分词
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import matplotlib.pyplot as plt
from wordcloud import WordCloud, STOPWORDS
import io
import tempfile

class PromptItemWidget(QWidget):
    """自定义提示词历史记录小部件"""
    
    copied = pyqtSignal(str)  # 复制提示词信号
    favorite_toggled = pyqtSignal(str, bool)  # 收藏切换信号
    deleted = pyqtSignal(str)  # 删除信号
    open_all_urls = pyqtSignal(list)  # 打开所有链接信号
    prompt_text_selected = pyqtSignal(str)  # 双击选择提示词信号
    send_prompt = pyqtSignal(str)  # 发送提示词信号
    summarize_ai_responses = pyqtSignal(str)  # 总结AI回复信号，参数为提示词ID
    
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
                # print(f"图标目录中的文件: {files}")
            else:
                print(f"图标目录不存在: {self.icon_dir}")
        except Exception as e:
            print(f"列出图标目录内容出错: {e}")
            
        self.setup_ui()
        self.update_data(prompt_data)
        
        # 获取 ThemeManager 实例 (从父级或全局)
        self.theme_manager = None
        app = QApplication.instance()
        if hasattr(app, 'theme_manager') and isinstance(app.theme_manager, ThemeManager):
             self.theme_manager = app.theme_manager
             self.theme_manager.theme_changed.connect(self.update_icons)
             self.theme_manager.theme_changed.connect(self.update_border)  # 连接边框更新
             # 初始图标颜色设置 (可能需要延迟)
             QTimer.singleShot(0, self.update_icons)
        else:
             print("警告: PromptItemWidget 无法获取 ThemeManager")
             QTimer.singleShot(0, self.update_icons) # 尝试用默认颜色更新
        
    def setup_ui(self):
        """设置UI界面"""
        # 创建外层框架布局
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)
        
        # 创建内容框架 - 这个框架将包含所有内容并有边框
        self.container_frame = QFrame()
        self.container_frame.setFrameShape(QFrame.Shape.StyledPanel)
        
        # 根据当前主题设置边框颜色
        app = QApplication.instance()
        border_color = "#4C566A"  # 深色主题默认颜色
        if hasattr(app, 'theme_manager'):
            if app.theme_manager.current_theme == "light":
                border_color = "#81A1C1"  # 浅色主题颜色
        
        self.container_frame.setStyleSheet(f"QFrame {{ border: 1px solid {border_color}; border-radius: 8px; background-color: transparent; }}")
        
        # 为内容框架创建内部布局
        inner_layout = QVBoxLayout(self.container_frame)
        inner_layout.setContentsMargins(10, 10, 10, 10)
        inner_layout.setSpacing(8)
        
        # 头部布局（时间和操作按钮）
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        
        # 时间标签
        self.time_label = QLabel()
        self.time_label.setObjectName("timeLabel") # 添加 objectName
        self.time_label.setFixedWidth(70)  # 减小宽度，因为现在是两行显示
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)  # 文本左对齐
        self.time_label.setStyleSheet("border: none;")
        header_layout.addWidget(self.time_label)
        
        # 添加一个水平框架作为图标容器
        self.icons_frame = QFrame()
        self.icons_frame.setFixedHeight(20)  # 设置为20px高度
        self.icons_frame.setStyleSheet("border: none;")
        self.icons_layout = QHBoxLayout(self.icons_frame)
        self.icons_layout.setContentsMargins(0, 0, 0, 0)
        self.icons_layout.setSpacing(4)  # 减小间距
        self.icons_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.icons_frame)
        
        # 添加弹簧
        header_layout.addStretch()
        
        # 发送按钮 - 改为普通按钮，不带下拉菜单
        self.send_btn = QToolButton()
        self.send_btn.setToolTip("发送原始提示词")
        self.send_btn.setFixedSize(QSize(20, 20))
        self.send_btn.setIconSize(QSize(16, 16))
        self.send_btn.setStyleSheet("border: none;")
        self.send_btn.clicked.connect(self.send_prompt_text)  # 直接连接发送方法
        header_layout.addWidget(self.send_btn)
        
        # 新增总结按钮
        self.summarize_btn = QToolButton()
        self.summarize_btn.setToolTip("总结AI回复")
        self.summarize_btn.setFixedSize(QSize(20, 20))
        self.summarize_btn.setIconSize(QSize(16, 16))
        self.summarize_btn.setStyleSheet("border: none;")
        self.summarize_btn.clicked.connect(self.summarize_responses)  # 直接连接总结方法
        header_layout.addWidget(self.summarize_btn)
        
        # 收藏按钮 - 使用自定义图标
        self.favorite_btn = QToolButton()
        self.favorite_btn.setToolTip("收藏提示词")
        self.favorite_btn.setFixedSize(QSize(20, 20))
        self.favorite_btn.setIconSize(QSize(16, 16))
        self.favorite_btn.setStyleSheet("border: none;")
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
        self.delete_btn.setToolTip("删除提示词")
        self.delete_btn.setFixedSize(QSize(20, 20))
        self.delete_btn.setIconSize(QSize(16, 16))
        self.delete_btn.setStyleSheet("border: none;")
        self.delete_btn.clicked.connect(self.delete_prompt)
        header_layout.addWidget(self.delete_btn)
        
        inner_layout.addLayout(header_layout)
        
        # 提示词内容
        self.content_label = QLabel()
        self.content_label.setObjectName("contentLabel") # 添加 objectName
        self.content_label.setWordWrap(True)
        self.content_label.setTextFormat(Qt.TextFormat.PlainText)
        self.content_label.setMaximumHeight(66)  # 约3行文本高度
        self.content_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.content_label.setStyleSheet("border: none;")
        inner_layout.addWidget(self.content_label)
        
        # 将内容框架添加到外层布局
        outer_layout.addWidget(self.container_frame)
        
        # 设置容器样式
        self.setMinimumHeight(110)
        self.setMaximumHeight(140)
        
    def create_ai_link_button(self, url, icon_color='#D8DEE9'):
        """创建AI链接按钮
        
        Args:
            url: AI链接URL
            icon_color: 图标颜色
            
        Returns:
            QToolButton: 创建的按钮
        """
        btn = QToolButton()
        icon = None
        
        # 使用正则表达式从URL中提取域名
        domain_match = re.search(r'https?://([^:/]+)', url)
        if domain_match:
            domain = domain_match.group(1)
        else:
            domain = ""
        
        # URL到平台标识的映射（按照一定的优先级排序）
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
        
        # 先尝试加载本地图标文件
        if ai_key:
            # 使用小写的key与文件名保持一致
            lowercase_key = ai_key.lower()
            icon_path = os.path.join(self.icon_dir, f"{lowercase_key}.png")  # 先尝试png
            
            if not os.path.exists(icon_path):
                icon_path = os.path.join(self.icon_dir, f"{lowercase_key}.ico")  # 再尝试ico
            
            if os.path.exists(icon_path):
                # 加载图标
                try:
                    if icon_path.endswith('.ico'):
                        icon = QIcon(icon_path)
                    else:
                        icon = QIcon(QPixmap(icon_path))
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
                default_color = icon_color # 使用传入的颜色
                icon = qta.icon(icon_name, color=default_color) # 使用 default_color
            except Exception as e:
                # 如果依然失败，使用最安全的图标
                print(f"qtawesome图标加载失败: {e}")
                icon = qta.icon("fa5s.globe", color=default_color) # 使用 default_color
                print("回退到默认图标: fa5s.globe")
        
        btn.setIcon(icon)
        btn.setToolTip(f"打开链接: {url}")
        
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
        self.open_all_urls.emit(urls)
    
    def update_data(self, prompt_data):
        """更新显示数据"""
        self.prompt_data = prompt_data
        
        # 调试信息：输出记录ID和提示词内容的一部分
        record_id = prompt_data.get('id', '无ID')
        prompt_text = prompt_data.get('prompt_text', '无提示词内容')
        
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
        
        # 添加AI链接按钮
        url_count = 0
        for i in range(1, 7):
            url_key = f"ai{i}_url"
            if url_key in prompt_data and prompt_data[url_key] and prompt_data[url_key].strip():
                url = prompt_data[url_key]
                # 传递当前图标颜色
                btn = self.create_ai_link_button(url, icon_color='#D8DEE9')
                self.icons_layout.addWidget(btn)
                url_count += 1
        
        # 如果有链接，添加"打开所有"按钮
        if url_count > 0:
            self.add_open_all_button()
        
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

    def send_prompt_text(self):
        """发送提示词"""
        prompt_text = self.prompt_data.get('prompt_text', '')
        if prompt_text:
            self.send_prompt.emit(prompt_text)
    
    def summarize_responses(self):
        """请求总结AI回复"""
        prompt_id = self.prompt_data.get('id')
        if prompt_id:
            print(f"请求总结AI回复，提示词ID: {prompt_id}")
            self.summarize_ai_responses.emit(prompt_id)

    def update_icons(self):
        # print("PromptItemWidget: 更新图标颜色...")
        icon_color = '#D8DEE9' # Default
        if self.theme_manager:
            theme_colors = self.theme_manager.get_current_theme_colors()
            icon_color = theme_colors.get('foreground', icon_color)
            
        # 更新按钮图标颜色
        self.send_btn.setIcon(qta.icon('fa5s.paper-plane', color=icon_color))
        self.summarize_btn.setIcon(qta.icon('fa5s.chart-bar', color=icon_color))
        self.delete_btn.setIcon(qta.icon('fa5s.trash-alt', color=icon_color))
        
        # 更新收藏按钮图标和颜色
        is_favorite = self.prompt_data.get('favorite', False)
        star_icon_name = 'fa5s.star' # 默认实心
        star_color = icon_color # 默认颜色
        if is_favorite:
             star_color = theme_colors.get('warning', '#EBCB8B') if self.theme_manager else '#EBCB8B' # 收藏用黄色
        else:
            # 尝试空星图标
            try:
                qta.icon('fa.star-o')
                star_icon_name = 'fa.star-o'
            except Exception:
                 try:
                     qta.icon('mdi.star-outline')
                     star_icon_name = 'mdi.star-outline'
                 except Exception:
                     # 使用灰色实心星
                     star_color = theme_colors.get('tertiary_bg', '#4C566A') if self.theme_manager else '#4C566A'
                     
        self.favorite_btn.setIcon(qta.icon(star_icon_name, color=star_color))
        
        # 更新AI链接按钮图标颜色 (需要重新创建或遍历)
        for i in range(self.icons_layout.count()):
            widget = self.icons_layout.itemAt(i).widget()
            if isinstance(widget, QToolButton) and hasattr(widget, 'property') and widget.property("url"): # 检查是否是AI链接按钮
                # 重新创建按钮以更新颜色 (简单但可能低效)
                # 或者直接更新图标颜色 (如果qtawesome支持)
                # 尝试直接更新颜色
                current_icon = widget.icon()
                # 假设qta.icon返回的QIcon可以通过某种方式获取原始名称和选项
                # 但标准QIcon没有这个功能，所以我们可能需要重新创建
                url = widget.property("url")
                # 重新创建按钮图标
                new_btn = self.create_ai_link_button(url, icon_color=icon_color)
                widget.setIcon(new_btn.icon()) # 只更新图标
                new_btn.deleteLater() # 删除临时按钮
            elif widget and widget.toolTip().startswith("在AI视图中打开所有链接"): # 更新打开所有按钮
                 widget.setIcon(qta.icon('fa5s.external-link-alt', color=icon_color))
                 
        # print("PromptItemWidget: 图标颜色更新完成")

    def update_border(self):
        """根据当前主题更新边框颜色"""
        border_color = "#4C566A"  # 深色主题默认颜色
        if self.theme_manager and self.theme_manager.current_theme == "light":
            border_color = "#81A1C1"  # 浅色主题颜色
            
        if hasattr(self, 'container_frame'):
            self.container_frame.setStyleSheet(f"QFrame {{ border: 1px solid {border_color}; border-radius: 8px; background-color: transparent; }}")
            print(f"PromptItemWidget: 边框颜色已更新为 {border_color}")


class PromptHistory(QWidget):
    """提示词历史记录组件"""
    
    # 定义信号
    prompt_selected = pyqtSignal(str)  # 提示词选中信号
    favorite_toggled = pyqtSignal(str, bool)  # 收藏状态切换信号，参数: prompt_id, is_favorite
    open_urls = pyqtSignal(list)  # 打开URLs信号，用于传递给AI视图
    request_set_prompt = pyqtSignal(str)  # 请求设置提示词内容，需要检查现有内容
    request_send_prompt = pyqtSignal(str)  # 请求直接发送提示词的信号
    request_summarize_responses = pyqtSignal(str)  # 请求总结AI回复的信号，参数为prompt_id
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setup_ui()
        self.refresh_history()
        
        # 获取 ThemeManager 并连接信号 (PromptItemWidget会自行处理)
        self.theme_manager = None
        app = QApplication.instance()
        if hasattr(app, 'theme_manager') and isinstance(app.theme_manager, ThemeManager):
             self.theme_manager = app.theme_manager
             self.theme_manager.theme_changed.connect(self._update_icons) # 更新自身图标
        else:
             print("警告: PromptHistory 无法获取 ThemeManager")
        # 初始调用放这里确保按钮已创建
        QTimer.singleShot(0, self._update_icons)
    
    def setup_ui(self):
        """设置UI界面"""
        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 创建标签页控件
        self.tab_widget = QTabWidget()
        self.tab_widget.setObjectName("promptHistoryTabs")
        self.tab_widget.setTabPosition(QTabWidget.TabPosition.North)
        self.tab_widget.setDocumentMode(True)  # 使标签页更现代化
        
        # 创建历史标签页
        self.history_tab = QWidget()
        self.setup_history_tab()
        self.tab_widget.addTab(self.history_tab, "历史")
        
        # 创建统计标签页
        self.stats_tab = QWidget()
        self.setup_stats_tab()
        self.tab_widget.addTab(self.stats_tab, "统计")
        
        # 将标签页控件添加到主布局
        main_layout.addWidget(self.tab_widget)
        
        # 初始化记录收藏过滤状态
        self.show_favorites_only = False
    
    def setup_history_tab(self):
        """设置历史标签页UI"""
        # 创建布局
        layout = QVBoxLayout(self.history_tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # 创建顶部工具栏
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setSpacing(8)
        
        # 创建搜索框
        self.search_input = QLineEdit()
        self.search_input.setObjectName("searchInput") # 添加 objectName
        self.search_input.setPlaceholderText("搜索历史记录...")
        self.search_input.textChanged.connect(self.search_history)
        toolbar.addWidget(self.search_input, 1)  # 搜索框占据大部分空间
        
        # 添加收藏过滤按钮 - 使用自定义图标
        self.favorite_filter_btn = QPushButton(self)
        self.favorite_filter_btn.setObjectName("favoriteFilterBtn") # 添加 objectName
        self.favorite_filter_btn.setToolTip("显示收藏的提示词")
        self.favorite_filter_btn.setCheckable(True)
        self.favorite_filter_btn.clicked.connect(self.toggle_favorite_filter)
        toolbar.addWidget(self.favorite_filter_btn)
        
        # 添加刷新按钮
        self.refresh_btn = QPushButton(self)
        self.refresh_btn.setObjectName("refreshBtn") # 添加 objectName
        self.refresh_btn.setToolTip("刷新历史记录")
        self.refresh_btn.clicked.connect(self.refresh_history)
        toolbar.addWidget(self.refresh_btn)
        
        # 添加工具栏到主布局
        layout.addLayout(toolbar)
        
        # 创建滚动区域和内容容器
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # 创建容器小部件用于存放历史记录项
        self.content_widget = QWidget()
        self.content_widget.setObjectName("contentWidget") # 添加 objectName
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(10, 10, 10, 10)
        self.content_layout.setSpacing(8)  # 设置条目之间的间距
        self.content_layout.addStretch()  # 添加弹簧，使条目靠上排列
        
        self.scroll_area.setWidget(self.content_widget)
        layout.addWidget(self.scroll_area)
    
    def setup_stats_tab(self):
        """设置统计标签页UI"""
        # 创建布局
        layout = QVBoxLayout(self.stats_tab)
        layout.setContentsMargins(3, 3, 3, 3)  # 进一步减小边距
        layout.setSpacing(3)  # 进一步减小间距
        
        # 基本统计部分
        stats_header = QLabel("基本统计")
        stats_header.setObjectName("statsHeader")
        stats_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stats_header.setStyleSheet("font-weight: bold; font-size: 14px; border-bottom: 1px solid #ccc; padding-bottom: 3px;")
        layout.addWidget(stats_header)
        
        # 四个统计方块容器
        stats_blocks = QHBoxLayout()
        stats_blocks.setSpacing(3)  # 进一步减小间距
        
        # 今日统计
        daily_block = QFrame()
        daily_block.setObjectName("dailyStatsBlock")
        daily_block.setFrameShape(QFrame.Shape.StyledPanel)
        daily_block.setStyleSheet("border: 1px solid #ccc; border-radius: 4px;")
        daily_layout = QVBoxLayout(daily_block)
        daily_layout.setContentsMargins(2, 2, 2, 2)  # 进一步减小内边距
        
        self.daily_count = QLabel("0")  # 修改为实例变量
        self.daily_count.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.daily_count.setStyleSheet("font-size: 20px; font-weight: bold; color: #8FBCBB;")
        
        daily_label = QLabel("今日")
        daily_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        daily_label.setStyleSheet("font-size: 11px;")
        
        daily_layout.addWidget(self.daily_count)
        daily_layout.addWidget(daily_label)
        stats_blocks.addWidget(daily_block)
        
        # 本周统计
        weekly_block = QFrame()
        weekly_block.setObjectName("weeklyStatsBlock")
        weekly_block.setFrameShape(QFrame.Shape.StyledPanel)
        weekly_block.setStyleSheet("border: 1px solid #ccc; border-radius: 4px;")
        weekly_layout = QVBoxLayout(weekly_block)
        weekly_layout.setContentsMargins(2, 2, 2, 2)  # 进一步减小内边距
        
        self.weekly_count = QLabel("0")  # 修改为实例变量
        self.weekly_count.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.weekly_count.setStyleSheet("font-size: 20px; font-weight: bold; color: #81A1C1;")
        
        weekly_label = QLabel("本周")
        weekly_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        weekly_label.setStyleSheet("font-size: 11px;")
        
        weekly_layout.addWidget(self.weekly_count)
        weekly_layout.addWidget(weekly_label)
        stats_blocks.addWidget(weekly_block)
        
        # 本月统计
        monthly_block = QFrame()
        monthly_block.setObjectName("monthlyStatsBlock")
        monthly_block.setFrameShape(QFrame.Shape.StyledPanel)
        monthly_block.setStyleSheet("border: 1px solid #ccc; border-radius: 4px;")
        monthly_layout = QVBoxLayout(monthly_block)
        monthly_layout.setContentsMargins(2, 2, 2, 2)  # 进一步减小内边距
        
        self.monthly_count = QLabel("0")  # 修改为实例变量，设置初始值为0
        self.monthly_count.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.monthly_count.setStyleSheet("font-size: 20px; font-weight: bold; color: #D08770;")
        
        monthly_label = QLabel("本月")
        monthly_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        monthly_label.setStyleSheet("font-size: 11px;")
        
        monthly_layout.addWidget(self.monthly_count)
        monthly_layout.addWidget(monthly_label)
        stats_blocks.addWidget(monthly_block)
        
        # 总计统计
        total_block = QFrame()
        total_block.setObjectName("totalStatsBlock")
        total_block.setFrameShape(QFrame.Shape.StyledPanel)
        total_block.setStyleSheet("border: 1px solid #ccc; border-radius: 4px;")
        total_layout = QVBoxLayout(total_block)
        total_layout.setContentsMargins(2, 2, 2, 2)  # 进一步减小内边距
        
        self.total_count = QLabel("0")  # 修改为实例变量，设置初始值为0
        self.total_count.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.total_count.setStyleSheet("font-size: 20px; font-weight: bold; color: #B48EAD;")
        
        total_label = QLabel("总计")
        total_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        total_label.setStyleSheet("font-size: 11px;")
        
        total_layout.addWidget(self.total_count)
        total_layout.addWidget(total_label)
        stats_blocks.addWidget(total_block)
        
        layout.addLayout(stats_blocks)
        
        # 对话趋势部分
        trends_header = QLabel("对话趋势")
        trends_header.setObjectName("trendsHeader")
        trends_header.setAlignment(Qt.AlignmentFlag.AlignCenter)  # 确保标题居中
        trends_header.setStyleSheet("font-weight: bold; font-size: 14px; padding: 3px 0;")
        layout.addWidget(trends_header)
        
        # 时间范围选择按钮组
        time_range_layout = QHBoxLayout()
        time_range_layout.setSpacing(1)  # 进一步减小按钮间距
        
        button_style = "QPushButton { padding: 2px 4px; font-size: 11px; }"
        active_style = "QPushButton { background-color: #5A9F5A; color: white; padding: 2px 4px; font-size: 11px; }"
        
        self.day_btn = QPushButton("日")  # 修改为实例变量
        self.day_btn.setObjectName("dayRangeBtn")
        self.day_btn.setCheckable(True)
        self.day_btn.setStyleSheet(button_style)
        self.day_btn.clicked.connect(lambda: self.update_trend_chart('day'))  # 连接更新图表方法
        time_range_layout.addWidget(self.day_btn)
        
        self.week_btn = QPushButton("周")  # 修改为实例变量
        self.week_btn.setObjectName("weekRangeBtn")
        self.week_btn.setCheckable(True)
        self.week_btn.setStyleSheet(button_style)
        self.week_btn.clicked.connect(lambda: self.update_trend_chart('week'))  # 连接更新图表方法
        time_range_layout.addWidget(self.week_btn)
        
        self.month_btn = QPushButton("月")  # 修改为实例变量
        self.month_btn.setObjectName("monthRangeBtn")
        self.month_btn.setCheckable(True)
        self.month_btn.setChecked(True)
        self.month_btn.setStyleSheet(active_style)
        self.month_btn.clicked.connect(lambda: self.update_trend_chart('month'))  # 连接更新图表方法
        time_range_layout.addWidget(self.month_btn)
        
        self.all_btn = QPushButton("全部")  # 修改为实例变量
        self.all_btn.setObjectName("allRangeBtn")
        self.all_btn.setCheckable(True)
        self.all_btn.setStyleSheet(button_style)
        self.all_btn.clicked.connect(lambda: self.update_trend_chart('all'))  # 连接更新图表方法
        time_range_layout.addWidget(self.all_btn)
        
        # 添加刷新按钮
        self.refresh_stats_btn = QPushButton()  # 修改为实例变量
        self.refresh_stats_btn.setObjectName("refreshStatsBtn")
        self.refresh_stats_btn.setToolTip("刷新统计数据")
        self.refresh_stats_btn.setFixedSize(20, 20)  # 减小按钮尺寸
        self.refresh_stats_btn.clicked.connect(self.refresh_statistics)  # 连接刷新方法
        time_range_layout.addWidget(self.refresh_stats_btn)
        
        layout.addLayout(time_range_layout)
        
        # 趋势图表占位符
        self.trends_chart = QLabel("加载中...")  # 修改为实例变量
        self.trends_chart.setObjectName("trendsChart")
        self.trends_chart.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.trends_chart.setStyleSheet("border: 1px solid #ccc; border-radius: 6px; padding: 5px; background-color: #f5f5f5;")
        self.trends_chart.setMinimumHeight(120)  # 进一步减小最小高度
        self.trends_chart.setMinimumWidth(0)  # 允许完全缩小宽度
        layout.addWidget(self.trends_chart)
        
        # 历史对话词云部分
        wordcloud_header = QLabel("历史对话词云")
        wordcloud_header.setObjectName("wordcloudHeader")
        wordcloud_header.setAlignment(Qt.AlignmentFlag.AlignCenter)  # 确保标题居中
        wordcloud_header.setStyleSheet("font-weight: bold; font-size: 14px; padding: 3px 0;")
        layout.addWidget(wordcloud_header)
        
        # 时间范围选择按钮组 (词云)
        wc_time_range_layout = QHBoxLayout()
        wc_time_range_layout.setSpacing(1)  # 减小按钮间距
        
        self.wc_day_btn = QPushButton("日")  # 修改为实例变量
        self.wc_day_btn.setObjectName("wcDayRangeBtn")
        self.wc_day_btn.setCheckable(True)
        self.wc_day_btn.setStyleSheet(button_style)
        self.wc_day_btn.clicked.connect(lambda: self.update_word_cloud('day'))  # 连接更新方法
        wc_time_range_layout.addWidget(self.wc_day_btn)
        
        self.wc_week_btn = QPushButton("周")  # 修改为实例变量
        self.wc_week_btn.setObjectName("wcWeekRangeBtn")
        self.wc_week_btn.setCheckable(True)
        self.wc_week_btn.setStyleSheet(button_style)
        self.wc_week_btn.clicked.connect(lambda: self.update_word_cloud('week'))  # 连接更新方法
        wc_time_range_layout.addWidget(self.wc_week_btn)
        
        self.wc_month_btn = QPushButton("月")  # 修改为实例变量
        self.wc_month_btn.setObjectName("wcMonthRangeBtn")
        self.wc_month_btn.setCheckable(True)
        self.wc_month_btn.setStyleSheet(button_style)
        self.wc_month_btn.clicked.connect(lambda: self.update_word_cloud('month'))  # 连接更新方法
        wc_time_range_layout.addWidget(self.wc_month_btn)
        
        self.wc_all_btn = QPushButton("全部")  # 修改为实例变量
        self.wc_all_btn.setObjectName("wcAllRangeBtn")
        self.wc_all_btn.setCheckable(True)
        self.wc_all_btn.setChecked(True)
        self.wc_all_btn.setStyleSheet(active_style)
        self.wc_all_btn.clicked.connect(lambda: self.update_word_cloud('all'))  # 连接更新方法
        wc_time_range_layout.addWidget(self.wc_all_btn)
        
        # 添加刷新按钮
        self.refresh_wordcloud_btn = QPushButton()  # 修改为实例变量
        self.refresh_wordcloud_btn.setObjectName("refreshWordcloudBtn")
        self.refresh_wordcloud_btn.setToolTip("刷新词云数据")
        self.refresh_wordcloud_btn.setFixedSize(20, 20)  # 减小按钮尺寸
        self.refresh_wordcloud_btn.clicked.connect(self.refresh_word_cloud)  # 连接刷新词云方法
        wc_time_range_layout.addWidget(self.refresh_wordcloud_btn)
        
        layout.addLayout(wc_time_range_layout)
        
        # 创建词云图占位符
        self.word_cloud = QLabel("加载中...")  # 修改变量名为 word_cloud
        self.word_cloud.setObjectName("wordcloudChart")
        self.word_cloud.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.word_cloud.setStyleSheet("border: 1px solid #ccc; border-radius: 6px; padding: 5px; background-color: #f5f5f5;")
        self.word_cloud.setMinimumHeight(120)  # 进一步减小最小高度
        self.word_cloud.setMinimumWidth(0)  # 允许完全缩小宽度
        layout.addWidget(self.word_cloud)
        
        # 设置图标
        QTimer.singleShot(0, self.update_stats_icons)
        
        # 初始加载统计数据
        QTimer.singleShot(100, self.refresh_statistics)
    
    def update_stats_icons(self):
        """更新统计页面的图标"""
        icon_color = '#D8DEE9'  # 默认颜色
        if self.theme_manager:
            theme_colors = self.theme_manager.get_current_theme_colors()
            icon_color = theme_colors.get('foreground', icon_color)
        
        # 为统计页面的刷新按钮设置图标
        refresh_stats_btn = self.stats_tab.findChild(QPushButton, "refreshStatsBtn")
        if refresh_stats_btn:
            refresh_stats_btn.setIcon(qta.icon('fa5s.sync', color=icon_color))
        
        refresh_wordcloud_btn = self.stats_tab.findChild(QPushButton, "refreshWordcloudBtn")
        if refresh_wordcloud_btn:
            refresh_wordcloud_btn.setIcon(qta.icon('fa5s.sync', color=icon_color))

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
        item_widget.send_prompt.connect(self.on_send_prompt)
        item_widget.summarize_ai_responses.connect(self.on_summarize_ai_responses)
        
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
        
        # 根据状态切换图标颜色（现在由 _update_icons 处理）
        # if checked:
        #     self.favorite_filter_btn.setIcon(self.filter_star_active)
        # else:
        #     self.favorite_filter_btn.setIcon(self.filter_star_normal)
            
        self._update_icons() # 调用更新确保按钮图标颜色正确
            
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
            
    def on_send_prompt(self, prompt_text):
        """处理发送提示词请求
        
        Args:
            prompt_text (str): 要发送的提示词文本
        """
        if prompt_text:
            # 直接转发提示词到辅助窗口处理
            self.request_send_prompt.emit(prompt_text)
            print(f"请求发送提示词: {prompt_text[:30]}...")
            
    def on_summarize_ai_responses(self, prompt_id):
        """处理总结AI回复请求
        
        Args:
            prompt_id (str): 提示词ID
        """
        if not prompt_id:
            print("无效的提示词ID，无法总结AI回复")
            return
            
        print(f"准备总结提示词ID为 {prompt_id} 的AI回复")
        
        # 转发请求到辅助窗口处理
        self.request_summarize_responses.emit(prompt_id)

    def _update_icons(self):
        print("PromptHistory: 更新自身图标颜色...")
        icon_color = '#D8DEE9' # Default
        active_color = '#EBCB8B' # Default Yellow for active filter
        
        if self.theme_manager:
            theme_colors = self.theme_manager.get_current_theme_colors()
            icon_color = theme_colors.get('foreground', icon_color)
            active_color = theme_colors.get('warning', active_color)
            
        # 更新刷新按钮图标
        if hasattr(self, 'refresh_btn'): # 需要保存引用
            self.refresh_btn.setIcon(qta.icon('fa5s.sync', color=icon_color))
            
        # 更新收藏过滤按钮图标
        if hasattr(self, 'favorite_filter_btn'):
            if self.favorite_filter_btn.isChecked():
                self.favorite_filter_btn.setIcon(qta.icon('fa5s.star', color=active_color))
            else:
                 self.favorite_filter_btn.setIcon(qta.icon('fa5s.star', color=icon_color))
        
        # 更新统计页面图标
        self.update_stats_icons()
                 
        print("PromptHistory: 自身图标颜色更新完成")

    def refresh_statistics(self):
        """刷新所有统计数据"""
        print("刷新统计数据...")
        try:
            self.update_basic_stats()
            self.update_trend_chart('month')  # 默认显示月视图
            self.update_word_cloud('all')     # 默认显示全部词云
        except Exception as e:
            print(f"刷新统计数据出错: {e}")
            import traceback
            traceback.print_exc()
            
    def update_basic_stats(self):
        """更新基本统计数据"""
        try:
            # 获取今日、本周、本月和总计的统计数据
            daily, weekly, monthly, total = self.get_prompt_stats()
            
            # 更新显示
            self.daily_count.setText(str(daily))
            self.weekly_count.setText(str(weekly))
            self.monthly_count.setText(str(monthly))
            self.total_count.setText(str(total))
            
            print(f"统计数据已更新: 今日={daily}, 本周={weekly}, 本月={monthly}, 总计={total}")
        except Exception as e:
            print(f"更新基本统计数据出错: {e}")
            
    def get_prompt_stats(self):
        """获取提示词统计数据
        
        Returns:
            tuple: (今日数量, 本周数量, 本月数量, 总计数量)
        """
        try:
            cursor = self.db_manager.conn.cursor()
            
            # 获取今日数量
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM prompt_details 
                WHERE date(datetime(timestamp, 'unixepoch')) = date('now')
            """)
            daily = cursor.fetchone()['count']
            
            # 获取本周数量
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM prompt_details 
                WHERE strftime('%Y-%W', datetime(timestamp, 'unixepoch')) = strftime('%Y-%W', 'now')
            """)
            weekly = cursor.fetchone()['count']
            
            # 获取本月数量
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM prompt_details 
                WHERE strftime('%Y-%m', datetime(timestamp, 'unixepoch')) = strftime('%Y-%m', 'now')
            """)
            monthly = cursor.fetchone()['count']
            
            # 获取总计数量
            cursor.execute("SELECT COUNT(*) as count FROM prompt_details")
            total = cursor.fetchone()['count']
            
            return daily, weekly, monthly, total
            
        except Exception as e:
            print(f"获取提示词统计数据出错: {e}")
            import traceback
            traceback.print_exc()
            return 0, 0, 0, 0
            
    def update_trend_chart(self, time_range):
        """更新趋势图表
        
        Args:
            time_range (str): 'day', 'week', 'month', 'all'
        """
        try:
            title, data = None, None
            
            # 根据选择的时间范围获取不同的趋势数据
            if time_range == 'day':
                title, data = self.get_daily_trend()
                x_label = '小时'
                x_values = [item['hour'] for item in data]
                y_values = [item['count'] for item in data]
            elif time_range == 'week':
                title, data = self.get_weekly_trend()
                x_label = '星期'
                x_values = [item['day'] for item in data]
                y_values = [item['count'] for item in data]
            elif time_range == 'month':
                title, data = self.get_monthly_trend()
                x_label = '日期'
                x_values = [item['day'] for item in data]
                y_values = [item['count'] for item in data]
            elif time_range == 'all':
                title, data = self.get_all_time_trend()
                x_label = '月份'
                x_values = [item['month'] for item in data]
                y_values = [item['count'] for item in data]
            else:
                # 默认显示月视图
                title, data = self.get_monthly_trend()
                x_label = '日期'
                x_values = [item['day'] for item in data]
                y_values = [item['count'] for item in data]
                
            # 更新趋势按钮状态
            self._update_trend_buttons(time_range)
                
            # 创建趋势图表
            if title and data:
                self._create_trend_chart(title, x_label, x_values, y_values, time_range)
            
        except Exception as e:
            print(f"更新趋势图表出错: {e}")
            import traceback
            traceback.print_exc()
    
    def _create_trend_chart(self, title, x_label, x_values, y_values, time_range):
        """创建趋势图表
        
        Args:
            title (str): 图表标题
            x_label (str): x轴标签
            x_values (list): x轴数据
            y_values (list): y轴数据
            time_range (str): 时间范围('day', 'week', 'month', 'all')
        """
        try:
            # 如果没有数据，显示提示信息
            if not x_values or not y_values:
                self.trends_chart.setText(f"没有{title}的趋势数据")
                return
                
            # 设置中文字体
            plt.rcParams['font.sans-serif'] = ['SimHei']  # 设置字体为黑体
            plt.rcParams['axes.unicode_minus'] = False    # 正常显示负号
            
            # 使用主题颜色并确保正确应用
            theme_colors = self.theme_manager.get_current_theme_colors() if self.theme_manager else {}
            
            # 背景始终为白色，所以文字始终使用黑色
            text_color = '#000000'  # 始终使用黑色文字
            line_color = '#5E81AC'  # 线条颜色
            highlight_color = '#EBCB8B'  # 高亮色保持醒目
            axis_color = '#2E3440'  # 轴线颜色
            grid_color = '#CCCCCC'  # 网格线颜色
            
            # 创建图表 - 使用更小的宽度
            fig = Figure(figsize=(4.5, 2.4), dpi=90)
            fig.patch.set_facecolor('none')  # 透明背景
            canvas = FigureCanvas(fig)
            ax = fig.add_subplot(111)
            ax.set_facecolor('white')  # 始终使用白色背景
            
            # 数据点
            x_indices = range(len(x_values))
            
            # 优化横坐标显示 - 仅显示部分刻度
            show_indices = []
            show_labels = []
            
            # 根据数据量确定采样间隔
            if time_range == 'month' and len(x_values) > 15:
                # 月视图：每5天显示一个刻度
                interval = 5
            elif time_range == 'day' and len(x_values) > 12:
                # 日视图：每4小时显示一个刻度
                interval = 4
            elif len(x_values) > 20:
                # 数据量大时增加间隔
                interval = 5
            elif len(x_values) > 10:
                # 中等数据量
                interval = 3
            else:
                # 数据量小时显示所有
                interval = 1
            
            # 生成要显示的刻度和标签
            for i, x in enumerate(x_values):
                # 始终显示第一个和最后一个，以及符合间隔的刻度
                if i == 0 or i == len(x_values) - 1 or i % interval == 0:
                    show_indices.append(i)
                    
                    # 将数字去掉前导零
                    if time_range == 'month' and len(x) == 2 and x.isdigit():
                        show_labels.append(str(int(x)))
                    elif time_range == 'day' and len(x) == 2 and x.isdigit():
                        show_labels.append(str(int(x)))
                    else:
                        show_labels.append(x)
            
            # 绘制折线图 - 增加线条粗细和对比度
            ax.plot(x_indices, y_values, marker='o', markersize=4, 
                   linewidth=2.0, color=line_color, alpha=0.9)
            
            # 添加数据点标记
            for i, v in enumerate(y_values):
                if v > 0:  # 只标记非零值
                    # 找出最大值进行高亮
                    if v == max(y_values):
                        ax.plot(i, v, marker='o', markersize=6, 
                               color=highlight_color, alpha=1.0)
            
            # 设置标题和轴标签 - 进一步增大字体提高可读性
            ax.set_title(title, fontsize=12, color=text_color, fontweight='bold')
            ax.set_xlabel(x_label, fontsize=10, color=text_color)
            ax.set_ylabel('对话数量', fontsize=10, color=text_color)
            
            # 设置x轴刻度和标签 - 增大字体，加粗
            ax.set_xticks(show_indices)
            ax.set_xticklabels(show_labels, rotation=45 if len(show_labels) > 10 else 0, 
                              fontsize=9, color=text_color, ha='right', fontweight='bold')
            
            # 设置y轴刻度字体更大更粗
            for label in ax.get_yticklabels():
                label.set_fontsize(9)
                label.set_fontweight('bold')
                label.set_color(text_color)
            
            # 减少y轴刻度数量
            if max(y_values) > 10:
                ax.yaxis.set_major_locator(plt.MaxNLocator(5))  # 最多显示5个刻度
            
            # 设置网格和调整布局
            ax.grid(True, linestyle='--', alpha=0.3, color=grid_color, linewidth=0.8)  # 使用灰色网格线
            
            # 增强坐标轴线的粗细和颜色
            ax.tick_params(axis='both', colors=text_color, labelsize=9, width=1.2, length=5)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            
            # 增强可见轴线的粗细
            for spine in ['bottom', 'left']:
                ax.spines[spine].set_linewidth(1.5)
                ax.spines[spine].set_color(axis_color)
            
            # 调整y轴起始位置为0
            if min(y_values) >= 0:
                ax.set_ylim(bottom=0)
                
            fig.tight_layout(pad=0.4)  # 内边距稍微增加
            
            # 保存到临时文件
            tmp_dir = tempfile.gettempdir()
            tmp_file = os.path.join(tmp_dir, f'trend_chart_{os.getpid()}.png')
            fig.savefig(tmp_file, transparent=True, bbox_inches='tight', pad_inches=0.05)
            plt.close(fig)
            
            # 设置图表显示
            pixmap = QPixmap(tmp_file)
            self.trends_chart.setPixmap(pixmap)
            self.trends_chart.setScaledContents(True)  # 设置为自动缩放内容
            self.trends_chart.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # 删除临时文件
            try:
                os.remove(tmp_file)
            except:
                pass
                
        except Exception as e:
            print(f"创建趋势图表出错: {e}")
            import traceback
            traceback.print_exc()
            self.trends_chart.setText(f"创建{title}图表出错: {str(e)}")
    
    def update_word_cloud(self, time_range):
        """更新词云图表
        
        Args:
            time_range (str): 'day', 'week', 'month', 'all'
        """
        try:
            # 更新按钮状态
            self._update_wordcloud_buttons(time_range)
            
            # 获取指定时间范围内的提示词文本
            cursor = self.db_manager.conn.cursor()
            
            if time_range == 'day':
                cursor.execute("""
                    SELECT prompt 
                    FROM prompt_details 
                    WHERE date(datetime(timestamp, 'unixepoch')) = date('now')
                """)
                title = "今日词云"
            elif time_range == 'week':
                cursor.execute("""
                    SELECT prompt 
                    FROM prompt_details 
                    WHERE strftime('%Y-%W', datetime(timestamp, 'unixepoch')) = strftime('%Y-%W', 'now')
                """)
                title = "本周词云"
            elif time_range == 'month':
                cursor.execute("""
                    SELECT prompt 
                    FROM prompt_details 
                    WHERE strftime('%Y-%m', datetime(timestamp, 'unixepoch')) = strftime('%Y-%m', 'now')
                """)
                title = "本月词云"
            else:  # 'all'
                cursor.execute("SELECT prompt FROM prompt_details")
                title = "全部词云"
                
            # 获取所有提示词文本
            prompts = cursor.fetchall()
            all_text = " ".join([p['prompt'] for p in prompts if p['prompt']])
            
            # 创建并显示词云
            self._create_word_cloud(title, all_text)
            
        except Exception as e:
            print(f"更新词云出错: {e}")
            import traceback
            traceback.print_exc()
            
    def _create_word_cloud(self, title, text):
        """创建词云图表
        
        Args:
            title (str): 词云标题
            text (str): 用于生成词云的文本
        """
        try:
            # 如果没有文本，显示提示信息
            if not text or len(text.strip()) < 10:
                self.word_cloud.setText(f"没有足够的文本生成{title}")
                return
                
            # 设置中文字体和停用词
            plt.rcParams['font.sans-serif'] = ['SimHei']
            plt.rcParams['axes.unicode_minus'] = False
            
            # 使用主题颜色
            theme_colors = self.theme_manager.get_current_theme_colors() if self.theme_manager else {}
            
            # 始终使用白色背景和黑色文字
            background_color = 'white'
            text_color = '#000000'  # 使用黑色文字
            
            # 中文分词
            words = jieba.cut(text)
            word_text = " ".join(words)
            
            # 添加停用词
            stopwords = set(STOPWORDS)
            stopwords.update(['的', '了', '和', '是', '在', '我', '你', '他', '她', '它', '们',
                              '这', '那', '有', '就', '不', '人', '都', '一', '啊', '吗',
                              '可以', '什么', '为什么', '怎么', '如何', '请', '需要'])
            
            # 生成词云 - 适应容器宽度
            wordcloud = WordCloud(
                font_path='simhei.ttf',  # 设置中文字体，根据系统可用字体调整
                background_color=background_color,
                max_words=50,  # 词数量保持适中
                width=600,  # 增加宽度使其更加填充
                height=300,  # 调整高度
                stopwords=stopwords,
                contour_width=1,
                contour_color=text_color,
                colormap='viridis',
                min_font_size=8,  # 设置最小字体大小
                max_font_size=36  # 限制最大字体大小
            ).generate(word_text)
            
            # 创建图表 - 调整宽度
            fig = Figure(figsize=(4.5, 2.8), dpi=90)
            fig.patch.set_facecolor('none')
            canvas = FigureCanvas(fig)
            ax = fig.add_subplot(111)
            ax.set_facecolor('white')  # 始终使用白色背景
            
            # 显示词云
            ax.imshow(wordcloud, interpolation='bilinear')
            ax.set_title(title, fontsize=11, color=text_color, fontweight='bold')  # 增大字体
            ax.axis('off')  # 隐藏坐标轴
            fig.tight_layout(pad=0.2)  # 减少内边距
            
            # 保存到临时文件
            tmp_dir = tempfile.gettempdir()
            tmp_file = os.path.join(tmp_dir, f'wordcloud_{os.getpid()}.png')
            fig.savefig(tmp_file, transparent=True, bbox_inches='tight', pad_inches=0.05)
            plt.close(fig)
            
            # 设置图表显示
            pixmap = QPixmap(tmp_file)
            self.word_cloud.setPixmap(pixmap)
            self.word_cloud.setScaledContents(True)  # 设置为自动缩放内容
            self.word_cloud.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # 删除临时文件
            try:
                os.remove(tmp_file)
            except:
                pass
                
        except Exception as e:
            print(f"创建词云出错: {e}")
            import traceback
            traceback.print_exc()
            self.word_cloud.setText(f"创建{title}出错: {str(e)}")

    def _update_trend_buttons(self, selected):
        """更新趋势按钮选中状态
        
        Args:
            selected (str): 选中的按钮，'day', 'week', 'month', 或 'all'
        """
        buttons = {
            'day': self.day_btn,
            'week': self.week_btn,
            'month': self.month_btn,
            'all': self.all_btn
        }
        
        # 更新所有按钮的样式
        for name, btn in buttons.items():
            if name == selected:
                btn.setChecked(True)
                btn.setStyleSheet("background-color: #5A9F5A; color: white;")
            else:
                btn.setChecked(False)
                btn.setStyleSheet("")
                
    def get_daily_trend(self):
        """获取今日趋势数据（按小时）
        
        Returns:
            tuple: (标题, 数据列表)
        """
        try:
            cursor = self.db_manager.conn.cursor()
            
            # 查询今日每小时的对话数量
            cursor.execute("""
                SELECT strftime('%H', datetime(timestamp, 'unixepoch')) as hour,
                       COUNT(*) as count
                FROM prompt_details
                WHERE date(datetime(timestamp, 'unixepoch')) = date('now')
                GROUP BY hour
                ORDER BY hour
            """)
            
            results = cursor.fetchall()
            
            # 格式化结果，确保24小时都有数据
            data = []
            for hour in range(24):
                hour_str = f"{hour:02d}"
                count = 0
                
                # 查找当前小时的数据
                for row in results:
                    if row['hour'] == hour_str:
                        count = row['count']
                        break
                
                data.append({
                    'hour': hour_str,
                    'count': count
                })
            
            return "今日对话趋势", data
            
        except Exception as e:
            print(f"获取今日趋势数据出错: {e}")
            import traceback
            traceback.print_exc()
            return "今日对话趋势", []
    
    def get_weekly_trend(self):
        """获取本周趋势数据（按天）
        
        Returns:
            tuple: (标题, 数据列表)
        """
        try:
            cursor = self.db_manager.conn.cursor()
            
            # 查询本周每天的对话数量
            cursor.execute("""
                SELECT strftime('%w', datetime(timestamp, 'unixepoch')) as day_of_week,
                       COUNT(*) as count
                FROM prompt_details
                WHERE strftime('%Y-%W', datetime(timestamp, 'unixepoch')) = strftime('%Y-%W', 'now')
                GROUP BY day_of_week
                ORDER BY day_of_week
            """)
            
            results = cursor.fetchall()
            
            # 星期几的中文表示
            weekday_names = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"]
            
            # 格式化结果，确保一周七天都有数据
            data = []
            for day in range(7):
                day_str = str(day)
                count = 0
                
                # 查找当前日期的数据
                for row in results:
                    if row['day_of_week'] == day_str:
                        count = row['count']
                        break
                
                data.append({
                    'day': weekday_names[day],
                    'count': count
                })
            
            return "本周对话趋势", data
            
        except Exception as e:
            print(f"获取本周趋势数据出错: {e}")
            import traceback
            traceback.print_exc()
            return "本周对话趋势", []
    
    def get_monthly_trend(self):
        """获取本月趋势数据（按天）
        
        Returns:
            tuple: (标题, 数据列表)
        """
        try:
            cursor = self.db_manager.conn.cursor()
            
            # 获取当前月份的天数
            cursor.execute("SELECT strftime('%d', 'now', 'start of month', '+1 month', '-1 day') as days_in_month")
            days_in_month = int(cursor.fetchone()['days_in_month'])
            
            # 查询本月每天的对话数量
            cursor.execute("""
                SELECT strftime('%d', datetime(timestamp, 'unixepoch')) as day,
                       COUNT(*) as count
                FROM prompt_details
                WHERE strftime('%Y-%m', datetime(timestamp, 'unixepoch')) = strftime('%Y-%m', 'now')
                GROUP BY day
                ORDER BY day
            """)
            
            results = cursor.fetchall()
            
            # 格式化结果，确保本月每天都有数据
            data = []
            for day in range(1, days_in_month + 1):
                day_str = f"{day:02d}"
                count = 0
                
                # 查找当前日期的数据
                for row in results:
                    if row['day'] == day_str:
                        count = row['count']
                        break
                
                data.append({
                    'day': day_str,
                    'count': count
                })
            
            return "本月对话趋势", data
            
        except Exception as e:
            print(f"获取本月趋势数据出错: {e}")
            import traceback
            traceback.print_exc()
            return "本月对话趋势", []
    
    def get_all_time_trend(self):
        """获取所有时间趋势数据（按月）
        
        Returns:
            tuple: (标题, 数据列表)
        """
        try:
            cursor = self.db_manager.conn.cursor()
            
            # 查询每月的对话数量
            cursor.execute("""
                SELECT strftime('%Y-%m', datetime(timestamp, 'unixepoch')) as month,
                       COUNT(*) as count
                FROM prompt_details
                GROUP BY month
                ORDER BY month
            """)
            
            results = cursor.fetchall()
            
            # 格式化结果
            data = []
            for row in results:
                data.append({
                    'month': row['month'],
                    'count': row['count']
                })
            
            return "全部对话趋势", data
            
        except Exception as e:
            print(f"获取全部趋势数据出错: {e}")
            import traceback
            traceback.print_exc()
            return "全部对话趋势", []

    def _update_wordcloud_buttons(self, selected):
        """更新词云按钮选中状态
        
        Args:
            selected (str): 选中的按钮，'day', 'week', 'month', 或  'all'
        """
        buttons = {
            'day': self.wc_day_btn,
            'week': self.wc_week_btn,
            'month': self.wc_month_btn,
            'all': self.wc_all_btn
        }
        
        # 更新所有按钮的样式
        for name, btn in buttons.items():
            if name == selected:
                btn.setChecked(True)
                btn.setStyleSheet("background-color: #5A9F5A; color: white;")
            else:
                btn.setChecked(False)
                btn.setStyleSheet("")
                
    def refresh_word_cloud(self):
        """刷新词云数据"""
        # 获取当前选中的时间范围
        if self.wc_day_btn.isChecked():
            time_range = 'day'
        elif self.wc_week_btn.isChecked():
            time_range = 'week'
        elif self.wc_month_btn.isChecked():
            time_range = 'month'
        else:
            time_range = 'all'
            
        self.update_word_cloud(time_range)

    def get_statistics(self):
        """获取对话统计数据
        
        Returns:
            dict: 包含今日、本周、本月和总计的对话数量
        """
        try:
            cursor = self.db_manager.conn.cursor()
            stats = {
                'today': 0,
                'week': 0,
                'month': 0,
                'total': 0
            }
            
            # 获取今日对话数量
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM prompt_details
                WHERE date(datetime(timestamp, 'unixepoch')) = date('now')
            """)
            stats['today'] = cursor.fetchone()['count']
            
            # 获取本周对话数量
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM prompt_details
                WHERE strftime('%Y-%W', datetime(timestamp, 'unixepoch')) = strftime('%Y-%W', 'now')
            """)
            stats['week'] = cursor.fetchone()['count']
            
            # 获取本月对话数量
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM prompt_details
                WHERE strftime('%Y-%m', datetime(timestamp, 'unixepoch')) = strftime('%Y-%m', 'now')
            """)
            stats['month'] = cursor.fetchone()['count']
            
            # 获取总对话数量
            cursor.execute("SELECT COUNT(*) as count FROM prompt_details")
            stats['total'] = cursor.fetchone()['count']
            
            return stats
            
        except Exception as e:
            print(f"获取统计数据出错: {e}")
            import traceback
            traceback.print_exc()
            return {'today': 0, 'week': 0, 'month': 0, 'total': 0}
            
    def update_statistics(self):
        """更新统计信息显示"""
        try:
            # 获取统计数据
            stats = self.get_statistics()
            
            # 更新显示
            self.today_count.setText(str(stats['today']))
            self.week_count.setText(str(stats['week']))
            self.month_count.setText(str(stats['month']))
            self.total_count.setText(str(stats['total']))
            
            # 如果数据为0，添加特殊样式
            for widget, count in [
                (self.today_count, stats['today']),
                (self.week_count, stats['week']),
                (self.month_count, stats['month']),
                (self.total_count, stats['total'])
            ]:
                if count == 0:
                    widget.setStyleSheet("color: #888;")
                else:
                    widget.setStyleSheet("")
                    
        except Exception as e:
            print(f"更新统计信息出错: {e}")
            import traceback
            traceback.print_exc()