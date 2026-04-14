---

description: "Task list for Phase 1 Hardening — LLM rate-limit resilience & KOROAD tool input discipline"
---

# Tasks: Phase 1 Hardening — LLM Rate-Limit Resilience & KOROAD Tool Input Discipline

**Input**: Design documents from `/specs/019-phase1-hardening/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Test tasks are INCLUDED because the spec has explicit FR-007 (unit test additions) and FR-011/FR-012 (live test changes), and SC-001..SC-005 are test-outcome metrics.

**Organization**: Grouped by user story (US1, US2, US3) so each story is independently testable and deliverable. User Stories 1 and 2 share source-file touchpoints but address distinct user value and can be validated independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]** — parallelizable (different files, no blocking dependency on an incomplete task)
- **[Story]** — one of US1 / US2 / US3 (omitted for Setup, Foundational, and Polish phases)

## Path Conventions

Single project at repository root: `src/kosmos/`, `tests/`. All paths below are absolute-from-repo-root.

---

## Phase 1: Setup (Shared Infrastructure)

No new dependencies or scaffolding required — this feature edits existing files in place. Setup phase is intentionally empty; proceed directly to Foundational.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Reusable primitives that every downstream user-story task consumes. US1 and US2 both depend on the retry-policy dataclass (T001) and live-suite rate-limit observation logging (T002); US3 is a governance task independent of code changes.

- [X] T001 [P] Add a `RetryPolicy` dataclass (fields: `max_attempts`, `base_seconds`, `cap_seconds`, `jitter_ratio`, `respect_retry_after`) with the defaults from `data-model.md § Entity 2`, co-located in `src/kosmos/llm/client.py`. No behavior change yet — export only.
- [X] T002 [P] Add a structured logging line (`logging.getLogger("kosmos.llm")`) in `src/kosmos/llm/client.py` that records category=`rate_limit`, attempt index, chosen delay, and whether `Retry-After` was honored. Used later by US2 tests to assert retry behavior. No behavior change to call sites yet.

**Checkpoint**: Foundational primitives exist. US1 and US2 may now start in parallel.

---

## Phase 3: User Story 1 — Correct district returned for a district-named natural-language query (Priority: P1) 🎯 MVP

**Goal**: Ensure the assistant consults geocoding first and fills KOROAD admin codes from that call, never from model memory.

**Independent Test**: `uv run pytest -m live -v -k test_live_scenario1_from_natural_address` passes with the first `koroad_accident_search` tool invocation carrying Seoul / Gangnam admin codes (SC-002). Contract-level assertion on the JSON schema exposed to the LLM passes (`tests/tools/koroad/test_koroad_accident_search.py`).

### Tests for User Story 1

- [X] T003 [P] [US1] Write unit test in `tests/tools/koroad/test_koroad_accident_search.py` asserting that `KoroadAccidentSearchInput.model_json_schema()` contains the phrases "address_to_region" and "never" (case-insensitive) in the descriptions of both `si_do` and `gu_gun`, and references `SidoCode` / `GugunCode` by name. Ensure test FAILS before T005 runs.
- [X] T004 [P] [US1] Extend `tests/live/test_live_e2e.py::test_live_scenario1_from_natural_address` so the first recorded `koroad_accident_search` tool-use event has `si_do = SidoCode.SEOUL` and `gu_gun = GugunCode.SEOUL_GANGNAM`, and the final Korean answer references "강남" (not any other Seoul district). Keep the existing geocoding-ordering check.

### Implementation for User Story 1

- [X] T005 [US1] In `src/kosmos/tools/koroad/koroad_accident_search.py`, strengthen the Pydantic v2 `Field(description=...)` on `KoroadAccidentSearchInput.si_do` and `KoroadAccidentSearchInput.gu_gun` per `contracts/koroad-tool-schema.md` (must-derive-from-`address_to_region`, never-from-memory with Gangnam counter-example reference, pointer to `SidoCode`/`GugunCode` enumeration). English source text only. T003 must now pass.
- [X] T006 [US1] In `src/kosmos/context/builder.py` (or the session bootstrap it feeds), append the Session Guidance block at the **end** of the system prompt per `data-model.md § Entity 5`: geocoding-first rule + no-memory-fill rule. Preserve the existing prompt-cache prefix — no mutation of text before the append point.
- [X] T007 [US1] Add a focused unit test covering T006 in `tests/context/` that asserts the system prompt emitted by `builder` contains both rule sentences and that the pre-existing prefix text is byte-identical to the prior output (cache-stability assertion). No new golden file — compute before/after strings in-test.

**Checkpoint**: US1 independently demonstrates that KOROAD admin codes are sourced from geocoding and that LLM-facing schema + system prompt explicitly forbid memory-fill.

---

## Phase 4: User Story 2 — Live validation suite completes without rate-limit failures (Priority: P1)

**Goal**: Replace the blind 60-second cooldown with Retry-After-aware exponential backoff plus a session-scope concurrency gate, covering both pre-stream and mid-stream 429 surfaces, and align default sampling/generation parameters with the published recommendations for the Korean LLM.

**Independent Test**: `uv run pytest -m live -v` reports 30 passed / 0 xfailed / 0 failed (SC-001), zero rate-limit-caused failures (SC-003), and `test_live_e2e_multi_turn_context` wall-clock ≤ the 60-second-cooldown baseline (SC-004). `tests/llm/` unit suite green with new payload-default assertions (SC-005).

### Tests for User Story 2

- [X] T008 [P] [US2] In `tests/llm/test_client.py`, add a test: mock 429 response with `Retry-After: 3` → assert `LLMClient.complete()` waited ≥ ~3s (allow ±200ms tolerance) before retry and succeeded on the second attempt.
- [X] T009 [P] [US2] In `tests/llm/test_client.py`, add a test: two consecutive 429s with **no** `Retry-After` → assert observed sleep delays are monotonically non-decreasing, bounded by `cap_seconds`, and fall within `[delay*(1-jitter), delay*(1+jitter)]`.
- [X] T010 [P] [US2] In `tests/llm/test_client.py`, add a test: `max_attempts` consecutive 429s → `LLMClient.complete()` raises `LLMResponseError` with a rate-limit category tag (no empty/partial response returned).
- [X] T011 [P] [US2] In `tests/llm/test_client.py`, add a test: mid-stream 429 chunk arriving after streaming started → `LLMClient.stream()` aborts the current iterator, discards partial text, re-enters retry, and ultimately either yields a complete response or raises categorized `LLMResponseError`.
- [X] T012 [P] [US2] In `tests/llm/test_client.py`, add a test: two `LLMClient.stream()` coroutines started on the same `LLMClient` instance serialize at the provider-call boundary (verify via an `asyncio.Event` sentinel placed in the mock transport that records entry times).
- [X] T013 [P] [US2] In `tests/llm/test_client.py`, add a test asserting that the outgoing provider payload for both `complete()` and `stream()` contains `temperature=1.0`, `top_p=0.95`, `presence_penalty=0.0`, `max_tokens=1024`, `enable_thinking=False` by default, and that explicit caller overrides replace those values in the payload (FR-010).

### Implementation for User Story 2

- [X] T014 [US2] In `src/kosmos/llm/client.py`, add `self._semaphore = asyncio.Semaphore(1)` in `__init__`. Wrap the provider-call core of `complete()` and `stream()` with `async with self._semaphore:` (release on both success and failure). T012 must now pass.
- [X] T015 [US2] In `src/kosmos/llm/client.py`, implement the Retry-After-first backoff loop around the provider call per `contracts/llm-client.md § Behavioral contract` items (2) and (4): parse `Retry-After` header; otherwise sleep `min(cap, base * 2**attempt) * uniform(1-jitter, 1+jitter)`; at most `max_attempts` attempts; on exhaustion raise `LLMResponseError` with rate-limit category. Consume the `RetryPolicy` dataclass from T001. T008–T010 must now pass.
- [X] T016 [US2] In `src/kosmos/llm/client.py`, extend `stream()` so chunks carrying a rate-limit error envelope abort the iterator, discard any partial text accumulator, and route the retry attempt through the same policy as pre-stream 429. T011 must now pass.
- [X] T017 [US2] In `src/kosmos/llm/client.py`, change the default values of `temperature` (→ 1.0), `top_p` (→ 0.95), add new parameters `presence_penalty` (default 0.0), `max_tokens` (default 1024), `enable_thinking` (default False) on both `complete()` and `stream()`. Thread all five into the outgoing payload. Keep every parameter overridable by explicit caller argument. T013 must now pass.
- [X] T018 [US2] In `tests/live/test_live_e2e.py::test_live_e2e_multi_turn_context`, remove the `asyncio.sleep(60)` cooldown between turn 1 and turn 2. No new assertions — success comes from T014+T015+T016 absorbing the burst. Confirms FR-012 + SC-004.

**Checkpoint**: US2 independently demonstrates that retry + semaphore eliminate 429-caused failures and the blind cooldown, while the Korean LLM runs with published recommended parameters by default.

---

## Phase 5: User Story 3 — Public record corrected (Priority: P2)

**Goal**: Retract the earlier public-discussion claim that K-EXAONE reliably memorizes Korean district administrative codes and cite the empirical counter-example.

**Independent Test**: Open the referenced public discussion thread; verify a dated retraction comment exists, cites the counter-example, and links to Epic #404.

### Implementation for User Story 3

- [X] T019 [US3] Post a retraction comment on the public discussion thread referenced by Epic #404. The comment MUST (a) cite the empirical counter-example ("강남역" → wrong gu_gun), (b) link to Epic #404 and this spec path `specs/019-phase1-hardening/`, and (c) name the adopted mitigation trio (Pydantic `Field(description=...)` hardening, system-prompt ordering rule, Retry-After-aware retry + per-session semaphore). English source text per repo convention. Confirms FR-014 + SC-006.

**Checkpoint**: US3 independently closes the governance loop on the prior public claim.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T020 [P] Update `CLAUDE.md` "Active Technologies" / "Recent Changes" entries to reflect that `019-phase1-hardening` landed (agent-context script already wrote the baseline; verify it reads correctly and add the one-line summary if missing).
- [X] T021 Run `uv run pytest tests/llm/ tests/tools/ tests/context/ -v` and confirm 100% green — SC-005 gate.
- [ ] T022 Run `uv run pytest -m live -v` three times on the maintainer's local machine and confirm 30 passed / 0 xfailed / 0 failed each run — SC-001 + SC-002 stability gate.
- [ ] T023 Execute the steps in `specs/019-phase1-hardening/quickstart.md` end-to-end, and record the observed multi-turn wall-clock time against the 60-second-cooldown baseline — SC-004 gate.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: empty — no dependencies.
- **Phase 2 (Foundational)**: depends on Setup (trivially). BLOCKS US1 and US2.
- **Phase 3 (US1)**: depends on T001/T002.
- **Phase 4 (US2)**: depends on T001/T002.
- **Phase 5 (US3)**: depends on nothing in-code; can run in parallel once Epic #404 is opened.
- **Phase 6 (Polish)**: depends on Phases 3, 4, 5 complete.

### Within each user story

- Tests are written **first** and MUST fail before implementation lands (T003 before T005; T004 before live runs; T008–T013 before T014–T017).
- Within US1, T005 and T006 touch different files and can run in parallel after T003 / T004 are authored; T007 depends on T006.
- Within US2, T014 (semaphore) is independent of T015 (retry loop) and T017 (param defaults) in terms of file sections but all three modify the same file; serialize at commit time. T016 depends on T015 landing first to reuse the retry loop.

### Parallel Opportunities

- **[P] across Foundational**: T001 ∥ T002.
- **[P] across US1 tests**: T003 ∥ T004.
- **[P] across US2 tests**: T008 ∥ T009 ∥ T010 ∥ T011 ∥ T012 ∥ T013.
- **[P] across user stories** once Foundational is done: US1 (one Teammate), US2 (second Teammate), US3 (Lead or third Teammate) can proceed concurrently — US1 and US2 touch disjoint files for their test authoring and do not block each other, and US3 is out-of-code.

---

## Parallel Example: Agent Teams dispatch at `/speckit-implement`

```text
# After Phase 2 Foundational is green, dispatch in parallel:
Team A (Sonnet, Backend Architect):  US1 — T003, T004 → T005, T006, T007
Team B (Sonnet, Backend Architect):  US2 — T008..T013 → T014, T015, T016, T017, T018
Team C (Sonnet, Technical Writer):   US3 — T019
Lead (Opus):                         Foundational T001/T002, Polish T020..T023, code review of Teams A/B
```

---

## Implementation Strategy

### MVP first

1. Phase 2 Foundational (T001, T002) — unlocks US1 and US2.
2. Phase 3 US1 (T003..T007) — restores trust contract for the "강남역" scenario; the single most user-visible defect.
3. **STOP and validate**: run the US1-only live assertion. If green, Phase 1 MVP is one defect short of release.

### Incremental delivery

4. Phase 4 US2 (T008..T018) — removes rate-limit flakiness and the blind cooldown.
5. Phase 5 US3 (T019) — closes the public record.
6. Phase 6 Polish (T020..T023) — SC gates.

### Parallel team strategy

Per the Agent Teams block above — three Teammates plus Lead review, with the constraint that all three source-file edits land before Phase 6 runs the live suite three times.

---

## Notes

- [P] = different files, no dependency. Same-file edits are serialized even when they modify different sections (ours: `src/kosmos/llm/client.py` for US2).
- Every user story is independently testable — US1 via the strengthened scenario-1 live test, US2 via the `tests/llm/` unit suite and the multi-turn live scenario, US3 via opening the public discussion.
- Commit after each task or logical group; use Conventional Commits (`feat(llm):`, `fix(tools/koroad):`, `test(live):`, `docs:`).
- Tests MUST fail before implementation lands, per repo convention.
- No new dependencies. No Rust / Go. TypeScript not touched (TUI is Phase 2).
- Verify live-suite live quota before T022 (three full runs on Tier 1 100 RPM).
