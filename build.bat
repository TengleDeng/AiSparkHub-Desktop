@echo off
REM 设置应用信息
set APP_NAME=AiSparkHub
set APP_VERSION=1.0.0
set REGENERATE_ISS=
set SKIP_INSTALLER=

REM 检查Python安装
echo 检查Python安装...
where python >nul 2>nul
if %ERRORLEVEL% neq 0 goto python_error

REM 获取Python版本
for /f "tokens=2" %%V in ('python --version 2^>^&1') do set python_version=%%V
echo 检测到Python版本: %python_version%

REM 检查是否使用Conda环境
python -c "import sys; print('conda' if 'conda' in sys.prefix else 'no-conda')" > temp.txt
set /p conda_env=<temp.txt
del temp.txt

if not "%conda_env%"=="conda" goto skip_conda_warning
echo 检测到Conda环境
echo.
echo 注意: 如果在打包过程中遇到pathlib相关错误，请运行:
echo conda remove pathlib
echo.
:skip_conda_warning

REM 不再检查必要依赖
echo 继续打包过程...

REM 检查Inno Setup安装
echo 检查Inno Setup安装...
where ISCC.exe >nul 2>nul
if %ERRORLEVEL% equ 0 goto inno_found

REM 尝试在默认安装路径查找
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" goto inno_found_x86
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" goto inno_found_x64

echo 警告: 未找到Inno Setup安装.
echo 如果您想创建安装程序, 请从以下网址下载并安装Inno Setup:
echo https://jrsoftware.org/isdl.php
echo.
echo 按任意键继续，将只执行PyInstaller打包...
pause >nul
set SKIP_INSTALLER=--skip-installer
goto skip_iss_question

:inno_found_x86
set "PATH=%PATH%;%ProgramFiles(x86)%\Inno Setup 6"
goto inno_found

:inno_found_x64
set "PATH=%PATH%;%ProgramFiles%\Inno Setup 6"

:inno_found
echo 已找到Inno Setup。

REM 询问是否要重新生成ISS文件
if "%SKIP_INSTALLER%"=="--skip-installer" goto skip_iss_question
echo.
echo 是否重新生成Inno Setup脚本文件？
choice /C YN /M "请选择(Y=是, N=否)"
if errorlevel 2 goto skip_iss_generation
if errorlevel 1 set REGENERATE_ISS=--regenerate-iss
:skip_iss_generation

:skip_iss_question
REM 开始打包过程
echo 开始打包 %APP_NAME% v%APP_VERSION%...

REM 显示使用的选项
echo 使用选项:
if "%SKIP_INSTALLER%"=="--skip-installer" echo - 跳过安装包创建
if "%REGENERATE_ISS%"=="--regenerate-iss" echo - 重新生成Inno Setup脚本

REM 构建命令行参数
set BUILD_ARGS=%APP_NAME% %APP_VERSION% %SKIP_INSTALLER% %REGENERATE_ISS%

REM 运行Python构建脚本
python build.py %BUILD_ARGS%

REM 检查打包结果
if %ERRORLEVEL% equ 0 goto build_success

echo.
echo 打包过程中出现错误。
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

:build_success
echo.
echo 打包完成!
echo 可在 dist 文件夹中找到生成的文件。
pause
exit /b 0

:python_error
echo 错误: 未找到Python, 请确保Python已安装并添加到PATH环境变量中.
pause
exit /b 1 