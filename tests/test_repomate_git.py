"""Tests for repomate.utils.git — git log parsing and statistics."""

from __future__ import annotations

import textwrap

from repomate.utils.git import (
    _compute_author_stats,
    _compute_churn,
    _compute_weekly_activity,
    _parse_log,
)


class TestParseLog:
    def test_single_commit(self):
        output = textwrap.dedent("""\
            abc12345|Alice|2026-04-15|Add login feature
            12\t3\tsrc/auth.py
            5\t0\ttests/test_auth.py
        """)
        commits = _parse_log(output)
        assert len(commits) == 1
        c = commits[0]
        assert c["hash"] == "abc12345"
        assert c["author"] == "Alice"
        assert c["date"] == "2026-04-15"
        assert c["subject"] == "Add login feature"
        assert len(c["files"]) == 2

    def test_multiple_commits(self):
        output = textwrap.dedent("""\
            11111111|Alice|2026-04-15|First commit
            10\t0\tsrc/main.py
            22222222|Bob|2026-04-16|Second commit
            5\t3\tsrc/utils.py
            33333333|Alice|2026-04-17|Third commit
            1\t1\tREADME.md
        """)
        commits = _parse_log(output)
        assert len(commits) == 3

    def test_binary_file_skipped(self):
        """Binary files show '-' for additions/deletions — should be handled as 0."""
        output = textwrap.dedent("""\
            abc12345|Alice|2026-04-15|Add image
            -\t-\tassets/logo.png
        """)
        commits = _parse_log(output)
        f = commits[0]["files"][0]
        assert f["additions"] == 0
        assert f["deletions"] == 0
        assert f["churn"] == 0


class TestComputeChurn:
    def test_aggregates_across_commits(self):
        commits = [
            {
                "files": [
                    {"path": "src/a.py", "additions": 10, "deletions": 2, "churn": 12},
                    {"path": "src/b.py", "additions": 5, "deletions": 0, "churn": 5},
                ]
            },
            {
                "files": [
                    {"path": "src/a.py", "additions": 3, "deletions": 1, "churn": 4},
                ]
            },
        ]
        result = _compute_churn(commits)
        a = next(r for r in result if r["path"] == "src/a.py")
        assert a["commits"] == 2
        assert a["additions"] == 13
        assert a["deletions"] == 3
        assert a["total_churn"] == 16

        b = next(r for r in result if r["path"] == "src/b.py")
        assert b["commits"] == 1


class TestComputeAuthorStats:
    def test_aggregates_by_author(self):
        commits = [
            {
                "author": "Alice",
                "files": [
                    {"path": "src/a.py", "additions": 10, "deletions": 2, "churn": 12},
                    {"path": "src/b.py", "additions": 5, "deletions": 0, "churn": 5},
                ],
            },
            {
                "author": "Bob",
                "files": [
                    {"path": "src/c.py", "additions": 8, "deletions": 3, "churn": 11},
                ],
            },
            {
                "author": "Alice",
                "files": [
                    {"path": "src/a.py", "additions": 1, "deletions": 1, "churn": 2},
                ],
            },
        ]
        result = _compute_author_stats(commits)
        assert result["Alice"]["commits"] == 2
        assert result["Alice"]["additions"] == 16
        assert result["Bob"]["commits"] == 1
        assert result["Bob"]["additions"] == 8


class TestComputeWeeklyActivity:
    def test_groups_by_week(self):
        commits = [
            {"date": "2026-04-15"},
            {"date": "2026-04-15"},
            {"date": "2026-04-16"},
            {"date": "2026-04-17"},
        ]
        result = _compute_weekly_activity(commits)
        assert result[0]["week"] == "2026-04-15"
        assert result[0]["commits"] == 2
        assert result[1]["week"] == "2026-04-16"
        assert result[1]["commits"] == 1
