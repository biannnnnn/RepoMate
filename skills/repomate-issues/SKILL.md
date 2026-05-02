---
name: repomate-issues
description: "Identifies test entry points, potential bugs, low-coverage areas, and generates a FIRST_ISSUES.md for new contributors. Use when: generating a first-issues list, identifying good starter tasks for interns, finding untested code paths, or scanning for common bug patterns. Load this skill after architecture analysis is complete."
---
# First Issues & Bug Finding

## Methodology

### Step 1: Test Gap Analysis

Run `mcp_repo_analysis_repo_find_tests(repo_path)` and analyze:

1. **Untested modules**: Files with 0 test coverage → candidate for "write tests" issues
2. **Test-to-source ratio by directory**: Directories with ratio < 0.5 need attention
3. **Framework detection**: What test framework is used? What's the test convention?
4. **Entry points**: `conftest.py`, setup files — these tell new hires how to run tests

### Step 2: Hotspot Analysis

Run `mcp_repo_analysis_repo_git_stats(repo_path, days=90)` and analyze:

1. **High-churn files** (>20 changes in 90 days): instability indicators
   - Cross-reference with test coverage: high-churn + no tests = 🚨 priority
2. **Recently active branches**: what's in progress?
3. **Top contributors**: who to ask about specific areas

### Step 3: Bug Pattern Scan

For each high-churn or untested file, use `mcp_repo_analysis_repo_analyze_file` and look for:

| Pattern | What to Look For | Severity |
|---------|-----------------|----------|
| **Missing error handling** | `try/except` gaps around I/O or network calls | High |
| **Bare except** | `except:` or `except Exception:` without specific types | Medium |
| **Unsafe type casts** | `as` casts (TS), unchecked type assertions | Medium |
| **Resource leaks** | Open files/connections without `with` or `finally` close | High |
| **Race conditions** | Shared mutable state without locks | High |
| **Hardcoded secrets** | API keys, tokens, or passwords in code | Critical |
| **SQL injection** | String formatting in SQL queries | Critical |
| **Missing input validation** | User input used without sanitization | High |
| **Overly complex functions** | Functions > 50 lines without docstring | Low |
| **TODO/FIXME/HACK** | Incomplete implementations | Info |

See `references/bug-patterns.md` for grep patterns to search for each.

### Step 4: Issue Grading

Grade each issue by difficulty:

- **🟢 Good First Issue**: < 20 lines changed, single file, clear acceptance criteria
- **🟡 Medium**:  20-100 lines, 2-3 files, may need design decision
- **🔴 Advanced**: 100+ lines, cross-module, requires architecture understanding

## FIRST_ISSUES.md Template

```markdown
# First Issues: <Repo Name>

## 🟢 Good First Issues (Week 1)

### GI-1: <Title>
- **Difficulty**: Beginner
- **Estimated time**: 2-4 hours
- **Files**: `[path/to/file.py:42-78](path/to/file.py#L42-L78)`
- **Problem**: <one-line description>
- **Acceptance criteria**:
  1. <specific, verifiable condition>
  2. ...
- **Hints**: <what to look at, who to ask>

[Repeat for 3-5 good first issues]

## 🟡 Medium Issues (Week 2-3)

### MI-1: <Title>
...

## 🔴 Advanced Issues (Month 1+)

### AI-1: <Title>
...

## Test Runner Quickstart
```bash
<command to run all tests>
<command to run a single test>
<command to run with coverage>
```
```

## Priority Heuristic

Sort issues by: `(high_churn * 3) + (no_tests * 3) + (bug_pattern_matches * 2) + (TODO_count * 1)`

This surfaces the lowest-hanging, highest-impact issues first — ideal for new contributors.
