#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
设置管理器 - 管理用户设置和配置
负责读取、保存用户设置，并提供访问接口
"""

import os
import json
from app.config import USER_SETTINGS_PATH, DEFAULT_USER_SETTINGS, SUPPORTED_AI_PLATFORMS

class SettingsManager:
    """用户设置管理器，负责处理用户配置信息"""
    
    _instance = None  # 单例模式
    
    def __new__(cls):
        """实现单例模式"""
        if cls._instance is None:
            cls._instance = super(SettingsManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """初始化设置管理器"""
        # 防止重复初始化
        if self._initialized:
            return
        
        # 确保设置文件目录存在
        os.makedirs(os.path.dirname(USER_SETTINGS_PATH), exist_ok=True)
        
        # 加载设置
        self.settings = self.load_settings()
        
        self._initialized = True
    
    def load_settings(self):
        """从文件加载设置，如果文件不存在则使用默认设置
        
        Returns:
            dict: 用户设置字典
        """
        if os.path.exists(USER_SETTINGS_PATH):
            try:
                with open(USER_SETTINGS_PATH, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                
                # 确保所有默认设置项都存在
                for key, value in DEFAULT_USER_SETTINGS.items():
                    if key not in settings:
                        settings[key] = value
                
                return settings
            except Exception as e:
                print(f"加载设置文件失败: {e}")
                return DEFAULT_USER_SETTINGS.copy()
        else:
            # 文件不存在，使用默认设置
            return DEFAULT_USER_SETTINGS.copy()
    
    def save_settings(self):
        """保存设置到文件"""
        try:
            with open(USER_SETTINGS_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            print(f"保存设置文件失败: {e}")
            return False
    
    def get_setting(self, key, default=None):
        """获取指定设置项
        
        Args:
            key (str): 设置项键名
            default: 默认值，如果设置项不存在则返回此值
        
        Returns:
            设置项的值
        """
        return self.settings.get(key, default)
    
    def set_setting(self, key, value):
        """设置指定设置项
        
        Args:
            key (str): 设置项键名
            value: 设置项的值
        
        Returns:
            bool: 是否成功设置
        """
        self.settings[key] = value
        return self.save_settings()
    
    def get_enabled_ai_platforms(self):
        """获取用户启用的AI平台列表
        
        Returns:
            list: 启用的AI平台配置列表
        """
        enabled_keys = self.get_setting('enabled_ai_platforms', DEFAULT_USER_SETTINGS['enabled_ai_platforms'])
        
        # 检查是否在支持的平台中
        valid_platforms = []
        for key in enabled_keys:
            if key in SUPPORTED_AI_PLATFORMS:
                valid_platforms.append(SUPPORTED_AI_PLATFORMS[key])
        
        # 限制最大AI视图数量
        max_views = self.get_setting('max_ai_views', DEFAULT_USER_SETTINGS['max_ai_views'])
        return valid_platforms[:max_views]
    
    def set_enabled_ai_platforms(self, platform_keys):
        """设置用户启用的AI平台列表
        
        Args:
            platform_keys (list): AI平台键名列表
        
        Returns:
            bool: 是否成功设置
        """
        # 验证平台键名是否有效
        valid_keys = [key for key in platform_keys if key in SUPPORTED_AI_PLATFORMS]
        return self.set_setting('enabled_ai_platforms', valid_keys)
    
    def get_max_ai_views(self):
        """获取最大AI视图数量
        
        Returns:
            int: 最大AI视图数量
        """
        return self.get_setting('max_ai_views', DEFAULT_USER_SETTINGS['max_ai_views'])
    
    def set_max_ai_views(self, max_views):
        """设置最大AI视图数量
        
        Args:
            max_views (int): 最大AI视图数量，范围1-5
        
        Returns:
            bool: 是否成功设置
        """
        # 确保值在合理范围内
        max_views = max(1, min(5, max_views))
        return self.set_setting('max_ai_views', max_views) 