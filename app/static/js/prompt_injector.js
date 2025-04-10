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
        responseSelector: '.markdown___vuBDJ'
    },
    // 豆包
    doubao: {
        input: 'textarea.semi-input-textarea',
        button: '#flow-end-msg-send',
        responseSelector: '[data-testid="receive_message"]'
    },
    // 元宝
    yuanbao: {
        input: '.ql-editor',
        button: 'a[class*="send-btn"]'
    },
    // Perplexity
    perplexity: {
        input: 'textarea.overflow-auto',
        button: 'button[aria-label="Submit"]',
        responseSelector: "#response-textarea"
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
        button: '.enter_icon'
    },
    // Grok
    grok: {
        input: 'textarea[aria-label=\"向Grok提任何问题\"]',
        button: 'button[type=\"submit\"][aria-label=\"提交\"]'
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
    // Get笔记
    biji: {
        input: '.custom-rich-input',
        button: '.n-button'
    },
    // DeepSeek
    deepseek: {
        input: '#chat-input',
        button: '[role="button"][aria-disabled="false"]'
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

// 将函数暴露给外部调用
window.AiSparkHub = window.AiSparkHub || {};
window.AiSparkHub.injectPrompt = injectPrompt;
window.AiSparkHub.getPlatformFromURL = getPlatformFromURL;

// 简单高亮功能
(function() {
    console.log("初始化简单高亮功能");
    
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
    
    // 添加标题
    const title = document.createElement('div');
    title.textContent = '文本工具';
    title.style.cssText = `
        font-size: 13px;
        color: #333;
        padding: 2px 6px 6px 6px;
        border-bottom: 1px solid #eee;
        margin-bottom: 6px;
        font-weight: bold;
    `;
    menu.appendChild(title);
    
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
        { name: '红色', color: 'rgba(255,0,0,0.3)', border: '2px solid red', icon: '🔴', action: 'highlight' },
        { name: '黄色', color: 'rgba(255,255,0,0.3)', border: '2px solid gold', icon: '🟡', action: 'highlight' },
        { name: '绿色', color: 'rgba(0,255,0,0.3)', border: '2px solid green', icon: '🟢', action: 'highlight' }
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
                highlightSelection(c.color, c.border);
            }
            menu.style.display = 'none';
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
    
    // 监听选择事件
    document.addEventListener('mouseup', function(e) {
        const selection = window.getSelection();
        if (selection.toString().trim()) {
            // 如果有选中文本，显示菜单
            menu.style.display = 'block';
            
            // 计算位置，避免超出屏幕边缘
            const menuWidth = 210; // 更新菜单宽度
            const menuHeight = 90; // 更新菜单高度
            
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
    });
    
    // 点击其他地方关闭菜单
    document.addEventListener('mousedown', function(e) {
        if (!menu.contains(e.target)) {
            menu.style.display = 'none';
        }
    });
    
    // 复制选中文本
    function copySelection() {
        const selection = window.getSelection();
        if (!selection.rangeCount) return;
        
        try {
            // 复制到剪贴板
            const text = selection.toString();
            navigator.clipboard.writeText(text)
                .then(() => {
                    // 复制成功提示
                    showToast('复制成功');
                })
                .catch(err => {
                    console.error('复制失败:', err);
                    // 尝试备用方法
                    backupCopy(text);
                });
        } catch (e) {
            console.error('复制失败:', e);
            backupCopy(selection.toString());
        }
    }
    
    // 备用复制方法
    function backupCopy(text) {
        // 创建临时文本区域
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.opacity = '0';
        document.body.appendChild(textArea);
        textArea.select();
        
        try {
            // 执行复制命令
            document.execCommand('copy');
            showToast('复制成功');
        } catch (e) {
            console.error('备用复制失败:', e);
            showToast('复制失败');
        }
        
        // 移除临时元素
        document.body.removeChild(textArea);
    }
    
    // 显示toast提示
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
    
    // 高亮选中文本
    function highlightSelection(bgColor, border) {
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
                span.style.borderBottom = border;
                span.style.transition = 'background-color 0.3s';
                
                // 尝试简单包裹
                originalRange.surroundContents(span);
                
                // 添加短暂闪烁效果以提供视觉反馈
                const originalBg = span.style.backgroundColor;
                span.style.backgroundColor = 'rgba(255,255,255,0.9)';
                setTimeout(() => {
                    span.style.backgroundColor = originalBg;
                }, 150);
            } else {
                // 复杂选择（跨多个元素），采用分段高亮方法
                highlightComplexSelection(originalRange, bgColor, border);
            }
            
            // 清除选择
            selection.removeAllRanges();
            console.log('已高亮文本');
            
        } catch (e) {
            console.error('高亮操作失败:', e);
            
            // 尝试使用备用的分段高亮方法
            try {
                const range = selection.getRangeAt(0);
                highlightComplexSelection(range, bgColor, border);
                selection.removeAllRanges();
                console.log('使用备用方法成功高亮文本');
            } catch (backupError) {
                console.error('备用高亮方法也失败:', backupError);
                showToast('无法高亮选中的内容，请尝试选择更简单的文本块');
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
                span.style.borderBottom = border;
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