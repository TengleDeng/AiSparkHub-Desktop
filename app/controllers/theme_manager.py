#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt, pyqtSignal, QObject

class ThemeManager(QObject):
    """主题管理器 - 控制应用程序的主题和样式"""
    
    theme_changed = pyqtSignal()  # 添加一个主题变化信号
    
    # Nord主题色板
    NORD_COLORS = {
        'polar_night': {
            'nord0': '#2E3440',  # 背景色
            'nord1': '#3B4252',  # 较亮的背景色
            'nord2': '#434C5E',  # 选中项背景色
            'nord3': '#4C566A'   # 高亮背景色
        },
        'snow_storm': {
            'nord4': '#D8DEE9',  # 前景色
            'nord5': '#E5E9F0',  # 较亮的前景色
            'nord6': '#ECEFF4'   # 高亮前景色
        },
        'frost': {
            'nord7': '#8FBCBB',  # 青色
            'nord8': '#88C0D0',  # 浅蓝色
            'nord9': '#81A1C1',  # 蓝色
            'nord10': '#5E81AC'  # 深蓝色
        },
        'aurora': {
            'nord11': '#BF616A',  # 红色
            'nord12': '#D08770',  # 橙色
            'nord13': '#EBCB8B',  # 黄色
            'nord14': '#A3BE8C',  # 绿色
            'nord15': '#B48EAD'   # 紫色
        }
    }
    
    def __init__(self):
        """初始化主题管理器"""
        super().__init__()
        self.current_theme = "dark"  # 默认使用深色主题
    
    def apply_theme(self, app):
        """应用主题到应用程序
        
        Args:
            app: QApplication实例
        """
        if self.current_theme == "dark":
            self.apply_dark_theme(app)
        else:
            self.apply_light_theme(app)
    
    def apply_dark_theme(self, app):
        """应用深色主题
        
        Args:
            app: QApplication实例
        """
        # 创建深色调色板
        palette = QPalette()
        
        # 设置窗口背景色
        palette.setColor(QPalette.ColorRole.Window, QColor(self.NORD_COLORS['polar_night']['nord0']))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(self.NORD_COLORS['snow_storm']['nord4']))
        
        # 设置按钮颜色
        palette.setColor(QPalette.ColorRole.Button, QColor(self.NORD_COLORS['polar_night']['nord1']))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(self.NORD_COLORS['snow_storm']['nord4']))
        
        # 设置基础颜色
        palette.setColor(QPalette.ColorRole.Base, QColor(self.NORD_COLORS['polar_night']['nord1']))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(self.NORD_COLORS['polar_night']['nord2']))
        
        # 设置文本颜色
        palette.setColor(QPalette.ColorRole.Text, QColor(self.NORD_COLORS['snow_storm']['nord4']))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(self.NORD_COLORS['snow_storm']['nord6']))
        
        # 设置高亮颜色
        palette.setColor(QPalette.ColorRole.Highlight, QColor(self.NORD_COLORS['frost']['nord10']))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(self.NORD_COLORS['snow_storm']['nord6']))
        
        # 设置链接颜色
        palette.setColor(QPalette.ColorRole.Link, QColor(self.NORD_COLORS['frost']['nord8']))
        palette.setColor(QPalette.ColorRole.LinkVisited, QColor(self.NORD_COLORS['frost']['nord9']))
        
        # 设置工具提示颜色
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(self.NORD_COLORS['polar_night']['nord2']))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(self.NORD_COLORS['snow_storm']['nord4']))
        
        # 应用调色板
        app.setPalette(palette)
        
        # 设置全局样式表
        app.setStyleSheet("""
            /* 基础控件样式 */
            QWidget {
                background-color: #2E3440;
                color: #D8DEE9;
            }
            
            /* 菜单栏样式 */
            QMenuBar {
                background-color: #2E3440;
                color: #D8DEE9;
            }
            QMenuBar::item:selected {
                background-color: #3B4252;
            }
            QMenu {
                background-color: #2E3440;
                color: #D8DEE9;
                border: 1px solid #3B4252;
            }
            QMenu::item:selected {
                background-color: #3B4252;
            }
            
            /* 滚动条样式 */
            QScrollBar:vertical {
                background-color: #2E3440;  /* 深色背景，与主题背景匹配 */
                width: 12px;
            }
            QScrollBar::handle:vertical {
                background-color: #4C566A;  /* 深色滑块 */
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #5E81AC;  /* 悬停时的颜色 */
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
            QScrollBar:horizontal {
                background-color: #2E3440;  /* 深色背景，与主题背景匹配 */
                height: 12px;
            }
            QScrollBar::handle:horizontal {
                background-color: #4C566A;  /* 深色滑块 */
                border-radius: 6px;
                min-width: 20px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #5E81AC;  /* 悬停时的颜色 */
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
            }
            
            /* 标签页样式 */
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
                height: 30px;
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
            
            /* 按钮样式 */
            QPushButton {
                background-color: #4C566A;
                color: #ECEFF4;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #5E81AC;
            }
            QPushButton:pressed {
                background-color: #81A1C1;
            }
            
            /* 文本框样式 */
            QLineEdit, QTextEdit, QPlainTextEdit {
                background-color: #3B4252;
                color: #D8DEE9;
                border: 1px solid #4C566A;
                border-radius: 4px;
                padding: 4px;
            }
            
            /* 工具栏样式 */
            QToolBar {
                background-color: #2E3440;
                border: none;
                spacing: 6px;
            }
            
            /* 状态栏样式 */
            QStatusBar {
                background-color: #2E3440;
                color: #D8DEE9;
            }
            
            /* 工具提示样式 */
            QToolTip {
                background-color: #3B4252;
                color: #D8DEE9;
                border: 1px solid #4C566A;
            }
            
            /* 特殊控件 - RibbonToolBar */
            #ribbonToolBar {
                background-color: #2E3440;
                border-right: 1px solid #4C566A;
                padding: 5px 2px;
                spacing: 8px;
            }
            #ribbonToolBar QToolButton {
                background-color: transparent;
                border: none;
                border-radius: 3px;
                padding: 5px;
                color: #D8DEE9; /* Icon color */
            }
            #ribbonToolBar QToolButton:hover {
                background-color: #3B4252;
            }
            #ribbonToolBar QToolButton:pressed {
                 background-color: #434C5E;
            }
            
            /* 特殊控件 - 标题栏 */
            #panelTitleBar {
                background-color: #2E3440;
            }
            
            /* AI View 特有样式 */
            QWebEngineView {
                background: #2E3440;
            }
            QSplitter::handle {
                background-color: #4C566A;
                width: 1px;
            }
            QComboBox#aiSelector {
                background-color: #3B4252;
                color: #D8DEE9;
                border: none;
                border-radius: 4px;
                padding: 1px 18px 1px 3px;
            }
            QComboBox#aiSelector::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left: none;
            }
            QComboBox#aiSelector::down-arrow {
                /* 需要一个图标，或者使用 qtawesome */
                /* image: url(:/icons/down-arrow-dark.png); */ 
            }
            QComboBox#aiSelector QAbstractItemView {
                background-color: #2E3440;
                color: #D8DEE9;
                selection-background-color: #4C566A;
                border: none;
                outline: none;
            }
            QComboBox#aiSelector:hover {
                background-color: #434C5E;
            }
            QWidget#aiTitleBar {
                background: #3B4252;
                border-bottom: none;
            }
            QWidget#aiTitleBar QPushButton:hover {
                background-color: #4C566A;
            }
            QWidget#aiTitleBar QPushButton:pressed {
                background-color: #5E81AC;
            }
            QWidget#aiTitleBar QPushButton {
                color: #D8DEE9; /* 设置深色主题下图标颜色 */
            }
            
            /* 窗口控制按钮 */
            QWidget#minimizeButton, QWidget#maximizeButton, QWidget#themeButton {
                background: transparent;
                border: none;
                padding: 6px 8px;
                margin: 0;
                color: #4C566A; /* Slightly darker icon color for better visibility */
            }
            QWidget#minimizeButton:hover, QWidget#maximizeButton:hover, QWidget#themeButton:hover {
                background: #434C5E; /* Use a slightly lighter dark bg for hover */
                color: #2E3440; /* Darker icon on hover */
            }
            QWidget#minimizeButton:pressed, QWidget#maximizeButton:pressed, QWidget#themeButton:pressed {
                background-color: #C7CED9; /* Slightly darker pressed state */
                color: #2E3440; /* Darker icon on pressed */
            }
            QWidget#closeButton {
                background: transparent;
                border: none;
                padding: 6px 8px;
                margin: 0;
                color: #4C566A; /* Match other window control icons */
            }
            QWidget#closeButton:hover {
                background: #BF616A; /* Match other hover background */
                color: #2E3440; /* Darker icon on hover */
            }
            QWidget#closeButton:pressed {
                background-color: #C7CED9; /* Match other pressed state */
                color: #2E3440; /* Darker icon on pressed */
            }
            
            /* WebView 地址栏样式 */
            QWidget#addressToolbar {
                background: #2E3440;
            }
            QWidget#addressToolbar QPushButton {
                background: transparent;
                border: none;
                padding: 2px;
                border-radius: 4px;
                color: #D8DEE9; /* 设置图标颜色 */
            }
            QWidget#addressToolbar QPushButton:hover {
                background: #3B4252;
            }
            QWidget#addressToolbar QPushButton:pressed {
                background: #434C5E;
            }
            QWidget#addressToolbar QLineEdit {
                background: #3B4252;
                color: #D8DEE9;
                border: 1px solid #434C5E;
                border-radius: 4px;
                padding: 2px 8px;
            }
            
            /* RibbonToolBar (AuxiliaryWindow) */
            #ribbonToolBar {
                background-color: #2E3440;
                border-right: 1px solid #4C566A;
                padding: 5px 2px;
                spacing: 8px;
            }
            #ribbonToolBar QToolButton {
                background-color: transparent;
                border: none;
                border-radius: 3px;
                padding: 5px;
                color: #D8DEE9; /* Icon color */
            }
            #ribbonToolBar QToolButton:hover {
                background-color: #3B4252;
            }
            #ribbonToolBar QToolButton:pressed {
                 background-color: #434C5E;
            }

            /* PanelWidget (AuxiliaryWindow) */
            QWidget#panelTitleBar QLabel { /* More specific selector */
                 color: #D8DEE9; 
                 font-weight: bold;
            }
            QWidget#panelTitleBar { /* Default Panel title */
                 background-color: #2E3440;
            }
            QWidget#auxiliaryTitleBar { /* Specific AuxiliaryWindow title */
                 background-color: #2E3440;
                 border-bottom: 1px solid #3B4252; /* Add border to custom title */
            }
            PanelWidget QFrame[frameShape="5"] { /* Horizontal Separator */
                background-color: #3B4252; 
                border: none; /* Ensure no extra border */
                max-height: 1px; /* Ensure it's thin */
            }
            
            /* AuxiliaryWindow Title Bar Buttons */
             QWidget#auxiliaryTitleBar QPushButton {
                 color: #4C566A; /* Use the same darker icon color */
                 background: transparent; /* Ensure transparent background */
                 border: none; /* Ensure no border */
                 padding: 4px 6px; /* Adjust padding if needed */
             }
             QWidget#auxiliaryTitleBar QPushButton:hover {
                 background: #D8DEE9;
             }
             QWidget#auxiliaryTitleBar QPushButton:pressed {
                 background-color: #C7CED9; /* Match generic pressed state */
             }
             
             /* QMessageBox (AuxiliaryWindow) */
             QMessageBox {
                 background-color: #2E3440;
             }
             QMessageBox QLabel {
                 color: #D8DEE9;
             }
            /* Use default QPushButton style defined above for MessageBox buttons */

            /* Global Scrollbar Style */
            QScrollBar:vertical {
                background-color: #2E3440;  /* 深色背景，与主题背景匹配 */
                width: 12px;
            }
            QScrollBar::handle:vertical {
                background-color: #4C566A;  /* 深色滑块 */
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #5E81AC;  /* 悬停时的颜色 */
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
            QScrollBar:horizontal {
                background-color: #2E3440;  /* 深色背景，与主题背景匹配 */
                height: 12px;
            }
            QScrollBar::handle:horizontal {
                background-color: #4C566A;  /* 深色滑块 */
                border-radius: 6px;
                min-width: 20px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #5E81AC;  /* 悬停时的颜色 */
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
            }
            
            /* TreeView Style */
            QTreeView {
                background-color: #2E3440;
                border: none;
                outline: none;
            }
            QTreeView::item {
                padding: 4px;
            }
            QTreeView::item:hover {
                background-color: #3B4252;
            }
            QTreeView::item:selected {
                background-color: #4C566A;
                color: #2E3440; /* Add dark text color for selected items */
            }
            QTreeView::branch {
                background-color: #2E3440;
            }
            QTreeView::branch:selected {
                background-color: #4C566A;
            }

            /* PromptHistory Styles */
            PromptHistory QLineEdit#searchInput {
                background-color: #2E3440;
                color: #D8DEE9;
                border: 1px solid #3B4252;
                border-radius: 4px;
                padding: 8px;
            }
            PromptHistory QPushButton#favoriteFilterBtn,
            PromptHistory QPushButton#refreshBtn {
                background-color: #2E3440;
                border: 1px solid #3B4252;
                border-radius: 4px;
                padding: 4px;
                color: #D8DEE9; /* Icon color */
            }
            PromptHistory QPushButton#favoriteFilterBtn:checked {
                background-color: #5E81AC;
                border-color: #5E81AC;
            }
            PromptHistory QPushButton#favoriteFilterBtn:hover,
            PromptHistory QPushButton#refreshBtn:hover {
                background-color: #3B4252;
            }
            PromptHistory QScrollArea {
                background-color: #2E3440;
                border: none;
            }
            PromptHistory QWidget#contentWidget {
                background-color: #2E3440;
            }
            
            /* PromptItemWidget Styles */
            PromptItemWidget {
                background-color: #2E3440;
                border-radius: 8px;
            }
            PromptItemWidget QLabel#timeLabel {
                color: #D8DEE9; /* Use standard foreground color for dark theme */
                font-size: 12px;
                border: none;
            }
            PromptItemWidget QLabel#contentLabel {
                 color: #E5E9F0;
                 background-color: #3B4252;
                 border-radius: 6px;
                 padding: 8px;
                 font-size: 13px;
                 border: none;
            }
            PromptItemWidget QToolButton {
                 background-color: #3B4252;
                 border-radius: 10px;
                 padding: 2px;
                 border: none;
                 color: #D8DEE9; /* Icon color */
            }
            PromptItemWidget QToolButton:hover {
                 background-color: #4C566A;
            }
            PromptItemWidget QToolButton:pressed {
                 background-color: #5E81AC;
            }

            /* PromptInput Styles */
            PromptInput QTextEdit {
                background-color: #2E3440;
                color: #D8DEE9;
                border: 1px solid #3B4252;
                border-radius: 4px;
                padding: 8px;
            }
            PromptInput QPushButton {
                background-color: #5E81AC; /* Default button style */
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            PromptInput QPushButton:hover {
                background-color: #81A1C1;
            }
            PromptInput QPushButton:pressed {
                background-color: #4C566A;
            }

            /* 确保PromptItemWidget内部的子控件没有边框 */
            QWidget#promptItemWidget QLabel,
            QWidget#promptItemWidget QToolButton,
            QWidget#promptItemWidget QFrame {
                border: none;
                background-color: transparent;
            }
        """)
    
    def apply_light_theme(self, app):
        """应用浅色主题
        
        Args:
            app: QApplication实例
        """
        # 创建浅色调色板
        palette = QPalette()
        
        # 设置窗口背景色
        palette.setColor(QPalette.ColorRole.Window, QColor(self.NORD_COLORS['snow_storm']['nord6']))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(self.NORD_COLORS['polar_night']['nord0']))
        
        # 设置按钮颜色
        palette.setColor(QPalette.ColorRole.Button, QColor(self.NORD_COLORS['snow_storm']['nord5']))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(self.NORD_COLORS['polar_night']['nord0']))
        
        # 设置基础颜色
        palette.setColor(QPalette.ColorRole.Base, QColor(self.NORD_COLORS['snow_storm']['nord6']))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(self.NORD_COLORS['snow_storm']['nord5']))
        
        # 设置文本颜色
        palette.setColor(QPalette.ColorRole.Text, QColor(self.NORD_COLORS['polar_night']['nord0']))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(self.NORD_COLORS['polar_night']['nord1']))
        
        # 设置高亮颜色
        palette.setColor(QPalette.ColorRole.Highlight, QColor(self.NORD_COLORS['frost']['nord8']))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(self.NORD_COLORS['snow_storm']['nord6']))
        
        # 设置链接颜色
        palette.setColor(QPalette.ColorRole.Link, QColor(self.NORD_COLORS['frost']['nord10']))
        palette.setColor(QPalette.ColorRole.LinkVisited, QColor(self.NORD_COLORS['frost']['nord9']))
        
        # 设置工具提示颜色
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(self.NORD_COLORS['snow_storm']['nord4']))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(self.NORD_COLORS['polar_night']['nord0']))
        
        # 应用调色板
        app.setPalette(palette)
        
        # 设置全局样式表
        light_qss = """
            QWidget {
                background-color: #ECEFF4;
                color: #2E3440;
            }
            QMenuBar {
                background-color: #E5E9F0;
                color: #2E3440;
            }
            QMenuBar::item:selected {
                background-color: #D8DEE9;
            }
            QMenu {
                background-color: #E5E9F0;
                color: #2E3440;
                border: 1px solid #D8DEE9;
            }
            QMenu::item:selected {
                background-color: #D8DEE9;
            }
            QScrollBar:vertical {
                background-color: #ECEFF4;
                width: 12px;
            }
            QScrollBar::handle:vertical {
                background-color: #D8DEE9;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #81A1C1;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
            QScrollBar:horizontal {
                background-color: #ECEFF4;
                height: 12px;
            }
            QScrollBar::handle:horizontal {
                background-color: #D8DEE9;
                border-radius: 6px;
                min-width: 20px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #81A1C1;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
            }
            
            /* 标签页样式 */
            QTabWidget::pane {
                border-top: 1px solid #D8DEE9;
                background-color: #ECEFF4;
            }
            QTabWidget::tab-bar {
                alignment: left;
                background-color: #ECEFF4;
            }
            QTabBar {
                background-color: #ECEFF4;
                qproperty-drawBase: 0;
            }
            QTabBar::tab {
                background: #E5E9F0;
                color: #2E3440;
                padding: 0px 12px;
                border: none;
                margin-right: 2px;
                min-width: 10ex;
                height: 30px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background: #D8DEE9;
                color: #2E3440;
            }
            QTabBar::tab:hover:!selected {
                background: #D8DEE9;
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
            
            /* 按钮样式 */
            QPushButton {
                background-color: #D8DEE9; /* General light button */
                color: #2E3440;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #B4C9E0; /* Lighter hover */
            }
            QPushButton:pressed {
                background-color: #a8bdd5; /* Slightly darker pressed */
            }
            
            /* 文本框样式 */
            QLineEdit, QTextEdit, QPlainTextEdit {
                background-color: #E5E9F0;
                color: #2E3440;
                border: 1px solid #D8DEE9;
                border-radius: 4px;
                padding: 4px;
            }
            
            /* 工具栏样式 */
            QToolBar {
                background-color: #E5E9F0;
                border: none;
                spacing: 6px;
            }
            
            /* 状态栏样式 */
            QStatusBar {
                background-color: #E5E9F0;
                color: #2E3440;
            }
            
            /* 工具提示样式 */
            QToolTip {
                background-color: #E5E9F0;
                color: #2E3440;
                border: 1px solid #D8DEE9;
            }
            
            /* 特殊控件 - RibbonToolBar */
            #ribbonToolBar {
                background-color: #E5E9F0;
                border-right: 1px solid #D8DEE9;
                padding: 5px 2px;
                spacing: 8px;
            }
            #ribbonToolBar QToolButton {
                background-color: transparent;
                border: none;
                border-radius: 3px;
                padding: 5px;
                color: #3B4252; /* Icon color */
            }
            #ribbonToolBar QToolButton:hover {
                background-color: #D8DEE9;
            }
            #ribbonToolBar QToolButton:pressed {
                 background-color: #B4C9E0;
            }
            
            /* 特殊控件 - 标题栏 */
            #panelTitleBar {
                background-color: #E5E9F0;
            }
            
            /* AI View 特有样式 */
            QWebEngineView {
                background: #ECEFF4;
            }
            QSplitter::handle {
                background-color: #D8DEE9;
                width: 1px;
            }
            QComboBox#aiSelector {
                background-color: #E5E9F0;
                color: #2E3440;
                border: 1px solid #D8DEE9; /* 浅色模式加个边框 */
                border-radius: 4px;
                padding: 1px 18px 1px 3px;
            }
            QComboBox#aiSelector::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left: none;
            }
            QComboBox#aiSelector::down-arrow {
                 /* 需要一个图标，或者使用 qtawesome */
                 /* image: url(:/icons/down-arrow-light.png); */
            }
            QComboBox#aiSelector QAbstractItemView {
                background-color: #ECEFF4;
                color: #2E3440;
                selection-background-color: #D8DEE9;
                border: none;
                outline: none;
            }
            QComboBox#aiSelector:hover {
                background-color: #D8DEE9;
            }
             QWidget#aiTitleBar {
                background: #E5E9F0;
                border-bottom: none;
            }
            QWidget#aiTitleBar QPushButton:hover {
                background-color: #D8DEE9;
            }
            QWidget#aiTitleBar QPushButton:pressed {
                background-color: #B4C9E0; /* 浅色模式的按下颜色 */
            }
            QWidget#aiTitleBar QPushButton {
                color: #3B4252; /* 设置浅色主题下图标颜色 */
            }
            
            /* 窗口控制按钮 */
            QWidget#minimizeButton, QWidget#maximizeButton, QWidget#themeButton {
                background: transparent;
                border: none;
                padding: 6px 8px;
                margin: 0;
                color: #4C566A; /* Slightly darker icon color for better visibility */
            }
            QWidget#minimizeButton:hover, QWidget#maximizeButton:hover, QWidget#themeButton:hover {
                background: #D8DEE9; /* Use a slightly lighter dark bg for hover */
                color: #2E3440; /* Darker icon on hover */
            }
            QWidget#minimizeButton:pressed, QWidget#maximizeButton:pressed, QWidget#themeButton:pressed {
                background-color: #C7CED9; /* Slightly darker pressed state */
                color: #2E3440; /* Darker icon on pressed */
            }
            QWidget#closeButton {
                background: transparent;
                border: none;
                padding: 6px 8px;
                margin: 0;
                color: #4C566A; /* Match other window control icons */
            }
            QWidget#closeButton:hover {
                background: #BF616A; /* Match other hover background */
                color: #2E3440; /* Darker icon on hover */
            }
            QWidget#closeButton:pressed {
                background-color: #C7CED9; /* Match other pressed state */
                color: #2E3440; /* Darker icon on pressed */
            }
            
            /* WebView 地址栏样式 */
            QWidget#addressToolbar {
                background: #E5E9F0; /* 浅色模式地址栏背景 */
            }
             QWidget#addressToolbar QPushButton {
                background: transparent;
                border: none;
                padding: 2px;
                border-radius: 4px;
                color: #3B4252; /* 设置图标颜色 */
            }
            QWidget#addressToolbar QPushButton:hover {
                background: #D8DEE9;
            }
            QWidget#addressToolbar QPushButton:pressed {
                background: #B4C9E0; /* 与 aiTitleBar 按钮按下颜色一致 */
            }
            QWidget#addressToolbar QLineEdit {
                background: #E5E9F0;
                color: #2E3440;
                border: 1px solid #D8DEE9;
                border-radius: 4px;
                padding: 2px 8px;
            }
            
            /* RibbonToolBar (AuxiliaryWindow) */
            #ribbonToolBar {
                background-color: #E5E9F0;
                border-right: 1px solid #D8DEE9;
                padding: 5px 2px;
                spacing: 8px;
            }
            #ribbonToolBar QToolButton {
                background-color: transparent;
                border: none;
                border-radius: 3px;
                padding: 5px;
                color: #3B4252; /* Icon color */
            }
            #ribbonToolBar QToolButton:hover {
                background-color: #D8DEE9;
            }
            #ribbonToolBar QToolButton:pressed {
                 background-color: #B4C9E0;
            }

            /* PanelWidget (AuxiliaryWindow) */
            QWidget#panelTitleBar QLabel { 
                 color: #2E3440; 
                 font-weight: bold;
            }
            QWidget#panelTitleBar {
                 background-color: #E5E9F0;
            }
            QWidget#auxiliaryTitleBar {
                 background-color: #E5E9F0;
                 border-bottom: 1px solid #D8DEE9; 
            }
            PanelWidget QFrame[frameShape="5"] { 
                background-color: #D8DEE9; 
                border: none;
                max-height: 1px;
            }
            
            /* AuxiliaryWindow Title Bar Buttons */
             QWidget#auxiliaryTitleBar QPushButton {
                 color: #4C566A; /* Use the same darker icon color */
                 background: transparent; /* Ensure transparent background */
                 border: none; /* Ensure no border */
                 padding: 4px 6px; /* Adjust padding if needed */
             }
             QWidget#auxiliaryTitleBar QPushButton:hover {
                 background: #D8DEE9;
             }
             QWidget#auxiliaryTitleBar QPushButton:pressed {
                 background-color: #C7CED9; /* Match generic pressed state */
             }
             
             /* QMessageBox (AuxiliaryWindow) */
             QMessageBox {
                 background-color: #ECEFF4;
             }
             QMessageBox QLabel {
                 color: #2E3440;
             }
             /* Use default QPushButton style defined above for MessageBox buttons */

             /* Global Scrollbar Style */
            QScrollBar:vertical {
                background-color: #2E3440;  /* 深色背景，与主题背景匹配 */
                width: 12px;
            }
            QScrollBar::handle:vertical {
                background-color: #4C566A;  /* 深色滑块 */
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #5E81AC;  /* 悬停时的颜色 */
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
            QScrollBar:horizontal {
                background-color: #2E3440;  /* 深色背景，与主题背景匹配 */
                height: 12px;
            }
            QScrollBar::handle:horizontal {
                background-color: #4C566A;  /* 深色滑块 */
                border-radius: 6px;
                min-width: 20px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #5E81AC;  /* 悬停时的颜色 */
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
            }
            
            /* TreeView Style */
            QTreeView {
                background-color: #ECEFF4; /* Light background */
                border: none;
                outline: none;
            }
            QTreeView::item {
                padding: 4px;
            }
            QTreeView::item:hover {
                background-color: #E5E9F0; /* Lighter hover */
            }
            QTreeView::item:selected {
                background-color: #D8DEE9; /* Light selection */
                color: #2E3440; /* Add dark text color for selected items */
            }
            QTreeView::branch {
                background-color: #ECEFF4;
            }
            QTreeView::branch:selected {
                background-color: #D8DEE9;
            }

            /* PromptHistory Styles */
            PromptHistory QLineEdit#searchInput {
                background-color: #ECEFF4; /* Light */
                color: #2E3440;
                border: 1px solid #D8DEE9;
                border-radius: 4px;
                padding: 8px;
            }
            PromptHistory QPushButton#favoriteFilterBtn,
            PromptHistory QPushButton#refreshBtn {
                background-color: #ECEFF4;
                border: 1px solid #D8DEE9;
                border-radius: 4px;
                padding: 4px;
                color: #3B4252; /* Icon color */
            }
            PromptHistory QPushButton#favoriteFilterBtn:checked {
                background-color: #88C0D0; /* Lighter blue */
                border-color: #88C0D0;
            }
            PromptHistory QPushButton#favoriteFilterBtn:hover,
            PromptHistory QPushButton#refreshBtn:hover {
                background-color: #E5E9F0;
            }
            PromptHistory QScrollArea {
                background-color: #ECEFF4;
                border: none;
            }
            PromptHistory QWidget#contentWidget {
                background-color: #ECEFF4;
            }
            
            /* PromptItemWidget Styles */
            PromptItemWidget {
                background-color: #E5E9F0; /* Lighter background */
                border-radius: 8px;
            }
            PromptItemWidget QLabel#timeLabel {
                color: #2E3440; /* Use standard foreground color */
                font-size: 12px;
                border: none;
            }
            PromptItemWidget QLabel#contentLabel {
                 color: #2E3440;
                 background-color: #ECEFF4; /* Lighter content bg */
                 border-radius: 6px;
                 padding: 8px;
                 font-size: 13px;
                 border: none;
            }
            PromptItemWidget QToolButton {
                 background-color: #D8DEE9; /* Light button bg */
                 border-radius: 10px;
                 padding: 2px;
                 border: none;
                 color: #3B4252; /* Icon color */
            }
            PromptItemWidget QToolButton:hover {
                 background-color: #B4C9E0;
            }
            PromptItemWidget QToolButton:pressed {
                 background-color: #a8bdd5; /* Match generic light button pressed */
            }

            /* PromptInput Styles */
            PromptInput QTextEdit {
                background-color: #ECEFF4; /* Light */
                color: #2E3440;
                border: 1px solid #D8DEE9;
                border-radius: 4px;
                padding: 8px;
            }
            PromptInput QPushButton {
                background-color: #D8DEE9; /* Match generic light button */
                color: #2E3440; /* Dark text */
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            PromptInput QPushButton:hover {
                background-color: #B4C9E0; /* Match generic light button hover */
            }
            PromptInput QPushButton:pressed {
                background-color: #a8bdd5; /* Match generic light button pressed */
            }
        """        
        print("--- Applying Light Theme QSS ---")
        print(light_qss) # 打印将要应用的QSS
        app.setStyleSheet(light_qss) # 重新应用样式表
        print("--- End of Light Theme QSS ---")
    
    def toggle_theme(self, app):
        """切换主题
        
        Args:
            app: QApplication实例
        """
        print("ThemeManager: Toggling theme...") # 添加打印
        self.current_theme = "light" if self.current_theme == "dark" else "dark"
        self.apply_theme(app) 
        print(f"ThemeManager: Theme changed to {self.current_theme}") # 添加打印
        self.theme_changed.emit()  # 发射主题变化信号
    
    def get_current_theme_colors(self):
        """获取当前主题的颜色对象，供其他组件使用
        
        Returns:
            dict: 包含当前主题颜色的字典
        """
        colors = {
            # 基础颜色
            'background': self.NORD_COLORS['polar_night']['nord0'] if self.current_theme == "dark" else self.NORD_COLORS['snow_storm']['nord6'],
            'foreground': self.NORD_COLORS['snow_storm']['nord4'] if self.current_theme == "dark" else self.NORD_COLORS['polar_night']['nord0'],
            
            # 次要背景颜色
            'secondary_bg': self.NORD_COLORS['polar_night']['nord1'] if self.current_theme == "dark" else self.NORD_COLORS['snow_storm']['nord5'],
            'tertiary_bg': self.NORD_COLORS['polar_night']['nord2'] if self.current_theme == "dark" else self.NORD_COLORS['snow_storm']['nord4'],
            
            # 高亮与强调色
            'highlight': self.NORD_COLORS['frost']['nord10'] if self.current_theme == "dark" else self.NORD_COLORS['frost']['nord8'],
            'accent': self.NORD_COLORS['frost']['nord8'] if self.current_theme == "dark" else self.NORD_COLORS['frost']['nord9'],
            
            # 功能性颜色
            'success': self.NORD_COLORS['aurora']['nord14'],
            'warning': self.NORD_COLORS['aurora']['nord13'],
            'error': self.NORD_COLORS['aurora']['nord11'],
            'info': self.NORD_COLORS['frost']['nord9'],
            
            # 是否是暗色主题
            'is_dark': self.current_theme == "dark"
        }
        
        return colors 