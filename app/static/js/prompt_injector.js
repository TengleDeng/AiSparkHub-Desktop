/**
 * 提示词注入脚本
 * 用于向各AI平台注入提示词并触发发送
 */

// 各平台的选择器配置
const PLATFORM_SELECTORS = {
    // ChatGPT
    chatgpt: {
        input: '#prompt-textarea',
        button: 'button[data-testid="send-button"]',
        responseSelector: '.markdown.prose'

    },
    // Kimi
    kimi: {
        input: '.chat-input-editor',
        button: '.send-button',
        responseSelector: '.segment-content-box'
    },
    // 豆包
    doubao: {
        input: 'textarea.semi-input-textarea',
        button: '#flow-end-msg-send',
        responseSelector: '[data-testid="message_text_content"]'
    },
    // 元宝
    yuanbao: {
        input: '.ql-editor',
        button: 'a[class*="send-btn"]',
        responseSelector: '.agent-chat__conv--ai__speech_show'
    },
    // Perplexity
    perplexity: {
        input: 'textarea.overflow-auto',
        button: 'button[aria-label="Submit"]',
        responseSelector: '[id^="markdown-content-"]'
    },
    // N
    n: {
        input: '#composition-input',
        button: '#home_chat_btn',
        responseSelector: '.chat-message-body'
    },
    // MetaSo
    metaso: {
        input: '.search-consult-textarea',
        button: '.send-arrow-button',
        responseSelector: '.message-body'
    },
    // ChatGLM
    chatglm: {
        input: 'textarea.scroll-display-none',
        button: '.enter_icon',
        responseSelector: '.chat-content'
    },
    // Grok
    grok: {
        input: 'textarea[aria-label=\"向Grok提任何问题\"]',
        button: 'button[type=\"submit\"][aria-label=\"提交\"]',
        responseSelector: '.message-bubble'
    },
    // Get笔记
    biji: {
        input: '.custom-rich-input',
        button: '.n-button',
        responseSelector: '.message-content'
    },
    // 文心一言
    yiyan: {
        input: '.yc-editor',
        button: '#sendBtn',
        responseSelector: '.chat-result-wrap'
    },
    // 通义
    tongyi: {
        input: '.ant-input',
        button: '[class*="operateBtn"]',
        responseSelector: '.msgContent'
    },
    // Gemini
    gemini: {
        input: '.text-input-field_textarea-wrapper',
        button: '.send-button',
        responseSelector: '.response-container'
    },
    // DeepSeek
    deepseek: {
        input: '#chat-input',
        button: '[role="button"][aria-disabled="false"]',
        responseSelector: '.ds-markdown'
    }
};

// URL到平台标识的映射
const URL_TO_PLATFORM = {
    'chat.openai.com': 'chatgpt',
    'chatgpt.com': 'chatgpt',
    'kimi.moonshot.cn': 'kimi',
    'www.doubao.com': 'doubao',
    'doubao.com': 'doubao',
    'www.perplexity.ai': 'perplexity',
    'perplexity.ai': 'perplexity',
    'n.cn': 'n',
    'metaso.cn': 'metaso',
    'www.metaso.cn': 'metaso',
    'chatglm.cn': 'chatglm',
    'www.chatglm.cn': 'chatglm',
    'yuanbao.tencent.com': 'yuanbao',
    'www.biji.com': 'biji',
    'biji.com': 'biji',
    'x.com': 'grok',
    'grok.com': 'grok',
    'www.grok.com': 'grok',
    'yiyan.baidu.com': 'yiyan',
    'tongyi.aliyun.com': 'tongyi',
    'gemini.google.com': 'gemini',
    'chat.deepseek.com': 'deepseek'
};

/**
 * 从URL中获取平台标识
 * @returns {string|null} 平台标识或null
 */
function getPlatformFromURL() {
    const host = window.location.hostname;
    return URL_TO_PLATFORM[host] || null;
}

/**
 * 向AI平台注入提示词并发送
 * @param {string} message 要发送的提示词
 * @returns {Promise<boolean>} 是否成功
 */
async function injectPrompt(message) {
    console.log('开始注入提示词...');
    
    // 确定平台
    const platform = getPlatformFromURL();
    if (!platform) {
        console.error('无法识别当前平台:', window.location.hostname);
        return false;
    }
    console.log('识别平台:', platform);

    // 获取平台选择器
    const selectors = PLATFORM_SELECTORS[platform];
    if (!selectors) {
        console.error('未知的平台:', platform);
        return false;
    }
    
    try {
        // 查找输入框
        const input = document.querySelector(selectors.input);
        console.log('Input selector:', selectors.input);
        if (!input) {
            console.error('未找到输入框');
            return false;
        }
        console.log('找到输入框:', input.tagName);

        // 聚焦和清空输入框
        input.focus();
        document.execCommand('selectAll', false, null);
        document.execCommand('delete', false, null);
        console.log('输入框已清空');

        // 直接注入文本
        document.execCommand('insertText', false, message);
        console.log('文本已注入');

        // 等待文本注入完成
        await new Promise(resolve => setTimeout(resolve, 500));

        // 尝试查找发送按钮
        console.log('Trying to find button with selector:', selectors.button);
        let button = document.querySelector(selectors.button);

        // 执行点击
        try {
            // 使用完整的鼠标事件序列
            ['mousedown', 'mouseup', 'click'].forEach(eventType => {
                const event = new MouseEvent(eventType, {
                    bubbles: true,
                    cancelable: true,
                    view: window
                });
                button.dispatchEvent(event);
            });
            console.log('Mouse event sequence dispatched successfully');
        } catch (error) {
            console.error('Failed to simulate click:', error);
            return false;
        }

        console.log('已点击发送按钮');
        return true;
    } catch (error) {
        console.error('执行出错:', error);
        return false;
    }
}

/**
 * 获取当前页面的完整URL
 * @returns {string} 当前页面URL
 */
function getCurrentPageUrl() {
    return window.location.href;
}

/**
 * 获取AI的最新回复内容
 * @returns {string} AI回复内容
 */
function getLatestAIResponse() {
    // 确定平台
    const platform = getPlatformFromURL();
    if (!platform) {
        console.error('无法识别当前平台:', window.location.hostname);
        return "无法识别当前平台";
    }
    
    // 获取平台选择器
    const selectors = PLATFORM_SELECTORS[platform];
    if (!selectors || !selectors.responseSelector) {
        console.error('未找到回复内容选择器:', platform);
        return "未找到回复内容选择器";
    }
    
    try {
        // 查找所有回复元素
        const responseElements = document.querySelectorAll(selectors.responseSelector);
        if (!responseElements || responseElements.length === 0) {
            console.error('未找到回复元素');
            return "未找到回复元素";
        }
        
        // 获取最后一个元素的内容（通常是最新回复）
        const lastResponse = responseElements[responseElements.length - 1];
        return lastResponse.innerText || lastResponse.textContent || "无法获取回复内容";
    } catch (error) {
        console.error('获取回复内容出错:', error);
        return "获取回复内容出错: " + error.message;
    }
}

/**
 * 获取提示词响应信息（URL和回复内容）
 * @returns {Object} 包含url和reply的对象
 */
function getPromptResponse() {
    return {
        url: getCurrentPageUrl(),
        reply: getLatestAIResponse()
    };
}

// 将函数暴露给外部调用
window.AiSparkHub = window.AiSparkHub || {};
window.AiSparkHub.injectPrompt = injectPrompt;
window.AiSparkHub.getPlatformFromURL = getPlatformFromURL;
window.AiSparkHub.getCurrentPageUrl = getCurrentPageUrl;
window.AiSparkHub.getLatestAIResponse = getLatestAIResponse;
window.AiSparkHub.getPromptResponse = getPromptResponse;

// 显示toast提示 - 将此函数移到前面，确保在其他代码引用它之前已定义
function showToast(message) {
    // 创建提示元素
    const toast = document.createElement('div');
    toast.textContent = message;
    toast.style.cssText = `
        position: fixed;
        bottom: 20px;
        left: 50%;
        transform: translateX(-50%);
        background: rgba(0, 0, 0, 0.7);
        color: white;
        padding: 8px 16px;
        border-radius: 4px;
        font-size: 14px;
        z-index: 10001;
        animation: fadeInOut 2s forwards;
    `;
    
    // 添加动画
    const toastStyle = document.createElement('style');
    toastStyle.textContent = `
        @keyframes fadeInOut {
            0% { opacity: 0; transform: translate(-50%, 20px); }
            15% { opacity: 1; transform: translate(-50%, 0); }
            85% { opacity: 1; transform: translate(-50%, 0); }
            100% { opacity: 0; transform: translate(-50%, -20px); }
        }
    `;
    document.head.appendChild(toastStyle);
    
    // 添加到文档
    document.body.appendChild(toast);
    
    // 2秒后移除
    setTimeout(() => {
        if (document.body.contains(toast)) {
            document.body.removeChild(toast);
        }
        if (document.head.contains(toastStyle)) {
            document.head.removeChild(toastStyle);
        }
    }, 2000);
}

// 将showToast函数暴露给全局作用域
window.AiSparkHub.showToast = showToast;

// 添加日志工具，将日志发送回Python
window.AiSparkHub.logToPython = function(level, message, data) {
    try {
        // 准备日志数据 - 处理循环引用问题
        const safeData = data ? safeJsonData(data) : null;
        
        const logData = {
            level: level,
            message: message,
            timestamp: new Date().toISOString(),
            data: safeData
        };
        
        // 将对象转为JSON字符串
        const logJson = JSON.stringify(logData);
        
        // 创建一个特殊的事件，Python端可以捕获
        const logEvent = new CustomEvent('aiSendLogToPython', { 
            detail: logJson 
        });
        
        // 触发事件
        document.dispatchEvent(logEvent);
        
        // 仍然保留控制台输出
        if (level === 'error') {
            console.error(message, data || '');
        } else {
            console.log(message, data || '');
        }
        
        return true;
    } catch (e) {
        console.error('发送日志到Python失败:', e);
        return false;
    }
};

// 处理循环引用和DOM对象问题的安全序列化函数
function safeJsonData(data) {
    if (!data) return null;
    
    // 如果是基本类型，直接返回
    if (typeof data !== 'object' || data === null) return data;
    
    // 如果是DOM节点，返回简化信息
    if (data.nodeType) {
        return {
            type: 'DOMNode',
            tagName: data.tagName || '未知节点',
            className: data.className || '',
            id: data.id || ''
        };
    }
    
    // 如果是错误对象
    if (data instanceof Error) {
        return {
            type: 'Error',
            name: data.name,
            message: data.message,
            stack: data.stack
        };
    }
    
    // 如果是数组，处理每个元素
    if (Array.isArray(data)) {
        return data.map(item => safeJsonData(item));
    }
    
    // 处理普通对象，过滤不安全属性
    try {
        const safeObj = {};
        const seen = new WeakSet(); // 用于检测循环引用
        
        Object.keys(data).forEach(key => {
            // 跳过函数和私有属性
            if (typeof data[key] === 'function' || key.startsWith('_')) return;
            
            const value = data[key];
            
            // 检测循环引用
            if (typeof value === 'object' && value !== null) {
                if (seen.has(value)) {
                    safeObj[key] = '[循环引用]';
                    return;
                }
                seen.add(value);
            }
            
            // 递归处理属性值
            safeObj[key] = safeJsonData(value);
        });
        
        return safeObj;
    } catch (e) {
        return {
            type: 'Object',
            note: '无法安全序列化',
            error: e.message
        };
    }
}

// 简化的日志方法
const logInfo = (msg, data) => window.AiSparkHub.logToPython('info', msg, data);
const logError = (msg, data) => window.AiSparkHub.logToPython('error', msg, data);
const logWarning = (msg, data) => window.AiSparkHub.logToPython('warning', msg, data);
const logDebug = (msg, data) => window.AiSparkHub.logToPython('debug', msg, data);

// 添加Rangy库支持 - 处理CSP限制问题
(function() {
    logInfo("===== Rangy库加载诊断 =====");
    logInfo("开始加载Rangy库...");
    
    // 检查是否已经加载过
    if (typeof window.rangyLoaded !== 'undefined') {
        logInfo("Rangy库已经开始加载，避免重复");
        return;
    }
    
    // 标记已经开始加载
    window.rangyLoaded = false;
    
    // 检测是否可能有CSP限制
    function detectCSP() {
        // 检查当前域名是否为已知的严格CSP站点
        const strictCSPSites = ['chat.openai.com', 'chatgpt.com', 'claude.ai', 'bard.google.com'];
        const currentHost = window.location.hostname;
        
        for (const site of strictCSPSites) {
            if (currentHost.includes(site)) {
                logWarning(`检测到可能的CSP限制站点: ${currentHost}`);
                return true;
            }
        }
        
        return false;
    }
    
    const hasCSPRestriction = detectCSP();
    
    // 尝试加载Rangy
    function loadRangy() {
        // 如果检测到CSP限制，显示警告并跳过加载
        if (hasCSPRestriction) {
            logWarning("当前网站存在CSP限制，无法加载外部Rangy库。将使用传统高亮方法。");
            showToast("此网站限制了外部脚本，将使用基本高亮功能");
            return;
        }
        
        // 动态加载Rangy核心
        const rangyScript = document.createElement('script');
        rangyScript.src = 'https://cdn.jsdelivr.net/npm/rangy@1.3.0/lib/rangy-core.min.js';
        rangyScript.async = false; // 改为同步加载，确保顺序
        
        // 加载完核心后加载highlighter模块
        rangyScript.onload = function() {
            logInfo("Rangy核心库加载成功!");
            
            // 先加载classapplier模块 (highlighter需要此模块)
            const classapplierScript = document.createElement('script');
            classapplierScript.src = 'https://cdn.jsdelivr.net/npm/rangy@1.3.0/lib/rangy-classapplier.min.js';
            classapplierScript.async = false;
            
            // 加载highlighter模块
            classapplierScript.onload = function() {
                logInfo("Rangy类应用模块加载成功!");
                
                const highlighterScript = document.createElement('script');
                highlighterScript.src = 'https://cdn.jsdelivr.net/npm/rangy@1.3.0/lib/rangy-highlighter.min.js';
                highlighterScript.async = false;
                
                highlighterScript.onload = function() {
                    logInfo("Rangy高亮模块加载成功!");
                    
                    // 初始化Rangy
                    if (typeof rangy !== 'undefined') {
                        try {
                            logInfo("准备初始化Rangy...");
                            rangy.init();
                            logInfo("Rangy初始化成功! 版本:", rangy.version);
                            
                            // 创建一个highlighter
                            const highlighter = rangy.createHighlighter();
                            
                            // 定义全局样式变量，以便所有高亮方法可以共享
                            window.AiSparkHub = window.AiSparkHub || {};
                            window.AiSparkHub.highlightStyles = {
                                yellow: {
                                    backgroundColor: "rgba(255,255,0,0.3)",
                                    borderBottom: "2px solid gold",
                                    transition: "background-color 0.3s"
                                },
                                red: {
                                    backgroundColor: "rgba(255,0,0,0.3)",
                                    borderBottom: "2px solid red",
                                    transition: "background-color 0.3s"
                                },
                                green: {
                                    backgroundColor: "rgba(0,255,0,0.3)",
                                    borderBottom: "2px solid green",
                                    transition: "background-color 0.3s"
                                }
                            };
                            
                            // 添加不同颜色的应用器
                            highlighter.addClassApplier(rangy.createClassApplier("ai-highlight-yellow", {
                                tagNames: ["span"],
                                elementAttributes: {
                                    "data-highlight-type": "yellow"
                                },
                                elementProperties: {
                                    style: window.AiSparkHub.highlightStyles.yellow
                                },
                                onElementCreate: function(element) {
                                    // 确保样式直接应用在元素上
                                    const style = window.AiSparkHub.highlightStyles.yellow;
                                    element.style.backgroundColor = style.backgroundColor;
                                    element.style.borderBottom = style.borderBottom; // 改为下划线
                                    element.style.transition = style.transition;
                                    element.className = "ai-highlight-yellow"; // 确保类名被应用
                                }
                            }));
                            
                            highlighter.addClassApplier(rangy.createClassApplier("ai-highlight-red", {
                                tagNames: ["span"],
                                elementAttributes: {
                                    "data-highlight-type": "red"
                                },
                                elementProperties: {
                                    style: window.AiSparkHub.highlightStyles.red
                                },
                                onElementCreate: function(element) {
                                    // 确保样式直接应用在元素上
                                    const style = window.AiSparkHub.highlightStyles.red;
                                    element.style.backgroundColor = style.backgroundColor;
                                    element.style.borderBottom = style.borderBottom; // 改为下划线
                                    element.style.transition = style.transition;
                                    element.className = "ai-highlight-red"; // 确保类名被应用
                                }
                            }));
                            
                            highlighter.addClassApplier(rangy.createClassApplier("ai-highlight-green", {
                                tagNames: ["span"],
                                elementAttributes: {
                                    "data-highlight-type": "green"
                                },
                                elementProperties: {
                                    style: window.AiSparkHub.highlightStyles.green
                                },
                                onElementCreate: function(element) {
                                    // 确保样式直接应用在元素上
                                    const style = window.AiSparkHub.highlightStyles.green;
                                    element.style.backgroundColor = style.backgroundColor;
                                    element.style.borderBottom = style.borderBottom; // 改为下划线
                                    element.style.transition = style.transition;
                                    element.className = "ai-highlight-green"; // 确保类名被应用
                                }
                            }));
                            
                            // 将highlighter保存到全局对象
                            window.AiSparkHub.rangyHighlighter = highlighter;
                            logInfo("Rangy高亮器配置完成", highlighter);
                            
                            // 标记加载成功
                            window.rangyLoaded = true;
                            
                            // 显示加载成功提示
                            showToast("Rangy高亮库加载成功！");
                        } catch (e) {
                            logError("Rangy初始化失败:", e);
                            showToast("Rangy初始化失败: " + e.message);
                        }
                    } else {
                        logError("Rangy对象不存在，加载失败");
                        showToast("Rangy对象不存在，加载失败");
                    }
                };
                
                highlighterScript.onerror = function() {
                    logError("Rangy高亮模块加载失败!");
                    showToast("Rangy高亮模块加载失败");
                };
                
                document.head.appendChild(highlighterScript);
            };
            
            classapplierScript.onerror = function() {
                logError("Rangy类应用模块加载失败!");
                showToast("Rangy类应用模块加载失败");
            };
            
            document.head.appendChild(classapplierScript);
        };
        
        rangyScript.onerror = function() {
            logError("Rangy核心库加载失败!");
            showToast("Rangy核心库加载失败");
        };
        
        document.head.appendChild(rangyScript);
    }
    
    // 开始加载
    loadRangy();
    
    logInfo("Rangy脚本已添加到文档中");
})();

// 修改原有的highlightSelection函数，使用Rangy
function highlightSelection(bgColor, border, type) {
    logInfo("🔍 检查Rangy状态");
    
    // 直接检查window对象
    logDebug("rangy对象存在: " + (typeof rangy !== 'undefined'));
    logDebug("rangyLoaded标志: " + window.rangyLoaded);
    logDebug("AiSparkHub对象: " + !!window.AiSparkHub);
    logDebug("rangyHighlighter对象: " + !!(window.AiSparkHub && window.AiSparkHub.rangyHighlighter));
    
    // 检查Rangy高亮器是否可用
    if (window.rangyLoaded && window.AiSparkHub && window.AiSparkHub.rangyHighlighter && typeof rangy !== 'undefined') {
        logInfo("✅ Rangy高亮器可用，尝试使用Rangy高亮文本");
        
        try {
            const selection = rangy.getSelection();
            
            logDebug("当前选择对象类型: " + (selection ? typeof selection : 'undefined'));
            logDebug("选择是否为空: " + (selection ? selection.isCollapsed : 'undefined'));
            logDebug("选择的文本: " + (selection ? selection.toString() : 'undefined'));
            
            if (selection.isCollapsed) {
                logInfo("没有选择文本，无法高亮");
                return false;
            }
            
            // 获取选中的文本内容
            const selectedText = selection.toString();
            
            // 根据颜色确定使用哪种样式
            let className = "ai-highlight-yellow"; // 默认黄色
            
            // 解析传入的颜色值
            logInfo("传入的颜色值: " + bgColor);
            
            // 更精确的颜色匹配
            if (typeof bgColor === 'string') {
                // 提取颜色分量进行比较
                if (bgColor.includes('red') || (bgColor.match(/rgba?\s*\(\s*255\s*,\s*0\s*,\s*0/))) {
                    className = "ai-highlight-red";
                    logInfo("选择红色高亮");
                } else if (bgColor.includes('green') || (bgColor.match(/rgba?\s*\(\s*0\s*,\s*255\s*,\s*0/))) {
                    className = "ai-highlight-green";
                    logInfo("选择绿色高亮");
                } else if (bgColor.includes('yellow') || (bgColor.match(/rgba?\s*\(\s*255\s*,\s*255\s*,\s*0/))) {
                    className = "ai-highlight-yellow";
                    logInfo("选择黄色高亮");
                } else {
                    logInfo("未匹配到具体颜色，使用默认黄色高亮");
                }
            }
            
            // 应用高亮
            logInfo("使用Rangy高亮，应用类: " + className);
            
            try {
                // 检查highlighter对象
                logDebug("检查highlighter可用性: " + !!window.AiSparkHub.rangyHighlighter);
                logDebug("检查highlightSelection方法: " + typeof window.AiSparkHub.rangyHighlighter.highlightSelection);
                
                // 试着使用highlighter
                window.AiSparkHub.rangyHighlighter.highlightSelection(className);
                logInfo("Rangy高亮操作成功!");
                
                // 获取选区范围信息
                const ranges = selection.getAllRanges();
                if (ranges.length > 0) {
                    const range = ranges[0]; // 获取第一个范围
                    
                    // 尝试获取XPath和偏移量
                    let xpath = '';
                    let offsetStart = 0;
                    let offsetEnd = 0;
                    
                    try {
                        if (range.startContainer && range.startContainer.nodeType === Node.TEXT_NODE) {
                            // 获取起始节点的XPath
                            xpath = getXPathForElement(range.startContainer.parentNode);
                            offsetStart = range.startOffset;
                            offsetEnd = range.endOffset;
                            
                            // 保存高亮数据到后端
                            saveHighlightToPython({
                                url: getCurrentPageUrl(),
                                text_content: selectedText,
                                xpath: xpath,
                                offset_start: offsetStart,
                                offset_end: offsetEnd,
                                highlight_type: type || className.replace('ai-highlight-', ''),
                                bg_color: bgColor,
                                border: border || '',
                                note: ''
                            });
                        }
                    } catch (xpathError) {
                        logError("获取XPath失败:" + xpathError.message);
                    }
                }
                
                // 查看创建的高亮元素样式
                setTimeout(() => {
                    const highlights = document.querySelectorAll("span." + className);
                    logInfo("创建的高亮元素数量: " + highlights.length);
                    if (highlights.length > 0) {
                        const lastHighlight = highlights[highlights.length - 1];
                        logInfo("高亮元素样式: " + lastHighlight.style.cssText);
                        logInfo("高亮元素类名: " + lastHighlight.className);
                    }
                }, 50);
                
                // 清除选择
                selection.removeAllRanges();
                
                // 显示成功提示
                showToast("✅ 高亮成功并已保存");
                
                return true;
            } catch (highlightError) {
                logError("Rangy高亮具体操作失败:" + highlightError.message);
                showToast("Rangy高亮操作失败: " + highlightError.message);
                return false;
            }
        } catch (e) {
            logError("Rangy高亮整体失败:" + e.message);
            showToast("Rangy高亮失败: " + e.message);
            return false;
        }
    } else {
        logWarning("❌ Rangy高亮器未初始化或不可用，使用原始方法");
        showToast("Rangy未加载完成，使用传统方法");
        return false;
    }
}

/**
 * 获取元素的XPath路径
 * @param {Element} element - DOM元素
 * @return {String} XPath路径
 */
function getXPathForElement(element) {
    if (!element) return '';
    
    // 如果已到达根节点，返回
    if (element.tagName === 'HTML') return '/HTML[1]';
    if (element === document.body) return '/HTML[1]/BODY[1]';
    
    let ix = 0;
    let siblings = element.parentNode.childNodes;
    
    for (let i = 0; i < siblings.length; i++) {
        let sibling = siblings[i];
        
        // 同样的元素类型
        if (sibling === element) {
            // 构建路径
            let path = getXPathForElement(element.parentNode);
            let tagName = element.tagName;
            
            // 添加索引
            path += '/' + tagName + '[' + (ix + 1) + ']';
            return path;
        }
        
        // 确保节点类型和标签名匹配后才递增计数
        if (sibling.nodeType === 1 && sibling.tagName === element.tagName) {
            ix++;
        }
    }
    
    // 如果未找到匹配项
    return '';
}

/**
 * 保存高亮数据到Python后端
 * @param {Object} highlightData - 高亮数据对象
 */
function saveHighlightToPython(highlightData) {
    try {
        logInfo("准备保存高亮数据到后端", highlightData);
        
        // 检查WebChannel状态（如果有这个方法）
        if (window.AiSparkHub && typeof window.AiSparkHub.checkWebChannel === "function") {
            window.AiSparkHub.checkWebChannel();
        }
        
        // 决定使用哪种传输方式
        if (window.AiSparkHub && window.AiSparkHub.webChannelAvailable === false) {
            // WebChannel不可用，直接使用备用方式
            logInfo("WebChannel被标记为不可用，使用备用方案");
            if (window.AiSparkHub.fallbackHighlight) {
                window.AiSparkHub.fallbackHighlight(highlightData);
                logInfo("已通过备用方案发送高亮数据");
                return true;
            }
        }
        
        // 尝试使用WebChannel方式（默认）
        try {
            // 创建自定义事件
            const event = new CustomEvent('aiSaveHighlightToPython', {
                detail: JSON.stringify(highlightData)
            });
            
            // 派发事件，由Python后端捕获
            document.dispatchEvent(event);
            
            logInfo("高亮数据保存事件已发送");
            return true;
        } catch (error) {
            logError("标准保存方式失败:", error.message);
            
            // 失败时尝试备用方式
            if (window.AiSparkHub && window.AiSparkHub.fallbackHighlight) {
                logInfo("尝试使用备用方案发送高亮数据");
                window.AiSparkHub.fallbackHighlight(highlightData);
                logInfo("已通过备用方案发送高亮数据");
                return true;
            } else {
                logError("备用传输方案不可用，无法保存高亮数据");
                return false;
            }
        }
    } catch (error) {
        logError("保存高亮数据失败:", error.message);
        return false;
    }
}

/**
 * 应用保存的高亮数据
 * @param {Array} highlightDataArray - 高亮数据数组
 */
function applyStoredHighlights(highlightDataArray) {
    if (!Array.isArray(highlightDataArray) || highlightDataArray.length === 0) {
        logInfo("没有高亮数据需要应用");
        return;
    }
    
    logInfo("开始应用保存的高亮数据", { count: highlightDataArray.length });
    
    // 确保Rangy已加载
    if (!window.rangyLoaded || !window.AiSparkHub || !window.AiSparkHub.rangyHighlighter) {
        logWarning("Rangy未初始化，无法应用高亮");
        setTimeout(() => applyStoredHighlights(highlightDataArray), 1000); // 延迟重试
        return;
    }
    
    // 遍历所有高亮数据
    highlightDataArray.forEach(data => {
        try {
            // 查找XPath对应的元素
            const element = getElementByXPath(data.xpath);
            
            if (!element || !element.childNodes || element.childNodes.length === 0) {
                logWarning("未找到匹配的元素:", data.xpath);
                return;
            }
            
            // 获取文本节点
            const textNodes = getAllTextNodesIn(element);
            if (textNodes.length === 0) {
                logWarning("元素内没有文本节点");
                return;
            }
            
            // 查找包含目标文本的节点
            let targetNode = null;
            let nodeText = '';
            
            for (const node of textNodes) {
                nodeText = node.nodeValue || '';
                if (nodeText.includes(data.text_content)) {
                    targetNode = node;
                    break;
                }
            }
            
            // 如果找不到精确匹配，使用第一个文本节点
            if (!targetNode && textNodes.length > 0) {
                targetNode = textNodes[0];
                logWarning("未找到包含目标文本的节点，使用第一个文本节点");
            }
            
            if (!targetNode) {
                logWarning("无法找到合适的文本节点");
                return;
            }
            
            // 创建范围并应用高亮
            try {
                const range = rangy.createRange();
                
                // 尝试使用保存的偏移量
                if (data.offset_start >= 0 && data.offset_end > data.offset_start) {
                    range.setStart(targetNode, data.offset_start);
                    range.setEnd(targetNode, data.offset_end);
                } else {
                    // 如果偏移量无效，尝试通过文本内容查找
                    const startPos = nodeText.indexOf(data.text_content);
                    if (startPos >= 0) {
                        range.setStart(targetNode, startPos);
                        range.setEnd(targetNode, startPos + data.text_content.length);
                    } else {
                        logWarning("无法在文本中定位高亮内容");
                        return;
                    }
                }
                
                // 确定高亮类名
                let className = 'ai-highlight-yellow'; // 默认
                
                if (data.highlight_type) {
                    if (data.highlight_type.includes('red')) {
                        className = 'ai-highlight-red';
                    } else if (data.highlight_type.includes('green')) {
                        className = 'ai-highlight-green';
                    } else if (data.highlight_type.includes('yellow')) {
                        className = 'ai-highlight-yellow';
                    }
                }
                
                // 应用高亮
                window.AiSparkHub.rangyHighlighter.highlightRange(className, range);
                logInfo("成功应用高亮", {
                    text: data.text_content,
                    class: className
                });
                
                // 发送高亮应用成功的通知
                notifyHighlightApplied(data.id);
                
            } catch (rangeError) {
                logError("创建或应用高亮范围失败:", rangeError.message);
            }
            
        } catch (error) {
            logError("应用高亮记录失败:", error.message);
        }
    });
}

/**
 * 通过XPath获取元素
 * @param {String} xpath - XPath表达式
 * @return {Element} 匹配的DOM元素
 */
function getElementByXPath(xpath) {
    try {
        return document.evaluate(
            xpath,
            document,
            null,
            XPathResult.FIRST_ORDERED_NODE_TYPE,
            null
        ).singleNodeValue;
    } catch (e) {
        logError("XPath求值失败:", e.message);
        return null;
    }
}

/**
 * 获取元素内所有文本节点
 * @param {Element} element - DOM元素
 * @return {Array} 文本节点数组
 */
function getAllTextNodesIn(element) {
    const textNodes = [];
    
    function collectTextNodes(node) {
        if (node.nodeType === Node.TEXT_NODE && node.nodeValue.trim()) {
            textNodes.push(node);
        } else {
            for (let i = 0; i < node.childNodes.length; i++) {
                collectTextNodes(node.childNodes[i]);
            }
        }
    }
    
    collectTextNodes(element);
    return textNodes;
}

/**
 * 通知Python后端高亮已应用
 * @param {Number} highlightId - 高亮记录ID
 */
function notifyHighlightApplied(highlightId) {
    try {
        // 创建自定义事件
        const event = new CustomEvent('aiHighlightApplied', {
            detail: JSON.stringify({ id: highlightId })
        });
        
        // 派发事件
        document.dispatchEvent(event);
    } catch (error) {
        logError("通知高亮应用状态失败:", error.message);
    }
}

// 简单高亮功能
(function() {
    logInfo("======== AiSparkHub 高亮和复制功能初始化 ========");
    logInfo("navigator.clipboard是否可用:" + (typeof navigator.clipboard !== 'undefined'));
    logInfo("document.execCommand是否可用:" + (typeof document.execCommand === 'function'));
    
    logInfo("初始化简单高亮功能");
    
    // 创建高亮菜单
    const menu = document.createElement('div');
    menu.id = 'highlight-menu';
    menu.style.cssText = `
        position: fixed;
        display: none;
        background: white;
        border: none;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 10000;
        padding: 6px;
        font-family: 'Segoe UI', Arial, sans-serif;
        max-width: 210px;
        animation: fadeIn 0.2s ease-out;
    `;

    // 容器用于水平排列按钮
    const buttonContainer = document.createElement('div');
    buttonContainer.style.cssText = `
        display: flex;
        justify-content: space-between;
        padding: 0 2px;
    `;
    menu.appendChild(buttonContainer);
    
    // 定义颜色和按钮
    const colors = [
        { name: '复制', color: '#f8f8f8', border: '2px solid #ccc', icon: '📋', action: 'copy' },
        { name: '红色', color: 'rgba(255,0,0,0.3)', border: '2px solid red', icon: '🔴', action: 'highlight', type: 'red' },
        { name: '黄色', color: 'rgba(255,255,0,0.3)', border: '2px solid gold', icon: '🟡', action: 'highlight', type: 'yellow' },
        { name: '绿色', color: 'rgba(0,255,0,0.3)', border: '2px solid green', icon: '🟢', action: 'highlight', type: 'green' }
    ];
    
    // 添加颜色按钮
    colors.forEach(c => {
        const btn = document.createElement('div');
        btn.style.cssText = `
            display: flex;
            flex-direction: column;
            align-items: center;
            margin: 0 3px;
            cursor: pointer;
            transition: transform 0.1s;
            user-select: none;
            width: 42px;
        `;
        
        // 按钮图标带色块
        const iconDiv = document.createElement('div');
        iconDiv.style.cssText = `
            width: 18px;
            height: 18px;
            border-radius: 50%;
            background-color: ${c.color};
            border: ${c.border};
            display: flex;
            justify-content: center;
            align-items: center;
            margin-bottom: 3px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            font-size: 12px;
        `;
        
        // 复制按钮使用图标文本
        if (c.action === 'copy') {
            iconDiv.innerHTML = '📋';
        }
        
        // 按钮文字
        const textDiv = document.createElement('div');
        textDiv.textContent = c.name;
        textDiv.style.cssText = `
            font-size: 11px;
            color: #555;
        `;
        
        btn.appendChild(iconDiv);
        btn.appendChild(textDiv);
        
        // 鼠标悬停和点击效果
        btn.onmouseover = () => {
            iconDiv.style.transform = 'scale(1.1)';
            textDiv.style.color = '#333';
        };
        btn.onmouseout = () => {
            iconDiv.style.transform = 'scale(1)';
            textDiv.style.color = '#555';
        };
        btn.onmousedown = () => {
            iconDiv.style.transform = 'scale(0.95)';
        };
        btn.onmouseup = () => {
            iconDiv.style.transform = 'scale(1.1)';
        };
        
        btn.onclick = () => {
            if (c.action === 'copy') {
                copySelection();
            } else {
                // 先尝试使用Rangy高亮
                logInfo("点击高亮按钮，尝试高亮，类型: " + c.type);
                const rangySuccess = highlightSelection(c.color, c.border, c.type);
                
                // 如果Rangy失败，使用原始方法
                if (!rangySuccess) {
                    logInfo("Rangy高亮失败，回退到传统方法");
                    legacyHighlightSelection(c.color, c.border, c.type);
                }
                
                menu.style.display = 'none';
            }
        };
        
        buttonContainer.appendChild(btn);
    });
    
    // 添加CSS动画
    const style = document.createElement('style');
    style.textContent = `
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
    `;
    document.head.appendChild(style);
    
    // 添加到文档
    document.body.appendChild(menu);
    
    // 检测当前网站类型
    const isPerplexity = window.location.hostname.includes('perplexity.ai');
    
    // 为Perplexity网站添加特殊处理
    if (isPerplexity) {
        logInfo("检测到Perplexity网站，使用键盘快捷键触发高亮菜单");
        
        // 添加指导提示
        const hintDiv = document.createElement('div');
        hintDiv.style.cssText = `
            position: fixed;
            top: 10px;
            right: 10px;
            background: rgba(0,0,0,0.7);
            color: white;
            padding: 8px 12px;
            border-radius: 4px;
            z-index: 9999;
            font-size: 12px;
            pointer-events: none;
            transition: opacity 0.3s;
            opacity: 0.8;
        `;
        hintDiv.textContent = "选择文本后按 Alt+H 显示高亮菜单";
        document.body.appendChild(hintDiv);
        
        // 5秒后隐藏提示
        setTimeout(() => {
            hintDiv.style.opacity = "0";
            setTimeout(() => {
                if (document.body.contains(hintDiv)) {
                    document.body.removeChild(hintDiv);
                }
            }, 300);
        }, 5000);
        
        // 监听键盘快捷键
        document.addEventListener('keydown', function(e) {
            // Alt+H 组合键显示高亮菜单
            if (e.altKey && e.key === 'h') {
                e.preventDefault(); // 防止默认行为
                const selection = window.getSelection();
                const text = selection.toString().trim();
                
                if (text) {
                    // 获取选择范围位置
                    try {
                        const range = selection.getRangeAt(0);
                        const rect = range.getBoundingClientRect();
                        
                        // 显示菜单在选择区域下方
                        const x = rect.left + (rect.width / 2);
                        const y = rect.bottom;
                        
                        // 用绝对定位显示菜单，避免React干扰
                        menu.style.display = 'none'; // 先隐藏，然后重新显示
                        menu.style.position = 'absolute';
                        menu.style.zIndex = '2147483647'; // 最大z-index
                        menu.style.left = x + 'px';
                        menu.style.top = (y + 10) + 'px';
                        
                        // 确保在视口内
                        if (parseFloat(menu.style.left) + 210 > window.innerWidth) {
                            menu.style.left = (window.innerWidth - 220) + 'px';
                        }
                        
                        // 显示菜单
                        menu.style.display = 'block';
                        logInfo("通过键盘快捷键显示高亮菜单");
                        
                        // 闪烁菜单以提示用户
                        menu.style.animation = 'none';
                        setTimeout(() => {
                            menu.style.animation = 'fadeIn 0.3s ease-out';
                        }, 10);
                    } catch (e) {
                        logError("显示菜单时出错: " + e.message);
                    }
                } else {
                    logInfo("没有选择文本，不显示菜单");
                }
            }
        });
        
        // 点击文档隐藏菜单（但不注册mouseup事件，避免React冲突）
        document.addEventListener('click', function(e) {
            if (menu.style.display === 'block' && !menu.contains(e.target)) {
                menu.style.display = 'none';
            }
        }, true); // 使用捕获阶段
        
    } else {
        // 其他网站使用标准监听方式
        document.addEventListener('mouseup', function(e) {
            // 处理当前的click/mouseup事件
            setTimeout(function() {
                const selection = window.getSelection();
                const text = selection.toString().trim();
                
                // 菜单默认不显示
                menu.style.display = 'none';
                
                // 有选中文本时才显示菜单
                if (text) {
                    menu.style.display = 'block';
                    
                    // 计算位置，避免超出屏幕边缘
                    const menuWidth = 210; // 菜单宽度
                    const menuHeight = 90; // 菜单高度
                    
                    let leftPos = e.pageX - menuWidth / 2;
                    let topPos = e.pageY + 10;
                    
                    // 确保不超出右边
                    if (leftPos + menuWidth > window.innerWidth + window.scrollX) {
                        leftPos = window.innerWidth + window.scrollX - menuWidth - 10;
                    }
                    
                    // 确保不超出左边
                    if (leftPos < window.scrollX) {
                        leftPos = window.scrollX + 10;
                    }
                    
                    // 确保不超出底部
                    if (topPos + menuHeight > window.innerHeight + window.scrollY) {
                        topPos = e.pageY - menuHeight - 10;
                    }
                    
                    menu.style.left = `${leftPos}px`;
                    menu.style.top = `${topPos}px`;
                }
            }, 0);
        });
    }
    
    // 点击页面任何位置关闭菜单（除了菜单本身）
    document.addEventListener('mousedown', function(e) {
        // 如果点击的不是菜单区域，就隐藏菜单
        if (!menu.contains(e.target)) {
            menu.style.display = 'none';
        }
    });
    
    // 添加键盘Escape键隐藏菜单
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            menu.style.display = 'none';
        }
    });
    
    // 复制选中文本
    function copySelection() {
        const selection = window.getSelection();
        if (!selection.rangeCount) {
            console.log('复制失败: 未选中任何文本');
            showToast('复制失败: 未选中任何文本');
            return;
        }
        
        const text = selection.toString();
        
        try {
            // 使用现代剪贴板API
            navigator.clipboard.writeText(text)
                .then(() => {
                    console.log('复制成功');
                    showToast('复制成功');
                })
                .catch(err => {
                    console.error('复制失败:', err);
                    showToast('复制失败');
                });
        } catch (e) {
            console.error('复制操作异常:', e);
            showToast('复制失败: ' + e.message);
        }
    }
    
    // 原始高亮方法，重命名为legacyHighlightSelection
    function legacyHighlightSelection(bgColor, border, type) {
        // 根据类型直接选择样式，而不是依赖颜色字符串分析
        let styleToUse;
        
        if (window.AiSparkHub && window.AiSparkHub.highlightStyles) {
            // 根据明确的类型参数选择样式
            if (type === 'red') {
                styleToUse = window.AiSparkHub.highlightStyles.red;
                logInfo("legacyHighlight: 使用红色样式");
            } else if (type === 'green') {
                styleToUse = window.AiSparkHub.highlightStyles.green;
                logInfo("legacyHighlight: 使用绿色样式");
            } else {
                styleToUse = window.AiSparkHub.highlightStyles.yellow;
                logInfo("legacyHighlight: 使用黄色样式");
            }
            
            // 获取正确的样式属性
            bgColor = styleToUse.backgroundColor;
            border = styleToUse.borderBottom;
        }
        
        const selection = window.getSelection();
        if (!selection.rangeCount) return;
        
        try {
            // 获取原始范围
            const originalRange = selection.getRangeAt(0);
            
            // 创建一个文档片段来分析选择的内容
            const fragment = originalRange.cloneContents();
            const nodes = getAllTextNodes(fragment);
            
            // 如果是简单选择（仅包含一个文本节点），使用传统方法
            if (nodes.length <= 1 && !originalRange.startContainer.contains(originalRange.endContainer) &&
                originalRange.startContainer === originalRange.endContainer) {
                // 创建高亮元素
                const span = document.createElement('span');
                span.style.backgroundColor = bgColor;
                span.style.borderBottom = border; // 使用borderBottom替代border
                span.style.transition = 'background-color 0.3s';
                
                // 尝试简单包裹
                originalRange.surroundContents(span);
                
                // 添加短暂闪烁效果以提供视觉反馈
                const originalBg = span.style.backgroundColor;
                span.style.backgroundColor = 'rgba(255,255,255,0.9)';
                setTimeout(() => {
                    span.style.backgroundColor = originalBg;
                }, 150);
                
                // 显示提示 - 简单方法
                showToast("🔶 使用简单方法高亮成功");
            } else {
                // 复杂选择（跨多个元素），采用分段高亮方法
                highlightComplexSelection(originalRange, bgColor, border);
                
                // 显示提示 - 复杂方法
                showToast("🔸 使用复杂方法高亮成功");
            }
            
            // 清除选择
            selection.removeAllRanges();
            console.log('已使用原始方法高亮文本');
            
        } catch (e) {
            console.error('高亮操作失败:', e);
            
            // 尝试使用备用的分段高亮方法
            try {
                const range = selection.getRangeAt(0);
                highlightComplexSelection(range, bgColor, border);
                selection.removeAllRanges();
                console.log('使用备用方法成功高亮文本');
                
                // 显示提示 - 备用方法
                showToast("⚠️ 使用备用方法高亮成功");
            } catch (backupError) {
                console.error('备用高亮方法也失败:', backupError);
                showToast('❌ 无法高亮选中的内容，请尝试选择更简单的文本块');
            }
        }
    }
    
    // 用于复杂选择（跨多个DOM元素）的高亮处理函数
    function highlightComplexSelection(range, bgColor, border) {
        // 创建一个TreeWalker来遍历范围内的所有文本节点
        const startNode = range.startContainer;
        const endNode = range.endContainer;
        const commonAncestor = range.commonAncestorContainer;
        
        // 创建一个文档片段来获取范围内的所有节点
        const fragment = range.cloneContents();
        const walker = document.createTreeWalker(
            commonAncestor,
            NodeFilter.SHOW_TEXT,
            {
                acceptNode: function(node) {
                    // 只接受范围内的文本节点
                    const nodeRange = document.createRange();
                    nodeRange.selectNode(node);
                    
                    // 检查节点是否与选择范围有交集
                    if (range.compareBoundaryPoints(Range.END_TO_START, nodeRange) <= 0 &&
                        range.compareBoundaryPoints(Range.START_TO_END, nodeRange) >= 0) {
                        return NodeFilter.FILTER_ACCEPT;
                    }
                    return NodeFilter.FILTER_REJECT;
                }
            }
        );
        
        // 收集范围内的所有文本节点
        const textNodes = [];
        let currentNode = walker.nextNode();
        
        while (currentNode) {
            // 只处理可见文本内容的节点
            if (currentNode.textContent.trim() !== '') {
                textNodes.push(currentNode);
            }
            currentNode = walker.nextNode();
        }
        
        // 处理每个文本节点
        textNodes.forEach((node, index) => {
            try {
                // 为每个节点创建一个新范围
                const nodeRange = document.createRange();
                
                // 设置范围的开始和结束
                if (node === startNode) {
                    // 第一个节点，从选择的起始位置开始
                    nodeRange.setStart(node, range.startOffset);
                    nodeRange.setEnd(node, node.length);
                } else if (node === endNode) {
                    // 最后一个节点，到选择的结束位置结束
                    nodeRange.setStart(node, 0);
                    nodeRange.setEnd(node, range.endOffset);
                } else {
                    // 中间节点，包含整个文本
                    nodeRange.selectNode(node);
                }
                
                // 创建高亮元素
                const span = document.createElement('span');
                span.style.backgroundColor = bgColor;
                span.style.borderBottom = border; // 使用borderBottom替代border
                span.style.transition = 'background-color 0.3s';
                
                // 使用surroundContents高亮此节点
                nodeRange.surroundContents(span);
                
                // 添加闪烁效果
                const originalBg = span.style.backgroundColor;
                span.style.backgroundColor = 'rgba(255,255,255,0.9)';
                setTimeout(() => {
                    span.style.backgroundColor = originalBg;
                }, 150);
                
            } catch (e) {
                console.warn(`无法高亮文本节点 ${index}:`, e);
            }
        });
    }
    
    // 获取所有文本节点的辅助函数
    function getAllTextNodes(node) {
        const textNodes = [];
        
        function collectTextNodes(currentNode) {
            if (currentNode.nodeType === Node.TEXT_NODE && currentNode.textContent.trim() !== '') {
                textNodes.push(currentNode);
            } else {
                for (let i = 0; i < currentNode.childNodes.length; i++) {
                    collectTextNodes(currentNode.childNodes[i]);
                }
            }
        }
        
        collectTextNodes(node);
        return textNodes;
    }
    
    console.log("简单高亮功能初始化完成");
})();

// 修改全局复制函数，直接使用navigator.clipboard
window.copyTextThroughJs = function(text) {
    console.log("复制文本:", text);
    try {
        navigator.clipboard.writeText(text)
            .then(() => {
                console.log("复制成功");
                alert("文本已复制到剪贴板");
                return true;
            })
            .catch(err => {
                console.error("复制失败:", err);
                alert("复制失败: " + err.message);
                return false;
            });
    } catch (e) {
        console.error("复制异常:", e);
        alert("复制失败: " + e.message);
        return false;
    }
    
    return true; // 返回true以表示复制请求已发出
};

/**
 * 测试WebChannel通信
 */
function testWebChannelCommunication() {
    logInfo("开始测试WebChannel通信...");
    
    try {
        // 检查必要对象
        const qtExists = typeof qt !== 'undefined';
        const transportExists = qtExists && typeof qt.webChannelTransport !== 'undefined';
        const webChannelExists = typeof QWebChannel !== 'undefined';
        
        logInfo("WebChannel前置检查:", {
            qt存在: qtExists,
            transport存在: transportExists,
            QWebChannel存在: webChannelExists
        });
        
        if (!qtExists || !transportExists) {
            logError("WebChannel通信所需的qt对象不完整，无法建立通信");
            return;
        }
        
        // 如果QWebChannel不存在，但qt.webChannelTransport存在，尝试等待QWebChannel对象
        if (!webChannelExists) {
            logWarning("QWebChannel对象不存在，等待10秒后重试");
            // 间隔1秒检查10次
            let checkCount = 0;
            const checkInterval = setInterval(function() {
                checkCount++;
                if (typeof QWebChannel !== 'undefined') {
                    logInfo("QWebChannel已加载，开始测试通信");
                    clearInterval(checkInterval);
                    completeTest();
                } else if (checkCount >= 10) {
                    logError("等待10秒后QWebChannel仍不可用，测试失败");
                    clearInterval(checkInterval);
                } else {
                    logInfo(`等待QWebChannel加载...第${checkCount}次检查`);
                }
            }, 1000);
            return;
        }
        
        completeTest();
    } catch (error) {
        logError("测试WebChannel通信时出错:", error.message);
    }
    
    // 执行实际测试
    function completeTest() {
        try {
            // 尝试创建WebChannel并发送测试数据
            logInfo("准备创建QWebChannel并测试通信...");
            
            new QWebChannel(qt.webChannelTransport, function(channel) {
                logInfo("QWebChannel已创建，可用对象:", Object.keys(channel.objects));
                
                if (channel.objects.highlightBridge) {
                    logInfo("找到highlightBridge对象，发送测试数据");
                    
                    const testData = {
                        text_content: "WebChannel通信测试",
                        url: window.location.href,
                        timestamp: new Date().toISOString(),
                        test: true
                    };
                    
                    channel.objects.highlightBridge.saveHighlight(JSON.stringify(testData));
                    logInfo("测试数据已发送到Python");
                    
                    // 尝试高亮操作
                    logInfo("测试高亮功能 - 创建自定义事件");
                    try {
                        const event = new CustomEvent('aiSaveHighlightToPython', {
                            detail: JSON.stringify(testData)
                        });
                        document.dispatchEvent(event);
                        logInfo("高亮事件已触发");
                    } catch (e) {
                        logError("触发高亮事件失败:", e.message);
                    }
                } else {
                    logError("无法找到highlightBridge对象，无法测试通信");
                }
            });
        } catch (error) {
            logError("测试通信失败:", error.message);
        }
    }
}

// 页面完全加载后执行WebChannel测试
window.addEventListener('load', function() {
    // 延迟5秒执行，确保所有组件已加载完成
    setTimeout(testWebChannelCommunication, 5000);
}); 