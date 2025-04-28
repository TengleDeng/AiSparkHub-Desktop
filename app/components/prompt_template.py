#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
提示词模板模块 - 管理和处理提示词模板

主要功能:
1. 模板加载与解析
2. 模板变量提取与处理
3. 变量输入UI管理
4. 模板预览与渲染
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
                            QPushButton, QFrame, QTextEdit, QLineEdit, QFileDialog, QScrollArea, QSizePolicy, QAbstractScrollArea)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QEvent, QObject, QMimeData
from PyQt6.QtGui import QColor, QDragEnterEvent, QDropEvent
import qtawesome as qta
import os
import re
from PyQt6.QtWidgets import QApplication
import datetime

# 导入文件转换器
from app.models.converters import ConverterFactory


class TemplateVariable:
    """模板变量类，管理单个变量的属性和值"""
    
    def __init__(self, name, options=None, default_value="", position=0, var_type=None):
        self.name = name
        self.options = options or []
        self.value = default_value or (options[0] if options else "")
        self.position = position
        self.var_type = var_type  # 变量类型：None(默认)、file等
        self.ui_elements = {}  # 存储变量相关的UI元素
        self.file_path = None  # 存储选择的文件路径（用于file类型变量）


class PromptTemplate(QWidget):
    """提示词模板管理器组件"""
    
    # 定义信号
    template_content_updated = pyqtSignal(str)  # 模板内容更新信号
    
    def __init__(self, parent=None):
        """初始化提示词模板管理器
        
        Args:
            parent: 父控件
        """
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(5)
        
        # 初始化变量
        self.current_template = None  # 保持原变量名
        self.template_variables = []  # 保持原变量名
        self.template_examples_created = False
        self.disable_preview_update = False  # 控制是否禁用预览更新
        
        # 获取主题管理器引用
        self.theme_manager = None
        app = QApplication.instance()
        if hasattr(app, 'theme_manager'):
            self.theme_manager = app.theme_manager
            self.theme_manager.theme_changed.connect(self._update_icons)
        
        # 设置UI
        self.setup_ui()
        
        # 自动加载模板
        self.loadTemplatesFromDirectory()
        
        # 初始化图标颜色
        self._update_icons()
        
        # 确保初始状态正确显示
        QTimer.singleShot(0, self.update_variables_ui)
    
    def setup_ui(self):
        """设置界面"""
        # 创建顶部控件，但不添加到布局，由外部控制显示位置
        self.setup_header_ui()
        
        # 变量输入区域（用QScrollArea包裹）
        self.variables_scroll = QScrollArea()
        self.variables_scroll.setWidgetResizable(True)
        self.variables_container = QWidget()
        self.variables_layout = QVBoxLayout(self.variables_container)
        self.variables_layout.setSpacing(4)  # 控件间距更小
        self.variables_layout.setContentsMargins(0, 2, 0, 2)  # 上下边距更小
        self.variables_scroll.setWidget(self.variables_container)
        self.layout.addWidget(self.variables_scroll)
        
        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet("background-color: var(--interactive-accent); height: 2px;")
        self.layout.addWidget(separator)
        
        # 预览区域
        self.setup_preview_ui()
        self.layout.addWidget(self.preview_container)
        
        # 确保初始状态下变量区域和预览区域可见
        self.variables_container.setVisible(True)
        self.preview_container.setVisible(True)
        
        self.variables_container.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        self.variables_scroll.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
    
    def setup_header_ui(self):
        """设置顶部区域控件 - 模板选择和管理"""
        # 模板下拉列表框
        self.template_combo = QComboBox()
        self.template_combo.setMinimumWidth(200)
        self.template_combo.addItem("📝 直接输入")  # 默认选项
        self.template_combo.currentIndexChanged.connect(self.on_template_selected)
        
        # 设置模板目录按钮
        self.template_dir_button = QPushButton()
        self.template_dir_button.setToolTip("设置模板目录")
        self.template_dir_button.clicked.connect(self.select_template_directory)
        # 确保按钮默认是扁平的，无背景色
        self.template_dir_button.setFlat(True)
        
        # 刷新按钮
        self.refresh_button = QPushButton()
        self.refresh_button.setToolTip("刷新模板列表")
        self.refresh_button.clicked.connect(self.loadTemplatesFromDirectory)
        # 确保按钮默认是扁平的，无背景色
        self.refresh_button.setFlat(True)
    
    def setup_preview_ui(self):
        """设置预览区域"""
        self.preview_container = QWidget()
        preview_layout = QVBoxLayout(self.preview_container)
        preview_layout.setContentsMargins(0, 5, 0, 5)
        
        # 预览标题栏，包含更新按钮和字符计数
        preview_header = QHBoxLayout()
        preview_header.addWidget(QLabel("<b>生成结果预览</b>"))
        
        # 添加刷新预览按钮
        self.refresh_preview_btn = QPushButton()
        self.refresh_preview_btn.setObjectName("refreshPreviewBtn")
        self.refresh_preview_btn.setToolTip("点击立即更新预览内容")
        self.refresh_preview_btn.clicked.connect(self.force_update_preview)
        self.refresh_preview_btn.setFlat(True)
        preview_header.addWidget(self.refresh_preview_btn)
        
        preview_header.addStretch(1)
        self.char_count_label = QLabel("(0字符)")
        self.char_count_label.setStyleSheet("color: var(--text-muted); font-size: 12px;")
        preview_header.addWidget(self.char_count_label)
        preview_layout.addLayout(preview_header)
        
        # 预览文本区域
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setStyleSheet("""
            border: 1px solid var(--background-modifier-border);
            border-radius: 4px;
            background-color: var(--background-primary-alt);
        """)
        preview_layout.addWidget(self.preview_text, 2)
        
        self.layout.addWidget(self.preview_container, 2)
        
        # 确保预览区域可见
        self.preview_container.setVisible(True)
    
    def get_template_directory(self):
        """获取模板目录路径"""
        # 从设置中获取，如果没有则使用默认值
        app = QApplication.instance()
        if hasattr(app, 'settings_manager'):
            template_dir = app.settings_manager.get_value("template_directory", "app/static/prompt")
        else:
            template_dir = "app/static/prompt"  # 默认目录
        
        # 确保是绝对路径
        if not os.path.isabs(template_dir):
            # 获取应用程序目录
            app_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            template_dir = os.path.join(app_dir, template_dir)
        
        return template_dir
    
    def update_path_label(self):
        """更新模板路径标签 - 方法保留但不再显示标签"""
        pass
    
    def select_template_directory(self):
        """选择模板目录"""
        # 获取当前目录
        current_dir = self.get_template_directory()
        
        # 打开目录选择对话框
        new_dir = QFileDialog.getExistingDirectory(
            self, "选择模板目录", current_dir,
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks
        )
        
        if new_dir:
            # 保存新目录到设置
            app = QApplication.instance()
            if hasattr(app, 'settings_manager'):
                app.settings_manager.set_value("template_directory", new_dir)
                print(f"已设置模板目录: {new_dir}")
            
            # 重新加载模板
            self.loadTemplatesFromDirectory()
    
    def loadTemplatesFromDirectory(self):
        """从模板目录加载模板文件"""
        # 获取模板目录路径
        template_dir = self.get_template_directory()
        
        # 清除现有模板（保留第一个"直接输入"选项）
        while self.template_combo.count() > 1:
            self.template_combo.removeItem(1)
        
        # 检查目录是否存在
        if not os.path.exists(template_dir):
            try:
                os.makedirs(template_dir)
                print(f"创建模板目录: {template_dir}")
            except Exception as e:
                print(f"创建模板目录失败: {e}")
                return
        
        # 加载模板文件
        try:
            template_files = [f for f in os.listdir(template_dir) 
                            if f.endswith(('.md', '.txt')) and os.path.isfile(os.path.join(template_dir, f))]
            
            # 按文件名排序
            template_files.sort()
            
            # 添加到下拉框
            for template_file in template_files:
                # 去掉扩展名作为显示名称
                display_name = os.path.splitext(template_file)[0]
                # 添加到下拉框，将完整路径作为用户数据
                self.template_combo.addItem(display_name, os.path.join(template_dir, template_file))
            
            print(f"已加载 {len(template_files)} 个模板")
            
            # 如果模板列表为空且是首次加载，创建示例模板
            if len(template_files) == 0 and not self.template_examples_created:
                self.create_example_templates()
                self.template_examples_created = True
                # 重新加载模板
                self.loadTemplatesFromDirectory()
                
        except Exception as e:
            print(f"加载模板文件失败: {e}")
    
    def create_example_templates(self):
        """创建示例模板"""
        template_dir = self.get_template_directory()
        
        # 示例模板列表
        examples = [
            {
                "name": "AI绘画提示词",
                "content": """生成一张{{绘画主体|招财猫|金渐层猫|银渐层猫}}的图片，风格为{{绘画风格|卡通漫画,儿童绘本,白色背景,粗蜡笔画,治愈,极简}}。

图片中的主体应该{{主体描述|坐在一堆金币上|戴着红色围巾|抱着鱼}}。

整体氛围要{{氛围|温馨|欢快|平静|活力四射}}，色调以{{主色调|暖色|冷色|中性色}}为主。

背景可以有{{背景元素|彩虹|星星|云朵|山丘}}，但不要过于复杂。

重要提示: 保持画面简洁清晰，突出主体，避免过多细节。"""
            },
            {
                "name": "文章总结分析",
                "content": """请阅读以下文章内容，并进行详细的分析总结：

{{文章内容}}

请从以下几个方面进行分析：
1. 文章的核心观点与主要论点
2. 文章的逻辑结构与论证方式
3. 文章使用的数据、证据和案例
4. 文章的语言风格与表达特点
5. 文章可能存在的问题或不足
6. 文章的价值与意义

最后，请给出你对这篇文章的整体评价。"""
            },
            {
                "name": "周报生成",
                "content": """### 工作周报生成

请根据以下工作内容，生成一份专业、简洁的周报。

#### 本周工作内容：
{{工作内容|完成了项目A的需求分析和设计方案；修复了系统B中的3个关键bug；参加了2次项目评审会议}}

#### 主要工作成果：
{{工作成果}}

#### 遇到的问题：
{{遇到的问题|暂无}}

#### 解决方案：
{{解决方案|暂无}}

#### 下周工作计划：
{{下周计划}}

请根据以上信息生成一份结构清晰、重点突出、语言专业的工作周报，适合向管理层汇报。周报中应包含工作内容、成果、问题及解决方案和下周计划等部分。"""
            },
            {
                "name": "文件内容分析",
                "content": """## 文件内容分析

请分析以下文件中的内容：

{{文档:file}}

请从以下方面进行详细分析：

1. 内容摘要：简要概述文件的主要内容
2. 关键点提取：列出文件中的重要信息和关键点
3. 结构分析：说明文件的组织结构和逻辑安排
4. 语言风格：分析文件的语言特点和表达方式
5. 改进建议：针对内容和结构提出具体的改进意见

请确保分析全面、客观，并提供有价值的洞见。"""
            },
            {
                "name": "多文件比较",
                "content": """## 多文件内容比较

请比较以下两个文件的内容：

### 文件1:
{{文件1:file}}

### 文件2:
{{文件2:file}}

请提供详细的比较分析，包括：

1. 共同点：两个文件包含的相同或相似内容
2. 差异点：两个文件的主要区别和独特内容
3. 内容质量比较：哪个文件在内容质量、完整性等方面更胜一筹
4. 结构比较：两个文件在组织结构上的异同
5. 建议：基于比较结果的建议和优化方向

请基于事实进行客观比较，避免主观偏见。"""
            }
        ]
        
        # 创建示例模板文件
        for example in examples:
            file_path = os.path.join(template_dir, f"{example['name']}.md")
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(example['content'])
                print(f"创建示例模板: {file_path}")
            except Exception as e:
                print(f"创建示例模板失败: {e}")
    
    def on_template_selected(self, index):
        """处理模板选择变化"""
        if index == 0:  # "直接输入"选项
            self.current_template = ""
            self.template_variables = []
            self.update_variables_ui()
            self.force_update_preview()  # 立即更新预览
            self.template_content_updated.emit("")  # 发送空白内容表示使用直接输入
            return
        
        # 获取模板文件路径
        template_path = self.template_combo.itemData(index)
        if not template_path or not os.path.exists(template_path):
            print(f"模板文件不存在: {template_path}")
            return
        
        try:
            # 读取模板内容
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            # 保存当前模板
            self.current_template = template_content
            self.template_variables = self.parse_template_variables(template_content)
            
            # 更新变量输入区域
            self.update_variables_ui()
            
            # 初始更新一次预览
            self.force_update_preview()  # 立即更新预览
            
            # 发送模板内容更新信号
            self.template_content_updated.emit(self.get_processed_template())
            
            # 确保变量输入区域可见
            self.variables_container.setVisible(True)
            
        except Exception as e:
            print(f"加载模板失败: {e}")
            import traceback
            traceback.print_exc()
    
    def parse_template_variables(self, template_content):
        """解析模板中的变量
        
        变量格式: {{变量名|选项1|选项2}} 或 {{变量名:类型|选项1|选项2}}
        支持的类型: file (文件选择)
        """
        if not template_content:
            return []
        
        variables = []
        # 使用正则表达式查找变量
        pattern = r'\{\{([^{}|:]+)(?::([^{}|]+))?(?:\|([^{}]*))?\}\}'
        matches = re.finditer(pattern, template_content)
        
        for match in matches:
            var_name = match.group(1).strip()
            var_type = match.group(2).strip() if match.group(2) else None
            options_str = match.group(3) or ''
            
            # 分割选项
            options = [opt.strip() for opt in options_str.split('|') if opt.strip()]
            
            # 避免重复添加同名变量
            if not any(var.name == var_name for var in variables):
                variables.append(TemplateVariable(
                    name=var_name,
                    var_type=var_type,  # 保存变量类型
                    options=options,
                    default_value=options[0] if options else '',
                    position=match.start()
                ))
        
        # 按变量在模板中的位置排序
        variables.sort(key=lambda x: x.position)
        
        return variables
    
    def update_variables_ui(self):
        """更新变量输入UI"""
        # 清空现有变量控件
        for i in reversed(range(self.variables_layout.count())):
            item = self.variables_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()
        
        if not self.template_variables:
            # 没有变量时显示提示
            if self.current_template:
                label = QLabel("此模板没有可配置的变量")
                label.setStyleSheet("color: var(--text-muted); padding: 10px;")
                self.variables_layout.addWidget(label)
            return
        
        # 为每个变量创建输入控件
        for var in self.template_variables:
            # 创建变量容器
            var_container = QWidget()
            var_layout = QVBoxLayout(var_container)
            var_layout.setContentsMargins(0, 5, 0, 5)
            
            # 变量标签
            label = QLabel(var.name)
            label.setStyleSheet("font-weight: bold; color: var(--text-normal);")
            label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
            label.setMinimumHeight(0)
            label.setFixedHeight(24)
            label.setContentsMargins(0, 0, 0, 0)
            var_layout.addWidget(label)
            
            # 清空之前的UI引用
            var.ui_elements = {}
            var.ui_elements['label'] = label
            
            # 根据变量类型创建不同的输入控件
            if var.var_type == 'file':
                file_drop_widget = FileDropWidget()
                file_drop_widget.setFixedHeight(42)
                file_drop_widget.var_ref = var
                file_drop_widget.file_dropped.connect(
                    lambda path, widget=file_drop_widget: self._on_file_dropped(path, widget)
                )
                file_drop_widget.file_cleared.connect(
                    lambda v=var: self._on_file_cleared(v)
                )
                if var.file_path:
                    file_drop_widget.set_file_path(var.file_path)
                var_layout.addWidget(file_drop_widget)
                var.ui_elements['file_drop_widget'] = file_drop_widget
            elif var.options:
                if len(var.options) > 1:
                    combo = QComboBox()
                    combo.var_ref = var
                    for option in var.options:
                        combo.addItem(option)
                    if var.value in var.options:
                        combo.setCurrentText(var.value)
                    combo.currentTextChanged.connect(self._on_combo_changed)
                    combo.setFixedHeight(36)
                    combo.setContentsMargins(0, 0, 0, 0)
                    var_layout.addWidget(combo)
                    var.ui_elements['input'] = combo
                else:
                    line_edit = QLineEdit(var.value or var.options[0])
                    line_edit.var_ref = var
                    line_edit.editingFinished.connect(
                        lambda edit=line_edit: self._on_editing_finished(edit)
                    )
                    line_edit.setFixedHeight(36)
                    line_edit.setContentsMargins(0, 0, 0, 0)
                    var_layout.addWidget(line_edit)
                    var.ui_elements['input'] = line_edit
            else:
                text_edit = QTextEdit()
                text_edit.setMaximumHeight(100)
                text_edit.setText(var.value)
                text_edit.var_ref = var
                text_edit.installEventFilter(self)
                text_edit.setFixedHeight(100)
                text_edit.setContentsMargins(0, 0, 0, 0)
                var_layout.addWidget(text_edit)
                var.ui_elements['input'] = text_edit
            
            # 添加底部弹性空间，防止控件间距被拉伸
            var_layout.addStretch(1)
            
            # 添加到变量布局
            self.variables_layout.addWidget(var_container)
        
    def _on_combo_changed(self, text):
        """处理下拉框选择变化"""
        # 获取发送者
        combo = self.sender()
        if combo and hasattr(combo, 'var_ref'):
            # 更新变量值
            combo.var_ref.value = text
            # 发送模板内容更新信号
            self.template_content_updated.emit(self.get_processed_template())
            # 下拉框没有连续输入问题，可以直接更新预览
            self.update_template_preview()
    
    def _on_editing_finished(self, line_edit):
        """处理行编辑完成事件"""
        if line_edit and hasattr(line_edit, 'var_ref'):
            # 更新变量值
            line_edit.var_ref.value = line_edit.text()
            # 发送模板内容更新信号
            self.template_content_updated.emit(self.get_processed_template())
            # 编辑完成后更新预览
            self.update_template_preview()
    
    def update_template_preview(self):
        """更新模板预览（支持富文本）"""
        try:
            if not self.current_template:
                self.preview_text.clear()
                self.char_count_label.setText("(0字符)")
                self.refresh_preview_btn.setStyleSheet("")
                return
            processed_content = self.get_processed_template()
            self.preview_text.setHtml(processed_content)
            count = len(self.preview_text.toPlainText())
            self.char_count_label.setText(f"({count}字符)")
            self.refresh_preview_btn.setStyleSheet("")
        except Exception as e:
            print(f"更新预览时出错: {e}")
            import traceback
            traceback.print_exc()
    
    def get_processed_template(self):
        """获取处理后的模板内容（变量内容用红色span包裹）"""
        if not self.current_template:
            return ""
        template_content = self.current_template
        for var in self.template_variables:
            # 构建变量的正则表达式模式
            if var.var_type:
                var_pattern = r'\{\{' + re.escape(var.name) + r':' + re.escape(var.var_type) + r'(?:\|[^{}]*)?\}\}'
            else:
                var_pattern = r'\{\{' + re.escape(var.name) + r'(?:\|[^{}]*)?\}\}'
            # 变量内容
            if var.var_type == 'file' and not var.file_path:
                replacement = f"<span style='color:#e63946'>【请选择{var.name}文件】</span>"
            elif var.var_type == 'file' and var.file_path:
                # 获取文件名和修改时间
                file_name = os.path.basename(var.file_path)
                try:
                    mtime = os.path.getmtime(var.file_path)
                    mtime_str = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
                except Exception:
                    mtime_str = ''
                header = f"<span style='color:#e63946'>{file_name}（{mtime_str}）</span>"
                # 文件内容
                if var.value:
                    lines = var.value.split('\n')
                    colored = '<br/>'.join([f"<span style='color:#e63946'>{line if line else '&nbsp;'}</span>" for line in lines])
                else:
                    colored = f"<span style='color:#e63946'>【文件无内容】</span>"
                replacement = header + '<br/>' + colored
            else:
                # 对于多行内容（如文件），每行都加span
                if var.value:
                    lines = var.value.split('\n')
                    colored = '<br/>'.join([f"<span style='color:#e63946'>{line if line else '&nbsp;'}</span>" for line in lines])
                    replacement = colored
                else:
                    replacement = f"<span style='color:#e63946'>【未填写:{var.name}】</span>"
            template_content = re.sub(var_pattern, lambda m: replacement, template_content)
        # 保证换行显示
        template_content = template_content.replace('\n', '<br/>')
        return template_content
    
    def get_plaintext_template(self):
        """获取处理后的模板内容（纯文本，无HTML标记，变量内容为纯文本）"""
        if not self.current_template:
            return ""
        template_content = self.current_template
        for var in self.template_variables:
            if var.var_type:
                var_pattern = r'\{\{' + re.escape(var.name) + r':' + re.escape(var.var_type) + r'(?:\|[^{}]*)?\}\}'
            else:
                var_pattern = r'\{\{' + re.escape(var.name) + r'(?:\|[^{}]*)?\}\}'
            if var.var_type == 'file' and not var.file_path:
                replacement = f"【请选择{var.name}文件】"
            elif var.var_type == 'file' and var.file_path:
                file_name = os.path.basename(var.file_path)
                try:
                    mtime = os.path.getmtime(var.file_path)
                    mtime_str = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
                except Exception:
                    mtime_str = ''
                header = f"{file_name}（{mtime_str}）"
                if var.value:
                    replacement = header + '\n' + var.value
                else:
                    replacement = header + '\n【文件无内容】'
            else:
                replacement = var.value if var.value else f"【未填写:{var.name}】"
            template_content = re.sub(var_pattern, lambda m: replacement, template_content)
        return template_content
    
    def get_current_template_name(self):
        """获取当前模板名称"""
        if self.current_template:
            return self.current_template.split('\n')[0]  # 假设模板名称在第一行
        return "直接输入"
    
    def is_using_direct_input(self):
        """是否使用直接输入模式"""
        return self.template_combo.currentIndex() == 0 or not self.current_template

    # 保留兼容性方法供外部调用
    def on_variable_value_changed(self, variable, new_value):
        """仅用于外部调用的方法，自定义UI使用其他方法"""
        variable.value = new_value
        self.template_content_updated.emit(self.get_processed_template())
        # 直接更新预览，无需设置按钮样式
        self.update_template_preview()

    def _update_icons(self):
        """更新图标颜色以适应当前主题"""
        # 默认颜色（深色主题）
        icon_color = '#D8DEE9'  # 默认深色主题前景色
        
        # 如果有主题管理器，获取当前主题颜色
        if self.theme_manager:
            theme_colors = self.theme_manager.get_current_theme_colors()
            is_dark = theme_colors.get('is_dark', True)
            # 根据主题设置图标颜色
            icon_color = '#FFFFFF' if is_dark else '#2E3440'
            print(f"PromptTemplate - 当前主题: {'深色' if is_dark else '浅色'}")
            print(f"PromptTemplate - 按钮图标颜色: {icon_color}")
        
        # 更新模板目录按钮图标
        if hasattr(self, 'template_dir_button'):
            self.template_dir_button.setIcon(qta.icon("fa5s.folder", color=icon_color))
        
        # 更新刷新按钮图标
        if hasattr(self, 'refresh_button'):
            self.refresh_button.setIcon(qta.icon("fa5s.sync", color=icon_color))
        
        # 更新刷新预览按钮（如果存在）
        if hasattr(self, 'refresh_preview_btn'):
            self.refresh_preview_btn.setIcon(qta.icon("fa5s.sync", color=icon_color))
            # 为刷新预览按钮添加图标（如果之前没有）
            if not self.refresh_preview_btn.icon().isNull():
                self.refresh_preview_btn.setText("")  # 如果有图标，可以移除文本
                self.refresh_preview_btn.setToolTip("刷新预览")
        
        # 更新所有文件浏览按钮
        for var in self.template_variables:
            if var.var_type == 'file' and 'file_drop_widget' in var.ui_elements:
                file_drop_widget = var.ui_elements['file_drop_widget']
                if hasattr(file_drop_widget, 'browse_button'):
                    file_drop_widget.browse_button.setIcon(qta.icon("fa5s.folder-open", color=icon_color))
                    file_drop_widget.browse_button.setText("")
                    file_drop_widget.browse_button.setToolTip("浏览文件")
        
        # 设置按钮样式
        buttons = [self.template_dir_button, self.refresh_button]
        for btn in buttons:
            if btn:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent;
                        border: none;
                        color: {icon_color};
                        padding: 4px 8px;
                    }}
                    QPushButton:hover {{
                        background: rgba(136,192,208,0.08);
                    }}
                    QPushButton:pressed {{
                        background: rgba(136,192,208,0.15);
                    }}
                """)
        
        # 设置所有文件浏览按钮的样式
        for var in self.template_variables:
            if var.var_type == 'file' and 'file_drop_widget' in var.ui_elements:
                file_drop_widget = var.ui_elements['file_drop_widget']
                if hasattr(file_drop_widget, 'browse_button'):
                    file_drop_widget.browse_button.setStyleSheet(f"""
                        QPushButton {{
                            background: transparent;
                            border: none;
                            color: {icon_color};
                            padding: 4px 8px;
                        }}
                        QPushButton:hover {{
                            background: rgba(136,192,208,0.08);
                        }}
                        QPushButton:pressed {{
                            background: rgba(136,192,208,0.15);
                        }}
                    """)
                
        # 如果样式仍然有问题，可以尝试强制刷新
        if hasattr(self, 'template_dir_button'):
            self.template_dir_button.style().unpolish(self.template_dir_button)
            self.template_dir_button.style().polish(self.template_dir_button)
        
        if hasattr(self, 'refresh_button'):
            self.refresh_button.style().unpolish(self.refresh_button)
            self.refresh_button.style().polish(self.refresh_button)

    def force_update_preview(self):
        """立即强制更新预览"""
        self.update_template_preview()

    def eventFilter(self, obj, event):
        """事件过滤器，用于处理QTextEdit的焦点离开事件"""
        if isinstance(obj, QTextEdit) and hasattr(obj, 'var_ref'):
            if event.type() == QEvent.Type.FocusOut:
                # 焦点离开，更新变量值和预览
                obj.var_ref.value = obj.toPlainText()
                # 发送模板内容更新信号
                self.template_content_updated.emit(self.get_processed_template())
                # 更新预览
                self.update_template_preview()
        
        # 继续处理事件
        return super().eventFilter(obj, event)

    def resizeEvent(self, event):
        total_height = self.height()
        max_var_height = int(total_height * 0.7)
        min_preview_height = int(total_height * 0.3)
        self.variables_scroll.setMaximumHeight(max_var_height)
        self.preview_container.setMinimumHeight(min_preview_height)
        super().resizeEvent(event)

    def _on_browse_file_clicked(self, file_widget):
        """处理浏览文件按钮点击事件"""
        if not hasattr(file_widget, 'var_ref'):
            return
            
        # 打开文件选择对话框
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择文件", 
            os.path.expanduser("~"), 
            "所有文件 (*.*)"
        )
        
        if file_path:
            self._process_selected_file(file_path, file_widget.var_ref, file_widget)
    
    def _on_file_dropped(self, file_path, file_widget):
        """处理文件拖放事件"""
        if hasattr(file_widget, 'var_ref'):
            self._process_selected_file(file_path, file_widget.var_ref, file_widget)
    
    def _on_file_cleared(self, variable):
        variable.file_path = None
        variable.value = ""
        self.template_content_updated.emit(self.get_processed_template())
        self.update_template_preview()

    def _process_selected_file(self, file_path, variable, file_widget):
        """处理选择的文件，读取内容并更新预览"""
        if not os.path.isfile(file_path):
            return
            
        # 更新文件路径显示
        file_widget.set_file_path(file_path)
        
        # 保存文件路径到变量
        variable.file_path = file_path
        
        try:
            # 使用转换器获取文件内容
            converter = ConverterFactory.get_converter(file_path)
            content, _ = converter.extract_content(file_path)
            
            # 设置变量值为文件内容
            variable.value = content
            
            # 发送模板内容更新信号
            self.template_content_updated.emit(self.get_processed_template())
            
            # 更新预览
            self.update_template_preview()
            
            print(f"已加载文件: {file_path}")
        except Exception as e:
            print(f"处理文件失败: {e}")
            import traceback
            traceback.print_exc()


class FileDropWidget(QWidget):
    """支持文件拖放、小部件双击选择和删除文件"""
    
    file_dropped = pyqtSignal(str)  # 文件拖放信号
    file_cleared = pyqtSignal()      # 文件清除信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(6)
        
        # 文件图标
        self.icon_label = QLabel()
        self.icon_label.setPixmap(qta.icon('fa5s.file-alt', color='#8ecae6').pixmap(28, 28))
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.icon_label, 0)
        
        # 文件名/提示标签
        self.file_label = QLabel("拖拽文件至此或双击选择文件")
        self.file_label.setStyleSheet("""
            QLabel {
                border: 2px dashed var(--interactive-accent);
                border-radius: 4px;
                padding: 8px;
                background-color: var(--background-primary-alt);
            }
        """)
        self.file_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.file_label, 1)
        
        # 删除按钮（初始隐藏）
        self.delete_button = QPushButton()
        self.delete_button.setIcon(qta.icon('fa5s.times-circle', color='#e63946'))
        self.delete_button.setFixedSize(28, 28)
        self.delete_button.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 14px;
            }
            QPushButton:hover {
                background: #f8d7da;
            }
        """)
        self.delete_button.setToolTip("移除文件")
        self.delete_button.clicked.connect(self.clear_file)
        self.delete_button.hide()
        self.layout.addWidget(self.delete_button, 0)

    def set_file_path(self, file_path):
        """设置已选择的文件路径"""
        if file_path:
            file_name = os.path.basename(file_path)
            self.file_label.setText(file_name)
            self.file_label.setToolTip(file_path)
            self.file_label.setStyleSheet("""
                QLabel {
                    border: 2px solid var(--interactive-accent);
                    border-radius: 4px;
                    padding: 8px;
                    background-color: var(--background-primary-alt);
                    color: var(--text-normal);

                }
            """)
            self.delete_button.show()
        else:
            self.file_label.setText("拖拽文件至此或双击选择文件")
            self.file_label.setToolTip("")
            self.file_label.setStyleSheet("""
                QLabel {
                    border: 2px dashed var(--interactive-accent);
                    border-radius: 4px;
                    padding: 8px;
                    background-color: var(--background-primary-alt);
                }
            """)
            self.delete_button.hide()

    def clear_file(self):
        self.set_file_path("")
        self.file_cleared.emit()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.file_label.setStyleSheet("""
                QLabel {
                    border: 2px dashed var(--interactive-accent-hover);
                    border-radius: 4px;
                    padding: 8px;
                    background-color: var(--background-modifier-hover);
                }
            """)
    def dragLeaveEvent(self, event):
        if not self.file_label.toolTip():
            self.file_label.setStyleSheet("""
                QLabel {
                    border: 2px dashed var(--interactive-accent);
                    border-radius: 4px;
                    padding: 8px;
                    background-color: var(--background-primary-alt);
                }
            """)
    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            file_path = event.mimeData().urls()[0].toLocalFile()
            self.set_file_path(file_path)
            self.file_dropped.emit(file_path)
            event.acceptProposedAction()
    def mouseDoubleClickEvent(self, event):
        # 双击弹出文件选择
        file_path, _ = QFileDialog.getOpenFileName(self, "选择文件", os.path.expanduser("~"), "所有文件 (*.*)")
        if file_path:
            self.set_file_path(file_path)
            self.file_dropped.emit(file_path)
        super().mouseDoubleClickEvent(event)
