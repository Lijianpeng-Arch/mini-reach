"""
Channel 基类 - 统一接口设计

每个平台（Web、GitHub、YouTube等）都实现这个接口，
提供统一的 search() 和 read() 方法。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional
from loguru import logger


@dataclass
class ChannelResult:
    """渠道操作结果"""
    success: bool
    content: Any = None
    error: Optional[str] = None
    source: str = ""  # 使用的后端来源
    metadata: dict = field(default_factory=dict)

    def __repr__(self) -> str:
        if self.success:
            return f"<ChannelResult success=True source={self.source}>"
        return f"<ChannelResult success=False error={self.error}>"


class Channel(ABC):
    """
    渠道抽象基类

    所有平台渠道必须实现以下方法：
    - check_available(): 检测渠道是否可用
    - search(): 搜索内容
    - read(): 读取具体内容
    """

    name: str = "base"  # 渠道名称
    description: str = ""  # 渠道描述
    priority: int = 0  # 优先级（数字越大越优先）

    def __init__(self):
        self.available: bool = False
        self._checked: bool = False
        self._check_error: Optional[str] = None
        self._init_channel()

    def _init_channel(self) -> None:
        """初始化渠道（可选重写）"""
        pass

    @abstractmethod
    def check_available(self) -> bool:
        """
        检测渠道是否可用

        Returns:
            True: 渠道可用
            False: 渠道不可用
        """
        pass

    def ensure_available(self) -> None:
        """确保渠道可用，不可用则抛出异常"""
        if not self._checked:
            self.available = self.check_available()
            self._checked = True

        if not self.available:
            raise RuntimeError(
                f"渠道 {self.name} 不可用: {self._check_error or 'check_available() 返回 False'}"
            )

    @abstractmethod
    def search(self, query: str, **kwargs) -> ChannelResult:
        """
        搜索内容

        Args:
            query: 搜索关键词
            **kwargs: 额外参数

        Returns:
            ChannelResult: 搜索结果
        """
        pass

    @abstractmethod
    def read(self, url: str, **kwargs) -> ChannelResult:
        """
        读取具体内容

        Args:
            url: 资源标识符（URL、仓库名等）
            **kwargs: 额外参数

        Returns:
            ChannelResult: 读取结果
        """
        pass

    def health_check(self) -> dict:
        """
        健康检查

        Returns:
            dict: 健康状态信息
        """
        if not self._checked:
            self.available = self.check_available()
            self._checked = True

        return {
            "name": self.name,
            "available": self.available,
            "error": self._check_error,
            "description": self.description,
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name} available={self.available}>"


class SimpleChannel(Channel):
    """
    简化版渠道基类

    适用于不需要复杂后端路由的平台，
    只用一种后端就能完成所有操作。
    """

    def check_available(self) -> bool:
        return True

    def search(self, query: str, **kwargs) -> ChannelResult:
        # 默认实现：把 query 当作 URL 直接读取
        return self.read(query, **kwargs)

    def read(self, url: str, **kwargs) -> ChannelResult:
        raise NotImplementedError(f"{self.__class__.__name__} 必须实现 read() 方法")


@dataclass
class SearchOptions:
    """搜索选项"""
    limit: int = 10  # 结果数量限制
    lang: Optional[str] = None  # 语言筛选
    time_range: Optional[str] = None  # 时间范围
    sort_by: str = "relevance"  # 排序方式