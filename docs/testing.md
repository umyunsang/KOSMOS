# Testing Guide

KOSMOS testing conventions and expectations. `AGENTS.md` summarizes the rules; this file is the long form.

## Stack

- **Runner**: `pytest` with `pytest-asyncio`
- **Fixtures**: recorded JSON under `tests/fixtures/`
- **Assertions**: plain `assert` — no unittest.TestCase subclasses
- **Mocks**: `pytest-mock` for in-process patches, `respx` for httpx, never mock Pydantic models

## Layout

```
tests/
├── conftest.py                  # shared fixtures
├── fixtures/
│   └── <provider>/<tool_id>.json
├── tools/
│   └── <provider>/test_<tool_id>.py
├── query_engine/
├── permissions/
└── agents/
```

Every source module under `src/kosmos/<area>/<module>.py` gets a parallel `tests/<area>/test_<module>.py`.

## Running tests

```bash
uv run pytest                    # default — fast, fixture-only
uv run pytest -m live            # include live API calls (local only)
uv run pytest tests/tools        # scope to one area
uv run pytest -k koroad          # filter by keyword
uv run pytest --cov=src/kosmos   # with coverage
```

Run `uv run pytest` before every commit. Once CI is configured, CI must be green before merging a PR.

## Live-call discipline

Integration tests that would hit live `data.go.kr` APIs are marked:

```python
import pytest

@pytest.mark.live
async def test_koroad_adapter_real_endpoint():
    ...
```

Rules:
- `@pytest.mark.live` tests are **skipped by default** via `pyproject.toml` config
- CI never runs them
- Developers run them locally when validating a new adapter or debugging a fixture mismatch
- If a live test fails, fix the adapter and re-record the fixture — do not delete the test

## Fixture recording

1. Set the API key: `export KOSMOS_DATA_GO_KR_KEY=...`
2. Run the recording script: `scripts/record_fixture.py <tool_id>`
3. Review the captured JSON for personal data, redact anything sensitive
4. Commit under `tests/fixtures/<provider>/<tool_id>.json`

Never commit a fixture containing real citizen PII. Synthetic values only.

## Test categories

**Unit tests** — pure functions, schema validation, tool input/output parsing. Must run in milliseconds and have no I/O.

**Adapter tests** — replay a recorded fixture through the adapter and assert the parsed output shape. Use `respx` to stub httpx.

**Integration tests** — exercise the query engine with a full tool loop against fixture-backed adapters. These are slower but still deterministic.

**Live tests** — marked `@pytest.mark.live`, opt-in only.

## Coverage expectations

- New tool adapters: one happy-path + one error-path test minimum
- New query engine features: unit tests for the state machine transitions
- Bug fixes: a regression test reproducing the bug, added in the same PR as the fix
- Refactors: the existing test suite must still pass; no loosening of assertions without justification

## What not to test

- Third-party library internals (httpx, pydantic, openai)
- The FriendliAI endpoint itself
- Trivial getters and one-line wrappers
- Private methods — test via the public interface

## Async tests

Use `pytest-asyncio` in auto mode:

```python
import pytest

@pytest.mark.asyncio
async def test_query_engine_loop():
    ...
```

Configure in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
markers = ["live: hits real data.go.kr APIs, skipped by default"]
```

## Test data language

Test values may include Korean strings when they represent real domain data a citizen would send (e.g., `"홍길동"`, `"부산광역시"`). Test names, docstrings, and assertion messages stay English per the source code language rule.
