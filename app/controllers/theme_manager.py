#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt

class ThemeManager:
    """主题管理器 - 控制应用程序的主题和样式"""
    
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
            QWidget {
                background-color: #2E3440;
                color: #D8DEE9;
            }
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
        """)
    
    def apply_light_theme(self, app):
        """应用浅色主题（待实现）
        
        Args:
            app: QApplication实例
        """
        # TODO: 实现浅色主题
        pass
    
    def toggle_theme(self, app):
        """切换主题
        
        Args:
            app: QApplication实例
        """
        self.current_theme = "light" if self.current_theme == "dark" else "dark"
        self.apply_theme(app) 