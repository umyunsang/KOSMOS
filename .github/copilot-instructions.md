## Review Rules

**ALWAYS prefix every inline comment with exactly one of:**

- `🔴 CRITICAL:` — security vulnerabilities, data loss risks, crashes, race conditions
- `🟡 IMPORTANT:` — logic errors, missing error handling, performance issues, type safety
- `🟢 SUGGESTION:` — style, naming, optional improvements, alternative approaches

**SKIP commenting on:**

- Code already covered by linting or type checking (formatting, import order, type annotations)
- Tests that already exist and pass
- Naming unless severely misleading
- Markdown, YAML, or configuration files

**Only comment when confidence > 80%.**
One sentence per issue. Include a suggested fix when possible.
