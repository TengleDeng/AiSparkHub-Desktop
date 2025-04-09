#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
AiSparkHub 配置文件
包含全局配置和默认设置
"""

# 应用信息
APP_NAME = "AiSparkHub"
APP_VERSION = "0.1.0"
APP_AUTHOR = "Tengle Deng"

# 数据库配置
DB_PATH = "data/prompts.db"

# 界面配置
THEME = "dark"  # 主题: "light" 或 "dark"
FONT_FAMILY = "Fira Code, Consolas, Courier New, monospace"
FONT_SIZE = 12

# 视图配置
DEFAULT_WINDOW_WIDTH = 1200
DEFAULT_WINDOW_HEIGHT = 800
DEFAULT_AUXILIARY_WINDOW_HEIGHT = 300

# AI配置
DEFAULT_AI_PROVIDERS = [
    {
        "name": "ChatGPT",
        "url": "https://chat.openai.com/",
        "input_selector": "textarea[placeholder='Message ChatGPT…']",
        "submit_selector": "button[data-testid='send-button']"
    },
    {
        "name": "DeepSeek",
        "url": "https://chat.deepseek.com/",
        "input_selector": "textarea.text-base",
        "submit_selector": "button.send-button"
    }
]

# JavaScript注入配置
JS_FILL_PROMPT_TEMPLATE = """
    document.querySelector('{input_selector}').value = '{prompt}';
    document.querySelector('{input_selector}').dispatchEvent(new Event('input', {{ bubbles: true }}));
    setTimeout(() => document.querySelector('{submit_selector}').click(), 500);
""" 