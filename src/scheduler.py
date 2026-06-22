"""
定时任务调度器
负责按计划自动执行爬取、分析、报表生成、邮件预警
"""

import os
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from src.crawler.manager import CrawlerManager
from src.analyzer.sentiment import SentimentAnalyzer
from src.models import init_db, SentimentPost, UserProfile, RiskLevel, UserType, CrawlLog, CrawlStatus
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

    # 宁夏标识关键词
    ningxia_keywords = keywords_config.get("ningxia_identifiers", [])
    phone_prefixes = keywords_config.get("phone_prefixes", [])

    logger.info(f"[调度] 开始本轮爬取，关键词数量: {len(all_keywords)}")

    # 初始化爬虫
    platform_cookies = {
        "weibo": os.getenv("WEIBO_COOKIE", ""),
        "zhihu": os.getenv("ZHIHU_COOKIE", ""),
        "baidu_tieba": os.getenv("TIEBA_COOKIE", ""),
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
    new_high_risk = []
    for raw in raw_posts:
        # 去重
        exists = session.query(SentimentPost).filter_by(post_id=raw.post_id).first()
        if exists:
            continue

        result = analyzer.analyze(raw)

        # 判断是否宁夏相关
        is_ningxia = False
        content_text = (raw.content or "") + (raw.title or "")
        for kw in ningxia_keywords:
            if kw in content_text:
                is_ningxia = True
                break
        if not is_ningxia and raw.phone_number:
            for prefix in phone_prefixes:
                if raw.phone_number.startswith(prefix):
                    is_ningxia = True
                    break

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
            is_ningxia=is_ningxia,
            image_urls=",".join(raw.image_urls) if raw.image_urls else None,
        )
        session.add(post)
        new_count += 1
        
        # 记录高风险
        if result.risk_level == "high":
            new_high_risk.append(post)

    session.commit()
    session.close()
    logger.info(f"[调度] 本轮新增 {new_count} 条舆情记录")
    
    # 如果有新的高风险舆情，发送预警邮件
    if new_high_risk:
        try:
            from scripts.email_alert import EmailAlert
            alert = EmailAlert()
            if alert.password:
                alert.send_high_risk_alert(new_high_risk)
                logger.info(f"[调度] 已发送高风险预警邮件，{len(new_high_risk)} 条")
        except Exception as e:
            logger.warning(f"[调度] 邮件预警失败: {e}")


def run_daily_report():
    """生成每日报表并发送邮件"""
    from datetime import date
    from scripts.generate_report import generate_daily_report
    from scripts.email_alert import EmailAlert
    
    today = date.today()
    
    # 生成报表
    filepath, stats = generate_daily_report(today)
    logger.info(f"[调度] 每日报表已生成: {filepath}")
    
    # 发送日报邮件
    try:
        alert = EmailAlert()
        if alert.password:
            alert.send_daily_report(filepath, stats)
            logger.info("[调度] 日报邮件已发送")
    except Exception as e:
        logger.warning(f"[调度] 日报邮件发送失败: {e}")


def start_scheduler():
    """启动定时调度器"""
    crawl_interval = int(os.getenv("CRAWL_INTERVAL_MINUTES", "360"))
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
