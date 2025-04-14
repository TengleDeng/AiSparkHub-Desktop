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

class PKMFileWatcher(QObject):
    """PKM文件监控类，监控MD文件的变化"""
    
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
        
        # 连接信号到数据库处理函数
        self.file_added.connect(self._on_file_added)
        self.file_modified.connect(self._on_file_modified)
        self.file_deleted.connect(self._on_file_deleted)
    
    def start_monitoring(self, folder_path):
        """开始监控文件夹
        
        Args:
            folder_path: 要监控的文件夹路径
        
        Returns:
            bool: 是否成功启动监控
        """
        if not folder_path or not os.path.exists(folder_path):
            print(f"无法监控不存在的文件夹: {folder_path}")
            return False
        
        try:
            # 停止现有监控
            self.stop_monitoring()
            
            # 添加根目录到监控列表
            self.watcher.addPath(folder_path)
            
            # 递归添加所有子目录
            for root, dirs, files in os.walk(folder_path):
                # 添加目录到监控
                for dir_name in dirs:
                    dir_path = os.path.join(root, dir_name)
                    self.watcher.addPath(dir_path)
                
                # 记录所有Markdown文件
                for file_name in files:
                    if file_name.lower().endswith('.md'):
                        file_path = os.path.join(root, file_name)
                        self.known_files.add(file_path)
                        self.watcher.addPath(file_path)
            
            print(f"开始监控文件夹: {folder_path}")
            print(f"共监控 {len(self.watcher.directories())} 个目录和 {len(self.watcher.files())} 个文件")
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
            
            # 获取目录中当前的Markdown文件
            try:
                for file_name in os.listdir(path):
                    if file_name.lower().endswith('.md'):
                        file_path = os.path.join(path, file_name)
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
                        
                        # 递归添加新目录中的所有子目录和Markdown文件
                        for root, dirs, files in os.walk(dir_path):
                            for sub_dir in dirs:
                                sub_dir_path = os.path.join(root, sub_dir)
                                self.watcher.addPath(sub_dir_path)
                            
                            for file_name in files:
                                if file_name.lower().endswith('.md'):
                                    file_path = os.path.join(root, file_name)
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
        print(f"文件添加: {file_path}")
        self.db_manager.add_or_update_pkm_file(file_path)
    
    def _on_file_modified(self, file_path):
        """处理文件修改事件"""
        print(f"文件修改: {file_path}")
        self.db_manager.add_or_update_pkm_file(file_path)
    
    def _on_file_deleted(self, file_path):
        """处理文件删除事件"""
        print(f"文件删除: {file_path}")
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
        self.load_pkm_settings()
        
        # 创建文件监控器
        self.file_watcher = PKMFileWatcher(self)
        
        # 如果已配置PKM文件夹，启动监控
        if self.pkm_folder and os.path.exists(self.pkm_folder):
            self.file_watcher.start_monitoring(self.pkm_folder)
    
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
        """初始化数据库表结构"""
        cursor = self.conn.cursor()
        
        # 提示词详细记录表
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
        
        # 创建PKM表，用于存储Markdown文件内容
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS pkm_files (
            id TEXT PRIMARY KEY,
            file_path TEXT NOT NULL,
            file_name TEXT NOT NULL,
            content TEXT NOT NULL,
            title TEXT,
            hash TEXT NOT NULL,
            last_modified INTEGER NOT NULL,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL,
            tags TEXT DEFAULT ''
        )
        ''')
        
        # 创建索引以加快搜索
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_pkm_content ON pkm_files(content);
        ''')
        
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_pkm_title ON pkm_files(title);
        ''')
        
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_pkm_tags ON pkm_files(tags);
        ''')
        
        self.conn.commit()
    
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
                    print(f"已加载PKM文件夹设置: {self.pkm_folder}")
        except Exception as e:
            print(f"加载PKM设置出错: {e}")
            self.pkm_folder = None
    
    def save_pkm_settings(self, pkm_folder):
        """保存PKM文件夹设置"""
        try:
            # 获取数据库所在目录的父目录作为配置目录
            db_dir = self._get_data_directory()
            config_dir = os.path.dirname(db_dir)  # 使用数据库目录的父目录
            
            # 确保配置目录存在
            os.makedirs(config_dir, exist_ok=True)
            
            # 设置文件路径
            config_file = os.path.join(config_dir, "pkm_settings.json")
            
            # 保存设置
            self.pkm_folder = pkm_folder
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump({'pkm_folder': pkm_folder}, f, ensure_ascii=False)
                
            print(f"已保存PKM文件夹设置: {pkm_folder}")
            
            # 重新启动文件监控
            self.file_watcher.stop_monitoring()
            if self.pkm_folder and os.path.exists(self.pkm_folder):
                self.file_watcher.start_monitoring(self.pkm_folder)
                
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
            file_path (str): 文件的完整路径
            
        Returns:
            bool: 操作是否成功
        """
        if not self.conn:
            print("数据库未连接")
            return False
            
        try:
            # 确认文件存在且为Markdown文件
            if not os.path.exists(file_path) or not file_path.lower().endswith('.md'):
                print(f"文件不存在或非Markdown文件: {file_path}")
                return False
                
            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # 计算文件hash
            file_hash = self.compute_file_hash(file_path)
            if not file_hash:
                return False
                
            # 获取文件名和时间信息
            file_name = os.path.basename(file_path)
            last_modified = int(os.path.getmtime(file_path))
            created_at = int(os.path.getctime(file_path))
            current_time = int(time.time())
            
            # 提取标题（如果有）
            title = self.extract_title_from_md(content)
            
            # 生成文件ID（使用相对路径的hash值）
            try:
                rel_path = os.path.relpath(file_path, self.pkm_folder)
                file_id = hashlib.md5(rel_path.encode('utf-8')).hexdigest()
            except ValueError:
                # 如果计算相对路径失败（可能路径在不同驱动器上），使用绝对路径
                file_id = hashlib.md5(file_path.encode('utf-8')).hexdigest()
                print(f"使用绝对路径生成ID: {file_path}")
            
            # 检查文件是否已存在于数据库中
            cursor = self.conn.cursor()
            cursor.execute("SELECT hash FROM pkm_files WHERE id = ?", (file_id,))
            row = cursor.fetchone()
            
            # 如果文件已存在且hash值相同，不需要更新
            if row and row['hash'] == file_hash:
                print(f"文件未变更，无需更新: {file_path}")
                return True
                
            # 添加或更新文件
            cursor.execute("""
                REPLACE INTO pkm_files 
                (id, file_path, file_name, content, title, hash, last_modified, created_at, updated_at, tags) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                file_id, file_path, file_name, content, title, file_hash, 
                last_modified, created_at, current_time, ''
            ))
            
            self.conn.commit()
            print(f"已{'更新' if row else '添加'}文件到PKM数据库: {file_path}")
            return True
            
        except Exception as e:
            print(f"添加或更新PKM文件出错: {e}")
            return False
    
    def delete_pkm_file(self, file_path):
        """从数据库中删除PKM文件
        
        Args:
            file_path (str): 文件的完整路径
            
        Returns:
            bool: 操作是否成功
        """
        if not self.conn:
            print("数据库未连接")
            return False
            
        try:
            # 生成文件ID
            try:
                rel_path = os.path.relpath(file_path, self.pkm_folder)
                file_id = hashlib.md5(rel_path.encode('utf-8')).hexdigest()
            except ValueError:
                # 如果计算相对路径失败，使用绝对路径
                file_id = hashlib.md5(file_path.encode('utf-8')).hexdigest()
                print(f"使用绝对路径生成ID进行删除: {file_path}")
            
            # 删除文件记录
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM pkm_files WHERE id = ?", (file_id,))
            
            if cursor.rowcount > 0:
                self.conn.commit()
                print(f"已从PKM数据库删除文件: {file_path}")
                return True
            else:
                print(f"文件不在PKM数据库中: {file_path}")
                return False
                
        except Exception as e:
            print(f"删除PKM文件出错: {e}")
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
            
            # 搜索文件内容、标题和标签
            cursor.execute("""
                SELECT id, file_path, file_name, title, updated_at
                FROM pkm_files
                WHERE content LIKE ? OR title LIKE ? OR tags LIKE ?
                ORDER BY updated_at DESC
                LIMIT ?
            """, (search_pattern, search_pattern, search_pattern, limit))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'id': row['id'],
                    'file_path': row['file_path'],
                    'file_name': row['file_name'],
                    'title': row['title'] or row['file_name'],
                    'updated_at': row['updated_at']
                })
                
            return results
            
        except Exception as e:
            print(f"搜索PKM文件出错: {e}")
            return []
    
    def scan_pkm_folder(self, progress_callback=None):
        """扫描PKM文件夹，更新数据库
        
        Args:
            progress_callback: 可选的进度回调函数，接收两个参数：当前处理文件数和总文件数
        
        Returns:
            dict: 包含添加、更新和删除文件数量的字典
        """
        if not self.pkm_folder or not os.path.exists(self.pkm_folder):
            print(f"PKM文件夹不存在: {self.pkm_folder}")
            return {'added': 0, 'updated': 0, 'deleted': 0, 'error': '文件夹不存在'}
            
        try:
            # 获取数据库中所有文件路径
            cursor = self.conn.cursor()
            cursor.execute("SELECT id, file_path FROM pkm_files")
            db_files = {row['id']: row['file_path'] for row in cursor.fetchall()}
            
            # 第一步：先统计文件夹中的所有.md文件
            all_md_files = []
            print("正在统计所有Markdown文件...")
            for root, dirs, files in os.walk(self.pkm_folder):
                for file in files:
                    if file.lower().endswith('.md'):
                        file_path = os.path.join(root, file)
                        all_md_files.append(file_path)
            
            total_files = len(all_md_files)
            print(f"找到 {total_files} 个Markdown文件")
            
            # 发送初始进度
            if progress_callback:
                progress_callback(0, total_files)
            
            # 第二步：依次处理每个文件
            added_count = 0
            updated_count = 0
            processed_count = 0
            
            for file_path in all_md_files:
                # 处理文件
                try:
                    rel_path = os.path.relpath(file_path, self.pkm_folder)
                    file_id = hashlib.md5(rel_path.encode('utf-8')).hexdigest()
                except ValueError:
                    # 如果计算相对路径失败，使用绝对路径
                    file_id = hashlib.md5(file_path.encode('utf-8')).hexdigest()
                
                result = self.add_or_update_pkm_file(file_path)
                if result:
                    if file_id in db_files:
                        updated_count += 1
                    else:
                        added_count += 1
                
                # 更新进度
                processed_count += 1
                if progress_callback and processed_count % 5 == 0:  # 每5个文件更新一次进度，减少UI开销
                    progress_callback(processed_count, total_files)
            
            # 确保最终进度为100%
            if progress_callback and total_files > 0:
                progress_callback(total_files, total_files)
            
            # 第三步：检查需要删除的文件（数据库中存在但实际文件系统中不存在的文件）
            deleted_count = 0
            for file_id, file_path in db_files.items():
                if file_path not in all_md_files and not os.path.exists(file_path):
                    self.delete_pkm_file(file_path)
                    deleted_count += 1
            
            return {
                'added': added_count, 
                'updated': updated_count, 
                'deleted': deleted_count
            }
            
        except Exception as e:
            print(f"扫描PKM文件夹出错: {e}")
            return {'added': 0, 'updated': 0, 'deleted': 0, 'error': str(e)}
    
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
    
    def search_combined(self, query, scope='all', limit=50):
        """组合搜索提示词和PKM文件
        
        Args:
            query (str): 搜索查询
            scope (str): 搜索范围 ('prompts', 'pkm', 'all')
            limit (int): 返回结果数量限制
            
        Returns:
            list: 匹配的记录列表，每个记录包含'type'字段 ('prompt'或'pkm')
        """
        if not self.conn:
            print("数据库未连接")
            return []
            
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
                results.sort(key=lambda x: x.get('timestamp', x.get('updated_at', 0)), reverse=True)
                # 限制最终结果数量
                results = results[:limit]
                
            return results
            
        except Exception as e:
            print(f"组合搜索出错: {e}")
            return [] 