@echo off
chcp 65001 >nul
REM ════════════════════════════════════════════════════════════
REM  博通研究系统 · 一键启动脚本（Windows）
REM  双击此文件即可启动系统，无需手动输入命令
REM ════════════════════════════════════════════════════════════
setlocal

REM 切换到此脚本所在目录（即项目根目录）
cd /d "%~dp0"

set "APP_PORT=8501"
set "APP_URL=http://localhost:%APP_PORT%"
set "STREAMLIT_CMD=streamlit"

echo.
echo ════════════════════════════════════════
echo   博通研究系统 · AVGO Research Agent
echo ════════════════════════════════════════

REM 如存在 .venv，则优先自动激活虚拟环境
if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
    set "STREAMLIT_CMD=.venv\Scripts\streamlit.exe"
    echo.
    echo [信息] 已自动激活 .venv 虚拟环境
) else (
    where streamlit >nul 2>nul
    if errorlevel 1 (
        echo.
        echo [错误] 未找到可用的 Streamlit 启动环境
        echo.
        echo 请先执行以下命令完成初始化：
        echo   python -m venv .venv
        echo   .venv\Scripts\pip install -r requirements.txt
        echo.
        pause
        exit /b 1
    )
    echo.
    echo [提示] 未发现 .venv，将尝试使用系统环境中的 streamlit
)

REM 检查 .env 文件
if not exist ".env" (
    echo.
    echo [提示] 未找到 .env 文件，AI 复盘功能可能不可用
    echo        如需使用 AI 功能，请复制 .env.example 为 .env 并填入 API Key
    echo.
)

REM 启动前检查默认端口是否已被占用
netstat -ano | findstr /r /c:":%APP_PORT% .*LISTENING" >nul
if not errorlevel 1 (
    echo.
    echo [错误] 端口 %APP_PORT% 已被占用，无法直接启动首页
    echo.
    echo 请先关闭占用 %APP_PORT% 的程序，或修改脚本中的 APP_PORT
    echo.
    pause
    exit /b 1
)

echo.
echo 正在启动...
echo 地址：%APP_URL%
echo 关闭此窗口可停止系统
echo.

REM 延迟 3 秒后自动打开浏览器（等 streamlit 启动完毕）
start /b cmd /c "timeout /t 3 >nul && start \"\" %APP_URL%"

REM 启动首页；首页本身就是第一个默认标签
%STREAMLIT_CMD% run app.py --server.port %APP_PORT% --server.headless false --browser.gatherUsageStats false
