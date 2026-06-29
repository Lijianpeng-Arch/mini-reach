"""
Web 渠道 - 读取任意网页

使用多种后端：
1. Jina Reader（首选）- 将网页转成 Markdown
2. 直接请求（备选）- 原始 HTML

无需登录，零配置，直接可用。
"""

import requests
from typing import Optional
from loguru import logger

from mini_reach.channels.base import Channel, ChannelResult


class WebChannel(Channel):
    """
    网页阅读渠道

    使用多种方式获取网页内容：
    1. Jina Reader API（首选）- 将网页转换为 Markdown
    2. 直接请求（备选）- 返回原始 HTML

    使用方式：
        channel = WebChannel()
        result = channel.read("https://github.com/...")
        print(result.content)
    """

    name = "web"
    description = "读取任意网页内容"
    priority = 100

    # Jina Reader API
    JINA_READER_URL = "https://r.jina.ai/"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        self._jina_available: Optional[bool] = None
        super().__init__()

    def _init_channel(self) -> None:
        """初始化"""
        logger.debug(f"初始化 {self.name} 渠道")

    def check_available(self) -> bool:
        """检测渠道是否可用"""
        self.available = True  # 始终可用
        return True

    def read(self, url: str, **kwargs) -> ChannelResult:
        """
        读取网页内容

        Args:
            url: 网页 URL
            **kwargs: 额外参数
                - timeout: 超时时间（默认 30 秒）

        Returns:
            ChannelResult: 网页内容
        """
        timeout = kwargs.get("timeout", 30)

        # 验证 URL 格式
        if not self._is_url(url):
            return ChannelResult(
                success=False,
                error=f"无效的 URL 格式: {url}",
                source="web"
            )

        # 优先尝试 Jina Reader
        if self._jina_available is None:
            self._jina_available = self._check_jina()

        if self._jina_available:
            result = self._read_with_jina(url, timeout)
            if result.success:
                return result

        # 降级到直接请求
        return self._read_direct(url, timeout)

    def _check_jina(self) -> bool:
        """检查 Jina API 是否可用"""
        try:
            response = self.session.get(
                self.JINA_READER_URL,
                params={"url": "https://example.com"},
                timeout=5
            )
            return response.status_code == 200
        except Exception:
            return False

    def _read_with_jina(self, url: str, timeout: int) -> ChannelResult:
        """使用 Jina Reader 读取"""
        try:
            logger.info(f"使用 Jina 读取: {url}")
            response = self.session.get(
                f"{self.JINA_READER_URL}{url}",
                timeout=timeout
            )

            if response.status_code == 200:
                content = response.text
                if not content.strip():
                    return ChannelResult(success=False, error="内容为空", source="jina")
                return ChannelResult(
                    success=True,
                    content=content,
                    source="jina-reader",
                    metadata={"url": url, "length": len(content)}
                )
            elif response.status_code == 429:
                self._jina_available = False
                return ChannelResult(success=False, error="请求过于频繁", source="jina")
            else:
                return ChannelResult(success=False, error=f"HTTP {response.status_code}", source="jina")

        except requests.exceptions.Timeout:
            return ChannelResult(success=False, error="超时", source="jina")
        except Exception as e:
            self._jina_available = False
            return ChannelResult(success=False, error=str(e), source="jina")

    def _read_direct(self, url: str, timeout: int) -> ChannelResult:
        """直接请求网页"""
        try:
            logger.info(f"直接读取: {url}")
            response = self.session.get(url, timeout=timeout)

            if response.status_code == 200:
                content = response.text
                # 简单提取纯文本
                text = self._html_to_text(content)
                return ChannelResult(
                    success=True,
                    content=text,
                    source="direct",
                    metadata={"url": url, "length": len(text)}
                )
            else:
                return ChannelResult(
                    success=False,
                    error=f"HTTP {response.status_code}",
                    source="direct"
                )

        except Exception as e:
            return ChannelResult(success=False, error=str(e), source="direct")

    def _html_to_text(self, html: str) -> str:
        """简单 HTML 转纯文本"""
        import re
        # 移除 script 和 style 标签
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.I)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.I)
        # 移除 HTML 标签
        html = re.sub(r'<[^>]+>', ' ', html)
        # 清理空白
        html = re.sub(r'\s+', ' ', html).strip()
        return html

    def search(self, query: str, **kwargs) -> ChannelResult:
        """Web 搜索：直接读取"""
        return self.read(query, **kwargs)

    @staticmethod
    def _is_url(text: str) -> bool:
        """判断是否为 URL"""
        text = text.strip().lower()
        return text.startswith("http://") or text.startswith("https://") or text.startswith("www.")

    def extract_links(self, content: str) -> list:
        """从内容中提取链接"""
        import re
        pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        matches = re.findall(pattern, content)
        return [{"title": title, "url": url} for title, url in matches]
