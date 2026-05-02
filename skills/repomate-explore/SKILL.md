---
name: repomate-explore
description: "Interactive code exploration and Q&A for understanding specific modules or subsystems. Use when: the user asks 'help me understand X module', 'what files should I read first for Y', 'how does Z work in this codebase', or any targeted question about a specific subsystem after initial onboarding. Provides a structured approach to trace code paths and recommend reading orders."
---
# Interactive Code Exploration

## When to Use This Skill

Load this skill when the user asks targeted questions like:
- "Help me understand the login module"
- "What files should I read first for the auth system?"
- "How does request routing work?"
- "Where is error handling defined?"
- "What's the database schema?"

Do NOT load this skill for full-onboarding requests — use `repomate-onboard` for that.

## Question Taxonomy

Classify the user's question into one of:

| Type | Question Pattern | Approach |
|------|-----------------|----------|
| **Entry-point** | "Where does X start?", "How do I run Y?" | Find CLI commands, HTTP routes, main() functions |
| **Data-flow** | "How does X get from A to B?" | Trace imports, function calls, data transformations |
| **Dependency** | "What does X depend on?", "Who uses X?" | Dependency graph + reverse dependency analysis |
| **Structure** | "How is X organized?", "What files are in Y?" | Directory tree + module classification |
| **Pattern** | "Why is X done this way?" | Architecture pattern recognition + rationale |

## Response Format

For every answer, structure your response as:

### 1. Quick Answer (2-3 sentences)
Summarize the answer in plain language before diving into details.

### 2. Recommended Reading Order
List files in dependency order (dependencies first, then the target, then dependents):

```
📖 Reading Order for "auth module":
1. config/auth.py           ← configuration (no deps)
2. utils/crypto.py           ← hashing utilities
3. models/user.py            ← data model
4. middleware/auth.py         ← the auth middleware itself
5. routes/login.py            ← HTTP handler that uses auth
6. tests/auth_test.py         ← test to see how auth is exercised
```

### 3. Key Entry Points
List the most important functions/classes to look at first, with line numbers:

```
🔑 Key Entry Points:
- AuthMiddleware.authenticate() — [middleware/auth.py:45-89](middleware/auth.py#L45-L89)
- create_session(user) — [utils/session.py:120-145](utils/session.py#L120-L145)
```

### 4. Concept Map
Show how the module relates to the rest of the codebase:

```
         ┌─────────────┐
         │  routes/     │ ← depends on auth
         ├─────────────┤
         │  middleware/ │ ← THE AUTH MODULE
         ├─────────────┤
         │  models/     │ ← auth depends on this
         │  utils/      │
         └─────────────┘
```

### 5. Code Citations
Every claim must cite exact locations:

> The `authenticate()` method at `[middleware/auth.py:45](middleware/auth.py#L45)` extracts the JWT from the Authorization header, verifies it at line 52, and retrieves the user from the database at line 58. If verification fails, it raises `AuthError` defined at `[middleware/auth.py:12](middleware/auth.py#L12)`.

## Tracing Methodology

To trace a feature end-to-end:

1. **Find the entry point**: Use `mcp_repo_analysis_repo_analyze_file` on likely entry files (CLI commands, route handlers, event listeners)
2. **Follow the imports**: Look at the imports list in the `repo_analyze_file` output to find what the entry point depends on
3. **Drill into each dependency**: Analyze each internal dependency to understand its role
4. **Map the data flow**: Trace how data transforms from entry to exit
5. **Identify the exit point**: Find where the response is sent, file is written, or event is emitted

## Reading Order Algorithm

To recommend a reading order:

1. Start with the target file(s) the user asked about
2. List their internal dependencies (from `repo_analyze_file` with `include_dependencies=true`)
3. Sort dependencies by depth: dependencies-of-dependencies first, then direct dependencies, then the target
4. Add test files for the target module at the end
5. Limit to 5-8 files for a focused reading session

## Common Follow-up Questions

After answering, suggest 2-3 follow-up questions the user might want to ask:

> **You might also want to know:**
> - "How does the auth system handle token refresh?"
> - "What database tables does auth use?"
> - "How do I add a new auth provider?"
