#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
from logging.handlers import RotatingFileHandler

def setup_logger():
    """
    设置应用程序日志记录器
    
    返回:
        logging.Logger: 配置好的日志记录器实例
    """
    # 创建logger
    logger = logging.getLogger('AiSparkHub')
    logger.setLevel(logging.INFO)
    
    # 确保日志目录存在
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # 创建文件处理器
    log_file = os.path.join(log_dir, 'app.log')
    file_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
    file_handler.setLevel(logging.INFO)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 创建格式器
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # 添加处理器到logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    logger.info("日志系统初始化完成")
    
    return logger 