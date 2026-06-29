"""
Web 渠道 - 使用 Jina Reader 读取任意网页

无需登录，零配置，直接可用。
Jina Reader 会把网页转成干净的 Markdown 格式。
"""

import requests
from typing import Optional
from loguru import logger

from mini_reach.channels.base import Channel, ChannelResult


class WebChannel(Channel):
    """
    网页阅读渠道

    使用 Jina Reader API 将网页转换为 Markdown，
    方便 AI Agent 理解和处理。

    使用方式：
        channel = WebChannel()
        result = channel.read("https://github.com/...")
        print(result.content)
    """

    name = "web"
    description = "读取任意网页内容（使用 Jina Reader）"
    priority = 100  # 最高优先级

    # Jina Reader API 端点
    JINA_READER_URL = "https://r.jina.ai/"
    JINA_HEADER = "Accept: text/plain"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "mini-reach/0.1.0 (AI Agent Web Reader)"
        })
        super().__init__()

    def _init_channel(self) -> None:
        """初始化时检查 Jina API 是否可用"""
        logger.debug(f"初始化 {self.name} 渠道")

    def check_available(self) -> bool:
        """
        检测 Jina Reader API 是否可用

        发送一个简单请求验证连接性。
        """
        try:
            response = self.session.get(
                self.JINA_READER_URL,
                params={"url": "https://example.com"},
                timeout=10
            )
            self.available = response.status_code == 200
            if not self.available:
                self._check_error = f"Jina API 返回状态码 {response.status_code}"
            return self.available
        except requests.exceptions.Timeout:
            self._check_error = "Jina API 超时"
            return False
        except requests.exceptions.RequestException as e:
            self._check_error = f"网络错误: {e}"
            return False

    def search(self, query: str, **kwargs) -> ChannelResult:
        """
        搜索功能：直接调用 read()

        对于 Web 渠道，搜索和读取使用相同的方法，
        因为 Jina 本身就是一个内容提取工具。

        Args:
            query: 搜索关键词（这里当作 URL 使用）
            **kwargs: 额外参数

        Returns:
            ChannelResult: 网页内容
        """
        # 如果 query 不是 URL 格式，尝试作为 URL 直接读取
        if not self._is_url(query):
            logger.warning(f"Web search 收到非 URL 输入: {query}，直接读取")
        return self.read(query, **kwargs)

    def read(self, url: str, **kwargs) -> ChannelResult:
        """
        读取网页内容

        Args:
            url: 网页 URL
            **kwargs: 额外参数
                - timeout: 超时时间（默认 30 秒）

        Returns:
            ChannelResult: 网页的 Markdown 内容
        """
        timeout = kwargs.get("timeout", 30)

        # 验证 URL 格式
        if not self._is_url(url):
            return ChannelResult(
                success=False,
                error=f"无效的 URL 格式: {url}",
                source="jina-reader"
            )

        try:
            logger.info(f"读取网页: {url}")

            # 使用 Jina Reader API
            response = self.session.get(
                f"{self.JINA_READER_URL}{url}",
                timeout=timeout
            )

            if response.status_code == 200:
                content = response.text

                # 检查内容是否为空
                if not content.strip():
                    return ChannelResult(
                        success=False,
                        error="网页内容为空",
                        source="jina-reader"
                    )

                # 检查是否被拦截
                if "The site is blocking automated access" in content:
                    return ChannelResult(
                        success=False,
                        error="网站阻止了自动化访问",
                        source="jina-reader"
                    )

                logger.info(f"成功读取网页，内容长度: {len(content)} 字符")

                return ChannelResult(
                    success=True,
                    content=content,
                    source="jina-reader",
                    metadata={
                        "url": url,
                        "length": len(content),
                        "chars": content[:200]  # 预览前 200 字符
                    }
                )

            elif response.status_code == 429:
                return ChannelResult(
                    success=False,
                    error="请求过于频繁，请稍后再试",
                    source="jina-reader"
                )

            else:
                return ChannelResult(
                    success=False,
                    error=f"HTTP {response.status_code}: {response.reason}",
                    source="jina-reader"
                )

        except requests.exceptions.Timeout:
            return ChannelResult(
                success=False,
                error=f"读取超时（{timeout}秒）",
                source="jina-reader"
            )

        except requests.exceptions.RequestException as e:
            logger.error(f"读取网页失败: {e}")
            return ChannelResult(
                success=False,
                error=f"网络错误: {e}",
                source="jina-reader"
            )

    @staticmethod
    def _is_url(text: str) -> bool:
        """简单判断是否为 URL"""
        text = text.strip().lower()
        return (
            text.startswith("http://") or
            text.startswith("https://") or
            text.startswith("www.")
        )

    def extract_links(self, content: str) -> list:
        """
        从 Markdown 内容中提取链接

        用于搜索结果展示。
        """
        import re
        pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        matches = re.findall(pattern, content)
        return [{"title": title, "url": url} for title, url in matches]