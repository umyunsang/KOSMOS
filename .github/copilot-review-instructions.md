# Copilot Code Review — Custom Instructions

## Project Context

KOSMOS is a conversational multi-agent platform that orchestrates Korean public APIs
(`data.go.kr`) through a tool loop powered by K-EXAONE (FriendliAI Serverless).
Python 3.12+ backend with Pydantic v2 for all data models.

## Critical Rules — Flag as errors

1. **Pydantic v2 only**: All tool input/output models must use `pydantic.BaseModel` (v2).
   Flag any use of `pydantic.v1`, `from pydantic.v1 import`, dict-based I/O without
   validation, or `Any` type annotations.

2. **No hardcoded secrets**: API keys, tokens, and credentials must never appear in source.
   All environment variables must use `KOSMOS_` prefix. Flag any bare strings that look
   like API keys or connection strings.

3. **No `print()` outside CLI layer**: Only `src/kosmos/cli/` may use `print()` or
   `rich.print()`. All other modules must use `logging`. Flag `print()` calls in
   non-CLI modules.

4. **English source text**: All comments, docstrings, log messages, error messages, and
   CLI output must be in English. Korean is allowed only in domain data (civil affairs
   content, legal terms, API response data, `search_hint` fields).

5. **No `Any` type**: Never use `typing.Any` or `Any` in type annotations. Use proper
   typed models, `Union`, or `object` instead.

6. **No live API calls in tests**: Tests calling real `data.go.kr` APIs must be decorated
   with `@pytest.mark.live`. Flag any undecorated test that makes HTTP requests to
   external services.

## Architecture Rules — Flag as warnings

7. **Fail-closed defaults**: Permission checks, tool execution gates, and safety filters
   must default to deny/reject. Flag any permission logic that defaults to allow.

8. **Type hints required**: All public functions and methods must have complete type
   annotations (parameters and return type). Flag missing annotations on public APIs.

9. **Import ordering**: Follow stdlib -> third-party -> local ordering. Flag violations.

10. **No dependency additions without spec**: New dependencies in `pyproject.toml` should
    be part of a spec-driven PR. Flag unexpected dependency additions.

11. **Async consistency**: HTTP calls via `httpx` should use `AsyncClient`. Flag
    synchronous `httpx.Client` usage in async contexts.

## What NOT to flag — Do NOT comment on these

- **Formatting and style**: whitespace, line length, trailing commas, quote style — handled by Ruff
- **Naming suggestions**: variable/function/class name preferences — skip unless misleading
- **Minor refactoring**: "could extract to a helper", "consider using X instead of Y" — skip
- **Documentation**: missing docstrings, comment improvements — skip unless critical to understanding
- **Import ordering**: handled by Ruff isort — do not flag
- **Minor optimization**: skip unless it changes algorithmic complexity (O(n) → O(n²))
- **Type narrowing suggestions**: skip unless it would prevent a runtime error
- Korean text in `search_hint` fields, domain data fixtures, or test data
- `KOSMOS_` prefixed environment variable references
- `@pytest.mark.live` decorated tests that call external APIs
- TypeScript files under TUI layer (Phase 2+, not yet implemented)

## Review philosophy

Only comment on issues you are **highly confident** about. Prioritize:
1. Bugs and logic errors that will cause runtime failures
2. Security vulnerabilities
3. Violations of the Critical Rules above

Do not leave comments that are merely suggestions or preferences. If in doubt, do not comment.
