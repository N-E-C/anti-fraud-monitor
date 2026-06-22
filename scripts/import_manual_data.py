#!/usr/bin/env python3
"""
导入舆情收集文件夹中的真实数据到数据库
"""

import os
import sys
import re
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

import pandas as pd
from src.models import init_db, SentimentPost, RiskLevel
from src.analyzer.sentiment import SentimentAnalyzer
from src.crawler.base import RawPost
from loguru import logger

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{PROJECT_ROOT}/data/monitor.db")
engine, Session = init_db(DATABASE_URL)
session = Session()
analyzer = SentimentAnalyzer()

# 文件列表
files = [
    '/mnt/c/Users/Cherney/Desktop/舆情收集/附：舆情信息（0225）.xlsx',
    '/mnt/c/Users/Cherney/Desktop/舆情收集/3-22移动关停.xlsx',
    '/mnt/c/Users/Cherney/Desktop/舆情收集/05-04移动关停.xlsx',
    '/mnt/c/Users/Cherney/Desktop/舆情收集/重要会议期间移动相关负面0304.xlsx',
]

# 宁夏关键词
NINGXIA_KEYWORDS = [
    "宁夏", "银川", "石嘴山", "吴忠", "固原", "中卫",
    "宁夏移动", "宁夏联通", "宁夏电信", "宁夏反诈",
]

NINGXIA_PHONE_PREFIXES = [
    "13469", "13519", "13619", "13709", "13895", "13995",
    "14709", "15009", "15109", "15209", "15709", "15809", "15909",
    "17809", "18209", "18309", "18409", "18709", "18809", "19509", "19809",
]


def is_ningxia(text, region=""):
    """判断是否宁夏相关"""
    check_text = f"{text} {region}"
    for kw in NINGXIA_KEYWORDS:
        if kw in check_text:
            return True
    return False


def parse_date(date_val):
    """解析日期"""
    if pd.isna(date_val):
        return None
    if isinstance(date_val, datetime):
        return date_val
    try:
        return pd.to_datetime(date_val)
    except:
        return None


def extract_platform(source):
    """提取平台名称"""
    if pd.isna(source):
        return "unknown"
    source = str(source).lower()
    if "微博" in source or "weibo" in source:
        return "weibo"
    elif "知乎" in source or "zhihu" in source:
        return "zhihu"
    elif "贴吧" in source or "tieba" in source:
        return "baidu_tieba"
    elif "抖音" in source or "douyin" in source:
        return "douyin"
    elif "快手" in source or "kuaishou" in source:
        return "kuaishou"
    elif "小红书" in source or "xiaohongshu" in source:
        return "xiaohongshu"
    elif "头条" in source or "toutiao" in source:
        return "toutiao"
    else:
        return "other"


total_imported = 0
total_skipped = 0

for filepath in files:
    filename = os.path.basename(filepath)
    logger.info(f"\n处理文件: {filename}")
    
    try:
        df = pd.read_excel(filepath)
    except Exception as e:
        logger.error(f"读取失败: {e}")
        continue
    
    # 统一列名映射
    col_mapping = {}
    for col in df.columns:
        col_lower = str(col).lower()
        if "标题" in col_lower or "内容" in col_lower:
            col_mapping["title"] = col
        elif "链接" in col_lower or "网址" in col_lower:
            col_mapping["url"] = col
        elif "来源" in col_lower or "平台" in col_lower or "首发" in col_lower:
            col_mapping["source"] = col
        elif "日期" in col_lower:
            col_mapping["date"] = col
        elif "作者" in col_lower:
            col_mapping["author"] = col
        elif "摘要" in col_lower:
            col_mapping["summary"] = col
        elif "地域" in col_lower or "省份" in col_lower or "归属" in col_lower:
            col_mapping["region"] = col
        elif "转发" in col_lower:
            col_mapping["reposts"] = col
        elif "评论" in col_lower:
            col_mapping["comments"] = col
        elif "点赞" in col_lower or "赞" in col_lower:
            col_mapping["likes"] = col
        elif "粉丝" in col_lower:
            col_mapping["followers"] = col
        elif "阅读" in col_lower:
            col_mapping["views"] = col
    
    logger.info(f"列映射: {col_mapping}")
    
    for idx, row in df.iterrows():
        # 提取内容
        title = str(row.get(col_mapping.get("title", ""), "")) if "title" in col_mapping else ""
        summary = str(row.get(col_mapping.get("summary", ""), "")) if "summary" in col_mapping else ""
        content = f"{title} {summary}".strip()
        
        if not content or content == "nan":
            total_skipped += 1
            continue
        
        # 提取其他字段
        url = str(row.get(col_mapping.get("url", ""), "")) if "url" in col_mapping else ""
        source = str(row.get(col_mapping.get("source", ""), "")) if "source" in col_mapping else ""
        author = str(row.get(col_mapping.get("author", ""), "")) if "author" in col_mapping else ""
        region = str(row.get(col_mapping.get("region", ""), "")) if "region" in col_mapping else ""
        
        # 数值字段
        def safe_int(val):
            try:
                return int(float(val)) if not pd.isna(val) else 0
            except:
                return 0
        
        reposts = safe_int(row.get(col_mapping.get("reposts", ""), 0))
        comments = safe_int(row.get(col_mapping.get("comments", ""), 0))
        likes = safe_int(row.get(col_mapping.get("likes", ""), 0))
        followers = safe_int(row.get(col_mapping.get("followers", ""), 0))
        views = safe_int(row.get(col_mapping.get("views", ""), 0))
        
        # 日期
        pub_date = parse_date(row.get(col_mapping.get("date", ""), None))
        
        # 平台
        platform = extract_platform(source)
        
        # 生成唯一ID
        post_id = f"manual_{filepath.split('/')[-1]}_{idx}"
        
        # 检查是否已存在
        exists = session.query(SentimentPost).filter_by(post_id=post_id).first()
        if exists:
            total_skipped += 1
            continue
        
        # 分析风险
        raw = RawPost(
            platform=platform,
            post_id=post_id,
            title=title,
            content=content,
        )
        result = analyzer.analyze(raw)
        
        # 判断宁夏
        nx = is_ningxia(content, region)
        
        # 创建记录
        post = SentimentPost(
            platform=platform,
            post_id=post_id,
            title=title[:500] if title else None,
            content=content,
            url=url if url != "nan" else None,
            author_name=author if author != "nan" else None,
            author_followers=followers,
            view_count=views,
            like_count=likes,
            comment_count=comments,
            share_count=reposts,
            risk_level=RiskLevel(result.risk_level),
            sentiment_score=result.sentiment_score,
            matched_keywords=",".join(result.matched_high + result.matched_medium),
            is_ningxia=nx,
            published_at=pub_date,
            crawled_at=datetime.utcnow(),
        )
        session.add(post)
        total_imported += 1

session.commit()
logger.success(f"\n导入完成！新增 {total_imported} 条，跳过 {total_skipped} 条")

# 统计
total = session.query(SentimentPost).count()
high = session.query(SentimentPost).filter_by(risk_level=RiskLevel.HIGH).count()
medium = session.query(SentimentPost).filter_by(risk_level=RiskLevel.MEDIUM).count()
low = session.query(SentimentPost).filter_by(risk_level=RiskLevel.LOW).count()
ningxia = session.query(SentimentPost).filter_by(is_ningxia=True).count()
logger.info(f"数据库总量: {total} (高风险={high}, 中风险={medium}, 低风险={low}, 宁夏={ningxia})")

session.close()
