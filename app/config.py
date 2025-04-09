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

# 用户设置配置
USER_SETTINGS_PATH = "data/settings.json"

# 界面配置
THEME = "dark"  # 主题: "light" 或 "dark"
FONT_FAMILY = "Fira Code, Consolas, Courier New, monospace"
FONT_SIZE = 12

# 视图配置
DEFAULT_WINDOW_WIDTH = 1200
DEFAULT_WINDOW_HEIGHT = 800
DEFAULT_AUXILIARY_WINDOW_HEIGHT = 300

# 支持的AI平台
SUPPORTED_AI_PLATFORMS = {
    "KIMI": {
        "key": "kimi",
        "name": "Kimi",
        "url": "https://kimi.moonshot.cn",
        "input_selector": ".chat-input-editor",
        "submit_selector": ".send-button",
        "response_selector": ".markdown___vuBDJ"
    },
    "YUANBAO": {
        "key": "yuanbao",
        "name": "元宝",
        "url": "https://yuanbao.tencent.com/",
        "input_selector": "textarea.text-base",
        "submit_selector": "button.send-button",
        "response_selector": ".agent-chat__conv--ai__speech_show"
    },
    "DOUBAO": {
        "key": "doubao",
        "name": "豆包",
        "url": "https://www.doubao.com/",
        "input_selector": "textarea.semi-input-textarea",
        "submit_selector": "#flow-end-msg-send",
        "response_selector": "[data-testid='receive_message']"
    },
    "CHATGPT": {
        "key": "chatgpt",
        "name": "ChatGPT",
        "url": "https://chat.openai.com/",
        "input_selector": "textarea[placeholder='Message ChatGPT…']",
        "submit_selector": "button[data-testid='send-button']",
        "response_selector": ".markdown.prose"
    },
    "PERPLEXITY": {
        "key": "perplexity",
        "name": "Perplexity",
        "url": "https://www.perplexity.ai/",
        "input_selector": "textarea.overflow-auto",
        "submit_selector": "button[aria-label=\"Submit\"]",
        "response_selector": "#response-textarea"
    },
    "N": {
        "key": "n",
        "name": "N",
        "url": "https://n.cn/",
        "input_selector": "#composition-input",
        "submit_selector": "#home_chat_btn",
        "response_selector": "#response-textarea"
    },
    "GROK": {
        "key": "grok",
        "name": "Grok",
        "url": "https://grok.com/",
        "input_selector": "textarea[aria-label=\"向Grok提任何问题\"]",
        "submit_selector": "button[type=\"submit\"][aria-label=\"提交\"]",
        "response_selector": "#response-textarea"
    },
    "CHATGLM": {
        "key": "chatglm",
        "name": "ChatGLM",
        "url": "https://chatglm.cn/",
        "input_selector": "textarea.scroll-display-none",
        "submit_selector": ".enter_icon",
        "response_selector": "#response-textarea"
    },
    "YIYAN": {
        "key": "yiyan",
        "name": "文心一言",
        "url": "https://yiyan.baidu.com/",
        "input_selector": ".yc-editor",
        "submit_selector": "#sendBtn",
        "response_selector": "#response-textarea"
    },
    "TONGYI": {
        "key": "tongyi",
        "name": "通义",
        "url": "https://tongyi.aliyun.com/",
        "input_selector": ".ant-input",
        "submit_selector": "[class*=\"operateBtn\"]",
        "response_selector": "#response-textarea"
    },
    "GEMINI": {
        "key": "gemini",
        "name": "Gemini",
        "url": "https://gemini.google.com/",
        "input_selector": ".text-input-field_textarea-wrapper",
        "submit_selector": ".send-button",
        "response_selector": "#response-textarea"
    },
    "DEEPSEEK": {
        "key": "deepseek",
        "name": "DeepSeek",
        "url": "https://chat.deepseek.com/",
        "input_selector": "#chat-input",
        "submit_selector": "[role=\"button\"][aria-disabled=\"false\"]",
        "response_selector": ".message-content"
    }
}

# 默认启用的AI平台
DEFAULT_ENABLED_PLATFORMS = ["GROK","DOUBAO"]

# 用户默认设置
DEFAULT_USER_SETTINGS = {
    "theme": THEME,
    "enabled_ai_platforms": DEFAULT_ENABLED_PLATFORMS,
    "max_ai_views": 4  # 最多显示的AI视图数量
}

# JavaScript注入配置
JS_FILL_PROMPT_TEMPLATE = """
    document.querySelector('{input_selector}').value = '{prompt}';
    document.querySelector('{input_selector}').dispatchEvent(new Event('input', {{ bubbles: true }}));
    setTimeout(() => document.querySelector('{submit_selector}').click(), 500);
""" 