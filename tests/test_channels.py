"""
mini-reach 单元测试

运行方式：
    pytest tests/ -v
    pytest tests/ -v -k web  # 只跑 web 相关的
"""

import pytest
from mini_reach.channels.base import Channel, ChannelResult


class TestChannelResult:
    """测试 ChannelResult 数据类"""

    def test_success_result(self):
        result = ChannelResult(success=True, content="test content")
        assert result.success is True
        assert result.content == "test content"
        assert result.error is None

    def test_error_result(self):
        result = ChannelResult(success=False, error="Something went wrong")
        assert result.success is False
        assert result.error == "Something went wrong"

    def test_result_with_metadata(self):
        result = ChannelResult(
            success=True,
            content="data",
            source="test-source",
            metadata={"key": "value"}
        )
        assert result.source == "test-source"
        assert result.metadata == {"key": "value"}

    def test_result_repr(self):
        success = ChannelResult(success=True, source="test")
        assert "success=True" in repr(success)

        error = ChannelResult(success=False, error="fail")
        assert "success=False" in repr(error)


class TestChannelBasics:
    """测试 Channel 基类"""

    def test_channel_subclass_must_implement(self):
        """测试子类必须实现抽象方法"""
        # Channel 是抽象类，直接实例化会报错
        with pytest.raises(TypeError):
            Channel()

    def test_channel_abstract_methods_exist(self):
        """测试 Channel 有抽象方法"""
        assert hasattr(Channel, 'check_available')
        assert hasattr(Channel, 'search')
        assert hasattr(Channel, 'read')

    def test_complete_channel_implementation(self):
        """测试完整的 Channel 实现"""

        class CompleteChannel(Channel):
            name = "complete"
            description = "A complete implementation"
            priority = 10

            def check_available(self) -> bool:
                return True

            def search(self, query: str, **kwargs):
                return ChannelResult(success=True, content=f"search: {query}")

            def read(self, url: str, **kwargs):
                return ChannelResult(success=True, content=f"read: {url}")

        channel = CompleteChannel()

        # check_available
        assert channel.check_available() is True

        # search
        result = channel.search("test")
        assert result.success is True
        assert result.content == "search: test"

        # read
        result = channel.read("http://example.com")
        assert result.success is True
        assert result.content == "read: http://example.com"

    def test_health_check(self):
        """测试健康检查"""

        class HealthyChannel(Channel):
            name = "healthy"

            def check_available(self) -> bool:
                return True

            def search(self, query: str, **kwargs):
                return ChannelResult(success=True)

            def read(self, url: str, **kwargs):
                return ChannelResult(success=True)

        channel = HealthyChannel()
        health = channel.health_check()

        assert health["name"] == "healthy"
        assert health["available"] is True
        assert health["error"] is None


class TestWebChannel:
    """测试 Web 渠道"""

    def test_is_url_validation(self):
        """测试 URL 验证"""
        from mini_reach.channels.web import WebChannel

        assert WebChannel._is_url("https://example.com") is True
        assert WebChannel._is_url("http://example.com") is True
        assert WebChannel._is_url("www.example.com") is True
        assert WebChannel._is_url("example.com") is False
        assert WebChannel._is_url("not a url") is False

    def test_web_channel_available(self):
        """测试 Web 渠道可用性"""
        from mini_reach.channels.web import WebChannel

        channel = WebChannel()
        # Web 渠道始终可用（有备选方案）
        assert channel.check_available() is True
        assert channel.available is True

    def test_web_read_invalid_url(self):
        """测试读取无效 URL"""
        from mini_reach.channels.web import WebChannel

        channel = WebChannel()
        result = channel.read("not a valid url")

        assert result.success is False
        assert "无效的 URL" in result.error

    def test_web_read_http_url(self):
        """测试读取 http URL"""
        from mini_reach.channels.web import WebChannel

        channel = WebChannel()
        result = channel.read("http://example.com")

        # 可能成功也可能失败（取决于网络）
        # 但不应该报"无效 URL"
        if not result.success:
            assert "无效的 URL" not in result.error


class TestGitHubChannel:
    """测试 GitHub 渠道"""

    def test_github_channel_initialization(self):
        """测试 GitHub 渠道初始化"""
        from mini_reach.channels.github import GitHubChannel

        channel = GitHubChannel()
        assert channel.name == "github"
        assert hasattr(channel, "gh_available")
        assert hasattr(channel, "gh_authenticated")

    def test_github_check_available(self):
        """测试 GitHub 可用性检查"""
        from mini_reach.channels.github import GitHubChannel

        channel = GitHubChannel()
        # 检查 gh CLI 是否可用
        result = channel.check_available()
        # 结果取决于系统是否安装了 gh CLI
        assert isinstance(result, bool)

    def test_github_read_invalid_path(self):
        """测试读取无效路径"""
        from mini_reach.channels.github import GitHubChannel

        channel = GitHubChannel()
        # 如果 gh CLI 可用，测试无效路径
        if channel.check_available():
            result = channel.read("invalid")
            assert result.success is False
            assert "无效的" in result.error


class TestRSSChannel:
    """测试 RSS 渠道"""

    def test_rss_channel_initialization(self):
        """测试 RSS 渠道初始化"""
        from mini_reach.channels.rss import RSSChannel

        channel = RSSChannel()
        assert channel.name == "rss"
        assert channel.check_available() is True

    def test_rss_clean_html(self):
        """测试 HTML 清理"""
        from mini_reach.channels.rss import RSSChannel

        channel = RSSChannel()

        # 测试基本清理
        html = "<p>Hello <b>World</b></p>"
        text = channel._clean_html(html)
        assert "Hello" in text
        assert "World" in text
        assert "<" not in text
        assert ">" not in text


class TestYouTubeChannel:
    """测试 YouTube 渠道"""

    def test_youtube_channel_initialization(self):
        """测试 YouTube 渠道初始化"""
        from mini_reach.channels.youtube import YouTubeChannel

        channel = YouTubeChannel()
        assert channel.name == "youtube"

    def test_extract_video_id(self):
        """测试视频 ID 提取"""
        from mini_reach.channels.youtube import YouTubeChannel

        # 直接 ID
        assert YouTubeChannel._extract_video_id("dQw4w9WgXcQ") == "dQw4w9WgXcQ"

        # 标准 URL
        assert YouTubeChannel._extract_video_id(
            "https://youtube.com/watch?v=dQw4w9WgXcQ"
        ) == "dQw4w9WgXcQ"

        # 短 URL
        assert YouTubeChannel._extract_video_id(
            "https://youtu.be/dQw4w9WgXcQ"
        ) == "dQw4w9WgXcQ"

        # 无效 URL
        assert YouTubeChannel._extract_video_id("invalid") is None

    def test_format_duration(self):
        """测试时长格式化"""
        from mini_reach.channels.youtube import YouTubeChannel

        assert YouTubeChannel._format_duration(30) == "30秒"
        assert YouTubeChannel._format_duration(90) == "1分30秒"
        assert YouTubeChannel._format_duration(3661) == "1小时1分"
        assert YouTubeChannel._format_duration(7200) == "2小时0分"
        assert YouTubeChannel._format_duration(0) == "0秒"


class TestMiniReach:
    """测试 MiniReach 核心"""

    def test_minireach_initialization(self):
        """测试 MiniReach 初始化"""
        from mini_reach import MiniReach

        mr = MiniReach()
        assert hasattr(mr, "_channels")
        assert hasattr(mr, "_channel_classes")

    def test_available_channels(self):
        """测试获取可用渠道"""
        from mini_reach import MiniReach

        mr = MiniReach()
        channels = mr.available_channels

        # 至少应该有 web 渠道
        assert "web" in channels
        assert isinstance(channels, list)

    def test_get_channel(self):
        """测试获取指定渠道"""
        from mini_reach import MiniReach

        mr = MiniReach()
        web = mr.get_channel("web")
        assert web is not None
        assert web.name == "web"

        # 获取不存在的渠道
        nonexistent = mr.get_channel("nonexistent")
        assert nonexistent is None

    def test_read_unknown_channel(self):
        """测试读取未知渠道"""
        from mini_reach import MiniReach

        mr = MiniReach()
        result = mr.read("unknown", "test")
        assert result.success is False
        assert "未知渠道" in result.error

    def test_search_unknown_channel(self):
        """测试搜索未知渠道"""
        from mini_reach import MiniReach

        mr = MiniReach()
        result = mr.search("unknown", "test")
        assert result.success is False
        assert "未知渠道" in result.error

    def test_health_check(self):
        """测试健康检查"""
        from mini_reach import MiniReach

        mr = MiniReach()
        health = mr.health_check()

        assert "total" in health
        assert "available" in health
        assert "channels" in health
        assert isinstance(health["channels"], list)


# 集成测试（需要网络）
class TestIntegration:
    """集成测试"""

    @pytest.mark.integration
    def test_rss_read(self):
        """测试读取真实 RSS 源"""
        from mini_reach import MiniReach

        mr = MiniReach()
        result = mr.read("rss", "https://feeds.bbci.co.uk/news/technology/rss.xml")

        # 如果网络正常，应该成功
        if result.success:
            assert "BBC" in result.content or "News" in result.content

    @pytest.mark.integration
    def test_github_search(self):
        """测试 GitHub 搜索"""
        from mini_reach import MiniReach

        mr = MiniReach()
        result = mr.search("github", "python test")

        if result.success:
            assert "search" in result.content.lower() or "python" in result.content.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
