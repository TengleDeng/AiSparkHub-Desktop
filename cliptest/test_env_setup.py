#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
剪贴板API测试环境设置工具
为测试最新版本PyQt6中的navigator.clipboard支持创建独立环境
"""

import os
import sys
import subprocess
import shutil
import argparse
import platform

# 环境配置
ENV_NAME = "clipboard_test_env"
VENV_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ENV_NAME)
TEST_DIR = os.path.join(VENV_DIR, "test")
TEST_FILE = "clipboard_test.py"

def run_command(cmd, cwd=None, env=None):
    """运行系统命令，打印输出"""
    print(f"执行: {' '.join(cmd)}")
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=cwd,
            env=env
        )
        for line in process.stdout:
            print(line.strip())
        process.wait()
        return process.returncode == 0
    except Exception as e:
        print(f"错误: {e}")
        return False

def get_python_executable():
    """获取Python解释器路径"""
    return sys.executable

def get_venv_python():
    """获取虚拟环境中的Python解释器路径"""
    if platform.system() == "Windows":
        return os.path.join(VENV_DIR, "Scripts", "python.exe")
    else:
        return os.path.join(VENV_DIR, "bin", "python")

def get_venv_pip():
    """获取虚拟环境中的pip路径"""
    if platform.system() == "Windows":
        return os.path.join(VENV_DIR, "Scripts", "pip.exe")
    else:
        return os.path.join(VENV_DIR, "bin", "pip")

def create_venv():
    """创建虚拟环境"""
    if os.path.exists(VENV_DIR):
        print(f"虚拟环境已存在: {VENV_DIR}")
        return True
    
    print(f"创建虚拟环境: {VENV_DIR}")
    python = get_python_executable()
    return run_command([python, "-m", "venv", VENV_DIR])

def install_packages():
    """安装所需的包"""
    print("安装最新版本的PyQt6...")
    pip = get_venv_pip()
    
    # 升级pip
    run_command([pip, "install", "--upgrade", "pip"])
    
    # 先安装wheel以确保二进制包安装正常
    run_command([pip, "install", "wheel"])
    
    # 定义要安装的版本
    qt_version = "6.9.0"  # 使用最新版本的PyQt6进行测试
    
    # 安装PyQt6及相关包，确保版本一致
    print(f"安装 PyQt6=={qt_version} 及相关包...")
    
    # 首先安装核心PyQt6
    if not run_command([pip, "install", f"PyQt6=={qt_version}"]):
        print(f"安装 PyQt6=={qt_version} 失败")
        return False
    
    # 然后安装WebEngine (它会自动安装匹配的Qt6依赖)
    if not run_command([pip, "install", f"PyQt6-WebEngine=={qt_version}"]):
        print(f"安装 PyQt6-WebEngine=={qt_version} 失败")
        return False
    
    # 显示已安装的版本
    run_command([pip, "list"])
    
    # 输出VC++运行时库的安装提示
    print("\n注意: 如果遇到DLL加载错误，请确保已安装Microsoft Visual C++ Redistributable:")
    print("下载链接: https://aka.ms/vs/17/release/vc_redist.x64.exe")
    
    return True

def setup_test_directory():
    """设置测试目录"""
    if not os.path.exists(TEST_DIR):
        os.makedirs(TEST_DIR)
    
    # 复制测试文件
    src_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), TEST_FILE)
    dst_file = os.path.join(TEST_DIR, TEST_FILE)
    
    if os.path.exists(src_file):
        shutil.copy2(src_file, dst_file)
        print(f"已复制测试文件到: {dst_file}")
    else:
        print(f"错误: 找不到测试文件 {src_file}")
        return False
    
    return True

def run_test():
    """运行测试"""
    print("运行剪贴板测试...")
    python = get_venv_python()
    test_script = os.path.join(TEST_DIR, TEST_FILE)
    
    # 设置环境变量以便在新环境中
    env = os.environ.copy()
    
    # 添加Qt插件目录到环境变量
    qt_plugin_path = os.path.join(VENV_DIR, "Lib", "site-packages", "PyQt6", "Qt6", "plugins")
    if platform.system() == "Windows":
        env["QT_PLUGIN_PATH"] = qt_plugin_path
    
    # 提示信息
    print(f"QT_PLUGIN_PATH: {qt_plugin_path}")
    
    success = run_command([python, test_script], cwd=TEST_DIR, env=env)
    
    if not success:
        print("\n测试运行失败，可能原因:")
        print("1. 缺少Microsoft Visual C++ Redistributable，请下载安装: https://aka.ms/vs/17/release/vc_redist.x64.exe")
        print("2. PyQt6-WebEngine未正确安装，请尝试手动安装")
        print(f"3. 系统路径问题，请检查QT_PLUGIN_PATH环境变量: {qt_plugin_path}")
    
    return success

def clean_env():
    """清理环境"""
    if os.path.exists(VENV_DIR):
        print(f"删除虚拟环境: {VENV_DIR}")
        try:
            shutil.rmtree(VENV_DIR)
            return True
        except Exception as e:
            print(f"删除虚拟环境失败: {e}")
            return False
    return True

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="剪贴板API测试环境设置工具")
    parser.add_argument("--clean", action="store_true", help="清理测试环境")
    parser.add_argument("--setup", action="store_true", help="仅设置环境但不运行测试")
    parser.add_argument("--run", action="store_true", help="仅运行测试")
    parser.add_argument("--simple", action="store_true", help="运行简单的PyQt测试")
    parser.add_argument("--kimi", action="store_true", help="运行Kimi网页测试")
    args = parser.parse_args()
    
    # 清理环境
    if args.clean:
        return clean_env()
    
    # 仅运行测试
    if args.run:
        return run_test()
    
    # 运行简单测试
    if args.simple:
        return run_simple_test()
    
    # 运行Kimi测试
    if args.kimi:
        return run_kimi_test()
    
    # 设置环境
    success = True
    if not os.path.exists(VENV_DIR) or not args.setup:
        success = create_venv() and success
        success = install_packages() and success
    
    success = setup_test_directory() and success
    
    # 完成设置后运行测试
    if success and not args.setup:
        success = run_test() and success
    
    return success

def run_simple_test():
    """运行简单的PyQt测试"""
    print("运行简单的PyQt测试...")
    
    # 复制简单测试文件
    src_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "simple_test.py")
    dst_file = os.path.join(TEST_DIR, "simple_test.py")
    
    if os.path.exists(src_file):
        if not os.path.exists(TEST_DIR):
            os.makedirs(TEST_DIR)
        shutil.copy2(src_file, dst_file)
        print(f"已复制简单测试文件到: {dst_file}")
    else:
        print(f"错误: 找不到简单测试文件 {src_file}")
        return False
    
    python = get_venv_python()
    
    # 设置环境变量
    env = os.environ.copy()
    
    # 添加Qt插件目录到环境变量
    qt_plugin_path = os.path.join(VENV_DIR, "Lib", "site-packages", "PyQt6", "Qt6", "plugins")
    if platform.system() == "Windows":
        env["QT_PLUGIN_PATH"] = qt_plugin_path
    
    print(f"QT_PLUGIN_PATH: {qt_plugin_path}")
    
    # 运行简单测试
    success = run_command([python, dst_file], cwd=TEST_DIR, env=env)
    
    if not success:
        print("\n简单测试失败，请确保已安装Microsoft Visual C++ Redistributable:")
        print("下载链接: https://aka.ms/vs/17/release/vc_redist.x64.exe")
    
    return success

def run_kimi_test():
    """运行Kimi网页测试"""
    print("运行Kimi网页测试...")
    
    # 复制Kimi测试文件
    src_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kimi_test.py")
    dst_file = os.path.join(TEST_DIR, "kimi_test.py")
    
    if os.path.exists(src_file):
        if not os.path.exists(TEST_DIR):
            os.makedirs(TEST_DIR)
        shutil.copy2(src_file, dst_file)
        print(f"已复制Kimi测试文件到: {dst_file}")
    else:
        print(f"错误: 找不到Kimi测试文件 {src_file}")
        return False
    
    python = get_venv_python()
    
    # 设置环境变量
    env = os.environ.copy()
    
    # 添加Qt插件目录到环境变量
    qt_plugin_path = os.path.join(VENV_DIR, "Lib", "site-packages", "PyQt6", "Qt6", "plugins")
    if platform.system() == "Windows":
        env["QT_PLUGIN_PATH"] = qt_plugin_path
    
    print(f"QT_PLUGIN_PATH: {qt_plugin_path}")
    
    # 运行Kimi测试
    success = run_command([python, dst_file], cwd=TEST_DIR, env=env)
    
    if not success:
        print("\nKimi测试失败，请确保已安装Microsoft Visual C++ Redistributable:")
        print("下载链接: https://aka.ms/vs/17/release/vc_redist.x64.exe")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 