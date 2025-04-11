// Orama Cloud 配置 - 使用与原应用相同的配置
const ORAMA_CONFIG = {
    endpoint: "https://cloud.orama.run/v1/indexes/tengledeng-vmoxv8",
    apiKey: "HFsJsLE3dwn6StXKYcgap3ZIHbGHu9bY"
};

// 搜索类型枚举
const SearchMode = {
    ORAMA_CLOUD: 'orama_cloud',
    ORAMA_CLOUD_KEYWORD: 'orama_cloud_keyword',
    ORAMA_CLOUD_VECTOR: 'orama_cloud_vector'
};

// 显示错误信息
function showError(message) {
    const errorDiv = document.getElementById('error');
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
    setTimeout(() => {
        errorDiv.style.display = 'none';
    }, 3000);
}

// 清除错误信息
function clearError() {
    const errorDiv = document.getElementById('error');
    errorDiv.style.display = 'none';
}

// 格式化时间戳
function formatTimestamp(timestamp) {
    if (!timestamp) return '未知时间';
    // 如果时间戳小于 100亿，说明是秒级时间戳，需要转换为毫秒级
    if (timestamp < 10000000000) {
        timestamp = timestamp * 1000;
    }
    const date = new Date(timestamp);
    return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
    });
}

// 高亮关键词的函数
function highlightKeywords(text, searchTerm) {
    if (!searchTerm) return text;
    const terms = searchTerm.trim().split(/\s+/);
    let highlightedText = text;
    
    terms.forEach(term => {
        if (!term) return;
        const regex = new RegExp(term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi');
        highlightedText = highlightedText.replace(regex, match => `<span style="background-color: #ffd54f; padding: 0 2px; border-radius: 2px;">${match}</span>`);
    });
    
    return highlightedText;
}

// 清除搜索结果
function clearResults() {
    const resultsDiv = document.getElementById('results');
    resultsDiv.innerHTML = '';
    document.body.classList.remove('has-results');
}

// 渲染搜索结果
function _renderResults(results, searchTerm) {
    const resultsDiv = document.getElementById('results');
    document.body.classList.add('has-results');
    
    if (!results || !results.hits || results.hits.length === 0) {
        resultsDiv.innerHTML = '<div style="text-align: center; padding: 20px; color: #70757a;">未找到相关结果</div>';
        return;
    }

    const resultCount = results.hits.length;

    let html = `
        <div class="sort-container">
            找到 ${resultCount} 个结果
            <select id="sortSelect" onchange="sortResults()" style="margin-left: 10px;">
                <option value="relevance">按相关度排序</option>
                <option value="time">按时间排序</option>
            </select>
        </div>
        <div id="resultsContainer"></div>
    `;

    resultsDiv.innerHTML = html;
    const resultsContainer = document.getElementById('resultsContainer');

    // 存储原始结果用于排序
    window.searchResults = results.hits;

    results.hits.forEach(hit => {
        const doc = hit.document;
        const resultItem = document.createElement('div');
        resultItem.className = 'result-item';
        
        // 显示标题
        const titleElement = document.createElement('h3');
        titleElement.textContent = doc.title || '无标题';
        if (searchTerm) {
            titleElement.innerHTML = highlightKeywords(titleElement.textContent, searchTerm);
        }
        resultItem.appendChild(titleElement);

        // 显示文件路径（在web版本中，路径只是展示不可点击）
        if (doc.path) {
            const pathElement = document.createElement('p');
            pathElement.className = 'file-link';
            pathElement.textContent = doc.path;
            resultItem.appendChild(pathElement);
        }

        // 显示内容
        if (doc.content) {
            const contentElement = document.createElement('p');
            contentElement.className = 'content';
            contentElement.textContent = doc.content;
            if (searchTerm) {
                contentElement.innerHTML = highlightKeywords(contentElement.textContent, searchTerm);
            }
            resultItem.appendChild(contentElement);
        }

        // 显示元数据
        const metaElement = document.createElement('div');
        metaElement.className = 'meta-info';
        
        // 显示相关度分数
        const scoreElement = document.createElement('span');
        scoreElement.textContent = `相关度: ${hit.score.toFixed(2)} | `;
        metaElement.appendChild(scoreElement);

        // 显示创建时间
        if (doc.ctime) {
            const ctimeElement = document.createElement('span');
            ctimeElement.textContent = `创建时间: ${formatTimestamp(doc.ctime)} | `;
            metaElement.appendChild(ctimeElement);
        }

        // 显示修改时间
        if (doc.mtime) {
            const mtimeElement = document.createElement('span');
            mtimeElement.textContent = `修改时间: ${formatTimestamp(doc.mtime)}`;
            metaElement.appendChild(mtimeElement);
        }

        resultItem.appendChild(metaElement);
        resultsContainer.appendChild(resultItem);
    });
}

// 排序结果
function sortResults() {
    const sortSelect = document.getElementById('sortSelect');
    const sortBy = sortSelect.value;
    const hits = [...window.searchResults];

    if (sortBy === 'time') {
        hits.sort((a, b) => {
            // 优先使用mtime，如果没有则使用ctime
            const timeA = a.document.mtime || a.document.ctime || 0;
            const timeB = b.document.mtime || b.document.ctime || 0;
            return timeB - timeA;
        });
    } else {
        // 默认按相关度排序
        hits.sort((a, b) => b.score - a.score);
    }

    const resultsContainer = document.getElementById('resultsContainer');
    resultsContainer.innerHTML = '';
    
    hits.forEach(hit => {
        const doc = hit.document;
        const resultItem = document.createElement('div');
        resultItem.className = 'result-item';
        
        // 显示标题
        const titleElement = document.createElement('h3');
        titleElement.textContent = doc.title || '无标题';
        resultItem.appendChild(titleElement);

        // 显示文件路径
        if (doc.path) {
            const pathElement = document.createElement('p');
            pathElement.className = 'file-link';
            pathElement.textContent = doc.path;
            resultItem.appendChild(pathElement);
        }

        // 显示内容
        if (doc.content) {
            const contentElement = document.createElement('p');
            contentElement.className = 'content';
            contentElement.textContent = doc.content;
            resultItem.appendChild(contentElement);
        }

        // 显示元数据
        const metaElement = document.createElement('div');
        metaElement.className = 'meta-info';
        
        // 显示相关度分数
        const scoreElement = document.createElement('span');
        scoreElement.textContent = `相关度: ${hit.score.toFixed(2)} | `;
        metaElement.appendChild(scoreElement);

        // 显示创建时间
        if (doc.ctime) {
            const ctimeElement = document.createElement('span');
            ctimeElement.textContent = `创建时间: ${formatTimestamp(doc.ctime)} | `;
            metaElement.appendChild(ctimeElement);
        }

        // 显示修改时间
        if (doc.mtime) {
            const mtimeElement = document.createElement('span');
            mtimeElement.textContent = `修改时间: ${formatTimestamp(doc.mtime)}`;
            metaElement.appendChild(mtimeElement);
        }

        resultItem.appendChild(metaElement);
        resultsContainer.appendChild(resultItem);
    });
}

// 准备搜索参数
function prepareSearchParams(query, searchType, limit = 10) {
    const params = {
        term: query,
        limit: limit
    };
    
    switch (searchType) {
        case 'vector':
            params.mode = 'vector';
            break;
        case 'keyword':
            params.mode = 'fulltext';
            break;
        case 'hybrid':
        default:
            params.mode = 'hybrid';
            break;
    }
    
    return params;
}

// 使用ES模块导入的客户端进行搜索
async function searchWithClient(params) {
    try {
        console.log("使用ES模块客户端搜索:", params);
        // 检查客户端是否可用
        if (!window.oramaClient) {
            throw new Error("Orama客户端未加载，请刷新页面重试");
        }
        
        const results = await window.oramaClient.search(params);
        console.log("客户端搜索结果:", results);
        
        // 将客户端返回的结果格式转换为标准格式
        if (results && typeof results === 'object') {
            if (!results.hits && results.data) {
                return {
                    hits: results.data.map(item => ({
                        document: item.document,
                        score: item.score
                    }))
                };
            }
        }
        
        return results;
    } catch (error) {
        console.error("搜索失败:", error);
        throw error;
    }
}

// 根据搜索模式获取搜索类型
function getSearchTypeForMode(mode) {
    switch (mode) {
        case SearchMode.ORAMA_CLOUD_VECTOR:
            return 'vector';
        case SearchMode.ORAMA_CLOUD_KEYWORD:
            return 'keyword';
        case SearchMode.ORAMA_CLOUD:
        default:
            return 'hybrid';
    }
}

// 这个performSearch函数会被index.html中的同名函数取代，
// 为了避免冲突，我们重命名它并让它调用index.html中的函数
async function _performSearch() {
    // 如果index.html定义了executeOramaSearch函数，我们就用它
    if (typeof window.executeOramaSearch === 'function') {
        // 获取搜索类型和搜索词
        const searchType = document.getElementById('searchType').value;
        const searchTerm = document.getElementById('searchInput').value;
        
        // 调用index.html中定义的函数
        window.performSearch();
    } else {
        // 原始实现，用于备份
        const searchType = document.getElementById('searchType').value;
        const searchTerm = document.getElementById('searchInput').value;
        
        if (!searchTerm) {
            showError('请输入搜索关键词');
            clearResults();
            return;
        }

        clearError();
        
        try {
            // 显示加载状态
            const searchBtn = document.querySelector('.search-button');
            if (searchBtn) {
                searchBtn.disabled = true;
                searchBtn.textContent = "搜索中...";
            }
            
            // 保存到搜索历史
            saveToHistory(searchTerm);

            // 获取搜索类型
            const searchMode = getSearchTypeForMode(searchType);
            console.log(`开始搜索:`, searchTerm);
            
            // 准备搜索参数
            const searchParams = prepareSearchParams(searchTerm, searchMode, 10);
            
            // 执行搜索
            let results = await searchWithClient(searchParams);
            
            // 恢复按钮状态
            if (searchBtn) {
                searchBtn.disabled = false;
                searchBtn.textContent = "搜索";
            }
            
            // 渲染结果
            _renderResults(results, searchTerm);
        } catch (error) {
            console.error('搜索过程出错:', error);
            showError(`搜索出错: ${error.message}`);
            
            // 恢复按钮状态
            const searchBtn = document.querySelector('.search-button');
            if (searchBtn) {
                searchBtn.disabled = false;
                searchBtn.textContent = "搜索";
            }
        }
    }
}

// 返回首页
function goHome() {
    document.getElementById('searchInput').value = '';
    clearResults();
    document.getElementById('searchInput').focus();
}

// 励志金句功能
// 默认金句列表
const DEFAULT_QUOTES = [
    "知识就是力量，行动才能改变命运",
    "成功不是偶然，而是日积月累的结果",
    "每一次尝试都是成长的机会",
    "坚持不一定成功，放弃一定失败",
    "当你感到疲惫时，记住为什么开始",
    "把每一次挫折当作成功的垫脚石",
    "伟大的成就，来自不倦的努力",
    "学会享受孤独，因为知识的获取常常是一个人的旅程",
    "你所知道的东西远不如你如何去学习重要",
    "今天你不为自己投资，明天你就为自己贫穷买单"
];

// 金句相关状态
let quotesList = [];
let quoteChangeInterval = 60000; // 默认为1分钟
let quoteTimer = null;

// 更新日期时间显示
function updateDateTime() {
    const datetimeElement = document.getElementById('datetimeDisplay');
    if (!datetimeElement) return;
    
    const now = new Date();
    const dateOptions = { year: 'numeric', month: '2-digit', day: '2-digit', weekday: 'short' };
    const timeOptions = { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false };
    
    const dateStr = now.toLocaleDateString('zh-CN', dateOptions);
    const timeStr = now.toLocaleTimeString('zh-CN', timeOptions);
    
    datetimeElement.textContent = `${timeStr} | ${dateStr}`;
}

// 初始化金句功能
function initializeQuotes() {
    // 从localStorage加载金句列表
    const savedQuotes = localStorage.getItem('motivationalQuotes');
    if (savedQuotes) {
        quotesList = JSON.parse(savedQuotes);
    } else {
        quotesList = [...DEFAULT_QUOTES];
        localStorage.setItem('motivationalQuotes', JSON.stringify(quotesList));
    }
    
    // 从localStorage加载切换间隔
    const savedInterval = localStorage.getItem('quoteChangeInterval');
    if (savedInterval) {
        quoteChangeInterval = parseInt(savedInterval, 10);
    }
    
    // 显示第一条金句
    refreshQuote();
    
    // 设置定时切换
    startQuoteTimer();
    
    // 显示并定时更新日期时间
    updateDateTime();
    setInterval(updateDateTime, 1000);
}

// 显示随机金句
function refreshQuote() {
    if (quotesList.length === 0) return;
    
    const quoteElement = document.getElementById('motivationalQuote');
    if (!quoteElement) return;
    
    // 获取当前金句，确保不重复
    const currentQuote = quoteElement.textContent;
    let newQuote = currentQuote;
    
    // 如果只有一条金句，直接使用
    if (quotesList.length === 1) {
        newQuote = quotesList[0];
    } else {
        // 确保不重复，随机选择新的金句
        while (newQuote === currentQuote) {
            const randomIndex = Math.floor(Math.random() * quotesList.length);
            newQuote = quotesList[randomIndex];
        }
    }
    
    // 添加淡入淡出效果
    quoteElement.style.opacity = '0';
    
    setTimeout(() => {
        quoteElement.textContent = newQuote;
        quoteElement.style.opacity = '1';
    }, 300);
}

// 启动金句定时切换
function startQuoteTimer() {
    // 清除现有定时器
    if (quoteTimer) {
        clearInterval(quoteTimer);
    }
    
    // 设置新定时器
    quoteTimer = setInterval(refreshQuote, quoteChangeInterval);
}

// 切换金句设置弹窗
function toggleQuoteSettings() {
    const modal = document.getElementById('quoteSettingsModal');
    if (!modal) return;
    
    const isVisible = modal.style.display === 'block';
    
    if (!isVisible) {
        // 显示弹窗前，先填充当前设置
        const quotesListArea = document.getElementById('quotesListArea');
        if (quotesListArea) {
            quotesListArea.value = quotesList.join('\n');
        }
        
        const intervalSelect = document.getElementById('quoteChangeInterval');
        if (intervalSelect) {
            for (let i = 0; i < intervalSelect.options.length; i++) {
                if (intervalSelect.options[i].value == quoteChangeInterval.toString()) {
                    intervalSelect.selectedIndex = i;
                    break;
                }
            }
        }
        
        modal.style.display = 'block';
    } else {
        modal.style.display = 'none';
    }
}

// 保存金句设置
function saveQuotes() {
    const quotesListArea = document.getElementById('quotesListArea');
    const intervalSelect = document.getElementById('quoteChangeInterval');
    
    if (!quotesListArea || !intervalSelect) return;
    
    // 解析并保存金句列表
    const quotesText = quotesListArea.value.trim();
    if (quotesText) {
        quotesList = quotesText.split('\n')
            .map(quote => quote.trim())
            .filter(quote => quote.length > 0);
    } else {
        quotesList = [...DEFAULT_QUOTES];
    }
    
    // 保存到localStorage
    localStorage.setItem('motivationalQuotes', JSON.stringify(quotesList));
    
    // 保存切换间隔设置
    quoteChangeInterval = parseInt(intervalSelect.value, 10);
    localStorage.setItem('quoteChangeInterval', quoteChangeInterval.toString());
    
    // 重启定时器
    startQuoteTimer();
    
    // 刷新显示
    refreshQuote();
    
    // 关闭弹窗
    toggleQuoteSettings();
}

// 搜索历史管理
let searchHistory = JSON.parse(localStorage.getItem('searchHistory') || '[]');

// 保存搜索历史
function saveToHistory(term) {
    if (!term) return;
    searchHistory = [term, ...searchHistory.filter(t => t !== term)].slice(0, 10);
    localStorage.setItem('searchHistory', JSON.stringify(searchHistory));
}

// 显示搜索历史
function showSearchHistory() {
    const searchHistoryDiv = document.getElementById('searchHistory');
    if (searchHistory.length === 0 || !searchHistoryDiv) return;
    
    searchHistoryDiv.innerHTML = '';
    searchHistory.slice(0, 5).forEach(term => {
        const item = document.createElement('div');
        item.className = 'history-item';
        item.innerHTML = `<i class="fas fa-history"></i>${term}`;
        item.onclick = () => {
            document.getElementById('searchInput').value = term;
            performSearch();
        };
        searchHistoryDiv.appendChild(item);
    });
    searchHistoryDiv.style.display = 'block';
    document.querySelector('.search-box').classList.add('show-history');
}

// 隐藏搜索历史
function hideSearchHistory() {
    const searchHistoryDiv = document.getElementById('searchHistory');
    if (!searchHistoryDiv) return;
    
    searchHistoryDiv.style.display = 'none';
    const searchBox = document.querySelector('.search-box');
    if (searchBox) {
        searchBox.classList.remove('show-history');
    }
}

// 初始化事件监听
document.addEventListener('DOMContentLoaded', () => {
    console.log("页面加载完成，初始化应用");
    
    // 初始化励志金句功能
    initializeQuotes();
    
    // 搜索框事件绑定
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        // 搜索框焦点事件
        searchInput.addEventListener('focus', () => {
            if (searchInput.value === '') {
                showSearchHistory();
            }
        });

        // 搜索框鼠标进入事件
        searchInput.addEventListener('mouseenter', () => {
            if (!document.body.classList.contains('has-results') || searchInput.value === '') {
                showSearchHistory();
            }
        });
        
        // 搜索框输入事件
        searchInput.addEventListener('input', () => {
            if (searchInput.value === '') {
                showSearchHistory();
            } else {
                hideSearchHistory();
            }
        });
        
        // 回车键搜索 - 使用index.html中定义的performSearch
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                if (typeof window.performSearch === 'function') {
                    window.performSearch();
                } else {
                    _performSearch();
                }
            }
        });
    }
    
    // 搜索框和历史记录的鼠标离开事件
    const searchContainer = document.querySelector('.search-wrapper');
    if (searchContainer) {
        searchContainer.addEventListener('mouseleave', () => {
            hideSearchHistory();
        });
    }
    
    // 点击其他地方时隐藏搜索历史
    document.addEventListener('click', (e) => {
        const searchHistoryDiv = document.getElementById('searchHistory');
        if (searchHistoryDiv && !searchHistoryDiv.contains(e.target) && e.target !== searchInput) {
            hideSearchHistory();
        }
    });
    
    // 暴露关键函数到全局，以便在index.html中使用
    window.searchWithClient = searchWithClient;
    window.renderResults = _renderResults;
    window.clearResults = clearResults;
}); 