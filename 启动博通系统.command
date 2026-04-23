#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════
#  博通研究系统 · 一键启动脚本（Mac）
#  双击此文件即可启动系统，无需手动输入命令
# ════════════════════════════════════════════════════════════

# 切换到此脚本所在目录（即项目根目录）
cd "$(dirname "$0")"

APP_PORT=8501
APP_URL="http://localhost:${APP_PORT}"
STREAMLIT_CMD="streamlit"

# 后台子进程 PID（用于打开浏览器），脚本退出时一并清理
BROWSER_PID=""
trap 'kill "${BROWSER_PID}" 2>/dev/null' EXIT

echo ""
echo "════════════════════════════════════════"
echo "  博通研究系统 · AVGO Research Agent"
echo "════════════════════════════════════════"

# 如存在 .venv，则优先自动激活虚拟环境
if [ -f ".venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source ".venv/bin/activate"
    STREAMLIT_CMD=".venv/bin/streamlit"
    echo ""
    echo "[信息] 已自动激活 .venv 虚拟环境"
else
    if ! command -v streamlit >/dev/null 2>&1; then
        echo ""
        echo "找不到可用的 Streamlit 启动环境"
        echo ""
        echo "请先在终端运行以下命令安装依赖："
        echo "  cd $(pwd)"
        echo "  python3 -m venv .venv"
        echo "  .venv/bin/pip install -r requirements.txt"
        echo ""
        read -r -p "按回车键退出..."
        exit 1
    fi
    echo ""
    echo "[提示] 未发现 .venv，将尝试使用系统环境中的 streamlit"
fi

# 检查 .env 文件（API Key 配置）
if [ ! -f ".env" ]; then
    echo ""
    echo "[提示] 未找到 .env 文件，AI 复盘功能可能不可用"
    echo "      如需使用 AI 功能，请复制 .env.example 为 .env 并填入 API Key"
    echo ""
fi

# 检查端口是否被占用，若被旧 Streamlit 进程占用则自动清理
if lsof -iTCP:"${APP_PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
    STALE_PID=$(lsof -iTCP:"${APP_PORT}" -sTCP:LISTEN -t 2>/dev/null | head -1)
    STALE_NAME=$(ps -p "${STALE_PID}" -o comm= 2>/dev/null || echo "未知进程")
    echo ""
    echo "[警告] 端口 ${APP_PORT} 已被占用"
    echo "       PID: ${STALE_PID}   进程: ${STALE_NAME}"
    echo ""
    echo "       正在尝试自动关闭旧进程..."
    if kill "${STALE_PID}" 2>/dev/null; then
        sleep 1
        # 确认端口已释放
        if lsof -iTCP:"${APP_PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
            # 普通 kill 不够，再试 kill -9
            kill -9 "${STALE_PID}" 2>/dev/null
            sleep 1
        fi
        if lsof -iTCP:"${APP_PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
            echo ""
            echo "[错误] 旧进程无法清理，端口 ${APP_PORT} 仍被占用"
            echo ""
            echo "       请手动执行："
            echo "         lsof -i :${APP_PORT}"
            echo "         kill -9 ${STALE_PID}"
            echo ""
            read -r -p "按回车键退出..."
            exit 1
        else
            echo "       旧进程已关闭，继续启动..."
        fi
    else
        echo ""
        echo "[错误] 无法关闭旧进程（PID ${STALE_PID}），端口 ${APP_PORT} 仍被占用"
        echo ""
        echo "       请手动执行："
        echo "         lsof -i :${APP_PORT}"
        echo "         kill -9 ${STALE_PID}"
        echo ""
        read -r -p "按回车键退出..."
        exit 1
    fi
fi

echo ""
echo "正在启动..."
echo "地址：${APP_URL}"
echo "   关闭此窗口可停止系统"
echo ""

# 延迟 2 秒后自动打开浏览器（等 streamlit 启动完毕）
(sleep 2 && open "${APP_URL}") &
BROWSER_PID=$!

# 启动主程序（前台运行，窗口保持开启直到 streamlit 退出）
"${STREAMLIT_CMD}" run app.py \
    --server.port "${APP_PORT}" \
    --server.headless true \
    --browser.gatherUsageStats false

EXIT_CODE=$?
if [ "${EXIT_CODE}" -ne 0 ]; then
    echo ""
    echo "[错误] 系统异常退出，退出码：${EXIT_CODE}"
    echo "       如需排查，请将以上日志截图后反馈"
fi
echo ""
read -r -p "按回车键关闭此窗口..."
