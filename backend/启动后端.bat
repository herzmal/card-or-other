@echo off
chcp 65001 >nul
title 卡牌对战后端
echo ======================================
echo   卡牌对战 Python 后端
echo   启动后请勿关闭本窗口！
echo ======================================
echo.
cd /d "%~dp0"
"D:\zzdelvelp\python\python.exe" -m uvicorn main:app --host 0.0.0.0 --port 8000
pause
