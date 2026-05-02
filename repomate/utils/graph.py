"""Dependency graph construction for repositories."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from repomate.utils.parser import parse_file


def build_dependency_graph(
    repo_path: str | Path,
    *,
    depth: int = 2,
    format: str = "mermaid",
) -> dict[str, Any]:
    """Build an import dependency graph for the repository.

    Args:
        repo_path: Root directory of the repository.
        depth: Max depth for dependency resolution (controls mermaid graph detail).
        format: Output format — "mermaid", "json", or "dot".
    """
    repo = Path(repo_path).resolve()
    if not repo.is_dir():
        return {"error": f"Directory not found: {repo}"}

    source_files = _find_source_files(repo)
    deps: dict[str, list[str]] = {}
    module_map: dict[str, str] = {}  # normalized_name -> full_path
    errors: list[str] = []

    for f in source_files:
        rel = str(f.relative_to(repo))
        result = parse_file(f)
        if "error" in result:
            errors.append(f"{rel}: {result['error']}")
            deps[rel] = []
        else:
            module_deps = result.get("internal_deps", [])
            deps[rel] = module_deps
            module_map[rel] = str(f)

    graph: dict[str, dict[str, Any]] = {}
    for file_path, file_deps in deps.items():
        node = _file_to_node(file_path, repo)
        graph[file_path] = {
            **node,
            "dependencies": file_deps,
            "dependency_count": len(file_deps),
        }

    reverse_deps = _build_reverse_deps(deps)
    for file_path, dependents in reverse_deps.items():
        if file_path in graph:
            graph[file_path]["dependents"] = dependents[:10]
            graph[file_path]["dependent_count"] = len(dependents)

    centrality = _compute_centrality(graph, reverse_deps)
    circular = _find_circular_deps(deps)

    output = {"files": len(source_files), "errors": errors}
    if format == "mermaid":
        output["mermaid"] = _to_mermaid(graph, deps, depth, reverse_deps)
    elif format == "dot":
        output["dot"] = _to_dot(graph, deps)
    output["graph"] = graph
    output["centrality"] = centrality[:20]
    output["circular_deps"] = circular
    return output


def _find_source_files(repo: Path) -> list[Path]:
    """Find all source files in the repository."""
    extensions = {
        ".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java",
        ".rb", ".swift", ".kt", ".scala", ".c", ".h", ".cpp", ".hpp",
        ".cs", ".php",
    }
    ignore_dirs = {
        "__pycache__", "node_modules", ".git", ".venv", "venv",
        "dist", "build", "target", ".tox", ".mypy_cache", ".pytest_cache",
        ".next", ".nuxt", "coverage", "tmp", "vendor",
    }
    files = []
    for entry in repo.rglob("*"):
        if entry.is_file() and entry.suffix in extensions:
            parts = set(entry.parts)
            if not ignore_dirs & parts:
                files.append(entry)
    return files


def _file_to_node(file_path: str, repo: Path) -> dict[str, Any]:
    """Convert a file path to a graph node."""
    parts = Path(file_path).parts
    return {
        "path": file_path,
        "name": Path(file_path).name,
        "directory": str(Path(file_path).parent) if len(parts) > 1 else ".",
        "category": _classify_file(file_path),
    }


def _classify_file(file_path: str) -> str:
    """Classify a file by its role in the project."""
    p = file_path.lower()

    # Test files: in test/spec directories or follow test naming conventions
    parts = tuple(Path(p).parts)
    if any(d in ("tests", "test", "spec", "__tests__", "e2e", "integration") for d in parts):
        return "test"
    name = Path(p).name
    if name.startswith("test_") or name.endswith("_test.py") or ".test." in name or ".spec." in name:
        return "test"

    if any(k in parts for k in ("config", "conf", "settings")):
        return "config"
    if any(k in parts for k in ("cli", "commands", "command", "cmd")):
        return "interface"
    if any(k in parts for k in ("utils", "util", "helpers", "helper", "common", "shared")):
        return "utility"
    if p.endswith("/__init__.py"):
        return "package"
    return "core"


def _build_reverse_deps(deps: dict[str, list[str]]) -> dict[str, list[str]]:
    """Build reverse dependency map: who depends on each file?"""
    reverse: dict[str, list[str]] = defaultdict(list)
    for file_path, file_deps in deps.items():
        module_parts = Path(file_path).parts
        for dep in file_deps:
            dep_file = _resolve_dep_to_path(dep, module_parts, deps)
            reverse[dep_file].append(file_path)
    return dict(reverse)


def _resolve_dep_to_path(
    dep: str, caller_parts: tuple[str, ...], deps: dict[str, list[str]]
) -> str:
    """Resolve a module dependency name to a file path."""
    # If dep already ends with .py, it's a direct file reference — don't mangle it
    if dep.endswith(".py"):
        if dep in deps:
            return dep
        candidates = [dep]
    else:
        dep_path = dep.replace(".", "/")
        candidates = [
            f"{dep_path}.py",
            f"{dep_path}/__init__.py",
            f"{'/'.join(caller_parts[:-1])}/{dep_path}.py",
        ]
    for c in candidates:
        if c in deps:
            return c
    return candidates[0] if candidates else f"{dep}.py"


def _compute_centrality(
    graph: dict[str, dict[str, Any]],
    reverse_deps: dict[str, list[str]],
) -> list[dict[str, Any]]:
    """Compute centrality scores for each module."""
    results = []
    for file_path, node in graph.items():
        in_degree = len(reverse_deps.get(file_path, []))
        out_degree = node.get("dependency_count", 0)
        results.append({
            "path": file_path,
            "in_degree": in_degree,
            "out_degree": out_degree,
            "centrality_score": in_degree + out_degree,
            "name": node["name"],
        })
    return sorted(results, key=lambda x: x["centrality_score"], reverse=True)


def _find_circular_deps(deps: dict[str, list[str]]) -> list[list[str]]:
    """Find circular dependencies using DFS."""
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {k: WHITE for k in deps}
    cycles: list[list[str]] = []

    def dfs(node: str, path: list[str]):
        color[node] = GRAY
        path.append(node)
        for neighbor in deps.get(node, []):
            neighbor_file = _resolve_dep_to_path(
                neighbor, tuple(Path(node).parts), deps
            )
            if neighbor_file not in color:
                continue
            if color.get(neighbor_file) == GRAY:
                idx = path.index(neighbor_file)
                cycles.append(path[idx:] + [neighbor_file])
            elif color.get(neighbor_file) == WHITE:
                dfs(neighbor_file, path)
        path.pop()
        color[node] = BLACK

    for node in deps:
        if color[node] == WHITE:
            dfs(node, [])
    return cycles[:20]


def _to_mermaid(
    graph: dict[str, dict[str, Any]],
    deps: dict[str, list[str]],
    depth: int,
    reverse_deps: dict[str, list[str]],
) -> str:
    """Generate a Mermaid.js graph TD diagram."""
    lines = ["graph TD"]
    node_ids: dict[str, str] = {}
    node_count = 0

    centrality = sorted(
        [(f, len(reverse_deps.get(f, []))) for f in graph],
        key=lambda x: x[1],
        reverse=True,
    )

    # Pick top nodes (limited to avoid huge graphs)
    shown: set[str] = set()
    for f, _ in centrality[:30]:
        shown.add(f)

    for file_path, node in graph.items():
        if file_path not in shown:
            continue
        node_count += 1
        nid = f"N{node_count}"
        node_ids[file_path] = nid
        label = node["name"].replace(".py", "").replace(".ts", "").replace(".js", "")
        cat = node.get("category", "core")
        style = {"core": "fill:#cff", "test": "fill:#fcf", "config": "fill:#ffc",
                  "interface": "fill:#ccf", "utility": "fill:#cfc"}.get(cat, "")
        lines.append(f"    {nid}[{label}]{' ' + style if style else ''}")

    for file_path, node in graph.items():
        if file_path not in shown:
            continue
        for dep in node.get("dependencies", []):
            target = _resolve_dep_to_path(dep, tuple(Path(file_path).parts), deps)
            if target in shown and target in node_ids:
                lines.append(f"    {node_ids[file_path]} --> {node_ids[target]}")

    return "\n".join(lines)


def _to_dot(
    graph: dict[str, dict[str, Any]], deps: dict[str, list[str]]
) -> str:
    """Generate a Graphviz DOT diagram."""
    lines = ["digraph G {", "    rankdir=LR;"]
    node_ids: dict[str, str] = {}
    node_count = 0

    for file_path, node in graph.items():
        node_count += 1
        nid = f"n{node_count}"
        node_ids[file_path] = nid
        label = node["name"]
        lines.append(f'    {nid} [label="{label}", shape=box];')

    for file_path, node in graph.items():
        for dep in node.get("dependencies", []):
            target = _resolve_dep_to_path(dep, tuple(Path(file_path).parts), deps)
            if target in node_ids:
                lines.append(f"    {node_ids[file_path]} -> {node_ids[target]};")

    lines.append("}")
    return "\n".join(lines)
