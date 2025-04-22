#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
AI对话视图系统 - AIView/AIWebView

功能架构:
1. 多AI平台网页容器
   - 动态加载配置(SUPPORTED_AI_PLATFORMS)
   - 共享WebProfile保持登录状态
   - 自动注入提示词脚本(prompt_injector.js)

2. 交互控制系统
   - 视图拖拽排序(move_left/move_right)
   - 单视图最大化/恢复(toggle_maximize_view)
   - 动态主题适配(theme_changed信号)

3. 数据流管理
   - 批量提示词填充(fill_prompt)
   - 异步响应收集(collect_all_responses)
   - URL智能解析(open_multiple_urls)

设计约束:
- 必须与ThemeManager配合使用
- 需要WebEngineCore >= Qt6.2
- 图标资源需放在/icons目录

维护记录:
- 2025-04-20 增加视图最大化功能
- 2025-04-18 实现主题响应式图标
- 2025-04-15 初版多AI容器支持
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QSplitter, QComboBox, QPushButton, QApplication
from PyQt6.QtCore import Qt, QUrl, QFile, QIODevice, QTimer, QSize
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings, QWebEngineScript
from PyQt6.QtGui import QPixmap, QIcon
import os
import qtawesome as qta
import sys
import logging
import json
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtCore import pyqtSlot, QObject

from app.config import SUPPORTED_AI_PLATFORMS
from app.controllers.web_profile_manager import WebProfileManager
from app.controllers.settings_manager import SettingsManager
from app.controllers.theme_manager import ThemeManager

# 图标文件夹路径 - 考虑打包环境和开发环境
ICON_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "icons")
if not os.path.exists(ICON_DIR) and getattr(sys, 'frozen', False):
    # 打包环境下可能路径不同，尝试相对于可执行文件的路径
    base_dir = os.path.dirname(sys.executable)
    ICON_DIR = os.path.join(base_dir, "icons")

# 注入脚本路径
INJECTOR_SCRIPT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "js", "prompt_injector.js")

class WebEnginePage(QWebEnginePage):
    """自定义WebEnginePage以捕获网页日志和错误"""
    
    def __init__(self, profile, parent=None):
        super().__init__(profile, parent)
        self.logger = logging.getLogger("AiSparkHub.WebConsole")
        self.view_name = parent.ai_name if hasattr(parent, 'ai_name') else "未知视图"
        
    def javaScriptConsoleMessage(self, level, message, line, source):
        """接收JavaScript控制台消息"""
        # 使用数字枚举值替代不存在的常量名称
        log_level_map = {
            0: "INFO",      # 对应 InfoMessageLevel
            1: "WARNING",   # 对应 WarningMessageLevel 
            2: "ERROR"      # 对应 ErrorMessageLevel
        }
        log_level = log_level_map.get(level, "INFO")
        source_name = os.path.basename(source) if source else "unknown"
        log_msg = f"[{self.view_name}][JS-{log_level}] {source_name}:{line} - {message}"
        
        # 根据级别记录到不同的日志级别
        if log_level == "ERROR":
            self.logger.error(log_msg)
        elif log_level == "WARNING":
            self.logger.warning(log_msg)
        else:
            self.logger.info(log_msg)
        
    def certificateError(self, error):
        """捕获证书错误"""
        url = error.url().toString()
        self.logger.error(f"[{self.view_name}] 证书错误: {url} - {error.errorDescription()}")
        return False  # 取消加载

class AIWebView(QWebEngineView):
    """单个AI网页视图"""
    
    def __init__(self, ai_config):
        """初始化AI网页视图
        
        Args:
            ai_config (dict): AI平台配置字典
        """
        super().__init__()
        self.ai_name = ai_config["name"]
        self.ai_url = ai_config["url"]
        self.input_selector = ai_config["input_selector"]
        self.submit_selector = ai_config["submit_selector"]
        self.response_selector = ai_config.get("response_selector", "")
        
        # 初始化日志器
        self.logger = logging.getLogger(f"AiSparkHub.AIView.{self.ai_name}")
        self.logger.info(f"初始化 {self.ai_name} 视图")
        
        # 使用共享的profile，保存登录信息
        self.profile_manager = WebProfileManager()
        shared_profile = self.profile_manager.get_profile()
        
        # 使用自定义Page以捕获网页日志
        web_page = WebEnginePage(shared_profile, self)
        self.setPage(web_page)
        
        # 创建桥接对象 - 但暂不创建WebChannel
        self.highlight_bridge = self._create_highlight_bridge()
        self.log_bridge = self._create_log_bridge()
        
        # WebChannel将在页面加载完成后创建
        self.channel = None
        
        self.logger.info("桥接对象已创建，WebChannel将在页面加载完成后初始化")
        
        # 设置剪贴板权限
        settings = web_page.settings()
        
        # 设置权限 - 使用try/except以兼容不同版本的PyQt6
        # 剪贴板权限
        try:
            settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard, True)
            self.logger.debug(f"已启用剪贴板访问权限")
        except (AttributeError, TypeError):
            self.logger.warning(f"JavascriptCanAccessClipboard属性不可用")
        
        try:
            settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanPaste, True)
            self.logger.debug(f"已启用剪贴板粘贴权限")
        except (AttributeError, TypeError):
            self.logger.warning(f"JavascriptCanPaste属性不可用")
        
        # 其他权限
        try:
            settings.setAttribute(QWebEngineSettings.WebAttribute.FullScreenSupportEnabled, True)
            self.logger.debug(f"已启用全屏支持")
        except (AttributeError, TypeError):
            self.logger.warning(f"FullScreenSupportEnabled属性不可用")
        
        try:
            settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
            self.logger.debug(f"已启用本地内容访问远程URL")
        except (AttributeError, TypeError):
            self.logger.warning(f"LocalContentCanAccessRemoteUrls属性不可用")
            
        try:
            settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
            self.logger.debug(f"已启用本地内容访问文件URL")
        except (AttributeError, TypeError):
            self.logger.warning(f"LocalContentCanAccessFileUrls属性不可用")
        
        # 设置最小高度
        self.setMinimumHeight(30)
        
        # 加载网页
        self.load(QUrl(self.ai_url))
        
        # 设置加载状态监听
        self.loadFinished.connect(self.on_load_finished)
        
        # 设置JavaScript日志处理器
        self.page().settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        
        # 获取数据库管理器实例
        app = QApplication.instance()
        if hasattr(app, 'db_manager'):
            self.db_manager = app.db_manager
        else:
            from app.models.database import DatabaseManager
            self.db_manager = DatabaseManager()
            self.logger.warning(f"无法从应用实例获取数据库管理器，创建新实例")
    
    def _create_highlight_bridge(self):
        """创建高亮桥接对象"""
        class HighlightBridge(QObject):
            @pyqtSlot(str)
            def saveHighlight(self, highlight_json):
                self.parent().logger.info("WebChannel接收到高亮保存请求")
                self.parent().save_highlight_from_js(highlight_json)
                
            @pyqtSlot(int)
            def updateHighlightApplied(self, highlight_id):
                self.parent().logger.info(f"WebChannel接收到高亮应用通知，ID: {highlight_id}")
                self.parent().update_highlight_applied_time(highlight_id)
        
        # 创建并返回桥接对象
        bridge = HighlightBridge(self)
        return bridge
    
    def _create_log_bridge(self):
        """创建日志桥接对象"""
        class LogBridge(QObject):
            @pyqtSlot(str)
            def receiveJsLog(self, log_json):
                self.parent().receive_js_log(log_json)
        
        # 创建并返回桥接对象
        bridge = LogBridge(self)
        return bridge
    
    def on_load_finished(self, success):
        """网页加载完成后的处理"""
        if success:
            self.logger.info(f"页面加载完成: {self.url().toString()}")
            
            # 导入WebChannel世界ID定义
            try:
                from PyQt6.QtWebEngineCore import QWebEngineScript
                self.MAIN_WORLD = QWebEngineScript.ScriptWorldId.MainWorld
                self.logger.info("导入ScriptWorldId成功，使用MainWorld注入")
            except (ImportError, AttributeError):
                self.MAIN_WORLD = 0  # 默认值，如果无法导入
                self.logger.warning("无法导入ScriptWorldId，使用默认值0")
                
            # 重新初始化WebChannel，确保世界ID一致
            self.channel = None
            
            # 首先注入qwebchannel.js脚本，然后在回调中设置WebChannel
            self.inject_qwebchannel_script(callback=self._continue_page_init)
        else:
            self.logger.error(f"页面加载失败: {self.url().toString()}")

    def _continue_page_init(self):
        """QWebChannel脚本加载后继续页面初始化"""
        self.logger.info("QWebChannel脚本加载完成，继续初始化页面...")
        
        # 创建WebChannel并设置 - 在QWebChannel脚本加载后
        self._setup_webchannel()
        
        # 注入Rangy脚本
        self.inject_rangy_scripts()
        
        # 注入提示词注入脚本
        self.inject_script()
        
        # 注入F12快捷键脚本，用于打开开发者工具
        try:
            debug_key_script = """
            document.addEventListener('keydown', function(e) {
                if (e.key === 'F12') {
                    console.log('F12 pressed - attempting to open dev tools');
                    // 在PyQt6 6.9.0中，此操作可打开开发者工具
                }
            });
            console.log('Debug key listener installed');
            """
            self.page().runJavaScript(debug_key_script)
        except Exception as e:
            self.logger.error(f"注入F12快捷键脚本失败: {str(e)}")
            
        # 安装JavaScript日志处理器
        self._install_js_log_handler()
        
        # 注入事件监听代码 - 在WebChannel设置后
        self.setup_highlight_handlers()
            
        # 加载当前页面的高亮数据
        self.load_highlights_for_current_page()
        
        # 测试WebChannel通信
        QTimer.singleShot(500, self.test_webchannel_communication)

    def inject_qwebchannel_script(self, callback=None):
        """注入qwebchannel.js脚本，这是WebChannel通信的必要条件
        
        Args:
            callback: 脚本注入完成后的回调函数
        """
        self.logger.info("正在注入qwebchannel.js脚本...")
        
        # 简化版的QWebChannel实现，避免语法错误和CSP限制
        qwebchannel_simplified = """
(function() {
    // 检查QWebChannel是否已存在，如果存在则不重复定义
    if (typeof QWebChannel !== 'undefined') {
        console.log('QWebChannel已存在，无需注入');
        return true;
    }
    
    console.log('正在定义QWebChannel...');
    
    // 定义消息类型
    var QWebChannelMessageTypes = {
        signal: 1,
        propertyUpdate: 2,
        init: 3,
        idle: 4,
        debug: 5,
        invokeMethod: 6,
        connectToSignal: 7,
        disconnectFromSignal: 8,
        setProperty: 9,
        response: 10
    };
    
    // 定义QWebChannel构造函数
    window.QWebChannel = function(transport, initCallback) {
        console.log('QWebChannel构造函数被调用');
        var channel = this;
        this.transport = transport;
        this.objects = {};
        
        this.send = function(data) {
            if (typeof(data) !== "string") {
                data = JSON.stringify(data);
            }
            channel.transport.send(data);
        };
        
        this.transport.onmessage = function(message) {
            var data = message.data;
            if (typeof data === "string") {
                data = JSON.parse(data);
            }
            switch (data.type) {
                case QWebChannelMessageTypes.signal:
                    console.log('收到signal消息');
                    break;
                case QWebChannelMessageTypes.response:
                    console.log('收到response消息');
                    break;
                case QWebChannelMessageTypes.propertyUpdate:
                    console.log('收到propertyUpdate消息');
                    break;
                default:
                    console.log('收到其他类型消息');
                    break;
            }
        };
        
        // 设置延迟，避免出现错误
        setTimeout(function() {
            try {
                if (initCallback) {
                    console.log('调用QWebChannel初始化回调');
                    initCallback(channel);
                }
            } catch(e) {
                console.error('QWebChannel初始化回调错误:', e);
            }
        }, 10);
    };
    
    console.log('QWebChannel定义完成');
    return true;
})();

// 测试QWebChannel是否可用
try {
    if (typeof QWebChannel === 'undefined') {
        console.error('QWebChannel定义失败');
    } else {
        console.log('QWebChannel定义成功, 类型:', typeof QWebChannel);
    }
} catch(e) {
    console.error('QWebChannel检查出错:', e);
}
        """
        
        try:
            # 先检查是否已加载
            check_script = """
            (function() {
                return typeof QWebChannel !== 'undefined';
            })();
            """
            
            def handle_check(result):
                if result:
                    self.logger.info("QWebChannel已存在，无需注入")
                    # 即使已经存在也继续执行回调
                    if callback:
                        callback()
                else:
                    self.logger.info("QWebChannel未定义，正在注入脚本...")
                    
                    # 使用在MainWorld中注入脚本
                    def verify_and_call_callback(result):
                        self._verify_qwebchannel_loaded(result)
                        if callback:
                            callback()
                            
                    try:
                        self.page().runJavaScript(
                            qwebchannel_simplified, 
                            self.MAIN_WORLD,
                            verify_and_call_callback
                        )
                    except TypeError:
                        # 回退到不指定世界的方式
                        self.logger.warning("无法在MainWorld中注入脚本，使用默认方式")
                        self.page().runJavaScript(
                            qwebchannel_simplified,
                            verify_and_call_callback
                        )
                    
            # 在与脚本相同的世界中执行检查
            try:
                self.page().runJavaScript(check_script, self.MAIN_WORLD, handle_check)
            except TypeError:
                self.page().runJavaScript(check_script, handle_check)
            
        except Exception as e:
            self.logger.error(f"注入QWebChannel脚本失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            # 出错时也执行回调，确保初始化流程继续
            if callback:
                callback()

    def _setup_webchannel(self):
        """设置WebChannel和注册桥接对象"""
        try:
            # 如果channel已存在，则先清除
            if self.channel:
                self.logger.info("清除现有WebChannel并重新创建")
                self.page().setWebChannel(None)
                self.channel = None
                
            # 创建新的WebChannel对象
            self.logger.info("创建新的WebChannel并注册桥接对象")
            self.channel = QWebChannel(self.page())
            
            # 为了确保桥接对象在整个应用程序生命周期内都可用
            # 将它们设为页面的属性，防止被垃圾回收
            self.page().setProperty("_highlight_bridge_ref", self.highlight_bridge)
            self.page().setProperty("_log_bridge_ref", self.log_bridge)
            
            # 注册桥接对象到WebChannel
            self.logger.info("注册highlightBridge和bridge对象到WebChannel")
            self.channel.registerObject("highlightBridge", self.highlight_bridge)
            self.channel.registerObject("bridge", self.log_bridge)
            
            # 使用正确的世界ID设置WebChannel
            try:
                # 明确指定在MainWorld中设置WebChannel
                self.page().setWebChannel(self.channel, self.MAIN_WORLD)
                self.logger.info(f"WebChannel已设置在MainWorld({self.MAIN_WORLD})中")
            except (TypeError, AttributeError) as e:
                # 如果不支持指定世界，则使用默认方式
                self.logger.warning(f"设置WebChannel世界ID失败: {str(e)}，使用默认方式")
                self.page().setWebChannel(self.channel)
                
            self.logger.info("WebChannel设置和对象注册完成")
            
            # 在WebChannel设置完成后等待一段时间再测试
            QTimer.singleShot(500, self._test_webchannel_after_setup)
                
        except Exception as e:
            self.logger.error(f"WebChannel设置失败: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
    
    def _test_webchannel_after_setup(self):
        """在WebChannel设置后执行简单测试"""
        check_script = """
        (function() {
            if (typeof qt !== 'undefined' && typeof qt.webChannelTransport !== 'undefined') {
                try {
                    new QWebChannel(qt.webChannelTransport, function(channel) {
                        var objects = Object.keys(channel.objects);
                        console.log('WebChannel测试对象列表:', objects);
                        return {
                            success: true,
                            objects: objects,
                            has_highlight_bridge: objects.includes('highlightBridge'),
                            has_bridge: objects.includes('bridge')
                        };
                    });
                } catch(e) {
                    console.error('WebChannel测试出错:', e);
                    return {success: false, error: e.toString()};
                }
            }
            return {success: false, error: 'qt.webChannelTransport未定义'};
        })();
        """
        
        try:
            self.page().runJavaScript(check_script, self.MAIN_WORLD, 
                lambda result: self.logger.info(f"WebChannel设置后测试结果: {result}")
            )
        except Exception:
            self.page().runJavaScript(check_script, 
                lambda result: self.logger.info(f"WebChannel设置后测试结果: {result}")
            )
    
    def _verify_qwebchannel_loaded(self, result):
        """验证QWebChannel是否成功加载"""
        self.logger.info(f"QWebChannel脚本注入结果: {result if result is not None else 'OK'}")
        
        # 再次检查QWebChannel是否定义成功
        check_script = """
        (function() {
            var status = {
                qwebchannel_exists: typeof QWebChannel !== 'undefined',
                qwebchannel_type: typeof QWebChannel,
                is_function: typeof QWebChannel === 'function'
            };
            console.log('QWebChannel加载检查:', JSON.stringify(status));
            return status;
        })();
        """
        
        # 使用相同的世界ID执行检查
        try:
            self.page().runJavaScript(check_script, self.MAIN_WORLD, lambda result: self.logger.info(f"QWebChannel验证结果: {result}"))
        except TypeError:
            self.page().runJavaScript(check_script, lambda result: self.logger.info(f"QWebChannel验证结果: {result}"))
    
    def test_webchannel_communication(self):
        """测试WebChannel通信是否正常工作"""
        self.logger.info("开始测试WebChannel通信...")
        
        # 1. 检查qt对象是否存在
        check_script = """
        (function() {
            var result = {
                qt_exists: typeof qt !== 'undefined',
                transport_exists: typeof qt !== 'undefined' && typeof qt.webChannelTransport !== 'undefined',
                webchannel_exists: typeof QWebChannel !== 'undefined'
            };
            console.log('WebChannel状态检查: ', JSON.stringify(result));
            return result;
        })();
        """
        self.page().runJavaScript(check_script, self._handle_webchannel_check)
        
        # 2. 如果QWebChannel不存在，先注入脚本再测试
        def _ensure_qwebchannel_and_test():
            self.page().runJavaScript("typeof QWebChannel !== 'undefined'", lambda result: self._execute_test() if result else self._inject_and_test())
        
        # 延迟执行，确保WebChannel检查完成
        QTimer.singleShot(500, _ensure_qwebchannel_and_test)
    
    def _inject_and_test(self):
        """注入QWebChannel脚本并测试通信"""
        self.logger.info("QWebChannel未定义，正在注入脚本并重新测试...")
        
        # 定义注入脚本后的回调函数
        def after_inject(result):
            self.logger.info(f"QWebChannel脚本注入结果: {result if result is not None else 'OK'}")
            # 延迟执行测试，确保脚本已加载
            QTimer.singleShot(1000, self._execute_test)
        
        # 注入脚本
        self.page().runJavaScript("""
        // 如果QWebChannel未定义，则在全局作用域上定义一个测试函数
        if (typeof QWebChannel === 'undefined') {
            console.log('正在注入临时QWebChannel实现...');
            
            // 简化版QWebChannel实现，仅用于测试
            window.QWebChannel = function(transport, initCallback) {
                console.log('QWebChannel构造函数被调用');
                this.transport = transport;
                this.objects = {};
                
                if (initCallback) {
                    console.log('调用QWebChannel初始化回调');
                    initCallback(this);
                }
            };
            
            console.log('QWebChannel已定义');
            return true;
        }
        return false;
        """, after_inject)
    
    def _execute_test(self):
        """执行WebChannel通信测试"""
        self.logger.info("正在执行WebChannel通信测试...")
        
        # 尝试主动发送一个测试事件
        test_script = """
        (function() {
            try {
                console.log('准备测试WebChannel通信...');
                if (typeof QWebChannel === 'undefined') {
                    console.error('QWebChannel仍然未定义，无法测试通信');
                    return {success: false, error: 'QWebChannel未定义'};
                }
                
                console.log('QWebChannel已定义，类型:', typeof QWebChannel);
                
                if (typeof qt === 'undefined' || typeof qt.webChannelTransport === 'undefined') {
                    console.error('qt.webChannelTransport未定义，无法测试通信');
                    return {success: false, error: 'qt.webChannelTransport未定义'};
                }
                
                // 创建一个直接绑定到window的bridge对象，用于测试
                window.testBridge = {
                    saveHighlight: function(data) {
                        console.log('测试bridge.saveHighlight被调用，数据:', data);
                        return true;
                    },
                    updateHighlightApplied: function(id) {
                        console.log('测试bridge.updateHighlightApplied被调用，ID:', id);
                        return true;
                    }
                };
                
                // 绕过QWebChannel，直接创建并触发高亮事件
                console.log('创建直接高亮测试...');
                try {
                    var testData = {
                        text_content: '测试WebChannel通信',
                        url: window.location.href,
                        timestamp: Date.now(),
                        test: true
                    };
                    
                    var event = new CustomEvent('aiSaveHighlightToPython', {
                        detail: JSON.stringify(testData)
                    });
                    
                    console.log('触发高亮事件aiSaveHighlightToPython');
                    document.dispatchEvent(event);
                    console.log('高亮事件已触发');
                } catch(directError) {
                    console.error('直接触发事件失败:', directError);
                }
                
                return {success: true, message: '测试完成，请检查控制台日志'};
            } catch(e) {
                console.error('测试WebChannel通信失败:', e);
                return {success: false, error: e.toString()};
            }
        })();
        """
        
        self.page().runJavaScript(test_script, self._handle_webchannel_test)
        
        # 测试直接访问bridge对象
        direct_test = """
        (function() {
            if (typeof qt !== 'undefined' && typeof qt.webChannelTransport !== 'undefined') {
                // 尝试直接获取WebChannel对象
                try {
                    new QWebChannel(qt.webChannelTransport, function(channel) {
                        console.log('直接获取WebChannel对象成功，可用对象:', Object.keys(channel.objects));
                        
                        // 检查highlightBridge对象是否存在
                        if (channel.objects.highlightBridge) {
                            console.log('找到highlightBridge对象，尝试直接调用');
                            
                            var testData = {
                                text_content: '直接调用测试',
                                url: window.location.href,
                                timestamp: new Date().toISOString(),
                                test: true
                            };
                            
                            // 直接调用Python的方法
                            try {
                                channel.objects.highlightBridge.saveHighlight(JSON.stringify(testData));
                                console.log('直接调用highlightBridge.saveHighlight成功');
                                return {direct_call: true, message: '直接调用成功'};
                            } catch(callError) {
                                console.error('直接调用highlightBridge方法失败:', callError);
                                return {direct_call: false, error: callError.toString()};
                            }
                        } else {
                            console.error('无法找到highlightBridge对象');
                            return {direct_call: false, error: '找不到highlightBridge对象'};
                        }
                    });
                    return {attempted: true};
                } catch(e) {
                    console.error('直接获取WebChannel失败:', e);
                    return {attempted: false, error: e.toString()};
                }
            } else {
                return {attempted: false, error: 'qt.webChannelTransport未定义'};
            }
        })();
        """
        
        self.page().runJavaScript(direct_test, lambda result: self.logger.info(f"WebChannel直接访问测试结果: {result}"))
    
    def _handle_webchannel_check(self, result):
        """处理WebChannel检查结果"""
        if result:
            self.logger.info(f"WebChannel状态: qt存在={result.get('qt_exists', False)}, "
                           f"transport存在={result.get('transport_exists', False)}, "
                           f"QWebChannel存在={result.get('webchannel_exists', False)}")
        else:
            self.logger.error("WebChannel检查返回空结果")
    
    def _handle_webchannel_test(self, result):
        """处理WebChannel测试结果"""
        self.logger.info(f"WebChannel测试结果: {result}")
    
    def setup_highlight_handlers(self):
        """设置高亮处理器，处理来自JavaScript的高亮相关事件"""
        self.logger.info(f"正在为{self.ai_name}设置高亮事件监听...")
        
        # 先确认WebChannel是否已设置
        if not self.channel:
            self.logger.warning("WebChannel未设置，先初始化WebChannel再设置高亮处理器")
            self._setup_webchannel()
        
        # 注入事件监听JavaScript
        js_code = """
        document.addEventListener('aiSaveHighlightToPython', function(event) {
            try {
                console.log('接收到高亮保存事件');
                const highlightData = JSON.parse(event.detail);
                console.log('已解析高亮数据:', highlightData);
                
                if (typeof qt === 'undefined' || typeof qt.webChannelTransport === 'undefined') {
                    console.error('错误: qt.webChannelTransport未定义，无法保存高亮');
                    // 失败时自动切换到备用方案
                    window.AiSparkHub.webChannelAvailable = false;
                    window.AiSparkHub.fallbackHighlight(highlightData);
                    return;
                }
                
                if (typeof QWebChannel === 'undefined') {
                    console.error('错误: QWebChannel未定义，无法保存高亮');
                    // 失败时自动切换到备用方案
                    window.AiSparkHub.webChannelAvailable = false;
                    window.AiSparkHub.fallbackHighlight(highlightData);
                    return;
                }
                
                console.log('准备通过WebChannel发送高亮数据');
                new QWebChannel(qt.webChannelTransport, function(channel) {
                    console.log('WebChannel已创建，可用对象:', Object.keys(channel.objects));
                    if (channel.objects.highlightBridge) {
                        console.log('找到highlightBridge对象，发送高亮数据');
                        try {
                        channel.objects.highlightBridge.saveHighlight(JSON.stringify(highlightData));
                            console.log('高亮数据已发送到Python');
                            window.AiSparkHub.webChannelAvailable = true; // 标记通信正常
                        } catch(callError) {
                            console.error('调用highlightBridge.saveHighlight失败:', callError);
                            window.AiSparkHub.webChannelAvailable = false;
                            window.AiSparkHub.fallbackHighlight(highlightData);
                        }
                    } else {
                        console.error('无法找到highlightBridge对象，事件无法处理');
                        // 标记WebChannel不可用
                        window.AiSparkHub.webChannelAvailable = false;
                        // 尝试使用备用方式
                        if (window.AiSparkHub && window.AiSparkHub.fallbackHighlight) {
                            console.log('尝试使用备用方式发送高亮数据');
                            window.AiSparkHub.fallbackHighlight(highlightData);
                        }
                    }
                });
            } catch(e) {
                console.error('处理高亮保存事件失败:', e);
                // 任何失败都尝试用备用方案
                if (window.AiSparkHub && window.AiSparkHub.fallbackHighlight) {
                    window.AiSparkHub.fallbackHighlight(highlightData);
                }
            }
        });
        
        document.addEventListener('aiHighlightApplied', function(event) {
            try {
                const data = JSON.parse(event.detail);
                new QWebChannel(qt.webChannelTransport, function(channel) {
                    if (channel.objects.highlightBridge) {
                        channel.objects.highlightBridge.updateHighlightApplied(data.id);
                    } else {
                        console.error('无法找到highlightBridge对象，无法更新高亮应用时间');
                        // 标记WebChannel不可用
                        window.AiSparkHub.webChannelAvailable = false;
                    }
                });
            } catch(e) {
                console.error('处理高亮应用通知失败:', e);
                window.AiSparkHub.webChannelAvailable = false;
            }
        });
        
        // 确保fallbackHighlight函数已定义
        if (!window.AiSparkHub) {
            window.AiSparkHub = {};
        }
        if (!window.AiSparkHub.fallbackHighlight) {
            window.AiSparkHub.fallbackHighlight = function(highlightData) {
                try {
                    // 使用LocalStorage存储
                    const key = 'HIGHLIGHT_' + Date.now() + '_' + Math.random().toString(36).substring(2, 10);
                    localStorage.setItem(key, JSON.stringify(highlightData));
                    console.log('备用方式: 高亮数据已保存到LocalStorage，键名:', key);
                } catch(e) {
                    console.error('备用高亮保存失败:', e);
                }
            };
        }
        
        // 添加工具函数，测试WebChannel连接
        window.testWebChannel = function() {
            try {
                if (typeof qt === 'undefined' || typeof qt.webChannelTransport === 'undefined') {
                    console.error('无法测试WebChannel: qt或webChannelTransport未定义');
                    return {success: false, error: '缺少qt.webChannelTransport'};
                }
                
                var result = 'pending';
                new QWebChannel(qt.webChannelTransport, function(channel) {
                    var objects = Object.keys(channel.objects);
                    console.log('WebChannel测试 - 可用对象:', objects);
                    
                    if (objects.includes('highlightBridge') && objects.includes('bridge')) {
                        console.log('WebChannel测试成功: 找到所有桥接对象');
                        result = {
                            success: true, 
                            objects: objects
                        };
                    } else {
                        console.error('WebChannel测试失败: 未找到所有桥接对象');
                        result = {
                            success: false, 
                            objects: objects,
                            missing: []
                        };
                        
                        if (!objects.includes('highlightBridge')) {
                            result.missing.push('highlightBridge');
                        }
                        
                        if (!objects.includes('bridge')) {
                            result.missing.push('bridge');
                        }
                    }
                });
                
                return result;
            } catch(e) {
                console.error('测试WebChannel时出错:', e);
                return {success: false, error: e.toString()};
            }
        };
        """
        
        # 验证highlightBridge对象是否可用
        test_script = """
        (function() {
            if (typeof qt !== 'undefined' && typeof qt.webChannelTransport !== 'undefined' && typeof QWebChannel !== 'undefined') {
                new QWebChannel(qt.webChannelTransport, function(channel) {
                    console.log('验证highlightBridge: 可用对象有:', Object.keys(channel.objects));
                    if (channel.objects.highlightBridge) {
                        console.log('highlightBridge对象可用，高亮功能正常');
                        window.AiSparkHub = window.AiSparkHub || {};
                        window.AiSparkHub.webChannelAvailable = true;
                        return true;
                    } else {
                        console.error('验证失败: highlightBridge对象不存在，高亮功能可能不可用');
                        window.AiSparkHub = window.AiSparkHub || {};
                        window.AiSparkHub.webChannelAvailable = false;
                        return false;
                    }
                });
            } else {
                console.error('无法验证highlightBridge: WebChannel组件不完整');
                window.AiSparkHub = window.AiSparkHub || {};
                window.AiSparkHub.webChannelAvailable = false;
                return false;
            }
        })();
        """
        
        # 运行JavaScript代码，确保在正确的世界中执行
        try:
            self.page().runJavaScript(js_code, self.MAIN_WORLD)
            self.page().runJavaScript(test_script, self.MAIN_WORLD, self._handle_highlight_test)
            self.logger.info("已在MainWorld中注入高亮事件监听JavaScript代码")
        except (TypeError, AttributeError):
            self.page().runJavaScript(js_code)
            self.page().runJavaScript(test_script, self._handle_highlight_test)
            self.logger.info("已注入高亮事件监听JavaScript代码（默认方式）")
            
        # 设置延迟验证，确保WebChannel和桥接对象正确设置
        QTimer.singleShot(1000, self._delayed_verify_webchannel)
        
        # 手动执行测试脚本
        self.page().runJavaScript("window.testWebChannel && window.testWebChannel()", 
            self.MAIN_WORLD if hasattr(self, 'MAIN_WORLD') else None,
            lambda result: self.logger.info(f"手动WebChannel测试结果: {result}")
        )
    
    def _handle_highlight_test(self, result):
        """处理高亮测试结果"""
        if result:
            self.logger.info("WebChannel桥接对象验证成功")
        else:
            self.logger.warning("WebChannel桥接对象验证失败，可能导致通信问题")
            
    def _delayed_verify_webchannel(self):
        """延迟验证WebChannel设置是否正确，如果不正确则尝试重新设置"""
        verification_script = """
        (function() {
            if (typeof qt === 'undefined' || typeof qt.webChannelTransport === 'undefined') {
                return {success: false, error: 'qt或webChannelTransport未定义'};
            }
            
            if (typeof QWebChannel === 'undefined') {
                return {success: false, error: 'QWebChannel未定义'};
            }
            
            try {
                var channelTest = false;
                new QWebChannel(qt.webChannelTransport, function(channel) {
                    var objects = Object.keys(channel.objects);
                    if (objects.includes('highlightBridge') && objects.includes('bridge')) {
                        channelTest = {success: true, objects: objects};
                    } else {
                        channelTest = {success: false, objects: objects, error: 'bridge对象不存在'};
                    }
                });
                return channelTest || {success: false, error: '测试结果未返回'};
            } catch(e) {
                return {success: false, error: e.toString()};
            }
        })();
        """
        
        try:
            self.page().runJavaScript(verification_script, self.MAIN_WORLD, self._handle_delayed_verification)
        except (TypeError, AttributeError):
            self.page().runJavaScript(verification_script, self._handle_delayed_verification)
            
    def _handle_delayed_verification(self, result):
        """处理延迟验证结果，如果验证失败则重新设置WebChannel"""
        if not result or not result.get('success', False):
            self.logger.warning(f"WebChannel延迟验证失败: {result}")
            # 强制重置WebChannel
            if self.channel:
                self.page().setWebChannel(None)
                self.channel = None
                
            # 重新创建桥接对象
            self.logger.info("重新创建桥接对象并重置WebChannel")
            self.highlight_bridge = self._create_highlight_bridge()
            self.log_bridge = self._create_log_bridge()
            
            # 重新设置WebChannel
            self.logger.info("尝试重新设置WebChannel...")
            self._setup_webchannel()
            
            # 再次测试，但使用二次验证函数避免无限循环
            QTimer.singleShot(1000, self._final_webchannel_verification)
        else:
            self.logger.info(f"WebChannel延迟验证成功，可用对象: {result.get('objects', [])}")
            
    def _final_webchannel_verification(self):
        """最终WebChannel验证，不会再次触发重置流程"""
        test_script = """
        (function() {
            try {
                if (typeof qt === 'undefined' || typeof qt.webChannelTransport === 'undefined') {
                    return {success: false, error: 'qt.webChannelTransport未定义'};
                }
                
                var result = {};
                new QWebChannel(qt.webChannelTransport, function(channel) {
                    var objects = Object.keys(channel.objects);
                    console.log('最终验证 - WebChannel对象列表:', objects);
                    result = {
                        success: objects.length > 0,
                        objects: objects,
                        has_highlight_bridge: objects.includes('highlightBridge'),
                        has_bridge: objects.includes('bridge')
                    };
                });
                return result;
            } catch(e) {
                return {success: false, error: e.toString()};
            }
        })();
        """
        
        try:
            self.page().runJavaScript(test_script, self.MAIN_WORLD, 
                lambda result: self.logger.info(f"最终WebChannel验证结果: {result}")
            )
        except Exception:
            self.page().runJavaScript(test_script, 
                lambda result: self.logger.info(f"最终WebChannel验证结果: {result}")
            )
    
    def save_highlight_from_js(self, highlight_json):
        """从JavaScript接收高亮数据并保存到数据库
        
        Args:
            highlight_json (str): JSON格式的高亮数据
        """
        try:
            self.logger.info(f"接收到高亮数据: {highlight_json[:100]}...")  # 记录接收到的原始数据(限制长度)
            
            data = json.loads(highlight_json)
            
            # 获取URL
            url = data.get('url')
            if not url:
                # 如果未提供URL，使用当前页面URL
                url = self.url().toString()
                self.logger.debug(f"未提供URL，使用当前页面URL: {url}")
            
            # 记录关键数据
            self.logger.info(f"准备保存高亮数据: URL={url}, 文本长度={len(data.get('text_content', ''))}, 类型={data.get('highlight_type', '未知')}")
            
            # 保存到数据库
            highlight_id = self.db_manager.save_highlight(
                url=url,
                text_content=data.get('text_content', ''),
                xpath=data.get('xpath', ''),
                offset_start=data.get('offset_start', 0),
                offset_end=data.get('offset_end', 0),
                highlight_type=data.get('highlight_type', 'yellow'),
                bg_color=data.get('bg_color', ''),
                border=data.get('border', ''),
                note=data.get('note', '')
            )
            
            if highlight_id:
                self.logger.info(f"成功保存高亮数据，ID: {highlight_id}")
            else:
                self.logger.error(f"保存高亮数据失败，返回的ID为空或无效")
            
        except Exception as e:
            self.logger.error(f"处理高亮数据时出错: {str(e)}")
            import traceback
            self.logger.error(f"错误详情: {traceback.format_exc()}")
    
    def update_highlight_applied_time(self, highlight_id):
        """更新高亮数据的应用时间
        
        Args:
            highlight_id (int): 高亮记录ID
        """
        try:
            success = self.db_manager.update_highlight_applied_time(highlight_id)
            if success:
                self.logger.debug(f"已更新高亮应用时间，ID: {highlight_id}")
            else:
                self.logger.warning(f"更新高亮应用时间失败，ID: {highlight_id}")
        except Exception as e:
            self.logger.error(f"更新高亮应用时间时出错: {str(e)}")
    
    def load_highlights_for_current_page(self):
        """加载当前页面的高亮数据并应用"""
        try:
            current_url = self.url().toString()
            self.logger.debug(f"正在加载页面高亮数据: {current_url}")
            
            # 获取当前URL的高亮数据
            highlights = self.db_manager.get_highlights_for_url(current_url)
            
            if not highlights:
                self.logger.debug(f"未找到页面高亮数据: {current_url}")
                return
                
            self.logger.info(f"找到{len(highlights)}条高亮数据")
            
            # 首先检查页面是否已加载完成，然后再应用高亮
            check_content_script = """
            (function() {
                // 检查页面主要内容是否已加载
                // 根据不同AI平台调整选择器
                var contentSelectors = [
                    '.chat-messages', // 通用聊天消息容器
                    '.chat-content',  // 通用聊天内容
                    '.chat-container',// 通用聊天容器
                    '.message-content',// 消息内容
                    'main',          // 主内容区
                    '.chat-main',    // 聊天主区域
                    '#chat-container',// ID选择器
                    '.conversation-content',// 会话内容
                    'article'        // 文章元素
                ];
                
                var contentFound = false;
                for (var i = 0; i < contentSelectors.length; i++) {
                    var elements = document.querySelectorAll(contentSelectors[i]);
                    if (elements.length > 0) {
                        // 检查至少一个元素有内容
                        for (var j = 0; j < elements.length; j++) {
                            if (elements[j].textContent.trim().length > 50) {
                                contentFound = true;
                                console.log('找到有内容的元素:', contentSelectors[i]);
                                break;
                            }
                        }
                        if (contentFound) break;
                    }
                }
                
                return {
                    contentLoaded: contentFound,
                    pageHeight: document.body.scrollHeight,
                    textLength: document.body.textContent.length
                };
            })();
            """
            
            # 尝试定期检查内容是否加载
            def check_and_apply():
                self.page().runJavaScript(check_content_script, lambda result: self._apply_highlights_if_ready(result, highlights))
            
            # 设置多个检查点，增加成功率
            QTimer.singleShot(1500, check_and_apply)  # 1.5秒后首次检查
            QTimer.singleShot(3000, check_and_apply)  # 3秒后再次检查
            QTimer.singleShot(5000, check_and_apply)  # 5秒后最终检查
            
        except Exception as e:
            self.logger.error(f"加载高亮数据时出错: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def _apply_highlights_if_ready(self, content_status, highlights):
        """根据内容加载状态决定是否应用高亮"""
        try:
            if not content_status:
                self.logger.warning("内容状态检查返回空结果")
                return
                
            content_loaded = content_status.get('contentLoaded', False)
            page_height = content_status.get('pageHeight', 0)
            text_length = content_status.get('textLength', 0)
            
            self.logger.debug(f"内容加载状态: 找到内容={content_loaded}, 页面高度={page_height}, 文本长度={text_length}")
            
            # 如果内容看起来已加载或页面高度/文本长度足够，则应用高亮
            if content_loaded or page_height > 1000 or text_length > 1000:
                self.logger.info("页面内容已加载，开始应用高亮")
                
                # 将高亮数据传递给前端JS处理
                js_code = f"if (typeof applyStoredHighlights === 'function') {{ applyStoredHighlights({json.dumps(highlights)}); }} else {{ console.warn('applyStoredHighlights函数不可用'); }}"
                self.page().runJavaScript(js_code)
            else:
                self.logger.debug("页面内容尚未完全加载，延迟应用高亮")
        except Exception as e:
            self.logger.error(f"应用高亮时出错: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
    
    def inject_script(self):
        """注入提示词注入脚本"""
        try:
            # 读取脚本文件
            script_file = QFile(INJECTOR_SCRIPT_PATH)
            
            if script_file.open(QIODevice.ReadOnly | QIODevice.Text):
                script_content = script_file.readAll().data().decode('utf-8')
                script_file.close()
                
                # 添加备用通信功能
                fallback_script = """
                // 添加备用高亮功能
                if (typeof saveHighlightToPython === 'function') {
                    const originalSaveHighlight = saveHighlightToPython;
                    saveHighlightToPython = function(highlightData) {
                        try {
                            // 先尝试正常方式
                            originalSaveHighlight(highlightData);
                            
                            // 同时使用备用方式，作为冗余
                            if (window.AiSparkHub && window.AiSparkHub.fallbackHighlight) {
                                window.AiSparkHub.fallbackHighlight(highlightData);
                            }
                        } catch(e) {
                            console.error('高亮保存失败，使用备用方式:', e);
                            // 如果正常方式失败，确保使用备用方式
                            if (window.AiSparkHub && window.AiSparkHub.fallbackHighlight) {
                                window.AiSparkHub.fallbackHighlight(highlightData);
                            }
                        }
                    };
                    console.log('已设置备用高亮保存功能');
                }
                """
                
                # 组合脚本
                combined_script = script_content + "\n" + fallback_script
                
                # 注入脚本 - 移除回调
                self.page().runJavaScript(combined_script)
                self.logger.debug(f"已注入提示词脚本（包含备用通信功能）")
            else:
                self.logger.error(f"无法打开脚本文件: {INJECTOR_SCRIPT_PATH}")
        except Exception as e:
            self.logger.exception(f"注入脚本时出错")
    
    def fill_prompt(self, prompt_text):
        """填充提示词并提交
        
        Args:
            prompt_text (str): 提示词文本
        """
        # 确保特殊字符的正确转义 (单引号、换行符、回车符和反斜杠)
        escaped_text = prompt_text.replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n').replace('\r', '\\r')
            
        # 调用注入方法 - 使用预先加载的脚本函数
        js_code = f"window.AiSparkHub.injectPrompt('{escaped_text}')"
        self.page().runJavaScript(js_code, self._handle_injection_result)
    
    def _handle_check_result(self, result):
        """处理脚本检查结果"""
        self.logger.debug(f"脚本检查结果: {result}")
    
    def _handle_injection_result(self, result):
        """处理注入结果"""
        self.logger.debug(f"提示词注入结果: {result}")
    
    def get_current_url(self, callback):
        """获取当前页面URL
        
        Args:
            callback: 回调函数，接收URL字符串
        """
        self.page().runJavaScript("window.AiSparkHub.getCurrentPageUrl()", callback)
    
    def get_ai_response(self, callback):
        """获取AI回复内容
        
        Args:
            callback: 回调函数，接收回复内容字符串
        """
        self.page().runJavaScript("window.AiSparkHub.getLatestAIResponse()", callback)
    
    def get_prompt_response(self, callback):
        """获取提示词响应信息（URL和回复内容）
        
        Args:
            callback: 回调函数，接收包含url和reply的对象
        """
        self.page().runJavaScript("window.AiSparkHub.getPromptResponse()", callback)

    def _install_js_log_handler(self):
        """安装JavaScript日志处理器，接收前端发送的日志"""
        js_code = """
        document.addEventListener('aiSendLogToPython', function(event) {
            try {
                const logData = JSON.parse(event.detail);
                // 直接调用QtWebEngine桥接的函数，而不是pywebview
                new QWebChannel(qt.webChannelTransport, function(channel) {
                    if (channel.objects.bridge) {
                    channel.objects.bridge.receiveJsLog(JSON.stringify(logData));
                    } else {
                        console.error('无法找到bridge对象，日志可能无法发送到后端');
                    }
                });
            } catch(e) {
                console.error('发送日志到Python时出错:', e);
            }
        });
        
        // 添加备用通信方式 - 通过LocalStorage
        window.AiSparkHub = window.AiSparkHub || {};
        window.AiSparkHub.fallbackHighlight = function(highlightData) {
            try {
                console.log('使用备用方式(LocalStorage)发送高亮数据');
                // 生成唯一key并存入LocalStorage
                const key = 'HIGHLIGHT_' + Date.now() + '_' + Math.random().toString(36).substring(2, 10);
                localStorage.setItem(key, JSON.stringify(highlightData));
                console.log('高亮数据已保存到LocalStorage，键名:', key);
                return true;
            } catch(e) {
                console.error('备用高亮方式(LocalStorage)失败:', e);
                // 尝试其他可能的备用机制
                try {
                    // 特殊格式化，前缀标识这是一个高亮数据
                    const encodedData = 'HIGHLIGHT:' + JSON.stringify(highlightData);
                    
                    // 尝试写入剪贴板 (作为最后的备用)
                    if (navigator.clipboard && navigator.clipboard.writeText) {
                        navigator.clipboard.writeText(encodedData)
                            .then(() => console.log('高亮数据已写入剪贴板(备用方案2)'))
                            .catch(err => console.error('剪贴板写入失败:', err));
                    } else {
                        console.error('所有备用方案均失败');
                    }
                } catch(clipboardError) {
                    console.error('所有备用通信方式均失败');
                }
                return false;
            }
        };

        // 添加WebChannel状态检测功能
        window.AiSparkHub.checkWebChannel = function() {
            try {
                if (typeof qt === 'undefined' || typeof qt.webChannelTransport === 'undefined') {
                    console.error('WebChannel不可用: qt或webChannelTransport未定义');
                    window.AiSparkHub.webChannelAvailable = false;
                    return false;
                }
                
                if (typeof QWebChannel === 'undefined') {
                    console.error('WebChannel不可用: QWebChannel未定义');
                    window.AiSparkHub.webChannelAvailable = false;
                    return false;
                }
                
                new QWebChannel(qt.webChannelTransport, function(channel) {
                    if (!channel.objects.highlightBridge) {
                        console.error('WebChannel可用但highlightBridge对象不存在');
                        window.AiSparkHub.webChannelAvailable = false;
                    } else {
                        console.log('WebChannel状态正常，highlightBridge对象可用');
                        window.AiSparkHub.webChannelAvailable = true;
                    }
                });
            } catch(e) {
                console.error('检查WebChannel状态失败:', e);
                window.AiSparkHub.webChannelAvailable = false;
                return false;
            }
        };
        
        // 增强saveHighlightToPython函数，添加自动故障切换能力
        window.saveHighlightToPython = function(highlightData) {
            // 先执行WebChannel状态检查
            window.AiSparkHub.checkWebChannel();
            
            try {
                // 如果WebChannel可用，正常发送
                if (window.AiSparkHub.webChannelAvailable !== false) {
                    const event = new CustomEvent('aiSaveHighlightToPython', {
                        detail: JSON.stringify(highlightData)
                    });
                    document.dispatchEvent(event);
                    console.log('通过aiSaveHighlightToPython事件发送高亮数据');
                    return true;
                } else {
                    // WebChannel不可用，直接使用备用方式
                    console.warn('检测到WebChannel不可用，直接使用备用方式');
                    window.AiSparkHub.fallbackHighlight(highlightData);
                    return true;
                }
            } catch(e) {
                console.error('保存高亮失败，使用备用方式:', e);
                window.AiSparkHub.fallbackHighlight(highlightData);
                return false;
            }
        };

        // 全局测试函数
        window.testHighlightBridge = function() {
            try {
                console.log('测试highlightBridge...');
                if (typeof qt === 'undefined' || typeof qt.webChannelTransport === 'undefined') {
                    console.error('qt.webChannelTransport不可用，无法测试');
                    return false;
                }
                
                new QWebChannel(qt.webChannelTransport, function(channel) {
                    console.log('WebChannel对象已获取，可用对象:', Object.keys(channel.objects));
                    if (channel.objects.highlightBridge) {
                        console.log('找到highlightBridge对象，发送测试数据');
                        const testData = {
                            text_content: "测试高亮",
                            url: window.location.href,
                            timestamp: new Date().toISOString(),
                            test: true
                        };
                        channel.objects.highlightBridge.saveHighlight(JSON.stringify(testData));
                        console.log('测试数据已通过highlightBridge发送');
                        return true;
                    } else {
                        console.error('未找到highlightBridge对象');
                        return false;
                    }
                });
            } catch(e) {
                console.error('测试highlightBridge失败:', e);
                return false;
            }
        };
        """
        
        # 运行JavaScript代码，确保在正确的世界中执行
        try:
            self.page().runJavaScript(js_code, self.MAIN_WORLD)
            self.logger.info("已在MainWorld中注入日志处理器和辅助函数")
        except (TypeError, AttributeError):
            self.page().runJavaScript(js_code)
            self.logger.info("已注入日志处理器和辅助函数（默认方式）")
        
        # 初始检查WebChannel状态
        try:
            self.page().runJavaScript("window.AiSparkHub.checkWebChannel()", self.MAIN_WORLD)
        except (TypeError, AttributeError):
            self.page().runJavaScript("window.AiSparkHub.checkWebChannel()")
        
        # 启动备用通信监控器
        self._setup_storage_monitor()
    
    def _setup_storage_monitor(self):
        """设置LocalStorage监控，作为WebChannel的备用通信方式"""
        self.logger.info("启动LocalStorage监控作为备用通信方式")
        
        # 创建定时器，每300毫秒检查一次LocalStorage
        self.storage_timer = QTimer(self)
        self.storage_timer.timeout.connect(self._check_local_storage)
        self.storage_timer.start(300)  # 300毫秒更频繁检查
        
        # 保留剪贴板监控作为第二备用方案
        self.clipboard_timer = QTimer(self)
        self.clipboard_timer.timeout.connect(self._check_clipboard)
        self.clipboard_timer.start(1000)  # 毫秒
        
        # 缓存上一次剪贴板内容，避免重复处理
        self.last_clipboard_text = ""
    
    def _check_local_storage(self):
        """检查LocalStorage是否有高亮数据"""
        js_code = """
        (function() {
            try {
                const keys = Object.keys(localStorage);
                const highlightKeys = keys.filter(k => k.startsWith('HIGHLIGHT_'));
                
                if (highlightKeys.length === 0) {
                    return null;
                }
                
                let results = [];
                
                for (const key of highlightKeys) {
                    try {
                        const data = localStorage.getItem(key);
                        results.push({key: key, data: data});
                        // 读取后删除
                        localStorage.removeItem(key);
                    } catch(e) {
                        console.error('读取LocalStorage数据失败:', e);
                    }
                }
                
                return results.length > 0 ? results : null;
            } catch(e) {
                console.error('检查LocalStorage时出错:', e);
                return null;
            }
        })();
        """
        try:
            self.page().runJavaScript(js_code, self.MAIN_WORLD, self._handle_local_storage_data)
        except (TypeError, AttributeError):
            self.page().runJavaScript(js_code, self._handle_local_storage_data)
    
    def _handle_local_storage_data(self, results):
        """处理从LocalStorage获取的高亮数据"""
        if not results:
            return
        
        self.logger.info(f"从LocalStorage发现{len(results)}条高亮数据")
        
        for item in results:
            try:
                data = item.get('data', '{}')
                key = item.get('key', 'unknown')
                self.logger.info(f"处理LocalStorage中的高亮数据: {key}")
                self.save_highlight_from_js(data)
            except Exception as e:
                self.logger.error(f"处理LocalStorage高亮数据出错: {str(e)}")
    
    def _check_clipboard(self):
        """检查剪贴板是否有高亮数据"""
        try:
            clipboard = QApplication.clipboard()
            text = clipboard.text()
            
            # 如果内容相同或为空，忽略
            if not text or text == self.last_clipboard_text:
                return
                
            self.last_clipboard_text = text
            
            # 检查是否是我们的特殊格式
            if text.startswith("HIGHLIGHT:"):
                self.logger.info("检测到剪贴板中的高亮数据")
                # 提取JSON数据
                json_data = text[len("HIGHLIGHT:"):]
                
                # 处理高亮数据
                self.save_highlight_from_js(json_data)
                
                # 清空剪贴板，避免重复处理
                clipboard.clear()
        except Exception as e:
            self.logger.error(f"检查剪贴板出错: {str(e)}")
            
    def receive_js_log(self, log_data):
        """接收并处理来自JavaScript的日志"""
        try:
            # 如果是字符串，尝试解析JSON
            if isinstance(log_data, str):
                log_data = json.loads(log_data)
            
            # 提取日志信息
            level = log_data.get('level', 'info').lower()
            message = log_data.get('message', '')
            timestamp = log_data.get('timestamp', '')
            data = log_data.get('data')
            
            # 格式化日志消息
            full_message = f"[JS-{timestamp}] {message}"
            if data:
                if isinstance(data, dict):
                    data_str = json.dumps(data, ensure_ascii=False)
                else:
                    data_str = str(data)
                full_message += f" - {data_str}"
            
            # 根据级别选择合适的日志方法
            if level == 'error':
                self.logger.error(full_message)
            elif level == 'warning':
                self.logger.warning(full_message)
            elif level == 'debug':
                self.logger.debug(full_message)
            else:
                self.logger.info(full_message)
                
        except Exception as e:
            self.logger.error(f"处理JS日志时出错: {e}")

    def inject_rangy_scripts(self):
        """注入Rangy高亮相关脚本，从本地文件加载"""
        self.logger.info("正在注入Rangy高亮脚本...")

        # 获取项目根目录
        import os
        # 获取当前文件的绝对路径
        current_file = os.path.abspath(__file__)
        # 获取项目根目录
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
        
        # 按依赖顺序定义脚本文件路径 - 使用绝对路径
        rangy_scripts = [
            os.path.join(base_dir, "app", "static", "js", "rangy-core.min.js"),
            os.path.join(base_dir, "app", "static", "js", "rangy-classapplier.min.js"), 
            os.path.join(base_dir, "app", "static", "js", "rangy-highlighter.min.js")
        ]
        
        try:
            # 依次加载并注入每个脚本
            for script_path in rangy_scripts:
                script_name = os.path.basename(script_path)
                self.logger.info(f"尝试加载Rangy脚本: {script_path}")
                
                script_file = QFile(script_path)
                
                if not script_file.exists():
                    self.logger.error(f"Rangy脚本文件不存在: {script_path}")
                    continue
                    
                if script_file.open(QIODevice.ReadOnly | QIODevice.Text):
                    script_content = script_file.readAll().data().decode('utf-8')
                    script_file.close()
                    
                    # 注入脚本，无需回调
                    self.page().runJavaScript(script_content)
                    self.logger.info(f"已注入Rangy脚本: {script_name}")
                else:
                    self.logger.error(f"无法打开Rangy脚本文件: {script_path}")
            
            # 所有脚本注入完成后验证
            verification_script = """
            (function() {
                var status = {
                    rangy_exists: typeof rangy !== 'undefined',
                    version: typeof rangy !== 'undefined' ? rangy.version : null,
                    highlighter_available: typeof rangy !== 'undefined' && 
                                          typeof rangy.createHighlighter === 'function'
                };
                console.log('Rangy状态检查:', JSON.stringify(status));
                return status;
            })();
            """
            
            self.page().runJavaScript(verification_script, self._handle_rangy_verification)
                
        except Exception as e:
            self.logger.error(f"注入Rangy脚本时出错: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
    
    def _handle_rangy_verification(self, result):
        """处理Rangy脚本注入验证结果"""
        if result and result.get('rangy_exists'):
            self.logger.info(f"Rangy脚本注入成功，版本: {result.get('version')}")
        else:
            self.logger.error("Rangy脚本注入失败，高亮功能可能不可用")

class AIView(QWidget):
    """AI对话页面，管理多个AI网页视图"""
    
    def __init__(self):
        super().__init__()
        
        # 初始化日志器
        self.logger = logging.getLogger("AiSparkHub.AIView")
        
        # 将 ThemeManager 初始化移到开头
        self.theme_manager = None
        app = QApplication.instance()
        if hasattr(app, 'theme_manager') and isinstance(app.theme_manager, ThemeManager):
            self.theme_manager = app.theme_manager
            self.theme_manager.theme_changed.connect(self._update_all_button_icons)
            self.logger.debug("已连接主题管理器")
        else:
            self.logger.warning("无法获取ThemeManager实例")
            
        # 获取设置管理器
        self.settings_manager = SettingsManager()
        
        # 创建布局
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # 创建分割器，用于调整各AI视图的宽度比例
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.layout.addWidget(self.splitter)
        
        # 存储AI网页视图
        self.ai_web_views = {}
        
        # 加载用户配置的AI平台
        self.load_ai_platforms()
    
    def load_ai_platforms(self):
        """根据用户设置加载AI平台"""
        # 获取用户启用的AI平台
        enabled_platforms = self.settings_manager.get_enabled_ai_platforms()
        
        # 清空现有视图
        for i in range(self.splitter.count()):
            widget = self.splitter.widget(0)
            widget.setParent(None)
        
        self.ai_web_views.clear()
        
        # 加载新视图
        for platform in enabled_platforms:
            self.add_ai_web_view_from_config(platform)
    
    def add_ai_web_view_from_config(self, ai_config):
        """从配置添加AI网页视图
        
        Args:
            ai_config (dict): AI平台配置
        
        Returns:
            AIWebView: 创建的AI网页视图
        """
        # 创建容器和标题
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)  # 设置布局间距为0，消除标题栏与网页内容之间的空白
        
        # 创建标题栏
        title_widget = QWidget()
        title_widget.setMaximumHeight(30)
        title_widget.setObjectName("aiTitleBar")
        title_layout = QHBoxLayout(title_widget)
        title_layout.setContentsMargins(8, 2, 8, 2)
        
        # 创建AI选择下拉框
        ai_selector = QComboBox()
        ai_selector.setObjectName("aiSelector")
        ai_selector.setFixedHeight(24)
        
        # 获取所有支持的AI平台
        platforms = list(SUPPORTED_AI_PLATFORMS.items())
        
        # 为每个平台创建图标和添加到下拉菜单
        self.logger.debug(f"加载AI平台选择器: {ai_config['name']} (key: {ai_config['key']})")
        for i, (dict_key, platform_config) in enumerate(platforms):
            icon = None
            lowercase_key = platform_config["key"]
            
            # 先尝试加载本地图标文件
            icon_path = os.path.join(ICON_DIR, f"{lowercase_key}.png") # 先尝试png
            if not os.path.exists(icon_path):
                icon_path = os.path.join(ICON_DIR, f"{lowercase_key}.ico") # 再尝试ico
            
            if os.path.exists(icon_path):
                # 加载图标
                try:
                    if icon_path.endswith('.ico'):
                        icon = QIcon(icon_path)
                    else:
                        icon = QIcon(QPixmap(icon_path))
                except Exception as e:
                    self.logger.warning(f"从{icon_path}加载图标失败: {str(e)}")
                    icon = None  # 加载失败，设为None以便尝试qtawesome
            else:
                self.logger.debug(f"未找到{lowercase_key}的本地图标，尝试使用qtawesome")
            
            # 如果本地图标加载失败，尝试使用qtawesome
            if icon is None:
                try:
                    # 根据AI平台选择合适的图标
                    icon_map = {
                        "chatgpt": "fa5b.chrome",      # ChatGPT使用Chrome图标
                        "kimi": "fa5s.robot",          # Kimi使用机器人图标
                        "doubao": "fa5s.comment",      # 其他平台使用通用对话图标
                        "yuanbao": "fa5s.comment-dots",
                        "perplexity": "fa5s.search",   # Perplexity用搜索图标
                        "metaso": "fa5s.search",       # 元搜索用搜索图标
                        "grok": "fa5b.twitter",        # Grok关联Twitter/X
                        "yiyan": "fa5b.baidu",         # 文心一言用百度图标
                        "gemini": "fa5b.google",       # Gemini用Google图标
                        "tongyi": "fa5b.alipay",       # 通义用阿里图标
                        "chatglm": "fa5s.brain",       # ChatGLM用脑图标
                        "biji": "fa5s.sticky-note",    # 笔记用便签图标
                        "n": "fa5s.yin-yang",          # N用特殊图标
                        "deepseek": "fa5s.power-off"   # DeepSeek用电源图标
                    }
                    
                    # 获取该平台对应的图标名，如果没有指定则使用评论图标
                    icon_name = icon_map.get(lowercase_key, "fa5s.comment")
                    icon = qta.icon(icon_name)
                except Exception as e:
                    self.logger.warning(f"使用qtawesome图标失败({lowercase_key}): {str(e)}")
                    # 如果qtawesome也失败，使用默认图标
                    icon = qta.icon("fa5s.comment")
                    self.logger.debug(f"使用默认qtawesome图标: fa5s.comment")
            
            # 添加到下拉菜单，将平台 key (小写) 作为 userData 存储
            ai_selector.addItem(icon, platform_config["name"], userData=lowercase_key)
            
        # 手动查找目标索引
        target_key_to_find = ai_config["key"]
        found_index = -1
        for idx in range(ai_selector.count()):
            item_data = ai_selector.itemData(idx)
            # 确保比较的是同类型且值相等
            if isinstance(item_data, str) and item_data == target_key_to_find:
                found_index = idx
                break # 找到即停止
        
        # 设置当前选中的AI
        if found_index != -1:
            ai_selector.setCurrentIndex(found_index)
        else:
            self.logger.warning(f"未找到{target_key_to_find}对应的索引，默认使用第一项")
            ai_selector.setCurrentIndex(0) # 如果找不到，默认显示第一项
        
        # 连接选择变更信号
        ai_selector.currentIndexChanged.connect(lambda index, c=container, s=ai_selector: self.on_ai_changed(c, index, s))
        
        # 创建控制按钮的通用样式 - 添加 hover 和 pressed 样式
        button_style = """
            QPushButton {
                background-color: transparent;
                border: none;
                padding: 2px;
                border-radius: 3px;
                max-width: 22px;
                max-height: 22px;
            }
            QPushButton:hover {
                background-color: rgba(120, 120, 120, 0.2);
            }
            QPushButton:pressed {
                background-color: rgba(100, 100, 100, 0.3);
            }
        """
        
        # 创建控制按钮
        # 1. 向左移动按钮
        move_left_btn = QPushButton()
        move_left_btn.setIcon(qta.icon("fa5s.arrow-left"))
        move_left_btn.setToolTip("将此视图向左移动")
        move_left_btn.setStyleSheet(button_style)
        move_left_btn.setIconSize(QSize(14, 14))
        move_left_btn.clicked.connect(lambda _, c=container: self.move_view_left(c))
        
        # 2. 向右移动按钮
        move_right_btn = QPushButton()
        move_right_btn.setIcon(qta.icon("fa5s.arrow-right"))
        move_right_btn.setToolTip("将此视图向右移动")
        move_right_btn.setStyleSheet(button_style)
        move_right_btn.setIconSize(QSize(14, 14))
        move_right_btn.clicked.connect(lambda _, c=container: self.move_view_right(c))
        
        # 3. 刷新按钮
        refresh_btn = QPushButton()
        refresh_btn.setIcon(qta.icon("fa5s.sync"))
        refresh_btn.setToolTip("刷新此视图")
        refresh_btn.setStyleSheet(button_style)
        refresh_btn.setIconSize(QSize(14, 14))
        refresh_btn.clicked.connect(lambda _, c=container: self.refresh_view(c))
        
        # 4. 最大化/恢复按钮
        maximize_btn = QPushButton()
        maximize_btn.setIcon(qta.icon("fa5s.expand"))
        maximize_btn.setToolTip("最大化此视图")
        maximize_btn.setStyleSheet(button_style)
        maximize_btn.setIconSize(QSize(14, 14))
        maximize_btn.clicked.connect(lambda _, c=container, b=maximize_btn: self.toggle_maximize_view(c, b))
        
        # 5. 添加视图按钮
        add_btn = QPushButton()
        add_btn.setIcon(qta.icon("fa5s.plus"))
        add_btn.setToolTip("在右侧添加新视图")
        add_btn.setStyleSheet(button_style)
        add_btn.setIconSize(QSize(14, 14))
        add_btn.clicked.connect(lambda _, c=container: self.add_view_after(c))
        
        # 6. 关闭按钮
        close_btn = QPushButton()
        close_btn.setIcon(qta.icon("fa5s.times"))
        close_btn.setToolTip("关闭此视图")
        close_btn.setStyleSheet(button_style)
        close_btn.setIconSize(QSize(14, 14))
        close_btn.clicked.connect(lambda _, c=container: self.close_view(c))
        
        # 存储按钮引用，以便后续访问
        container.move_left_btn = move_left_btn
        container.move_right_btn = move_right_btn
        container.refresh_btn = refresh_btn
        container.maximize_btn = maximize_btn
        container.add_btn = add_btn
        container.close_btn = close_btn
        container.is_maximized = False  # 记录是否处于最大化状态
        
        # 设置按钮初始图标（带颜色）
        self._set_initial_button_icons(container)
        
        # 将下拉菜单添加到标题栏
        title_layout.addWidget(ai_selector)
        title_layout.addStretch(1)
        
        # 添加控制按钮到标题栏右侧
        title_layout.addWidget(move_left_btn)
        title_layout.addWidget(move_right_btn)
        title_layout.addWidget(refresh_btn)
        title_layout.addWidget(maximize_btn)
        title_layout.addWidget(add_btn)
        title_layout.addWidget(close_btn)
        
        # 添加标题栏到容器
        container_layout.addWidget(title_widget)
        
        # 创建AI网页视图
        web_view = AIWebView(ai_config)
        
        # 添加到容器并存储
        container_layout.addWidget(web_view)
        container.web_view = web_view  # 将web_view作为容器的属性存储
        container.ai_key = ai_config["key"]  # 存储当前加载的AI平台标识
        
        # 添加到分割器
        self.splitter.addWidget(container)
        
        # 存储网页视图 (确保key与存储时一致)
        self.ai_web_views[ai_config["key"]] = web_view
        
        # 调整分割器各部分的宽度比例
        self.adjust_splitter_sizes()
        
        # 更新导航按钮状态
        self.update_navigation_buttons()
        
        # 添加新方法：设置按钮初始图标
        self._set_initial_button_icons(container)
        
        return web_view
    
    def add_ai_web_view(self, ai_name, ai_url, input_selector=None, submit_selector=None):
        """添加AI网页视图 (兼容旧接口)
        
        Args:
            ai_name (str): AI名称
            ai_url (str): AI网页URL
            input_selector (str): 输入框选择器
            submit_selector (str): 提交按钮选择器
        """
        # 查找匹配的AI平台配置
        ai_config = None
        for key, config in SUPPORTED_AI_PLATFORMS.items():
            if config["name"] == ai_name:
                ai_config = config.copy()
                break
        
        # 如果没有找到匹配的配置，创建一个新的
        if not ai_config:
            ai_config = {
                "key": ai_name.lower(),
                "name": ai_name,
                "url": ai_url,
                "input_selector": input_selector,
                "submit_selector": submit_selector,
                "response_selector": ""
            }
        
        # 使用自定义选择器覆盖默认值
        if input_selector:
            ai_config["input_selector"] = input_selector
        if submit_selector:
            ai_config["submit_selector"] = submit_selector
        
        return self.add_ai_web_view_from_config(ai_config)
    
    def adjust_splitter_sizes(self):
        """调整分割器各部分的宽度比例"""
        count = self.splitter.count()
        if count > 0:
            width = self.width()
            sizes = [width // count] * count
            self.splitter.setSizes(sizes)
    
    def fill_prompt(self, prompt_text):
        """向所有AI网页填充提示词
        
        Args:
            prompt_text (str): 提示词文本
        """
        for web_view in self.ai_web_views.values():
            web_view.fill_prompt(prompt_text)
            
    def collect_all_responses(self, callback):
        """收集所有AI网页视图的响应信息
        
        收集每个WebView的URL和回复内容，并在完成后调用回调函数
        
        Args:
            callback: 回调函数，接收由各WebView返回的信息组成的列表
                     每项包含url和reply字段
        """
        responses = []
        pending_count = len(self.ai_web_views)
        
        if pending_count == 0:
            # 如果没有WebView，立即返回空列表
            callback([])
            return
        
        def response_collected(result, web_view_key):
            """单个响应收集完成的回调"""
            nonlocal responses, pending_count
            
            # 添加响应到列表
            if result:
                responses.append(result)
            else:
                # 如果获取失败，添加一个包含URL但没有回复的项
                web_view = self.ai_web_views[web_view_key]
                responses.append({
                    "url": web_view.url().toString(),
                    "reply": "无法获取回复内容"
                })
            
            # 减少待处理计数
            pending_count -= 1
            
            # 如果所有WebView都已处理完成，调用总回调
            if pending_count == 0:
                callback(responses)
        
        # 遍历所有WebView，获取响应
        for key, web_view in self.ai_web_views.items():
            web_view.get_prompt_response(lambda result, k=key: response_collected(result, k))
    
    def resizeEvent(self, event):
        """窗口大小变化时调整分割器各部分的宽度比例"""
        super().resizeEvent(event)
        self.adjust_splitter_sizes()
    
    def on_ai_changed(self, container, index, selector):
        """处理AI平台选择变更
        
        Args:
            container: 包含web_view的容器
            index: 选择的索引
            selector: 下拉菜单控件
        """
        # 获取选中的AI平台标识 (从 userData 获取)
        ai_key = selector.itemData(index) # userData 存储的是小写 key
        
        # 检查获取的 key 是否有效
        if not ai_key or not isinstance(ai_key, str):
             self.logger.error(f"从下拉菜单获取的AI key无效或类型错误 (index={index}, data={ai_key})")
             return
        
        self.logger.debug(f"接收到AI平台变更信号: index={index}, key='{ai_key}'")
        
        # 避免重复加载同一个平台
        if hasattr(container, 'ai_key') and container.ai_key == ai_key:
            self.logger.debug(f"AI平台未变化('{ai_key}')，无需切换")
            return
        
        # 获取AI平台配置 (使用小写 key 从 SUPPORTED_AI_PLATFORMS 查找)
        # 注意：SUPPORTED_AI_PLATFORMS 的键是大写的，值里面的 'key' 是小写的
        ai_config = None
        for dict_key, platform_config in SUPPORTED_AI_PLATFORMS.items():
            if platform_config.get("key") == ai_key:
                ai_config = platform_config
                self.logger.debug(f"找到匹配的AI平台配置: {ai_key} (原字典键: '{dict_key}')")
                break
        
        if not ai_config:
            self.logger.error(f"在SUPPORTED_AI_PLATFORMS中找不到key='{ai_key}'的配置")
            return
        
        self.logger.info(f"准备切换到AI平台: {ai_config['name']}")
        
        # 保存旧的web_view引用以便稍后删除
        old_web_view = None
        if hasattr(container, 'web_view'):
            old_web_view = container.web_view
            self.logger.debug(f"找到旧的WebView实例: {old_web_view.ai_name}")
        
        # 创建新的web_view
        web_view = AIWebView(ai_config) # 使用找到的 config 创建
        
        # 替换容器中的web_view
        layout = container.layout()
        if old_web_view:
            # 移除旧的web_view
            layout.removeWidget(old_web_view)
            self.logger.debug(f"从布局中移除旧WebView ({old_web_view.ai_name})")
            old_web_view.setParent(None) # 解除父子关系，确保能被删除
            old_web_view.deleteLater()
            self.logger.debug(f"标记旧WebView ({old_web_view.ai_name})为待删除")
            
            # 从字典中移除旧的引用 (使用旧的 key)
            old_key = container.ai_key # 获取旧的key
            if old_key in self.ai_web_views and self.ai_web_views[old_key] == old_web_view:
                del self.ai_web_views[old_key]
                self.logger.debug(f"从ai_web_views字典中移除旧引用 (key: '{old_key}')")
            else:
                self.logger.warning(f"在ai_web_views中找不到/无法移除旧引用 (key: '{old_key}')")
        else:
            self.logger.warning("容器中未找到旧WebView引用")
        
        # 添加新的web_view
        layout.addWidget(web_view)
        self.logger.debug(f"添加新WebView ({web_view.ai_name})到布局")
        
        # 更新容器的属性
        container.web_view = web_view
        container.ai_key = ai_key # 更新为新的小写 key
        self.logger.debug(f"更新容器属性为新平台 (key: '{ai_key}')")
        
        # 更新web_view字典 (使用新的小写 key)
        self.ai_web_views[ai_key] = web_view
        self.logger.debug(f"更新ai_web_views字典添加新引用 (key: '{ai_key}')")
        
        self.logger.info(f"成功切换到AI平台: {ai_config['name']}")
    
    def move_view_left(self, container):
        """将视图向左移动一个位置
        
        Args:
            container: 包含web_view的容器
        """
        index = self.splitter.indexOf(container)
        if index > 0:  # 如果不是最左侧的视图
            # 获取左侧视图
            left_widget = self.splitter.widget(index - 1)
            
            # 记住当前的大小
            sizes = self.splitter.sizes()
            left_size = sizes[index - 1]
            current_size = sizes[index]
            
            # 移除并重新插入容器
            self.splitter.insertWidget(index - 1, container)
            
            # 恢复大小
            sizes[index - 1] = current_size
            sizes[index] = left_size
            self.splitter.setSizes(sizes)
            
            # 更新导航按钮状态
            self.update_navigation_buttons()
    
    def move_view_right(self, container):
        """将视图向右移动一个位置
        
        Args:
            container: 包含web_view的容器
        """
        index = self.splitter.indexOf(container)
        if index < self.splitter.count() - 1:  # 如果不是最右侧的视图
            # 获取右侧视图
            right_widget = self.splitter.widget(index + 1)
            
            # 记住当前的大小
            sizes = self.splitter.sizes()
            right_size = sizes[index + 1]
            current_size = sizes[index]
            
            # 移除并重新插入容器
            self.splitter.insertWidget(index + 1, container)
            
            # 恢复大小
            sizes[index] = right_size
            sizes[index + 1] = current_size
            self.splitter.setSizes(sizes)
            
            # 更新导航按钮状态
            self.update_navigation_buttons()
    
    def refresh_view(self, container):
        """刷新视图
        
        Args:
            container: 包含web_view的容器
        """
        if hasattr(container, 'web_view'):
            container.web_view.reload()
    
    def toggle_maximize_view(self, container, button):
        """切换视图的最大化/恢复状态
        
        Args:
            container: 包含web_view的容器
            button: 最大化/恢复按钮
        """
        # 获取所有视图容器
        containers = []
        for i in range(self.splitter.count()):
            containers.append(self.splitter.widget(i))
        
        theme_colors = self.theme_manager.get_current_theme_colors() if self.theme_manager else {}
        icon_color = theme_colors.get('foreground', '#D8DEE9') # 获取当前主题的前景色
            
        if not container.is_maximized:
            # 最大化：隐藏其他视图，调整当前视图为全宽
            for c in containers:
                if c != container:
                    c.hide()
            # 更新按钮图标为"恢复"
            button.setIcon(qta.icon("fa5s.compress", color=icon_color))
            button.setToolTip("恢复视图大小")
            container.is_maximized = True
        else:
            # 恢复：显示所有视图，重新调整宽度
            for c in containers:
                c.show()
            # 更新按钮图标为"最大化"
            button.setIcon(qta.icon("fa5s.expand", color=icon_color))
            button.setToolTip("最大化此视图")
            container.is_maximized = False
            # 重新调整所有视图大小
            self.adjust_splitter_sizes()
    
    def add_view_after(self, container):
        """在当前视图右侧添加新视图
        
        Args:
            container: 包含web_view的容器
        """
        index = self.splitter.indexOf(container)
        
        # 获取当前支持的AI平台列表
        enabled_platforms = self.settings_manager.get_enabled_ai_platforms()
        
        # 如果有可用的AI平台，则添加第一个
        if enabled_platforms:
            # 创建新视图
            new_view = self.add_ai_web_view_from_config(enabled_platforms[0])
            
            # 将新视图移动到当前视图右侧
            new_container = None
            for i in range(self.splitter.count()):
                widget = self.splitter.widget(i)
                if hasattr(widget, 'web_view') and widget.web_view == new_view:
                    new_container = widget
                    break
            
            if new_container:
                # 移动到当前视图右侧
                current_index = self.splitter.indexOf(new_container)
                if current_index != index + 1:
                    # 记住当前的大小
                    sizes = self.splitter.sizes()
                    
                    # 移除并重新插入
                    self.splitter.insertWidget(index + 1, new_container)
                    
                    # 重新调整大小
                    self.adjust_splitter_sizes()
                    
                    # 更新导航按钮状态
                    self.update_navigation_buttons()
    
    def close_view(self, container):
        """关闭视图
        
        Args:
            container: 包含web_view的容器
        """
        # 获取容器索引
        index = self.splitter.indexOf(container)
        if index == -1:
            return
        
        # 检查视图数量，保证至少保留一个视图
        if self.splitter.count() <= 1:
            return
        
        # 获取AI key，从字典中移除
        if hasattr(container, 'ai_key'):
            ai_key = container.ai_key
            if ai_key in self.ai_web_views:
                del self.ai_web_views[ai_key]
        
        # 从分割器中移除
        container.setParent(None)
        
        # 如果当前是最大化状态，恢复其他视图
        if hasattr(container, 'is_maximized') and container.is_maximized:
            for i in range(self.splitter.count()):
                self.splitter.widget(i).show()
        
        # 调整剩余视图的大小
        self.adjust_splitter_sizes()
        
        # 更新导航按钮状态
        self.update_navigation_buttons()
        
        # 标记为稍后删除
        container.deleteLater()
    
    def update_navigation_buttons(self):
        """更新所有容器的导航按钮状态（左右移动按钮）"""
        count = self.splitter.count()
        
        # 遍历所有容器
        for i in range(count):
            container = self.splitter.widget(i)
            
            # 对于最左侧的容器，隐藏向左按钮
            if hasattr(container, 'move_left_btn'):
                container.move_left_btn.setVisible(i > 0)
            
            # 对于最右侧的容器，隐藏向右按钮
            if hasattr(container, 'move_right_btn'):
                container.move_right_btn.setVisible(i < count - 1)
    
    def open_multiple_urls(self, urls):
        """打开多个URL到不同的AI网页视图
        
        Args:
            urls (list): 要打开的URL列表
        """
        if not urls:
            self.logger.warning("没有URL可以打开")
            return
            
        self.logger.info(f"打开URLs请求: {urls}")
        
        # 清空现有视图
        for i in range(self.splitter.count()):
            widget = self.splitter.widget(0)
            widget.setParent(None)
        
        self.ai_web_views.clear()
        
        # 为每个URL创建一个新的网页视图
        for url in urls:
            # 从URL分析AI平台
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            if domain.startswith('www.'):
                domain = domain[4:]
                
            # URL到平台标识的映射
            url_to_platform = {
                'chat.openai.com': 'chatgpt',
                'chatgpt.com': 'chatgpt',
                'kimi.moonshot.cn': 'kimi',
                'doubao.com': 'doubao',
                'perplexity.ai': 'perplexity',
                'n.cn': 'n',
                'metaso.cn': 'metaso',
                'chatglm.cn': 'chatglm',
                'yuanbao.tencent.com': 'yuanbao',
                'biji.com': 'biji',
                'x.com': 'grok',
                'grok.com': 'grok',
                'yiyan.baidu.com': 'yiyan',
                'tongyi.aliyun.com': 'tongyi',
                'gemini.google.com': 'gemini',
                'chat.deepseek.com': 'deepseek',
                'claude.ai': 'claude',
                'anthropic.com': 'claude',
                'bing.com': 'bing'
            }
            
            # 根据域名获取平台标识
            ai_key = url_to_platform.get(domain)
            
            # 如果找不到精确匹配，尝试部分匹配
            if not ai_key:
                for host, key in url_to_platform.items():
                    if host in domain:
                        ai_key = key
                        break
            
            # 如果无法识别平台，使用通用配置
            if not ai_key:
                ai_key = "unknown"
                ai_name = "未知平台"
                self.logger.warning(f"无法识别URL域名: {domain}")
            else:
                # 查找匹配的AI平台配置
                ai_name = None
                for key, config in SUPPORTED_AI_PLATFORMS.items():
                    if config["key"] == ai_key:
                        ai_name = config["name"]
                        break
                
                if not ai_name:
                    ai_name = ai_key.capitalize()  # 如果找不到名称，使用key的首字母大写形式
                    self.logger.debug(f"未找到{ai_key}的平台名称，使用首字母大写形式")
            
            # 创建配置
            ai_config = {
                "key": ai_key,
                "name": ai_name,
                "url": url,
                "input_selector": "",  # 不需要输入选择器，只是查看
                "submit_selector": "",
                "response_selector": ""
            }
            
            self.logger.debug(f"为URL创建AI视图: {url} -> {ai_name}")
            # 添加网页视图
            self.add_ai_web_view_from_config(ai_config)
        
        # 调整视图大小
        self.adjust_splitter_sizes()

    # 新增方法：设置容器按钮的初始图标和颜色
    def _set_initial_button_icons(self, container):
        if not self.theme_manager:
            self.logger.warning("警告: ThemeManager 未初始化，无法设置按钮图标颜色")
            # 可以设置一个默认颜色或无颜色
            icon_color = '#D8DEE9' # 默认深色前景色
        else:
            theme_colors = self.theme_manager.get_current_theme_colors()
            # 使用前景色作为图标颜色
            icon_color = theme_colors.get('foreground', '#D8DEE9') 
            
        # 检查按钮是否存在并设置图标
        if hasattr(container, 'move_left_btn'):
            container.move_left_btn.setIcon(qta.icon("fa5s.arrow-left", color=icon_color))
        if hasattr(container, 'move_right_btn'):
            container.move_right_btn.setIcon(qta.icon("fa5s.arrow-right", color=icon_color))
        if hasattr(container, 'refresh_btn'):
            container.refresh_btn.setIcon(qta.icon("fa5s.sync", color=icon_color))
        if hasattr(container, 'maximize_btn'):
            # 根据当前状态设置正确的图标
            icon_name = "fa5s.compress" if container.is_maximized else "fa5s.expand"
            container.maximize_btn.setIcon(qta.icon(icon_name, color=icon_color))
        if hasattr(container, 'add_btn'):
            container.add_btn.setIcon(qta.icon("fa5s.plus", color=icon_color))
        if hasattr(container, 'close_btn'):
            container.close_btn.setIcon(qta.icon("fa5s.times", color=icon_color))

    # 新增方法：更新所有容器按钮的图标颜色以响应主题变化
    def _update_all_button_icons(self):
        if not self.theme_manager:
            self.logger.warning("警告: ThemeManager 未初始化，无法更新按钮图标颜色")
            return
        
        self.logger.debug("AIView: 接收到主题变化信号，正在更新按钮图标...")
        theme_colors = self.theme_manager.get_current_theme_colors()
        icon_color = theme_colors.get('foreground', '#D8DEE9') # 获取当前主题的前景色
        self.logger.debug(f"AIView: 当前主题图标颜色: {icon_color}")

        # 遍历分割器中的所有容器
        for i in range(self.splitter.count()):
            container = self.splitter.widget(i)
            if container is None: # 添加检查以防万一
                continue
                
            self.logger.debug(f"AIView: 正在更新容器 {i} 的按钮图标...")
            # 检查按钮是否存在并更新图标颜色
            if hasattr(container, 'move_left_btn'):
                container.move_left_btn.setIcon(qta.icon("fa5s.arrow-left", color=icon_color))
            if hasattr(container, 'move_right_btn'):
                container.move_right_btn.setIcon(qta.icon("fa5s.arrow-right", color=icon_color))
            if hasattr(container, 'refresh_btn'):
                container.refresh_btn.setIcon(qta.icon("fa5s.sync", color=icon_color))
            if hasattr(container, 'maximize_btn'):
                icon_name = "fa5s.compress" if container.is_maximized else "fa5s.expand"
                container.maximize_btn.setIcon(qta.icon(icon_name, color=icon_color))
            if hasattr(container, 'add_btn'):
                container.add_btn.setIcon(qta.icon("fa5s.plus", color=icon_color))
            if hasattr(container, 'close_btn'):
                container.close_btn.setIcon(qta.icon("fa5s.times", color=icon_color))
            self.logger.debug(f"AIView: 容器 {i} 图标更新完成。") 
            
    def get_visual_order_of_views(self):
        """
        获取视觉上从左到右的视图顺序，返回按视觉顺序排列的ai_key列表
        """
        visual_order = []
        
        # 确保有分割器且包含视图
        if not hasattr(self, 'splitter') or self.splitter is None:
            self.logger.warning("无法获取视觉顺序：splitter不存在")
            return list(self.ai_web_views.keys())  # 回退到字典顺序
            
        # 遍历分割器中的所有小部件（从左到右的顺序）
        for i in range(self.splitter.count()):
            container = self.splitter.widget(i)
            # 检查容器是否有ai_key属性
            if hasattr(container, 'ai_key'):
                visual_order.append(container.ai_key)
                self.logger.debug(f"找到视图 {container.ai_key} 位于位置 {i}")
            else:
                self.logger.debug(f"在位置 {i} 的容器没有ai_key属性")
                
        self.logger.info(f"视觉顺序：{visual_order}")
        return visual_order 