"""
简单的PyQt6测试脚本，检查基本功能
"""

import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget

def main():
    print("正在初始化QApplication...")
    app = QApplication(sys.argv)
    print("成功创建QApplication")
    
    print("正在创建主窗口...")
    window = QMainWindow()
    window.setWindowTitle("PyQt6测试")
    window.setGeometry(100, 100, 400, 200)
    
    # 创建中央部件
    central_widget = QWidget()
    window.setCentralWidget(central_widget)
    
    # 创建布局
    layout = QVBoxLayout(central_widget)
    
    # 创建标签
    label = QLabel("PyQt6测试成功!")
    layout.addWidget(label)
    
    print("窗口创建成功，准备显示...")
    window.show()
    print("窗口已显示")
    
    print("Qt版本信息:")
    from PyQt6.QtCore import QT_VERSION_STR, PYQT_VERSION_STR
    print(f"Qt版本: {QT_VERSION_STR}")
    print(f"PyQt版本: {PYQT_VERSION_STR}")
    
    return app.exec()

if __name__ == "__main__":
    try:
        print("开始PyQt6简单测试...")
        sys.exit(main())
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc() 