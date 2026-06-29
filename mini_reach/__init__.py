"""mini-reach: 让 AI Agent 连接互联网的轻量级工具箱"""

__version__ = "0.1.0"
__author__ = "Jiutian"

from mini_reach.channels.base import Channel
from mini_reach.core import MiniReach

__all__ = ["Channel", "MiniReach", "__version__"]