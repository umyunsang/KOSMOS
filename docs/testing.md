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

| Layer | What it answers | Tool | Output | LLM-readable? |
|-------|----------------|------|--------|---------------|
| 1. Unit / fixture tests | "Does each module's contract hold?" | `pytest` / `bun test` | text | ✓ grep |
| 2. **stdio JSONL probe** | "Does the backend invoke tools when given a citizen prompt?" | `subprocess.Popen(['uv','run','kosmos','--ipc','stdio'])` + line-based JSONL frames | `*.jsonl` | ✓ grep |
| 3. **Text-log smoke** | "Does the full TUI session render the expected text?" | `expect(1)` / `script(1)` / `asciinema rec` | `*.txt` / `*.cast` (JSON-Lines) | ✓ grep |
| 4. **vhs visual + PNG keyframes** | "Does the rendered UI render the expected pixels at each scenario stage?" | `vhs file.tape` with `Output ...gif` + 3+ `Screenshot ...png` directives | `*.gif` (animated) + `*.png` (keyframes) | ✓ multimodal vision (Claude/Codex Read tool on each PNG) |

All four layers are **gating** for TUI-changing PRs (2026-04-29 — Layer 4 promoted from supplementary). Layers 1–3 are LLM-grep-friendly text; Layer 4 is LLM-vision-friendly via the keyframe PNGs (the bare `.gif` is for humans + animated proof, but the agent Read tool only renders its first frame, which is typically a blank prompt during boot).

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

### Layer 4 — vhs visual + PNG keyframes

`vhs` (Charm, ≥ 0.11) records `.gif` / `.mp4` / `.webm` for animated visual proof AND captures static PNG keyframes at named scenario stages via the `Screenshot` directive. The PNG keyframes are the **LLM-reviewable** artefact: Lead Opus uses the Read tool (Claude / Codex multimodal vision) to inspect each keyframe before push. The bare `.gif` is for humans and animated proof — the agent Read tool only renders its first frame, which during boot is typically a blank prompt.

**Canonical 3-keyframe rule** (extend per scenario complexity):

| Keyframe | Stage | What it proves |
|---|---|---|
| `smoke-keyframe-1-boot.png` | After `bun run tui` settles | KOSMOS branding, boot-guard line (`tool_registry: N entries verified ...`), prompt rendered |
| `smoke-keyframe-2-input.png` | After citizen Korean input + Enter | Input was accepted (text echoed in REPL prompt area, ANSI not garbled) |
| `smoke-keyframe-3-action.png` | After scenario action settles (permission prompt, tool call, agentic-loop indicator) | The change being landed actually fires — primitive call, permission render, error envelope, etc. |

Add more keyframes when the scenario branches (e.g. permission `y` vs `n`, `/help` overlay, `/agents --detail`). 3 is the floor, not the ceiling.

**Reference tape** (run from worktree root):

```text
# specs/<spec>/scripts/smoke.tape
Output specs/<spec>/smoke.gif
Set Width 1200
Set Height 800
Set FontSize 14
Set TypingSpeed 50ms

# Backend mock so the TUI boots without a live FriendliAI key
Env KOSMOS_BACKEND_CMD "sleep 60"

Type "cd tui && bun run tui"
Enter
Sleep 6s
Screenshot specs/<spec>/smoke-keyframe-1-boot.png

Type "강남역 어디야?"
Enter
Sleep 4s
Screenshot specs/<spec>/smoke-keyframe-2-input.png

Sleep 6s
Screenshot specs/<spec>/smoke-keyframe-3-action.png

Ctrl+C
Sleep 500ms
Ctrl+C
```

```bash
vhs specs/<spec>/scripts/smoke.tape
```

Lead Opus then runs `Read` on each `*.png` and asserts the visible elements match the spec's acceptance criteria. **DO NOT** use ffmpeg post-extraction to pull middle frames — `Screenshot` is more deterministic (frame timing controlled by the tape) and a single tool, no shell-out.

The tape, the gif, and every keyframe go into the spec directory and the PR description references them. The text-log version of the same scenario (Layer 3) lives next to them for LLM grep audit.

**Why this layer is mandatory** (and not, as previously stated, "supplementary"): pure text logs cannot detect ANSI-cell-level rendering regressions (purple-on-purple branding text invisible against the wrong theme; Korean wide-glyph alignment breaking the prompt; the UFO mascot rendering as `?`-blocks). The Epic γ #2294 PR #2394 review surfaced the gap — `feedback_pr_pre_merge_interactive_test` was satisfied by the text log, but no agent had visually confirmed the citizen UI actually composed correctly. Layer 4 with `Screenshot` PNGs closes that loop without sacrificing the LLM-review property.

### Cross-layer debugging heuristics

- **Tool-calling regression** — Layer 2 (stdio) is the gate. If `tool_call` count is 0, the prompt or registry is the bug.
- **TUI render regression** — Layer 3 (text log) reveals it: missing assistant text, garbled ANSI, frozen cursor.
- **Latency or streaming regression** — Layer 3 `.cast` timestamps surface chunk delays.
- **Prompt / context bleed** — Layer 3 grep on the captured transcript: e.g. `grep -E '/Users/|gitStatus|claudeMd' smoke.txt` should return zero for citizen runs.
- **Visual / pixel-level regression** — Layer 4 `Screenshot` PNGs, agent-vision-reviewed via Read. Catches: theme contrast (purple-on-purple branding), Korean wide-glyph misalignment, mascot rendering as `?`-blocks, banner truncation, REPL prompt jumping.

### Reference implementations

- **Epic γ #2294** (`specs/2294-5-primitive-align/scripts/`) — the canonical Layer 2 + 4 template post-2026-04-29 promotion:
  - `smoke-emergency-lookup.expect` — Layer 2 (expect-driven, mock-backend, captures the agentic-loop entry path).
  - `smoke-emergency-lookup.tape` — Layer 4 (vhs visual; emit `smoke-emergency-lookup.gif` + 3 `Screenshot` keyframes).
- **Epic #2152** (`specs/2152-system-prompt-redesign/scripts/`) — pre-2026-04-29 era; uses Layer 2 + the old "Layer 4 is supplementary" pattern:
  - `smoke-stdio.py` — Layer 2 (Python-driven stdio JSONL probe; deterministic SC-1 audit).
  - `smoke-one.sh` / `smoke-five.sh` — Layer 3 (expect-driven citizen scenarios under `script(1)`).
  - `smoke.tape` — Layer 4 in the old shape (gif only). Future PRs touching this Epic SHOULD migrate it to the keyframe pattern.

Use the Epic γ #2294 templates as the canonical starting point for any future TUI-affecting Epic.
