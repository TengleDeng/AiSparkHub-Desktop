# AiSparkHub 参赛网站使用说明

## 概述

本文档提供了如何使用和自定义AiSparkHub参赛展示网站的详细说明。这个网站是为了参加"AI落地实干案例"挑战赛而创建的，用于展示AiSparkHub多AI对话桌面应用的功能和价值。

## 准备工作

在使用网站前，您需要准备以下图片资源：

1. **logo.png** - AiSparkHub应用程序Logo (建议尺寸: 150x40px)
2. **app-screenshot.png** - 主页显示的应用截图 (建议尺寸: 1200x800px)
3. **demo-screenshot.png** - 功能演示部分的截图 (建议尺寸: 800x600px)
4. **case1.png** - 内容创作案例截图 (建议尺寸: 600x400px)
5. **case2.png** - 研究分析案例截图 (建议尺寸: 600x400px)
6. **case3.png** - 代码优化案例截图 (建议尺寸: 600x400px)
7. **guide1.png** - 安装步骤截图 (建议尺寸: 600x400px)
8. **guide2.png** - 配置步骤截图 (建议尺寸: 600x400px)
9. **guide3.png** - 使用步骤截图 (建议尺寸: 600x400px)

将这些图片放在`images`文件夹中。

## 使用方法

### 本地预览

1. 将所有图片文件放入`images`目录
2. 使用浏览器打开`index.html`文件进行预览

```
双击 index.html 文件
```

### 部署到Web服务器

1. 将整个`AiSparkHub-Website`文件夹上传到您的Web服务器
2. 确保保持文件结构不变

## 自定义内容

### 修改文字内容

编辑`index.html`文件中的文本内容。主要区域包括：

- 头部标题和导航
- 主页标语
- 功能描述
- 案例研究
- 效率对比数据
- 使用指南
- 页脚信息

### 修改图表数据

编辑`js/main.js`文件中的图表数据：

```javascript
// 约在第29-32行
datasets: [
    {
        label: '传统方式',
        data: [45, 60, 40, 50, 55], // 修改这里的数据
        backgroundColor: '#4C566A',
        borderColor: '#4C566A',
        borderWidth: 1
    },
    {
        label: '使用AiSparkHub',
        data: [15, 25, 20, 18, 22], // 修改这里的数据
        backgroundColor: '#88C0D0',
        borderColor: '#88C0D0',
        borderWidth: 1
    }
]
```

### 修改样式

编辑`css/styles.css`文件可以修改网站的视觉风格：

- 颜色：修改`:root`部分的颜色变量
- 字体：修改`:root`部分的字体变量
- 布局：修改各个部分的布局代码
- 动画：修改动画相关的CSS代码

## 兼容性说明

- 网站使用了现代CSS和JavaScript特性，建议使用最新版本的Chrome、Firefox、Safari或Edge浏览器
- 图片懒加载功能在旧浏览器上有兼容性处理
- 动画效果在所有现代浏览器上都能正常工作

## 性能优化

网站已经实施了以下性能优化措施：

1. **图片懒加载** - 只有当图片进入视口时才会加载
2. **CSS优化** - 使用CSS变量减少重复代码
3. **平滑滚动** - 使用原生JavaScript实现平滑滚动，减少外部依赖
4. **响应式设计** - 网站在各种设备上都能良好显示

## 常见问题

### 图片没有显示

- 检查图片是否放在正确的文件夹(`images/`)
- 确保图片文件名与HTML中的引用一致
- 检查图片格式是否是常见的Web格式(如PNG, JPG, WEBP)

### 字体或图标不显示

- 确保网站能够访问CDN(https://cdnjs.cloudflare.com/)
- 尝试将字体和图标文件下载到本地使用

### 图表不显示

- 确保网站能够访问CDN(https://cdn.jsdelivr.net/)
- 检查浏览器控制台是否有JavaScript错误 