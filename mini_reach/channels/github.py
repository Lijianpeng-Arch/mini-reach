"""
GitHub 渠道 - 使用 gh CLI 操作 GitHub

支持：
- 读取仓库信息
- 读取文件内容
- 读取 README
- 搜索仓库
"""

import subprocess
import json
import os
import shutil
from typing import Optional
from loguru import logger

from mini_reach.channels.base import Channel, ChannelResult


def _find_gh_executable() -> Optional[str]:
    """查找 gh 可执行文件路径"""
    # 1. 尝试直接调用（PATH 中）
    if shutil.which("gh"):
        return "gh"

    # 2. Windows 常见路径
    windows_paths = [
        r"C:\Program Files\GitHub CLI\gh.exe",
        r"C:\Program Files (x86)\GitHub CLI\gh.exe",
    ]
    for path in windows_paths:
        if os.path.exists(path):
            return path

    # 3. 尝试 PATH 环境变量中的目录
    for path in os.environ.get("PATH", "").split(os.pathsep):
        gh_path = os.path.join(path, "gh.exe")
        if os.path.exists(gh_path):
            return gh_path

    return None


class GitHubChannel(Channel):
    """
    GitHub 操作渠道

    使用 GitHub CLI (gh) 与 GitHub API 交互。
    支持读取公开仓库的代码、文件、README 等。

    前置条件：
        - 安装 gh CLI: https://cli.github.com/
        - 运行 gh auth login 进行认证（读取私有仓库需要）

    使用方式：
        channel = GitHubChannel()
        result = channel.read("owner/repo")  # 读取仓库信息
        result = channel.read("owner/repo/path/to/file.txt")  # 读取文件
    """

    name = "github"
    description = "读取 GitHub 仓库和文件（使用 gh CLI）"
    priority = 90

    def __init__(self):
        self.gh_available: bool = False
        self.gh_authenticated: bool = False
        self._gh_path: Optional[str] = None
        super().__init__()

    def _init_channel(self) -> None:
        """初始化时检查 gh CLI 状态"""
        logger.debug(f"初始化 {self.name} 渠道")
        self._gh_path = _find_gh_executable()

    def check_available(self) -> bool:
        """
        检测 gh CLI 是否可用

        检查两个方面：
        1. gh 命令是否存在
        2. 是否已登录（gh auth status）
        """
        if not self._gh_path:
            self._check_error = "gh CLI 未安装，请访问 https://cli.github.com/ 安装"
            return False

        try:
            # 检查 gh 是否安装
            result = subprocess.run(
                [self._gh_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                self._check_error = "gh CLI 未安装或不可用"
                self.gh_available = False
                return False

            self.gh_available = True

            # 检查是否已登录（公开仓库不需要登录，但认证后功能更多）
            auth_result = subprocess.run(
                [self._gh_path, "auth", "status"],
                capture_output=True,
                text=True,
                timeout=5
            )
            self.gh_authenticated = auth_result.returncode == 0

            if not self.gh_authenticated:
                logger.warning("gh CLI 未登录，公开仓库读取功能仍可用")

            self.available = True
            return True

        except FileNotFoundError:
            self._check_error = "gh CLI 未安装，请访问 https://cli.github.com/ 安装"
            return False
        except subprocess.TimeoutExpired:
            self._check_error = "gh CLI 检查超时"
            return False
        except Exception as e:
            self._check_error = f"检查失败: {e}"
            return False

    def _run_gh(self, args: list, timeout: int = 30) -> tuple[int, str, str]:
        """
        运行 gh 命令的辅助方法

        Args:
            args: gh 命令参数列表
            timeout: 超时时间（秒）

        Returns:
            (returncode, stdout, stderr)
        """
        try:
            gh_cmd = [self._gh_path] if self._gh_path else ["gh"]
            result = subprocess.run(
                gh_cmd + args,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "命令超时"
        except Exception as e:
            return -1, "", str(e)

    def search(self, query: str, **kwargs) -> ChannelResult:
        """
        搜索 GitHub 仓库

        Args:
            query: 搜索关键词
            **kwargs: 额外参数
                - limit: 结果数量限制（默认 10）

        Returns:
            ChannelResult: 搜索结果
        """
        limit = kwargs.get("limit", 10)

        if not self.gh_available:
            return ChannelResult(
                success=False,
                error=self._check_error or "gh CLI 不可用",
                source="gh-cli"
            )

        logger.info(f"搜索 GitHub 仓库: {query}")

        returncode, stdout, stderr = self._run_gh([
            "search", "repos", query,
            "--limit", str(limit),
            "--json", "name,owner,description,url,stargazersCount,language"
        ])

        if returncode == 0:
            try:
                repos = json.loads(stdout)
                formatted = self._format_search_results(repos)
                return ChannelResult(
                    success=True,
                    content=formatted,
                    source="gh-cli",
                    metadata={"count": len(repos), "query": query}
                )
            except json.JSONDecodeError as e:
                return ChannelResult(
                    success=False,
                    error=f"解析结果失败: {e}",
                    source="gh-cli"
                )
        else:
            return ChannelResult(
                success=False,
                error=stderr or "搜索失败",
                source="gh-cli"
            )

    def _format_search_results(self, repos: list) -> str:
        """格式化搜索结果为可读文本"""
        if not repos:
            return "未找到匹配的仓库"

        lines = ["# GitHub 仓库搜索结果\n"]
        for i, repo in enumerate(repos, 1):
            lines.append(f"## {i}. {repo['owner']['login']}/{repo['name']}")
            lines.append(f"- ⭐ {repo.get('stargazersCount', 0)}")
            if repo.get('language'):
                lines.append(f"- 🐍 {repo['language']}")
            if repo.get('description'):
                lines.append(f"- {repo['description']}")
            lines.append(f"- 🔗 {repo['url']}")
            lines.append("")

        return "\n".join(lines)

    def read(self, path: str, **kwargs) -> ChannelResult:
        """
        读取 GitHub 内容

        Args:
            path: 仓库路径，格式为 "owner/repo" 或 "owner/repo/path/to/file"
            **kwargs: 额外参数
                - ref: 分支/标签/commit SHA（可选）

        Returns:
            ChannelResult: 内容结果
        """
        if not self.gh_available:
            return ChannelResult(
                success=False,
                error=self._check_error or "gh CLI 不可用",
                source="gh-cli"
            )

        parts = path.strip("/").split("/")
        if len(parts) < 2:
            return ChannelResult(
                success=False,
                error=f"无效的仓库路径: {path}，格式应为 owner/repo 或 owner/repo/path",
                source="gh-cli"
            )

        owner, repo = parts[0], parts[1]
        file_path = "/".join(parts[2:]) if len(parts) > 2 else None
        ref = kwargs.get("ref")

        # 构建命令
        args = ["api", f"repos/{owner}/{repo}"]
        if file_path:
            args[1] = f"repos/{owner}/{repo}/contents/{file_path}"
            if ref:
                args.extend(["--field", f"ref={ref}"])

        logger.info(f"读取 GitHub 内容: {owner}/{repo}" + (f"/{file_path}" if file_path else ""))

        returncode, stdout, stderr = self._run_gh(args)

        if returncode != 0:
            return ChannelResult(
                success=False,
                error=stderr or "读取失败",
                source="gh-cli"
            )

        try:
            data = json.loads(stdout)

            # 如果是文件，返回内容
            if "content" in data:
                import base64
                content = base64.b64decode(data["content"]).decode("utf-8")
                return ChannelResult(
                    success=True,
                    content=content,
                    source="gh-cli",
                    metadata={
                        "path": path,
                        "size": data.get("size", 0),
                        "sha": data.get("sha", ""),
                        "type": data.get("type", "file")
                    }
                )

            # 如果是仓库，返回仓库信息
            return ChannelResult(
                success=True,
                content=self._format_repo_info(data),
                source="gh-cli",
                metadata={
                    "owner": owner,
                    "repo": repo,
                    "stars": data.get("stargazers_count", 0)
                }
            )

        except json.JSONDecodeError as e:
            return ChannelResult(
                success=False,
                error=f"解析响应失败: {e}",
                source="gh-cli"
            )
        except Exception as e:
            return ChannelResult(
                success=False,
                error=str(e),
                source="gh-cli"
            )

    def _format_repo_info(self, data: dict) -> str:
        """格式化仓库信息"""
        lines = [
            f"# {data['full_name']}",
            "",
            f"{data.get('description', '无描述')}",
            "",
            f"- ⭐ {data.get('stargazers_count', 0)} Stars",
            f"- 🍴 {data.get('forks_count', 0)} Forks",
            f"- 👁 {data.get('watchers_count', 0)} Watchers",
            "",
            f"**语言**: {data.get('language', '未知')}",
            f"**许可证**: {data.get('license', {}).get('name') or '无' if isinstance(data.get('license'), dict) else '无'}",
            f"**最后更新**: {data.get('pushed_at', '未知')}",
            "",
            f"🔗 {data.get('html_url', '')}"
        ]
        return "\n".join(lines)

    def read_file(self, owner: str, repo: str, path: str, ref: Optional[str] = None) -> ChannelResult:
        """
        读取仓库中的文件

        Args:
            owner: 仓库所有者
            repo: 仓库名
            path: 文件路径
            ref: 分支/标签（可选）

        Returns:
            ChannelResult: 文件内容
        """
        return self.read(f"{owner}/{repo}/{path}", ref=ref)

    def get_readme(self, owner: str, repo: str) -> ChannelResult:
        """
        获取仓库的 README

        Args:
            owner: 仓库所有者
            repo: 仓库名

        Returns:
            ChannelResult: README 内容
        """
        return self.read(f"{owner}/{repo}/README.md")