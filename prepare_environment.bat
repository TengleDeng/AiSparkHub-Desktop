@echo off
echo AiSparkHub 环境优化脚本
echo ==============================

rem 检查conda是否可用
call conda --version >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo 错误: 未找到conda命令。请确保Anaconda或Miniconda已安装并在PATH中。
    goto :end
)

echo 当前活动的conda环境:
call conda env list | findstr "*"
echo.

:menu
echo 请选择操作:
echo 1. 修复当前环境中的pathlib冲突问题
echo 2. 创建新的优化环境
echo 3. 退出
echo.
set /p choice=请输入选项(1-3): 

if "%choice%"=="1" goto fix_current
if "%choice%"=="2" goto create_new
if "%choice%"=="3" goto end
echo 无效选项，请重试
goto menu

:fix_current
echo.
echo 正在修复当前环境中的pathlib问题...
call conda remove -y pathlib
if %ERRORLEVEL% neq 0 (
    echo 警告: 移除pathlib时出错，可能当前环境中没有安装该包。
) else (
    echo 成功移除pathlib包。
)

echo.
echo 确保PyInstaller已正确安装...
call pip uninstall -y pyinstaller pyinstaller-hooks-contrib
call pip install -U pyinstaller
echo.
echo 当前环境已优化完成。
goto end

:create_new
echo.
set /p env_name=输入新环境名称(默认: aisparkhub_new): 
if "%env_name%"=="" set env_name=aisparkhub_new

echo 创建优化的conda环境: %env_name%
call conda create -y -n %env_name% python=3.11 --no-default-packages
call conda activate %env_name%

echo 安装关键依赖...
call pip install PyQt6 PyQt6-WebEngine qtawesome
call pip install pyinstaller

echo.
echo ✓ 新环境 '%env_name%' 已创建并配置!
echo   请使用以下命令激活环境:
echo     conda activate %env_name%
echo.
goto end

:end
echo.
echo 完成!
pause 