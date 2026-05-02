"""Git operations for repository analysis."""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _run_git(repo_path: str | Path, *args: str) -> str:
    """Run a git command and return stdout. Raises subprocess.CalledProcessError on failure."""
    result = subprocess.run(
        ["git", "-C", str(repo_path), *args],
        capture_output=True,
        text=True,
        timeout=30,
    )
    result.check_returncode()
    return result.stdout


def get_git_stats(
    repo_path: str | Path,
    days: int = 90,
    top_n: int = 20,
) -> dict[str, Any]:
    """Analyze git history for churn, authorship, and hotspots.

    Args:
        repo_path: Path to the git repository.
        days: Number of days of history to analyze.
        top_n: Number of top entries to return.
    """
    repo = Path(repo_path).resolve()
    if not (repo / ".git").exists():
        return {"error": f"Not a git repository: {repo}"}

    try:
        current_branch = _run_git(repo, "rev-parse", "--abbrev-ref", "HEAD").strip()
    except subprocess.CalledProcessError:
        current_branch = "unknown"

    try:
        # git log with numstat: %H|%an|%ad|%s followed by numstat lines
        log_output = _run_git(
            repo,
            "log",
            f"--since={days}.days",
            "--numstat",
            "--format=%H|%an|%ad|%s",
            "--date=short",
        )
    except subprocess.CalledProcessError as e:
        return {"error": f"git log failed: {e.stderr.strip()}"}

    commits = _parse_log(log_output)
    file_churn = _compute_churn(commits)
    author_stats = _compute_author_stats(commits)
    weekly_activity = _compute_weekly_activity(commits)
    recent_branches = _get_recent_branches(repo, days)

    return {
        "repo_path": str(repo),
        "current_branch": current_branch,
        "days_analyzed": days,
        "total_commits": len(commits),
        "contributors": len(author_stats),
        "most_changed_files": file_churn[:top_n],
        "top_contributors": sorted(
            author_stats.items(), key=lambda x: x[1]["commits"], reverse=True
        )[:top_n],
        "weekly_activity": weekly_activity,
        "recent_branches": recent_branches[:10],
    }


def _parse_log(output: str) -> list[dict[str, Any]]:
    """Parse git log --numstat output into structured commits."""
    commits = []
    current_commit = None

    for line in output.strip().split("\n"):
        if not line:
            continue
        if line.startswith("commit "):
            continue
        if "|" in line and line.count("|") >= 3:
            # Commit header: HASH|AUTHOR|DATE|SUBJECT
            parts = line.split("|", 3)
            if len(parts) == 4:
                current_commit = {
                    "hash": parts[0][:8],
                    "author": parts[1],
                    "date": parts[2],
                    "subject": parts[3],
                    "files": [],
                }
                commits.append(current_commit)
        elif current_commit is not None:
            # Numstat line: additions\tdeletions\tfilepath
            parts = line.split("\t")
            if len(parts) == 3:
                try:
                    adds = int(parts[0]) if parts[0] != "-" else 0
                    dels = int(parts[1]) if parts[1] != "-" else 0
                except ValueError:
                    adds = dels = 0
                current_commit["files"].append({
                    "path": parts[2],
                    "additions": adds,
                    "deletions": dels,
                    "churn": adds + dels,
                })

    return commits


def _compute_churn(commits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aggregate file churn across all commits."""
    churn: dict[str, dict[str, Any]] = {}
    for c in commits:
        for f in c["files"]:
            path = f["path"]
            if path not in churn:
                churn[path] = {"path": path, "commits": 0, "additions": 0, "deletions": 0, "total_churn": 0}
            churn[path]["commits"] += 1
            churn[path]["additions"] += f["additions"]
            churn[path]["deletions"] += f["deletions"]
            churn[path]["total_churn"] += f["churn"]
    return sorted(churn.values(), key=lambda x: x["total_churn"], reverse=True)


def _compute_author_stats(commits: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Aggregate stats by author."""
    authors: dict[str, dict[str, Any]] = {}
    for c in commits:
        author = c["author"]
        if author not in authors:
            authors[author] = {"commits": 0, "files_touched": 0, "additions": 0, "deletions": 0}
        authors[author]["commits"] += 1
        authors[author]["additions"] += sum(f["additions"] for f in c["files"])
        authors[author]["deletions"] += sum(f["deletions"] for f in c["files"])
        authors[author]["files_touched"] += len(c["files"])
    return authors


def _compute_weekly_activity(commits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group commits by week."""
    weeks: dict[str, int] = {}
    for c in commits:
        week = c["date"]
        weeks[week] = weeks.get(week, 0) + 1
    return [
        {"week": w, "commits": n}
        for w, n in sorted(weeks.items())
    ]


def _get_recent_branches(repo: Path, days: int) -> list[dict[str, Any]]:
    """Get recently active branches."""
    try:
        output = _run_git(
            repo,
            "for-each-ref",
            "--sort=-committerdate",
            "refs/heads/",
            "--format=%(refname:short)|%(committerdate:short)|%(authorname)",
        )
    except subprocess.CalledProcessError:
        return []

    branches = []
    for line in output.strip().split("\n"):
        if not line:
            continue
        parts = line.split("|", 2)
        if len(parts) == 3:
            branches.append({
                "name": parts[0],
                "last_commit": parts[1],
                "author": parts[2],
            })
    return branches
