#!/usr/bin/env python3
"""
数据库迁移脚本
添加 is_ningxia、image_urls 字段和 crawl_logs 表
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

import sqlite3
from loguru import logger

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{PROJECT_ROOT}/data/monitor.db")

# 从 URL 中提取路径
if DATABASE_URL.startswith("sqlite:///"):
    db_path = DATABASE_URL.replace("sqlite:///", "")
else:
    db_path = os.path.join(PROJECT_ROOT, "data", "monitor.db")

logger.info(f"数据库路径: {db_path}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # 检查 sentiment_posts 表是否有 is_ningxia 列
    cursor.execute("PRAGMA table_info(sentiment_posts)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if "is_ningxia" not in columns:
        logger.info("添加 is_ningxia 列...")
        cursor.execute("ALTER TABLE sentiment_posts ADD COLUMN is_ningxia BOOLEAN DEFAULT 0")
        conn.commit()
        logger.success("is_ningxia 列添加成功")
    else:
        logger.info("is_ningxia 列已存在")
    
    if "image_urls" not in columns:
        logger.info("添加 image_urls 列...")
        cursor.execute("ALTER TABLE sentiment_posts ADD COLUMN image_urls TEXT")
        conn.commit()
        logger.success("image_urls 列添加成功")
    else:
        logger.info("image_urls 列已存在")
    
    # 检查 crawl_logs 表是否存在
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='crawl_logs'")
    if not cursor.fetchone():
        logger.info("创建 crawl_logs 表...")
        cursor.execute("""
            CREATE TABLE crawl_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform VARCHAR(50) NOT NULL,
                status VARCHAR(20) DEFAULT 'success',
                keywords_count INTEGER DEFAULT 0,
                new_posts_count INTEGER DEFAULT 0,
                error_message TEXT,
                started_at DATETIME,
                finished_at DATETIME,
                duration_seconds INTEGER
            )
        """)
        conn.commit()
        logger.success("crawl_logs 表创建成功")
    else:
        logger.info("crawl_logs 表已存在")
    
    logger.success("数据库迁移完成！")
    
except Exception as e:
    logger.error(f"迁移失败: {e}")
    conn.rollback()
finally:
    conn.close()
