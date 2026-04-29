"""
配置加载工具
"""

import os
import yaml
from dotenv import load_dotenv

load_dotenv()


def load_config() -> dict:
    """加载环境变量配置"""
    return {
        "database_url": os.getenv("DATABASE_URL", "sqlite:///data/monitor.db"),
        "crawl_interval": int(os.getenv("CRAWL_INTERVAL_MINUTES", "60")),
        "report_hour": int(os.getenv("REPORT_HOUR", "8")),
        "log_level": os.getenv("LOG_LEVEL", "INFO"),
    }


def load_keywords(config_path: str = "config/keywords.yaml") -> dict:
    """加载关键词配置"""
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data.get("keywords", {})
    except FileNotFoundError:
        return {"high_risk": [], "medium_risk": [], "neutral": []}
