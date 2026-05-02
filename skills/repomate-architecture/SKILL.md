---
name: repomate-architecture
description: "Codebase architecture analysis with file-level evidence citations (file path + line number). Use when: generating ARCHITECTURE.md for a repo, explaining core modules and their relationships, tracing data flow through a codebase, or answering 'how is X organized' questions. Load this skill after you have a codebase map from repo_structure — it guides deeper architectural analysis."
---
# Architecture Analysis with Evidence Citations

## Core Principle: Every Claim Needs a Citation

When describing architecture, every statement about code must include a file path and line range. Format: `[path/to/file.py:42-78](path/to/file.py#L42-L78)`

Never guess. Use `mcp_repo_analysis_repo_analyze_file` to verify before making claims.

## Analysis Methodology

### 1. Module Classification

Classify every source directory into one of:

| Category | Heuristic | Example |
|----------|-----------|---------|
| **Core domain** | Business logic, models, services | `src/models/`, `lib/core/` |
| **Interface** | API handlers, CLI, controllers | `routes/`, `commands/`, `handlers/` |
| **Infrastructure** | Database, networking, file I/O | `db/`, `http/`, `storage/` |
| **Utility** | Shared helpers, common libs | `utils/`, `common/`, `helpers/` |
| **Configuration** | Settings, env, feature flags | `config/`, `settings/` |
| **Test** | Test suites and fixtures | `tests/`, `spec/`, `__tests__/` |

### 2. Dependency Analysis Workflow

1. Start with `mcp_repo_analysis_repo_dependency_graph(repo_path, format="mermaid")`
2. Identify high-centrality nodes (in_degree + out_degree > 5)
3. For each high-centrality node, drill in with `mcp_repo_analysis_repo_analyze_file(file_path, include_dependencies=true)`
4. Trace the dependency chain: who imports this → what it imports → what those import
5. Build a layered diagram showing data flow direction

### 3. Pattern Recognition

Identify the dominant architectural pattern:

| Pattern | Signature |
|---------|-----------|
| **Layered** | Clear directory separation (presentation/business/data) with one-way deps |
| **MVC** | `models/`, `views/`, `controllers/` directories |
| **Plugin/Strategy** | Base class/interface + multiple implementations, factory pattern |
| **Event-Driven** | Event bus, message queue, pub/sub imports |
| **Hexagonal** | `ports/` and `adapters/` directories, interface-based boundaries |
| **Pipeline** | Sequential processing stages, chain-of-responsibility pattern |
| **Microkernel** | Small core + many plugin directories |

See `references/patterns.md` for detailed detection heuristics.

### 4. Key Interfaces & Extension Points

Identify:
- Public API surface: exported functions, public classes, HTTP routes, CLI commands
- Extension points: plugin interfaces, hook systems, configuration-driven behavior
- Integration boundaries: database interfaces, external service calls, MQ topics

### 5. Data Flow Tracing

Pick a representative feature and trace it:
1. Entry point (HTTP route, CLI command, event handler)
2. Middleware/auth/validation layers
3. Business logic processing
4. Data access
5. Response/event emission

## ARCHITECTURE.md Template

```markdown
# Architecture: <Repo Name>

## Overview
- **Language**: <primary language>
- **Pattern**: <dominant pattern>
- **Total source files**: <count>
- **Key dependencies**: <list external deps>

## Project Map
[Directory tree with module annotations]

## Core Modules
### <Module Name>
- **Path**: `<path/>`
- **Responsibility**: <one-line>
- **Depended on by**: <count> modules
- **Depends on**: <list of internal modules>
- **Key files**:
  - `[path/to/file.py:1-100](path/to/file.py#L1-L100)` — <purpose>
  - ...

## Data Flow
[Mermaid or ASCII diagram showing data flow]

## Extension Points
[List of plugin interfaces, hooks, config-driven behaviors]

## External Dependencies
[Critical third-party libraries and what they're used for]

## Anti-Patterns & Technical Debt
[areas that deviate from the dominant pattern or have accumulated churn]
```

## Citation Rules

- **Module descriptions**: cite the file that defines the module's public interface
- **Class/function claims**: cite exact line range from `repo_analyze_file` output
- **Data flow**: cite the entry point line, the processing line, and the output line
- **Dependencies**: cite the import statement line
- **Pattern claims**: cite at least 2 files that demonstrate the pattern
