# Bug Pattern Catalog

Grep patterns to search for common bugs. Run these with `grep -rn` or the equivalent search tool against the repository.

## Security

| Pattern | Grep | Example | Severity |
|---------|------|---------|----------|
| Hardcoded secrets | `password\s*=|api_key\s*=|secret\s*=|token\s*=` | `API_KEY = "sk-..."` | 🔴 Critical |
| SQL injection | `f".*SELECT\|f".*INSERT\|f".*UPDATE\|f".*DELETE\|%.*sql\|\.format\(.*sql` | `f"SELECT * FROM users WHERE id={user_id}"` | 🔴 Critical |
| XSS (unescaped output) | `innerHTML\|dangerouslySetInnerHTML\|v-html` | `div.innerHTML = userInput` | 🟠 High |
| Command injection | `os\.system\(.*format\|os\.system\(.*f"\|subprocess.*shell=True` | `os.system(f"rm {path}")` | 🔴 Critical |
| Open redirect | `redirect.*request\.\|redirect.*params` | `redirect(request.args.get('next'))` | 🟡 Medium |

## Error Handling

| Pattern | Grep | Severity |
|---------|------|----------|
| Bare except (Python) | `except:\|except Exception:` | 🟡 Medium |
| Empty catch | `catch.*\{\s*\}` | 🟡 Medium |
| Swallowed error | `except.*:\s*pass\|except.*:\s*logger` | 🟠 High |
| Unchecked promise | `\.then\(.*\)(?!.*\.catch)` | 🟡 Medium |

## Resource Management

| Pattern | Grep | Severity |
|---------|------|----------|
| Unclosed file | `open\(.*(?!.*with)` | 🟠 High |
| Unclosed connection | `\.connect\(.*(?!.*close)` | 🟠 High |
| Missing cleanup | `\.acquire\(.*(?!.*release)\|\.lock\(.*(?!.*unlock)` | 🟠 High |

## Concurrency

| Pattern | Grep | Severity |
|---------|------|----------|
| Shared state without lock | `global\s+\w+\s*(?!.*Lock)\|self\.\w+\s*=.*(?!.*lock)` | 🟠 High |
| Sleep in test | `time\.sleep\|sleep\(\d+\)` | 🟡 Medium |
| Untimed wait | `await.*(?!.*timeout)` | 🟡 Medium |

## Code Quality

| Pattern | Grep | Severity |
|---------|------|----------|
| TODO/FIXME/HACK | `TODO\|FIXME\|HACK\|XXX\|WORKAROUND` | 🟢 Info |
| Commented-out code | `#.*def \|#.*class \|//.*function \|//.*class ` | 🟢 Info |
| Debug prints | `console\.log\|print\(.*\|fmt\.Println\|println!` | 🟢 Info |
| Overly broad exception | `except Exception:\|except BaseException:\|catch \(Exception` | 🟡 Medium |

## Testing

| Pattern | Grep | Severity |
|---------|------|----------|
| Skipped test | `@skip\|@pytest\.mark\.skip\|it\.skip\|test\.skip\|xtest\|xdescribe` | 🟢 Info |
| Test with no assertions | Test files without `assert\|expect\|\.should\.` | 🟡 Medium |
| Flaky test indicators | `\.retry\|flaky\|\.times\(\d+\)` in test files | 🟠 High |

## Type Safety (TypeScript/Python with types)

| Pattern | Grep | Severity |
|---------|------|----------|
| `as` cast (TS) | `\s+as\s+\w+` | 🟡 Medium |
| `any` type | `:\s*any\b` | 🟡 Medium |
| `@ts-ignore` | `@ts-ignore\|@ts-expect-error` | 🟡 Medium |
| `# type: ignore` | `# type: ignore` | 🟢 Info |
