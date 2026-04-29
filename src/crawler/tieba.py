"""
百度贴吧爬虫
通过百度贴吧搜索接口抓取相关帖子
贴吧是反诈投诉的高频平台之一
"""

import re
from datetime import datetime
from typing import List, Optional

from bs4 import BeautifulSoup
from loguru import logger

from .base import BaseCrawler, RawPost


class TiebaCrawler(BaseCrawler):
    """百度贴吧爬虫"""

    PLATFORM_NAME = "baidu_tieba"
    SEARCH_URL = "https://tieba.baidu.com/f/search/res"

    def search(self, keyword: str, page: int = 1) -> List[RawPost]:
        """搜索贴吧帖子"""
        params = {
            "isnew": 1,
            "kw": "",           # 吧名（留空全局搜索）
            "qw": keyword,      # 搜索关键词
            "rn": 10,           # 每页条数
            "pn": (page - 1) * 10,
        }
        resp = self._safe_get(self.SEARCH_URL, params=params)
        if not resp:
            return []

        return self._parse(resp.text)

    def _parse(self, html: str) -> List[RawPost]:
        """解析贴吧搜索结果"""
        posts = []
        soup = BeautifulSoup(html, "lxml")

        for item in soup.select(".s_post"):
            try:
                # 标题和链接
                title_el = item.select_one(".p_title a")
                title = title_el.get_text(strip=True) if title_el else ""
                url = title_el.get("href", "") if title_el else ""
                if url and not url.startswith("http"):
                    url = "https://tieba.baidu.com" + url

                # 帖子ID
                post_id = re.search(r"/(\d+)", url)
                post_id = post_id.group(1) if post_id else url

                # 摘要内容
                content_el = item.select_one(".p_content")
                content = content_el.get_text(strip=True) if content_el else ""

                # 作者
                author_el = item.select_one(".p_author_name")
                author_name = author_el.get_text(strip=True) if author_el else ""

                # 时间
                time_el = item.select_one(".p_date")
                time_str = time_el.get_text(strip=True) if time_el else ""
                published_at = self._parse_time(time_str)

                # 回复数
                reply_el = item.select_one(".p_reply")
                comment_count = 0
                if reply_el:
                    nums = re.findall(r"\d+", reply_el.get_text())
                    comment_count = int(nums[0]) if nums else 0

                posts.append(RawPost(
                    platform=self.PLATFORM_NAME,
                    post_id=post_id,
                    title=title,
                    content=content,
                    url=url,
                    author_name=author_name,
                    comment_count=comment_count,
                    published_at=published_at,
                ))
            except Exception as e:
                logger.debug(f"[tieba] 解析单条失败: {e}")

        return posts

    @staticmethod
    def _parse_time(time_str: str) -> Optional[datetime]:
        try:
            # 格式：2024-01-15 10:30
            return datetime.strptime(time_str.strip(), "%Y-%m-%d %H:%M")
        except Exception:
            return None
