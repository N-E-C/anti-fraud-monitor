#!/bin/bash
# 反诈舆情监测 Dashboard 启动脚本

cd "$(dirname "$0")/.."

# 检查虚拟环境
if [ ! -d ".venv" ]; then
    echo "错误: 未找到虚拟环境，请先运行 python -m venv .venv"
    exit 1
fi

# 激活虚拟环境
source .venv/bin/activate

# 默认端口
PORT=${1:-5000}

echo "=========================================="
echo "  反诈舆情监测 Dashboard"
echo "=========================================="
echo ""
echo "启动地址: http://localhost:$PORT"
echo ""
echo "功能说明:"
echo "  - 数据概览: 查看统计数据和最新高风险舆情"
echo "  - 全部舆情: 浏览和筛选所有舆情数据"
echo "  - 宁夏舆情: 查看宁夏公司相关舆情"
echo "  - 爬取状态: 查看各平台爬取状态和日志"
echo ""
echo "按 Ctrl+C 停止服务"
echo "=========================================="
echo ""

# 启动 Flask
python dashboard/app.py --port $PORT --host 0.0.0.0
