@echo off
echo 修复pathlib与PyInstaller的兼容问题
echo ======================================

echo 从conda环境中移除pathlib包...
call conda remove -y pathlib

echo.
echo 完成！现在可以重新运行build.bat来打包应用程序了。
echo.
pause 