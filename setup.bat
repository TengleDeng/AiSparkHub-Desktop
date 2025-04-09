@echo off
echo 正在创建AiSparkHub环境，请稍候...

:: 检查conda是否安装
where conda >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo 错误: 未找到conda命令。请先安装Anaconda或Miniconda。
    exit /b 1
)

:: 删除已存在的环境
echo 正在检查并删除已存在的环境...
call conda remove --name aisparkhub --all -y

:: 创建新的conda环境
echo 正在创建新的conda环境...
call conda create --name aisparkhub python=3.11 -y

:: 激活环境
echo 正在激活环境...
call conda activate aisparkhub

:: 安装依赖
echo 正在安装依赖...
call pip install -r requirements.txt

:: 创建数据目录
if not exist "data" mkdir data

echo ======================================
echo 安装完成! 使用以下命令启动应用:
echo run.bat
echo ======================================

pause 