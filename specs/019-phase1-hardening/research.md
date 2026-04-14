# Phase 0 Research — Phase 1 Hardening

**Feature**: 019-phase1-hardening
**Date**: 2026-04-14
**Inputs**: [spec.md](./spec.md), [plan.md](./plan.md), `docs/vision.md § Reference materials`, `.specify/memory/constitution.md`

## Scope

Resolve any `NEEDS CLARIFICATION` markers in plan.md Technical Context (none — all fields concrete). Validate Deferred Items per Constitution Principle VI. Consolidate per-layer design decisions with Decision / Rationale / Alternatives. Map each decision to a concrete reference in `docs/vision.md § Reference materials` per Constitution Principle I.

## Deferred-items validation (Principle VI gate)

- `spec.md § Scope Boundaries & Deferred Items` present — ✅.
- "Out of Scope (Permanent)" lists seven items: LLM replacement, defense-in-depth admin-code validation inside the accident adapter, TUI work, other citizen scenarios, new geocoding/weather endpoints, higher LLM tier, live-suite in CI. All items are permanent exclusions; none require tracking issues.
- "Deferred to Future Work" explicitly states "No items deferred — all requirements are addressed in this epic." — ✅.
- Spec text scanned for unregistered deferral language (patterns: "separate epic", "future epic", "Phase 2+", "v2", "deferred to", "later release", "out of scope for v1"). Only matches are inside the Scope Boundaries section itself, and they refer to items already registered in "Out of Scope (Permanent)". No ghost-work risk.

**Gate result**: PASS.

## Decisions

### D1 — Retry policy: Retry-After-first, bounded exponential backoff with jitter (FR-005, FR-006, FR-008)

- **Decision**: On HTTP 429, parse the `Retry-After` header. If present and parsable as seconds, sleep for `max(header_value, min_backoff)` before retrying. If absent, sleep for `base * 2**attempt` jittered by ±20%, capped at 60s per attempt, with a hard budget of 5 attempts. On budget exhaustion, raise the existing `LLMResponseError` (categorized terminal failure surface).
- **Rationale**: Matches the Error Recovery matrix described in `docs/vision.md § Layer 6` ("429 Rate limited → exponential backoff (base 1s, cap 60s)") and the OpenAI Agents SDK retry-matrix pattern. Jitter prevents synchronized retry storms (stamina's enforced-jitter rationale). The Retry-After-first rule honors the provider's own guidance when supplied, minimizing wasted bucket capacity.
- **Primary reference**: OpenAI Agents SDK (`openai/openai-agents-python`) — retry matrix with composable policies.
- **Secondary reference**: stamina (`hynek/stamina`) — production-grade async retry with enforced jitter and capped backoff.
- **Alternatives considered**:
  - *aiobreaker circuit breaker*: useful for cross-session failure isolation but overkill for a single-session per-minute bucket; adds state that outlives a session. Rejected for this epic.
  - *LangGraph RetryPolicy per-node*: node-level retry assumes a graph runtime KOSMOS does not yet use at Layer 1. Rejected.
  - *Unbounded retry until success*: violates FR-008 (categorized terminal failure required).

### D2 — Streaming 429 detection parity (FR-007)

- **Decision**: 429 chunks that arrive after the HTTP response has started streaming are treated identically to a pre-stream 429. Detection point: the streaming iterator inspects each chunk; if the provider emits an error envelope indicating rate-limit, the iterator aborts, the partial text is discarded (not surfaced to the caller as a complete response), and the retry loop around `stream()` is invoked on the same terms as a pre-stream 429.
- **Rationale**: The Claude Agent SDK streaming-error pattern prescribes surfacing streaming failures as terminal-or-retriable at the iterator boundary rather than letting partial output escape. Spec Acceptance Scenario §2-U2 requires this symmetry. Avoids "half-answer looks complete" failure mode called out in Edge Cases.
- **Primary reference**: Claude Agent SDK (`anthropics/claude-agent-sdk-python`) — streaming error handling.
- **Alternatives considered**:
  - *Tolerate mid-stream 429 as end-of-stream*: silently returns a truncated answer. Rejected — violates FR-008 explicit-failure requirement and trust contract with citizen.

### D3 — Per-session concurrency gate (FR-009)

- **Decision**: `LLMClient.__init__` creates `self._semaphore = asyncio.Semaphore(1)`. Both `complete()` and `stream()` wrap their provider-call core inside `async with self._semaphore:`. Scope is one `LLMClient` instance — matches the session's lifetime in the current CLI. No cross-instance coordination.
- **Rationale**: The FriendliAI Tier-1 100 RPM/TPM bucket is per-account but observed pressure arises primarily from same-session concurrent turns (orchestrator + worker patterns in Layer 1). Per-session serialization is the smallest gate that removes the observed live-suite collision without requiring a cross-process token bucket. The Claude Agent SDK async generator loop and the Claude Code sourcemap tool-loop design both serialize LLM calls at the loop level — this decision matches that shape.
- **Primary reference**: Claude Agent SDK async generator loop.
- **Secondary reference**: Claude Code sourcemap (`ChinaSiro/claude-code-sourcemap`) — tool loop internals.
- **Alternatives considered**:
  - *Token bucket at process level*: more accurate but requires shared state that does not exist in the current CLI. Deferred permanently in this epic's Out-of-Scope (higher tier / broader concurrency control).
  - *No gate, rely on retry alone*: fails SC-001 when two turns race into the same 100-RPM minute.

### D4 — Tool-input guidance via Pydantic `Field(description=...)` (FR-003)

- **Decision**: Strengthen the `description` text on `KoroadAccidentSearchInput.si_do` and `KoroadAccidentSearchInput.gu_gun` to forbid memory-fill, require derivation from a prior `address_to_region` call, and reference the enumerated valid-code sets (`SidoCode`, `GugunCode`).
- **Rationale**: Pydantic v2 exposes `Field(description=...)` in the generated JSON schema, which is the structure handed to the LLM as the tool's parameter contract. Modifying the description strengthens LLM-visible guidance without altering runtime validation (the adapter's call to the upstream API remains the source of truth — the `Out of Scope (Permanent)` item bars us from adding defense-in-depth validation here). Pydantic AI's schema-driven registry demonstrates this pattern.
- **Primary reference**: Pydantic AI (`pydantic/pydantic-ai`) — schema-driven tool registry.
- **Secondary reference**: Claude Agent SDK — tool definitions.
- **Alternatives considered**:
  - *Custom validator that rejects "memorized-looking" codes*: heuristic, false-positive-prone, and contradicts the Out-of-Scope rule. Rejected.
  - *New schema field recording provenance*: out of scope and ripples through other adapters. Rejected.

### D5 — System-prompt ordering rule appended at context-assembly time (FR-001, FR-002, FR-004)

- **Decision**: Append a concise ordering-rule block at the **end** of the system prompt emitted by `src/kosmos/context/builder.py` (or the session bootstrap that owns it). The rule states: when the citizen's query names a location, invoke the geocoding tool first and then use its output to fill location-coded tool inputs; never fill administrative codes from memory.
- **Rationale**: Appending at the end preserves the existing prompt-cache prefix (Anthropic docs + "Don't Break the Cache" arXiv 2601.06007) — important because KOSMOS relies on prompt caching for cost. The Claude Code sourcemap context-assembly pattern separates stable system preamble from turn-specific additions; this decision matches that shape. The rule is phrased as a protocol ("always call geocoding before a location-coded authoritative tool"), not a hint, because LLM-visible guidance is more reliable when unambiguous.
- **Primary reference**: Claude Code sourcemap (`ChinaSiro/claude-code-sourcemap`) — context assembly.
- **Secondary reference**: Anthropic documentation — prompt caching; "Don't Break the Cache" (arXiv 2601.06007).
- **Alternatives considered**:
  - *Inject rule per turn at the top of the user message*: breaks prompt cache. Rejected.
  - *Only strengthen tool descriptions without changing the system prompt*: insufficient; the failure mode involves the LLM choosing which tool to call and in what order — an ordering rule belongs in the system prompt.

### D6 — Default sampling/generation parameters aligned to published recommendations (FR-010)

- **Decision**: Default `temperature=1.0`, `top_p=0.95`, `presence_penalty=0.0`, `max_tokens=1024`, `enable_thinking=False`. Every default remains overridable by explicit caller argument. Payload assembly threads the new fields through for both `complete()` and `stream()`.
- **Rationale**: The Korean LLM's published README recommends these settings for the latency-sensitive, non-reasoning interactive path that Phase 1 uses. Adopting them at the client default minimizes per-call overrides and gives every caller the recommended behavior unless they opt out.
- **Primary reference**: HF EXAONE README (official provider documentation).
- **Alternatives considered**:
  - *Leave defaults as-is and override in each call site*: drift risk; future callers will diverge. Rejected.
  - *Enable `enable_thinking=True` by default*: violates the non-reasoning / latency-sensitive path this phase targets. Rejected.

### D7 — Drop fixed 60s cooldown in the live multi-turn test (FR-012)

- **Decision**: Remove `asyncio.sleep(60)` between turns in the live multi-turn scenario. Rely on the semaphore (D3) + retry policy (D1) to absorb per-minute bucket pressure.
- **Rationale**: The fixed cooldown is a symptom of missing primitives; once D1 + D3 land, the cooldown becomes dead code that inflates wall-clock time (SC-004). Acceptance Scenario §4-U2 requires the suite to be faster-or-equal after the change.
- **Primary reference**: plan.md D1 + D3.
- **Alternatives considered**:
  - *Keep the cooldown as a belt-and-suspenders*: contradicts SC-004.

### D8 — Per-scenario live assertion on first KOROAD call admin codes (FR-011)

- **Decision**: The live E2E test for the "강남역" query asserts that the **first** `koroad_accident_search` invocation in the recorded tool-use events carries administrative codes corresponding to Seoul / Gangnam (per the project's enumerated tables). If not, the test fails.
- **Rationale**: The defect surfaced exactly at the "first authoritative-tool call" boundary — a citizen who gets the wrong district on the first call has already been misled. Asserting on first-call preserves the trust contract even if the LLM self-corrects on a subsequent turn.
- **Primary reference**: spec.md User Story 1 Acceptance Scenario 1.
- **Alternatives considered**:
  - *Assert only on final answer text*: weaker; the answer could be correct by accident while the tool call carried wrong codes. Rejected.

## Consolidated outcome

- All `NEEDS CLARIFICATION` markers in plan.md Technical Context are already resolved (none present).
- Every plan-level design decision has a reference source from `docs/vision.md § Reference materials`, satisfying Constitution Principle I.
- Deferred-items gate passes; no free-text deferrals outside the registered table.
- Constitution Principles II, III, IV, V checks from plan.md hold under these decisions — no new risks introduced.

**Phase 0 gate result**: PASS. Proceed to Phase 1.
