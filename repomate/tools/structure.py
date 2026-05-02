"""repo_structure — Generate an annotated directory tree of the repository."""

from __future__ import annotations

from pathlib import Path
from typing import Any

IGNORE_DIRS = {
    "__pycache__", "node_modules", ".git", ".venv", "venv", ".tox",
    "dist", "build", "target", ".mypy_cache", ".pytest_cache",
    ".next", ".nuxt", "coverage", "tmp", "vendor", ".idea", ".vscode",
    ".DS_Store", "eggs", ".eggs", "*.egg-info",
}

SOURCE_EXTENSIONS = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java",
    ".rb", ".swift", ".kt", ".scala", ".c", ".h", ".cpp", ".hpp",
    ".cs", ".php", ".r", ".jl", ".ex", ".exs", ".clj", ".cljs",
}

CONFIG_EXTENSIONS = {
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".env",
    ".xml", ".iml",
}

DOC_EXTENSIONS = {".md", ".rst", ".txt", ".adoc", ".org"}


def repo_structure(
    repo_path: str,
    max_depth: int = 4,
    include_patterns: list[str] | None = None,
    exclude_patterns: list[str] | None = None,
) -> dict[str, Any]:
    """Generate an annotated directory tree of the repository.

    Args:
        repo_path: Absolute path to the repository root.
        max_depth: Maximum directory depth to traverse.
        include_patterns: Glob patterns for files to include.
        exclude_patterns: Glob patterns for directories to exclude.
    """
    repo = Path(repo_path).resolve()
    if not repo.is_dir():
        return {"error": f"Directory not found: {repo}"}

    if include_patterns is None:
        include_patterns = [
            "*.py", "*.ts", "*.tsx", "*.js", "*.jsx", "*.go", "*.rs",
            "*.java", "*.rb", "*.swift", "*.kt", "*.scala", "*.c", "*.h",
            "*.cpp", "*.hpp", "*.cs", "*.php",
        ]
    if exclude_patterns is None:
        exclude_patterns = sorted(IGNORE_DIRS)

    tree = _walk_tree(repo, repo, max_depth, 0, exclude_patterns, include_patterns)
    summary = _summarize_tree(tree)

    return {
        "repo_path": str(repo),
        "max_depth": max_depth,
        "tree": tree_to_markdown(tree),
        "summary": summary,
    }


def _walk_tree(
    root: Path,
    current: Path,
    max_depth: int,
    depth: int,
    exclude_dirs: list[str],
    include_patterns: list[str],
) -> dict[str, Any]:
    """Recursively walk the directory tree."""
    import fnmatch

    node: dict[str, Any] = {
        "name": current.name if current != root else str(root),
        "type": "directory",
        "depth": depth,
        "children": [],
        "file_count": 0,
    }

    if depth >= max_depth:
        node["truncated"] = True
        return node

    try:
        entries = sorted(current.iterdir(), key=lambda e: (e.is_file(), e.name.lower()))
    except PermissionError:
        node["no_access"] = True
        return node

    for entry in entries:
        if entry.is_dir():
            if entry.name in exclude_dirs or entry.name.startswith(".") and entry.name not in (".github",):
                continue
            child = _walk_tree(root, entry, max_depth, depth + 1, exclude_dirs, include_patterns)
            if child.get("file_count", 0) > 0 or child.get("children"):
                node["children"].append(child)
                node["file_count"] += child["file_count"]
        elif entry.is_file():
            if any(fnmatch.fnmatch(entry.name, p) for p in include_patterns):
                node["children"].append({
                    "name": entry.name,
                    "type": _classify_file(str(entry.relative_to(root))),
                    "size": entry.stat().st_size,
                })
                node["file_count"] += 1

    return node


def _classify_file(file_path: str) -> str:
    """Classify a file by its role."""
    suffix = Path(file_path).suffix.lower()
    if suffix in SOURCE_EXTENSIONS:
        p = file_path.lower()
        if "test" in p or p.endswith("_test.py") or p.endswith(".test.ts"):
            return "test"
        if any(k in Path(p).parts for k in ("config", "conf", "settings")):
            return "config"
        if any(k in Path(p).parts for k in ("cli", "command", "cmd")):
            return "interface"
        if any(k in Path(p).parts for k in ("util", "helper", "common", "shared")):
            return "utility"
        if p.endswith("/__init__.py"):
            return "package"
        return "source"
    if suffix in CONFIG_EXTENSIONS:
        return "config"
    if suffix in DOC_EXTENSIONS:
        return "documentation"
    return "other"


def tree_to_markdown(node: dict[str, Any], indent: int = 0) -> str:
    """Convert the tree dict to a markdown-formatted string."""
    lines = []
    prefix = "  " * indent
    name = node["name"]
    ntype = node.get("type", "")

    if ntype == "directory":
        file_count = node.get("file_count", 0)
        lines.append(f"{prefix}- **{name}/** ({file_count} files)")
        for child in node.get("children", []):
            lines.append(tree_to_markdown(child, indent + 1))
    else:
        emoji = {
            "source": "📄", "test": "🧪", "config": "⚙️",
            "interface": "🔌", "utility": "🧰", "package": "📦",
            "documentation": "📝", "other": "📎",
        }.get(ntype, "📄")
        lines.append(f"{prefix}- {emoji} {name}")

    if node.get("truncated"):
        lines.append(f"{prefix}  ↳ ... (truncated at max depth)")
    if node.get("no_access"):
        lines.append(f"{prefix}  ↳ (access denied)")

    return "\n".join(lines)


def _summarize_tree(tree: dict[str, Any]) -> dict[str, Any]:
    """Generate summary statistics from the tree."""
    counts: dict[str, int] = {}
    dir_summary: list[dict[str, Any]] = []

    def _walk(node: dict[str, Any]):
        for child in node.get("children", []):
            if child.get("type") == "directory":
                fc = child.get("file_count", 0)
                if fc > 0:
                    dir_summary.append({"name": child["name"], "files": fc})
                _walk(child)
            else:
                t = child.get("type", "other")
                counts[t] = counts.get(t, 0) + 1

    _walk(tree)
    dir_summary.sort(key=lambda d: d["files"], reverse=True)

    return {
        "total_files": sum(counts.values()),
        "by_type": counts,
        "top_directories": dir_summary[:10],
    }
