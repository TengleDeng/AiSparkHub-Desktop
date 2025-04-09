#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库管理类 - 管理SQLite数据库的连接和操作
"""

import os
import json
import sqlite3
from datetime import datetime

class DatabaseManager:
    """数据库管理类 - 管理SQLite数据库的连接和操作"""
    
    def __init__(self, db_path="data/prompts.db"):
        """初始化数据库管理器"""
        # 确保数据目录存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # 连接数据库
        self.conn = sqlite3.connect(db_path)
        # 将查询结果作为字典返回
        self.conn.row_factory = sqlite3.Row
        # 启用外键支持
        self.conn.execute("PRAGMA foreign_keys = ON")
        
        # 初始化数据库
        self.init_database()
    
    def init_database(self):
        """初始化数据库表结构"""
        cursor = self.conn.cursor()
        
        # 创建提示词历史表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS prompt_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prompt_text TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            ai_targets TEXT
        )
        ''')
        
        self.conn.commit()
    
    def add_prompt(self, prompt_text, ai_targets):
        """添加提示词记录到数据库
        
        Args:
            prompt_text (str): 提示词文本
            ai_targets (list): 目标AI列表
        
        Returns:
            int: 新记录的ID
        """
        cursor = self.conn.cursor()
        
        # 将AI目标列表转换为JSON字符串
        ai_targets_json = json.dumps(ai_targets)
        
        # 插入记录
        cursor.execute(
            "INSERT INTO prompt_history (prompt_text, ai_targets) VALUES (?, ?)",
            (prompt_text, ai_targets_json)
        )
        
        self.conn.commit()
        return cursor.lastrowid
    
    def get_prompt_history(self, limit=50):
        """获取提示词历史记录
        
        Args:
            limit (int): 最大记录数
        
        Returns:
            list: 历史记录列表
        """
        cursor = self.conn.cursor()
        
        cursor.execute(
            "SELECT id, prompt_text, timestamp, ai_targets FROM prompt_history ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        )
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'id': row['id'],
                'prompt_text': row['prompt_text'],
                'timestamp': row['timestamp'],
                'ai_targets': json.loads(row['ai_targets'])
            })
        
        return results
    
    def search_prompts(self, search_text, limit=50):
        """搜索提示词历史记录
        
        Args:
            search_text (str): 搜索文本
            limit (int): 最大记录数
        
        Returns:
            list: 匹配的历史记录列表
        """
        cursor = self.conn.cursor()
        
        search_pattern = f"%{search_text}%"
        cursor.execute(
            "SELECT id, prompt_text, timestamp, ai_targets FROM prompt_history WHERE prompt_text LIKE ? ORDER BY timestamp DESC LIMIT ?",
            (search_pattern, limit)
        )
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'id': row['id'],
                'prompt_text': row['prompt_text'],
                'timestamp': row['timestamp'],
                'ai_targets': json.loads(row['ai_targets'])
            })
        
        return results
    
    def close_connection(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close() 