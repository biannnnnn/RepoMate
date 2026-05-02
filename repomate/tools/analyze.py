"""repo_analyze_file — Extract imports, classes, functions with line numbers."""

from __future__ import annotations

from typing import Any

from repomate.utils.parser import parse_file


def repo_analyze_file(
    file_path: str,
    include_dependencies: bool = False,
) -> dict[str, Any]:
    """Analyze a single source file and extract its structure.

    Returns imports, classes, functions, and their line ranges.
    Every element includes exact line numbers for citation purposes.

    Args:
        file_path: Absolute path to the file to analyze.
        include_dependencies: Whether to resolve and categorize dependencies.
    """
    result = parse_file(file_path, include_dependencies=include_dependencies)

    if "error" in result:
        return result

    # Add a citation-ready summary
    summary_parts = []
    if result.get("classes"):
        summary_parts.append(f"{len(result['classes'])} classes")
    if result.get("functions"):
        summary_parts.append(f"{len(result['functions'])} functions")
    if result.get("imports"):
        summary_parts.append(f"{len(result['imports'])} imports")

    language = result.get("language", "unknown")
    file_path_str = result.get("file_path", file_path)

    result["citation_summary"] = (
        f"{file_path_str} ({language}): {', '.join(summary_parts)}, "
        f"{result.get('total_lines', 0)} lines"
    )

    # Build a markdown representation for easy agent consumption
    md = [f"# File Analysis: {file_path_str}", ""]
    md.append(f"**Language**: {language}")
    md.append(f"**Lines**: {result.get('total_lines', 0)}")
    md.append("")

    if result.get("classes"):
        md.append("## Classes")
        for cls in result["classes"]:
            bases = f"({', '.join(cls['bases'])})" if cls.get("bases") else ""
            end = cls.get("end_line", "")
            line_range = f"line {cls['line']}" + (f"-{end}" if end else "")
            md.append(f"- **{cls['name']}**{bases} — {line_range}")
            for method in cls.get("methods", []):
                m_end = method.get("end_line", "")
                m_range = f"line {method['line']}" + (f"-{m_end}" if m_end else "")
                md.append(f"  - `{method['name']}()` — {m_range}")
        md.append("")

    if result.get("functions"):
        md.append("## Top-Level Functions")
        for func in result["functions"]:
            end = func.get("end_line", "")
            line_range = f"line {func['line']}" + (f"-{end}" if end else "")
            args = ", ".join(a["name"] for a in func.get("args", []))
            md.append(f"- **`{func['name']}({args})`** — {line_range}")
        md.append("")

    if result.get("imports"):
        internal = result.get("internal_deps", [])
        external = result.get("external_deps", [])
        if internal:
            md.append("## Internal Dependencies")
            for d in internal:
                md.append(f"- `{d}`")
            md.append("")
        if external:
            md.append("## External Dependencies")
            for d in external[:15]:
                md.append(f"- `{d}`")

    result["markdown"] = "\n".join(md)
    return result
