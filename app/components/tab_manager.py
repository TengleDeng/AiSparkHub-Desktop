#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import QTabWidget, QPushButton, QTabBar, QWidget
from PyQt6.QtCore import Qt, QEvent, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon
import qtawesome as qta

class TabManager(QTabWidget):
    """标签页管理器组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # 标记特殊标签页
        self.plus_tab_index = -1
        self.ai_tab_index = -1
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI界面"""
        # 设置标签可关闭 (仅网页标签可关闭，AI标签不可关闭)
        self.setTabsClosable(True)
        
        # 设置标签可移动
        self.setMovable(True)
        
        # 不要尝试断开信号，直接连接我们的处理函数
        # self.tabCloseRequested.disconnect()  # 删除这行，它会导致错误
        
        # 连接到我们自己的关闭标签处理函数
        self.tabCloseRequested.connect(self.handle_tab_close_request)
        
        # 连接标签切换信号
        self.currentChanged.connect(self.on_tab_changed)
        
        # 设置样式
        self.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background: #2E3440;
            }
            QTabWidget::tab-bar {
                alignment: left;
            }
            QTabBar::tab {
                background: #3B4252;
                color: #D8DEE9;
                padding: 0px 12px;
                border: none;
                margin-right: 2px;
                height: 30px;
            }
            QTabBar::tab:selected {
                background: #4C566A;
            }
            QTabBar::tab:hover {
                background: #434C5E;
            }
        """)
    
    def add_tab(self, widget, title, icon_name=None, closable=True):
        """添加新标签页
        
        Args:
            widget: 标签页内容组件
            title (str): 标签页标题
            icon_name (str): 图标名称
            closable (bool): 是否可关闭
        """
        # 如果有"+"标签，先移除它
        if self.plus_tab_index >= 0:
            self.removeTab(self.plus_tab_index)
            self.plus_tab_index = -1
        
        # 添加新标签页
        index = self.addTab(widget, title)
        if icon_name:
            self.setTabIcon(index, qta.icon(icon_name))
            
        # 如果标签不可关闭，隐藏关闭按钮
        if not closable:
            self.tabBar().setTabButton(index, self.tabBar().ButtonPosition.RightSide, None)
            # 如果是AI对话标签，记录它的索引
            if title == "AI对话":
                self.ai_tab_index = index
        
        return index
    
    def add_plus_tab(self):
        """添加"+"标签页"""
        # 创建空白窗口用于"+"标签页
        empty_widget = QWidget()
        
        # 添加"+"标签页到末尾
        self.plus_tab_index = self.addTab(empty_widget, "+")
        
        # 设置标签不可关闭
        self.tabBar().setTabButton(self.plus_tab_index, self.tabBar().ButtonPosition.RightSide, None)
        
        # 设置工具提示
        self.setTabToolTip(self.plus_tab_index, "添加新标签页")
    
    def add_new_tab(self):
        """添加新的空白标签页"""
        from app.components.web_view import WebView
        web_view = WebView()
        index = self.add_tab(web_view, "新标签页", "fa5s.globe")
        # 切换到新创建的标签页
        self.setCurrentIndex(index)
        return index
        
    def add_ai_view_tab(self, ai_view, title="AI对话"):
        """添加新的AI对话标签页（不可关闭）
        
        Args:
            ai_view: AI视图组件
            title (str): 标签页标题
        """
        idx = self.add_tab(ai_view, title, "fa5s.robot", closable=False)
        self.ai_tab_index = idx
        return idx
    
    def on_tab_changed(self, index):
        """标签页切换事件处理
        
        Args:
            index (int): 新的标签页索引
        """
        # 如果切换到"+"标签页，就创建新标签并切换过去
        if index == self.plus_tab_index:
            # 创建新标签页
            from app.components.web_view import WebView
            web_view = WebView()
            
            # 临时保存"+"标签的位置
            plus_index = self.plus_tab_index
            
            # 移除"+"标签（避免重复）
            self.removeTab(plus_index)
            self.plus_tab_index = -1
            
            # 添加新标签页
            new_index = self.addTab(web_view, "新标签页")
            if new_index >= 0:
                self.setTabIcon(new_index, qta.icon("fa5s.globe"))
                
            # 重新添加"+"标签页
            empty_widget = QWidget()
            self.plus_tab_index = self.addTab(empty_widget, "+")
            self.tabBar().setTabButton(self.plus_tab_index, self.tabBar().ButtonPosition.RightSide, None)
            self.setTabToolTip(self.plus_tab_index, "添加新标签页")
            
            # 确保标签栏更新
            self.tabBar().update()
            
            # 延迟50毫秒后切换到新创建的标签页（解决可能的UI更新问题）
            QTimer.singleShot(50, lambda: self.setCurrentIndex(new_index))
    
    def handle_tab_close_request(self, index):
        """处理标签页关闭请求
        
        Args:
            index (int): 标签页索引
        """
        print(f"请求关闭标签页: {index}, 加号标签: {self.plus_tab_index}, AI标签: {self.ai_tab_index}")
        
        # 不允许关闭特殊标签页
        if index == self.plus_tab_index or index == self.ai_tab_index:
            print(f"尝试关闭特殊标签页，已阻止")
            return
        
        # 保存当前索引，用于调整状态
        current_index = self.currentIndex()
        
        # 记录需要关闭的标签页标题，用于日志
        tab_title = self.tabText(index)
        print(f"关闭标签页: {tab_title} (索引: {index})")
        
        # 手动调用removeTab进行关闭
        self.blockSignals(True)  # 阻止信号触发递归关闭
        
        # 如果要关闭的是"+"号前面的标签，则需要更新"+"号索引
        if index < self.plus_tab_index:
            self.plus_tab_index -= 1
            print(f"更新加号标签索引为: {self.plus_tab_index}")
        
        # 强制移除标签页
        self.removeTab(index)
        
        # 恢复信号
        self.blockSignals(False)
        
        # 调整当前索引，确保显示合理
        count = self.count()
        if count > 0:
            # 如果关闭的是当前标签，则选中一个合适的标签
            if current_index == index:
                # 优先选择原来索引位置的标签（现在索引已经变化）
                if index < count:
                    self.setCurrentIndex(index)
                else:
                    # 如果关闭的是最后一个普通标签，则选中AI标签
                    self.setCurrentIndex(self.ai_tab_index)
            else:
                # 如果当前标签的索引因关闭而改变，则调整
                if current_index > index:
                    self.setCurrentIndex(current_index - 1)
                else:
                    self.setCurrentIndex(current_index)
        
        # 强制更新UI
        self.update()
        self.tabBar().update()
        print(f"标签关闭后，当前标签索引: {self.currentIndex()}, 标签总数: {self.count()}")
    
    def closeEvent(self, event):
        """处理标签页管理器关闭事件"""
        super().closeEvent(event) 