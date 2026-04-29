"""
知乎爬虫
通过知乎搜索接口抓取相关内容（问答/文章）
"""

import re
import json
from datetime import datetime
from typing import List, Optional

from loguru import logger

from .base import BaseCrawler, RawPost


class ZhihuCrawler(BaseCrawler):
    """知乎搜索爬虫"""

    PLATFORM_NAME = "zhihu"
    SEARCH_API = "https://www.zhihu.com/api/v4/search_v3"

    def __init__(self, keywords: List[str], cookie: str = "", proxy: Optional[str] = None):
        super().__init__(keywords, proxy)
        self.session.headers.update({
            "x-requested-with": "fetch",
            "Referer": "https://www.zhihu.com/search",
        })
        if cookie:
            self.session.headers["Cookie"] = cookie

    def search(self, keyword: str, page: int = 1) -> List[RawPost]:
        """搜索知乎内容"""
        params = {
            "t": "general",
            "q": keyword,
            "correction": 1,
            "offset": (page - 1) * 20,
            "limit": 20,
            "filter_fields": "",
        }
        resp = self._safe_get(self.SEARCH_API, params=params)
        if not resp:
            return []

        try:
            data = resp.json()
            return self._parse(data)
        except Exception as e:
            logger.warning(f"[zhihu] JSON解析失败: {e}")
            return []

    def _parse(self, data: dict) -> List[RawPost]:
        """解析知乎搜索API返回数据"""
        posts = []
        items = data.get("data", [])

        for item in items:
            try:
                obj = item.get("object", {})
                obj_type = obj.get("type", "")

                if obj_type == "answer":
                    post_id = str(obj.get("id", ""))
                    question = obj.get("question", {})
                    title = question.get("title", "")
                    content = re.sub(r"<[^>]+>", "", obj.get("content", ""))[:500]
                    url = f"https://www.zhihu.com/question/{question.get('id')}/answer/{post_id}"
                    author = obj.get("author", {})
                    author_name = author.get("name", "")
                    author_id = author.get("url_token", "")
                    author_followers = author.get("follower_count", 0)
                    like_count = obj.get("voteup_count", 0)
                    comment_count = obj.get("comment_count", 0)
                    published_at = datetime.fromtimestamp(obj.get("created_time", 0))

                elif obj_type == "article":
                    post_id = str(obj.get("id", ""))
                    title = obj.get("title", "")
                    content = re.sub(r"<[^>]+>", "", obj.get("content", ""))[:500]
                    url = f"https://zhuanlan.zhihu.com/p/{post_id}"
                    author = obj.get("author", {})
                    author_name = author.get("name", "")
                    author_id = author.get("url_token", "")
                    author_followers = author.get("follower_count", 0)
                    like_count = obj.get("voteup_count", 0)
                    comment_count = obj.get("comment_count", 0)
                    published_at = datetime.fromtimestamp(obj.get("created", 0))
                else:
                    continue

                posts.append(RawPost(
                    platform=self.PLATFORM_NAME,
                    post_id=post_id,
                    title=title,
                    content=content,
                    url=url,
                    author_name=author_name,
                    author_id=author_id,
                    author_followers=author_followers,
                    like_count=like_count,
                    comment_count=comment_count,
                    published_at=published_at,
                ))
            except Exception as e:
                logger.debug(f"[zhihu] 解析单条失败: {e}")

        return posts
