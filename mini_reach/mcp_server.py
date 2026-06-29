"""
mini-reach MCP 服务器

将 mini-reach 作为 MCP (Model Context Protocol) 服务器运行，
让 Claude Code 等 AI 工具可以直接调用。

运行方式：
    python -m mini_reach.mcp_server
    # 或者
    mini-reach mcp
"""

import json
import sys
from typing import Any, Optional

from loguru import logger

from mini_reach.core import MiniReach


class MCPProtocol:
    """
    简化的 MCP 协议处理器

    支持的 JSON-RPC 方法：
    - tools/list: 列出所有可用工具
    - tools/call: 调用指定工具
    """

    def __init__(self):
        self.mr = MiniReach()

    def handle_request(self, request: dict) -> dict:
        """
        处理 MCP 请求

        Args:
            request: JSON-RPC 请求

        Returns:
            JSON-RPC 响应
        """
        method = request.get("method", "")
        request_id = request.get("id")

        try:
            if method == "tools/list":
                result = self.list_tools()
            elif method == "tools/call":
                params = request.get("params", {})
                result = self.call_tool(
                    params.get("name", ""),
                    params.get("arguments", {})
                )
            elif method == "initialize":
                result = self.initialize()
            elif method == "shutdown":
                result = self.shutdown()
            else:
                return self.error_response(
                    request_id,
                    -32601,
                    f"Method not found: {method}"
                )

            return self.success_response(request_id, result)

        except Exception as e:
            logger.error(f"MCP 请求处理失败: {e}")
            return self.error_response(request_id, -32603, str(e))

    @staticmethod
    def success_response(request_id: Optional[Any], result: Any) -> dict:
        """构建成功响应"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result
        }

    @staticmethod
    def error_response(request_id: Optional[Any], code: int, message: str) -> dict:
        """构建错误响应"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message
            }
        }

    def initialize(self) -> dict:
        """初始化"""
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": "mini-reach",
                "version": "0.1.0"
            }
        }

    def shutdown(self) -> dict:
        """关闭"""
        return {"success": True}

    def list_tools(self) -> dict:
        """列出所有可用工具"""
        tools = []

        # Web 读取
        tools.append({
            "name": "web_read",
            "description": "读取任意网页内容，返回 Markdown 格式",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "网页 URL"
                    },
                    "timeout": {
                        "type": "number",
                        "description": "超时时间（秒）",
                        "default": 30
                    }
                },
                "required": ["url"]
            }
        })

        # GitHub 搜索
        tools.append({
            "name": "github_search",
            "description": "搜索 GitHub 仓库",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词"
                    },
                    "limit": {
                        "type": "number",
                        "description": "结果数量限制",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        })

        # GitHub 读取
        tools.append({
            "name": "github_read",
            "description": "读取 GitHub 仓库信息或文件",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "仓库路径，格式: owner/repo 或 owner/repo/path"
                    },
                    "ref": {
                        "type": "string",
                        "description": "分支/标签（可选）"
                    }
                },
                "required": ["path"]
            }
        })

        # RSS 读取
        tools.append({
            "name": "rss_read",
            "description": "读取 RSS/Atom 订阅源",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "RSS 订阅地址"
                    },
                    "limit": {
                        "type": "number",
                        "description": "返回条目数量",
                        "default": 20
                    }
                },
                "required": ["url"]
            }
        })

        # YouTube 字幕
        tools.append({
            "name": "youtube_subtitle",
            "description": "提取 YouTube 视频字幕",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "video": {
                        "type": "string",
                        "description": "视频 URL 或视频 ID"
                    },
                    "lang": {
                        "type": "string",
                        "description": "字幕语言",
                        "default": "zh-Hans,zh-Hant,en"
                    }
                },
                "required": ["video"]
            }
        })

        # 渠道诊断
        tools.append({
            "name": "doctor",
            "description": "诊断所有渠道状态",
            "inputSchema": {
                "type": "object",
                "properties": {}
            }
        })

        return {"tools": tools}

    def call_tool(self, name: str, arguments: dict) -> dict:
        """
        调用工具

        Args:
            name: 工具名称
            arguments: 工具参数

        Returns:
            工具执行结果
        """
        logger.info(f"调用工具: {name} with args: {arguments}")

        if name == "web_read":
            result = self.mr.read("web", arguments.get("url", ""))
            return self._format_result(result)

        elif name == "github_search":
            result = self.mr.search(
                "github",
                arguments.get("query", ""),
                limit=arguments.get("limit", 10)
            )
            return self._format_result(result)

        elif name == "github_read":
            result = self.mr.read("github", arguments.get("path", ""))
            return self._format_result(result)

        elif name == "rss_read":
            result = self.mr.read("rss", arguments.get("url", ""))
            return self._format_result(result)

        elif name == "youtube_subtitle":
            result = self.mr.read(
                "youtube",
                arguments.get("video", ""),
                lang=arguments.get("lang", "zh-Hans,zh-Hant,en")
            )
            return self._format_result(result)

        elif name == "doctor":
            health = self.mr.health_check()
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(health, ensure_ascii=False, indent=2)
                    }
                ]
            }

        else:
            raise ValueError(f"Unknown tool: {name}")

    def _format_result(self, result) -> dict:
        """格式化 ChannelResult 为 MCP 响应"""
        if result.success:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": result.content or ""
                    }
                ],
                "metadata": result.metadata
            }
        else:
            return {
                "isError": True,
                "content": [
                    {
                        "type": "text",
                        "text": f"错误: {result.error}"
                    }
                ]
            }


def run_stdio_server():
    """通过标准输入/输出运行 MCP 服务器"""
    mcp = MCPProtocol()

    while True:
        try:
            # 读取一行 JSON-RPC 请求
            line = sys.stdin.readline()
            if not line:
                break

            request = json.loads(line)
            response = mcp.handle_request(request)

            # 输出响应
            print(json.dumps(response), flush=True)

        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败: {e}")
            print(json.dumps({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32700,
                    "message": f"Parse error: {e}"
                }
            }), flush=True)

        except KeyboardInterrupt:
            break


def main():
    """主入口"""
    import argparse

    parser = argparse.ArgumentParser(description="mini-reach MCP 服务器")
    parser.add_argument("--mode", choices=["stdio"], default="stdio",
                        help="服务器模式")
    args = parser.parse_args()

    if args.mode == "stdio":
        run_stdio_server()


if __name__ == "__main__":
    main()
