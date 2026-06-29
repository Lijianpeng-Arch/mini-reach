"""
mini-reach 核心模块

统一管理所有渠道，提供简单的 API 访问。
"""

from typing import Optional, Type
from loguru import logger

from mini_reach.channels.base import Channel, ChannelResult
from mini_reach.channels.web import WebChannel
from mini_reach.channels.github import GitHubChannel
from mini_reach.channels.rss import RSSChannel
from mini_reach.channels.youtube import YouTubeChannel
from mini_reach.channels.bilibili import BilibiliChannel


class MiniReach:
    """
    mini-reach 主入口类

    统一管理所有渠道，提供简单易用的 API。

    使用方式：
        mr = MiniReach()
        result = mr.read("web", "https://example.com")
        result = mr.search("github", "react hooks")
    """

    def __init__(self, auto_init: bool = True):
        """
        初始化 mini-reach

        Args:
            auto_init: 是否自动初始化并检查所有渠道（默认 True）
        """
        self._channels: dict[str, Channel] = {}
        self._channel_classes: dict[str, Type[Channel]] = {
            "web": WebChannel,
            "github": GitHubChannel,
            "rss": RSSChannel,
            "youtube": YouTubeChannel,
            "bilibili": BilibiliChannel,
        }

        if auto_init:
            self._init_channels()

    def _init_channels(self) -> None:
        """初始化所有渠道"""
        logger.info("初始化渠道...")

        for name, channel_class in self._channel_classes.items():
            try:
                channel = channel_class()
                # 检查渠道是否可用
                channel.ensure_available()
                self._channels[name] = channel
                logger.info(f"✅ 渠道 {name} 就绪")
            except Exception as e:
                logger.warning(f"⚠️ 渠道 {name} 不可用: {e}")

    @property
    def available_channels(self) -> list[str]:
        """获取所有可用的渠道列表"""
        return list(self._channels.keys())

    def get_channel(self, name: str) -> Optional[Channel]:
        """
        获取指定渠道

        Args:
            name: 渠道名称（如 "web", "github"）

        Returns:
            Channel 对象，如果不存在返回 None
        """
        return self._channels.get(name)

    def register_channel(self, name: str, channel: Channel) -> None:
        """
        注册一个新渠道

        Args:
            name: 渠道名称
            channel: Channel 实例
        """
        self._channels[name] = channel
        logger.info(f"已注册渠道: {name}")

    def read(self, channel_name: str, url: str, **kwargs) -> ChannelResult:
        """
        读取内容

        Args:
            channel_name: 渠道名称
            url: 资源标识符（URL、仓库路径等）
            **kwargs: 额外参数

        Returns:
            ChannelResult: 操作结果
        """
        channel = self._channels.get(channel_name)
        if not channel:
            return ChannelResult(
                success=False,
                error=f"未知渠道: {channel_name}，可用渠道: {self.available_channels}"
            )

        try:
            return channel.read(url, **kwargs)
        except Exception as e:
            logger.error(f"读取失败 [{channel_name}]: {e}")
            return ChannelResult(
                success=False,
                error=str(e),
                source=channel_name
            )

    def search(self, channel_name: str, query: str, **kwargs) -> ChannelResult:
        """
        搜索内容

        Args:
            channel_name: 渠道名称
            query: 搜索关键词
            **kwargs: 额外参数

        Returns:
            ChannelResult: 搜索结果
        """
        channel = self._channels.get(channel_name)
        if not channel:
            return ChannelResult(
                success=False,
                error=f"未知渠道: {channel_name}，可用渠道: {self.available_channels}"
            )

        try:
            return channel.search(query, **kwargs)
        except Exception as e:
            logger.error(f"搜索失败 [{channel_name}]: {e}")
            return ChannelResult(
                success=False,
                error=str(e),
                source=channel_name
            )

    def health_check(self) -> dict:
        """
        健康检查

        Returns:
            dict: 所有渠道的健康状态
        """
        status = {
            "total": len(self._channel_classes),
            "available": 0,
            "channels": []
        }

        for name, channel_class in self._channel_classes.items():
            try:
                channel = self._channels.get(name)
                if channel:
                    health = channel.health_check()
                else:
                    # 尝试实例化检查
                    channel = channel_class()
                    health = channel.health_check()

                if health["available"]:
                    status["available"] += 1

                status["channels"].append(health)
            except Exception as e:
                status["channels"].append({
                    "name": name,
                    "available": False,
                    "error": str(e)
                })

        return status

    def doctor(self) -> None:
        """诊断所有渠道的状态"""
        from rich.console import Console
        from rich.table import Table

        console = Console()
        health = self.health_check()

        console.print("\n📋 mini-reach 渠道诊断\n")
        console.print(f"总渠道数: {health['total']}")
        console.print(f"可用渠道: {health['available']}\n")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("渠道", style="cyan")
        table.add_column("状态", justify="center")
        table.add_column("描述")

        for ch in health["channels"]:
            status = "✅ 可用" if ch["available"] else "❌ 不可用"
            error = f"\n  原因: {ch.get('error', '未知')}" if not ch["available"] else ""
            table.add_row(
                ch["name"],
                status,
                ch.get("description", "") + error
            )

        console.print(table)

        if health["available"] == 0:
            console.print("\n⚠️ 没有可用渠道，请检查配置或安装依赖")

    def __repr__(self) -> str:
        return f"<MiniReach channels={self.available_channels}>"


# 便捷函数
def create() -> MiniReach:
    """创建 MiniReach 实例的便捷函数"""
    return MiniReach()


def read(channel: str, url: str, **kwargs) -> ChannelResult:
    """快速读取内容的便捷函数"""
    mr = MiniReach()
    return mr.read(channel, url, **kwargs)


def search(channel: str, query: str, **kwargs) -> ChannelResult:
    """快速搜索的便捷函数"""
    mr = MiniReach()
    return mr.search(channel, query, **kwargs)