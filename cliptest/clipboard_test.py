#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
剪贴板API测试程序
测试navigator.clipboard API在PyQt6 WebEngineView环境中的支持情况
"""

import sys
import os
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QTextEdit, QLabel, QComboBox, QHBoxLayout
from PyQt6.QtCore import QUrl, Qt, QSize
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings, QWebEnginePage, QWebEngineProfile
from PyQt6.QtGui import QIcon

class ClipboardTestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Navigator.clipboard API 测试")
        self.setMinimumSize(800, 600)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 创建控制面板
        control_panel = QWidget()
        control_layout = QHBoxLayout(control_panel)
        
        # 创建按钮
        self.test_button = QPushButton("开始测试")
        self.test_button.clicked.connect(self.run_test)
        control_layout.addWidget(self.test_button)
        
        # 添加权限设置
        permission_label = QLabel("剪贴板权限设置:")
        control_layout.addWidget(permission_label)
        
        self.permission_combo = QComboBox()
        self.permission_combo.addItems([
            "所有权限都开启",
            "仅 JavascriptCanAccessClipboard",
            "仅 JavascriptCanPaste",
            "所有权限都关闭"
        ])
        self.permission_combo.currentIndexChanged.connect(self.change_permissions)
        control_layout.addWidget(self.permission_combo)
        
        # 清除日志按钮
        self.clear_button = QPushButton("清除日志")
        self.clear_button.clicked.connect(self.clear_logs)
        control_layout.addWidget(self.clear_button)
        
        # 添加控制面板到主布局
        main_layout.addWidget(control_panel)
        
        # 创建水平分割布局
        split_layout = QHBoxLayout()
        main_layout.addLayout(split_layout)
        
        # 创建WebView
        self.web_view = QWebEngineView()
        split_layout.addWidget(self.web_view, 3)  # 比例为3
        
        # 创建日志区域
        log_layout = QVBoxLayout()
        split_layout.addLayout(log_layout, 2)  # 比例为2
        
        log_label = QLabel("测试日志")
        log_layout.addWidget(log_label)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        
        # 初始化WebView设置
        self.setup_web_view()
        
        # 显示就绪信息
        self.log("剪贴板测试程序初始化完成")
        self.log("点击'开始测试'按钮开始测试navigator.clipboard API")
    
    def setup_web_view(self):
        """设置WebView初始配置"""
        # 创建自定义配置文件
        self.profile = QWebEngineProfile("ClipboardTest", self.web_view)
        
        # 创建页面
        self.page = QWebEnginePage(self.profile, self.web_view)
        self.web_view.setPage(self.page)
        
        # 设置默认权限
        self.apply_permissions(0)  # 默认所有权限开启
        
        # 监听页面加载完成
        self.web_view.loadFinished.connect(self.on_load_finished)
        
        # 允许开发者工具
        try:
            self.page.settings().setAttribute(QWebEngineSettings.WebAttribute.DeveloperExtrasEnabled, True)
            self.log("开发者工具已启用")
        except Exception as e:
            self.log(f"启用开发者工具失败: {e}")
        
        # 创建并加载测试HTML
        self.load_test_page()
    
    def apply_permissions(self, mode):
        """应用剪贴板权限设置
        
        Args:
            mode (int): 0=全开, 1=仅Access, 2=仅Paste, 3=全关
        """
        settings = self.page.settings()
        
        if mode == 0:  # 所有权限开启
            settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanPaste, True)
            self.log("设置: 所有剪贴板权限已开启")
        elif mode == 1:  # 仅Access
            settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanPaste, False)
            self.log("设置: 仅 JavascriptCanAccessClipboard 开启")
        elif mode == 2:  # 仅Paste
            settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard, False)
            settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanPaste, True)
            self.log("设置: 仅 JavascriptCanPaste 开启")
        else:  # 全关
            settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard, False)
            settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanPaste, False)
            self.log("设置: 所有剪贴板权限已关闭")
    
    def change_permissions(self, index):
        """更改权限设置并重新加载页面"""
        self.apply_permissions(index)
        self.web_view.reload()
        self.log(f"已更改权限设置并重新加载页面")
    
    def load_test_page(self):
        """加载测试HTML页面"""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Navigator.clipboard API 测试</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    margin: 20px;
                    background-color: #f9f9f9;
                }
                h1 {
                    color: #333;
                }
                .test-panel {
                    background-color: #fff;
                    border: 1px solid #ddd;
                    padding: 20px;
                    margin-top: 20px;
                    border-radius: 5px;
                }
                button {
                    padding: 8px 16px;
                    background: #4285f4;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                    margin: 5px;
                }
                button:hover {
                    background: #3b78e7;
                }
                pre {
                    background: #f5f5f5;
                    padding: 10px;
                    border-radius: 4px;
                    overflow: auto;
                    margin-top: 15px;
                    border: 1px solid #eee;
                }
                .success {
                    color: green;
                    font-weight: bold;
                }
                .failure {
                    color: red;
                    font-weight: bold;
                }
            </style>
        </head>
        <body>
            <h1>Navigator.clipboard API 测试</h1>
            
            <div class="test-panel">
                <h2>环境检测</h2>
                <div id="env-info">检测中...</div>
                
                <h2>Navigator.clipboard 测试</h2>
                <button id="test-btn">测试 writeText</button>
                <button id="test-exec-btn">测试 execCommand</button>
                <pre id="test-results">点击按钮开始测试...</pre>
            </div>
            
            <script>
                // 显示环境信息
                function showEnvironmentInfo() {
                    const envInfo = document.getElementById('env-info');
                    const info = [
                        `<p>用户代理: <code>${navigator.userAgent}</code></p>`,
                        `<p>navigator.clipboard 可用性: <code>${typeof navigator.clipboard !== 'undefined'}</code></p>`
                    ];
                    
                    if (typeof navigator.clipboard !== 'undefined') {
                        info.push(`<p>clipboard.writeText 可用性: <code>${typeof navigator.clipboard.writeText === 'function'}</code></p>`);
                        info.push(`<p>clipboard.readText 可用性: <code>${typeof navigator.clipboard.readText === 'function'}</code></p>`);
                    }
                    
                    info.push(`<p>document.execCommand 可用性: <code>${typeof document.execCommand === 'function'}</code></p>`);
                    envInfo.innerHTML = info.join('');
                }
                
                // 记录测试结果
                function log(message, isSuccess = null) {
                    const results = document.getElementById('test-results');
                    let formattedMessage = message;
                    
                    if (isSuccess === true) {
                        formattedMessage = `<span class="success">✓ ${message}</span>`;
                    } else if (isSuccess === false) {
                        formattedMessage = `<span class="failure">✗ ${message}</span>`;
                    }
                    
                    results.innerHTML += formattedMessage + '<br>';
                    
                    // 记录到控制台
                    console.log(message);
                }
                
                // 清空测试结果
                function clearResults() {
                    document.getElementById('test-results').innerHTML = '';
                }
                
                // 测试 navigator.clipboard.writeText
                async function testClipboardWriteText() {
                    clearResults();
                    
                    log('开始测试 navigator.clipboard.writeText...');
                    
                    if (typeof navigator.clipboard === 'undefined') {
                        log('navigator.clipboard API 不可用!', false);
                        return;
                    }
                    
                    if (typeof navigator.clipboard.writeText !== 'function') {
                        log('navigator.clipboard.writeText 方法不可用!', false);
                        return;
                    }
                    
                    try {
                        const testText = '这是一个测试文本 - ' + new Date().toISOString();
                        log(`尝试复制文本: "${testText}"`);
                        
                        await navigator.clipboard.writeText(testText);
                        log('navigator.clipboard.writeText Promise 已解决 (成功)', true);
                        log('请手动粘贴检查剪贴板内容是否匹配');
                    } catch (error) {
                        log(`navigator.clipboard.writeText 失败: ${error.message}`, false);
                        log('错误详情: ' + JSON.stringify(error, Object.getOwnPropertyNames(error)));
                    }
                }
                
                // 测试 document.execCommand 复制
                function testExecCommand() {
                    clearResults();
                    
                    log('开始测试 document.execCommand("copy")...');
                    
                    if (typeof document.execCommand !== 'function') {
                        log('document.execCommand 不可用!', false);
                        return;
                    }
                    
                    try {
                        const textarea = document.createElement('textarea');
                        const testText = '这是一个execCommand测试文本 - ' + new Date().toISOString();
                        textarea.value = testText;
                        textarea.style.position = 'fixed';
                        textarea.style.left = '0';
                        textarea.style.top = '0';
                        textarea.style.opacity = '0';
                        document.body.appendChild(textarea);
                        
                        log(`尝试复制文本: "${testText}"`);
                        
                        textarea.focus();
                        textarea.select();
                        
                        const success = document.execCommand('copy');
                        document.body.removeChild(textarea);
                        
                        if (success) {
                            log('document.execCommand("copy") 成功', true);
                            log('请手动粘贴检查剪贴板内容是否匹配');
                        } else {
                            log('document.execCommand("copy") 返回false', false);
                        }
                    } catch (error) {
                        log(`document.execCommand("copy") 失败: ${error.message}`, false);
                    }
                }
                
                // 初始化
                document.addEventListener('DOMContentLoaded', function() {
                    showEnvironmentInfo();
                    
                    // 绑定按钮事件
                    document.getElementById('test-btn').addEventListener('click', testClipboardWriteText);
                    document.getElementById('test-exec-btn').addEventListener('click', testExecCommand);
                    
                    // 导出测试函数供Python调用
                    window.runClipboardTest = testClipboardWriteText;
                    window.runExecCommandTest = testExecCommand;
                });
            </script>
        </body>
        </html>
        """
        
        self.web_view.setHtml(html)
        self.log("测试页面已加载")
    
    def on_load_finished(self, success):
        """页面加载完成处理"""
        if success:
            self.log("页面加载成功")
        else:
            self.log("页面加载失败")
    
    def run_test(self):
        """运行剪贴板API测试"""
        self.log("\n--- 开始新测试 ---")
        self.log(f"当前权限设置: {self.permission_combo.currentText()}")
        
        # 调用JavaScript测试函数
        js_code = "runClipboardTest();"
        self.web_view.page().runJavaScript(js_code)
    
    def log(self, message):
        """添加日志消息"""
        self.log_text.append(message)
    
    def clear_logs(self):
        """清空日志区域"""
        self.log_text.clear()
        self.log("日志已清空")
        
        # 同时清空网页中的测试结果
        js_code = "document.getElementById('test-results').innerHTML = '测试结果已清空';"
        self.web_view.page().runJavaScript(js_code)

def main():
    """主函数"""
    app = QApplication(sys.argv)
    window = ClipboardTestWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 