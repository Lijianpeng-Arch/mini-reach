# 🌐 mini-reach

> 让 AI Agent 连接互联网的轻量级工具箱

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## 🎯 项目简介

mini-reach 是一个简化版的 [Agent-Reach](https://github.com/Panniantong/Agent-Reach)，专注于为 AI Agent 提供互联网访问能力。

如果你想让 Claude Code、Cursor、Windsurf 等 AI 编程工具能够：
- 📖 读取任意网页内容
- 🔍 搜索 GitHub 仓库
- 📂 读取仓库文件和 README

那么 mini-reach 就是为你设计的！

## ✨ 特性

- 🪶 **轻量级** - 只有 2 个核心渠道，代码简洁易理解
- 🔌 **可扩展** - 基于 Channel 基类，轻松添加新平台
- 🎨 **开箱即用** - 零配置，web 渠道无需任何设置
- 📝 **代码即文档** - 适合学习 AI Agent 架构设计

## 📦 支持的渠道

| 渠道 | 功能 | 前置条件 |
|------|------|----------|
| `web` | 读取任意网页（Markdown 格式） | 无 |
| `github` | 搜索仓库、读取文件、README | 安装 gh CLI |

## 🚀 快速开始

### 安装

```bash
# 克隆项目
git clone https://github.com/Jiutian-ai/mini-reach.git
cd mini-reach

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 前置条件

#### GitHub 渠道（可选）
```bash
# 安装 GitHub CLI
# macOS
brew install gh

# Windows
winget install GitHub.cli

# Linux
sudo apt install gh

# 登录（读取私有仓库需要）
gh auth login
```

### 使用方式

#### Python API

```python
from mini_reach import MiniReach

# 创建实例
mr = MiniReach()

# 读取网页
result = mr.read("web", "https://github.com")
if result.success:
    print(result.content)

# 搜索 GitHub
result = mr.search("github", "react hooks")
if result.success:
    print(result.content)

# 读取 GitHub 仓库
result = mr.read("github", "anthropics/claude-code")
```

#### 命令行

```bash
# 读取网页
mini-reach read web https://github.com

# 搜索 GitHub 仓库
mini-reach search github python async

# 读取 GitHub 仓库信息
mini-reach read github owner/repo

# 读取 GitHub 文件
mini-reach read github owner/repo/path/to/file.py

# 诊断渠道状态
mini-reach doctor
```

## 🏗️ 项目架构

```
mini-reach/
├── mini_reach/
│   ├── __init__.py       # 包入口
│   ├── core.py           # 核心调度器
│   ├── cli.py            # 命令行工具
│   └── channels/
│       ├── __init__.py
│       ├── base.py       # Channel 基类
│       ├── web.py        # 网页渠道
│       └── github.py     # GitHub 渠道
├── tests/                # 测试
├── pyproject.toml        # 项目配置
└── README.md
```

### 核心设计

每个平台（渠道）都实现 `Channel` 基类：

```python
class Channel(ABC):
    name: str              # 渠道名称
    priority: int          # 优先级

    def check_available(self) -> bool: ...
    def search(self, query: str) -> ChannelResult: ...
    def read(self, url: str) -> ChannelResult: ...
```

## 🎓 学习路线

1. **先看 `channels/base.py`** - 理解 Channel 基类设计
2. **再看 `channels/web.py`** - 最简单的渠道实现
3. **然后看 `channels/github.py`** - 稍微复杂的渠道
4. **最后看 `core.py`** - 理解如何统一调度

## 🔧 扩展开发

添加新的渠道非常简单，只需：

1. 在 `channels/` 目录创建新文件（如 `twitter.py`）
2. 继承 `Channel` 基类实现抽象方法
3. 在 `core.py` 的 `_channel_classes` 中注册

```python
from mini_reach.channels.base import Channel, ChannelResult

class TwitterChannel(Channel):
    name = "twitter"
    description = "Twitter/X 操作"

    def check_available(self) -> bool:
        # 检测渠道是否可用
        ...

    def search(self, query: str, **kwargs) -> ChannelResult:
        ...

    def read(self, url: str, **kwargs) -> ChannelResult:
        ...
```

## 📝 License

MIT License - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- [Agent-Reach](https://github.com/Panniantong/Agent-Reach) - 灵感来源
- [Jina AI](https://jina.ai/reader) - 提供网页转 Markdown 服务
- [GitHub CLI](https://cli.github.com/) - 命令行 GitHub 工具