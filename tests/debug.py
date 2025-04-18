import sys
import traceback
import os

# 确保当前目录在sys.path中
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if current_dir not in sys.path:
    sys.path.append(current_dir)

try:
    # 直接导入ai_platform_tester.py文件
    path = os.path.join('tests', 'ai_platform_tester.py')
    import importlib.util
    spec = importlib.util.spec_from_file_location("ai_platform_tester", path)
    ai_platform_tester = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ai_platform_tester)
    
    print("成功导入所需模块")
    
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    tester = ai_platform_tester.AIPlatformTester()
    print("成功创建AIPlatformTester实例")
    
    tester.show()
    print("显示窗口")
    
    sys.exit(app.exec())
except Exception as e:
    print(f"错误: {e}")
    print("详细错误信息:")
    traceback.print_exc() 