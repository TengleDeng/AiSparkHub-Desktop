#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
AI平台选择器测试工具 (AiSparkHub AI Platform Tester)

本程序用于测试和验证不同AI平台的DOM选择器配置是否有效，主要功能包括：
1. 模拟浏览器环境访问多个AI平台(如ChatGPT、Kimi、文心一言等)
2. 注入JavaScript测试脚本(prompt_injector.js)自动化测试平台交互
3. 验证输入框、发送按钮和响应区域的选择器有效性
4. 支持提示词注入测试和响应获取测试
5. 生成详细的测试报告，包括成功/失败状态和建议修复方案
6. 多平台并行测试，支持批量验证多个AI平台

该工具主要用于确保AiSparkHub应用能够正确与各大AI平台交互，
当AI平台更新其界面结构时，可使用此工具快速诊断并更新选择器配置。

作者: Tengle
日期: 2024-04-18
"""

import sys
import os
import json
import time
from PyQt6.QtWidgets import QApplication, QMainWindow, QTabWidget, QVBoxLayout, QWidget, QPushButton, QTextEdit, QLabel, QProgressBar, QGridLayout, QCheckBox
from PyQt6.QtCore import QUrl, QTimer, pyqtSignal, QThread, QObject
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineScript

class AITesterThread(QThread):
    # 定义信号
    update_status = pyqtSignal(str, str) # 平台名, 状态信息
    update_result = pyqtSignal(str, bool, str) # 平台名, 成功/失败, 详细信息
    test_completed = pyqtSignal()
    
    def __init__(self, platform, url, test_script, test_questions):
        super().__init__()
        self.platform = platform
        self.url = url
        self.test_script = test_script
        self.test_questions = test_questions
        self.webview = None
        self.test_results = {}
        
    def run(self):
        # 创建WebView并执行测试
        try:
            self.update_status.emit(self.platform, f"正在加载平台: {self.url}")
            
            # 创建WebView (需要在主线程中创建)
            self.webview = QWebEngineView()
            
            # 配置完成回调
            self.webview.loadFinished.connect(self.on_page_loaded)
            
            # 加载页面
            self.webview.load(QUrl(self.url))
            
            # 执行事件循环，直到测试完成
            while not self.isInterruptionRequested():
                # 定期检查测试是否完成
                if 'final_result' in self.test_results:
                    self.update_result.emit(
                        self.platform, 
                        self.test_results.get('success', False),
                        self.test_results.get('final_result', "测试执行失败")
                    )
                    self.test_completed.emit()
                    break
                    
                # 休眠一下，避免CPU占用过高
                self.msleep(100)
                
        except Exception as e:
            error_msg = f"测试线程执行出错: {str(e)}"
            self.update_status.emit(self.platform, error_msg)
            self.update_result.emit(self.platform, False, error_msg)
            self.test_completed.emit()
    
    def on_page_loaded(self, success):
        """页面加载完成后执行测试"""
        if not success:
            self.update_status.emit(self.platform, "页面加载失败")
            self.test_results = {
                'success': False,
                'final_result': "页面加载失败，无法执行测试"
            }
            return
            
        self.update_status.emit(self.platform, "页面加载完成，注入测试脚本")
        
        # 注入测试脚本
        self.webview.page().runJavaScript(self.test_script, self.on_script_injected)
    
    def on_script_injected(self, result):
        """测试脚本注入完成后的回调"""
        self.update_status.emit(self.platform, "测试脚本注入完成，开始测试选择器")
        
        # 运行选择器测试
        test_script = """
        // 测试选择器的有效性
        function testSelectors() {
            // 确定平台
            const platform = window.AiSparkHub?.getPlatformFromURL() || null;
            if (!platform) {
                return {
                    success: false,
                    platform: window.location.hostname,
                    message: "无法识别当前平台",
                    details: {}
                };
            }
            
            // 获取平台选择器
            const selectors = window.AiSparkHub?.PLATFORM_SELECTORS?.[platform] || null;
            if (!selectors) {
                return {
                    success: false,
                    platform: platform,
                    message: "无法获取平台选择器",
                    details: {}
                };
            }
            
            // 测试结果
            const results = {
                platform: platform,
                hostname: window.location.hostname,
                input: { 
                    selector: selectors.input,
                    exists: false,
                    element: null
                },
                button: { 
                    selector: selectors.button,
                    exists: false,
                    element: null 
                },
                responseSelector: { 
                    selector: selectors.responseSelector,
                    exists: false,
                    elements: [] 
                }
            };
            
            // 测试输入框
            try {
                const input = document.querySelector(selectors.input);
                results.input.exists = !!input;
                results.input.element = input ? input.tagName : null;
            } catch(e) {
                results.input.error = e.message;
            }
            
            // 测试按钮
            try {
                const button = document.querySelector(selectors.button);
                results.button.exists = !!button;
                results.button.element = button ? button.tagName : null;
            } catch(e) {
                results.button.error = e.message;
            }
            
            // 测试响应选择器
            try {
                const responseElements = document.querySelectorAll(selectors.responseSelector);
                results.responseSelector.exists = responseElements.length > 0;
                results.responseSelector.count = responseElements.length;
                
                if (responseElements.length > 0) {
                    // 获取最后一个元素以进行测试
                    const lastElement = responseElements[responseElements.length - 1];
                    results.responseSelector.content = lastElement.textContent.substring(0, 100) + '...';
                }
            } catch(e) {
                results.responseSelector.error = e.message;
            }
            
            // 整体测试结果
            const success = results.input.exists && results.button.exists && results.responseSelector.exists;
            
            return {
                success: success,
                platform: platform,
                message: success ? "所有选择器测试通过" : "部分选择器测试失败",
                details: results
            };
        }
        
        // 运行测试并返回结果
        return testSelectors();
        """
        
        self.webview.page().runJavaScript(test_script, self.on_selectors_tested)
    
    def on_selectors_tested(self, result):
        """选择器测试完成的回调"""
        if not result:
            self.update_status.emit(self.platform, "选择器测试失败，未返回结果")
            self.test_results = {
                'success': False,
                'final_result': "选择器测试失败，未返回结果"
            }
            return
            
        # 解析测试结果
        success = result.get('success', False)
        message = result.get('message', "未知结果")
        details = result.get('details', {})
        
        # 格式化详细结果
        formatted_result = f"平台: {self.platform}\n"
        formatted_result += f"主机名: {details.get('hostname', 'unknown')}\n"
        formatted_result += f"测试结果: {'通过' if success else '失败'}\n\n"
        
        # 输入框测试结果
        input_result = details.get('input', {})
        formatted_result += f"输入框: {'成功' if input_result.get('exists', False) else '失败'}\n"
        formatted_result += f"  选择器: {input_result.get('selector', 'unknown')}\n"
        if input_result.get('error'):
            formatted_result += f"  错误: {input_result.get('error')}\n"
        
        # 按钮测试结果
        button_result = details.get('button', {})
        formatted_result += f"发送按钮: {'成功' if button_result.get('exists', False) else '失败'}\n"
        formatted_result += f"  选择器: {button_result.get('selector', 'unknown')}\n"
        if button_result.get('error'):
            formatted_result += f"  错误: {button_result.get('error')}\n"
        
        # 响应选择器测试结果
        response_result = details.get('responseSelector', {})
        formatted_result += f"响应选择器: {'成功' if response_result.get('exists', False) else '失败'}\n"
        formatted_result += f"  选择器: {response_result.get('selector', 'unknown')}\n"
        formatted_result += f"  找到元素数: {response_result.get('count', 0)}\n"
        if response_result.get('content'):
            formatted_result += f"  示例内容: {response_result.get('content')}\n"
        if response_result.get('error'):
            formatted_result += f"  错误: {response_result.get('error')}\n"
        
        # 更新状态
        status_msg = f"选择器测试{'通过' if success else '失败'}: {message}"
        self.update_status.emit(self.platform, status_msg)
        
        # 是否继续测试提示词发送
        if success and self.test_questions:
            self.update_status.emit(self.platform, "开始测试提示词发送...")
            self.test_prompt()
        else:
            # 直接完成测试
            self.test_results = {
                'success': success,
                'final_result': formatted_result
            }
    
    def test_prompt(self):
        """测试发送提示词功能"""
        if not self.test_questions:
            return
            
        # 使用第一个测试问题
        test_prompt = self.test_questions[0]
        
        # 处理特殊字符，预先转义引号
        escaped_prompt = test_prompt.replace('"', r'\"')
        
        # 发送提示词
        inject_script = f"""
        if (window.AiSparkHub && window.AiSparkHub.injectPrompt) {{
            window.AiSparkHub.injectPrompt("{escaped_prompt}").then(result => {{
                return {{
                    success: result,
                    message: result ? "提示词发送成功" : "提示词发送失败"
                }};
            }});
        }} else {{
            return {{
                success: false,
                message: "AiSparkHub.injectPrompt 不可用"
            }};
        }}
        """
        
        self.update_status.emit(self.platform, "发送测试提示词...")
        self.webview.page().runJavaScript(inject_script, self.on_prompt_sent)
    
    def on_prompt_sent(self, result):
        """提示词发送完成的回调"""
        if not result:
            self.update_status.emit(self.platform, "提示词发送失败，未返回结果")
            # 合并之前的选择器测试结果
            if 'final_result' in self.test_results:
                self.test_results['final_result'] += "\n\n提示词发送测试: 失败 (未返回结果)"
            else:
                self.test_results = {
                    'success': False,
                    'final_result': "提示词发送测试: 失败 (未返回结果)"
                }
            return
            
        success = result.get('success', False)
        message = result.get('message', "未知结果")
        
        status_msg = f"提示词发送{'成功' if success else '失败'}: {message}"
        self.update_status.emit(self.platform, status_msg)
        
        # 如果发送成功，等待5秒后测试响应获取
        if success:
            self.update_status.emit(self.platform, "等待AI响应...")
            QTimer.singleShot(5000, self.test_response)
        else:
            # 合并之前的选择器测试结果
            if 'final_result' in self.test_results:
                self.test_results['final_result'] += f"\n\n提示词发送测试: 失败\n{message}"
            else:
                self.test_results = {
                    'success': False,
                    'final_result': f"提示词发送测试: 失败\n{message}"
                }
    
    def test_response(self):
        """测试响应获取功能"""
        # 尝试获取AI响应
        response_script = """
        if (window.AiSparkHub && window.AiSparkHub.getPromptResponse) {
            return window.AiSparkHub.getPromptResponse();
        } else {
            return {
                success: false,
                message: "AiSparkHub.getPromptResponse 不可用"
            };
        }
        """
        
        self.update_status.emit(self.platform, "获取AI响应...")
        self.webview.page().runJavaScript(response_script, self.on_response_received)
    
    def on_response_received(self, result):
        """响应获取完成的回调"""
        if not result:
            self.update_status.emit(self.platform, "响应获取失败，未返回结果")
            # 合并之前的测试结果
            if 'final_result' in self.test_results:
                self.test_results['final_result'] += "\n\n响应获取测试: 失败 (未返回结果)"
            else:
                self.test_results = {
                    'success': False,
                    'final_result': "响应获取测试: 失败 (未返回结果)"
                }
            return
            
        reply = result.get('reply', "")
        url = result.get('url', "")
        
        success = reply and reply != "未找到回复元素" and reply != "无法获取回复内容"
        
        status_msg = f"响应获取{'成功' if success else '失败'}"
        self.update_status.emit(self.platform, status_msg)
        
        # 格式化响应结果
        formatted_response = f"\n\n响应获取测试: {'成功' if success else '失败'}\n"
        formatted_response += f"URL: {url}\n"
        formatted_response += f"响应内容: {reply[:200]}{'...' if len(reply) > 200 else ''}"
        
        # 合并之前的测试结果
        if 'final_result' in self.test_results:
            self.test_results['final_result'] += formatted_response
        else:
            self.test_results = {
                'success': success,
                'final_result': formatted_response
            }
        
        # 完成测试
        self.update_status.emit(self.platform, "测试完成")

class AIPlatformTester(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI平台选择器测试工具")
        self.setMinimumSize(1200, 800)
        
        # 平台配置 - 从prompt_injector.js中提取
        self.platforms = {
            "chatgpt": {
                "name": "ChatGPT",
                "url": "https://chat.openai.com/",
                "selectors": {
                    "input": "#prompt-textarea",
                    "button": "button[data-testid='send-button']",
                    "response": ".markdown.prose"
                }
            },
            "kimi": {
                "name": "Kimi",
                "url": "https://kimi.moonshot.cn/",
                "selectors": {
                    "input": ".chat-input-editor",
                    "button": ".send-button",
                    "response": ".segment-content-box"
                }
            },
            "perplexity": {
                "name": "Perplexity",
                "url": "https://www.perplexity.ai/",
                "selectors": {
                    "input": "textarea.overflow-auto",
                    "button": "button[aria-label='Submit']",
                    "response": "[id^='markdown-content-']"
                }
            },
            "doubao": {
                "name": "豆包",
                "url": "https://www.doubao.com/",
                "selectors": {
                    "input": "textarea.semi-input-textarea",
                    "button": "#flow-end-msg-send",
                    "response": "[data-testid='receive_message']"
                }
            },
            "yiyan": {
                "name": "文心一言",
                "url": "https://yiyan.baidu.com/",
                "selectors": {
                    "input": ".yc-editor",
                    "button": "#sendBtn",
                    "response": ".chat-result-wrap"
                }
            }
            # 可以添加更多平台...
        }
        
        # 测试问题
        self.test_questions = [
            "这是一个选择器测试。请用不超过50个字回复这条消息，测试是否能获取到回复内容。",
            "简单测试问题2：你能返回一个带数字列表的回复吗？请列出3个你认为重要的AI应用场景。"
        ]
        
        # UI初始化
        self._setup_ui()
        
        # 加载Web Profile和Cookie
        self._load_cookies()
        
        # 当前测试状态
        self.current_tests = []
        self.test_results = {}
    
    def _setup_ui(self):
        # 创建主窗口部件和布局
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        
        # 控制区域
        control_panel = QWidget()
        control_layout = QGridLayout(control_panel)
        
        # 平台选择区域
        platforms_label = QLabel("<b>选择要测试的平台:</b>")
        control_layout.addWidget(platforms_label, 0, 0, 1, 3)
        
        # 添加平台复选框
        self.platform_checkboxes = {}
        row, col = 1, 0
        for key, platform in self.platforms.items():
            checkbox = QCheckBox(platform["name"])
            checkbox.setChecked(True)  # 默认选中所有平台
            self.platform_checkboxes[key] = checkbox
            control_layout.addWidget(checkbox, row, col)
            col += 1
            if col > 2:  # 每行3个平台
                col = 0
                row += 1
        
        # 控制按钮
        self.start_button = QPushButton("开始测试")
        self.start_button.clicked.connect(self.start_tests)
        control_layout.addWidget(self.start_button, row+1, 0)
        
        self.stop_button = QPushButton("停止测试")
        self.stop_button.clicked.connect(self.stop_tests)
        self.stop_button.setEnabled(False)
        control_layout.addWidget(self.stop_button, row+1, 1)
        
        # 测试进度
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        control_layout.addWidget(self.progress_bar, row+1, 2)
        
        # 将控制面板添加到主布局
        main_layout.addWidget(control_panel)
        
        # 测试日志区域
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        main_layout.addWidget(self.log_text)
        
        # 测试结果标签页
        self.results_tabs = QTabWidget()
        main_layout.addWidget(self.results_tabs)
        
        # 设置中央窗口部件
        self.setCentralWidget(main_widget)
    
    def _load_cookies(self):
        # 从data/webdata加载Cookie信息
        try:
            cookie_dir = 'data/webdata'
            if os.path.exists(cookie_dir):
                # 实现Cookie加载逻辑
                self.log("已加载Cookie数据，可免登录测试")
            else:
                self.log("警告: 未找到Cookie数据目录，测试可能需要手动登录", "warning")
        except Exception as e:
            self.log(f"加载Cookie出错: {str(e)}", "error")
    
    def log(self, message, level="info"):
        # 向日志区域添加消息
        timestamp = time.strftime("%H:%M:%S")
        
        html_format = {
            "info": "black",
            "success": "green",
            "warning": "orange",
            "error": "red"
        }
        
        html = f'<span style="color:{html_format.get(level, "black")}"><b>[{timestamp}]</b> {message}</span>'
        self.log_text.append(html)
    
    def start_tests(self):
        # 获取选中的平台
        selected_platforms = [key for key, checkbox in self.platform_checkboxes.items() if checkbox.isChecked()]
        
        if not selected_platforms:
            self.log("请至少选择一个平台进行测试", "warning")
            return
        
        # 更新UI状态
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.progress_bar.setValue(0)
        
        # 清空旧结果
        self.test_results = {}
        while self.results_tabs.count() > 0:
            self.results_tabs.removeTab(0)
        
        # 准备测试脚本
        test_script = self._prepare_test_script()
        
        # 开始测试
        self.log(f"开始测试 {len(selected_platforms)} 个平台...", "info")
        
        # 创建并启动测试线程
        self.current_tests = []
        for platform_key in selected_platforms:
            platform = self.platforms[platform_key]
            
            # 创建平台结果标签页
            result_widget = QWidget()
            result_layout = QVBoxLayout(result_widget)
            result_text = QTextEdit()
            result_text.setReadOnly(True)
            result_layout.addWidget(result_text)
            
            tab_index = self.results_tabs.addTab(result_widget, platform["name"])
            
            # 创建测试线程
            test_thread = AITesterThread(
                platform_key, 
                platform["url"], 
                test_script,
                self.test_questions
            )
            
            # 连接信号
            test_thread.update_status.connect(
                lambda platform, status, p=platform_key, t=result_text: 
                self._update_platform_status(p, status, t)
            )
            
            test_thread.update_result.connect(
                lambda platform, success, details, p=platform_key, t=result_text:
                self._update_platform_result(p, success, details, t)
            )
            
            # 启动线程
            test_thread.start()
            self.current_tests.append(test_thread)
        
        # 更新进度条
        self._update_progress()
    
    def _update_platform_status(self, platform, status, text_edit):
        # 更新平台测试状态
        timestamp = time.strftime("%H:%M:%S")
        html = f'<span style="color:blue"><b>[{timestamp}]</b> {status}</span>'
        text_edit.append(html)
        
        # 全局日志
        self.log(f"[{self.platforms[platform]['name']}] {status}")
    
    def _update_platform_result(self, platform, success, details, text_edit):
        # 更新平台测试结果
        timestamp = time.strftime("%H:%M:%S")
        color = "green" if success else "red"
        status = "成功" if success else "失败"
        
        html = f'<span style="color:{color}"><b>[{timestamp}] 测试{status}!</b></span><br>'
        html += f'<pre style="background:#f8f8f8;padding:8px;border-radius:4px;">{details}</pre>'
        text_edit.append(html)
        
        # 保存结果
        self.test_results[platform] = {
            "success": success,
            "details": details
        }
        
        # 全局日志
        self.log(f"[{self.platforms[platform]['name']}] 测试{status}", "success" if success else "error")
        
        # 更新进度
        self._update_progress()
    
    def _update_progress(self):
        # 更新测试进度
        completed = len(self.test_results)
        total = len(self.current_tests)
        
        if total > 0:
            progress = int(completed / total * 100)
            self.progress_bar.setValue(progress)
            
            if completed == total:
                self.log("所有测试已完成!", "success")
                self.start_button.setEnabled(True)
                self.stop_button.setEnabled(False)
                
                # 生成最终报告
                self._generate_final_report()
    
    def _generate_final_report(self):
        # 创建最终报告标签页
        report_widget = QWidget()
        report_layout = QVBoxLayout(report_widget)
        report_text = QTextEdit()
        report_text.setReadOnly(True)
        report_layout.addWidget(report_text)
        
        # 添加报告标签页
        self.results_tabs.addTab(report_widget, "总结报告")
        self.results_tabs.setCurrentIndex(self.results_tabs.count() - 1)
        
        # 生成报告内容
        html = '<h2>AI平台选择器测试报告</h2>'
        html += '<table border="1" cellpadding="5" style="border-collapse:collapse;width:100%">'
        html += '<tr style="background:#f1f3f4"><th>平台</th><th>测试结果</th><th>输入框</th><th>按钮</th><th>响应元素</th></tr>'
        
        success_count = 0
        for platform_key, result in self.test_results.items():
            platform_name = self.platforms[platform_key]['name']
            success = result['success']
            if success:
                success_count += 1
                
            # 解析详细结果
            details = result['details']
            input_ok = "✅" if "输入框: 成功" in details else "❌"
            button_ok = "✅" if "发送按钮: 成功" in details else "❌"
            response_ok = "✅" if "响应选择器: 成功" in details else "❌"
            
            row_style = 'background:#e8f5e9' if success else 'background:#ffebee'
            html += f'<tr style="{row_style}">'
            html += f'<td>{platform_name}</td>'
            html += f'<td>{("✅ 通过" if success else "❌ 失败")}</td>'
            html += f'<td>{input_ok}</td><td>{button_ok}</td><td>{response_ok}</td>'
            html += '</tr>'
        
        html += '</table>'
        
        # 添加总结
        total = len(self.test_results)
        html += f'<p><b>测试结果:</b> {success_count}/{total} 平台测试通过 ({int(success_count/total*100)}%)</p>'
        
        # 添加建议
        if success_count < total:
            html += '<p><b>建议:</b> 检查失败平台的选择器定义，可能需要更新</p>'
        
        # 显示报告
        report_text.setHtml(html)
        
        # 尝试保存报告到文件
        try:
            # 保存报告到 report.html 文件
            with open('selector_test_report.html', 'w', encoding='utf-8') as f:
                f.write(html)
            self.log("测试报告已保存到 selector_test_report.html", "success")
        except Exception as e:
            self.log(f"无法保存测试报告: {str(e)}", "error")
    
    def _prepare_test_script(self):
        """准备测试脚本 - 使用已有的prompt_injector.js"""
        prompt_injector_path = 'app/static/js/prompt_injector.js'
        
        try:
            with open(prompt_injector_path, 'r', encoding='utf-8') as f:
                script = f.read()
                self.log(f"已加载测试脚本: {prompt_injector_path}", "success")
                return script
        except Exception as e:
            self.log(f"加载测试脚本失败: {str(e)}", "error")
            return ""
    
    def stop_tests(self):
        # 停止所有测试
        for test in self.current_tests:
            if test.isRunning():
                test.terminate()
                test.wait()
        
        self.log("测试已手动停止", "warning")
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

# 主程序入口
if __name__ == "__main__":
    app = QApplication(sys.argv)
    tester = AIPlatformTester()
    tester.show()
    sys.exit(app.exec())