# Implementation Plan: Phase 1 Hardening — LLM Rate-Limit Resilience & KOROAD Tool Input Discipline

**Branch**: `019-phase1-hardening` | **Date**: 2026-04-14 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/019-phase1-hardening/spec.md`

## Summary

Close two live-validation defects blocking Phase 1 MVP release:

1. **Tool-input discipline** — enforce that administrative region codes (sido/gugun) for the KOROAD accident-search tool are always sourced from a prior `address_to_region` geocoding call, never fabricated from LLM memory. Applied via Pydantic v2 `Field(description=...)` hardening (tool schema) and session-bootstrap system-prompt ordering rules (context assembly).
2. **Rate-limit resilience** — replace the blind `asyncio.sleep(60)` cooldown with Retry-After-aware exponential backoff plus a per-session `asyncio.Semaphore(1)` concurrency gate in the LLM client, handling both pre-stream and mid-stream 429 surfaces. Default sampling/generation parameters realigned with the Korean LLM's published recommendations.

Validated by the live suite (`-m live`) going 30/30 green with no fixed cooldowns, while existing mocked unit tests for `tests/llm/`, `tests/tools/`, `tests/context/` remain green.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: `httpx >=0.27` (async HTTP + streaming 429 detection), `pydantic >=2.0` (tool I/O schemas with `Field(description=...)` exposed as JSON schema to the LLM), `pytest` + `pytest-asyncio` (unit + `@pytest.mark.live` gated E2E). No new runtime dependencies introduced.
**Storage**: N/A (no persistent state; rate-limit retry counters and semaphore live in `LLMClient` instance memory for the session's lifetime).
**Testing**: `uv run pytest` (mocked) + `uv run pytest -m live` (maintainer-local, off-CI). Unit tests cover Retry-After parsing, exponential-backoff timing, semaphore serialization, and new default-parameter payload assertions. Live tests cover the "강남역" admin-code assertion and the multi-turn scenario without fixed cooldown.
**Target Platform**: Local CLI (`kosmos` REPL) on macOS/Linux maintainer machines. CI runs only the non-live subset.
**Project Type**: Single project — existing `src/kosmos/` (Python library + CLI). No frontend/backend split; TUI is out of scope (Phase 2).
**Performance Goals**:
- Live multi-turn scenario wall-clock ≤ current baseline (which includes the 60s blind cooldown) — SC-004.
- Within bounded retry budget (5 attempts, 60s cap) the LLM client recovers from ≥95% of observed 429 occurrences — SC-003.
**Constraints**:
- FriendliAI Serverless Tier 1 bucket (100 RPM / 100 TPM) — per-session serialization sufficient per Assumptions §Spec.
- Live suite runs under maintainer quota only; CI MUST NOT call live providers (`AGENTS.md § Hard rules`).
- Backwards-compatible signature — any new parameter must be overridable by explicit caller argument (FR-010).
**Scale/Scope**:
- ~30 live-marked tests across 6 live test modules.
- Touched files (estimated): `src/kosmos/llm/client.py`, `src/kosmos/tools/koroad/koroad_accident_search.py`, `src/kosmos/context/builder.py` (or session bootstrap), plus `tests/llm/`, `tests/live/test_live_e2e.py`.

## Constitution Check

*GATE: Evaluated before Phase 0 research and re-evaluated after Phase 1 design.*

| Principle | Applies to this feature? | Compliance check |
|---|---|---|
| **I. Reference-Driven Development** | Yes (Layer 1, 2, 5, 6) | Every design decision maps to a reference in `docs/vision.md § Reference materials`. See mapping table below. Phase 0 `research.md` records one Decision/Rationale/Alternative per mapped layer. |
| **II. Fail-Closed Security** | Yes (Layer 2) | KOROAD tool-input hardening is a fail-closed enhancement: ambiguous admin codes now emit LLM-visible "NEVER fill from memory" guidance. No bypass-immune permission check is weakened. `requires_auth`, `is_personal_data`, `is_concurrency_safe`, `cache_ttl_seconds` defaults unchanged. |
| **III. Pydantic v2 Strict Typing** | Yes (Layer 2) | `KoroadAccidentSearchInput` remains Pydantic v2; only `Field(description=...)` text is strengthened. No `Any` introduced. `input_schema` / `output_schema` / `search_hint` untouched. |
| **IV. Government API Compliance** | Yes | Live KOROAD/Kakao/KMA calls remain off-CI (`@pytest.mark.live`). No hardcoded keys. `rate_limit_per_minute` tracking unchanged. Happy + error path preserved. |
| **V. Policy Alignment** | Indirect | The LLM reliability fix protects citizens from receiving wrong-district accident data — aligns with Principle 8 (single trustworthy conversational window) and PIPA spirit (do not hand back data the citizen did not actually ask for). |
| **VI. Deferred Work Accountability** | Yes | Spec "Deferred to Future Work" table states "No items deferred — all requirements are addressed in this epic." No free-text "future phase" references in spec. `/speckit-analyze` will re-verify. |

### Reference mapping (Principle I — mandatory)

| Requirement | Layer | Primary reference | Secondary reference | Design decision |
|---|---|---|---|---|
| FR-005, FR-006, FR-007, FR-008 (retry, Retry-After, jitter, mid-stream 429, categorized terminal failure) | **6 — Error Recovery** | OpenAI Agents SDK retry matrix | stamina (enforced jitter + capped backoff) + Claude Agent SDK (streaming error handling) | Retry-After-first policy; on absence, stamina-style exponential backoff with ±20% jitter, 60s cap, 5 attempts; streaming chunk-level 429 surfaced identically to pre-stream; exhaustion → `LLMResponseError`. |
| FR-009 (per-session concurrency gate) | **1 — Query Engine** | Claude Agent SDK async generator loop | Claude Code sourcemap (tool loop internals) | `asyncio.Semaphore(1)` held across `complete()` and `stream()` on the same `LLMClient` instance — serializes same-session bucket pressure without cross-session coupling. |
| FR-003 (tool input guidance block) | **2 — Tool System** | Pydantic AI schema-driven registry | Claude Agent SDK tool definitions | Use Pydantic v2 `Field(description=...)` which surfaces verbatim in the JSON schema emitted to the LLM — no new schema layer introduced. |
| FR-001, FR-002, FR-004 (system-prompt ordering rule, no-memory-fill) | **5 — Context Assembly** | Claude Code sourcemap (context assembly) | Anthropic docs (prompt caching stability) | Append ordering-rule block at the end of the system prompt so existing cache prefix is preserved; rule is phrased as a protocol, not a hint. |
| FR-010 (default sampling/generation parameters) | Provider-side | HF EXAONE README (official recommendations) | — | `temperature=1.0`, `top_p=0.95`, `presence_penalty=0.0`, `max_tokens=1024`, `enable_thinking=False`; all overridable by explicit caller argument. |
| FR-014 (discussion retraction) | Governance | Constitution Principle I (public record) | — | Comment on the referenced public discussion thread citing the empirical counter-example and linking to Epic #404. |

**Gate result (pre-Phase 0)**: PASS — no principle violation; reference mapping complete.

## Project Structure

### Documentation (this feature)

```text
specs/019-phase1-hardening/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   ├── llm-client.md    # LLMClient public contract (signatures, retry policy, semaphore semantics)
│   └── koroad-tool-schema.md  # KoroadAccidentSearchInput field description contract
├── checklists/
│   └── requirements.md  # Completed spec quality checklist
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created by /speckit-plan)
```

### Source Code (repository root)

Single Python project; no new top-level directories.

```text
src/kosmos/
├── llm/
│   └── client.py                       # FR-001..FR-003, FR-005..FR-010 — retry, semaphore, HF default params
├── tools/
│   └── koroad/
│       └── koroad_accident_search.py   # FR-003 — Pydantic Field(description=...) hardening (si_do/gu_gun)
├── context/
│   └── builder.py                      # FR-001, FR-004 — system-prompt ordering-rule append
└── session/                            # (existing) — session bootstrap may be touched for FR-004

tests/
├── llm/
│   └── test_client.py                  # FR-007 — Retry-After parse, backoff timing, semaphore serialization, default-param payload
├── tools/
│   └── koroad/
│       └── test_koroad_accident_search.py  # Pydantic schema description assertion (green on restatement only)
└── live/
    └── test_live_e2e.py                # FR-006, FR-011, FR-012 — drop asyncio.sleep(60); assert first KOROAD call admin codes
```

**Structure Decision**: Reuse the existing single-project layout rooted at `src/kosmos/`. No package relocations, no new sub-packages. Spec changes are in-place edits to three source files plus targeted test additions in `tests/llm/` and `tests/live/test_live_e2e.py`. Task parallelization (Agent Teams) will fan out across the three source files (`llm/client.py`, `tools/koroad/koroad_accident_search.py`, `context/builder.py`) because they have no cross-file import dependency for the changes required here.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified.**

No violations. Table intentionally empty.
