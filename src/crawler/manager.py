"""
爬虫管理器
统一调度各平台爬虫，汇聚数据并存库
"""

import os
from typing import List, Dict, Type, Optional
from loguru import logger

from .base import BaseCrawler, RawPost
from .weibo import WeiboCrawler
from .tieba import TiebaCrawler
from .zhihu import ZhihuCrawler

# 尝试导入新平台爬虫（可能未配置）
try:
    from .douyin import DouyinCrawler
    HAS_DOUYIN = True
except ImportError:
    HAS_DOUYIN = False

try:
    from .kuaishou import KuaishouCrawler
    HAS_KUAISHOU = True
except ImportError:
    HAS_KUAISHOU = False

try:
    from .xiaohongshu import XiaohongshuCrawler
    HAS_XIAOHONGSHU = True
except ImportError:
    HAS_XIAOHONGSHU = False


# 已注册的平台爬虫
def get_registered_crawlers() -> Dict[str, Type[BaseCrawler]]:
    """动态获取已注册的爬虫（根据依赖情况）"""
    crawlers = {
        "weibo": WeiboCrawler,
        "baidu_tieba": TiebaCrawler,
        "zhihu": ZhihuCrawler,
    }
    
    # 新平台爬虫（框架代码，需要配置后才能用）
    if HAS_DOUYIN:
        crawlers["douyin"] = DouyinCrawler
    if HAS_KUAISHOU:
        crawlers["kuaishou"] = KuaishouCrawler
    if HAS_XIAOHONGSHU:
        crawlers["xiaohongshu"] = XiaohongshuCrawler
    
    return crawlers


class CrawlerManager:
    """
    爬虫管理器
    统一配置关键词、调度各平台爬虫并汇总结果
    """

    def __init__(self, keywords: List[str], platform_cookies: dict = None, 
                 platform_api_keys: dict = None, proxy: str = None,
                 enabled_platforms: List[str] = None):
        """
        :param keywords: 监控关键词列表
        :param platform_cookies: 各平台 Cookie，格式 {"weibo": "...", "zhihu": "..."}
        :param platform_api_keys: 各平台 API Key（第三方数据平台）
        :param proxy: HTTP 代理（可选）
        :param enabled_platforms: 启用的平台列表（None表示全部启用）
        """
        self.keywords = keywords
        self.platform_cookies = platform_cookies or {}
        self.platform_api_keys = platform_api_keys or {}
        self.proxy = proxy
        self.enabled_platforms = enabled_platforms
        self.crawlers: List[BaseCrawler] = []
        self._init_crawlers()

    def _init_crawlers(self):
        """初始化各平台爬虫实例"""
        registered = get_registered_crawlers()
        
        for platform, CrawlerClass in registered.items():
            # 检查是否启用该平台
            if self.enabled_platforms and platform not in self.enabled_platforms:
                continue
                
            cookie = self.platform_cookies.get(platform, "")
            api_key = self.platform_api_keys.get(platform, "")
            
            try:
                # 根据不同平台传入不同参数
                if platform == "douyin":
                    crawler = CrawlerClass(self.keywords, api_key=api_key, proxy=self.proxy)
                elif platform in ("weibo", "zhihu", "xiaohongshu", "kuaishou", "baidu_tieba"):
                    crawler = CrawlerClass(self.keywords, cookie=cookie, proxy=self.proxy)
                else:
                    crawler = CrawlerClass(self.keywords, proxy=self.proxy)
                    
                self.crawlers.append(crawler)
                logger.info(f"爬虫初始化成功: {platform}")
            except Exception as e:
                logger.warning(f"爬虫初始化失败 {platform}: {e}")

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
