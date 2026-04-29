"""
小红书爬虫
小红书反爬机制比较强，直接爬取容易被封
"""

import re
import json
from datetime import datetime
from typing import List, Optional

from loguru import logger

from .base import BaseCrawler, RawPost


class XiaohongshuCrawler(BaseCrawler):
    """小红书爬虫（框架）"""

    PLATFORM_NAME = "xiaohongshu"
    SEARCH_URL = "https://edith.xiaohongshu.com/api/sns/web/v1/search/notes"

    def __init__(self, keywords: List[str], cookie: str = "", proxy: Optional[str] = None):
        super().__init__(keywords, proxy)
        if cookie:
            self.session.headers["Cookie"] = cookie
        self.session.headers.update({
            "Origin": "https://www.xiaohongshu.com",
            "Referer": "https://www.xiaohongshu.com/",
        })

    def search(self, keyword: str, page: int = 1) -> List[RawPost]:
        """
        搜索小红书内容
        
        小红书的搜索接口需要cookie和签名验证
        直接调用很容易被封，建议：
        1. 使用第三方数据平台
        2. 或者降低频率 + 代理池
        """
        logger.warning("[xiaohongshu] 暂未接入实际数据源，反爬较强")
        return []
