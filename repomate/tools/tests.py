"""repo_find_tests — Locate test files, detect framework, flag untested modules."""

from __future__ import annotations

from pathlib import Path
from typing import Any

TEST_FILE_PATTERNS = [
    "test_*.py", "*_test.py", "test_*.ts", "*.test.ts",
    "*.test.tsx", "*.spec.ts", "*.spec.tsx", "test_*.js",
    "*.test.js", "*.spec.js", "*Test.java", "*Tests.java",
    "*_test.go", "*_test.rs", "*_spec.rb",
]

TEST_DIR_NAMES = {"tests", "test", "spec", "__tests__", "e2e", "integration"}

FRAMEWORK_SIGNATURES: dict[str, list[str]] = {
    "pytest": ["pytest.ini", "pyproject.toml", "conftest.py", "setup.cfg"],
    "jest": ["jest.config.js", "jest.config.ts", "jest.config.json"],
    "vitest": ["vitest.config.js", "vitest.config.ts"],
    "mocha": [".mocharc.js", ".mocharc.json", ".mocharc.yml"],
    "junit": ["pom.xml"],
    "go test": ["go.mod"],
    "cargo test": ["Cargo.toml"],
    "rspec": [".rspec", "spec/spec_helper.rb"],
    "unittest": ["setup.py"],
}


STRUCTURAL_TEST_DIRS = {"tests", "test"}


def repo_find_tests(
    repo_path: str,
    framework_hint: str = "auto",
) -> dict[str, Any]:
    """Locate test files, identify test frameworks, and flag untested source modules.

    Args:
        repo_path: Absolute path to the repository root.
        framework_hint: Optional framework hint to prioritize detection.
    """
    repo = Path(repo_path).resolve()
    if not repo.is_dir():
        return {"error": f"Directory not found: {repo}"}

    test_files = _find_test_files(repo)
    framework = _detect_framework(repo, framework_hint)
    test_dirs = _find_test_directories(repo)
    test_entry_points = _find_entry_points(repo, test_files)
    coverage = _assess_coverage(repo, test_files)
    test_to_source_ratio = _compute_test_ratio(repo, test_files)

    return {
        "repo_path": str(repo),
        "framework": framework,
        "test_files_count": len(test_files),
        "test_files": test_files[:50],
        "test_directories": [str(d.relative_to(repo)) for d in test_dirs],
        "test_entry_points": test_entry_points,
        "test_to_source_ratio": test_to_source_ratio,
        "coverage_assessment": coverage,
    }


def _find_test_files(repo: Path) -> list[dict[str, Any]]:
    """Find all test files in the repository."""
    import fnmatch

    ignore_dirs = {"__pycache__", "node_modules", ".git", ".venv", "venv",
                    "dist", "build", "target", ".tox"}

    results = []
    for entry in repo.rglob("*"):
        if not entry.is_file():
            continue
        if any(d in entry.parts for d in ignore_dirs):
            continue

        rel = str(entry.relative_to(repo))
        # Check if it's in a test directory or matches test naming patterns
        is_test = any(d in TEST_DIR_NAMES for d in entry.parts)
        if not is_test:
            is_test = any(fnmatch.fnmatch(entry.name, p) for p in TEST_FILE_PATTERNS)

        if is_test:
            results.append({
                "path": rel,
                "name": entry.name,
                "directory": str(entry.parent.relative_to(repo)),
                "size": entry.stat().st_size,
            })

    results.sort(key=lambda f: f["path"])
    return results


def _detect_framework(repo: Path, hint: str) -> dict[str, Any]:
    """Detect test frameworks used in the repository."""
    detected = []
    for framework, markers in FRAMEWORK_SIGNATURES.items():
        for marker in markers:
            if (repo / marker).exists():
                detected.append(framework)
                break

    if not detected:
        for fw, markers in FRAMEWORK_SIGNATURES.items():
            for marker in markers:
                found = list(repo.rglob(marker))
                if found:
                    detected.append(fw)
                    break

    if not detected:
        detected.append("unknown")

    if hint != "auto" and hint not in detected:
        detected.insert(0, f"{hint} (hint)")

    return {
        "detected": detected,
        "primary": detected[0],
        "hint": hint,
    }


def _find_test_directories(repo: Path) -> list[Path]:
    """Find directories that contain tests."""
    dirs = []
    for entry in repo.rglob("*"):
        if not entry.is_dir():
            continue
        if any(d.startswith(".") for d in entry.parts):
            continue
        rel = entry.relative_to(repo)
        parts = rel.parts
        if any(d in TEST_DIR_NAMES for d in parts):
            dirs.append(entry)
    return sorted(dirs, key=lambda d: len(d.relative_to(repo).parts))


def _find_entry_points(
    repo: Path, test_files: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Identify test entry points (config files, fixtures, setup)."""
    entry_names = {
        "conftest.py", "__init__.py", "setup.js", "setup.ts",
        "jest.setup.js", "jest.setup.ts", "helper.py", "helpers.py",
    }
    points = []
    for tf in test_files:
        if tf["name"] in entry_names:
            full_path = repo / tf["path"]
            points.append({
                "path": tf["path"],
                "type": "fixture" if "conftest" in tf["name"] or "setup" in tf["name"] else "setup",
                "size": full_path.stat().st_size if full_path.exists() else 0,
            })
    return points


def _assess_coverage(
    repo: Path, test_files: list[dict[str, Any]]
) -> dict[str, Any]:
    """Assess which source modules are tested and which aren't."""
    source_files = _find_source_files(repo)
    test_targets = _infer_test_targets(test_files)

    tested = set()
    untested = []
    for sf in source_files:
        rel = str(sf.relative_to(repo))
        module_name = sf.stem
        # Check if any test targets match
        matched = any(
            module_name in target or target in module_name
            for target in test_targets
        )
        if matched:
            tested.add(rel)
        else:
            untested.append(rel)

    return {
        "source_files_total": len(source_files),
        "source_files_tested": len(tested),
        "untested_modules": untested[:30],
        "coverage_ratio": round(len(tested) / max(len(source_files), 1), 2),
    }


def _find_source_files(repo: Path) -> list[Path]:
    """Find all source files (non-test)."""
    import fnmatch

    extensions = {".py", ".ts", ".tsx", ".js", ".go", ".rs", ".java", ".rb"}
    ignore_dirs = {"__pycache__", "node_modules", ".git", ".venv", "venv",
                    "dist", "build", "target"}

    files = []
    for entry in repo.rglob("*"):
        if entry.is_file() and entry.suffix in extensions:
            rel = str(entry.relative_to(repo))
            if any(d in entry.parts for d in ignore_dirs):
                continue
            is_test = any(d in TEST_DIR_NAMES for d in entry.parts)
            if not is_test:
                is_test = any(fnmatch.fnmatch(entry.name, p) for p in TEST_FILE_PATTERNS)
            if not is_test:
                files.append(entry)

    return files


def _infer_test_targets(test_files: list[dict[str, Any]]) -> set[str]:
    """Infer which source modules a test file targets by removing test prefix/suffix."""
    targets = set()
    for tf in test_files:
        name = tf["name"]
        stem = Path(name).stem
        # Remove test_ prefix or _test suffix
        if stem.startswith("test_"):
            targets.add(stem[5:])
        elif stem.endswith("_test"):
            targets.add(stem[:-5])
        elif stem.endswith(".test") or stem.endswith(".spec"):
            targets.add(stem.rsplit(".", 1)[0])
        else:
            targets.add(stem)
    return targets


def _compute_test_ratio(
    repo: Path, test_files: list[dict[str, Any]]
) -> dict[str, Any]:
    """Compute test-to-source ratio by directory."""
    dirs: dict[str, dict[str, int]] = {}
    for tf in test_files:
        d = tf["directory"]
        if d not in dirs:
            dirs[d] = {"tests": 0, "source": 0}
        dirs[d]["tests"] += 1

    source_files = _find_source_files(repo)
    for sf in source_files:
        d = str(sf.parent.relative_to(repo))
        if d == ".":
            d = "<root>"
        if d not in dirs:
            dirs[d] = {"tests": 0, "source": 0}
        dirs[d]["source"] += 1

    return {
        d: {**v, "ratio": round(v["tests"] / max(v["source"], 1), 2)}
        for d, v in sorted(dirs.items())
        if v["source"] > 0
    }
