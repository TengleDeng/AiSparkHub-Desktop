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
        altInput: 'textarea[placeholder="Message ChatGPT…"]'
    },
    // Kimi
    kimi: {
        input: '[id="msh-chateditor"]',
        button: '[id="send-button"]',
        altInput: '.chat-input-editor'
    },
    // 豆包
    doubao: {
        input: 'textarea.semi-input-textarea',
        button: '#flow-end-msg-send'
    },
    // 元宝
    yuanbao: {
        input: '.ql-editor',
        button: 'a[class*="send-btn"]'
    },
    // Perplexity
    perplexity: {
        input: 'textarea.overflow-auto',
        button: 'button[aria-label="Submit"]'
    },
    // N
    n: {
        input: '#composition-input',
        button: '#home_chat_btn'
    },
    // MetaSo
    metaso: {
        input: '.search-consult-textarea',
        button: '.send-arrow-button'
    },
    // ChatGLM
    chatglm: {
        input: 'textarea.scroll-display-none',
        button: '.enter',
        altButton: '.enter_icon'
    },
    // Grok
    grok: {
        input: 'textarea.r-30o5oe',
        button: 'button.r-1f2l425',
        altInput: 'textarea[aria-label="向Grok提任何问题"]',
        altButton: 'button[type="submit"][aria-label="提交"]'
    },
    // Get笔记
    biji: {
        input: '.custom-rich-input',
        button: '.n-button'
    },
    // 文心一言
    yiyan: {
        input: '.yc-editor',
        button: '#sendBtn'
    },
    // 通义
    tongyi: {
        input: '.ant-input',
        button: '[class*="operateBtn"]'
    },
    // Gemini
    gemini: {
        input: '.text-input-field_textarea-wrapper',
        button: '.send-button'
    },
    // DeepSeek
    deepseek: {
        input: '#chat-input',
        button: '[role="button"][aria-disabled="false"]',
        altInput: 'textarea.text-base',
        altButton: 'button.send-button'
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
 * 将文本转换为Base64
 */
function textToBase64(text) {
    try {
        return btoa(unescape(encodeURIComponent(text)));
    } catch (e) {
        console.error('Base64编码失败:', e);
        return '';
    }
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
    
    // 将消息转换为Base64格式
    const base64Message = textToBase64(message);
    
    // 构建注入代码
    const injectionCode = `
        (async function() {
            try {
                // 查找输入框
                const input = document.querySelector('${selectors.input}');
                console.log('Input selector:', '${selectors.input}');
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

                // 直接注入文本，使用原始可靠的方法
                const originalMessage = decodeURIComponent(escape(atob("${base64Message}")));
                document.execCommand('insertText', false, originalMessage);
                console.log('文本已注入');

                // 等待文本注入完成
                await new Promise(resolve => setTimeout(resolve, 500));

                // 尝试查找发送按钮（多种方式）
                console.log('Trying to find button with selector:', '${selectors.button}');
                let button = document.querySelector('${selectors.button}');

                // 统一的点击处理逻辑
                const simulateClick = (element) => {
                    try {
                        // 使用完整的鼠标事件序列
                        ['mousedown', 'mouseup', 'click'].forEach(eventType => {
                            const event = new MouseEvent(eventType, {
                                bubbles: true,
                                cancelable: true,
                                view: window
                            });
                            element.dispatchEvent(event);
                        });
                        console.log('Mouse event sequence dispatched successfully');
                        return true;
                    } catch (error) {
                        console.error('Failed to simulate click:', error);
                        return false;
                    }
                };

                // 执行点击
                if (!simulateClick(button)) {
                    console.error('Click simulation failed');
                    return false;
                }

                console.log('已点击发送按钮');
                return true;
            } catch (error) {
                console.error('执行出错:', error);
                return false;
            }
        })();
    `;
    
    try {
        // 执行注入代码
        return await eval(injectionCode);
    } catch (error) {
        console.error('注入脚本执行失败:', error);
        return false;
    }
}

// 将函数暴露给外部调用
window.AiSparkHub = window.AiSparkHub || {};
window.AiSparkHub.injectPrompt = injectPrompt;
window.AiSparkHub.getPlatformFromURL = getPlatformFromURL; 