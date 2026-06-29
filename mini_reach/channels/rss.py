"""
RSS 渠道 - 订阅任意 RSS/Atom 源

支持：
- 读取 RSS/Atom 订阅源
- 解析条目列表
- 获取文章内容摘要
"""

import feedparser
from typing import Optional
from datetime import datetime
from loguru import logger

from mini_reach.channels.base import Channel, ChannelResult


class RSSChannel(Channel):
    """
    RSS 阅读渠道

    使用 feedparser 解析 RSS/Atom 订阅源，
    支持大多数主流博客、新闻网站的 RSS 输出。

    使用方式：
        channel = RSSChannel()
        result = channel.read("https://example.com/feed.xml")
        result = channel.search("https://example.com/feed.xml")
    """

    name = "rss"
    description = "读取 RSS/Atom 订阅源"
    priority = 80

    def __init__(self):
        self._feed_cache: dict = {}
        super().__init__()

    def _init_channel(self) -> None:
        """初始化"""
        logger.debug(f"初始化 {self.name} 渠道")

    def check_available(self) -> bool:
        """
        检测 feedparser 是否可用
        """
        try:
            import feedparser
            self.available = True
            return True
        except ImportError:
            self._check_error = "feedparser 未安装，请运行: pip install feedparser"
            return False

    def read(self, url: str, **kwargs) -> ChannelResult:
        """
        读取 RSS 源

        Args:
            url: RSS/Atom 订阅地址
            **kwargs: 额外参数
                - limit: 返回条目数量（默认 20）

        Returns:
            ChannelResult: RSS 源内容
        """
        limit = kwargs.get("limit", 20)

        try:
            logger.info(f"读取 RSS 源: {url}")

            # 解析 RSS
            feed = feedparser.parse(url)

            if feed.bozo and not feed.entries:
                # 解析错误且没有条目
                return ChannelResult(
                    success=False,
                    error=f"RSS 解析失败: {feed.bozo_exception}",
                    source="feedparser"
                )

            # 格式化输出
            content = self._format_feed(feed, limit)

            logger.info(f"成功读取 RSS，共 {len(feed.entries)} 条")

            return ChannelResult(
                success=True,
                content=content,
                source="feedparser",
                metadata={
                    "title": feed.feed.get("title", "未知"),
                    "url": url,
                    "count": len(feed.entries),
                    "entries": [
                        {
                            "title": entry.get("title", ""),
                            "link": entry.get("link", ""),
                            "published": entry.get("published", "")
                        }
                        for entry in feed.entries[:limit]
                    ]
                }
            )

        except Exception as e:
            logger.error(f"读取 RSS 失败: {e}")
            return ChannelResult(
                success=False,
                error=str(e),
                source="feedparser"
            )

    def search(self, query: str, **kwargs) -> ChannelResult:
        """
        搜索 RSS 条目

        这个实现会读取 RSS 然后过滤匹配的条目。
        query 可以是 URL，也可以是关键词（会搜索匹配的标题/描述）

        Args:
            query: RSS URL 或关键词
            **kwargs: 额外参数

        Returns:
            ChannelResult: 匹配的条目
        """
        # 如果是 URL，直接读取
        if query.startswith("http://") or query.startswith("https://"):
            return self.read(query, **kwargs)

        # 否则返回错误（RSS 不支持关键词搜索）
        return ChannelResult(
            success=False,
            error="RSS 渠道不支持关键词搜索，请提供完整的 RSS URL",
            source="feedparser"
        )

    def _format_feed(self, feed, limit: int = 20) -> str:
        """格式化 RSS 源为可读文本"""
        lines = []

        # 源信息
        title = feed.feed.get("title", "未知标题")
        link = feed.feed.get("link", "")
        description = feed.feed.get("description", "")

        lines.append(f"# {title}")
        if link:
            lines.append(f"🔗 {link}")
        if description:
            lines.append(f"\n{description}")
        lines.append("")

        # 条目列表
        lines.append(f"## 最近更新 ({len(feed.entries)} 条)\n")

        for i, entry in enumerate(feed.entries[:limit], 1):
            entry_title = entry.get("title", "无标题")
            entry_link = entry.get("link", "")
            entry_published = entry.get("published", "未知时间")
            entry_summary = self._clean_html(entry.get("summary", ""))

            lines.append(f"### {i}. {entry_title}")
            lines.append(f"📅 {entry_published}")
            if entry_link:
                lines.append(f"🔗 {entry_link}")
            if entry_summary:
                lines.append(f"\n{entry_summary[:200]}{'...' if len(entry_summary) > 200 else ''}")
            lines.append("")

        return "\n".join(lines)

    def _clean_html(self, text: str) -> str:
        """简单清理 HTML 标签"""
        import re
        # 移除 HTML 标签
        text = re.sub(r'<[^>]+>', '', text)
        # 清理多余空白
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def get_entry_content(self, url: str, entry_link: str) -> ChannelResult:
        """
        获取指定条目的完整内容

        Args:
            url: RSS 源地址
            entry_link: 条目链接

        Returns:
            ChannelResult: 条目内容
        """
        # 先读取 RSS
        result = self.read(url)
        if not result.success:
            return result

        # 查找匹配的条目
        for entry in result.metadata.get("entries", []):
            if entry["link"] == entry_link:
                # 用 WebChannel 获取完整内容
                from mini_reach.channels.web import WebChannel
                web = WebChannel()
                return web.read(entry_link)

        return ChannelResult(
            success=False,
            error=f"未找到条目: {entry_link}",
            source="rss"
        )