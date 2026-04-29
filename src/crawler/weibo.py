"""
微博爬虫
通过微博搜索接口抓取相关舆情内容

注意：
- 微博有反爬机制，需配合 Cookie 使用
- 搜索接口：https://s.weibo.com/weibo?q=<关键词>
- 建议配置有效的微博 Cookie 以提高成功率
"""

import re
from datetime import datetime
from typing import List, Optional
from urllib.parse import quote

from bs4 import BeautifulSoup
from loguru import logger

from .base import BaseCrawler, RawPost


class WeiboCrawler(BaseCrawler):
    """微博搜索爬虫"""

    PLATFORM_NAME = "weibo"
    SEARCH_URL = "https://s.weibo.com/weibo"

    def __init__(self, keywords: List[str], cookie: str = "", proxy: Optional[str] = None):
        super().__init__(keywords, proxy)
        if cookie:
            self.session.headers["Cookie"] = cookie
        # 微博需要 Referer
        self.session.headers["Referer"] = "https://weibo.com/"

    def search(self, keyword: str, page: int = 1) -> List[RawPost]:
        """搜索微博"""
        params = {
            "q": keyword,
            "page": page,
            "typeall": 1,
        }
        resp = self._safe_get(self.SEARCH_URL, params=params)
        if not resp:
            return []

        return self._parse_search_results(resp.text, keyword)

    def _parse_search_results(self, html: str, keyword: str) -> List[RawPost]:
        """解析微博搜索结果页面"""
        posts = []
        soup = BeautifulSoup(html, "lxml")

        for card in soup.select(".card-wrap[mid]"):
            try:
                post_id = card.get("mid", "")
                if not post_id:
                    continue

                # 作者信息
                author_el = card.select_one(".name")
                author_name = author_el.get_text(strip=True) if author_el else ""
                author_href = author_el.get("href", "") if author_el else ""
                author_id = re.search(r"uid=(\d+)", author_href)
                author_id = author_id.group(1) if author_id else ""

                # 粉丝数（部分情况可获取）
                verified = bool(card.select_one(".icon-vip, .icon-svip, .icon-verify"))

                # 正文
                content_el = card.select_one(".txt")
                content = content_el.get_text(strip=True) if content_el else ""

                # 帖子链接
                link_el = card.select_one("a[href*='/detail/']")
                url = f"https://weibo.com{link_el['href']}" if link_el else ""

                # 互动数据
                reposts = self._extract_count(card, "转发")
                comments = self._extract_count(card, "评论")
                likes = self._extract_count(card, "赞")

                # 发布时间
                time_el = card.select_one(".from a")
                published_at = self._parse_time(time_el.get_text(strip=True) if time_el else "")

                posts.append(RawPost(
                    platform=self.PLATFORM_NAME,
                    post_id=post_id,
                    content=content,
                    url=url,
                    author_name=author_name,
                    author_id=author_id,
                    author_verified=verified,
                    share_count=reposts,
                    comment_count=comments,
                    like_count=likes,
                    published_at=published_at,
                ))
            except Exception as e:
                logger.debug(f"[weibo] 解析单条失败: {e}")
                continue

        return posts

    @staticmethod
    def _extract_count(card, label: str) -> int:
        """从卡片中提取数字（转发/评论/赞）"""
        for el in card.select("a"):
            text = el.get_text(strip=True)
            if label in text:
                nums = re.findall(r"\d+", text)
                return int(nums[0]) if nums else 0
        return 0

    @staticmethod
    def _parse_time(time_str: str) -> Optional[datetime]:
        """解析微博时间字符串"""
        now = datetime.now()
        try:
            if "分钟前" in time_str:
                mins = int(re.search(r"\d+", time_str).group())
                return now.replace(second=0, microsecond=0)
            elif "今天" in time_str:
                t = re.search(r"(\d+):(\d+)", time_str)
                if t:
                    return now.replace(hour=int(t.group(1)), minute=int(t.group(2)), second=0, microsecond=0)
            elif re.match(r"\d{2}-\d{2}", time_str):
                parts = time_str.split("-")
                return datetime(now.year, int(parts[0]), int(parts[1]))
        except Exception:
            pass
        return None
