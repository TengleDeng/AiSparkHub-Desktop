#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QListWidget, QListWidgetItem,
                           QLineEdit, QLabel, QHBoxLayout, QPushButton, QMenu)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QColor, QAction
import qtawesome as qta
from datetime import datetime

class PromptHistoryItem(QListWidgetItem):
    """提示词历史记录项"""
    
    def __init__(self, prompt_data):
        super().__init__()
        self.prompt_data = prompt_data
        self.setup_display()
    
    def setup_display(self):
        """设置显示内容"""
        # 获取时间戳字符串或转换时间戳
        try:
            if isinstance(self.prompt_data['timestamp'], str):
                try:
                    time_str = datetime.fromisoformat(self.prompt_data['timestamp']).strftime("%Y-%m-%d %H:%M:%S")
                except (ValueError, TypeError):
                    # 如果isoformat解析失败，使用当前时间
                    time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            else:
                # 如果是数字时间戳，转换为时间字符串
                # 检查时间戳是否在合理范围内
                if isinstance(self.prompt_data['timestamp'], (int, float)) and 0 <= self.prompt_data['timestamp'] <= 32503680000:
                    timestamp = datetime.fromtimestamp(self.prompt_data['timestamp'])
                    time_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    # 无效时间戳，使用当前时间
                    time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, OSError, OverflowError, TypeError) as e:
            print(f"时间戳显示错误: {self.prompt_data.get('timestamp', '无时间戳')}, {e}")
            # 所有错误都使用当前时间
            time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 提取提示词文本
        prompt_text = self.prompt_data.get('prompt_text', '无提示词内容')
        
        # 设置显示文本
        display_text = f"{time_str}\n{prompt_text[:100]}..."
        self.setText(display_text)
        
        # 设置工具提示
        ai_targets = self.prompt_data.get('ai_targets', ['未知AI'])
        if not isinstance(ai_targets, list):
            ai_targets = ['未知AI']
            
        tooltip = f"目标AI: {', '.join(ai_targets)}\n"
        tooltip += f"完整内容:\n{prompt_text}"
        
        # 添加收藏状态
        if 'favorite' in self.prompt_data and self.prompt_data['favorite']:
            tooltip = "⭐ 已收藏\n" + tooltip
            # 设置前景色为金色以突出显示收藏项
            self.setForeground(QColor(255, 215, 0))
            
        self.setToolTip(tooltip)


class PromptHistory(QWidget):
    """提示词历史记录组件"""
    
    # 定义信号
    prompt_selected = pyqtSignal(str)  # 提示词选中信号
    favorite_toggled = pyqtSignal(str, bool)  # 收藏状态切换信号，参数: prompt_id, is_favorite
    
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
        
        # 添加收藏过滤按钮
        self.favorite_filter_btn = QPushButton(self)
        self.favorite_filter_btn.setIcon(qta.icon('fa5s.star'))
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
        
        # 创建列表
        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self.on_item_double_clicked)
        # 添加右键菜单
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.list_widget)
        
        # 设置样式
        self.setStyleSheet("""
            QLineEdit {
                background-color: #2E3440;
                color: #D8DEE9;
                border: 1px solid #3B4252;
                border-radius: 4px;
                padding: 8px;
            }
            QListWidget {
                background-color: #2E3440;
                color: #D8DEE9;
                border: 1px solid #3B4252;
                border-radius: 4px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #3B4252;
            }
            QListWidget::item:hover {
                background-color: #3B4252;
            }
            QListWidget::item:selected {
                background-color: #4C566A;
            }
        """)
        
        # 初始化记录收藏过滤状态
        self.show_favorites_only = False
    
    def refresh_history(self):
        """刷新历史记录"""
        self.list_widget.clear()
        
        # 根据过滤状态决定获取全部还是仅收藏记录
        if self.show_favorites_only:
            # 获取数据库中的收藏记录
            history = self.get_favorite_prompts()
        else:
            # 获取所有历史记录 (使用新的接口查询prompt_details表)
            history = self.db_manager.get_prompt_history()
        
        for prompt_data in history:
            item = PromptHistoryItem(prompt_data)
            self.list_widget.addItem(item)
    
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
                "SELECT id, prompt, timestamp, favorite FROM prompt_details WHERE favorite = 1 ORDER BY timestamp DESC LIMIT ?",
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
                            from urllib.parse import urlparse
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
                
                results.append({
                    'id': row['id'],
                    'prompt_text': row['prompt'],
                    'timestamp': timestamp_str,
                    'ai_targets': ai_targets,
                    'favorite': bool(row['favorite'])
                })
            
            return results
        except Exception as e:
            print(f"获取收藏记录失败: {e}")
            return []
    
    def search_history(self, text):
        """搜索历史记录"""
        if not text and not self.show_favorites_only:
            self.refresh_history()
            return
        
        self.list_widget.clear()
        
        # 结合搜索文本和收藏过滤条件
        if self.show_favorites_only:
            # 在收藏记录中搜索
            favorites = self.get_favorite_prompts()
            results = [item for item in favorites if text.lower() in item['prompt_text'].lower()]
        else:
            # 在所有记录中搜索
            results = self.db_manager.search_prompts(text)
            
        for prompt_data in results:
            item = PromptHistoryItem(prompt_data)
            self.list_widget.addItem(item)
    
    def toggle_favorite_filter(self, checked):
        """切换收藏过滤状态"""
        self.show_favorites_only = checked
        self.refresh_history()
    
    def on_item_double_clicked(self, item):
        """处理项目双击事件"""
        if isinstance(item, PromptHistoryItem):
            self.prompt_selected.emit(item.prompt_data['prompt_text'])
    
    def show_context_menu(self, position):
        """显示右键菜单"""
        item = self.list_widget.itemAt(position)
        if not item or not isinstance(item, PromptHistoryItem):
            return
            
        # 获取prompt_id
        prompt_id = item.prompt_data.get('id')
        if not prompt_id:
            return
            
        # 创建菜单
        menu = QMenu(self)
        
        # 添加"复制"操作
        copy_action = QAction("复制提示词", self)
        copy_action.triggered.connect(lambda: self.copy_prompt_to_clipboard(item.prompt_data['prompt_text']))
        menu.addAction(copy_action)
        
        # 添加"收藏/取消收藏"操作
        is_favorite = item.prompt_data.get('favorite', False)
        favorite_action = QAction("取消收藏" if is_favorite else "收藏", self)
        favorite_action.triggered.connect(lambda: self.toggle_favorite(prompt_id))
        menu.addAction(favorite_action)
        
        # 在菜单位置显示菜单
        try:
            # PyQt6中应该使用exec方法
            menu.exec(self.list_widget.mapToGlobal(position))
        except AttributeError:
            # 如果exec不存在，尝试exec_（可能在某些PyQt6版本中）
            menu.exec_(self.list_widget.mapToGlobal(position))
    
    def copy_prompt_to_clipboard(self, text):
        """复制提示词到剪贴板"""
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(text)
    
    def toggle_favorite(self, prompt_id):
        """切换收藏状态"""
        if not prompt_id:
            return
            
        # 切换数据库中的收藏状态
        new_state = self.db_manager.toggle_prompt_favorite(prompt_id)
        
        # 发射信号通知状态变化
        self.favorite_toggled.emit(prompt_id, new_state)
        
        # 刷新显示
        self.refresh_history() 