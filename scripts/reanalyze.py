#!/usr/bin/env python3
"""
重新分析所有记录，更新风险等级
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from src.models import init_db, SentimentPost, RiskLevel
from src.analyzer.sentiment import SentimentAnalyzer
from src.crawler.base import RawPost
from loguru import logger

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{PROJECT_ROOT}/data/monitor.db")
engine, Session = init_db(DATABASE_URL)
session = Session()

analyzer = SentimentAnalyzer()

# 查询所有记录
posts = session.query(SentimentPost).all()
logger.info(f"待分析记录: {len(posts)} 条")

# 统计变化
stats = {"high": 0, "medium": 0, "low": 0}
changes = 0

for post in posts:
    old_level = post.risk_level.value if post.risk_level else "unknown"
    
    # 构造 RawPost 用于分析
    raw = RawPost(
        platform=post.platform,
        post_id=post.post_id,
        title=post.title or "",
        content=post.content or "",
    )
    
    # 重新分析
    result = analyzer.analyze(raw)
    new_level = result.risk_level
    
    # 更新
    post.risk_level = RiskLevel(new_level)
    post.matched_keywords = ",".join(result.matched_high + result.matched_medium)
    post.sentiment_score = result.sentiment_score
    
    stats[new_level] += 1
    if old_level != new_level:
        changes += 1

session.commit()

logger.success(f"分析完成！")
logger.info(f"新分布: 高风险={stats['high']}, 中风险={stats['medium']}, 低风险={stats['low']}")
logger.info(f"风险等级变化: {changes} 条")

session.close()
