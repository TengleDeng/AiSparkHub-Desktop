// 等待DOM完全加载
document.addEventListener('DOMContentLoaded', function() {
    initThemeToggle();
});

// 主题切换功能
function initThemeToggle() {
    const themeToggleBtn = document.getElementById('theme-toggle-btn');
    const htmlElement = document.documentElement;
    
    // 检查本地存储中是否有保存的主题偏好
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme) {
        htmlElement.className = savedTheme;
        updateChartColors();
    }
    
    // 监听主题切换按钮点击
    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', function() {
            if (htmlElement.classList.contains('light-theme')) {
                htmlElement.className = 'dark-theme';
                localStorage.setItem('theme', 'dark-theme');
            } else {
                htmlElement.className = 'light-theme';
                localStorage.setItem('theme', 'light-theme');
            }
            
            // 更新图表颜色
            updateChartColors();
        });
    }
}

// 更新图表颜色以适应当前主题
function updateChartColors() {
    const timeChartCanvas = document.getElementById('timeChart');
    if (!timeChartCanvas) return;
    
    // 尝试获取图表实例
    try {
        const chart = Chart.getChart(timeChartCanvas);
        if (!chart) return;
        
        const isLightTheme = document.documentElement.classList.contains('light-theme');
        
        // 更新图表文字颜色
        const textColor = isLightTheme ? '#2E3440' : '#ECEFF4';
        const gridColor = isLightTheme ? 'rgba(76, 86, 106, 0.1)' : 'rgba(236, 239, 244, 0.1)';
        
        chart.options.plugins.legend.labels.color = textColor;
        chart.options.plugins.title.color = textColor;
        chart.options.scales.x.ticks.color = isLightTheme ? '#4C566A' : '#D8DEE9';
        chart.options.scales.y.ticks.color = isLightTheme ? '#4C566A' : '#D8DEE9';
        chart.options.scales.x.grid.color = gridColor;
        chart.options.scales.y.grid.color = gridColor;
        
        chart.update();
    } catch (error) {
        console.log('图表还未初始化或无法获取');
    }
} 