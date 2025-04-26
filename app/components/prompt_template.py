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
                            QPushButton, QFrame, QTextEdit, QLineEdit, QFileDialog)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QEvent, QObject
from PyQt6.QtGui import QColor
import qtawesome as qta
import os
import re
from PyQt6.QtWidgets import QApplication

# 添加事件过滤器，避免焦点问题
class TextEditEventFilter(QObject):
    textChanged = pyqtSignal(QTextEdit)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.typing_timer = QTimer()
        self.typing_timer.setSingleShot(True)
        self.typing_timer.setInterval(300)  # 300ms防抖
        self.current_edit = None
    
    def eventFilter(self, obj, event):
        if isinstance(obj, QTextEdit):
            if event.type() == QEvent.Type.KeyPress:
                self.current_edit = obj
                # 重启计时器
                self.typing_timer.stop()
                self.typing_timer.timeout.connect(lambda: self.textChanged.emit(self.current_edit))
                self.typing_timer.start()
            
        return False  # 继续处理事件


class TemplateVariable:
    """模板变量类，管理单个变量的属性和值"""
    
    def __init__(self, name, options=None, default_value="", position=0):
        self.name = name
        self.options = options or []
        self.value = default_value or (options[0] if options else "")
        self.position = position
        self.ui_elements = {}  # 存储变量相关的UI元素


class PromptTemplate(QWidget):
    """提示词模板管理器组件"""
    
    # 定义信号
    template_content_updated = pyqtSignal(str)  # 模板内容更新信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(5)
        
        # 初始化变量
        self.current_template = None
        self.template_variables = []
        self.template_examples_created = False
        
        # 创建事件过滤器
        self.text_edit_filter = TextEditEventFilter(self)
        self.text_edit_filter.textChanged.connect(self._on_text_edit_changed)
        
        # 设置UI
        self.setup_ui()
        
        # 自动加载模板
        self.loadTemplatesFromDirectory()
        
        # 确保初始状态正确显示
        QTimer.singleShot(0, self.update_variables_ui)
    
    def setup_ui(self):
        """设置界面"""
        # 创建顶部控件，但不添加到布局，由外部控制显示位置
        self.setup_header_ui()
        
        # 变量输入区域
        self.variables_container = QWidget()
        self.variables_layout = QVBoxLayout(self.variables_container)
        self.variables_layout.setContentsMargins(0, 5, 0, 5)
        self.layout.addWidget(self.variables_container, 1)
        
        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet("background-color: var(--interactive-accent); height: 2px;")
        self.layout.addWidget(separator)
        
        # 预览区域
        self.setup_preview_ui()
        
        # 确保初始状态下变量区域和预览区域可见
        self.variables_container.setVisible(True)
    
    def setup_header_ui(self):
        """设置顶部区域控件 - 模板选择和管理"""
        # 模板下拉列表框
        self.template_combo = QComboBox()
        self.template_combo.setMinimumWidth(200)
        self.template_combo.addItem("📝 直接输入")  # 默认选项
        self.template_combo.currentIndexChanged.connect(self.on_template_selected)
        
        # 设置模板目录按钮
        self.template_dir_button = QPushButton()
        self.template_dir_button.setIcon(qta.icon("fa5s.folder"))
        self.template_dir_button.setToolTip("设置模板目录")
        self.template_dir_button.clicked.connect(self.select_template_directory)
        # 确保按钮默认是扁平的，无背景色
        self.template_dir_button.setFlat(True)
        
        # 刷新按钮
        self.refresh_button = QPushButton()
        self.refresh_button.setIcon(qta.icon("fa5s.sync"))
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
        self.refresh_preview_btn = QPushButton("刷新预览")
        self.refresh_preview_btn.setToolTip("点击更新预览内容")
        self.refresh_preview_btn.clicked.connect(self.update_template_preview)
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
            template_dir = app.settings_manager.get_value("template_directory", "AI/prompt")
        else:
            template_dir = "AI/prompt"  # 默认目录
        
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
            self.current_template = None
            self.template_variables = []
            self.update_variables_ui()
            self.update_template_preview()  # 立即清空预览
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
            self.current_template = {
                'path': template_path,
                'name': self.template_combo.itemText(index),
                'content': template_content
            }
            
            # 解析模板变量
            self.template_variables = self.parse_template_variables(template_content)
            
            # 更新变量输入区域
            self.update_variables_ui()
            
            # 初始更新一次预览
            self.update_template_preview()
            
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
        
        变量格式: {{变量名|选项1|选项2}}
        """
        if not template_content:
            return []
        
        variables = []
        # 使用正则表达式查找变量
        pattern = r'\{\{([^{}|]+)(?:\|([^{}]*))?\}\}'
        matches = re.finditer(pattern, template_content)
        
        for match in matches:
            var_name = match.group(1).strip()
            options_str = match.group(2) or ''
            
            # 分割选项
            options = [opt.strip() for opt in options_str.split('|') if opt.strip()]
            
            # 避免重复添加同名变量
            if not any(var.name == var_name for var in variables):
                variables.append(TemplateVariable(
                    name=var_name,
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
            var_layout.addWidget(label)
            
            # 清空之前的UI引用
            var.ui_elements = {}
            var.ui_elements['label'] = label
            
            # 根据是否有选项决定控件类型
            if var.options:
                # 多个选项使用下拉框
                if len(var.options) > 1:
                    combo = QComboBox()
                    # 设置标签，用于在回调中识别关联的变量
                    combo.setProperty("var_name", var.name)
                    for option in var.options:
                        combo.addItem(option)
                    
                    # 设置初始值
                    if var.value in var.options:
                        combo.setCurrentText(var.value)
                    
                    # 为了避免lambda问题，使用自定义处理方法
                    combo.currentTextChanged.connect(self._on_combo_changed)
                    var_layout.addWidget(combo)
                    var.ui_elements['input'] = combo
                
                # 单个选项使用文本框并填入默认值
                else:
                    line_edit = QLineEdit(var.value or var.options[0])
                    # 设置标签，用于在回调中识别关联的变量
                    line_edit.setProperty("var_name", var.name)
                    # 不使用直接连接
                    line_edit.textChanged.connect(self._on_line_edit_changed)
                    var_layout.addWidget(line_edit)
                    var.ui_elements['input'] = line_edit
            else:
                # 无选项使用多行文本框
                text_edit = QTextEdit()
                text_edit.setMaximumHeight(100)
                text_edit.setText(var.value)
                # 设置标签，用于在回调中识别关联的变量
                text_edit.setProperty("var_name", var.name)
                
                # 使用事件过滤器代替信号连接
                text_edit.installEventFilter(self.text_edit_filter)
                
                var_layout.addWidget(text_edit)
                var.ui_elements['input'] = text_edit
            
            # 添加到变量布局
            self.variables_layout.addWidget(var_container)
        
        # 添加底部空白
        self.variables_layout.addStretch(1)
    
    def _on_combo_changed(self, text):
        """处理下拉框值变化"""
        # 获取发送者
        sender = self.sender()
        if sender:
            # 获取关联的变量名称
            var_name = sender.property("var_name")
            if var_name:
                # 查找对应的变量
                for var in self.template_variables:
                    if var.name == var_name:
                        # 更新变量值
                        var.value = text
                        # 更新按钮状态
                        self.refresh_preview_btn.setText("刷新预览 ⟳")
                        self.refresh_preview_btn.setStyleSheet("background-color: #5E81AC; color: white;")
                        # 发送模板内容更新信号
                        self.template_content_updated.emit(self.get_processed_template())
                        break

    def _on_line_edit_changed(self, text):
        """处理单行文本框值变化"""
        # 获取发送者
        sender = self.sender()
        if sender:
            # 获取关联的变量名称
            var_name = sender.property("var_name")
            if var_name:
                # 查找对应的变量
                for var in self.template_variables:
                    if var.name == var_name:
                        # 更新变量值
                        var.value = text
                        # 更新按钮状态
                        self.refresh_preview_btn.setText("刷新预览 ⟳")
                        self.refresh_preview_btn.setStyleSheet("background-color: #5E81AC; color: white;")
                        # 发送模板内容更新信号
                        self.template_content_updated.emit(self.get_processed_template())
                        break

    def _on_text_edit_changed(self, text_edit):
        """处理多行文本框值变化"""
        if text_edit:
            # 获取关联的变量名称
            var_name = text_edit.property("var_name")
            if var_name:
                # 获取当前文本
                current_text = text_edit.toPlainText()
                # 查找对应的变量
                for var in self.template_variables:
                    if var.name == var_name:
                        # 更新变量值
                        var.value = current_text
                        # 更新按钮状态
                        self.refresh_preview_btn.setText("刷新预览 ⟳")
                        self.refresh_preview_btn.setStyleSheet("background-color: #5E81AC; color: white;")
                        # 发送模板内容更新信号
                        self.template_content_updated.emit(self.get_processed_template())
                        break
    
    def update_template_preview(self):
        """更新模板预览 - 只在用户明确请求时更新"""
        # 重置按钮状态
        self.refresh_preview_btn.setText("刷新预览")
        self.refresh_preview_btn.setStyleSheet("")
        
        if not self.current_template:
            self.preview_text.clear()
            self.char_count_label.setText("(0字符)")
            return
        
        # 获取处理后的模板
        processed_template = self.get_processed_template()
        
        # 更新预览区域
        self.preview_text.setText(processed_template)
        
        # 更新字符计数
        char_count = len(processed_template)
        self.char_count_label.setText(f"({char_count}字符)")
    
    def get_processed_template(self):
        """获取处理后的模板内容"""
        if not self.current_template:
            return ""
        
        template_content = self.current_template['content']
        
        # 替换所有变量
        for var in self.template_variables:
            var_pattern = r'\{\{' + re.escape(var.name) + r'(?:\|[^{}]*)?\}\}'
            replacement = var.value if var.value else f"【未填写:{var.name}】"
            template_content = re.sub(var_pattern, replacement, template_content)
        
        return template_content
    
    def get_current_template_name(self):
        """获取当前模板名称"""
        if self.current_template:
            return self.current_template['name']
        return "直接输入"
    
    def is_using_direct_input(self):
        """是否使用直接输入模式"""
        return self.template_combo.currentIndex() == 0 or self.current_template is None

    # 保留兼容性方法供外部调用
    def on_variable_value_changed(self, variable, new_value):
        """仅用于外部调用的方法，自定义UI使用其他方法"""
        variable.value = new_value
        self.template_content_updated.emit(self.get_processed_template())
        self.refresh_preview_btn.setText("刷新预览 ⟳")
        self.refresh_preview_btn.setStyleSheet("background-color: #5E81AC; color: white;")
