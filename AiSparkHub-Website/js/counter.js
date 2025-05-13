// 访问计数器功能
document.addEventListener('DOMContentLoaded', function() {
    initVisitorCounter();
});

// 初始化访问计数器
function initVisitorCounter() {
    // 本地存储计数器
    let visitCount = localStorage.getItem('visitCount') || 0;
    visitCount = parseInt(visitCount) + 1;
    localStorage.setItem('visitCount', visitCount);
    
    // 更新计数器显示
    const counterElement = document.getElementById('visitor-counter');
    if (counterElement) {
        counterElement.textContent = visitCount;
    }
    
    // 更新总计数器 (如果使用了Firebase或其他服务)
    updateTotalCounter();
}

// 更新总访问计数（如果有远程计数服务）
function updateTotalCounter() {
    const totalCounterElement = document.getElementById('total-counter');
    if (!totalCounterElement) return;
    
    // 以下是模拟数据，实际项目中应该使用真实的API调用
    const randomIncrement = Math.floor(Math.random() * 5) + 1;
    let totalCount = localStorage.getItem('simulatedTotalCount') || 1000;
    totalCount = parseInt(totalCount) + randomIncrement;
    localStorage.setItem('simulatedTotalCount', totalCount);
    
    // 格式化数字显示（添加千位分隔符）
    totalCounterElement.textContent = totalCount.toLocaleString();
}

// 如果需要实时更新（例如多标签页同步），可以添加以下代码
window.addEventListener('storage', function(e) {
    if (e.key === 'visitCount' || e.key === 'simulatedTotalCount') {
        const counterElement = document.getElementById('visitor-counter');
        const totalCounterElement = document.getElementById('total-counter');
        
        if (e.key === 'visitCount' && counterElement) {
            counterElement.textContent = e.newValue;
        }
        
        if (e.key === 'simulatedTotalCount' && totalCounterElement) {
            totalCounterElement.textContent = parseInt(e.newValue).toLocaleString();
        }
    }
});
