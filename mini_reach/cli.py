"""
mini-reach CLI - 命令行工具

用法:
    mini-reach read web https://example.com
    mini-reach read github owner/repo
    mini-reach search github react hooks
    mini-reach doctor
    mini-reach --help
"""

import argparse
import sys
from loguru import logger

from mini_reach import __version__
from mini_reach.core import MiniReach


def setup_logging(verbose: bool = False) -> None:
    """配置日志输出"""
    logger.remove()
    level = "DEBUG" if verbose else "INFO"
    logger.add(sys.stderr, level=level, format="<level>{message}</level>")


def cmd_read(args) -> int:
    """读取命令"""
    mr = MiniReach()
    result = mr.read(args.channel, args.url)

    if result.success:
        print(result.content)
        return 0
    else:
        print(f"❌ 读取失败: {result.error}", file=sys.stderr)
        return 1


def cmd_search(args) -> int:
    """搜索命令"""
    mr = MiniReach()
    result = mr.search(args.channel, args.query, limit=args.limit)

    if result.success:
        print(result.content)
        return 0
    else:
        print(f"❌ 搜索失败: {result.error}", file=sys.stderr)
        return 1


def cmd_doctor(args) -> int:
    """诊断命令"""
    mr = MiniReach()
    mr.doctor()
    return 0


def cmd_list_channels(args) -> int:
    """列出所有渠道"""
    mr = MiniReach()
    health = mr.health_check()

    print(f"\n📦 mini-reach 渠道列表\n")
    print(f"可用渠道: {health['available']}/{health['total']}\n")

    for ch in health["channels"]:
        status = "✅" if ch["available"] else "❌"
        print(f"  {status} {ch['name']:<12} - {ch.get('description', '')}")

    return 0


def main() -> int:
    """主入口"""
    parser = argparse.ArgumentParser(
        prog="mini-reach",
        description="让 AI Agent 连接互联网的轻量级工具箱",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  mini-reach read web https://github.com
  mini-reach read github anthropics/claude-code
  mini-reach search github python async
  mini-reach doctor

支持渠道:
  web     - 网页阅读（Jina Reader）
  github  - GitHub 仓库和文件
  rss     - RSS/Atom 订阅源
  youtube - YouTube 视频字幕
        """
    )

    parser.add_argument("--version", action="version", version=f"mini-reach {__version__}")
    parser.add_argument("-v", "--verbose", action="store_true", help="显示详细日志")

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # read 命令
    read_parser = subparsers.add_parser("read", help="读取内容")
    read_parser.add_argument("channel", choices=["web", "github", "rss", "youtube"], help="渠道名称")
    read_parser.add_argument("url", help="URL 或资源路径")
    read_parser.set_defaults(func=cmd_read)

    # search 命令
    search_parser = subparsers.add_parser("search", help="搜索内容")
    search_parser.add_argument("channel", choices=["github", "youtube"], help="渠道名称")
    search_parser.add_argument("query", help="搜索关键词")
    search_parser.add_argument("--limit", "-n", type=int, default=10, help="结果数量（默认 10）")
    search_parser.set_defaults(func=cmd_search)

    # doctor 命令
    doctor_parser = subparsers.add_parser("doctor", help="诊断渠道状态")
    doctor_parser.set_defaults(func=cmd_doctor)

    # channels 命令
    channels_parser = subparsers.add_parser("channels", help="列出所有渠道")
    channels_parser.set_defaults(func=cmd_list_channels)

    # 解析参数
    args = parser.parse_args()

    # 配置日志
    setup_logging(args.verbose)

    # 无命令时显示帮助
    if not args.command:
        parser.print_help()
        return 0

    # 执行命令
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())