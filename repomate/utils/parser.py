"""AST-based code analysis with regex fallback for non-Python files."""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

_LANGUAGE_PARSERS: dict[str, str] = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".rb": "ruby",
    ".swift": "swift",
    ".kt": "kotlin",
    ".scala": "scala",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".php": "php",
}


def detect_language(file_path: str | Path) -> str:
    """Detect programming language from file extension."""
    suffix = Path(file_path).suffix.lower()
    if suffix in _LANGUAGE_PARSERS:
        return _LANGUAGE_PARSERS[suffix]
    if suffix == ".m":
        return "objective-c"
    return "unknown"


def parse_file(
    file_path: str | Path, *, include_dependencies: bool = False
) -> dict[str, Any]:
    """Parse a source file and extract structural information.

    Returns a dict with imports, classes, functions, and their line ranges.
    For Python files, uses the AST module. For other languages, uses regex heuristics.
    """
    path = Path(file_path)
    lang = detect_language(path)

    try:
        source = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return {"error": str(e), "language": lang, "file_path": str(path)}

    if lang == "python":
        return _parse_python_ast(source, str(path), include_dependencies)
    return _parse_with_regex(source, str(path), lang, include_dependencies)


def _parse_python_ast(
    source: str, path: str, include_dependencies: bool
) -> dict[str, Any]:
    """Parse Python source using the AST module."""
    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError as e:
        return {"error": f"Syntax error: {e}", "language": "python", "file_path": path}

    imports: list[dict[str, Any]] = []
    classes: list[dict[str, Any]] = []
    functions: list[dict[str, Any]] = []
    top_level_constants: list[dict[str, Any]] = []

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append({
                    "name": alias.name,
                    "alias": alias.asname,
                    "line": node.lineno,
                    "kind": "import",
                })
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                imports.append({
                    "name": f"{node.module or ''}.{alias.name}" if node.module else alias.name,
                    "alias": alias.asname,
                    "line": node.lineno,
                    "kind": "from",
                    "module": node.module,
                })
        elif isinstance(node, ast.ClassDef):
            class_info = _extract_class_info(node)
            classes.append(class_info)
        elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            func_info = _extract_function_info(node)
            functions.append(func_info)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    top_level_constants.append({
                        "name": target.id,
                        "line": node.lineno,
                    })

    classes.sort(key=lambda c: c["line"])
    functions.sort(key=lambda f: f["line"])

    result: dict[str, Any] = {
        "file_path": path,
        "language": "python",
        "total_lines": len(source.splitlines()),
        "imports": imports,
        "classes": classes,
        "functions": functions,
        "top_level_constants": top_level_constants,
    }

    if include_dependencies:
        result["internal_deps"] = _resolve_internal_deps(imports, path)
        result["external_deps"] = _resolve_external_deps(imports)

    return result


def _extract_class_info(node: ast.ClassDef) -> dict[str, Any]:
    """Extract class metadata from an AST ClassDef node."""
    bases = [_format_expr(b) for b in node.bases]
    methods = []
    for child in node.body:
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            methods.append(_extract_function_info(child))
    return {
        "name": node.name,
        "line": node.lineno,
        "end_line": node.end_lineno,
        "bases": bases,
        "methods": methods,
        "decorators": [_format_expr(d) for d in node.decorator_list],
        "docstring": ast.get_docstring(node),
    }


def _extract_function_info(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> dict[str, Any]:
    """Extract function metadata from an AST FunctionDef node."""
    args = []
    for arg in node.args.args:
        arg_info = {"name": arg.arg}
        if arg.annotation:
            arg_info["type"] = _format_expr(arg.annotation)
        args.append(arg_info)
    return {
        "name": node.name,
        "line": node.lineno,
        "end_line": node.end_lineno,
        "args": args,
        "decorators": [_format_expr(d) for d in node.decorator_list],
        "is_async": isinstance(node, ast.AsyncFunctionDef),
        "docstring": ast.get_docstring(node),
    }


def _format_expr(node: ast.expr) -> str:
    """Format an AST expression node back to source-like string."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_format_expr(node.value)}.{node.attr}"
    if isinstance(node, ast.Call):
        return f"{_format_expr(node.func)}(...)"
    if isinstance(node, ast.Subscript):
        return f"{_format_expr(node.value)}[...]"
    return type(node).__name__


def _resolve_internal_deps(
    imports: list[dict[str, Any]], file_path: str
) -> list[str]:
    """Identify imports that reference modules within the same project."""
    internal = []
    file_dir = Path(file_path).parent
    for imp in imports:
        if imp.get("kind") == "from":
            module = imp.get("module", "")
            if module:
                parts = module.split(".")
                # Check if the top-level package exists next to the file
                candidate = file_dir / parts[0]
                if candidate.is_dir():
                    internal.append(module)
    return sorted(set(internal))


def _resolve_external_deps(imports: list[dict[str, Any]]) -> list[str]:
    """Identify imports from third-party packages."""
    stdlib = {
        "os", "sys", "re", "json", "time", "datetime", "pathlib", "typing",
        "collections", "itertools", "functools", "abc", "contextlib", "io",
        "logging", "hashlib", "uuid", "math", "random", "subprocess", "shutil",
        "tempfile", "argparse", "copy", "dataclasses", "enum", "asyncio",
        "unittest", "pytest", "warnings", "textwrap", "inspect", "ast",
        "threading", "multiprocessing", "urllib", "http", "socket", "ssl",
        "email", "xml", "html", "csv", "configparser", "tomllib", "base64",
        "fnmatch", "glob", "struct", "pickle", "sqlite3", "gc", "traceback",
        "signal", "atexit", "platform", "getpass", "gettext", "locale",
        "statistics", "decimal", "fractions", "operator", "types",
        "__future__", "typing_extensions",
    }
    external = []
    for imp in imports:
        name = imp["name"]
        if imp.get("kind") == "from":
            module = imp.get("module", "")
            if module:
                top = module.split(".")[0]
                if top not in stdlib:
                    external.append(module)
        elif imp["kind"] == "import":
            top = name.split(".")[0]
            if top not in stdlib:
                external.append(name)
    return sorted(set(external))


# ── Regex-based fallback parser for non-Python languages ──────────────

_CLASS_PATTERNS: dict[str, str] = {
    "typescript": r"export\s+(?:abstract\s+)?class\s+(\w+)",
    "javascript": r"class\s+(\w+)",
    "go": r"type\s+(\w+)\s+struct",
    "rust": r"(?:pub\s+)?struct\s+(\w+)",
    "java": r"(?:public\s+|private\s+|protected\s+)?(?:abstract\s+|final\s+)?(?:class|interface|enum)\s+(\w+)",
    "ruby": r"class\s+(\w+)",
}

_FUNCTION_PATTERNS: dict[str, str] = {
    "typescript": r"(?:export\s+)?(?:async\s+)?function\s+(\w+)",
    "javascript": r"(?:async\s+)?function\s+(\w+)",
    "go": r"func\s+(?:\([^)]*\)\s+)?(\w+)",
    "rust": r"(?:pub\s+)?fn\s+(\w+)",
    "ruby": r"def\s+(\w+)",
}

_IMPORT_PATTERNS: dict[str, str] = {
    "typescript": r"import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]",
    "javascript": r"(?:import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]|require\(['\"]([^'\"]+)['\"]\))",
    "go": r"import\s+(?:\(\s*)?\"([^\"]+)\"",
    "rust": r"use\s+([^;]+);",
}


def _parse_with_regex(
    source: str, path: str, lang: str, include_dependencies: bool
) -> dict[str, Any]:
    """Parse source using regex patterns for the detected language."""
    lines = source.splitlines()

    imports = _extract_pattern(
        source, _IMPORT_PATTERNS.get(lang, ""), "import", lines
    )
    classes = _extract_pattern(
        source, _CLASS_PATTERNS.get(lang, ""), "class", lines
    )
    functions = _extract_pattern(
        source, _FUNCTION_PATTERNS.get(lang, ""), "function", lines
    )

    result: dict[str, Any] = {
        "file_path": path,
        "language": lang,
        "total_lines": len(lines),
        "imports": imports,
        "classes": classes,
        "functions": functions,
        "parser": "regex",
    }
    if include_dependencies:
        result["external_deps"] = sorted(
            {i["name"] for i in imports if not i["name"].startswith(".")}
        )
    return result


def _extract_pattern(
    source: str, pattern: str, kind: str, lines: list[str]
) -> list[dict[str, Any]]:
    """Extract named matches from source using a regex pattern."""
    if not pattern:
        return []
    results = []
    for match in re.finditer(pattern, source, re.MULTILINE):
        line_num = source[: match.start()].count("\n") + 1
        name = match.group(1) or match.group(0)
        results.append({
            "name": name,
            "line": line_num,
            "kind": kind,
            "source": lines[line_num - 1].strip() if line_num <= len(lines) else "",
        })
    return results
