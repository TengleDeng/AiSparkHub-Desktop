#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
WebProfileManager - 管理网页浏览相关的配置文件
负责管理cookies，缓存等网页数据的持久化存储
"""

import os
import sys
from pathlib import Path
from PyQt6.QtWebEngineCore import QWebEngineProfile

class WebProfileManager:
    """Web配置文件管理器，用于管理cookies、缓存等网页数据"""
    
    _instance = None  # 单例模式
    
    def __new__(cls):
        """实现单例模式"""
        if cls._instance is None:
            cls._instance = super(WebProfileManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """初始化Web配置文件管理器"""
        # 防止重复初始化
        if self._initialized:
            return
        
        # 确定数据存储路径
        self.data_dir = self._get_data_directory()
        
        # 确保存储目录存在
        os.makedirs(self.data_dir, exist_ok=True)
        
        # 创建持久化配置文件
        self.profile = QWebEngineProfile("AiSparkHub")
        
        # 设置持久化存储路径
        self.profile.setPersistentStoragePath(os.path.join(self.data_dir, "webdata"))
        self.profile.setCachePath(os.path.join(self.data_dir, "cache"))
        
        # 启用持久化cookie存储
        self.profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies)
        
        self._initialized = True
    
    def _get_data_directory(self):
        """获取应用数据目录
        
        根据不同操作系统获取合适的用户数据目录
        
        Returns:
            str: 应用数据目录路径
        """
        # 应用名称
        app_name = "AiSparkHub"
        
        # 运行在打包环境中
        if getattr(sys, 'frozen', False):
            # PyInstaller打包环境
            if sys.platform == 'win32':
                # Windows: %APPDATA%\AiSparkHub
                base_dir = os.environ.get('APPDATA', '')
                return os.path.join(base_dir, app_name)
            elif sys.platform == 'darwin':
                # macOS: ~/Library/Application Support/AiSparkHub
                return os.path.join(str(Path.home()), "Library", "Application Support", app_name)
            else:
                # Linux: ~/.local/share/AiSparkHub
                return os.path.join(str(Path.home()), ".local", "share", app_name)
        else:
            # 开发环境直接使用项目目录下的data文件夹
            return os.path.abspath("data")
    
    def get_profile(self):
        """获取Web配置文件
        
        Returns:
            QWebEngineProfile: 配置文件对象
        """
        return self.profile
    
    def clear_browsing_data(self):
        """清除浏览数据（cookies、缓存等）"""
        # 清除所有cookies
        cookie_store = self.profile.cookieStore()
        cookie_store.deleteAllCookies()
        
        # 清除HTTP缓存
        self.profile.clearHttpCache() 