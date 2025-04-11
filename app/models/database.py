#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
数据库管理类 - 管理SQLite数据库的连接和操作
"""

import os
import json
import sqlite3
import sys
from pathlib import Path
from datetime import datetime

class DatabaseManager:
    """数据库管理类 - 管理SQLite数据库的连接和操作"""
    
    def __init__(self, db_name="prompts.db"):
        """初始化数据库管理器"""
        # 获取应用数据目录
        data_dir = self._get_data_directory()
        db_path = os.path.join(data_dir, db_name)
        
        # 安全创建目录 - 如果不使用主程序的预创建目录功能，这里确保目录存在
        # 在大多数情况下，这个目录已经被主程序创建
        try:
            if not os.path.exists(data_dir):
                os.makedirs(data_dir, exist_ok=True)
                print(f"数据库管理器创建目录: {data_dir}")
        except (PermissionError, OSError) as e:
            print(f"警告: 无法创建数据库目录 '{data_dir}': {e}")
            # 尝试回退到临时目录
            import tempfile
            data_dir = tempfile.gettempdir()
            db_path = os.path.join(data_dir, db_name)
            print(f"回退到临时目录: {data_dir}")
        
        try:
            # 连接数据库
            self.conn = sqlite3.connect(db_path)
            # 将查询结果作为字典返回
            self.conn.row_factory = sqlite3.Row
            # 启用外键支持
            self.conn.execute("PRAGMA foreign_keys = ON")
            
            # 初始化数据库
            self.init_database()
        except sqlite3.Error as e:
            print(f"数据库连接错误: {e}")
            self.conn = None  # 确保连接失败时设置为None，避免后续错误
    
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
                return os.path.join(base_dir, app_name, "database")
            elif sys.platform == 'darwin':
                # macOS: ~/Library/Application Support/AiSparkHub
                return os.path.join(str(Path.home()), "Library", "Application Support", app_name, "database")
            else:
                # Linux: ~/.local/share/AiSparkHub
                return os.path.join(str(Path.home()), ".local", "share", app_name, "database")
        else:
            # 开发环境直接使用项目目录下的data文件夹
            data_dir = os.path.abspath("data")
            return os.path.join(data_dir, "database")
        
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
        
        # 创建新的提示词详细记录表，存储URL和回复内容
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS prompt_details (
            id TEXT PRIMARY KEY,
            prompt TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            ai1_url TEXT DEFAULT '',
            ai1_reply TEXT DEFAULT '',
            ai2_url TEXT DEFAULT '',
            ai2_reply TEXT DEFAULT '',
            ai3_url TEXT DEFAULT '',
            ai3_reply TEXT DEFAULT '',
            ai4_url TEXT DEFAULT '',
            ai4_reply TEXT DEFAULT '',
            ai5_url TEXT DEFAULT '',
            ai5_reply TEXT DEFAULT '',
            ai6_url TEXT DEFAULT '',
            ai6_reply TEXT DEFAULT '',
            favorite BOOLEAN DEFAULT 0
        )
        ''')
        
        self.conn.commit()
    
    def add_prompt(self, prompt_text, ai_targets):
        """添加提示词记录到数据库 (兼容旧版本)
        
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
    
    def add_prompt_details(self, prompt_id, prompt_text, timestamp, webviews, favorite=False):
        """添加详细的提示词记录，包含URL和回复内容
        
        Args:
            prompt_id (str): 提示词ID (通常是时间戳字符串)
            prompt_text (str): 提示词文本
            timestamp (int): 时间戳
            webviews (list): WebView信息列表，每项包含url和reply
            favorite (bool): 是否收藏
            
        Returns:
            bool: 是否成功
        """
        cursor = self.conn.cursor()
        
        try:
            # 准备插入参数
            params = {
                "id": prompt_id,
                "prompt": prompt_text,
                "timestamp": timestamp,
                "favorite": 1 if favorite else 0
            }
            
            # 为每个webview添加对应的URL和回复内容
            for i, webview in enumerate(webviews, 1):
                if i > 6:  # 最多保存6个AI的数据
                    break
                
                ai_url = webview.get("url", "")
                ai_reply = webview.get("reply", "")
                
                params[f"ai{i}_url"] = ai_url
                params[f"ai{i}_reply"] = ai_reply
            
            # 构建SQL语句
            fields = ["id", "prompt", "timestamp"]
            placeholders = ["?", "?", "?"]
            values = [prompt_id, prompt_text, timestamp]
            
            # 添加AI字段
            for i in range(1, 7):
                if f"ai{i}_url" in params:
                    fields.append(f"ai{i}_url")
                    placeholders.append("?")
                    values.append(params[f"ai{i}_url"])
                    
                    fields.append(f"ai{i}_reply")
                    placeholders.append("?")
                    values.append(params[f"ai{i}_reply"])
            
            # 添加favorite字段
            fields.append("favorite")
            placeholders.append("?")
            values.append(params["favorite"])
            
            # 构建完整SQL
            sql = f"REPLACE INTO prompt_details ({', '.join(fields)}) VALUES ({', '.join(placeholders)})"
            
            # 执行SQL
            cursor.execute(sql, values)
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"保存提示词详细信息失败: {e}")
            return False
    
    def get_prompt_details(self, prompt_id):
        """获取指定ID的提示词详细信息
        
        Args:
            prompt_id (str): 提示词ID
            
        Returns:
            dict: 提示词详细信息
        """
        cursor = self.conn.cursor()
        
        cursor.execute(
            "SELECT * FROM prompt_details WHERE id = ?",
            (prompt_id,)
        )
        
        row = cursor.fetchone()
        if row:
            result = {
                'id': row['id'],
                'prompt': row['prompt'],
                'timestamp': row['timestamp'],
                'favorite': bool(row['favorite']),
                'webviews': []
            }
            
            # 构建webviews列表
            for i in range(1, 7):
                url_key = f"ai{i}_url"
                reply_key = f"ai{i}_reply"
                
                if url_key in row and row[url_key]:
                    result['webviews'].append({
                        'url': row[url_key],
                        'reply': row[reply_key] if reply_key in row else ''
                    })
            
            return result
        
        return None
    
    def get_all_prompt_details(self, limit=50):
        """获取所有提示词详细信息
        
        Args:
            limit (int): 最大记录数
            
        Returns:
            list: 提示词详细信息列表
        """
        cursor = self.conn.cursor()
        
        cursor.execute(
            "SELECT * FROM prompt_details ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        )
        
        results = []
        for row in cursor.fetchall():
            result = {
                'id': row['id'],
                'prompt': row['prompt'],
                'timestamp': row['timestamp'],
                'favorite': bool(row['favorite']),
                'webviews': []
            }
            
            # 构建webviews列表
            for i in range(1, 7):
                url_key = f"ai{i}_url"
                reply_key = f"ai{i}_reply"
                
                if url_key in row and row[url_key]:
                    result['webviews'].append({
                        'url': row[url_key],
                        'reply': row[reply_key] if reply_key in row else ''
                    })
            
            results.append(result)
        
        return results
        
    def search_prompt_details(self, search_text, limit=50):
        """搜索提示词详细信息
        
        Args:
            search_text (str): 搜索文本
            limit (int): 最大记录数
            
        Returns:
            list: 匹配的提示词详细信息列表
        """
        cursor = self.conn.cursor()
        
        search_pattern = f"%{search_text}%"
        cursor.execute(
            "SELECT * FROM prompt_details WHERE prompt LIKE ? ORDER BY timestamp DESC LIMIT ?",
            (search_pattern, limit)
        )
        
        results = []
        for row in cursor.fetchall():
            result = {
                'id': row['id'],
                'prompt': row['prompt'],
                'timestamp': row['timestamp'],
                'favorite': bool(row['favorite']),
                'webviews': []
            }
            
            # 构建webviews列表
            for i in range(1, 7):
                url_key = f"ai{i}_url"
                reply_key = f"ai{i}_reply"
                
                if url_key in row and row[url_key]:
                    result['webviews'].append({
                        'url': row[url_key],
                        'reply': row[reply_key] if reply_key in row else ''
                    })
            
            results.append(result)
        
        return results
    
    def toggle_prompt_favorite(self, prompt_id):
        """切换提示词收藏状态
        
        Args:
            prompt_id (str): 提示词ID
            
        Returns:
            bool: 新的收藏状态
        """
        cursor = self.conn.cursor()
        
        # 获取当前状态
        cursor.execute("SELECT favorite FROM prompt_details WHERE id = ?", (prompt_id,))
        row = cursor.fetchone()
        if not row:
            return False
            
        # 切换状态
        new_state = not bool(row['favorite'])
        cursor.execute(
            "UPDATE prompt_details SET favorite = ? WHERE id = ?",
            (1 if new_state else 0, prompt_id)
        )
        
        self.conn.commit()
        return new_state
    
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