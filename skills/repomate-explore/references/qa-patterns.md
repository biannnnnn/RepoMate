# Q&A Pattern Reference

Patterns for answering different types of code exploration questions.

## Entry-Point Questions

**Examples**: "Where does the auth system start?", "How do I run the task scheduler?"

**Workflow**:
1. Identify the module's public interface from the dependency graph
2. Look for: CLI commands, HTTP route registrations, `main()` functions, `__init__.py` exports
3. Use `repo_analyze_file` on the public interface files
4. Map the call chain: entry → validation → processing → response

**Response template**:
```
The {module} starts at [file:line]. Here's the flow:
1. {entry point} receives the request/command
2. It delegates to {next function}
3. ...
To invoke it: {CLI command or HTTP request}
```

## Data-Flow Questions

**Examples**: "How does a request get processed?", "How does data get from the API to the database?"

**Workflow**:
1. Start from the entry point
2. Use `repo_analyze_file` to get dependencies
3. Follow the import chain: entry → service → repository → model
4. Document data transformations at each step
5. Identify any side effects (logging, events, notifications)

**Response template**:
```
Data flow for {feature}:

1. **Input** at [file:line]: {what comes in}
2. **Validation** at [file:line]: {what gets checked}
3. **Processing** at [file:line]: {what transformation happens}
4. **Persistence** at [file:line]: {what gets stored}
5. **Response** at [file:line]: {what goes out}
```

## Dependency Questions

**Examples**: "Who uses the User model?", "What does the auth middleware depend on?"

**Workflow**:
1. Call `repo_dependency_graph` to get the full picture
2. For "who uses X": look at dependents (reverse dependencies)
3. For "what does X depend on": look at forward dependencies
4. Sort by centrality: most-depended-upon modules are most important to understand first

**Response template**:
```
{module} is depended on by {count} modules:
- [file:line] — {how it uses it}
- ...

{module} depends on {count} modules:
- [file:line] — {why it needs it}
```

## Structure Questions

**Examples**: "How is the project organized?", "What's in the utils directory?"

**Workflow**:
1. Call `repo_structure` focused on the area of interest
2. Classify files by role
3. Note any patterns: consistent file naming, 1-class-per-file, barrel exports

**Response template**:
```
{Directory} contains {count} files organized as:
- {category}: {file list with brief descriptions}
```

## Pattern Questions

**Examples**: "Why is auth implemented this way?", "Is this a plugin architecture?"

**Workflow**:
1. Read `references/patterns.md` from `repomate-architecture`
2. Look for pattern signatures in the codebase
3. Cite 2-3 pieces of evidence supporting the pattern classification
4. Explain the rationale: what problem does this pattern solve here?

**Response template**:
```
This is a {pattern name}. Evidence:
1. [file:line] — {pattern element}
2. [file:line] — {pattern element}

This pattern is used because {rationale}. The trade-off is {trade-off}.
```
