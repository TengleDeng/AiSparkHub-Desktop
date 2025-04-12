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
                background-color: #2E3440;
                width: 12px;
            }
            QScrollBar::handle:vertical {
                background-color: #4C566A;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #5E81AC;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
            QScrollBar:horizontal {
                background-color: #2E3440;
                height: 12px;
            }
            QScrollBar::handle:horizontal {
                background-color: #4C566A;
                border-radius: 6px;
                min-width: 20px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #5E81AC;
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
            }
            #ribbonToolBar QToolButton:hover {
                background-color: #3B4252;
            }
            
            /* 特殊控件 - 标题栏 */
            #panelTitleBar {
                background-color: #2E3440;
            }
            
            /* 窗口控制按钮 */
            QWidget#minimizeButton, QWidget#maximizeButton, QWidget#themeButton {
                background: transparent;
                border: none;
                padding: 6px 8px;
                margin: 0;
            }
            QWidget#minimizeButton:hover, QWidget#maximizeButton:hover, QWidget#themeButton:hover {
                background: #3B4252;
            }
            QWidget#closeButton {
                background: transparent;
                border: none;
                padding: 6px 8px;
                margin: 0;
            }
            QWidget#closeButton:hover {
                background: #BF616A;
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
        app.setStyleSheet("""
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
                height: 38px;
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
                background-color: #5E81AC;
                color: #ECEFF4;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #81A1C1;
            }
            QPushButton:pressed {
                background-color: #88C0D0;
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
            }
            #ribbonToolBar QToolButton:hover {
                background-color: #D8DEE9;
            }
            
            /* 特殊控件 - 标题栏 */
            #panelTitleBar {
                background-color: #E5E9F0;
            }
            
            /* 窗口控制按钮 */
            QWidget#minimizeButton, QWidget#maximizeButton, QWidget#themeButton {
                background: transparent;
                border: none;
                padding: 6px 8px;
                margin: 0;
            }
            QWidget#minimizeButton:hover, QWidget#maximizeButton:hover, QWidget#themeButton:hover {
                background: #D8DEE9;
            }
            QWidget#closeButton {
                background: transparent;
                border: none;
                padding: 6px 8px;
                margin: 0;
            }
            QWidget#closeButton:hover {
                background: #BF616A;
            }
        """)
    
    def toggle_theme(self, app):
        """切换主题
        
        Args:
            app: QApplication实例
        """
        self.current_theme = "light" if self.current_theme == "dark" else "dark"
        self.apply_theme(app)
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