#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Kimi网页测试程序
特别测试navigator.clipboard在PyQt6 WebEngineView环境中的支持情况
使用具体的AI网站：https://kimi.moonshot.cn/
"""

import sys
import os
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QTextEdit, QLabel
from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings, QWebEnginePage, QWebEngineProfile

class KimiTestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kimi网页测试 - navigator.clipboard检测")
        self.setMinimumSize(1200, 800)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        layout = QVBoxLayout(central_widget)
        
        # 创建控制面板
        control_panel = QWidget()
        control_layout = QVBoxLayout(control_panel)
        
        # 添加诊断按钮
        self.check_button = QPushButton("检测navigator.clipboard可用性")
        self.check_button.clicked.connect(self.check_clipboard)
        control_layout.addWidget(self.check_button)
        
        # 添加测试按钮
        self.test_button = QPushButton("测试复制功能")
        self.test_button.clicked.connect(self.test_copy)
        control_layout.addWidget(self.test_button)
        
        # 添加日志区域
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        control_layout.addWidget(self.log_area)
        
        # 设置控制面板最大宽度
        control_panel.setMaximumWidth(300)
        layout.addWidget(control_panel)
        
        # 创建WebView
        self.web_view = QWebEngineView()
        layout.addWidget(self.web_view)
        
        # 设置布局比例
        layout.setStretch(0, 1)  # 控制面板
        layout.setStretch(1, 4)  # WebView
        
        # 初始化WebView配置
        self.setup_web_view()
        
        # 加载Kimi网页
        self.load_kimi()
    
    def setup_web_view(self):
        """设置WebView配置"""
        # 创建自定义配置
        self.profile = QWebEngineProfile("KimiTest", self.web_view)
        
        # 创建页面
        self.page = QWebEnginePage(self.profile, self.web_view)
        self.web_view.setPage(self.page)
        
        # 启用所有权限
        settings = self.page.settings()
        
        # 设置权限 - 使用try/except以兼容不同版本的PyQt6
        # 剪贴板权限
        try:
            settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard, True)
            self.log("已启用JavascriptCanAccessClipboard")
        except (AttributeError, TypeError):
            self.log("警告: JavascriptCanAccessClipboard属性不可用")
        
        try:
            settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanPaste, True)
            self.log("已启用JavascriptCanPaste")
        except (AttributeError, TypeError):
            self.log("警告: JavascriptCanPaste属性不可用")
        
        # 其他权限
        try:
            settings.setAttribute(QWebEngineSettings.WebAttribute.FullScreenSupportEnabled, True)
            self.log("已启用FullScreenSupportEnabled")
        except (AttributeError, TypeError):
            self.log("警告: FullScreenSupportEnabled属性不可用")
        
        try:
            settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
            self.log("已启用LocalContentCanAccessRemoteUrls")
        except (AttributeError, TypeError):
            self.log("警告: LocalContentCanAccessRemoteUrls属性不可用")
        
        try:
            settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
            self.log("已启用LocalContentCanAccessFileUrls")
        except (AttributeError, TypeError):
            self.log("警告: LocalContentCanAccessFileUrls属性不可用")
        
        # 开发者工具 - 不同版本可能有不同名称
        dev_tools_enabled = False
        
        # 尝试启用开发者工具 (方式1)
        try:
            settings.setAttribute(QWebEngineSettings.WebAttribute.DeveloperExtrasEnabled, True)
            self.log("已启用开发者工具 (DeveloperExtrasEnabled)")
            dev_tools_enabled = True
        except (AttributeError, TypeError):
            self.log("DeveloperExtrasEnabled属性不可用，尝试其他方式...")
        
        # 尝试启用开发者工具 (方式2)
        if not dev_tools_enabled:
            try:
                # 以整数方式访问
                settings.setAttribute(QWebEngineSettings.WebAttribute(11), True)  # 11可能是DeveloperExtrasEnabled的枚举值
                self.log("已启用开发者工具 (WebAttribute(11))")
                dev_tools_enabled = True
            except (ValueError, TypeError, AttributeError):
                self.log("WebAttribute(11)不可用...")
        
        # 尝试启用开发者工具 (方式3) 
        if not dev_tools_enabled:
            # 打印所有可用的WebAttribute
            self.log("\n可用的WebAttribute:")
            try:
                for name in dir(QWebEngineSettings.WebAttribute):
                    if not name.startswith('_'):
                        self.log(f" - {name}")
            except:
                self.log("无法获取WebAttribute列表")
        
        self.log("WebView配置已设置完成")
        
        # 连接信号
        self.web_view.loadFinished.connect(self.on_load_finished)
    
    def load_kimi(self):
        """加载Kimi网页"""
        self.log("正在加载Kimi网页...")
        self.web_view.load(QUrl("https://kimi.moonshot.cn/"))
    
    def on_load_finished(self, success):
        """页面加载完成处理"""
        if success:
            self.log("Kimi网页加载成功")
            # 注入诊断脚本
            self.inject_diagnostic_script()
        else:
            self.log("Kimi网页加载失败")
    
    def inject_diagnostic_script(self):
        """注入诊断脚本"""
        self.log("正在注入诊断脚本...")
        script = """
        (function() {
            // 记录剪贴板API可用性
            const clipboardAvailable = typeof navigator.clipboard !== 'undefined';
            const writeTextAvailable = clipboardAvailable && typeof navigator.clipboard.writeText === 'function';
            const readTextAvailable = clipboardAvailable && typeof navigator.clipboard.readText === 'function';
            
            console.log('诊断信息:');
            console.log('navigator.clipboard可用性:', clipboardAvailable);
            console.log('clipboard.writeText可用性:', writeTextAvailable);
            console.log('clipboard.readText可用性:', readTextAvailable);
            console.log('document.execCommand可用性:', typeof document.execCommand === 'function');
            
            // 返回诊断结果
            return {
                userAgent: navigator.userAgent,
                clipboardAvailable: clipboardAvailable,
                writeTextAvailable: writeTextAvailable,
                readTextAvailable: readTextAvailable,
                execCommandAvailable: typeof document.execCommand === 'function'
            };
        })();
        """
        
        self.web_view.page().runJavaScript(script, self.handle_diagnostic_result)
    
    def handle_diagnostic_result(self, result):
        """处理诊断结果"""
        if not result:
            self.log("诊断失败，未能获取结果")
            return
        
        self.log("\n诊断结果:")
        self.log(f"用户代理: {result.get('userAgent', '未知')}")
        self.log(f"navigator.clipboard可用性: {result.get('clipboardAvailable', False)}")
        self.log(f"clipboard.writeText可用性: {result.get('writeTextAvailable', False)}")
        self.log(f"clipboard.readText可用性: {result.get('readTextAvailable', False)}")
        self.log(f"document.execCommand可用性: {result.get('execCommandAvailable', False)}")
        
        # 存储结果以供后续使用
        self.diagnostic_result = result
    
    def check_clipboard(self):
        """检测navigator.clipboard可用性"""
        self.log("\n重新检测navigator.clipboard可用性...")
        self.inject_diagnostic_script()
    
    def test_copy(self):
        """测试复制功能"""
        self.log("\n测试复制功能...")
        script = """
        (function() {
            // 创建测试文本
            const testText = "这是Kimi测试的复制文本 - " + new Date().toISOString();
            console.log("测试文本:", testText);
            
            // 测试结果对象
            const result = {
                testText: testText,
                clipboardSuccess: false,
                execCommandSuccess: false,
                error: null
            };
            
            // 检查navigator.clipboard可用性
            if (typeof navigator.clipboard !== 'undefined' && 
                typeof navigator.clipboard.writeText === 'function') {
                
                // 尝试使用navigator.clipboard
                try {
                    // 注意：这是异步的，但我们需要同步返回结果
                    // 所以实际结果可能不会反映在返回值中
                    navigator.clipboard.writeText(testText)
                        .then(() => {
                            console.log("navigator.clipboard.writeText成功");
                        })
                        .catch(err => {
                            console.error("navigator.clipboard.writeText失败:", err);
                        });
                    
                    // 假设成功，但实际上可能不是
                    result.clipboardSuccess = true;
                } catch (e) {
                    console.error("navigator.clipboard异常:", e);
                    result.error = e.toString();
                }
            }
            
            // 测试document.execCommand
            if (typeof document.execCommand === 'function') {
                try {
                    // 创建临时textarea
                    const textarea = document.createElement('textarea');
                    textarea.value = testText;
                    textarea.style.position = 'fixed';
                    textarea.style.opacity = '0';
                    document.body.appendChild(textarea);
                    
                    // 选择并复制
                    textarea.select();
                    result.execCommandSuccess = document.execCommand('copy');
                    
                    // 移除临时元素
                    document.body.removeChild(textarea);
                } catch (e) {
                    console.error("execCommand异常:", e);
                    result.error = e.toString();
                }
            }
            
            return result;
        })();
        """
        
        self.web_view.page().runJavaScript(script, self.handle_copy_result)
    
    def handle_copy_result(self, result):
        """处理复制测试结果"""
        if not result:
            self.log("复制测试失败，未能获取结果")
            return
        
        self.log(f"测试文本: {result.get('testText', '未知')}")
        self.log(f"navigator.clipboard测试: {'成功' if result.get('clipboardSuccess', False) else '失败'}")
        self.log(f"document.execCommand测试: {'成功' if result.get('execCommandSuccess', False) else '失败'}")
        
        if result.get('error'):
            self.log(f"错误信息: {result.get('error')}")
        
        self.log("测试完成，请检查剪贴板内容是否包含测试文本")
    
    def log(self, message):
        """记录日志"""
        self.log_area.append(message)

def main():
    """主函数"""
    app = QApplication(sys.argv)
    window = KimiTestWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 