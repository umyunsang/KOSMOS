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

## CI OTEL suppression

CI sets `OTEL_SDK_DISABLED=true` at the job level (`jobs.test.env`) so no OTLP exporter, `BatchSpanProcessor`, or network activity is ever initialised during test runs (FR-009, SC-003).

## TUI verification methodology

Pytest covers the Python backend; the TUI (Ink + Bun) and the stdio IPC bridge sit *outside* that perimeter. "작동 확인" / "검증" / "smoke" requests MUST exercise the actual interactive path — code grep alone is not verification (memory `feedback_runtime_verification`).

This section is the canonical reference cited from `AGENTS.md § TUI verification`. It distils the upstream community guidance (Charm `vhs`, `asciinema`, POSIX `expect(1)` / `script(1)`, Microsoft `node-pty`) into a four-layer ladder where each layer answers a different question and isolates a different failure mode.

### The four-layer ladder

Run **all four layers** for any change that touches the chat-request emit path, the TUI render layer, or the LLM orchestration loop. The cost is a few minutes; the alternative is shipping a regression that pytest cannot see.

| Layer | What it answers | Tool | Output | LLM-grep? |
|-------|----------------|------|--------|-----------|
| 1. Unit / fixture tests | "Does each module's contract hold?" | `pytest` / `bun test` | text | ✓ |
| 2. **stdio JSONL probe** | "Does the backend invoke tools when given a citizen prompt?" | `subprocess.Popen(['uv','run','kosmos','--ipc','stdio'])` + line-based JSONL frames | `*.jsonl` | ✓ |
| 3. **Text-log smoke** | "Does the full TUI session render the expected text?" | `expect(1)` / `script(1)` / `asciinema rec` | `*.txt` / `*.cast` (JSON-Lines) | ✓ |
| 4. **vhs `.tape` (visual)** | "Does the rendered UI match what a citizen will actually see?" | `vhs file.tape` | `*.gif` / `*.mp4` / `*.webm` | ✗ (binary) |

Layers 1–3 are the **gating** layers — every smoke run must produce text artefacts that LLM reviewers (Codex inline review) and CI greps can audit. Layer 4 is **supplementary** for human-eye review.

### Layer 2 — stdio JSONL probe

The most deterministic verification. Bypasses the TUI render layer entirely; proves the LLM tool-calling chain works.

```bash
# Spawn the backend, send one chat_request, read JSONL frames back.
specs/<spec>/scripts/smoke-stdio.py
# → emits smoke-stdio-<scenario>.jsonl per scenario
# → grep -c '"kind":"tool_call"' smoke-stdio-*.jsonl
```

Frame schema is `kosmos.ipc.frame_schema.ChatRequestFrame` (extra fields rejected — `version: "1.0"` not `1`). Required fields: `version`, `kind`, `role`, `session_id`, `correlation_id`, `frame_seq`, `ts`, `messages`. The backend's first reply is a `session_event{event:"exit"}` only when stdin closes — there is no boot-ready signal; just send the request immediately after spawn.

When this layer fails the bug is in the prompt / registry / agentic loop (server side). When it passes but Layer 3 fails, the bug is in the TUI render or the IPC bridge (TS side).

### Layer 3 — Text-log smoke

Captures the full pty session including ANSI escape codes. Three interchangeable tools, ranked by reliability under LLM driving:

1. **`expect`** — POSIX-standard, scripted, tightest control. Use for citizen smoke runs:

   ```bash
   expect <<'EOF' > specs/<spec>/smoke.txt 2>&1
   set timeout 90
   spawn -noecho bun --cwd tui run tui
   sleep 6
   send -- "강남역 어디?\r"
   sleep 60
   send -- "\x03"
   expect eof
   EOF
   ```

   Caveat: `expect`'s `log_file` directive silently drops output when the script is driven via heredoc; wrap the call in `script(1)` for reliable capture.

2. **`script(1)`** — POSIX terminal session capture. Wraps any command (including expect):

   ```bash
   script -q smoke.txt expect -f /tmp/scenario.exp
   ```

   On macOS the syntax is `script -q file cmd args`; on Linux `script -q -c "cmd args" file`.

3. **`asciinema`** — JSON-Lines (`.cast`) format. Best when timestamp-aware analysis is needed:

   ```bash
   asciinema rec --command "bun run tui" --idle-time-limit 2 smoke.cast
   ```

When this layer fails but Layer 2 passes, the regression is in the TUI render path (Ink components, raw-mode keystroke handling, frame transport).

### Layer 4 — vhs `.tape` (human visual)

`vhs` records `.gif` / `.mp4` / `.webm` only — not text. Use it for human-eye review of the rendered UI, not for LLM verification:

```text
# specs/<spec>/scripts/smoke.tape
Output specs/<spec>/smoke.gif
Set Width 1200
Set Height 800
Set FontSize 14
Set TypingSpeed 50ms
Type "bun run tui"
Enter
Sleep 6s
Type "강남역 어디야?"
Enter
Sleep 60s
Ctrl+C
```

```bash
vhs specs/<spec>/scripts/smoke.tape
```

The gif goes into the spec directory and the PR description references it. The text-log version of the same scenario (Layer 3) lives next to it for LLM grep audit.

### Cross-layer debugging heuristics

- **Tool-calling regression** — Layer 2 (stdio) is the gate. If `tool_call` count is 0, the prompt or registry is the bug.
- **TUI render regression** — Layer 3 (text log) reveals it: missing assistant text, garbled ANSI, frozen cursor.
- **Latency or streaming regression** — Layer 3 `.cast` timestamps surface chunk delays.
- **Prompt / context bleed** — Layer 3 grep on the captured transcript: e.g. `grep -E '/Users/|gitStatus|claudeMd' smoke.txt` should return zero for citizen runs.
- **Visual-only regression (colours, alignment)** — Layer 4 gif, eyeballed.

### Reference implementation

Epic #2152 (`specs/2152-system-prompt-redesign/scripts/`) ships:

- `smoke-stdio.py` — Layer 2 (Python-driven stdio JSONL probe; deterministic SC-1 audit).
- `smoke-one.sh` / `smoke-five.sh` — Layer 3 (expect-driven citizen scenarios under `script(1)`).
- `smoke.tape` — Layer 4 (vhs visual recording for the integrated PR description).

Use these as the template for any future TUI-affecting Epic.
