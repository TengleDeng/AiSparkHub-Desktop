// 等待DOM完全加载
document.addEventListener('DOMContentLoaded', function() {
    // 初始化图表
    initCharts();
    
    // 添加导航栏滚动效果
    initScrollEffect();
    
    // 添加平滑滚动
    initSmoothScroll();
    
    // 添加图片懒加载
    initLazyLoading();

    // 初始化滚动动画
    initScrollAnimations();
});

// 初始化图表
function initCharts() {
    // 获取图表容器
    const timeChartCanvas = document.getElementById('timeChart');
    
    if (timeChartCanvas) {
        // 创建时间对比图表
        const timeChart = new Chart(timeChartCanvas, {
            type: 'bar',
            data: {
                labels: ['内容创作', '文献研究', '代码优化', '多平台协作', '数据分析'],
                datasets: [
                    {
                        label: '传统方式',
                        data: [45, 60, 40, 50, 55],
                        backgroundColor: '#4C566A',
                        borderColor: '#4C566A',
                        borderWidth: 1
                    },
                    {
                        label: '使用AiSparkHub',
                        data: [15, 25, 20, 18, 22],
                        backgroundColor: '#88C0D0',
                        borderColor: '#88C0D0',
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            color: '#ECEFF4'
                        }
                    },
                    title: {
                        display: true,
                        text: '完成任务时间对比 (分钟)',
                        color: '#ECEFF4',
                        font: {
                            size: 16
                        }
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false
                    }
                },
                scales: {
                    x: {
                        grid: {
                            color: 'rgba(236, 239, 244, 0.1)'
                        },
                        ticks: {
                            color: '#D8DEE9'
                        }
                    },
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(236, 239, 244, 0.1)'
                        },
                        ticks: {
                            color: '#D8DEE9'
                        }
                    }
                }
            }
        });
    }
}

// 导航栏滚动效果
function initScrollEffect() {
    // 获取导航元素
    const header = document.querySelector('header');
    
    // 监听滚动事件
    window.addEventListener('scroll', () => {
        if (window.scrollY > 50) {
            header.style.backgroundColor = 'rgba(34, 39, 48, 0.95)';
            header.style.boxShadow = '0 4px 20px rgba(0, 0, 0, 0.3)';
        } else {
            header.style.backgroundColor = '#222730';
            header.style.boxShadow = '0 2px 10px rgba(0, 0, 0, 0.2)';
        }
    });
    
    // 更新活动导航项
    updateActiveNavItem();
}

// 平滑滚动
function initSmoothScroll() {
    // 获取所有导航链接
    const navLinks = document.querySelectorAll('nav a, .hero-buttons a, .footer-links a');
    
    // 为每个链接添加点击事件
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            // 检查链接是否为锚点
            const href = this.getAttribute('href');
            if (href.startsWith('#') && href !== '#') {
                e.preventDefault();
                
                // 获取目标元素
                const targetId = href.substring(1);
                const targetElement = document.getElementById(targetId);
                
                if (targetElement) {
                    // 计算滚动位置（考虑固定导航栏的高度）
                    const headerHeight = document.querySelector('header').offsetHeight;
                    const targetPosition = targetElement.getBoundingClientRect().top + window.pageYOffset;
                    const offsetPosition = targetPosition - headerHeight;
                    
                    // 平滑滚动
                    window.scrollTo({
                        top: offsetPosition,
                        behavior: 'smooth'
                    });
                    
                    // 更新URL
                    history.pushState(null, null, href);
                }
            }
        });
    });
}

// 更新活动导航项
function updateActiveNavItem() {
    const sections = document.querySelectorAll('section[id]');
    const navItems = document.querySelectorAll('nav ul li a');
    
    window.addEventListener('scroll', () => {
        let current = '';
        const headerHeight = document.querySelector('header').offsetHeight;
        
        sections.forEach(section => {
            const sectionTop = section.offsetTop - headerHeight - 100;
            const sectionHeight = section.offsetHeight;
            
            if (window.scrollY >= sectionTop && window.scrollY < sectionTop + sectionHeight) {
                current = section.getAttribute('id');
            }
        });
        
        navItems.forEach(item => {
            item.classList.remove('active');
            if (item.getAttribute('href') === `#${current}`) {
                item.classList.add('active');
            }
        });
    });
}

// 懒加载图片
function initLazyLoading() {
    // 获取所有带有data-src属性的图片
    const lazyImages = document.querySelectorAll('img[data-src]');
    
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.removeAttribute('data-src');
                    imageObserver.unobserve(img);
                }
            });
        });
        
        lazyImages.forEach(img => {
            imageObserver.observe(img);
        });
    } else {
        // 回退方案：简单地加载所有图片
        lazyImages.forEach(img => {
            img.src = img.dataset.src;
            img.removeAttribute('data-src');
        });
    }
}

// 滚动动画
function initScrollAnimations() {
    const animatedElements = document.querySelectorAll('.animate-on-scroll');
    
    if ('IntersectionObserver' in window) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    // 根据不同的元素类型添加不同的动画类
                    if (entry.target.classList.contains('feature-card') || 
                        entry.target.classList.contains('stat-card') || 
                        entry.target.classList.contains('guide-step')) {
                        entry.target.classList.add('fade-in-up');
                    } else if (entry.target.classList.contains('case-card')) {
                        entry.target.classList.add('fade-in-left');
                    } else if (entry.target.classList.contains('comparison-stat')) {
                        entry.target.classList.add('fade-in-right');
                    } else {
                        // 默认动画
                        entry.target.classList.add('fade-in-up');
                    }
                    
                    // 停止观察已经显示的元素
                    observer.unobserve(entry.target);
                }
            });
        }, {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        });
        
        animatedElements.forEach(element => {
            observer.observe(element);
        });
    } else {
        // 如果浏览器不支持IntersectionObserver，直接显示所有元素
        animatedElements.forEach(element => {
            element.style.opacity = 1;
        });
    }
}

// 添加播放按钮点击事件
const playButton = document.querySelector('.play-button');
if (playButton) {
    playButton.addEventListener('click', function(e) {
        e.preventDefault();
        alert('演示视频功能尚未实现。这里将播放AiSparkHub演示视频。');
    });
}

// 当页面加载完成后，初始化一次滚动动画
window.addEventListener('load', () => {
    // 触发一次滚动事件，以初始化当前视口内的动画
    window.dispatchEvent(new Event('scroll'));
}); 