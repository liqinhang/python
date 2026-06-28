@echo off
chcp 65001 >nul
cd /d "e:\大二下学习\python大作业"
echo 正在启动排行榜服务器...
C:\Users\15985\AppData\Local\Programs\Python\Python310\python.exe -m uvicorn server:app --reload --port 8000
pause
