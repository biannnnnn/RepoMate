# Onboarding Document Template

Use this template when generating ONBOARDING.md. Replace placeholders with actual repo data.

## Day 1: Setup & First Run

**Goal**: Get the project running locally

### Setup Steps
1. [Platform-specific setup requirements]
2. Clone and install dependencies: `[install command]`
3. Configure environment: [env vars to set]
4. Run the dev server: `[run command]`

### Reading (30-60 min)
- [README.md, CONTRIBUTING.md, etc.]
- Top-level config files: [list]
- The directory structure overview (from `repo_structure` output)

### Checkpoint
- [ ] Project runs locally
- [ ] Can navigate top-level directory structure
- [ ] Understands the primary language and framework

## Day 2: Core Architecture

**Goal**: Understand the high-level design

### Reading (2-3 hours)
- ARCHITECTURE.md (generated)
- [3-5 most-central files from dependency graph]

### Exercise
- Draw a diagram of the main modules and their relationships
- Identify the entry point for one user-facing feature

### Checkpoint
- [ ] Can explain the architectural pattern
- [ ] Knows which modules depend on which
- [ ] Can find the 5 most-imported modules

## Day 3: Data Flow

**Goal**: Trace data end-to-end

### Reading (2-3 hours)
- [List of data flow files: entry → handler → service → model → response]

### Exercise
- Pick a simple feature, trace it from request to response
- Document the data flow in a sequence diagram

### Checkpoint
- [ ] Can trace one feature end-to-end
- [ ] Understands the data model
- [ ] Knows where validation happens

## Day 4: Testing & Tools

**Goal**: Run tests and set up debugging

### Reading (1-2 hours)
- [Test infrastructure files: conftest, setup, helpers]
- The test framework documentation

### Exercise
- Run the full test suite
- Run a single test with a debugger
- Read 3 test files to understand testing patterns

### Checkpoint
- [ ] Test suite passes
- [ ] Can write and run a new test
- [ ] Familiar with debugging tools

## Day 5: First Contribution

**Goal**: Ship your first change

### Pick an Issue
Choose a GI-* (Good First Issue) from FIRST_ISSUES.md.

### Process
1. Create a feature branch
2. Implement the fix
3. Write/update tests
4. Open a PR
5. Go through code review
6. Merge

### Checkpoint
- [ ] First PR opened
- [ ] Familiar with code review process
- [ ] Can navigate the codebase independently
