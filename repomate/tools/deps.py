"""repo_dependency_graph — Build import dependency graph for the repository."""

from __future__ import annotations

from typing import Any

from repomate.utils.graph import build_dependency_graph


def repo_dependency_graph(
    repo_path: str,
    format: str = "mermaid",
    depth: int = 2,
) -> dict[str, Any]:
    """Build an import dependency graph for the repository.

    Args:
        repo_path: Absolute path to the repository root.
        format: Output format — "mermaid", "json", or "dot".
        depth: Max dependency depth to resolve.
    """
    result = build_dependency_graph(repo_path, depth=depth, format=format)

    if "error" in result:
        return result

    # Add a markdown summary for the agent
    centrality = result.get("centrality", [])
    circular = result.get("circular_deps", [])
    errors = result.get("errors", [])

    md = [f"# Dependency Graph: {repo_path}", ""]
    md.append(f"**Files analyzed**: {result.get('files', 0)}")
    md.append("")

    if errors:
        md.append(f"**Parse errors**: {len(errors)} files")
        md.append("")

    if centrality:
        md.append("## High-Centrality Modules (most connected)")
        for c in centrality[:10]:
            label = "🔴" if c.get("in_degree", 0) > 10 else "🟡" if c.get("in_degree", 0) > 3 else "🟢"
            md.append(
                f"- {label} `{c['path']}` — "
                f"depended on by {c['in_degree']} modules, "
                f"depends on {c['out_degree']} modules"
            )

    if circular:
        md.append("")
        md.append("## Circular Dependencies")
        for cycle in circular[:10]:
            md.append(f"- {' → '.join(cycle)}")

    if result.get("mermaid"):
        md.append("")
        md.append("## Mermaid Diagram")
        md.append("```mermaid")
        md.append(result["mermaid"])
        md.append("```")

    result["markdown"] = "\n".join(md)
    return result
