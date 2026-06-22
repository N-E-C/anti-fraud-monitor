"""
爬虫基类
定义所有平台爬虫的公共接口
"""

import abc
import time
import random
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

import requests
from loguru import logger


@dataclass
class RawPost:
    """原始帖子数据（爬取后未经分析的数据）"""
    platform: str
    post_id: str
    title: str = ""
    content: str = ""
    url: str = ""
    author_name: str = ""
    author_id: str = ""
    author_followers: int = 0
    author_verified: bool = False
    view_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    share_count: int = 0
    published_at: Optional[datetime] = None
    image_urls: List[str] = field(default_factory=list)
    raw_data: dict = field(default_factory=dict)


class BaseCrawler(abc.ABC):
    """
    所有平台爬虫的基类
    继承此类实现各平台的具体爬虫
    """

    PLATFORM_NAME: str = "unknown"

    # 请求头模拟浏览器
    DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }

    def __init__(self, keywords: List[str], proxy: Optional[str] = None):
        self.keywords = keywords
        self.proxy = proxy
        self.session = requests.Session()
        self.session.headers.update(self.DEFAULT_HEADERS)
        if proxy:
            self.session.proxies = {"http": proxy, "https": proxy}

    @abc.abstractmethod
    def search(self, keyword: str, page: int = 1) -> List[RawPost]:
        """
        搜索指定关键词，返回帖子列表
        子类必须实现此方法
        """
        raise NotImplementedError

    def crawl_all_keywords(self, pages_per_keyword: int = 3) -> List[RawPost]:
        """
        遍历所有关键词进行抓取
        """
        results: List[RawPost] = []
        seen_ids = set()

        for keyword in self.keywords:
            logger.info(f"[{self.PLATFORM_NAME}] 搜索关键词: {keyword}")
            for page in range(1, pages_per_keyword + 1):
                try:
                    posts = self.search(keyword, page)
                    for post in posts:
                        if post.post_id not in seen_ids:
                            seen_ids.add(post.post_id)
                            results.append(post)
                    # 随机延迟，避免被封
                    time.sleep(random.uniform(1.5, 3.5))
                except Exception as e:
                    logger.warning(f"[{self.PLATFORM_NAME}] 抓取失败 keyword={keyword} page={page}: {e}")
                    break

        logger.info(f"[{self.PLATFORM_NAME}] 本次共抓取 {len(results)} 条")
        return results

    def _safe_get(self, url: str, params: dict = None, **kwargs) -> Optional[requests.Response]:
        """安全请求，带重试"""
        for attempt in range(3):
            try:
                resp = self.session.get(url, params=params, timeout=10, **kwargs)
                if resp.status_code == 200:
                    return resp
                logger.warning(f"[{self.PLATFORM_NAME}] HTTP {resp.status_code} url={url}")
            except requests.RequestException as e:
                logger.warning(f"[{self.PLATFORM_NAME}] 请求异常 attempt={attempt+1}: {e}")
                time.sleep(2 ** attempt)
        return None
