# Data Model — Phase 1 Hardening

**Feature**: 019-phase1-hardening
**Date**: 2026-04-14

This feature introduces no persistent entities. The entities below are behavioral/runtime — they describe invariants and relationships for runtime objects and prompt blocks so that contracts and tasks can be derived cleanly.

## Entity 1 — Administrative region code pair

A `(sido, gugun)` pair used as input to an authoritative-data tool (KOROAD accident search).

| Field | Type | Source of truth | Rule |
|---|---|---|---|
| `si_do` | `SidoCode` (enum) | Prior `address_to_region` call | MUST be the value from the geocoding result; MUST NOT be filled from LLM memory. |
| `gu_gun` | `GugunCode` (enum) | Prior `address_to_region` call | Same rule. Must belong to the enumerated valid set for the paired `si_do`. |

**Invariants**:
- Provenance: every value in this pair traces to a tool-use event within the same session where a geocoding tool was invoked before the authoritative-data tool.
- Enumeration: values outside the enumerated `SidoCode` / `GugunCode` sets are rejected by Pydantic v2 validation as before (no new runtime validation added this epic — Out of Scope).

## Entity 2 — Rate-limit retry policy

A per-call policy object governing reaction to provider rate-limit errors.

| Field | Type | Default | Rule |
|---|---|---|---|
| `max_attempts` | `int` | `5` | Hard cap including the initial attempt. |
| `base_seconds` | `float` | `1.0` | Exponential backoff base when Retry-After is absent. |
| `cap_seconds` | `float` | `60.0` | Per-attempt maximum sleep. |
| `jitter_ratio` | `float` | `0.2` | ±20% multiplicative jitter. |
| `respect_retry_after` | `bool` | `True` | When `True`, Retry-After overrides the computed backoff for that attempt. |

**State transitions**:
- `attempting(i)` → `sleeping(delay)` on 429 received.
- `sleeping(delay)` → `attempting(i+1)` when the timer elapses, provided `i+1 ≤ max_attempts`.
- `attempting(i)` → `succeeded` on any non-429 terminal response.
- `attempting(max_attempts)` or `streaming_429_after_max_attempts` → `terminal_failure` surfaced as `LLMResponseError` with a category tag.

## Entity 3 — Session-level concurrency gate

A per-`LLMClient` serialization primitive.

| Field | Type | Rule |
|---|---|---|
| `_semaphore` | `asyncio.Semaphore` | Initialized with value `1` in `LLMClient.__init__`. |

**Invariants**:
- Every call to `complete()` and `stream()` acquires `_semaphore` before contacting the provider.
- The semaphore is released on both success and failure paths (via `async with`).
- The gate does not coordinate across different `LLMClient` instances — scope is one session.

## Entity 4 — Tool-input guidance block

The machine-readable description text attached to a Pydantic v2 field via `Field(description=...)`, which is emitted verbatim as part of the JSON schema the LLM reads.

| Target field | Required guidance content |
|---|---|
| `KoroadAccidentSearchInput.si_do` | (a) states MUST-be-derived-from-`address_to_region`; (b) states NEVER-fill-from-memory with empirical counter-example reference; (c) points to `SidoCode` enumeration for valid codes. |
| `KoroadAccidentSearchInput.gu_gun` | Same triad, scoped to gugun-level codes, and references the empirical Gangnam counter-example. |

**Invariants**:
- The text is English-only (AGENTS.md hard rule) but the semantics cover Korean-language queries.
- No runtime behavior changes — the description is a documentation artifact surfaced through schema only.

## Entity 5 — Session guidance block

A block appended to the system prompt at context-assembly time, giving the LLM ordering rules for tool use.

| Slot | Required content |
|---|---|
| Geocoding-first rule | "When the citizen's message names a district, neighborhood, landmark, or address, invoke the geocoding tool before any tool that takes an administrative code." |
| No-memory-fill rule | "Do not fill administrative region codes from memory; pass them only after a geocoding tool has produced them in this session." |

**Invariants**:
- Appended at the **end** of the existing system prompt (prompt-cache prefix preserved).
- English source text. No Korean prose inside the rule (tool names and error messages in the rule may use the project's existing identifiers).
- No turn-specific interpolation — the block is static so the cache key remains stable.

## Cross-entity relationships

- Entity 4 (tool-input guidance) and Entity 5 (session guidance) both target the same invariant from different surfaces: the LLM must not fabricate admin codes.
- Entity 2 (retry policy) and Entity 3 (concurrency gate) together satisfy FR-005..FR-009 — retry handles recoverable 429s; the gate reduces 429 incidence.
- Entity 1 (code pair) is the value that flows through the tool call; Entities 4+5 are the guidance surfaces that constrain how it is populated.
