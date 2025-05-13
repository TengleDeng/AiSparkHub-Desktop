@echo off
echo 临时移除AiSparkHub-Website目录并推送到远程仓库...

REM 保存当前提交ID
for /f "tokens=*" %%a in ('git rev-parse HEAD') do set ORIGINAL_COMMIT=%%a

REM 创建临时分支保存当前状态
git branch temp-push-branch %ORIGINAL_COMMIT%

REM 从索引中移除AiSparkHub-Website目录
git rm --cached -r AiSparkHub-Website
git commit --amend -m "临时移除AiSparkHub-Website目录进行推送"

REM 执行推送
git push

REM 恢复到原始状态
git reset --hard temp-push-branch
git branch -D temp-push-branch

echo 推送完成，已恢复AiSparkHub-Website目录的本地跟踪。 