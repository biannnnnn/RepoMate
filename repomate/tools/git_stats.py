"""repo_git_stats — Analyze git history for churn, authorship, and hotspots."""

from __future__ import annotations

from typing import Any

from repomate.utils.git import get_git_stats


def repo_git_stats(
    repo_path: str,
    days: int = 90,
    top_n: int = 20,
) -> dict[str, Any]:
    """Analyze git history for churn, hotspots, and contributor activity.

    Args:
        repo_path: Absolute path to the repository root.
        days: Number of days of history to analyze.
        top_n: Number of top entries to return in each category.
    """
    stats = get_git_stats(repo_path, days=days, top_n=top_n)

    if "error" in stats:
        return stats

    # Build a markdown summary
    md = [f"# Git Stats: {stats.get('repo_path', repo_path)}", ""]
    md.append(f"**Branch**: `{stats.get('current_branch', 'unknown')}`")
    md.append(f"**Period**: last {stats.get('days_analyzed', days)} days")
    md.append(f"**Commits**: {stats.get('total_commits', 0)}")
    md.append(f"**Contributors**: {stats.get('contributors', 0)}")
    md.append("")

    # Top contributors
    top_contributors = stats.get("top_contributors", [])
    if top_contributors:
        if isinstance(top_contributors[0], (list, tuple)):
            md.append("## Top Contributors")
            for name, info in top_contributors[:10]:
                md.append(f"- **{name}**: {info['commits']} commits")
        md.append("")

    # Most changed files
    most_changed = stats.get("most_changed_files", [])
    if most_changed:
        md.append("## Hotspot Files (highest churn)")
        for f in most_changed[:15]:
            md.append(
                f"- `{f['path']}` — {f['total_churn']} changes "
                f"(+{f['additions']}/-{f['deletions']}) across {f['commits']} commits"
            )
        md.append("")

    # Recent branches
    branches = stats.get("recent_branches", [])
    if branches:
        md.append("## Recent Branches")
        for b in branches[:10]:
            md.append(f"- `{b['name']}` — last commit {b['last_commit']} by {b['author']}")
        md.append("")

    # Weekly activity
    weekly = stats.get("weekly_activity", [])
    if weekly:
        md.append("## Commit Activity Timeline")
        for w in weekly:
            bar = "█" * min(w["commits"], 30)
            md.append(f"- {w['week']}: {bar} ({w['commits']})")

    stats["markdown"] = "\n".join(md)
    return stats
