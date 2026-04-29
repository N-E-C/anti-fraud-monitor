"""
程序入口
"""

import os
import sys
import argparse
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

# 日志配置
logger.add(
    "logs/monitor_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="30 days",
    level=os.getenv("LOG_LEVEL", "INFO"),
    encoding="utf-8",
)


def main():
    parser = argparse.ArgumentParser(description="客户自媒体反诈微舆情监测工具")
    subparsers = parser.add_subparsers(dest="command")

    # 子命令: 启动调度器（持续监测）
    subparsers.add_parser("start", help="启动持续监测调度器")

    # 子命令: 立即执行一次爬取
    subparsers.add_parser("crawl", help="立即执行一次爬取与分析")

    # 子命令: 生成报表
    report_parser = subparsers.add_parser("report", help="生成数据报表")
    report_parser.add_argument("--date", default=None, help="报表日期 YYYY-MM-DD（默认今天）")

    # 子命令: 初始化数据库
    subparsers.add_parser("initdb", help="初始化数据库")

    args = parser.parse_args()

    if args.command == "start":
        from src.scheduler import start_scheduler
        logger.info("启动持续监测模式...")
        start_scheduler()

    elif args.command == "crawl":
        from src.scheduler import run_crawl_and_analyze
        logger.info("执行一次性爬取...")
        run_crawl_and_analyze()
        logger.info("爬取完成")

    elif args.command == "report":
        from src.scheduler import run_daily_report
        from datetime import date
        if args.date:
            report_date = date.fromisoformat(args.date)
        else:
            report_date = date.today()
        run_daily_report()
        logger.info("报表生成完成，输出至 reports/output/")

    elif args.command == "initdb":
        from src.models import init_db
        os.makedirs("data", exist_ok=True)
        engine, _ = init_db(os.getenv("DATABASE_URL", "sqlite:///data/monitor.db"))
        logger.info("数据库初始化完成")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
