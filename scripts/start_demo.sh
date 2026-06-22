#!/bin/bash
# 展示模式启动脚本
# 使用独立的展示数据库，不污染正式数据

cd "$(dirname "$0")/.."

# 检查虚拟环境
if [ ! -d ".venv" ]; then
    echo "错误: 未找到虚拟环境"
    exit 1
fi

# 激活虚拟环境
source .venv/bin/activate

# 检查展示数据库
if [ ! -f "data/demo.db" ]; then
    echo "展示数据库不存在，正在生成..."
    python scripts/generate_demo_data.py
fi

# 默认端口
PORT=${1:-5001}

echo "=========================================="
echo "  反诈舆情监测系统 - 展示模式"
echo "=========================================="
echo ""
echo "⚠️  注意: 当前使用展示数据库，数据为模拟数据"
echo ""
echo "启动地址: http://localhost:$PORT"
echo ""
echo "按 Ctrl+C 停止服务"
echo "=========================================="
echo ""

# 使用展示数据库启动
DATABASE_URL="sqlite:///data/demo.db" python dashboard/app.py --port $PORT --host 0.0.0.0
