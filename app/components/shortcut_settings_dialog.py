#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QComboBox, QDialogButtonBox, 
                            QGridLayout, QGroupBox, QLineEdit, QMessageBox)
from PyQt6.QtCore import Qt, QSettings, pyqtSignal
from PyQt6.QtGui import QKeySequence, QIcon
import qtawesome as qta

class KeySequenceEdit(QLineEdit):
    """自定义的按键序列编辑器，用于捕获键盘组合键"""
    
    key_captured = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("点击此处按下键盘快捷键组合")
        self.setReadOnly(True)
        self.current_keys = []
        self.modifiers = {
            Qt.KeyboardModifier.ControlModifier: "Ctrl",
            Qt.KeyboardModifier.AltModifier: "Alt",
            Qt.KeyboardModifier.ShiftModifier: "Shift",
            Qt.KeyboardModifier.MetaModifier: "Meta"
        }
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
    def keyPressEvent(self, event):
        """捕获键盘按键事件"""
        if event.key() == Qt.Key.Key_Escape:
            # 清空当前输入
            self.current_keys = []
            self.setText("")
            event.accept()
            return
            
        # 忽略单独的修饰键
        if event.key() in (Qt.Key.Key_Control, Qt.Key.Key_Alt, 
                           Qt.Key.Key_Shift, Qt.Key.Key_Meta):
            event.accept()
            return
            
        # 记录当前组合键
        modifiers = event.modifiers()
        keys = []
        
        # 添加修饰键
        for mod, name in self.modifiers.items():
            if modifiers & mod:
                keys.append(name)
                
        # 添加主键
        key = QKeySequence(event.key()).toString()
        if key and key not in ['Ctrl', 'Alt', 'Shift', 'Meta']:
            keys.append(key)
            
        # 更新显示
        if keys:
            key_text = "+".join(keys)
            self.setText(key_text)
            self.current_keys = keys
            self.key_captured.emit(key_text)
            
        event.accept()

class ShortcutSettingsDialog(QDialog):
    """快捷键设置对话框"""
    
    shortcuts_changed = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("快捷键设置")
        self.setMinimumWidth(450)
        
        # 初始快捷键配置
        self.default_shortcuts = {
            "main_window": "Alt+X",
            "auxiliary_window": "Alt+C"
        }
        
        # 当前快捷键配置
        self.shortcuts = self.load_shortcuts()
        
        self.init_ui()
        
    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        
        # 创建窗口控制组
        window_group = QGroupBox("窗口控制快捷键")
        window_layout = QGridLayout()
        
        # 主窗口快捷键
        window_layout.addWidget(QLabel("主窗口显示/隐藏:"), 0, 0)
        self.main_window_edit = KeySequenceEdit()
        self.main_window_edit.setText(self.shortcuts.get("main_window", self.default_shortcuts["main_window"]))
        self.main_window_edit.key_captured.connect(lambda key: self.on_key_captured("main_window", key))
        window_layout.addWidget(self.main_window_edit, 0, 1)
        
        # 辅助窗口快捷键
        window_layout.addWidget(QLabel("辅助窗口显示/隐藏:"), 1, 0)
        self.auxiliary_window_edit = KeySequenceEdit()
        self.auxiliary_window_edit.setText(self.shortcuts.get("auxiliary_window", self.default_shortcuts["auxiliary_window"]))
        self.auxiliary_window_edit.key_captured.connect(lambda key: self.on_key_captured("auxiliary_window", key))
        window_layout.addWidget(self.auxiliary_window_edit, 1, 1)
        
        # 重置按钮
        reset_btn = QPushButton("恢复默认")
        reset_btn.clicked.connect(self.reset_shortcuts)
        window_layout.addWidget(reset_btn, 2, 1, alignment=Qt.AlignmentFlag.AlignRight)
        
        window_group.setLayout(window_layout)
        layout.addWidget(window_group)
        
        # 提示信息
        info_label = QLabel("按 Esc 键清除当前输入。修改快捷键后需要重启应用程序才能生效。")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # 确定和取消按钮
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.save_shortcuts)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
    def on_key_captured(self, shortcut_name, key_text):
        """当捕获到快捷键时的处理函数"""
        # 检查是否与其他快捷键冲突
        for name, value in self.shortcuts.items():
            if name != shortcut_name and value == key_text:
                QMessageBox.warning(self, "快捷键冲突", 
                                   f"快捷键 '{key_text}' 已被分配给 '{self.get_shortcut_display_name(name)}'，请选择其他快捷键。")
                # 重置为原值
                if shortcut_name == "main_window":
                    self.main_window_edit.setText(self.shortcuts.get(shortcut_name, ""))
                elif shortcut_name == "auxiliary_window":
                    self.auxiliary_window_edit.setText(self.shortcuts.get(shortcut_name, ""))
                return
                
        # 更新快捷键
        self.shortcuts[shortcut_name] = key_text
    
    def get_shortcut_display_name(self, shortcut_name):
        """获取快捷键的显示名称"""
        names = {
            "main_window": "主窗口显示/隐藏",
            "auxiliary_window": "辅助窗口显示/隐藏"
        }
        return names.get(shortcut_name, shortcut_name)
        
    def reset_shortcuts(self):
        """重置所有快捷键为默认值"""
        self.shortcuts = self.default_shortcuts.copy()
        self.main_window_edit.setText(self.default_shortcuts["main_window"])
        self.auxiliary_window_edit.setText(self.default_shortcuts["auxiliary_window"])
        
    def save_shortcuts(self):
        """保存快捷键设置"""
        # 读取当前输入值
        self.shortcuts["main_window"] = self.main_window_edit.text()
        self.shortcuts["auxiliary_window"] = self.auxiliary_window_edit.text()
        
        # 保存到设置文件
        settings = QSettings("AiSparkHub", "GlobalShortcuts")
        for name, value in self.shortcuts.items():
            settings.setValue(name, value)
            
        # 发出信号通知快捷键已更改
        self.shortcuts_changed.emit(self.shortcuts)
        
        # 提示需要重启
        QMessageBox.information(self, "保存成功", 
                             "快捷键设置已保存。请重启应用程序以使新的快捷键生效。")
        
        self.accept()
        
    def load_shortcuts(self):
        """从设置文件加载快捷键配置"""
        settings = QSettings("AiSparkHub", "GlobalShortcuts")
        shortcuts = {}
        
        for name, default_value in self.default_shortcuts.items():
            shortcuts[name] = settings.value(name, default_value)
            
        return shortcuts 