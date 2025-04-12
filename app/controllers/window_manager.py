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
            
            # 确保PromptSync能访问数据库管理器
            db_manager = self.auxiliary_window.db_manager
            if db_manager and not prompt_sync.db_manager:
                prompt_sync.set_db_manager(db_manager)
                print("已设置提示词同步器的数据库管理器")
                
            print("已将AI视图注册到提示词同步器")
        else:
            print("警告：未找到主窗口的AI视图")
        
        # 连接辅助窗口的"打开主窗口"请求信号
        self.auxiliary_window.request_open_main_window.connect(self.show_main_window)
        print("已连接辅助窗口的打开主窗口请求信号")
    
    def set_initial_display_mode(self):
        """根据屏幕情况设置初始显示模式"""
        # 获取屏幕大小
        screen = QApplication.primaryScreen()
        screen_size = screen.availableGeometry()
        
        # 首先重置窗口状态
        self.main_window.showNormal()
        self.auxiliary_window.showNormal()
        
        # 暂时禁用无边框以便可以正确设置位置
        main_flags = self.main_window.windowFlags()
        aux_flags = self.auxiliary_window.windowFlags()
        
        self.main_window.setWindowFlags(main_flags & ~Qt.WindowType.FramelessWindowHint)
        self.auxiliary_window.setWindowFlags(aux_flags & ~Qt.WindowType.FramelessWindowHint)
        
        # 重新显示窗口（更改flags后需要重新show）
        self.main_window.show()
        self.auxiliary_window.show()
        
        # 设置窗口在屏幕中央
        main_width = min(1200, screen_size.width() - 100)
        main_height = min(800, screen_size.height() - 100)
        main_x = (screen_size.width() - main_width) // 2
        main_y = (screen_size.height() - main_height) // 2
        
        # 设置辅助窗口与主窗口大小相似，稍微错开位置避免完全重叠
        aux_x = main_x + 50
        aux_y = main_y + 50
        
        # 设置窗口位置和大小
        self.main_window.setGeometry(main_x, main_y, main_width, main_height)
        self.auxiliary_window.setGeometry(aux_x, aux_y, main_width, main_height)
        
        # 强制处理事件，确保位置设置完成
        QApplication.processEvents()
        
        # 恢复无边框
        self.main_window.setWindowFlags(main_flags)
        self.auxiliary_window.setWindowFlags(aux_flags)
        
        # 重新显示窗口
        self.main_window.show()
        self.auxiliary_window.show()
        
        # 初始设置主窗口最大化，辅助窗口不最大化
        self.main_window.showMaximized()
        print("单屏幕模式：主窗口已最大化显示")
    
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
            print("检测到多个屏幕，设置双屏幕模式")
            
            # ===== 处理主窗口 =====
            # 首先重置窗口状态
            self.main_window.showNormal()
            
            # 暂时禁用无边框
            original_flags = self.main_window.windowFlags()
            self.main_window.setWindowFlags(original_flags & ~Qt.WindowType.FramelessWindowHint)
            self.main_window.show()  # 窗口标志修改后需要重新show
            
            # 获取第二个屏幕的几何信息
            second_screen_geometry = screens[1].availableGeometry()
            print(f"第二屏幕几何信息: {second_screen_geometry}")
            
            # 将窗口移到第二个屏幕上
            self.main_window.setGeometry(
                second_screen_geometry.x() + 50,
                second_screen_geometry.y() + 50,
                second_screen_geometry.width() - 100,
                second_screen_geometry.height() - 100
            )
            
            # 强制处理事件，确保窗口移动完成
            QApplication.processEvents()
            
            # 恢复无边框
            self.main_window.setWindowFlags(original_flags)
            self.main_window.show()
            
            # 最大化窗口
            self.main_window.showMaximized()
            print("主窗口已设置在第二屏幕上并最大化")
            
            # ===== 处理辅助窗口 =====
            # 首先重置窗口状态
            self.auxiliary_window.showNormal()
            
            # 暂时禁用无边框
            original_flags = self.auxiliary_window.windowFlags()
            self.auxiliary_window.setWindowFlags(original_flags & ~Qt.WindowType.FramelessWindowHint)
            self.auxiliary_window.show()  # 窗口标志修改后需要重新show
            
            # 获取第一个屏幕的几何信息
            first_screen_geometry = screens[0].availableGeometry()
            print(f"第一屏幕几何信息: {first_screen_geometry}")
            
            # 将窗口移到第一个屏幕上
            self.auxiliary_window.setGeometry(
                first_screen_geometry.x() + 50,
                first_screen_geometry.y() + 50,
                first_screen_geometry.width() - 100,
                first_screen_geometry.height() - 100
            )
            
            # 强制处理事件，确保窗口移动完成
            QApplication.processEvents()
            
            # 恢复无边框
            self.auxiliary_window.setWindowFlags(original_flags)
            self.auxiliary_window.show()
            
            # 最大化窗口
            self.auxiliary_window.showMaximized()
            print("辅助窗口已设置在第一屏幕上并最大化")
        else:
            print("只检测到一个屏幕，将在单屏幕上显示两个窗口")
            
            # 首先重置窗口状态
            self.main_window.showNormal()
            self.auxiliary_window.showNormal()
            
            # 暂时禁用无边框
            main_flags = self.main_window.windowFlags()
            aux_flags = self.auxiliary_window.windowFlags()
            
            self.main_window.setWindowFlags(main_flags & ~Qt.WindowType.FramelessWindowHint)
            self.auxiliary_window.setWindowFlags(aux_flags & ~Qt.WindowType.FramelessWindowHint)
            
            # 重新显示窗口
            self.main_window.show()
            self.auxiliary_window.show()
            
            # 错开位置避免完全重叠
            screen_size = QApplication.primaryScreen().availableGeometry()
            self.main_window.move(screen_size.x() + 20, screen_size.y() + 20)
            self.auxiliary_window.move(screen_size.x() + 70, screen_size.y() + 70)
            
            # 强制处理事件，确保位置设置完成
            QApplication.processEvents()
            
            # 恢复无边框
            self.main_window.setWindowFlags(main_flags)
            self.auxiliary_window.setWindowFlags(aux_flags)
            
            # 重新显示窗口
            self.main_window.show()
            self.auxiliary_window.show()
            
            # 最大化主窗口
            self.main_window.showMaximized()
            print("单屏幕模式：主窗口已最大化显示")
            
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
    
    def show_main_window(self):
        """显示主窗口，响应辅助窗口的请求"""
        print("收到打开主窗口请求")
        if not self.main_window.isVisible():
            self.main_window.show()
            print("主窗口已显示")
    
    def apply_theme_to_windows(self):
        """应用当前主题样式到所有窗口"""
        app = QApplication.instance()
        
        if not hasattr(app, 'theme_manager'):
            print("警告：未找到主题管理器")
            return
            
        # 获取当前主题样式
        theme_colors = app.theme_manager.get_current_theme_colors()
        is_dark = theme_colors['is_dark']
        
        # 更新最大化/还原按钮图标
        if self.main_window and hasattr(self.main_window, 'maximize_button'):
            import qtawesome as qta
            icon_name = 'fa5s.window-restore' if self.main_window.isMaximized() else 'fa5s.window-maximize'
            self.main_window.maximize_button.setIcon(qta.icon(icon_name))
            
        if self.auxiliary_window and hasattr(self.auxiliary_window, 'maximize_button'):
            import qtawesome as qta
            icon_name = 'fa5s.window-restore' if self.auxiliary_window.isMaximized() else 'fa5s.window-maximize'
            self.auxiliary_window.maximize_button.setIcon(qta.icon(icon_name))
            
        # 更新主题切换按钮图标
        if self.main_window and hasattr(self.main_window, 'theme_button'):
            self.main_window._update_theme_icon()
            
        if self.auxiliary_window and hasattr(self.auxiliary_window, 'theme_button'):
            self.auxiliary_window._update_theme_icon()
        
        # 打印主题切换状态
        print(f"已成功应用{'深色' if is_dark else '浅色'}主题到应用程序")

    def toggle_theme(self):
        """切换应用程序主题"""
        # 获取当前应用程序实例
        app = QApplication.instance()
        
        # 获取主题管理器
        if hasattr(app, 'theme_manager'):
            # 切换主题
            app.theme_manager.toggle_theme(app)
            print(f"已切换主题为: {app.theme_manager.current_theme}")
            
            # 更新窗口样式和图标
            self.apply_theme_to_windows()
        else:
            print("警告：未找到主题管理器") 