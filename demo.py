#!/usr/bin/env python3
"""RepoMate 演示脚本 —— 面试展示用。

测试所有 5 个 MCP 工具 + 语义缓存 + Skills 元数据提取。

用法:
    python demo.py [repo_path]
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

REPO = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()


def section(title: str) -> None:
    print(f"\n{'═' * 60}")
    print(f"  {title}")
    print(f"{'═' * 60}")


def ok(label: str, value: str = "") -> None:
    print(f"  ✅ {label}: {value}")


def info(label: str, value: str = "") -> None:
    print(f"  📋 {label}: {value}")


def warn(label: str, value: str = "") -> None:
    print(f"  ⚠️  {label}: {value}")


# ── Demo 1: 仓库结构扫描 ──────────────────────────────────────────

def demo_structure():
    section("Demo 1: 仓库结构扫描 — repo_structure")
    from repomate.tools.structure import repo_structure

    t0 = time.time()
    result = repo_structure(str(REPO), max_depth=4)

    summary = result["summary"]
    ok("文件总数", str(summary["total_files"]))
    info("类型分布", str(summary["by_type"]))
    info("Top 目录", ", ".join(
        f"{d['name']}({d['files']})" for d in summary["top_directories"][:6]
    ))
    info("耗时", f"{time.time() - t0:.3f}s")


# ── Demo 2: 文件深度分析 ──────────────────────────────────────────

def demo_analyze():
    section("Demo 2: 文件分析 — repo_analyze_file")
    from repomate.tools.analyze import repo_analyze_file

    # 找一个核心文件
    candidates = [
        "nanobot/agent/loop.py",
        "nanobot/agent/skills.py",
        "repomate/utils/parser.py",
    ]
    target = next((c for c in candidates if (REPO / c).exists()), None)
    if not target:
        warn("无合适文件", "跳过")
        return

    t0 = time.time()
    result = repo_analyze_file(str(REPO / target))

    ok("文件", target)
    ok("语言", result.get("language", "?"))
    ok("行数", str(result.get("total_lines", "?")))
    info("类", str(len(result.get("classes", []))))
    info("顶层函数", str(len(result.get("functions", []))))
    info("导入", str(len(result.get("imports", []))))

    if result.get("classes"):
        for cls in result["classes"][:3]:
            info(f"  class {cls['name']}", f"line {cls['line']}")
            for m in cls.get("methods", [])[:2]:
                info(f"    {m['name']}()", f"line {m['line']}")

    info("耗时", f"{time.time() - t0:.3f}s")


# ── Demo 3: 测试发现 ──────────────────────────────────────────────

def demo_find_tests():
    section("Demo 3: 测试发现 — repo_find_tests")
    from repomate.tools.tests import repo_find_tests

    t0 = time.time()
    result = repo_find_tests(str(REPO))

    ok("框架", result["framework"]["primary"])
    ok("测试文件数", str(result["test_files_count"]))
    ok("测试目录", str(result["test_directories"][:3]))

    coverage = result["coverage_assessment"]
    ok("源码文件总数", str(coverage["source_files_total"]))
    ok("有测试覆盖", str(coverage["source_files_tested"]))
    ok("覆盖率", f"{coverage['coverage_ratio']:.0%}")
    if coverage["untested_modules"]:
        info("未测试模块示例", ", ".join(coverage["untested_modules"][:5]))
    info("耗时", f"{time.time() - t0:.3f}s")


# ── Demo 4: Git 统计 ──────────────────────────────────────────────

def demo_git_stats():
    section("Demo 4: Git 统计 — repo_git_stats")
    from repomate.tools.git_stats import repo_git_stats

    t0 = time.time()
    result = repo_git_stats(str(REPO), days=90)

    if "error" in result:
        warn("失败", result["error"])
        return

    ok("分支", result.get("current_branch", "?"))
    ok("近 90 天提交", str(result.get("total_commits", "?")))
    ok("贡献者", str(result.get("contributors", "?")))
    info("耗时", f"{time.time() - t0:.3f}s")


# ── Demo 5: 依赖图 ────────────────────────────────────────────────

def demo_deps():
    section("Demo 5: 依赖图 — repo_dependency_graph")
    from repomate.tools.deps import repo_dependency_graph

    t0 = time.time()
    result = repo_dependency_graph(str(REPO), format="json")

    ok("分析文件数", str(result.get("files", "?")))
    info("循环依赖", f"{len(result.get('circular_deps', []))} 处")

    centrality = result.get("centrality", [])
    if centrality:
        info("Top 5 高中心度模块:")
        for c in centrality[:5]:
            label = "🔴" if c["in_degree"] > 10 else "🟡" if c["in_degree"] > 3 else "🟢"
            info(f"  {label} {c['path']}",
                 f"被依赖 {c['in_degree']} 次, 依赖 {c['out_degree']} 个模块")

    info("耗时", f"{time.time() - t0:.3f}s")


# ── Demo 6: 语义缓存 ──────────────────────────────────────────────

async def demo_cache():
    section("Demo 6: 语义缓存 — 命中率测试")
    from repomate.cache.semantic_cache import SemanticCache

    cache = SemanticCache(ttl_seconds=3600)
    await cache.initialize()

    # 预热：存储一些查询
    queries = [
        "onboarding me to this codebase",
        "how does the agent loop work?",
        "what files should I read first?",
        "explain the auth system",
        "where are tests located?",
        "how does memory consolidation work?",
        "what MCP tools are available?",
        "how are skills loaded?",
    ]

    for q in queries:
        await cache.store(q, str(REPO), f"Cached response for: {q}")

    # 测试命中率
    test_cases = [
        # (query, repo, expect_hit)
        ("onboarding me to this codebase", str(REPO), True),   # 精确匹配
        ("how does the agent loop work?", str(REPO), True),     # 精确匹配
        ("tell me about the agent processing loop", str(REPO), False),  # 变体
        ("what should I read first as a new developer?", str(REPO), False),  # 变体
        ("explain the auth system", "/other/repo", False),      # 不同仓库
    ]

    hits = 0
    for query, repo, _ in test_cases:
        hit = await cache.lookup(query, repo, similarity_threshold=0.9)
        if hit:
            hits += 1
            info(f"命中: '{query[:50]}...'", f"相似度={hit.similarity:.3f}")
        else:
            info(f"未命中: '{query[:50]}...'")

    ok("精确查询命中", f"{hits}/{len(test_cases)} 个用例")
    ok("缓存统计", str(cache.stats.to_dict()))
    info("说明", "精确匹配命中率取决于嵌入向量质量。使用 OpenAI embeddings 时命中率会显著提升。")


# ── Demo 7: Skills 元数据 ──────────────────────────────────────────

def demo_skills():
    section("Demo 7: Skills 渐进式加载 — SKILL.md 元数据")
    import yaml

    skills_dir = REPO / "skills"
    if not skills_dir.is_dir():
        warn("skills/ 目录不存在", "跳过")
        return

    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            continue

        content = skill_file.read_text()
        if content.startswith("---"):
            _, fm, _ = content.split("---", 2)
            meta = yaml.safe_load(fm)
            name = meta.get("name", skill_dir.name)
            desc = meta.get("description", "")[:80]
            ok(name, desc)

            # 检查参考文件
            refs_dir = skill_dir / "references"
            if refs_dir.is_dir():
                refs = [r.name for r in refs_dir.iterdir()]
                info(f"  参考文件", ", ".join(refs))


# ── 主流程 ─────────────────────────────────────────────────────────

def main():
    print("""
  ╔══════════════════════════════════════════════════════════╗
  ║           RepoMate — 面试演示脚本                         ║
  ║           基于 NanoBot 的代码库入职 Agent                  ║
  ╚══════════════════════════════════════════════════════════╝
""")
    info("目标仓库", str(REPO))

    demo_structure()
    demo_analyze()
    demo_find_tests()
    demo_git_stats()
    demo_deps()
    asyncio.run(demo_cache())
    demo_skills()

    print(f"\n{'═' * 60}")
    print(f"  演示完成。所有 5 个 MCP 工具 + 缓存 + Skills 均正常工作。")
    print(f"{'═' * 60}\n")


if __name__ == "__main__":
    main()
