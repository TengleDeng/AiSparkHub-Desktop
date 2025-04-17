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
import time
from urllib.parse import urlparse
import hashlib
from PyQt6.QtCore import QObject, QFileSystemWatcher, pyqtSignal
from watchdog.observers import Observer
import jieba  # 添加jieba分词库
import re
import uuid

class PKMFileWatcher(QObject):
    """PKM文件监控类，监控所有支持的文件格式变化"""
    
    # 定义文件变化信号
    file_added = pyqtSignal(str)  # 文件添加
    file_modified = pyqtSignal(str)  # 文件修改
    file_deleted = pyqtSignal(str)  # 文件删除
    scan_completed = pyqtSignal(dict)  # 扫描完成
    
    def __init__(self, db_manager, parent=None):
        """初始化文件监控器
        
        Args:
            db_manager: 数据库管理器实例
            parent: 父QObject
        """
        super().__init__(parent)
        self.db_manager = db_manager
        
        # 文件系统监视器
        self.watcher = QFileSystemWatcher()
        self.watcher.directoryChanged.connect(self._handle_directory_changed)
        self.watcher.fileChanged.connect(self._handle_file_changed)
        
        # 已知文件列表
        self.known_files = set()
        
        # 文件变化保护，防止重复处理
        self._last_changes = {}
        self._debounce_time = 1.0  # 防抖时间（秒）
        
        # 信号连接状态
        self._signals_connected = False
        
        # 连接信号到数据库处理函数
        self._connect_signals()
    
    def _connect_signals(self):
        """连接信号到数据库处理函数"""
        if not self._signals_connected:
            try:
                # 先断开已有连接，避免重复连接
                try:
                    self.file_added.disconnect(self._on_file_added)
                    self.file_modified.disconnect(self._on_file_modified)
                    self.file_deleted.disconnect(self._on_file_deleted)
                except (TypeError, RuntimeError):
                    # 如果未连接，忽略错误
                    pass
                
                # 仅连接到数据库更新函数，不连接UI更新函数
                self.file_added.connect(self._on_file_added)
                self.file_modified.connect(self._on_file_modified)
                self.file_deleted.connect(self._on_file_deleted)
                self._signals_connected = True
                print("文件监控信号已连接到数据库处理函数")
            except Exception as e:
                print(f"连接文件监控信号出错: {e}")
    
    def reconnect_signals(self):
        """重新连接信号处理函数，用于在外部断开连接后恢复"""
        self._connect_signals()
        return self._signals_connected
    
    def start_monitoring(self, folders):
        """开始监控文件夹
        
        Args:
            folders: 要监控的文件夹路径列表
            
        Returns:
            bool: 成功返回True，失败返回False
        """
        try:
            # 如果已经在监控，先停止
            if self.watcher.directories() or self.watcher.files():
                self.stop_monitoring()
            
            print(f"开始监控文件夹: {folders}")
            
            # 记录需要监控的所有文件和目录
            dirs_to_monitor = []
            files_to_monitor = []
            
            # 遍历所有文件夹，收集需要监控的文件和目录
            for folder in folders:
                if not folder or not os.path.exists(folder):
                    print(f"无法监控不存在的文件夹: {folder}")
                    continue
                
                # 添加根目录
                dirs_to_monitor.append(folder)
                
                # 递归添加所有子目录和文件
                for root, dirs, files in os.walk(folder):
                    # 添加所有子目录
                    for dir_name in dirs:
                        dir_path = os.path.join(root, dir_name)
                        dirs_to_monitor.append(dir_path)
                    
                    # 记录所有支持的文件
                    for file_name in files:
                        file_path = os.path.join(root, file_name)
                        if self.db_manager.is_supported_extension(file_path):
                            self.known_files.add(file_path)
                            files_to_monitor.append(file_path)
            
            # 批量添加所有目录到监控
            if dirs_to_monitor:
                self.watcher.addPaths(dirs_to_monitor)
                
            # 批量添加所有文件到监控
            if files_to_monitor:
                self.watcher.addPaths(files_to_monitor)
            
            # 输出支持的文件格式统计
            format_counts = {}
            for file_path in files_to_monitor:
                format_name = self.db_manager.get_format_for_extension(file_path) or "unknown"
                if format_name not in format_counts:
                    format_counts[format_name] = 0
                format_counts[format_name] += 1
            
            format_stat = ", ".join([f"{format}: {count}个" for format, count in format_counts.items()])
            print(f"共监控 {len(self.watcher.directories())} 个目录和 {len(self.watcher.files())} 个文件 ({format_stat})")
            return True
            
        except Exception as e:
            print(f"启动文件监控出错: {e}")
            return False
    
    def stop_monitoring(self):
        """停止监控"""
        # 移除所有已监控的目录和文件
        directories = self.watcher.directories()
        if directories:
            self.watcher.removePaths(directories)
            
        files = self.watcher.files()
        if files:
            self.watcher.removePaths(files)
            
        self.known_files.clear()
        self._last_changes.clear()
        
        print("已停止所有文件监控")
    
    def _handle_directory_changed(self, path):
        """处理目录变化
        
        Args:
            path: 发生变化的目录路径
        """
        try:
            # 防抖处理
            current_time = time.time()
            if path in self._last_changes and current_time - self._last_changes[path] < self._debounce_time:
                return
            self._last_changes[path] = current_time
            
            # 检查新增和删除的文件
            current_files = set()
            
            # 获取目录中当前所有支持的文件
            try:
                for file_name in os.listdir(path):
                    file_path = os.path.join(path, file_name)
                    if not os.path.isdir(file_path) and self.db_manager.is_supported_extension(file_path):
                        current_files.add(file_path)
                        
                        # 如果是新文件，添加到监控并触发添加事件
                        if file_path not in self.known_files:
                            self.known_files.add(file_path)
                            self.watcher.addPath(file_path)
                            self.file_added.emit(file_path)
            except (FileNotFoundError, PermissionError):
                # 目录可能已被删除或无权访问
                pass
            
            # 检查已知文件中不再存在的文件
            dir_known_files = {f for f in self.known_files if os.path.dirname(f) == path}
            for file_path in dir_known_files - current_files:
                self.known_files.remove(file_path)
                if file_path in self.watcher.files():
                    self.watcher.removePath(file_path)
                self.file_deleted.emit(file_path)
            
            # 检查目录结构变化（新增子目录）
            try:
                for dir_name in os.listdir(path):
                    dir_path = os.path.join(path, dir_name)
                    if os.path.isdir(dir_path) and dir_path not in self.watcher.directories():
                        self.watcher.addPath(dir_path)
                        
                        # 递归添加新目录中的所有子目录和支持的文件
                        for root, dirs, files in os.walk(dir_path):
                            for sub_dir in dirs:
                                sub_dir_path = os.path.join(root, sub_dir)
                                self.watcher.addPath(sub_dir_path)
                            
                            for file_name in files:
                                file_path = os.path.join(root, file_name)
                                if self.db_manager.is_supported_extension(file_path):
                                    self.known_files.add(file_path)
                                    self.watcher.addPath(file_path)
                                    self.file_added.emit(file_path)
            except (FileNotFoundError, PermissionError):
                # 目录可能已被删除或无权访问
                pass
            
        except Exception as e:
            print(f"处理目录变化出错 ({path}): {e}")
    
    def _handle_file_changed(self, path):
        """处理文件变化
        
        Args:
            path: 发生变化的文件路径
        """
        try:
            # 防抖处理
            current_time = time.time()
            if path in self._last_changes and current_time - self._last_changes[path] < self._debounce_time:
                return
            self._last_changes[path] = current_time
            
            # 检查文件是否仍然存在
            if os.path.exists(path):
                # 文件被修改
                self.file_modified.emit(path)
            else:
                # 文件被删除
                if path in self.known_files:
                    self.known_files.remove(path)
                self.file_deleted.emit(path)
        
        except Exception as e:
            print(f"处理文件变化出错 ({path}): {e}")
    
    def scan_files(self):
        """扫描所有文件，更新数据库"""
        result = self.db_manager.scan_pkm_folder()
        self.scan_completed.emit(result)
    
    def _on_file_added(self, file_path):
        """处理文件添加事件"""
        # 仅处理支持的文件格式
        if self.db_manager.is_supported_extension(file_path):
            format_name = self.db_manager.get_format_for_extension(file_path) or "unknown"
            print(f"文件添加({format_name}): {file_path}")
            self.db_manager.add_or_update_pkm_file(file_path)
    
    def _on_file_modified(self, file_path):
        """处理文件修改事件"""
        # 仅处理支持的文件格式
        if self.db_manager.is_supported_extension(file_path):
            format_name = self.db_manager.get_format_for_extension(file_path) or "unknown"
            print(f"文件修改({format_name}): {file_path}")
            self.db_manager.add_or_update_pkm_file(file_path)
    
    def _on_file_deleted(self, file_path):
        """处理文件删除事件"""
        format_name = self.db_manager.get_format_for_extension(file_path) or "unknown"
        print(f"文件删除({format_name}): {file_path}")
        self.db_manager.delete_pkm_file(file_path)

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
        
        # 定义支持的文件格式
        self.supported_file_formats = {
            "markdown": {
                "extensions": [".md", ".markdown"],
                "enabled": True,
                "description": "Markdown文件"
            },
            "html": {
                "extensions": [".html", ".htm"],
                "enabled": False,
                "description": "HTML文件"
            },
            "text": {
                "extensions": [".txt", ".text"],
                "enabled": False,
                "description": "纯文本文件"
            },
            "docx": {
                "extensions": [".docx", ".doc"],
                "enabled": False,
                "description": "Word文档"
            },
            "pdf": {
                "extensions": [".pdf"],
                "enabled": False,
                "description": "PDF文件"
            },
            "pptx": {
                "extensions": [".pptx", ".ppt"],
                "enabled": False,
                "description": "PowerPoint演示文稿"
            },
            "xlsx": {
                "extensions": [".xlsx", ".xls"],
                "enabled": False,
                "description": "Excel表格"
            }
        }
        
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
            
        # PKM文件监控文件夹路径
        self.pkm_folder = None
        self.pkm_folders = []
        self.load_pkm_settings()
        
        # 创建文件监控器
        self.file_watcher = PKMFileWatcher(self)
        
        # 定时检查文件监控信号连接
        from PyQt6.QtCore import QTimer
        self._signal_check_timer = QTimer()
        self._signal_check_timer.timeout.connect(self._check_watcher_signals)
        self._signal_check_timer.start(30000)  # 每30秒检查一次信号连接
        
        # 如果已配置PKM文件夹，启动监控
        existing_folders = [folder for folder in self.pkm_folders if os.path.exists(folder)]
        if existing_folders:
            # 一次性启动所有文件夹的监控
            self.file_watcher.start_monitoring(existing_folders)
        elif self.pkm_folder and os.path.exists(self.pkm_folder):
            # 兼容旧版本单文件夹配置
            self.file_watcher.start_monitoring([self.pkm_folder])
    
    def _check_watcher_signals(self):
        """检查文件监控信号是否连接，如果断开则重新连接"""
        # 通过_signals_connected标志检查连接状态
        if hasattr(self, 'file_watcher') and not getattr(self.file_watcher, '_signals_connected', False):
            print("发现文件监控信号已断开，正在重新连接...")
            self.file_watcher.reconnect_signals()
    
    def _get_data_directory(self):
        """获取应用数据目录
        
        根据不同操作系统获取合适的用户数据目录
        
        Returns:
            str: 应用数据目录路径
        """
        # 获取项目根目录下的data/database目录（优先使用此路径）
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        data_dir = os.path.join(base_dir, "data", "database")
        
        # 如果data目录存在，直接使用此路径
        if os.path.exists(os.path.dirname(data_dir)):
            return data_dir
            
        # 应用名称
        app_name = "AiSparkHub"
        
        # 如果data目录不存在，才使用系统目录
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
            # 开发环境使用项目目录下的data/database文件夹（这是备用路径，通常不会走到这里）
            return data_dir
        
    def init_database(self):
        """初始化数据库，创建必要的表"""
        try:
            cursor = self.conn.cursor()
            
            # 创建提示词表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS prompts (
                id TEXT PRIMARY KEY,
                prompt TEXT,
                timestamp INTEGER,
                ai_targets TEXT
            )
            ''')
            
            # 创建提示词详情表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS prompt_details (
                id TEXT PRIMARY KEY,
                prompt TEXT,
                timestamp INTEGER,
                favorite INTEGER DEFAULT 0,
                ai1_url TEXT,
                ai1_reply TEXT,
                ai2_url TEXT,
                ai2_reply TEXT,
                ai3_url TEXT,
                ai3_reply TEXT,
                ai4_url TEXT,
                ai4_reply TEXT,
                ai5_url TEXT,
                ai5_reply TEXT,
                ai6_url TEXT,
                ai6_reply TEXT
            )
            ''')
            
            # 创建PKM文件夹表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS pkm_folders (
                id TEXT PRIMARY KEY,
                folder_path TEXT UNIQUE,
                enabled INTEGER DEFAULT 1,
                created_at INTEGER
            )
            ''')
            
            # 创建PKM文件表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS pkm_files (
                id TEXT PRIMARY KEY,
                file_path TEXT UNIQUE,
                file_name TEXT,
                title TEXT,
                content TEXT,
                tags TEXT,
                hash TEXT,
                file_format TEXT,
                created_at INTEGER,
                updated_at INTEGER,
                last_modified INTEGER
            )
            ''')
            
            # 创建PKM文件全文检索表 (FTS5)
            # 注意：这是一个虚拟表，仅用于索引和搜索
            cursor.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS pkm_fts USING fts5(
                id UNINDEXED,  -- ID字段不进行索引
                title,         -- 标题
                content,       -- 内容
                tags,          -- 标签
                file_name      -- 文件名
            )
            ''')
            
            # 添加索引以提高搜索性能
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_pkm_title ON pkm_files(title)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_pkm_tags ON pkm_files(tags)')
            
            self.conn.commit()
            print("数据库初始化成功")
        except Exception as e:
            print(f"初始化数据库出错: {e}")
            if self.conn:
                self.conn.rollback()
            raise e
            
        # 检查是否需要为现有PKM文件填充FTS表
        self._populate_fts_for_existing_files()
    
    def _populate_fts_for_existing_files(self):
        """检查FTS表是否为空，如果是，则用现有PKM文件填充"""
        if not self.conn:
            print("数据库未连接")
            return
            
        try:
            cursor = self.conn.cursor()
            
            # 检查pkm_fts表是否为空
            cursor.execute("SELECT COUNT(*) FROM pkm_fts")
            count = cursor.fetchone()[0]
            
            if count == 0:
                print("FTS表为空，正在填充现有文件...")
                
                # 查询所有PKM文件记录
                cursor.execute("""
                    SELECT id, title, file_path, file_name, content, tags, created_at, updated_at, file_format, hash
                    FROM pkm_files
                """)
                files = cursor.fetchall()
                
                # 开始事务
                self.conn.execute("BEGIN TRANSACTION")
                
                # 为每个文件创建FTS条目
                insert_cursor = self.conn.cursor()
                for file in files:
                    id, title, file_path, file_name, content, tags, created_at, updated_at, file_format, hash = file
                    
                    # 处理内容进行FTS索引
                    processed_title = self.process_text_for_fts(title) if title else ""
                    processed_content = self.process_text_for_fts(content) if content else ""
                    processed_tags = self.process_text_for_fts(tags) if tags else ""
                    
                    # 插入FTS表
                    insert_cursor.execute("""
                        INSERT INTO pkm_fts (id, title, content, tags, file_name)
                        VALUES (?, ?, ?, ?, ?)
                    """, (id, processed_title, processed_content, processed_tags, file_name))
                
                # 提交事务
                self.conn.execute("COMMIT")
                print(f"成功将 {len(files)} 个文件添加到FTS索引")
                
        except Exception as e:
            # 回滚事务
            if self.conn:
                self.conn.execute("ROLLBACK")
            print(f"填充FTS索引时出错: {e}")
            import traceback
            traceback.print_exc()
    
    def add_prompt(self, prompt_text, ai_targets):
        """添加提示词记录到数据库 (兼容旧版本，直接转为添加到prompt_details表)
        
        Args:
            prompt_text (str): 提示词文本
            ai_targets (list): 目标AI列表
        
        Returns:
            str: 新记录的ID
        """
        # 生成唯一的提示词ID（基于时间戳）
        prompt_id = str(int(time.time() * 1000))
        timestamp = int(time.time())
        
        # 创建一个空的webviews列表
        webviews = []
        
        # 调用add_prompt_details方法添加记录
        success = self.add_prompt_details(prompt_id, prompt_text, timestamp, webviews, False)
        
        return prompt_id if success else None
    
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
        """搜索提示词和AI回复详细信息
        
        Args:
            search_text (str): 搜索文本
            limit (int): 最大记录数
            
        Returns:
            list: 匹配的提示词详细信息列表
        """
        cursor = self.conn.cursor()
        
        search_pattern = f"%{search_text}%"
        cursor.execute(
            """SELECT * FROM prompt_details 
               WHERE prompt LIKE ? 
               OR ai1_reply LIKE ? 
               OR ai2_reply LIKE ? 
               OR ai3_reply LIKE ? 
               OR ai4_reply LIKE ? 
               OR ai5_reply LIKE ? 
               OR ai6_reply LIKE ? 
               ORDER BY timestamp DESC LIMIT ?""",
            (search_pattern, search_pattern, search_pattern, 
             search_pattern, search_pattern, search_pattern, 
             search_pattern, limit)
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
        """获取提示词历史记录（从prompt_details表获取）
        
        Args:
            limit (int): 最大记录数
        
        Returns:
            list: 历史记录列表
        """
        cursor = self.conn.cursor()
        
        cursor.execute(
            """SELECT id, prompt, timestamp, favorite, 
               ai1_url, ai2_url, ai3_url, ai4_url, ai5_url, ai6_url 
               FROM prompt_details ORDER BY timestamp DESC LIMIT ?""",
            (limit,)
        )
        
        results = []
        for row in cursor.fetchall():
            # 构建与旧格式兼容的记录
            # 从prompt_details表构建ai_targets列表（从webviews域名提取）
            ai_targets = []
            
            # 查询当前记录的所有webview信息
            for i in range(1, 7):
                url_key = f"ai{i}_url"
                if url_key in row and row[url_key]:
                    # 从URL提取域名作为AI标识
                    url = row[url_key]
                    try:
                        # 简单分析URL获取域名
                        domain = urlparse(url).netloc
                        # 去除www.前缀
                        if domain.startswith('www.'):
                            domain = domain[4:]
                        # 添加到ai_targets列表
                        if domain and domain not in ai_targets:
                            ai_targets.append(domain)
                    except:
                        # 如果解析失败，使用默认值
                        ai_targets.append(f"AI{i}")
            
            # 如果没有解析到任何AI，添加一个默认值
            if not ai_targets:
                ai_targets = ["未知AI"]
            
            # 安全处理时间戳
            try:
                if isinstance(row['timestamp'], int) and 0 <= row['timestamp'] <= 32503680000:  # 合理的时间戳范围(1970-3000年)
                    timestamp_str = datetime.fromtimestamp(row['timestamp']).isoformat()
                elif isinstance(row['timestamp'], str):
                    # 如果已经是字符串，直接使用
                    timestamp_str = row['timestamp']
                else:
                    # 其他情况使用当前时间
                    timestamp_str = datetime.now().isoformat()
            except (ValueError, OSError, OverflowError) as e:
                print(f"时间戳转换错误: {row['timestamp']}, {e}")
                # 发生错误时使用当前时间
                timestamp_str = datetime.now().isoformat()
            
            record = {
                'id': row['id'],
                'prompt_text': row['prompt'],
                'timestamp': timestamp_str,
                'ai_targets': ai_targets,
                'favorite': bool(row['favorite'])
            }
            
            # 添加URL字段
            for i in range(1, 7):
                url_key = f"ai{i}_url"
                if url_key in row:
                    record[url_key] = row[url_key]
            
            results.append(record)
        
        return results
    
    def search_prompts(self, search_text, limit=50):
        """搜索提示词历史记录（从prompt_details表搜索）
        
        Args:
            search_text (str): 搜索文本
            limit (int): 最大记录数
        
        Returns:
            list: 匹配的历史记录列表
        """
        cursor = self.conn.cursor()
        
        search_pattern = f"%{search_text}%"
        cursor.execute(
            """SELECT id, prompt, timestamp, favorite,
               ai1_url, ai2_url, ai3_url, ai4_url, ai5_url, ai6_url
               FROM prompt_details WHERE prompt LIKE ? ORDER BY timestamp DESC LIMIT ?""",
            (search_pattern, limit)
        )
        
        results = []
        for row in cursor.fetchall():
            # 构建与旧格式兼容的记录
            # 从prompt_details表构建ai_targets列表（从webviews域名提取）
            ai_targets = []
            
            # 查询当前记录的所有webview信息
            for i in range(1, 7):
                url_key = f"ai{i}_url"
                if url_key in row and row[url_key]:
                    # 从URL提取域名作为AI标识
                    url = row[url_key]
                    try:
                        # 简单分析URL获取域名
                        domain = urlparse(url).netloc
                        # 去除www.前缀
                        if domain.startswith('www.'):
                            domain = domain[4:]
                        # 添加到ai_targets列表
                        if domain and domain not in ai_targets:
                            ai_targets.append(domain)
                    except:
                        # 如果解析失败，使用默认值
                        ai_targets.append(f"AI{i}")
            
            # 如果没有解析到任何AI，添加一个默认值
            if not ai_targets:
                ai_targets = ["未知AI"]
            
            # 安全处理时间戳
            try:
                if isinstance(row['timestamp'], int) and 0 <= row['timestamp'] <= 32503680000:  # 合理的时间戳范围(1970-3000年)
                    timestamp_str = datetime.fromtimestamp(row['timestamp']).isoformat()
                elif isinstance(row['timestamp'], str):
                    # 如果已经是字符串，直接使用
                    timestamp_str = row['timestamp']
                else:
                    # 其他情况使用当前时间
                    timestamp_str = datetime.now().isoformat()
            except (ValueError, OSError, OverflowError) as e:
                print(f"时间戳转换错误: {row['timestamp']}, {e}")
                # 发生错误时使用当前时间
                timestamp_str = datetime.now().isoformat()
            
            record = {
                'id': row['id'],
                'prompt_text': row['prompt'],
                'timestamp': timestamp_str,
                'ai_targets': ai_targets,
                'favorite': bool(row['favorite'])
            }
            
            # 添加URL字段
            for i in range(1, 7):
                url_key = f"ai{i}_url"
                if url_key in row:
                    record[url_key] = row[url_key]
            
            results.append(record)
        
        return results
    
    def close_connection(self):
        """关闭数据库连接"""
        # 停止定时器
        if hasattr(self, '_signal_check_timer'):
            self._signal_check_timer.stop()
            
        # 停止文件监控
        if hasattr(self, 'file_watcher'):
            self.file_watcher.stop_monitoring()
            
        if self.conn:
            self.conn.close()
    
    def load_pkm_settings(self):
        """从配置文件加载PKM文件夹设置"""
        try:
            # 获取数据库所在目录的父目录作为配置目录
            db_dir = self._get_data_directory()
            config_dir = os.path.dirname(db_dir)  # 使用数据库目录的父目录
            
            # 确保配置目录存在
            os.makedirs(config_dir, exist_ok=True)
            
            # 设置文件路径
            config_file = os.path.join(config_dir, "pkm_settings.json")
            
            # 如果配置文件存在，读取配置
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    self.pkm_folder = settings.get('pkm_folder', None)
                    self.pkm_folders = settings.get('pkm_folders', [])
                    
                    # 加载文件格式设置
                    file_formats = settings.get('file_formats', None)
                    if file_formats:
                        for format_name, format_config in file_formats.items():
                            if format_name in self.supported_file_formats:
                                self.supported_file_formats[format_name]["enabled"] = format_config.get("enabled", False)
                    
                    # 兼容旧版本：如果有pkm_folder但没有pkm_folders，将pkm_folder添加到pkm_folders
                    if self.pkm_folder and not self.pkm_folders:
                        self.pkm_folders = [self.pkm_folder]
                        
                    # 加载数据库中保存的文件夹
                    if self.conn:
                        try:
                            cursor = self.conn.cursor()
                            cursor.execute("SELECT folder_path FROM pkm_folders")
                            rows = cursor.fetchall()
                            db_folders = [row['folder_path'] for row in rows]
                            
                            # 确保所有数据库中的文件夹都在pkm_folders中
                            for folder in db_folders:
                                if folder not in self.pkm_folders:
                                    self.pkm_folders.append(folder)
                        except:
                            pass
                    
                    print(f"已加载PKM文件夹设置: {len(self.pkm_folders)}个文件夹")
        except Exception as e:
            print(f"加载PKM设置出错: {e}")
            self.pkm_folder = None
            self.pkm_folders = []
    
    def save_pkm_settings(self, pkm_folders, file_formats=None):
        """保存PKM文件夹设置
        
        Args:
            pkm_folders (list): PKM文件夹路径列表
            file_formats (dict, optional): 文件格式设置
            
        Returns:
            bool: 是否保存成功
        """
        try:
            # 获取数据库所在目录的父目录作为配置目录
            db_dir = self._get_data_directory()
            config_dir = os.path.dirname(db_dir)  # 使用数据库目录的父目录
            
            # 确保配置目录存在
            os.makedirs(config_dir, exist_ok=True)
            
            # 设置文件路径
            config_file = os.path.join(config_dir, "pkm_settings.json")
            
            # 保存设置
            self.pkm_folders = pkm_folders
            self.pkm_folder = pkm_folders[0] if pkm_folders else None  # 兼容旧版本
            
            # 更新文件格式设置
            if file_formats:
                for format_name, format_config in file_formats.items():
                    if format_name in self.supported_file_formats:
                        self.supported_file_formats[format_name]["enabled"] = format_config.get("enabled", False)
            
            # 创建要保存的设置字典
            settings = {
                'pkm_folder': self.pkm_folder,
                'pkm_folders': self.pkm_folders,
                'file_formats': self.supported_file_formats
            }
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False)
            
            # 更新数据库中的文件夹记录
            if self.conn:
                cursor = self.conn.cursor()
                # 清空现有记录
                cursor.execute("DELETE FROM pkm_folders")
                
                # 添加新记录
                current_time = int(time.time())
                for folder in self.pkm_folders:
                    folder_id = hashlib.md5(folder.encode('utf-8')).hexdigest()
                    cursor.execute(
                        "INSERT INTO pkm_folders (id, folder_path, created_at) VALUES (?, ?, ?)",
                        (folder_id, folder, current_time)
                    )
                self.conn.commit()
                
            print(f"已保存PKM文件夹设置: {len(self.pkm_folders)}个文件夹")
            
            # 重新启动文件监控 - 修改这里，一次性传递所有文件夹，避免单独启停
            self.file_watcher.stop_monitoring()
            # 过滤出存在的文件夹
            existing_folders = [folder for folder in self.pkm_folders if os.path.exists(folder)]
            if existing_folders:
                # 一次性启动所有文件夹的监控
                self.file_watcher.start_monitoring(existing_folders)
            
            # 确保信号连接仍然有效
            self.file_watcher.reconnect_signals()
                
            return True
        except Exception as e:
            print(f"保存PKM设置出错: {e}")
            return False
    
    def compute_file_hash(self, file_path):
        """计算文件内容的hash值"""
        try:
            with open(file_path, 'rb') as f:
                file_data = f.read()
                return hashlib.md5(file_data).hexdigest()
        except Exception as e:
            print(f"计算文件hash出错: {e}")
            return None
    
    def extract_title_from_md(self, content):
        """从Markdown内容中提取标题"""
        try:
            # 尝试从第一个#标题提取
            lines = content.split('\n')
            for line in lines:
                if line.strip().startswith('# '):
                    return line.strip().replace('# ', '')
            
            # 如果没有#标题，尝试使用文件的第一行作为标题
            if lines and lines[0].strip():
                return lines[0].strip()
            
            # 如果还是没有，返回None
            return None
        except Exception as e:
            print(f"提取标题出错: {e}")
            return None
    
    def add_or_update_pkm_file(self, file_path):
        """添加或更新PKM文件到数据库
        
        Args:
            file_path (str): 文件路径
            
        Returns:
            str: 文件ID
        """
        if not self.conn:
            print("数据库未连接")
            return None
            
        if not os.path.exists(file_path):
            print(f"文件不存在: {file_path}")
            return None
        
        # 规范化路径
        file_path = self._normalize_path(file_path)
        
        try:
            # 计算文件哈希值
            file_hash = self.compute_file_hash(file_path)
            # 获取文件名
            file_name = os.path.basename(file_path)
            # 获取上次修改时间
            last_modified = int(os.path.getmtime(file_path))
            # 当前时间戳
            now = int(time.time())
            
            # 获取文件格式
            file_format = self.get_format_for_extension(file_path)
            if not file_format:
                file_format = "unknown"
                
            cursor = self.conn.cursor()
            
            # 检查文件是否已存在
            cursor.execute("SELECT id, hash FROM pkm_files WHERE file_path = ?", (file_path,))
            row = cursor.fetchone()
            
            # 提取文件内容
            content = ""
            title = ""
            tags = ""
            
            # 根据文件格式决定如何处理内容
            if file_format == "markdown":
                try:
                    # 读取Markdown文件内容
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 提取标题（从文件内容的第一行或文件名）
                    title = self.extract_title_from_md(content) or file_name
                    
                    # 从文件内容中提取标签（可以自定义规则）
                    # 例如 #tag1 #tag2 格式
                    tag_pattern = r'#(\w+)'
                    tags = ' '.join(re.findall(tag_pattern, content))
                    
                except Exception as e:
                    print(f"读取Markdown文件出错: {e}")
            elif file_format == "text":
                try:
                    # 普通文本文件
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 使用文件名作为标题
                    title = file_name
                    
                except Exception as e:
                    print(f"读取文本文件出错: {e}")
            # 可以添加其他文件格式的处理...
            else:
                # 对于未知格式，可以尝试以文本方式读取
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except:
                    content = f"无法读取文件内容，格式: {file_format}"
                
                title = file_name
            
            # 为FTS预处理分词
            processed_title = self.process_text_for_fts(title)
            processed_content = self.process_text_for_fts(content)
            processed_tags = self.process_text_for_fts(tags)
            processed_file_name = self.process_text_for_fts(file_name)
            
            if row:
                # 文件已存在，检查哈希值是否变化
                file_id, old_hash = row
                
                if file_hash != old_hash:
                    # 更新文件内容
                    cursor.execute("""
                        UPDATE pkm_files SET 
                        content = ?, title = ?, hash = ?, last_modified = ?, updated_at = ?, tags = ?, file_format = ?
                        WHERE id = ?
                    """, (content, title, file_hash, last_modified, now, tags, file_format, file_id))
                    
                    # 更新FTS表内容
                    cursor.execute("""
                        UPDATE pkm_fts SET
                        title = ?, content = ?, tags = ?, file_name = ?
                        WHERE id = ?
                    """, (processed_title, processed_content, processed_tags, processed_file_name, file_id))
                    
                    print(f"已更新文件: {file_path}")
                else:
                    # 文件未变化，仅更新最后修改时间
                    cursor.execute("""
                        UPDATE pkm_files SET last_modified = ?, updated_at = ? WHERE id = ?
                    """, (last_modified, now, file_id))
                    
                    print(f"文件未变化: {file_path}")
                
                self.conn.commit()
                return file_id
                
            else:
                # 新文件，添加到数据库
                file_id = str(uuid.uuid4())
                
                cursor.execute("""
                    INSERT INTO pkm_files 
                    (id, file_path, file_name, content, title, hash, last_modified, 
                    created_at, updated_at, tags, file_format)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (file_id, file_path, file_name, content, title, file_hash, 
                     last_modified, now, now, tags, file_format))
                
                # 添加到FTS表
                cursor.execute("""
                    INSERT INTO pkm_fts
                    (id, title, content, tags, file_name)
                    VALUES (?, ?, ?, ?, ?)
                """, (file_id, processed_title, processed_content, processed_tags, processed_file_name))
                
                self.conn.commit()
                print(f"已添加新文件: {file_path}")
                return file_id
                
        except Exception as e:
            print(f"添加或更新PKM文件出错: {file_path}, {str(e)}")
            if self.conn:
                self.conn.rollback()
            return None
    
    def _normalize_path(self, path):
        """标准化文件路径，确保路径格式一致
        
        Args:
            path (str): 需要标准化的路径
            
        Returns:
            str: 标准化后的路径
        """
        # 确保使用正斜杠作为路径分隔符
        normalized = path.replace('\\', '/')
        # 移除末尾的斜杠（如果有）
        if normalized.endswith('/'):
            normalized = normalized[:-1]
        return normalized
    
    def _check_path_variants(self, original_path):
        """生成可能的路径变体来尝试匹配数据库中的记录
        
        Args:
            original_path (str): 原始路径
            
        Returns:
            list: 可能的路径变体列表
        """
        variants = []
        
        # 添加原始路径
        variants.append(original_path)
        
        # 添加规范化的路径
        normalized = self._normalize_path(original_path)
        if normalized != original_path:
            variants.append(normalized)
            
        # 添加不同分隔符的变体
        if '\\' in original_path:
            variants.append(original_path.replace('\\', '/'))
        if '/' in original_path:
            variants.append(original_path.replace('/', '\\'))
            
        # 添加区分大小写的变体（适用于不区分大小写的文件系统）
        try:
            # 不区分大小写的系统上，数据库可能存储了不同大小写的路径
            if os.path.exists(original_path):
                actual_path = os.path.realpath(original_path)
                if actual_path not in variants:
                    variants.append(actual_path)
        except:
            pass
            
        return list(set(variants))  # 去重后返回
    
    def delete_pkm_file(self, file_path):
        """从数据库中删除PKM文件
        
        Args:
            file_path (str): 文件路径
            
        Returns:
            bool: 是否成功删除
        """
        if not self.conn:
            print("数据库未连接")
            return False
        
        # 规范化路径
        file_path = self._normalize_path(file_path)
        
        try:
            cursor = self.conn.cursor()
            
            # 先查询文件ID
            cursor.execute("SELECT id FROM pkm_files WHERE file_path = ?", (file_path,))
            row = cursor.fetchone()
            
            if row:
                file_id = row[0]
                
                # 删除主表记录
                cursor.execute("DELETE FROM pkm_files WHERE id = ?", (file_id,))
                
                # 同步删除FTS表记录
                cursor.execute("DELETE FROM pkm_fts WHERE id = ?", (file_id,))
                
                self.conn.commit()
                print(f"已从数据库删除文件: {file_path}")
                return True
            else:
                print(f"文件不在数据库中: {file_path}")
                return False
                
        except Exception as e:
            print(f"删除PKM文件出错: {e}")
            if self.conn:
                self.conn.rollback()
            return False
    
    def search_pkm_files(self, query, limit=50):
        """搜索PKM文件内容
        
        Args:
            query (str): 搜索查询
            limit (int): 返回结果数量限制
            
        Returns:
            list: 匹配的文件记录列表
        """
        if not self.conn:
            print("数据库未连接")
            return []
            
        try:
            cursor = self.conn.cursor()
            
            # 构建搜索模式
            search_pattern = f"%{query}%"
            
            # 首先检查file_format列是否存在
            cursor.execute("PRAGMA table_info(pkm_files)")
            columns = cursor.fetchall()
            has_file_format = any(column['name'] == 'file_format' for column in columns)
            
            # 准备查询字段
            fields = "id, file_path, file_name, title, updated_at, last_modified"
            if has_file_format:
                fields += ", file_format"
            
            # 搜索文件内容、标题和标签
            cursor.execute(f"""
                SELECT {fields}
                FROM pkm_files
                WHERE content LIKE ? OR title LIKE ? OR tags LIKE ?
                ORDER BY updated_at DESC
                LIMIT ?
            """, (search_pattern, search_pattern, search_pattern, limit))
            
            results = []
            rows = cursor.fetchall()
            for row in rows:
                # 将sqlite3.Row对象转换为普通字典，避免索引错误
                row_dict = dict(row)
                
                # 创建基本结果字典
                result = {
                    'id': row_dict.get('id', ''),
                    'file_path': row_dict.get('file_path', ''),
                    'file_name': row_dict.get('file_name', ''),
                    'title': row_dict.get('title') or row_dict.get('file_name', ''),
                    'updated_at': row_dict.get('updated_at', 0),
                    'last_modified': row_dict.get('last_modified', 0)
                }
                
                # 添加文件格式信息（如果存在）
                if has_file_format and 'file_format' in row_dict:
                    result['file_format'] = row_dict.get('file_format')
                else:
                    # 如果数据库中没有file_format字段，从文件扩展名判断
                    ext = os.path.splitext(result['file_path'])[1].lower()
                    for format_name, format_config in self.supported_file_formats.items():
                        if ext in format_config['extensions']:
                            result['file_format'] = format_name
                            break
                
                results.append(result)
                
            return results
            
        except Exception as e:
            print(f"搜索PKM文件出错: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def scan_pkm_folder(self, folders=None, callback=None):
        """扫描指定的PKM文件夹，添加或更新数据库记录
        
        Args:
            folders (list, optional): 要扫描的文件夹列表，如果为None则使用配置的文件夹
            callback (function, optional): 进度回调函数，接收一个包含统计信息的字典
            
        Returns:
            dict: 包含统计信息的字典
        """
        # 初始化统计数据
        total_stats = {
            'total_files': 0,            # 扫描的文件总数
            'added_files': 0,            # 新增的文件数
            'updated_files': 0,          # 更新的文件数
            'unchanged_files': 0,        # 未变更的文件数
            'skipped_files': 0,          # 跳过的文件数（不支持的格式）
            'failed_files': 0,           # 处理失败的文件数
            'deleted_files': 0,        # 从数据库中删除的文件数
            'format_stats': {},          # 每种文件格式的数量统计
            'progress': 0                # 当前进度（0-100）
        }
        
        # 如果没有指定文件夹，使用配置的文件夹
        if folders is None:
            if hasattr(self, 'pkm_folders') and self.pkm_folders:
                folders = self.pkm_folders
            elif hasattr(self, 'pkm_folder') and self.pkm_folder:
                folders = [self.pkm_folder]
            else:
                print("未配置PKM文件夹")
                if callback:
                    callback(total_stats)
                return total_stats
        
        # 确保folders是列表
        if isinstance(folders, str):
            folders = [folders]
        
        # 检查文件夹是否存在
        valid_folders = []
        for folder in folders:
            if os.path.exists(folder) and os.path.isdir(folder):
                valid_folders.append(folder)
            else:
                print(f"PKM文件夹不存在或不是目录: {folder}")
        
        if not valid_folders:
            print("没有有效的PKM文件夹")
            if callback:
                callback(total_stats)
            return total_stats
        
        # 获取所有支持的文件
        current_files = set()
        for folder in valid_folders:
            for root, _, files in os.walk(folder):
                for file in files:
                    if self.is_supported_extension(file):
                        file_path = os.path.join(root, file)
                        normalized_path = self._normalize_path(file_path)
                        current_files.add(normalized_path)
        
        # 获取数据库中已有的文件
        existing_files = set()
        if self.conn:
            cursor = self.conn.cursor()
            cursor.execute("SELECT file_path FROM pkm_files")
            rows = cursor.fetchall()
            for row in rows:
                # 标准化路径以确保一致性
                normalized_path = self._normalize_path(row['file_path'])
                existing_files.add(normalized_path)
        
        # 计算总文件数
        total_stats['total_files'] = len(current_files)
        
        # 处理文件
        processed_count = 0
        for file_path in current_files:
            try:
                # 检查文件类型，跳过不支持的格式
                if not self.is_supported_extension(file_path):
                    total_stats['skipped_files'] += 1
                    continue
                    
                # 添加或更新文件
                result = self.add_or_update_pkm_file(file_path)
                
                # 获取文件格式
                format_name = self.get_format_for_extension(file_path) or "unknown"
                
                # 更新统计
                if isinstance(result, dict):
                    status = result.get('status', '')
                    message = result.get('message', '无消息')
                    
                    if status == 'added':
                        total_stats['added_files'] += 1
                        print(f"文件添加成功: {file_path} - {message}")
                        # 更新格式统计
                        if format_name not in total_stats['format_stats']:
                            total_stats['format_stats'][format_name] = 0
                        total_stats['format_stats'][format_name] += 1
                    elif status == 'updated':
                        total_stats['updated_files'] += 1
                        print(f"文件更新成功: {file_path} - {message}")
                        # 更新格式统计
                        if format_name not in total_stats['format_stats']:
                            total_stats['format_stats'][format_name] = 0
                        total_stats['format_stats'][format_name] += 1
                    elif status == 'unchanged':
                        total_stats['unchanged_files'] += 1
                        print(f"文件未变更: {file_path}")
                        # 更新格式统计
                        if format_name not in total_stats['format_stats']:
                            total_stats['format_stats'][format_name] = 0
                        total_stats['format_stats'][format_name] += 1
                    elif status == 'skipped':
                        total_stats['skipped_files'] += 1
                        print(f"文件已跳过: {file_path} - {message}")
                    else:
                        # 处理其他状态（如error）
                        total_stats['failed_files'] += 1
                        print(f"文件处理失败: {file_path} - {status}: {message}")
                else:
                    # 兼容旧版逻辑，处理字符串返回值
                    if result == "added":
                        total_stats['added_files'] += 1
                        # 更新格式统计
                        if format_name not in total_stats['format_stats']:
                            total_stats['format_stats'][format_name] = 0
                        total_stats['format_stats'][format_name] += 1
                    elif result == "updated":
                        total_stats['updated_files'] += 1
                        # 更新格式统计
                        if format_name not in total_stats['format_stats']:
                            total_stats['format_stats'][format_name] = 0
                        total_stats['format_stats'][format_name] += 1
                    elif result == "unchanged":
                        total_stats['unchanged_files'] += 1
                        # 更新格式统计
                        if format_name not in total_stats['format_stats']:
                            total_stats['format_stats'][format_name] = 0
                        total_stats['format_stats'][format_name] += 1
                    else:
                        total_stats['failed_files'] += 1
                    
            except Exception as e:
                print(f"处理文件出错 {file_path}: {str(e)}")
                total_stats['failed_files'] += 1
                
            # 更新进度
            processed_count += 1
            if callback and total_stats['total_files'] > 0:
                total_stats['progress'] = int(processed_count / total_stats['total_files'] * 100)
                # 添加当前正在处理的文件路径
                total_stats['current_file'] = file_path
                callback(total_stats)
        
        # 检查并处理已删除的文件
        deleted_files = existing_files - current_files
        for file_path in deleted_files:
            try:
                # 从数据库中删除文件
                if self.delete_pkm_file(file_path):
                    total_stats['deleted_files'] += 1
                    print(f"已从数据库删除不存在的文件: {file_path}")
                    
                    # 文件格式统计调整
                    format_name = self.get_format_for_extension(file_path) or "unknown"
                    if format_name in total_stats['format_stats']:
                        # 如果已经有这种格式的文件计数，但这个文件已删除，更新统计
                        total_stats['format_stats'][format_name] -= 1
                        # 确保计数不会变为负数
                        if total_stats['format_stats'][format_name] < 0:
                            total_stats['format_stats'][format_name] = 0
            except Exception as e:
                print(f"删除文件记录出错 {file_path}: {str(e)}")
        
        # 汇总统计
        summary = (
            f"扫描完成。总文件数: {total_stats['total_files']}, "
            f"新增: {total_stats['added_files']}, "
            f"更新: {total_stats['updated_files']}, "
            f"未变更: {total_stats['unchanged_files']}, "
            f"跳过: {total_stats['skipped_files']}, "
            f"失败: {total_stats['failed_files']}, "
            f"删除: {total_stats['deleted_files']}"
        )
        print(summary)
        
        # 最终结果回调
        if callback:
            total_stats['summary'] = summary
            callback(total_stats)
            
        return total_stats
    
    def get_pkm_file_content(self, file_id):
        """获取指定文件的内容
        
        Args:
            file_id (str): 文件ID
            
        Returns:
            dict: 文件信息，包括内容
        """
        if not self.conn:
            print("数据库未连接")
            return None
            
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT id, file_path, file_name, content, title, updated_at
                FROM pkm_files
                WHERE id = ?
            """, (file_id,))
            
            row = cursor.fetchone()
            if row:
                return {
                    'id': row['id'],
                    'file_path': row['file_path'],
                    'file_name': row['file_name'],
                    'content': row['content'],
                    'title': row['title'] or row['file_name'],
                    'updated_at': row['updated_at']
                }
            return None
            
        except Exception as e:
            print(f"获取PKM文件内容出错: {e}")
            return None
    
    def search_combined(self, query, scope='all', limit=50, search_params=None):
        """组合搜索提示词和PKM文件，支持高级搜索语法
        
        Args:
            query (str): 搜索查询
            scope (str): 搜索范围 ('prompts', 'pkm', 'all')
            limit (int): 返回结果数量限制
            search_params (dict, optional): 高级搜索参数，包含以下字段:
                - terms (list): 普通搜索词列表
                - exact (list): 精确匹配词列表
                - excluded (list): 排除词列表
                - mode (str): 搜索模式，包含 "全部包含(AND)"、"任一包含(OR)" 或 "精确匹配"
            
        Returns:
            list: 匹配的记录列表，每个记录包含'type'字段 ('prompt'或'pkm')
        """
        if not self.conn:
            print("数据库未连接")
            return []
            
        results = []
        
        print(f"执行组合搜索，查询: '{query}', 范围: {scope}, 限制: {limit}")
        
        # 如果没有提供高级搜索参数，但提供了查询字符串，解析为高级搜索参数
        if query and not search_params:
            # 分词处理查询字符串，然后用作普通搜索词
            segmented_term = self.process_text_for_fts(query)
            search_params = {
                'terms': [segmented_term],
                'exact': [],
                'excluded': [],
                'mode': '任一包含(OR)' 
            }
            
            # 尝试使用高级搜索
            try:
                # 打印高级搜索参数
                print(f"转换为高级搜索参数: {search_params}")
                
                # 获取搜索模式和条件
                search_mode = self._convert_search_mode(search_params.get('mode', ''))
                terms = search_params.get('terms', [])
                exact_matches = search_params.get('exact', [])
                excluded_terms = search_params.get('excluded', [])
                
                # 搜索提示词
                if scope in ['prompts', 'all']:
                    prompt_results = self.search_prompt_details_advanced(
                        terms=terms,
                        exact_matches=exact_matches,
                        excluded_terms=excluded_terms,
                        search_mode=search_mode,
                        limit=limit
                    )
                    for res in prompt_results:
                        res['type'] = 'prompt'
                        results.append(res)
                        
                # 搜索PKM文件
                if scope in ['pkm', 'all']:
                    pkm_results = self.search_pkm_files_advanced(
                        terms=terms,
                        exact_matches=exact_matches,
                        excluded_terms=excluded_terms,
                        search_mode=search_mode,
                        limit=limit
                    )
                    for res in pkm_results:
                        res['type'] = 'pkm'
                        results.append(res)
                
                # 如果是搜索全部，根据时间戳/更新时间排序 (降序)
                if scope == 'all':
                    results.sort(key=lambda x: x.get('timestamp', x.get('updated_at', x.get('created_at', 0))), reverse=True)
                    # 限制最终结果数量
                    results = results[:limit]
                    
                print(f"简单查询转高级搜索完成，找到 {len(results)} 条结果")
                return results
                
            except Exception as e:
                print(f"简单查询转高级搜索出错: {e}")
                # 如果转换搜索失败，回退到传统搜索方法
                return self._traditional_search(query, scope, limit)
        
        # 如果没有提供查询或高级搜索参数，使用简单搜索模式
        elif not search_params:
            return self._traditional_search(query, scope, limit)
        
        # 使用已提供的高级搜索参数
        try:
            # 打印高级搜索参数
            print(f"使用提供的高级搜索参数: {search_params}")
            
            # 获取搜索模式和条件并进行分词处理
            search_mode = self._convert_search_mode(search_params.get('mode', ''))
            
            # 对普通搜索词进行分词处理
            terms = [self.process_text_for_fts(term) for term in search_params.get('terms', [])]
            
            # 对精确匹配词和排除词不做分词处理，保持原样
            exact_matches = search_params.get('exact', [])
            excluded_terms = search_params.get('excluded', [])
            
            # 搜索提示词
            if scope in ['prompts', 'all']:
                prompt_results = self.search_prompt_details_advanced(
                    terms=terms,
                    exact_matches=exact_matches,
                    excluded_terms=excluded_terms,
                    search_mode=search_mode,
                    limit=limit
                )
                for res in prompt_results:
                    res['type'] = 'prompt'
                    results.append(res)
                    
            # 搜索PKM文件
            if scope in ['pkm', 'all']:
                pkm_results = self.search_pkm_files_advanced(
                    terms=terms,
                    exact_matches=exact_matches,
                    excluded_terms=excluded_terms,
                    search_mode=search_mode,
                    limit=limit
                )
                for res in pkm_results:
                    res['type'] = 'pkm'
                    results.append(res)
            
            # 如果是搜索全部，根据时间戳/更新时间排序 (降序)
            if scope == 'all':
                results.sort(key=lambda x: x.get('timestamp', x.get('updated_at', x.get('created_at', 0))), reverse=True)
                # 限制最终结果数量
                results = results[:limit]
                
            print(f"高级组合搜索完成，找到 {len(results)} 条结果")
            return results
                
        except Exception as e:
            print(f"高级组合搜索出错: {e}")
            import traceback
            traceback.print_exc()
            # 如果高级搜索失败，回退到简单搜索
            return self._traditional_search(query, scope, limit)
    
    def _convert_search_mode(self, mode_str):
        """转换界面搜索模式为后端搜索模式
        
        Args:
            mode_str (str): 界面搜索模式字符串，如 "全部包含(AND)"
            
        Returns:
            str: 内部搜索模式 ('AND' 或 'OR')
        """
        mode_str = mode_str.strip()
        if "全部包含" in mode_str or "AND" in mode_str.upper():
            return 'AND'
        elif "任一包含" in mode_str or "OR" in mode_str.upper():
            return 'OR'
        else:  # 默认为OR
            return 'OR'
    
    def _traditional_search(self, query, scope='all', limit=50):
        """传统搜索方法，作为回退选项"""
        results = []
        try:
            # 搜索提示词
            if scope in ['prompts', 'all']:
                prompt_results = self.search_prompt_details(query, limit=limit)
                for res in prompt_results:
                    res['type'] = 'prompt' # 添加类型标识
                    results.append(res)
                    
            # 搜索PKM文件
            if scope in ['pkm', 'all']:
                pkm_results = self.search_pkm_files(query, limit=limit)
                for res in pkm_results:
                    res['type'] = 'pkm' # 添加类型标识
                    results.append(res)
            
            # 如果是搜索全部，根据时间戳/更新时间排序 (降序)
            if scope == 'all':
                results.sort(key=lambda x: x.get('timestamp', x.get('updated_at', x.get('created_at', 0))), reverse=True)
                # 限制最终结果数量
                results = results[:limit]
                
            return results
            
        except Exception as e:
            print(f"传统搜索出错: {e}")
            return []
    
    def is_format_enabled(self, format_name):
        """检查指定的文件格式是否已启用
        
        Args:
            format_name (str): 文件格式名称
            
        Returns:
            bool: 是否启用
        """
        if format_name in self.supported_file_formats:
            return self.supported_file_formats[format_name]["enabled"]
        return False
    
    def is_supported_extension(self, file_path):
        """检查文件扩展名是否为支持的格式
        
        Args:
            file_path (str): 文件路径
            
        Returns:
            bool: 是否支持
        """
        ext = os.path.splitext(file_path)[1].lower()
        
        for format_name, format_config in self.supported_file_formats.items():
            if format_config["enabled"] and ext in format_config["extensions"]:
                return True
        
        return False
    
    def get_format_for_extension(self, file_path):
        """获取文件对应的格式名称
        
        Args:
            file_path (str): 文件路径
            
        Returns:
            str: 格式名称，如果不支持则返回None
        """
        ext = os.path.splitext(file_path)[1].lower()
        
        for format_name, format_config in self.supported_file_formats.items():
            if ext in format_config["extensions"]:
                return format_name
        
        return None
    
    def search_prompt_details_advanced(self, terms=None, exact_matches=None, excluded_terms=None, search_mode='AND', limit=50):
        """高级搜索提示词
        
        Args:
            terms (list): 普通搜索词列表 (已经分词处理)
            exact_matches (list): 精确匹配词列表 (不需要分词)
            excluded_terms (list): 排除词列表 (不需要分词)
            search_mode (str): 搜索模式，'AND'表示全部包含，'OR'表示任一包含
            limit (int): 结果数量限制
            
        Returns:
            list: 匹配的提示词记录列表
        """
        if not self.conn:
            print("数据库未连接")
            return []
            
        # 防止None值
        terms = terms or []
        exact_matches = exact_matches or []
        excluded_terms = excluded_terms or []
        
        try:
            cursor = self.conn.cursor()
            
            # 提示词搜索不使用FTS5，使用传统方法
            # 获取所有提示词及其详情
            cursor.execute("""
                SELECT p.id, p.prompt as title, '' as prompt_type, '' as category, '' as tags, 
                       p.timestamp as created_at, p.timestamp as updated_at,
                       d.id as detail_id, d.prompt as content, '' as model, '' as parameters, 
                       0 as version, 0 as is_default, d.timestamp, '' as notes
                FROM prompts p
                LEFT JOIN prompt_details d ON p.id = d.id
                ORDER BY p.timestamp DESC
            """)
            
            all_prompts = cursor.fetchall()
            
            # 根据搜索条件过滤结果
            results = []
            prompt_ids_added = set()  # 用于跟踪已添加的提示词ID
            
            for row in all_prompts:
                # 提取记录字段
                prompt = {
                    'id': row[0],
                    'title': row[1],
                    'prompt_type': row[2],
                    'category': row[3],
                    'tags': row[4],
                    'created_at': row[5],
                    'updated_at': row[6],
                    'details': {
                        'id': row[7],
                        'content': row[8],
                        'model': row[9],
                        'parameters': row[10],
                        'version': row[11],
                        'is_default': bool(row[12]),
                        'timestamp': row[13],
                        'notes': row[14]
                    }
                }
                
                # 如果已经添加过这个ID，则跳过
                if prompt['id'] in prompt_ids_added:
                    continue
                
                # 执行搜索条件匹配
                title = (prompt['title'] or '').lower()
                content = (prompt['details']['content'] or '').lower()
                tags = (prompt['tags'] or '').lower()
                notes = (prompt['details']['notes'] or '').lower()
                
                # 检查是否匹配普通搜索词
                terms_match = True
                if terms:
                    term_matches = []
                    for term in terms:
                        term = term.lower()
                        term_match = (term in content or term in title or term in tags or term in notes)
                        term_matches.append(term_match)
                    
                    if search_mode == 'AND':
                        terms_match = all(term_matches)
                    else:  # OR
                        terms_match = any(term_matches)
                
                # 检查是否匹配精确匹配词
                exact_match = True
                if exact_matches:
                    for term in exact_matches:
                        term = term.lower()
                        if term not in content and term not in title and term not in tags and term not in notes:
                            exact_match = False
                            break
                
                # 检查是否包含排除词
                excluded_match = False
                if excluded_terms:
                    for term in excluded_terms:
                        term = term.lower()
                        if term in content or term in title or term in tags or term in notes:
                            excluded_match = True
                            break
                
                # 只有当满足所有条件时，才添加到结果中
                if terms_match and exact_match and not excluded_match:
                    # 获取所有详情版本
                    cursor.execute("""
                        SELECT id, content, model, parameters, version, is_default, timestamp, notes
                        FROM prompt_details
                        WHERE prompt_id = ?
                        ORDER BY version DESC
                    """, (prompt['id'],))
                    
                    detail_rows = cursor.fetchall()
                    if detail_rows:
                        # 构建详情列表
                        details = []
                        for detail_row in detail_rows:
                            detail = {
                                'id': detail_row[0],
                                'content': detail_row[1],
                                'model': detail_row[2],
                                'parameters': detail_row[3],
                                'version': detail_row[4],
                                'is_default': bool(detail_row[5]),
                                'timestamp': detail_row[6],
                                'notes': detail_row[7]
                            }
                            
                            # 尝试解析parameters
                            try:
                                if detail['parameters']:
                                    detail['parameters'] = json.loads(detail['parameters'])
                            except:
                                detail['parameters'] = {}
                                
                            details.append(detail)
                        
                        # 用所有详情版本替换单一详情
                        prompt['details'] = details
                        
                        # 添加到结果中并记录ID
                        results.append(prompt)
                        prompt_ids_added.add(prompt['id'])
                        
                        # 如果达到限制数量，提前结束
                        if len(results) >= limit:
                            break
            
            return results
            
        except Exception as e:
            print(f"高级搜索提示词出错: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def search_pkm_files_advanced(self, terms=None, exact_matches=None, excluded_terms=None, search_mode="OR", limit=100):
        """
        使用FTS5搜索PKM文件
        
        Args:
            terms (list): 要搜索的术语列表
            exact_matches (list): 要精确匹配的术语列表
            excluded_terms (list): 要排除的术语列表
            search_mode (str): 搜索模式，可以是"AND"或"OR"
            limit (int): 返回结果的最大数量
            
        Returns:
            list: 包含匹配文件信息的字典列表
        """
        if not self.conn:
            print("数据库未连接")
            return []
            
        try:
            # 构建FTS查询
            fts_query = self._build_fts_query(terms, exact_matches, excluded_terms, search_mode)
            
            # 执行FTS搜索
            cursor = self.conn.cursor()
            cursor.execute(f"""
                SELECT f.id, highlight(pkm_fts, 1, '<mark>', '</mark>') as highlighted_title, 
                       f.file_path, f.file_name, f.title, f.tags, 
                       f.created_at, f.updated_at, f.file_format, f.hash, f.content,
                       f.last_modified
                FROM pkm_fts 
                JOIN pkm_files f ON pkm_fts.id = f.id
                WHERE pkm_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (fts_query, limit))
            
            results = []
            for row in cursor.fetchall():
                file_id, highlighted_title, file_path, file_name, title, tags, created_at, updated_at, file_format, hash, content, last_modified = row
                
                # 构建结果字典
                file_info = {
                    "id": file_id,
                    "file_path": file_path,
                    "file_name": file_name,
                    "title": title,
                    "tags": tags,
                    "created_at": created_at,
                    "updated_at": updated_at,
                    "file_format": file_format,
                    "hash": hash,
                    "content": content,
                    "last_modified": last_modified
                }
                
                # 如果有高亮标题，添加到结果中
                if highlighted_title and highlighted_title != title:
                    file_info["highlighted_title"] = highlighted_title
                    
                results.append(file_info)
                
            return results
                
        except Exception as e:
            print(f"FTS搜索出错: {e}")
            print("回退到传统搜索方法")
            import traceback
            traceback.print_exc()
            
            # 回退到传统搜索方法
            return self._search_pkm_files_advanced_traditional(terms, exact_matches, excluded_terms, search_mode, limit)
    
    def _build_fts_query(self, terms, exact_matches, excluded_terms, search_mode):
        """构建FTS5查询字符串
        
        Args:
            terms (list): 已分词的普通搜索词列表
            exact_matches (list): 精确匹配词列表
            excluded_terms (list): 排除词列表
            search_mode (str): 搜索模式，'AND'或'OR'
            
        Returns:
            str: FTS5查询字符串
        """
        query_parts = []
        
        # 处理普通搜索词
        if terms:
            terms_str = []
            for term in terms:
                # 由于已经通过process_text_for_fts进行了分词，这里不需要再额外处理
                if term and term.strip():
                    terms_str.append(term)
            
            if terms_str:
                if search_mode == 'AND':
                    query_parts.append(" AND ".join(terms_str))
                else:  # OR mode
                    query_parts.append(" OR ".join(terms_str))
        
        # 处理精确匹配词（使用引号包围）
        if exact_matches:
            for term in exact_matches:
                if term and term.strip():
                    # 对精确匹配词使用双引号
                    query_parts.append(f'"{term}"')
        
        # 合并所有正向查询（默认使用OR连接）
        combined_query = ""
        if query_parts:
            combined_query = " OR ".join(query_parts)
        
        # 添加排除词 (使用NOT操作符)
        if excluded_terms and combined_query:
            for term in excluded_terms:
                if term and term.strip():
                    combined_query += f' NOT {term}'
        
        return combined_query
    
    def process_text_for_fts(self, text):
        """对文本进行预处理，用于FTS全文搜索
        
        Args:
            text (str): 原始文本
            
        Returns:
            str: 分词后的文本，使用空格分隔
        """
        if not text:
            return ""
            
        # 使用jieba的搜索引擎模式进行分词
        # 搜索引擎模式适合检索场景，粒度更细，召回率更高
        words = jieba.cut_for_search(text)
        
        # 将分词结果用空格连接成字符串
        return " ".join(words)
    
    def _search_pkm_files_advanced_traditional(self, terms=None, exact_matches=None, excluded_terms=None, search_mode="OR", limit=100):
        """
        使用传统方法在不使用FTS的情况下进行PKM文件的高级搜索
        
        Args:
            terms (list): 要搜索的术语列表
            exact_matches (list): 要精确匹配的术语列表
            excluded_terms (list): 要排除的术语列表
            search_mode (str): 搜索模式，可以是"AND"或"OR"
            limit (int): 返回结果的最大数量
            
        Returns:
            list: 包含匹配文件信息的字典列表
        """
        if not self.conn:
            print("数据库未连接")
            return []
            
        # 防止None值
        terms = terms or []
        exact_matches = exact_matches or []
        excluded_terms = excluded_terms or []
        
        try:
            cursor = self.conn.cursor()
            
            # 获取所有PKM文件
            cursor.execute("""
                SELECT id, file_path, file_name, title, content, tags, 
                       created_at, updated_at, file_format, hash, last_modified
                FROM pkm_files
            """)
            
            all_files = cursor.fetchall()
            results = []
            
            for row in all_files:
                file_id, file_path, file_name, title, content, tags, created_at, updated_at, file_format, hash, last_modified = row
                
                # 构建文件信息字典
                file_info = {
                    "id": file_id,
                    "file_path": file_path,
                    "file_name": file_name,
                    "title": title, 
                    "content": content,
                    "tags": tags,
                    "created_at": created_at,
                    "updated_at": updated_at,
                    "file_format": file_format,
                    "hash": hash,
                    "last_modified": last_modified
                }
                
                # 如果没有搜索条件，添加所有文件
                if not terms and not exact_matches and not excluded_terms:
                    results.append(file_info)
                    continue
                
                # 创建用于搜索的组合文本 (标题+内容+标签)
                search_text = " ".join(filter(None, [
                    title or "", 
                    content or "", 
                    tags or ""
                ])).lower()
                
                # 应用搜索逻辑
                matches_all = True
                matches_any = False
                
                # 检查普通搜索词
                for term in terms:
                    term_lower = term.lower()
                    term_match = term_lower in search_text
                    if not term_match and search_mode == "AND":
                        matches_all = False
                        break
                    if term_match and search_mode == "OR":
                        matches_any = True
                
                # 如果是AND模式且已经不匹配，跳过其他检查
                if search_mode == "AND" and not matches_all:
                    continue
                
                # 检查精确匹配
                for exact_term in exact_matches:
                    exact_term_lower = exact_term.lower()
                    exact_match = exact_term_lower in search_text
                    if not exact_match and search_mode == "AND":
                        matches_all = False
                        break
                    if exact_match and search_mode == "OR":
                        matches_any = True
                
                # 如果是AND模式且已经不匹配，跳过其他检查
                if search_mode == "AND" and not matches_all:
                    continue
                
                # 检查排除词
                should_exclude = False
                for excluded_term in excluded_terms:
                    excluded_term_lower = excluded_term.lower()
                    if excluded_term_lower in search_text:
                        should_exclude = True
                        break
                
                # 如果应该排除，跳过
                if should_exclude:
                    continue
                
                # 最终决定是否添加到结果
                if (search_mode == "AND" and matches_all) or (search_mode == "OR" and matches_any) or (not terms and not exact_matches):
                    results.append(file_info)
                    
                    # 如果达到限制，停止添加
                    if len(results) >= limit:
                        break
            
            return results[:limit]  # 返回结果，确保不超过限制
            
        except Exception as e:
            print(f"传统搜索出错: {e}")
            import traceback
            traceback.print_exc()
            return []