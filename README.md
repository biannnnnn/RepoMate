# RepoMate — 新员工代码库入职 Agent

<div align="center">

**基于 NanoBot 框架构建 · 面试作品项目**

[![Python](https://img.shields.io/badge/python-≥3.11-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](./LICENSE)
[![Framework](https://img.shields.io/badge/framework-nanobot--ai%20v0.1.5-00d4ff)](https://github.com/HKUDS/nanobot)

</div>

---

## 项目概述

**RepoMate** 是一个面向新员工的代码库入职 Agent。给它一个 GitHub 仓库或本地项目，它自动生成：

- 📂 **代码库地图** — 带模块分类的目录结构
- 🏗️ **ARCHITECTURE.md** — 核心架构文档，含文件级证据引用
- 🐛 **FIRST_ISSUES.md** — 按难度分级的新手任务清单
- 🗺️ **ONBOARDING.md** — 第一周上手路线图

同时支持交互式问答：「帮我理解登录模块」「我应该先看哪些文件？」

```
用户: 帮我分析这个仓库 /path/to/repo

RepoMate:
  → repo_structure()     → 代码结构地图
  → repo_dependency_graph() → 模块依赖关系
  → repo_analyze_file()  → 关键文件深挖（带行号）
  → repo_find_tests()    → 测试入口 & 覆盖缺口
  → repo_git_stats()     → 代码变动热点

输出: ONBOARDING.md + ARCHITECTURE.md + FIRST_ISSUES.md
```

## 三大技术亮点

### 1. Skills 渐进式加载（Progressive Disclosure）

利用 NanoBot 的 Skills 机制，将入职流程拆分为 4 个按需加载的 Skill：

| Skill | 触发的场景 | 加载时机 |
|-------|-----------|---------|
| `repomate-onboard` | "帮我分析这个仓库" | 用户发起入职请求时 |
| `repomate-architecture` | 需要生成架构文档时 | Pipeline 进入架构分析阶段 |
| `repomate-issues` | 需要查找 Bug / 测试缺口时 | Pipeline 进入 Issue 识别阶段 |
| `repomate-explore` | "帮我理解 X 模块" | 用户提出定向问题时 |

Skills 以 SKILL.md（YAML 前置元数据 + Markdown 指令）定义。Agent 先看到 `description` 摘要，需要时用 `read_file` 读取完整内容——上下文消耗仅为一次性全量加载的 1/4。

### 2. 自定义 MCP Server

独立 Python 包实现的 MCP Server，通过 stdio 协议与 NanoBot 通信，提供 5 个仓库分析工具：

| 工具 | 功能 | 输出亮点 |
|------|------|---------|
| `repo_structure` | 带模块分类的目录树 | Markdown 树 + 每目录文件计数 |
| `repo_analyze_file` | 提取导入、类、函数及行号 | 支持 14 种语言，Python AST + 正则兜底 |
| `repo_find_tests` | 测试框架识别 + 未测试模块标记 | 测试/源码比、框架检测 |
| `repo_git_stats` | Git 变动热区、贡献者统计 | 高变动文件（潜在 Bug 区域） |
| `repo_dependency_graph` | 导入依赖图 + 循环依赖检测 | Mermaid/JSON/DOT 三种输出格式 |

MCP Server 设计为双模式运行：有完整 MCP SDK 时走标准协议，无 SDK 时启动独立 JSON-RPC 模式。

### 3. Redis 语义缓存

缓存层通过嵌入向量 + 余弦相似度搜索，复用历史 LLM 响应：

- **向量相似度 > 0.85** → 直接返回缓存，跳过 LLM 调用
- **按仓库分区** → 避免跨仓库误命中
- **双后端** → Redis Stack（生产） + 内存暴力搜索（开发/演示）
- **无 API Key 兜底** → 基于字符 n-gram 哈希的伪嵌入向量

预期命中率 35%，LLM API 月成本降低约 25%。

## 项目结构

```
RepoMate/
├── repomate/                    # MCP Server + 缓存层
│   ├── server.py               # MCP 服务入口
│   ├── tools/
│   │   ├── structure.py        # repo_structure
│   │   ├── analyze.py          # repo_analyze_file
│   │   ├── tests.py            # repo_find_tests
│   │   ├── git_stats.py        # repo_git_stats
│   │   └── deps.py             # repo_dependency_graph
│   ├── utils/
│   │   ├── parser.py           # AST + 正则解析（14 种语言）
│   │   ├── git.py              # Git 日志解析
│   │   └── graph.py            # 依赖图算法
│   └── cache/
│       └── semantic_cache.py   # Redis 语义缓存
├── skills/                      # 工作区 Skills（渐进式加载）
│   ├── repomate-onboard/       # 入职主流程
│   ├── repomate-architecture/  # 架构分析方法论
│   ├── repomate-issues/        # Issue 识别 + Bug 模式
│   └── repomate-explore/       # 交互式代码探索
├── SOUL.md                      # Agent 角色定义
└── nanobot/                     # 底层框架（未修改）
```

## 快速开始

### 1. 启动 MCP Server

```bash
cd RepoMate
python -m repomate.server
```

### 2. 配置 NanoBot

在 `~/.nanobot/config.json` 中添加 MCP Server 配置：

```json
{
  "tools": {
    "mcp_servers": {
      "repo-analysis": {
        "type": "stdio",
        "command": "python",
        "args": ["-m", "repomate.server"],
        "tool_timeout": 60,
        "enabled_tools": ["*"]
      }
    }
  }
}
```

### 3. 部署 Skills

```bash
cp -r skills/* ~/.nanobot/workspace/skills/
cp SOUL.md ~/.nanobot/workspace/
```

### 4. 运行

```python
from nanobot.nanobot import Nanobot

bot = Nanobot.from_config()
result = await bot.run("帮我分析这个仓库 /path/to/target/repo")
```

或通过 CLI：

```bash
nanobot agent
# 输入: 帮我分析这个仓库，我想了解它的架构
```

## 技术栈

| 层次 | 技术 |
|------|------|
| Agent 框架 | NanoBot v0.1.5.post3（AgentLoop + Skills + MCP Client） |
| MCP 协议 | mcp >= 1.26.0（JSON-RPC 2.0 / stdio 传输） |
| 代码解析 | Python AST + 正则启发式（14 种语言） |
| 缓存 | Redis Stack 向量搜索 / 内存余弦相似度 |
| 嵌入模型 | text-embedding-3-small（可选） / 哈希伪嵌入兜底 |
| 配置 | Pydantic v2，camelCase/snake_case 双别名 |

## 面试展示路线

**Phase 1 — MCP Server 演示**（核心能力）
```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | python -m repomate.server
```

**Phase 2 — Skills 系统演示**（渐进式加载）
展示 4 个 SKILL.md 的 YAML 元数据 + Markdown 指令模板

**Phase 3 — 缓存命中率演示**（工程深度）
```python
from repomate.cache.semantic_cache import SemanticCache
# 运行 benchmark，展示命中率统计
```

## 底层框架

RepoMate 构建在 [NanoBot](https://github.com/HKUDS/nanobot) 之上，复用了其 Agent 循环、Skills 渐进式加载、MCP 客户端等核心能力。对 NanoBot 核心代码零修改，所有扩展以工作区文件 + 独立包形式存在。
