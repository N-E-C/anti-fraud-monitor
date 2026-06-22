#!/usr/bin/env python3
"""
优化版日报生成器
输出格式：按风险等级分组，包含宁夏专区，附带统计图表
"""

import os
import sys
from datetime import datetime, date

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from src.models import init_db, SentimentPost, RiskLevel
from sqlalchemy import func, desc
from loguru import logger
import pandas as pd


def generate_daily_report(report_date=None):
    """生成优化版日报"""
    DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{PROJECT_ROOT}/data/monitor.db")
    engine, Session = init_db(DATABASE_URL)
    session = Session()
    
    if report_date is None:
        report_date = date.today()
    
    # 当天数据
    day_start = datetime.combine(report_date, datetime.min.time())
    day_end = datetime.combine(report_date, datetime.max.time())
    
    posts = session.query(SentimentPost).filter(
        SentimentPost.crawled_at >= day_start,
        SentimentPost.crawled_at <= day_end
    ).all()
    
    # 统计
    total = len(posts)
    high = [p for p in posts if p.risk_level == RiskLevel.HIGH]
    medium = [p for p in posts if p.risk_level == RiskLevel.MEDIUM]
    low = [p for p in posts if p.risk_level == RiskLevel.LOW]
    ningxia = [p for p in posts if p.is_ningxia]
    ningxia_high = [p for p in ningxia if p.risk_level == RiskLevel.HIGH]
    
    # 平台分布
    platform_counts = {}
    for p in posts:
        platform_counts[p.platform] = platform_counts.get(p.platform, 0) + 1
    
    PLATFORM_NAMES = {
        "weibo": "微博", "zhihu": "知乎", "baidu_tieba": "贴吧",
        "douyin": "抖音", "kuaishou": "快手", "xiaohongshu": "小红书",
    }
    
    # 生成Excel报告
    output_dir = os.path.join(PROJECT_ROOT, "reports", "output")
    os.makedirs(output_dir, exist_ok=True)
    
    filepath = os.path.join(output_dir, f"反诈舆情日报_{report_date.strftime('%Y%m%d')}.xlsx")
    
    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
        # Sheet 1: 概览
        overview_data = {
            "指标": [
                "报告日期", "数据总量", "高风险", "中风险", "低风险",
                "宁夏相关", "宁夏高风险", "主要平台"
            ],
            "数值": [
                report_date.strftime("%Y-%m-%d"),
                total, len(high), len(medium), len(low),
                len(ningxia), len(ningxia_high),
                "、".join([f"{PLATFORM_NAMES.get(k,k)}({v})" for k,v in sorted(platform_counts.items(), key=lambda x:-x[1])[:3]])
            ]
        }
        pd.DataFrame(overview_data).to_excel(writer, sheet_name="概览", index=False)
        
        # Sheet 2: 高风险舆情
        if high:
            high_data = []
            for p in high:
                high_data.append({
                    "平台": PLATFORM_NAMES.get(p.platform, p.platform),
                    "内容摘要": p.content[:100] + "..." if len(p.content) > 100 else p.content,
                    "作者": p.author_name,
                    "命中关键词": p.matched_keywords,
                    "宁夏": "✓" if p.is_ningxia else "",
                    "点赞": p.like_count,
                    "评论": p.comment_count,
                    "发布时间": p.published_at.strftime("%Y-%m-%d %H:%M") if p.published_at else "",
                    "链接": p.url or "",
                })
            pd.DataFrame(high_data).to_excel(writer, sheet_name="高风险舆情", index=False)
        
        # Sheet 3: 宁夏专区
        if ningxia:
            nx_data = []
            for p in ningxia:
                nx_data.append({
                    "风险等级": {"high": "高风险", "medium": "中风险", "low": "低风险"}.get(p.risk_level.value if p.risk_level else "", "未知"),
                    "平台": PLATFORM_NAMES.get(p.platform, p.platform),
                    "内容摘要": p.content[:150] + "..." if len(p.content) > 150 else p.content,
                    "作者": p.author_name,
                    "命中关键词": p.matched_keywords,
                    "手机号": p.phone_number or "",
                    "点赞": p.like_count,
                    "评论": p.comment_count,
                    "发布时间": p.published_at.strftime("%Y-%m-%d %H:%M") if p.published_at else "",
                    "链接": p.url or "",
                })
            pd.DataFrame(nx_data).to_excel(writer, sheet_name="宁夏舆情", index=False)
        
        # Sheet 4: 全部数据
        all_data = []
        for p in posts:
            all_data.append({
                "平台": PLATFORM_NAMES.get(p.platform, p.platform),
                "风险等级": {"high": "高风险", "medium": "中风险", "low": "低风险"}.get(p.risk_level.value if p.risk_level else "", "未知"),
                "内容": p.content,
                "作者": p.author_name,
                "命中关键词": p.matched_keywords,
                "宁夏": "✓" if p.is_ningxia else "",
                "点赞": p.like_count,
                "评论": p.comment_count,
                "转发": p.share_count,
                "发布时间": p.published_at.strftime("%Y-%m-%d %H:%M") if p.published_at else "",
                "爬取时间": p.crawled_at.strftime("%Y-%m-%d %H:%M") if p.crawled_at else "",
                "链接": p.url or "",
            })
        pd.DataFrame(all_data).to_excel(writer, sheet_name="全部数据", index=False)
    
    logger.success(f"日报已生成: {filepath}")
    session.close()
    
    return filepath, {
        "date": report_date.strftime("%Y-%m-%d"),
        "total": total,
        "high": len(high),
        "medium": len(medium),
        "low": len(low),
        "ningxia": len(ningxia),
        "ningxia_high": len(ningxia_high),
        "platforms": platform_counts,
    }


if __name__ == "__main__":
    filepath, stats = generate_daily_report()
    print(f"\n日报统计:")
    print(f"  日期: {stats['date']}")
    print(f"  总量: {stats['total']}")
    print(f"  高风险: {stats['high']}")
    print(f"  中风险: {stats['medium']}")
    print(f"  低风险: {stats['low']}")
    print(f"  宁夏: {stats['ningxia']} (高风险={stats['ningxia_high']})")
