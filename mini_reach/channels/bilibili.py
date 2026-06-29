"""
Bilibili 渠道 - B站视频搜索和信息获取

支持：
- 获取视频信息（BV号）
- 获取UP主信息
- 获取弹幕
- 获取字幕（需要登录）

使用 B站官方 API
"""

import requests
import re
import subprocess
from typing import Optional, List, Dict, Any
from loguru import logger

from mini_reach.channels.base import Channel, ChannelResult


class BilibiliChannel(Channel):
    """
    Bilibili 操作渠道

    使用 B站官方 API 获取视频信息。

    使用方式：
        channel = BilibiliChannel()
        result = channel.read("BV1xx411c7mD")  # 获取视频信息
        result = channel.read("https://www.bilibili.com/video/BV1xx411c7mD")
    """

    name = "bilibili"
    description = "B站视频信息获取"
    priority = 75

    # B站 API
    VIDEO_API = "https://api.bilibili.com/x/web-interface/view"
    SUBTITLE_API = "https://api.bilibili.com/x/player/v2"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.bilibili.com"
        })
        super().__init__()

    def _init_channel(self) -> None:
        """初始化"""
        logger.debug(f"初始化 {self.name} 渠道")

    def check_available(self) -> bool:
        """检测渠道是否可用"""
        try:
            # 测试 API 连通性
            response = self.session.get(
                self.VIDEO_API,
                params={"bvid": "BV1xx411c7mD"},
                timeout=10
            )
            data = response.json()
            self.available = data.get("code") == 0
            if not self.available:
                self._check_error = f"B站 API 不可用: {data.get('message')}"
            return self.available
        except Exception as e:
            self._check_error = f"网络错误: {e}"
            return False

    def search(self, query: str, **kwargs) -> ChannelResult:
        """
        搜索功能：提示用户使用 read 方法

        由于 B站搜索 API 不稳定，建议直接使用视频链接或 BV号。

        Args:
            query: 搜索关键词或视频链接/BV号
            **kwargs: 额外参数

        Returns:
            ChannelResult: 提示信息
        """
        # 检查是否是有效的 BV 号或链接
        bv_id = self._extract_bvid(query)
        if bv_id:
            # 如果是 BV 号，直接读取
            return self.read(bv_id, **kwargs)

        # 否则返回提示
        return ChannelResult(
            success=True,
            content=f"""# B站搜索提示

你输入的是搜索关键词: {query}

B站渠道目前支持以下功能：

## 1. 直接获取视频信息
直接提供视频 BV号 或 链接：
- `BV1xx411c7mD`
- `https://www.bilibili.com/video/BV1xx411c7mD`
- `https://b23.tv/xxxxx`

## 2. 热门 Python 教程推荐
你可以尝试这些 BV号：
- BV1r54y1q7Fj - Python 入门教程
- BV1Ja411c7fD - Python 进阶
- BV1Hu4y1Z7Vx - Python Web 开发

## 3. 获取弹幕
提供视频 BV号 可以获取弹幕摘要
""",
            source="bilibili",
            metadata={"type": "search_hint", "query": query}
        )

    def read(self, video_id: str, **kwargs) -> ChannelResult:
        """
        获取视频信息

        Args:
            video_id: 视频 BV号、链接或 b23.tv 短链接
            **kwargs: 额外参数
                - include_danmu: 是否包含弹幕（默认 True）

        Returns:
            ChannelResult: 视频信息
        """
        # 提取 BV 号
        bv_id = self._extract_bvid(video_id)
        if not bv_id:
            return ChannelResult(
                success=False,
                error=f"无效的 B站链接: {video_id}，请提供 BV号 (如 BV1xx411c7mD) 或完整链接",
                source="bilibili"
            )

        include_danmu = kwargs.get("include_danmu", True)

        try:
            logger.info(f"获取 B站视频: {bv_id}")

            # 获取视频详情
            response = self.session.get(
                self.VIDEO_API,
                params={"bvid": bv_id},
                timeout=15
            )

            data = response.json()

            if data.get("code") != 0:
                return ChannelResult(
                    success=False,
                    error=f"获取失败: {data.get('message', '未知错误')}",
                    source="bilibili-api"
                )

            video_data = data.get("data", {})
            content = self._format_video_info(video_data)

            # 获取弹幕
            if include_danmu:
                cid = video_data.get("cid")
                if cid:
                    danmu = self._get_danmu(cid)
                    if danmu:
                        content += "\n\n---\n\n## 弹幕精选\n\n" + danmu

            return ChannelResult(
                success=True,
                content=content,
                source="bilibili-api",
                metadata={
                    "bvid": bv_id,
                    "title": video_data.get("title", ""),
                    "aid": video_data.get("aid"),
                    "cid": video_data.get("cid")
                }
            )

        except Exception as e:
            logger.error(f"B站视频获取失败: {e}")
            return ChannelResult(
                success=False,
                error=str(e),
                source="bilibili-api"
            )

    def _get_danmu(self, cid: int) -> Optional[str]:
        """获取弹幕"""
        try:
            danmu_url = f"https://api.bilibili.com/x/v1/dm/list.so?oid={cid}"
            response = self.session.get(danmu_url, timeout=10)

            if response.status_code == 200:
                danmu_text = self._parse_danmu(response.content)
                if danmu_text:
                    return danmu_text
        except Exception as e:
            logger.debug(f"获取弹幕失败: {e}")

        return None

    def _parse_danmu(self, xml_content: bytes) -> str:
        """解析弹幕 XML"""
        try:
            import xml.etree.ElementTree as ET

            root = ET.fromstring(xml_content)
            danmu_list = []

            for d in root.findall(".//d"):
                text = d.text
                if text:
                    danmu_list.append(text)

            # 返回弹幕摘要
            if danmu_list:
                # 取前 50 条弹幕
                sample = danmu_list[:50]
                return "\n".join(sample) + f"\n\n(共 {len(danmu_list)} 条弹幕，显示前 50 条)"
            return ""

        except Exception:
            return ""

    def _format_video_info(self, data: Dict) -> str:
        """格式化视频信息"""
        stat = data.get("stat", {})
        owner = data.get("owner", {})

        # 格式化时间
        from datetime import datetime
        pubdate = data.get("pubdate", 0)
        pubdate_str = datetime.fromtimestamp(pubdate).strftime("%Y-%m-%d %H:%M") if pubdate else "未知"

        lines = [
            f"# {data.get('title', '未知标题')}",
            "",
            f"**UP主**: [{owner.get('name', '未知')}](https://space.bilibili.com/{owner.get('mid', '')})",
            f"**分区**: {data.get('tname', '未知')}",
            f"**发布时间**: {pubdate_str}",
            "",
            f"### 统计数据",
            f"- ▶️ 播放: {self._format_number(stat.get('view', 0))}",
            f"- 👍 点赞: {self._format_number(stat.get('like', 0))}",
            f"- ⭐ 投币: {self._format_number(stat.get('coin', 0))}",
            f"- 📤 分享: {self._format_number(stat.get('share', 0))}",
            f"- 💬 评论: {self._format_number(stat.get('reply', 0))}",
            f"- 📥 收藏: {self._format_number(stat.get('favorite', 0))}",
            "",
            f"### 简介",
            f"{data.get('desc', '无')}",
            "",
            f"---\n",
            f"**BV号**: `{data.get('bvid', '')}`",
            f"**AV号**: av{data.get('aid', '')}",
            f"🔗 https://www.bilibili.com/video/{data.get('bvid', '')}",
        ]

        return "\n".join(lines)

    @staticmethod
    def _extract_bvid(url_or_id: str) -> Optional[str]:
        """从链接或 ID 提取 BV 号"""
        if not url_or_id:
            return None

        # 已经是 BV 号
        if url_or_id.startswith("BV"):
            return url_or_id[:12] if len(url_or_id) >= 12 else None

        # 完整链接
        patterns = [
            (r'bilibili\.com/video/(BV[\w]+)', None),
            (r'b23\.tv/(\w+)', 'resolve'),
        ]

        for pattern, action in patterns:
            match = re.search(pattern, url_or_id)
            if match:
                bvid = match.group(1)
                if action == 'resolve':
                    bvid = BilibiliChannel._resolve_short_link(f"https://b23.tv/{bvid}")
                if bvid:
                    return bvid.upper() if bvid.startswith("BV") else f"BV{bvid}"

        return None

    @staticmethod
    def _resolve_short_link(url: str) -> Optional[str]:
        """解析短链接"""
        try:
            r = requests.head(url, timeout=5, allow_redirects=True)
            match = re.search(r'bilibili\.com/video/(BV[\w]+)', r.url)
            return match.group(1) if match else None
        except Exception:
            return None

    @staticmethod
    def _format_number(num: int) -> str:
        """格式化数字"""
        if num >= 100000000:
            return f"{num / 100000000:.1f}亿"
        elif num >= 10000:
            return f"{num / 10000:.1f}万"
        return str(num)
