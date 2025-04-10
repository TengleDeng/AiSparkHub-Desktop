@echo off
echo AiSparkHub 打包脚本
echo ===========================

rem 检查Python是否安装
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
  echo 错误: 未检测到Python！请确保Python已安装并添加到PATH环境变量。
  goto :end
)

rem 检查必要的依赖
echo 检查并安装依赖项...

python -c "import PyQt6" >nul 2>nul
if %ERRORLEVEL% neq 0 (
  echo 正在安装必要的依赖项: PyQt6...
  pip install PyQt6 PyQt6-WebEngine
  if %ERRORLEVEL% neq 0 (
    echo 错误: 安装PyQt6失败!
    goto :end
  )
)

python -c "import qtawesome" >nul 2>nul
if %ERRORLEVEL% neq 0 (
  echo 正在安装必要的依赖项: qtawesome...
  pip install qtawesome
  if %ERRORLEVEL% neq 0 (
    echo 错误: 安装qtawesome失败!
    goto :end
  )
)

python -c "import PyInstaller" >nul 2>nul
if %ERRORLEVEL% neq 0 (
  echo 正在安装必要的依赖项: pyinstaller...
  pip install pyinstaller
  if %ERRORLEVEL% neq 0 (
    echo 错误: 安装PyInstaller失败!
    goto :end
  )
)

rem 检查Inno Setup是否安装
echo 检查Inno Setup...
set INNO_PATH="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist %INNO_PATH% (
  echo 警告: 在标准路径下未找到Inno Setup！
  echo 安装包将无法自动创建。
  echo 您可以从https://jrsoftware.org/isdl.php下载Inno Setup
  echo 然后手动编译生成的installer_script.iss文件。
)

echo.
echo 开始打包应用程序...
echo.

rem 运行打包脚本
python build.py
if %ERRORLEVEL% neq 0 (
  echo.
  echo 打包失败，请检查错误信息。
  goto :end
)

echo.
echo 打包过程完成
echo.
if not exist %INNO_PATH% (
  echo 如果Inno Setup编译器未找到，请手动编译installer_script.iss文件
  echo 您可以从https://jrsoftware.org/isdl.php下载Inno Setup
)

:end
pause 