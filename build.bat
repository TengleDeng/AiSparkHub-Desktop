@echo off
setlocal enabledelayedexpansion

REM 设置应用信息
set APP_NAME=AiSparkHub
set APP_VERSION=0.25

REM 检查Python安装
echo 检查Python安装...
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo 错误: 未找到Python, 请确保Python已安装并添加到PATH环境变量中.
    pause
    exit /b 1
)

REM 获取Python版本
for /f "tokens=2" %%V in ('python --version 2^>^&1') do set python_version=%%V
echo 检测到Python版本: %python_version%

REM 检查是否使用Conda环境
python -c "import sys; print('conda' if 'conda' in sys.prefix else 'no-conda')" > temp.txt
set /p conda_env=<temp.txt
del temp.txt

if "%conda_env%"=="conda" (
    echo 检测到Conda环境
    
    REM 检查pathlib包（可能会导致PyInstaller冲突）
    python -c "import importlib.util; print('installed' if importlib.util.find_spec('pathlib') else 'not-installed')" > temp.txt
    set /p pathlib_status=<temp.txt
    del temp.txt
    
    if "!pathlib_status!"=="installed" (
        echo.
        echo 警告: 检测到pathlib包，它可能与PyInstaller不兼容
        echo 如果在打包过程中遇到pathlib相关错误，请在继续之前运行:
        echo conda remove pathlib
        echo.
        choice /C YN /M "是否继续? (Y=是, N=否)"
        if errorlevel 2 (
            echo 操作已取消
            exit /b 1
        )
    )
)

REM 检查必要依赖
echo 检查必要的包...
set REQUIRED_PACKAGES=PyQt6 qtawesome pyinstaller pynput

set MISSING_PACKAGES=
for %%p in (%REQUIRED_PACKAGES%) do (
    python -c "import importlib.util; print('installed' if importlib.util.find_spec('%%p') else 'not-installed')" > temp.txt
    set /p package_status=<temp.txt
    del temp.txt
    
    if "!package_status!"=="not-installed" (
        set MISSING_PACKAGES=!MISSING_PACKAGES! %%p
    )
)

if not "!MISSING_PACKAGES!"=="" (
    echo 错误: 缺少以下必要包:!MISSING_PACKAGES!
    echo 请使用以下命令安装它们:
    echo pip install!MISSING_PACKAGES!
    pause
    exit /b 1
)

REM 检查Inno Setup安装
echo 检查Inno Setup安装...
reg query "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 6_is1" /v "DisplayName" >nul 2>nul
if %ERRORLEVEL% neq 0 (
    reg query "HKLM\SOFTWARE\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 6_is1" /v "DisplayName" >nul 2>nul
    if %ERRORLEVEL% neq 0 (
        echo 警告: 未找到Inno Setup安装.
        echo 如果您想创建安装程序, 请从以下网址下载并安装Inno Setup:
        echo https://jrsoftware.org/isdl.php
        echo.
        echo 按任意键继续，将只执行PyInstaller打包...
        pause >nul
        set SKIP_INSTALLER=--skip-installer
    ) else (
        set SKIP_INSTALLER=
    )
) else (
    set SKIP_INSTALLER=
)

REM 开始打包过程
echo 开始打包 %APP_NAME% v%APP_VERSION%...

REM 构建命令行参数
set BUILD_ARGS=%APP_NAME% %APP_VERSION% %SKIP_INSTALLER%

REM 运行Python构建脚本
python build.py %BUILD_ARGS%

REM 检查打包结果
if %ERRORLEVEL% neq 0 (
    echo.
    echo 打包过程中出现错误。
    
    REM 提供常见错误的解决方案
    echo.
    echo 常见错误解决方案:
    echo.
    echo 1. 如果出现 "ImportError: cannot import name 'abc' from 'pathlib'" 或 pathlib 相关错误:
    echo    这是由于 pathlib 包与 PyInstaller 不兼容导致的。
    echo    请运行: conda remove pathlib
    echo    然后重新运行此脚本。
    echo.
    echo 2. 如果出现 "ModuleNotFoundError" 错误:
    echo    请确保所有依赖项已安装:
    echo    pip install PyQt6 qtawesome pyinstaller pynput
    echo.
    echo 3. 如果出现 "PermissionError" 或无法删除文件的错误:
    echo    请关闭所有可能正在使用这些文件的程序，包括编辑器或文件浏览器。
    echo.
    
    pause
    exit /b 1
)

echo.
echo 打包完成!
echo 可在 dist 文件夹中找到生成的文件。

pause
exit /b 0 