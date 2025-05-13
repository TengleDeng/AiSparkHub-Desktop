# AiSparkHub 参赛展示网站

本网站是为了参加"AI落地实干案例"挑战赛而创建的展示页面，用于展示AiSparkHub多AI对话桌面应用的功能和价值。

## 目录结构

```
AiSparkHub-Website/
├── index.html       # 主页面
├── css/             # 样式文件
│   └── styles.css   # 主样式表
├── js/              # JavaScript文件
│   └── main.js      # 主脚本文件
├── images/          # 图片资源目录
│   ├── logo.png     # 应用Logo
│   ├── app-screenshot.png  # 应用截图
│   └── ... 其他图片资源
└── README.md        # 本文档
```

## 功能特点

- 响应式设计，适配各种设备
- 暗色主题，符合应用程序的设计风格
- 交互式图表展示效率对比
- 平滑滚动和动画效果
- 图片懒加载优化性能

## 使用方法

1. **本地预览**

   只需用浏览器打开`index.html`文件即可在本地预览网站。

   ```
   双击 index.html
   ```

2. **发布到Web服务器**

   将整个文件夹上传到Web服务器即可部署网站。

## 自定义修改

- **更换图片**: 将对应的图片文件放入`images`目录，确保文件名匹配
- **修改内容**: 编辑`index.html`文件中的相应部分
- **调整样式**: 修改`css/styles.css`文件中的样式定义
- **添加功能**: 在`js/main.js`中编写额外的JavaScript代码

## 图片资源说明

网站需要以下图片资源：

1. logo.png - AiSparkHub应用程序Logo
2. app-screenshot.png - 主页显示的应用截图
3. demo-screenshot.png - 功能演示部分的截图
4. case1.png - 内容创作案例截图
5. case2.png - 研究分析案例截图
6. case3.png - 代码优化案例截图
7. guide1.png - 安装步骤截图
8. guide2.png - 配置步骤截图
9. guide3.png - 使用步骤截图

## 技术栈

- HTML5
- CSS3 (变量、Flexbox、Grid、响应式设计)
- JavaScript (原生ES6+)
- Chart.js (数据可视化)
- Font Awesome (图标)

## 注意事项

- 网站使用了现代CSS和JavaScript特性，建议使用最新版本的Chrome、Firefox、Safari或Edge浏览器
- 为获得最佳效果，请确保添加所有所需的图片资源
- 图表数据可在js/main.js文件中根据实际情况进行修改 