# AiSparkHub桌面版打包指南

此文档介绍如何使用打包脚本创建AiSparkHub桌面应用的可执行文件和安装程序。

## 系统要求

- Windows 操作系统
- Python 3.8+
- 必要的Python包: PyQt6, qtawesome, pyinstaller, pynput
- 可选: Inno Setup 6 (用于创建安装程序)

## 快速开始

最简单的方法是直接运行`build.bat`批处理文件：

```
build.bat
```

这将自动检查环境依赖，并使用默认参数构建应用程序。

## 高级用法

### 命令行参数

`build.py`脚本支持以下命令行参数：

```
python build.py [app_name] [app_version] [选项]
```

参数说明：
- `app_name`: 应用名称，默认为"AiSparkHub"
- `app_version`: 应用版本号，默认为"1.0.0"

选项：
- `--skip-clean`: 跳过清理构建文件夹
- `--skip-installer`: 跳过生成安装程序
- `--icon <图标路径>`: 指定自定义应用图标路径

示例：
```
python build.py MyApp 2.0.0 --icon my_icon.ico
```

### 常见问题解决

#### pathlib冲突错误

如果您使用Conda环境并遇到以下错误：
```
ImportError: cannot import name 'abc' from 'pathlib'
```

解决方法：
```
conda remove pathlib
```

#### 权限错误

如果遇到无法删除文件或目录的权限错误，请确保：
1. 关闭所有可能使用这些文件的程序，包括编辑器或文件浏览器
2. 关闭正在运行的AiSparkHub应用实例

#### 缺少模块错误

如果看到`ModuleNotFoundError`，请安装所需的依赖：
```
pip install PyQt6 qtawesome pyinstaller pynput
```

## 输出文件

打包完成后，您可以在以下位置找到生成的文件：

- 可执行文件：`dist/AiSparkHub/` 目录
- 安装程序：`installer/` 目录 (如果安装了Inno Setup)

## 自定义打包配置

如需更高级的自定义，您可以编辑以下文件：

- `build.py`: 主要的打包脚本，包含PyInstaller配置和安装程序生成逻辑
- `build.bat`: Windows批处理脚本，提供环境检查和用户界面

## 可能的扩展

- 添加对macOS和Linux的支持
- 实现自动版本号递增
- 添加自动化测试作为打包流程的一部分
- 优化打包尺寸和性能

---

如有任何问题或建议，请联系开发团队。 