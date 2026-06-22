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

                # 正文 - 清理掉"展开c"、"收起c"等按钮文本
                content_el = card.select_one(".txt")
                content = content_el.get_text(strip=True) if content_el else ""
                # 清理无关文本
                content = content.replace("展开c", "").replace("收起c", "").replace("展开", "").replace("收起", "").strip()

                # 帖子链接 - 查找格式为 //weibo.com/{用户ID}/{帖子短ID} 的链接
                post_link = None
                for a in card.find_all("a", href=True):
                    href = a.get("href", "")
                    # 匹配格式：//weibo.com/{用户ID}/{帖子短ID}（帖子短ID通常是字母数字组合）
                    if "weibo.com" in href:
                        # 移除协议前缀和查询参数
                        clean_href = href.lstrip("/").split("?")[0]
                        parts = clean_href.split("/")
                        # 格式：weibo.com/用户ID/帖子短ID
                        if len(parts) >= 3 and parts[0] == "weibo.com":
                            user_id = parts[1]
                            post_short_id = parts[2]
                            # 帖子短ID通常是字母数字混合，且较长
                            if post_short_id and len(post_short_id) > 5:
                                post_link = href
                                break
                
                if post_link:
                    # 处理 //weibo.com/... 格式
                    if post_link.startswith("//"):
                        url = f"https:{post_link}"
                    elif post_link.startswith("/"):
                        url = f"https://weibo.com{post_link}"
                    else:
                        url = post_link
                else:
                    # 备选方案：使用帖子ID构造链接
                    url = f"https://weibo.com/{post_id}" if post_id else ""

                # 互动数据 - 微博新版结构：3个li分别是转发、评论、赞
                act_bar = card.select_one(".card-act")
                reposts = 0
                comments = 0
                likes = 0
                if act_bar:
                    lis = act_bar.select("li")
                    if len(lis) >= 3:
                        # 第1个li：转发
                        repost_text = lis[0].get_text(strip=True)
                        reposts = int(repost_text) if repost_text.isdigit() else 0
                        # 第2个li：评论
                        comment_text = lis[1].get_text(strip=True)
                        comments = int(comment_text) if comment_text.isdigit() else 0
                        # 第3个li：赞
                        like_text = lis[2].get_text(strip=True)
                        likes = int(like_text) if like_text.isdigit() else 0

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
            # 新增：解析 "YYYY年MM月DD日 HH:MM" 或 "YY年MM月DD日 HH:MM" 格式
            elif "年" in time_str and "月" in time_str and "日" in time_str:
                match = re.search(r"(\d{2,4})年(\d+)月(\d+).*?(\d+):(\d+)", time_str)
                if match:
                    year = int(match.group(1))
                    # 处理两位数年份（如24 -> 2024）
                    if year < 100:
                        year = 2000 + year
                    month = int(match.group(2))
                    day = int(match.group(3))
                    hour = int(match.group(4))
                    minute = int(match.group(5))
                    return datetime(year, month, day, hour, minute)
            # 解析 "MM月DD日 HH:MM" 格式（无年份）
            elif "月" in time_str and "日" in time_str:
                match = re.search(r"(\d+)月(\d+).*?(\d+):(\d+)", time_str)
                if match:
                    month = int(match.group(1))
                    day = int(match.group(2))
                    hour = int(match.group(3))
                    minute = int(match.group(4))
                    return datetime(now.year, month, day, hour, minute)
        except Exception:
            pass
        return None
