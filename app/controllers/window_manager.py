#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import QSplitter, QWidget, QVBoxLayout, QApplication
from PyQt6.QtCore import Qt, QObject, QRect

class WindowManager(QObject):
    """窗口管理器 - 管理主窗口和辅助窗口的关系和显示模式"""
    
    MODE_DUAL_SCREEN = 1    # 双屏幕模式
    MODE_SINGLE_SCREEN = 2  # 单屏幕模式
    
    def __init__(self, main_window, auxiliary_window):
        super().__init__()
        self.main_window = main_window
        self.auxiliary_window = auxiliary_window
        self.current_mode = None
        self.combined_window = None
        self.splitter = None
        
        # 连接主窗口和辅助窗口
        self.connect_windows()
    
    def connect_windows(self):
        """连接主窗口和辅助窗口，设置通信和协作机制"""
        # 连接提示词同步
        # 获取主窗口的AIView实例
        main_ai_view = self.main_window.get_ai_view()
        if main_ai_view:
            # 获取辅助窗口的PromptSync实例
            prompt_sync = self.auxiliary_window.prompt_sync
            # 注册AIView到PromptSync
            prompt_sync.register_ai_view(main_ai_view)
            print("已将AI视图注册到提示词同步器")
        else:
            print("警告：未找到主窗口的AI视图")
    
    def set_initial_display_mode(self):
        """根据屏幕情况设置初始显示模式"""
        # 获取屏幕大小
        screen = QApplication.primaryScreen()
        screen_size = screen.availableGeometry()
        
        # 主窗口位置和大小
        main_width = min(1200, screen_size.width() - 100)
        main_height = min(800, screen_size.height() - 100)
        main_x = (screen_size.width() - main_width) // 2
        main_y = (screen_size.height() - main_height - 300) // 2
        
        # 辅助窗口位置和大小
        aux_width = main_width
        aux_height = 300
        aux_x = main_x
        aux_y = main_y + main_height
        
        # 设置窗口位置和大小
        self.main_window.setGeometry(QRect(main_x, main_y, main_width, main_height))
        self.auxiliary_window.setGeometry(QRect(aux_x, aux_y, aux_width, aux_height))
    
    def set_dual_screen_mode(self):
        """设置为双屏幕模式"""
        if self.current_mode == self.MODE_DUAL_SCREEN:
            return
        
        # 如果当前是单屏幕模式，需要分离窗口
        if self.current_mode == self.MODE_SINGLE_SCREEN:
            self.separate_windows()
        
        # 获取屏幕列表，假设第一个屏幕是主屏幕
        screens = QApplication.instance().screens()
        if len(screens) > 1:
            # 将主窗口移到第二个屏幕
            second_screen_geometry = screens[1].availableGeometry()
            self.main_window.setGeometry(second_screen_geometry)
            
            # 将辅助窗口移到第一个屏幕（通常是主屏幕）
            first_screen_geometry = screens[0].availableGeometry()
            self.auxiliary_window.setGeometry(first_screen_geometry)
            
            # 确保窗口都可见
            self.main_window.show()
            self.auxiliary_window.show()
            
        self.current_mode = self.MODE_DUAL_SCREEN
    
    def set_single_screen_mode(self):
        """设置为单屏幕模式"""
        if self.current_mode == self.MODE_SINGLE_SCREEN:
            return
        
        # 创建组合窗口
        self.combined_window = QWidget()
        self.combined_window.setWindowTitle("AiSparkHub - 多AI对话桌面应用")
        
        # 创建垂直布局
        layout = QVBoxLayout(self.combined_window)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 创建分割器
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        
        # 从原始窗口获取中央部件
        main_central_widget = self.main_window.centralWidget()
        auxiliary_central_widget = self.auxiliary_window.centralWidget()
        
        # 将中央部件添加到分割器
        self.splitter.addWidget(main_central_widget)
        self.splitter.addWidget(auxiliary_central_widget)
        
        # 设置分割比例
        self.splitter.setSizes([700, 300])
        
        # 添加分割器到布局
        layout.addWidget(self.splitter)
        
        # 隐藏原始窗口
        self.main_window.hide()
        self.auxiliary_window.hide()
        
        # 显示组合窗口
        self.combined_window.show()
        
        self.current_mode = self.MODE_SINGLE_SCREEN
    
    def separate_windows(self):
        """分离为独立窗口"""
        if self.current_mode != self.MODE_SINGLE_SCREEN:
            return
        
        # 从分割器获取中央部件
        main_central_widget = self.splitter.widget(0)
        auxiliary_central_widget = self.splitter.widget(1)
        
        # 将中央部件重新设置回原始窗口
        self.main_window.setCentralWidget(main_central_widget)
        self.auxiliary_window.setCentralWidget(auxiliary_central_widget)
        
        # 隐藏组合窗口
        self.combined_window.hide()
        
        # 显示原始窗口
        self.main_window.show()
        self.auxiliary_window.show()
        
        self.current_mode = self.MODE_DUAL_SCREEN
    
    def toggle_display_mode(self):
        """切换显示模式"""
        if self.current_mode == self.MODE_DUAL_SCREEN:
            self.set_single_screen_mode()
        else:
            self.set_dual_screen_mode() 