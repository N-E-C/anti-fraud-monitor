"""
爬虫管理器
统一调度各平台爬虫，汇聚数据并存库
"""

from typing import List, Dict, Type
from loguru import logger

from .base import BaseCrawler, RawPost
from .weibo import WeiboCrawler
from .tieba import TiebaCrawler
from .zhihu import ZhihuCrawler


# 已注册的平台爬虫
REGISTERED_CRAWLERS: Dict[str, Type[BaseCrawler]] = {
    "weibo": WeiboCrawler,
    "baidu_tieba": TiebaCrawler,
    "zhihu": ZhihuCrawler,
    # TODO: 后续可接入 douyin / xiaohongshu / bilibili
}


class CrawlerManager:
    """
    爬虫管理器
    统一配置关键词、调度各平台爬虫并汇总结果
    """

    def __init__(self, keywords: List[str], platform_cookies: dict = None, proxy: str = None):
        """
        :param keywords: 监控关键词列表
        :param platform_cookies: 各平台 Cookie，格式 {"weibo": "...", "zhihu": "..."}
        :param proxy: HTTP 代理（可选）
        """
        self.keywords = keywords
        self.platform_cookies = platform_cookies or {}
        self.proxy = proxy
        self.crawlers: List[BaseCrawler] = []
        self._init_crawlers()

    def _init_crawlers(self):
        """初始化各平台爬虫实例"""
        for platform, CrawlerClass in REGISTERED_CRAWLERS.items():
            cookie = self.platform_cookies.get(platform, "")
            try:
                if platform in ("weibo", "zhihu"):
                    crawler = CrawlerClass(self.keywords, cookie=cookie, proxy=self.proxy)
                else:
                    crawler = CrawlerClass(self.keywords, proxy=self.proxy)
                self.crawlers.append(crawler)
                logger.info(f"爬虫初始化: {platform}")
            except Exception as e:
                logger.error(f"爬虫初始化失败 {platform}: {e}")

    def run_all(self, pages_per_keyword: int = 2) -> List[RawPost]:
        """
        运行所有平台的爬虫
        :return: 汇总的原始帖子列表
        """
        all_posts: List[RawPost] = []
        for crawler in self.crawlers:
            try:
                posts = crawler.crawl_all_keywords(pages_per_keyword)
                all_posts.extend(posts)
                logger.info(f"平台 {crawler.PLATFORM_NAME} 抓取完成，新增 {len(posts)} 条")
            except Exception as e:
                logger.error(f"平台 {crawler.PLATFORM_NAME} 运行失败: {e}")

        logger.info(f"本轮全平台共抓取 {len(all_posts)} 条")
        return all_posts
