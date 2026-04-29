"""
定时任务调度器
负责按计划自动执行爬取、分析、报表生成
"""

import os
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from src.crawler.manager import CrawlerManager
from src.analyzer.sentiment import SentimentAnalyzer
from src.reporter.excel_reporter import ExcelReporter
from src.models import init_db, SentimentPost, UserProfile, RiskLevel, UserType
from src.utils.config import load_config, load_keywords


def run_crawl_and_analyze():
    """执行一轮爬取 + 分析 + 入库"""
    config = load_config()
    keywords_config = load_keywords()

    # 合并所有等级关键词
    all_keywords = (
        keywords_config.get("high_risk", []) +
        keywords_config.get("medium_risk", []) +
        keywords_config.get("neutral", [])
    )

    logger.info(f"[调度] 开始本轮爬取，关键词数量: {len(all_keywords)}")

    # 初始化爬虫
    platform_cookies = {
        "weibo": os.getenv("WEIBO_COOKIE", ""),
        "zhihu": os.getenv("ZHIHU_COOKIE", ""),
    }
    manager = CrawlerManager(
        keywords=all_keywords,
        platform_cookies=platform_cookies,
    )

    # 初始化分析器
    analyzer = SentimentAnalyzer(
        high_risk_kws=keywords_config.get("high_risk", []),
        medium_risk_kws=keywords_config.get("medium_risk", []),
    )

    # 初始化数据库
    engine, Session = init_db(os.getenv("DATABASE_URL", "sqlite:///data/monitor.db"))
    session = Session()

    # 爬取
    raw_posts = manager.run_all(pages_per_keyword=2)

    # 分析并入库
    new_count = 0
    for raw in raw_posts:
        # 去重
        exists = session.query(SentimentPost).filter_by(post_id=raw.post_id).first()
        if exists:
            continue

        result = analyzer.analyze(raw)

        post = SentimentPost(
            platform=raw.platform,
            post_id=raw.post_id,
            title=raw.title,
            content=raw.content,
            url=raw.url,
            author_name=raw.author_name,
            author_id=raw.author_id,
            author_followers=raw.author_followers,
            author_verified=raw.author_verified,
            view_count=raw.view_count,
            like_count=raw.like_count,
            comment_count=raw.comment_count,
            share_count=raw.share_count,
            published_at=raw.published_at,
            crawled_at=datetime.utcnow(),
            risk_level=RiskLevel(result.risk_level),
            sentiment_score=result.sentiment_score,
            matched_keywords=",".join(result.matched_high + result.matched_medium),
            user_type=UserType.SUSPECTED_FRAUD if result.suspected_fraud_flag else UserType.UNKNOWN,
            phone_number=result.mentioned_phones[0] if result.mentioned_phones else None,
        )
        session.add(post)
        new_count += 1

    session.commit()
    session.close()
    logger.info(f"[调度] 本轮新增 {new_count} 条舆情记录")


def run_daily_report():
    """生成每日报表"""
    from datetime import date
    engine, Session = init_db(os.getenv("DATABASE_URL", "sqlite:///data/monitor.db"))
    session = Session()

    today = date.today()
    posts = session.query(SentimentPost).filter(
        SentimentPost.crawled_at >= datetime.combine(today, datetime.min.time())
    ).all()

    posts_data = [
        {
            "platform": p.platform,
            "post_id": p.post_id,
            "title": p.title,
            "content": p.content,
            "url": p.url,
            "author_name": p.author_name,
            "author_followers": p.author_followers,
            "view_count": p.view_count,
            "like_count": p.like_count,
            "comment_count": p.comment_count,
            "share_count": p.share_count,
            "published_at": p.published_at,
            "risk_level": p.risk_level.value if p.risk_level else "unknown",
            "sentiment_score": p.sentiment_score,
            "matched_keywords": p.matched_keywords,
            "suspected_fraud_flag": p.user_type == UserType.SUSPECTED_FRAUD,
            "mentioned_phones": p.phone_number or "",
        }
        for p in posts
    ]

    session.close()

    reporter = ExcelReporter(output_dir="reports/output")
    filepath = reporter.generate_daily_report(posts_data, today)
    logger.info(f"[调度] 每日报表已生成: {filepath}")


def start_scheduler():
    """启动定时调度器"""
    crawl_interval = int(os.getenv("CRAWL_INTERVAL_MINUTES", "60"))
    report_hour = int(os.getenv("REPORT_HOUR", "8"))

    scheduler = BlockingScheduler(timezone="Asia/Shanghai")

    # 定时爬取（每 N 分钟一次）
    scheduler.add_job(
        run_crawl_and_analyze,
        "interval",
        minutes=crawl_interval,
        id="crawl_job",
        name="舆情爬取与分析",
    )

    # 每日报表（每天 08:00）
    scheduler.add_job(
        run_daily_report,
        CronTrigger(hour=report_hour, minute=0),
        id="report_job",
        name="每日报表生成",
    )

    logger.info(f"调度器启动：爬取间隔={crawl_interval}分钟，报表时间={report_hour}:00")
    logger.info("立即执行第一次爬取...")
    run_crawl_and_analyze()

    scheduler.start()


if __name__ == "__main__":
    start_scheduler()
