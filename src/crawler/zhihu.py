"""
知乎爬虫
通过知乎搜索接口抓取相关舆情
"""

import re
from datetime import datetime
from typing import List, Optional

from loguru import logger

from .base import BaseCrawler, RawPost


class ZhihuCrawler(BaseCrawler):
    """知乎爬虫"""

    PLATFORM_NAME = "zhihu"

    SEARCH_URL = "https://www.zhihu.com/api/v4/search_v3"

    def search(self, keyword: str, page: int = 1) -> List[RawPost]:
        """搜索知乎"""
        posts = []
        params = {
            "t": "general",
            "q": keyword,
            "correction": 1,
            "offset": (page - 1) * 20,
            "limit": 20,
        }

        try:
            resp = self._safe_get(self.SEARCH_URL, params=params)
            if not resp:
                return posts

            data = resp.json()
            items = data.get("data", [])

            for item in items:
                try:
                    obj = item.get("object", {})
                    obj_type = obj.get("type", "")

                    # 回答
                    if obj_type == "answer":
                        post_id = str(obj.get("id", ""))
                        question = obj.get("question", {})
                        title = question.get("title", "")
                        content = re.sub(r"<[^>]+>", "", obj.get("content", ""))[:500]
                        url = f"https://www.zhihu.com/question/{question.get('id', '')}/answer/{post_id}"
                        author = obj.get("author", {})
                        author_name = author.get("name", "")
                        author_id = author.get("url_token", "")
                        author_followers = author.get("follower_count", 0)
                        like_count = obj.get("voteup_count", 0)
                        comment_count = obj.get("comment_count", 0)
                        ts = obj.get("created_time", 0)
                        published_at = datetime.fromtimestamp(ts) if ts and ts > 0 else None

                    # 文章
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
                        ts = obj.get("created", 0)
                        published_at = datetime.fromtimestamp(ts) if ts and ts > 0 else None
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

        except Exception as e:
            logger.error(f"[zhihu] 搜索失败: {e}")

        return posts
