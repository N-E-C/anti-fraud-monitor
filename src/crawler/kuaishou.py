"""
快手爬虫
快手相对抖音来说反爬稍弱，但也没有公开搜索API
"""

import re
from datetime import datetime
from typing import List, Optional

from loguru import logger

from .base import BaseCrawler, RawPost


class KuaishouCrawler(BaseCrawler):
    """快手爬虫（框架）"""

    PLATFORM_NAME = "kuaishou"

    def __init__(self, keywords: List[str], cookie: str = "", proxy: Optional[str] = None):
        super().__init__(keywords, proxy)
        if cookie:
            self.session.headers["Cookie"] = cookie

    def search(self, keyword: str, page: int = 1) -> List[RawPost]:
        """
        搜索快手内容
        
        TODO: 接入实际数据源
        可能的方案：
        1. 快手开放平台（需要申请权限）
        2. 第三方数据服务
        3. 关键词RSS监控
        """
        logger.warning("[kuaishou] 暂未接入实际数据源")
        return []
