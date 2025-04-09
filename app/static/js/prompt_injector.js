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
 * 查找匹配的输入元素
 * @param {Object} selectors 选择器对象
 * @returns {HTMLElement|null} 找到的输入元素或null
 */
function findInputElement(selectors) {
    // 尝试主选择器
    let input = document.querySelector(selectors.input);
    if (input) return input;
    
    // 尝试备用选择器
    if (selectors.altInput) {
        input = document.querySelector(selectors.altInput);
        if (input) return input;
    }
    
    // 如果找不到输入元素，尝试通过标签和属性查找可能的输入框
    const possibleInputs = Array.from(document.querySelectorAll('textarea, [contenteditable="true"]'));
    return possibleInputs.length > 0 ? possibleInputs[0] : null;
}

/**
 * 查找匹配的按钮元素
 * @param {Object} selectors 选择器对象
 * @returns {HTMLElement|null} 找到的按钮元素或null
 */
function findButtonElement(selectors) {
    // 尝试主选择器
    let button = document.querySelector(selectors.button);
    if (button) return button;
    
    // 尝试备用选择器
    if (selectors.altButton) {
        button = document.querySelector(selectors.altButton);
        if (button) return button;
    }
    
    // 寻找可能的发送按钮
    const possibleButtons = Array.from(document.querySelectorAll('button'));
    // 查找标签名包含"发送"、"提交"或英文相关词汇的按钮
    const sendButton = possibleButtons.find(btn => {
        const text = btn.textContent.toLowerCase();
        return text.includes('发送') || text.includes('提交') || 
               text.includes('send') || text.includes('submit');
    });
    
    return sendButton || null;
}

/**
 * 设置输入框的值
 * @param {HTMLElement} input 输入元素
 * @param {string} message 消息内容
 */
function setInputValue(input, message) {
    // 检查是否是contenteditable元素
    if (input.getAttribute('contenteditable') === 'true') {
        input.innerHTML = message;
        input.dispatchEvent(new Event('input', { bubbles: true }));
        return;
    }
    
    // 尝试使用value属性
    if ('value' in input) {
        input.value = message;
        input.dispatchEvent(new Event('input', { bubbles: true }));
        return;
    }
    
    // 尝试使用insertText命令
    input.focus();
    document.execCommand('selectAll', false, null);
    document.execCommand('delete', false, null);
    document.execCommand('insertText', false, message);
}

/**
 * 向AI平台注入提示词并发送
 * @param {string} message 要发送的提示词
 * @param {string} [platformOverride] 可选的平台覆盖，默认从URL推断
 * @returns {Promise<boolean>} 是否成功
 */
async function injectPrompt(message, platformOverride = null) {
    try {
        console.log('开始注入提示词');
        
        // 确定平台
        const platform = platformOverride || getPlatformFromURL();
        if (!platform) {
            console.error('无法识别当前平台');
            return false;
        }
        console.log('识别平台:', platform);

        // 获取平台选择器
        const selectors = PLATFORM_SELECTORS[platform];
        if (!selectors) {
            console.error('未知的平台:', platform);
            return false;
        }

        // 查找输入框
        const input = findInputElement(selectors);
        if (!input) {
            console.error('未找到输入框');
            return false;
        }
        console.log('找到输入框:', input);
        
        // 设置输入值
        setInputValue(input, message);
        console.log('已设置输入值');
        
        // 等待文本注入完成
        await new Promise(resolve => setTimeout(resolve, 300));
        
        // 查找并点击发送按钮
        const button = findButtonElement(selectors);
        if (!button) {
            console.error('未找到发送按钮');
            return false;
        }
        console.log('找到发送按钮:', button);
        
        // 检查按钮是否被禁用
        if (button.disabled || button.getAttribute('aria-disabled') === 'true') {
            console.error('发送按钮被禁用');
            return false;
        }
        
        // 点击发送按钮
        button.click();
        console.log('已点击发送按钮');
        
        return true;
    } catch (error) {
        console.error('执行出错:', error);
        return false;
    }
}

// 将函数暴露给外部调用
window.AiSparkHub = window.AiSparkHub || {};
window.AiSparkHub.injectPrompt = injectPrompt; 