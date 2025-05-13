# AiSparkHub - 多AI对话桌面应用

## 项目概述
AiSparkHub 是一个基于 Python 的桌面应用程序，旨在为用户提供与多个 AI 同时对话的交互体验。程序支持双屏幕和单屏幕两种显示模式，支持多标签页浏览网页、文件夹浏览、提示词输入及历史记录管理。核心功能是通过统一的提示词输入区与多个 AI 交互，并将交互记录存储在 libSQL 数据库中。

## 主要功能
- 双屏幕和单屏幕两种显示模式
- 多标签页浏览，支持同时与多个AI对话
- 文件夹浏览器，方便打开本地文件
- 提示词输入区，一键向多个AI发送提示词
- 提示词历史记录管理，方便复用之前的提示词
- 采用类似Obsidian的界面风格

## 技术栈
- Python 3.11
- PyQt 6.5.0
- libSQL数据库
- qtawesome图标库

## 安装与运行
1. 确保已安装conda环境管理系统
2. 运行安装脚本：
   ```
   setup.bat
   ```
   该脚本将自动创建conda环境并安装所需依赖
   
3. 运行应用：
   ```
   run.bat
   ```

## 项目结构
```
AiSparkHub-Desktop/
├── main.py                    # 应用入口点
├── requirements.txt           # Python依赖列表
├── environment.yml            # Conda环境配置
├── setup.bat                  # Windows安装脚本
├── run.bat                    # 启动应用脚本
├── README.md                  # 项目说明文档
├── .gitignore                 # Git忽略文件
├── app/                       # 应用主目录
│   ├── __init__.py
│   ├── config.py              # 配置文件
│   ├── assets/                # 静态资源
│   ├── components/            # UI组件
│   ├── models/                # 数据模型
│   ├── controllers/           # 控制器
│   └── utils/                 # 工具函数
└── data/                      # 应用数据存储
```

## 开发者指南
请参考程序设计说明书了解详细的设计思路和实现细节。

## 开发环境设置
1. 克隆仓库：
   ```
   git clone https://github.com/yourusername/AiSparkHub-Desktop.git
   ```

2. 创建开发环境：
   ```
   cd AiSparkHub-Desktop
   conda env create -f environment.yml
   ```

3. 激活环境：
   ```
   conda activate aisparkhub
   ```

4. 运行应用：
   ```
   python main.py
   ```

## 许可证
MIT

---

## 程序设计说明书

## 项目名称
**AiSparkHub - 多 AI 对话桌面应用**

## 项目概述
AiSparkHub 是一个基于 Python 的桌面应用程序，旨在为用户提供与多个 AI 同时对话的交互体验。程序支持双屏幕和单屏幕两种显示模式，支持多标签页浏览网页、文件夹浏览、提示词输入及历史记录管理。核心功能是通过统一的提示词输入区与多个 AI 交互，并将交互记录存储在 libSQL 数据库中。

---

## 功能需求

### 1. 窗口设计
#### 1.1 双屏幕模式
- **窗口 1**（主窗口，类似 Chrome 浏览器）
  - 多标签页设计，默认第一个标签页为 AI 对话页面。
  - AI 对话页面支持并列显示多个 AI 网页（例如 ChatGPT、DeepSeek 等），用户可设定并列显示的 AI 数量。
  - 其他标签页支持打开任意网页，包含地址栏。
- **窗口 2**（辅助窗口）
  - 左侧：文件夹浏览区，支持文件系统导航。
  - 中间：提示词输入区，支持多行文本输入。
  - 右侧：提示词历史记录边栏，支持查看、搜索和复用历史提示词。

#### 1.2 单屏幕模式
- 两个窗口合并为一个窗口：
  - 窗口 1 显示在上方。
  - 窗口 2 显示在下方。
- 支持窗口分离，用户可拖动分离为独立窗口。

### 2. 核心功能
#### 2.1 提示词通信
- 用户在窗口 2 的提示词输入区输入文本后，点击"发送"按钮，文本将同时发送到窗口 1 中所有 AI 网页的提示词输入框，并触发提交。
- 支持 AI 网页的自动填充和提交（通过模拟用户输入或调用 API）。

#### 2.2 数据存储
- 使用 libSQL 数据库存储提示词历史记录。
- 每条记录包含：提示词内容、发送时间、目标 AI 列表。
- 历史记录支持在窗口 2 的右侧边栏查看和复用。

#### 2.3 界面风格
- 采用类似 Obsidian 的界面风格，简洁、深色主题，注重可读性和用户体验。
- 使用 `qtawesome` 统一图标风格；

### 3. 其他功能
- 支持窗口大小调整和拖拽。
- 支持快捷键（例如 Ctrl+Enter 发送提示词）。
- 支持 AI 网页数量的动态调整（通过设置页面或配置文件）。

---

## 技术栈
- **编程语言**：Python 3.11
- **界面框架**：PyQt 6.5.0
- **数据库**：libSQL（轻量级 SQLite 替代品）
- **图标库**：qtawesome
- **网页交互**：
  - 使用 PyQt 的 QWebEngineView 加载和控制网页。
  - 通过 JavaScript 注入实现提示词的自动填充和提交。
- **文件系统**：Python 标准库 `os` 和 `pathlib` 实现文件夹浏览。

---
**生成程序时要求**：
1.良好的目录结构
2.生成gitignore
3.生成conda创建环境及安装顺序说明及命令，bat文件


## 程序架构设计

### 1. 模块划分
#### 1.1 主窗口模块（窗口 1）
- **TabManager**：管理多标签页，支持动态添加、删除标签页。
- **AIView**：管理 AI 对话页面，使用 QWebEngineView 加载多个 AI 网页，支持并列布局。
- **WebView**：普通网页浏览标签页，支持地址栏输入和网页加载。

#### 1.2 辅助窗口模块（窗口 2）
- **FileExplorer**：文件夹浏览模块，使用 QTreeView 显示文件系统。
- **PromptInput**：提示词输入区，使用 QTextEdit 支持多行输入。
- **PromptHistory**：提示词历史记录边栏，使用 QListWidget 显示历史记录，支持点击复用。

#### 1.3 数据管理模块
- **DatabaseManager**：管理 libSQL 数据库，负责提示词的存储和查询。
- **PromptSync**：实现提示词从窗口 2 到窗口 1 的同步，调用 JavaScript 注入。

#### 1.4 界面管理模块
- **WindowManager**：管理窗口的显示模式（单屏幕/双屏幕），支持合并和分离。
- **ThemeManager**：管理界面风格，加载 Obsidian 风格主题和图标。

### 2. 数据流
1. 用户在窗口 2 的 PromptInput 输入提示词。
2. 点击"发送"后，PromptSync 模块将提示词发送到窗口 1 的所有 AIView 实例。
3. AIView 通过 JavaScript 注入将提示词填入 AI 网页的输入框并提交。
4. 提示词和相关元数据通过 DatabaseManager 存储到 libSQL。
5. PromptHistory 模块从数据库读取历史记录并更新显示。

---

## 界面布局设计

### 1. 双屏幕模式
- **窗口 1**：
  - 顶部：标签页栏（TabManager）。
  - 中间：AI 对话页面（AIView）或网页浏览页面（WebView）。
  - 底部：状态栏（显示加载状态等）。
- **窗口 2**：
  - 左侧（30%）：FileExplorer。
  - 中间（40%）：PromptInput。
  - 右侧（30%）：PromptHistory。

### 2. 单屏幕模式
- 合并窗口：
  - 上半部分（70%）：窗口 1 内容。
  - 下半部分（30%）：窗口 2 内容。
- 支持拖拽分离。

### 3. 风格设计
- 深色主题，主色调为深灰色（#2E3440），辅色为浅蓝色（#88C0D0）。
- 字体：使用等宽字体（如 Fira Code）以提高代码和文本可读性。
- 图标：加载 Icons，所有按钮和功能区域使用图标+文字组合。

---

## 实现细节

### 1. 主窗口实现
- 使用 PyQt 的 QTabWidget 实现标签页管理。
- AI 对话页面使用 QWebEngineView 加载网页，通过 QHBoxLayout 实现并列布局。
- 网页交互通过 QWebEngineView 的 `runJavaScript` 方法注入 JavaScript 代码，例如：
  ```javascript
  document.querySelector('#prompt-input').value = '用户输入的提示词';
  document.querySelector('#submit-button').click();
  ```

### 2. 辅助窗口实现
- 文件夹浏览使用 QTreeView，结合 QFileSystemModel 加载文件系统。
- 提示词输入区使用 QTextEdit，支持多行输入和快捷键绑定。
- 历史记录边栏使用 QListWidget，点击条目时自动填充到输入区。

### 3. 数据库实现
- libSQL 数据库表结构：
  ```sql
  CREATE TABLE prompt_history (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      prompt_text TEXT NOT NULL,
      timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
      ai_targets TEXT
  );
  ```
- 插入记录：
  ```python
  import libsql_experimental as libsql

  db = libsql.connect("prompts.db")
  db.execute("INSERT INTO prompt_history (prompt_text, ai_targets) VALUES (?, ?)",
             ("用户输入的提示词", "ChatGPT,DeepSeek"))
  ```

### 4. 提示词同步
- PromptSync 模块监听 PromptInput 的发送信号，调用 AIView 的注入方法。
- 注入代码示例：
  ```python
  for web_view in ai_views:
      web_view.page().runJavaScript(
          f"document.querySelector('#prompt-input').value = '{prompt}';"
          f"document.querySelector('#submit-button').click();"
      )
  ```

---

## 打包和安装

### 打包应用程序

我们提供了一套完整的打包工具，可以将应用程序打包为Windows安装程序。

#### 前提条件

1. 安装Python 3.8或更高版本
2. 安装必要的依赖项：`PyQt6`, `PyQt6-WebEngine`, `qtawesome`
3. 安装Inno Setup（可选，用于创建安装程序）：[下载地址](https://jrsoftware.org/isdl.php)

#### 打包步骤

1. 运行批处理文件 `build.bat`，它会自动：
   - 检查并安装必要的依赖
   - 使用PyInstaller打包应用程序
   - 创建Inno Setup脚本
   - 如果安装了Inno Setup，自动编译安装程序

2. 如果没有安装Inno Setup，请手动打开生成的 `installer_script.iss` 文件并编译它。

3. 完成后，安装程序将存放在 `installer` 目录中。

### 手动打包

如果需要手动执行打包过程，可以按照以下步骤操作：

1. 清理之前的构建：
   ```
   rmdir /s /q build dist
   ```

2. 使用PyInstaller打包应用：
   ```
   python -m PyInstaller --name AiSparkHub --windowed --noconfirm --clean --log-level INFO --onedir main.py
   ```

3. 使用Inno Setup打开并编译 `installer_script.iss` 文件。

## 注意事项

- 安装包中包含完整的应用程序和运行时环境，无需单独安装Python
- 用户设置和数据库存储在本地应用数据目录中

## 构建指南

### Windows构建
使用以下命令在Windows系统上构建应用：

```bash
python build.py [应用名称] [版本号]
```

例如：
```bash
python build.py AiSparkHub 1.0.0
```

这将创建一个Windows安装程序(.exe)文件。

### macOS构建
为macOS构建应用有两种方式：

#### 1. 直接在macOS上构建
如果你有Mac设备，可以直接在macOS上运行：

```bash
# 安装必要工具
brew install create-dmg
pip install PyQt6 qtawesome PyInstaller pynput

# 构建应用
python build.py [应用名称] [版本号]
```

#### 2. 使用GitHub Actions自动构建（推荐）

项目已配置GitHub Actions自动构建macOS应用，无需Mac设备：

1. 将代码推送到GitHub仓库：

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/用户名/仓库名.git
git push -u origin main
```

2. 打开GitHub仓库页面，进入"Actions"标签
3. 点击"Build macOS App"工作流
4. 点击"Run workflow"手动触发构建，或通过推送代码自动触发
5. 构建完成后，在"Actions"页面下载DMG安装包

你也可以创建tag触发发布：

```bash
git tag v1.0.0
git push --tags
```

成功构建后，会自动创建GitHub Release，包含DMG安装包。

## 系统要求
- Windows 10/11 或 macOS 10.14+
- 推荐8GB以上内存

## 许可证
[具体许可证信息]

## 强制推送到 GitHub
git push origin main --force
