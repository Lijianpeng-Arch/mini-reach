"""
YouTube 渠道 - 提取视频字幕和元信息

支持：
- 获取视频字幕（自动生成或手动上传）
- 获取视频基本信息
- 搜索视频
"""

import subprocess
import json
import re
from typing import Optional
from loguru import logger

from mini_reach.channels.base import Channel, ChannelResult


class YouTubeChannel(Channel):
    """
    YouTube 操作渠道

    使用 yt-dlp 提取视频字幕和元信息。
    支持自动字幕和手动上传的字幕。

    使用方式：
        channel = YouTubeChannel()
        result = channel.read("https://youtube.com/watch?v=xxx")  # 获取字幕
        result = channel.read("video_id")  # 用视频 ID
    """

    name = "youtube"
    description = "提取 YouTube 视频字幕（使用 yt-dlp）"
    priority = 70

    def __init__(self):
        self.yt_dlp_available: bool = False
        self._yt_dlp_path: Optional[str] = None
        super().__init__()

    def _init_channel(self) -> None:
        """初始化时检查 yt-dlp"""
        logger.debug(f"初始化 {self.name} 渠道")

    def check_available(self) -> bool:
        """
        检测 yt-dlp 是否可用
        """
        try:
            # 尝试调用 yt-dlp
            result = subprocess.run(
                ["yt-dlp", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                self.yt_dlp_available = True
                self._yt_dlp_path = "yt-dlp"
                self.available = True
                return True

            self._check_error = "yt-dlp 运行失败"
            return False

        except FileNotFoundError:
            self._check_error = "yt-dlp 未安装，请运行: pip install yt-dlp"
            return False
        except Exception as e:
            self._check_error = f"检查失败: {e}"
            return False

    def read(self, video: str, **kwargs) -> ChannelResult:
        """
        读取视频字幕

        Args:
            video: 视频 URL 或视频 ID
            **kwargs: 额外参数
                - lang: 字幕语言（默认 zh-Hans）
                - format: 输出格式（text/markdown，默认 text）

        Returns:
            ChannelResult: 字幕内容
        """
        if not self.yt_dlp_available:
            return ChannelResult(
                success=False,
                error=self._check_error or "yt-dlp 不可用",
                source="yt-dlp"
            )

        lang = kwargs.get("lang", "zh-Hans,zh-Hant,en")
        output_format = kwargs.get("format", "text")

        # 提取视频 ID
        video_id = self._extract_video_id(video)
        if not video_id:
            return ChannelResult(
                success=False,
                error=f"无效的 YouTube URL: {video}",
                source="yt-dlp"
            )

        logger.info(f"提取 YouTube 字幕: {video_id}")

        # 构建 yt-dlp 命令
        # 使用 --write-auto-sub 获取自动字幕
        # 使用 --skip-download 不下载视频
        # 使用 --sub-langs 指定语言
        # 使用 --convert-subs 转成文本

        cmd = [
            self._yt_dlp_path,
            "--no-playlist",
            "--write-auto-sub",
            "--write-subs",
            "--sub-langs", lang,
            "--skip-download",
            "--dump-json",
            f"https://www.youtube.com/watch?v={video_id}"
        ]

        try:
            # 先获取视频信息
            info_result = subprocess.run(
                [self._yt_dlp_path, "--dump-json", f"https://www.youtube.com/watch?v={video_id}"],
                capture_output=True,
                text=True,
                timeout=30
            )

            if info_result.returncode != 0:
                return ChannelResult(
                    success=False,
                    error=f"获取视频信息失败: {info_result.stderr}",
                    source="yt-dlp"
                )

            info = json.loads(info_result.stdout)
            video_title = info.get("title", "未知标题")
            video_duration = info.get("duration", 0)
            video_uploader = info.get("uploader", "未知作者")

            # 尝试下载字幕
            subtitle_result = self._download_subtitle(video_id, lang)

            if subtitle_result.success:
                content = f"""# {video_title}

**作者**: {video_uploader}
**时长**: {self._format_duration(video_duration)}
**链接**: https://youtube.com/watch?v={video_id}

---

## 字幕

{subtitle_result.content}
"""
            else:
                # 没有字幕，返回视频信息
                content = f"""# {video_title}

**作者**: {video_uploader}
**时长**: {self._format_duration(video_duration)}
**链接**: https://youtube.com/watch?v={video_id}

---

⚠️ 此视频没有可用字幕（可能原因：
- 视频没有字幕
- 自动字幕未生成
- 不支持该语言）
"""

            return ChannelResult(
                success=True,
                content=content,
                source="yt-dlp",
                metadata={
                    "video_id": video_id,
                    "title": video_title,
                    "uploader": video_uploader,
                    "duration": video_duration,
                    "has_subtitle": subtitle_result.success
                }
            )

        except subprocess.TimeoutExpired:
            return ChannelResult(
                success=False,
                error="下载超时",
                source="yt-dlp"
            )
        except json.JSONDecodeError:
            return ChannelResult(
                success=False,
                error="解析视频信息失败",
                source="yt-dlp"
            )
        except Exception as e:
            logger.error(f"读取 YouTube 失败: {e}")
            return ChannelResult(
                success=False,
                error=str(e),
                source="yt-dlp"
            )

    def search(self, query: str, **kwargs) -> ChannelResult:
        """
        搜索 YouTube 视频

        这个实现会使用 Invidious API 进行搜索，
        不需要 YouTube API key。

        Args:
            query: 搜索关键词
            **kwargs: 额外参数
                - limit: 结果数量（默认 10）

        Returns:
            ChannelResult: 搜索结果
        """
        limit = kwargs.get("limit", 10)

        logger.info(f"搜索 YouTube: {query}")

        # 使用 Invidious 实例搜索
        try:
            import requests
            response = requests.get(
                "https://yewtu.be/api/v1/search",
                params={
                    "q": query,
                    "type": "video",
                    "limit": limit
                },
                timeout=15
            )

            if response.status_code == 200:
                videos = response.json()
                content = self._format_search_results(query, videos)

                return ChannelResult(
                    success=True,
                    content=content,
                    source="invidious-api",
                    metadata={"count": len(videos), "query": query}
                )
            else:
                return ChannelResult(
                    success=False,
                    error=f"搜索失败: HTTP {response.status_code}",
                    source="invidious-api"
                )

        except Exception as e:
            logger.error(f"YouTube 搜索失败: {e}")
            return ChannelResult(
                success=False,
                error=f"搜索失败: {e}",
                source="invidious-api"
            )

    def _download_subtitle(self, video_id: str, lang: str) -> ChannelResult:
        """下载字幕文件"""
        import os
        import tempfile

        try:
            # 创建临时目录
            with tempfile.TemporaryDirectory() as tmpdir:
                output_template = os.path.join(tmpdir, "subtitle")

                cmd = [
                    self._yt_dlp_path,
                    "--no-playlist",
                    "--write-auto-sub",
                    "--write-subs",
                    "--sub-langs", lang,
                    "--skip-download",
                    "--convert-subs", "vtt",
                    "-o", output_template,
                    f"https://www.youtube.com/watch?v={video_id}"
                ]

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                # 检查是否有字幕文件生成
                vtt_files = [f for f in os.listdir(tmpdir) if f.endswith(".vtt")]
                if vtt_files:
                    with open(os.path.join(tmpdir, vtt_files[0]), "r", encoding="utf-8") as f:
                        vtt_content = f.read()

                    # 转换 VTT 为纯文本
                    text = self._vtt_to_text(vtt_content)
                    return ChannelResult(
                        success=True,
                        content=text,
                        source="yt-dlp"
                    )

                return ChannelResult(
                    success=False,
                    error="未找到字幕文件",
                    source="yt-dlp"
                )

        except Exception as e:
            return ChannelResult(
                success=False,
                error=str(e),
                source="yt-dlp"
            )

    def _vtt_to_text(self, vtt_content: str) -> str:
        """将 VTT 字幕转换为纯文本"""
        lines = vtt_content.split("\n")
        text_lines = []

        for line in lines:
            # 跳过时间轴和标签
            if "-->" in line:
                continue
            if line.strip().startswith("WEBVTT"):
                continue
            if line.strip().startswith("NOTE"):
                continue
            if not line.strip():
                continue
            # 清理 HTML 标签
            line = re.sub(r"<[^>]+>", "", line)
            text_lines.append(line.strip())

        return "\n".join(text_lines)

    @staticmethod
    def _extract_video_id(url_or_id: str) -> Optional[str]:
        """从 URL 或 ID 提取视频 ID"""
        # 如果直接是视频 ID（11位字母数字）
        if re.match(r'^[a-zA-Z0-9_-]{11}$', url_or_id):
            return url_or_id

        # 从 URL 提取
        patterns = [
            r'(?:v=|/v/|youtu\.be/)([a-zA-Z0-9_-]{11})',
            r'watch\?v=([a-zA-Z0-9_-]{11})',
        ]

        for pattern in patterns:
            match = re.search(pattern, url_or_id)
            if match:
                return match.group(1)

        return None

    @staticmethod
    def _format_duration(seconds: int) -> str:
        """格式化时长"""
        if seconds < 60:
            return f"{seconds}秒"
        elif seconds < 3600:
            return f"{seconds // 60}分{seconds % 60}秒"
        else:
            return f"{seconds // 3600}小时{(seconds % 3600) // 60}分"

    def _format_search_results(self, query: str, videos: list) -> str:
        """格式化搜索结果"""
        if not videos:
            return f"未找到与「{query}」相关的视频"

        lines = [f"# YouTube 搜索: {query}\n"]

        for i, video in enumerate(videos, 1):
            title = video.get("title", "无标题")
            video_id = video.get("videoId", "")
            author = video.get("author", "未知")
            length = video.get("lengthSeconds", 0)
            views = video.get("viewCount", 0)

            lines.append(f"## {i}. {title}")
            lines.append(f"- 👤 {author}")
            lines.append(f"- ⏱ {self._format_duration(int(length))}")
            lines.append(f"- 👁 {views:,} 次观看")
            lines.append(f"- 🔗 https://youtube.com/watch?v={video_id}")
            lines.append("")

        return "\n".join(lines)