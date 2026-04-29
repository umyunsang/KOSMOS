# Phase 0 Research — Epic ζ #2297

**Date**: 2026-04-30
**Author**: Lead Opus (this session)
**Branch**: `2297-zeta-e2e-smoke`
**Status**: Complete

## Constitutional reference mapping

Per Constitution § I (Reference-Driven Development) every design decision below is mapped to a primary reference and, where applicable, a secondary reference.

| Decision | Primary reference | Secondary reference |
|---|---|---|
| Backend `_VerifyInputForLLM` pre-validator (FR-008a) | Pydantic v2 official docs § "Validators / mode='before'" | Spec 025 V6 `@model_validator` pattern (auth_type↔auth_level invariant) — same library convention applied to a different invariant |
| Canonical map sourced from markdown at boot (FR-008b) | Spec 026 PromptLoader (`prompts/manifest.yaml` SHA-256 fail-closed) — already-loaded markdown is the single source-of-truth | CC `restored-src/services/api/`-style read-once-at-boot pattern (no per-request markdown parsing) |
| TUI `dispatchPrimitive.ts` shared helper (FR-005) | CC `restored-src/services/tools/toolExecution.ts:1207` (Tool.call invocation site, byte-identical signature preserved) | AutoGen AgentRuntime mailbox pattern (Spec 027 — Future-keyed-by-call-id registry) |
| TUI `_pendingCallRegistry.ts` (FR-001-FR-004 backing) | Backend `_pending_calls: dict[str, asyncio.Future]` in `src/kosmos/ipc/stdio.py:1462` (the canonical pattern that this is mirroring on the TS side) | Spec 027 mailbox `replay_unread` state |
| Layer 4 vhs PNG keyframes (FR-012) | AGENTS.md § TUI verification methodology Layer 4 (canonical, 2026-04-29 promotion) | charm-vhs ≥ 0.11 native `Screenshot` directive (no ffmpeg post-extraction) |
| Layer 2 PTY scenario (FR-011) | AGENTS.md § TUI verification methodology Layer 2 (`expect` / `asciinema` / `script`) | feedback memory `feedback_pr_pre_merge_interactive_test` |
| 10-fixture verify-family battery (FR-019) | Spec ε #2296 5-family ε mocks + 5 inherited families = 10-row canonical map | η `prompts/system_v1.md` `<verify_families>` block (single source-of-truth) |
| `policy-mapping.md` international gateway citations (FR-017) | AGENTS.md § CORE THESIS (Singapore APEX / Estonia X-Road / EU EUDI / Japan マイナポータル named explicitly) | Each foreign spec's own canonical URL |
| 5 OPAQUE scenario docs (FR-018) | AGENTS.md § L1-B B3 ("OPAQUE domains are never wrapped — LLM hands off via `docs/scenarios/`") | `docs/requirements/kosmos-migration-tree.md` § L1-B B3 |

## Root-cause analysis (Phase 0 critical finding)

The η-Lead's "TUI Tool.call() stub blocker" hypothesis (η spec § Mid-Epic findings #2) was **incomplete**. Code reading on 2026-04-30 by this Phase 0 research established the actual citizen-blocker:

### Evidence chain

1. **`prompts/system_v1.md` v2 `<verify_chain_pattern>` worked example** teaches the LLM to call:
   ```text
   verify(tool_id="mock_verify_module_modid",
          params={"scope_list": ["lookup:hometax.simplified", "submit:hometax.tax-return"],
                  "purpose_ko": "종합소득세 신고",
                  "purpose_en": "Comprehensive income tax filing"})
   ```

2. **`src/kosmos/tools/mvp_surface.py:243` `_VerifyInputForLLM`** declares:
   ```python
   class _VerifyInputForLLM(BaseModel):
       family_hint: str = Field(...)
       session_context: dict[str, object] = Field(default_factory=dict, ...)
   ```
   The OpenAI-compat schema published to K-EXAONE shows `family_hint` + `session_context` as the canonical fields.

3. **`src/kosmos/ipc/stdio.py:993` `_dispatch_primitive`** for the `verify` arm reads:
   ```python
   family_hint = str(args_obj.get("family_hint") or args_obj.get("family") or "")
   session_ctx = cast("dict[str, object]", args_obj.get("session_context") or {})
   raw = await verify(family_hint=family_hint, session_context=session_ctx)
   ```
   When LLM emits `verify(tool_id=..., params=...)`, both `family_hint` and `family` are missing → `family_hint=""` → `kosmos.primitives.verify()` rejects empty family.

4. **`specs/2298-system-prompt-rewrite/smoke-citizen-taxreturn-pty.txt` tail** (η T011 attempt 3) shows the LLM emitting **0 tool_calls** and producing a conversational fallback: "현재 공공서비스 시스템에는 종합소득세 신고 기능이 제공되지 않고 있습니다." This is consistent with the LLM seeing a contradictory instruction (prompt teaches `tool_id`, schema requires `family_hint`) and falling back to "I cannot do this" rather than emitting a malformed call.

5. **TUI `tool.call()` stubs** (η Lead's diagnosis target) — code reading at `tui/src/services/tools/toolExecution.ts:1207` confirms `tool.call()` IS invoked locally for every LLM tool_use, but the backend `_handle_chat_request` ALSO self-dispatches via `_dispatch_primitive` (`stdio.py:1496`) as a background task. Both resolve the same `_pending_calls[call_id]` Future; backend wins the race for in-memory mocks. So the TUI stub is a **secondary correctness gap**, not the citizen-blocker.

### Conclusion

The citizen-blocker is the **schema↔prompt contradiction** in the verify primitive's input shape. The fix is at the backend boundary — extend `_VerifyInputForLLM` with a `@model_validator(mode="before")` that accepts both shapes and translates `tool_id`/`params` → `family_hint`/`session_context`. Per FR-022 (`prompts/**` immutable), this Epic cannot revert the prompt to the legacy shape — and even if FR-022 allowed it, the η-shipped `tool_id`-based shape is the right user-facing API (it matches the `lookup`/`submit`/`subscribe` envelope convention).

The TUI Tool.call() stubs are still replaced (FR-001–FR-007) for correctness — they are wrong as a code-quality matter even if the citizen race usually goes the right way. The two fixes are independent and ship together.

## Architecture decisions

### Decision 1 — Backend pre-validator translates `tool_id` → `family_hint`

**Choice**: Add `@model_validator(mode="before")` to `_VerifyInputForLLM` in `src/kosmos/tools/mvp_surface.py`.

**Rationale**:
- Pre-validator runs before field validation, so it can rebuild the dict shape.
- Pydantic v2 validators are first-class — Constitution § III mandates Pydantic v2 strict typing, and the validator returns a strict dict that the schema then validates normally.
- The LLM-published OpenAI schema (via `mvp_surface.VERIFY_TOOL.input_schema.model_json_schema()`) will list `tool_id` as the canonical field (citizen-facing convention) once the schema is updated; legacy `family_hint` callers continue to work for backward compatibility.
- Single layer of change — no TUI translation, no LLM prompt change, no dispatcher signature change. The `_dispatch_primitive` continues to read `family_hint` and works unchanged.

**Alternatives considered**:
- *Option A — TUI-side translation in `VerifyPrimitive.call()`* — rejected. The TUI stub is in a race with backend `_dispatch_primitive`; backend wins. TUI translation does not reach the dispatcher in time. Even if it did, two layers performing translation is brittle.
- *Option C — change `prompts/system_v1.md` to teach `family_hint` instead of `tool_id`* — rejected. FR-022 forbids touching `prompts/`. Even without FR-022, the η-shipped `tool_id` convention is preferred — it matches `lookup(tool_id, params)` and `submit(tool_id, params)`.
- *Option D — extend `kosmos.primitives.verify.dispatch()` to accept `tool_id`* — rejected. Dispatcher signature change cascades to integration tests; the schema layer is the right boundary.

### Decision 2 — Canonical map read from `prompts/system_v1.md` at boot

**Choice**: New module `src/kosmos/tools/verify_canonical_map.py` parses the `<verify_families>` markdown table on first import (lazy module-level `lru_cache`d call). Returns a frozen `dict[str, str]` mapping `tool_id → family_hint`.

**Rationale**:
- Single source-of-truth = the markdown. No drift possible by construction.
- Boot-time parse is O(20 lines); negligible startup cost.
- FR-008b regression test parses the same markdown and asserts ≥10 entries + presence of the 10 canonical families.
- `prompts/system_v1.md` is loaded by Spec 026 `PromptLoader` at boot anyway (already in memory), but for module-level isolation we re-read just the `<verify_families>` slice. This avoids coupling `mvp_surface` to `PromptLoader` startup ordering.

**Alternatives considered**:
- *Hardcode the 10 entries in Python* — rejected. Drift risk between code and markdown over time.
- *Generate the map at PromptLoader load and inject* — over-engineered for a 10-row constant. Rejected for simplicity.

### Decision 3 — TUI shared `dispatchPrimitive.ts` helper

**Choice**: New `tui/src/tools/_shared/dispatchPrimitive.ts` exports a single `dispatchPrimitive<I, O>(name, input, context)` async function. It (a) generates a fresh `call_id` (UUIDv7), (b) registers a TUI-side pending call in a session-scoped `pendingCallRegistry`, (c) emits an IPC `tool_call` frame via the existing bridge, (d) awaits the matching `tool_result` frame (with FR-006 timeout), (e) returns the resolved envelope as `ToolResult<O>`. The 4 primitive `.ts` files import this helper and call it from inside their `call()` body.

**Rationale**:
- Single conversion point — easier to maintain and test than 4 parallel implementations.
- Mirrors backend `_pending_calls` pattern (line-for-line analog), so conceptual symmetry is preserved.
- Timeout knob (FR-006) lives in one place.
- Unit-testable in isolation via `bun test`.

**Alternatives considered**:
- *Inline dispatch in each primitive's `call()` body* — rejected. Duplication × 4 with no compensating benefit.
- *Use the existing `tx-registry.ts` for pending-call tracking* — rejected. `tx-registry.ts` is for idempotency-on-resubmit (Spec 032 WS3 T044), not for awaiting tool_result. Different concern.

### Decision 4 — TUI `llmClient.ts` adds `tool_result` frame route

**Choice**: Extend the frame consumer loop in `tui/src/ipc/llmClient.ts:405` (the existing `tool_call` arm) with a parallel `tool_result` arm that resolves the matching pending call via `pendingCallRegistry.resolve(call_id, frame)`. The frame is otherwise consumed silently (no SDK event yielded).

**Rationale**:
- llmClient is the single consumer of `bridge.frames()` for the chat_request stream — all inbound frames flow through there.
- The `tool_result` frame's `correlation_id` matches the chat_request's, so the same stream is the right place to route it.
- No fork of the frame stream needed (a fork would race against the SDK's `message_stop` and complicate teardown).

**Alternatives considered**:
- *Fork the frame stream in the bridge layer* — rejected. Adds a second consumer that competes with llmClient for the async iterable; complicates lifecycle.
- *Route via `bridge.onFrame` telemetry hook* — rejected. `onFrame` is fire-and-forget telemetry; it cannot resolve a Future synchronously and would race with llmClient's own frame consumption.

### Decision 5 — TUI dispatcher does NOT translate `tool_id` for verify

**Choice**: TUI `VerifyPrimitive.call()` forwards the LLM-emitted shape unchanged. The IPC `tool_call` frame's `arguments` field carries `{tool_id, params}` verbatim. The backend's `_VerifyInputForLLM` pre-validator (Decision 1) owns the translation.

**Rationale**:
- Single layer of translation (FR-008 requirement). Dual translation would create a maintenance trap.
- The backend dispatcher is authoritative; the TUI is a thin renderer + dispatcher.
- FR-009 codifies this — symmetric tests assert the IPC `tool_call` frame preserves field names verbatim.

**Alternatives considered**:
- *TUI-side translation* — rejected. See Decision 1 alternatives.

### Decision 6 — Receipt determinism under CI

**Choice**: The mock submit adapter `mock_submit_module_hometax_taxreturn` checks `os.environ.get("CI") == "true"` and uses a deterministic seed for the 5-character random suffix when set. Production behavior (random suffix) is preserved when `CI` is unset.

**Rationale**:
- FR-021 mandates non-flaky CI; deterministic seed is the simplest way.
- The mock adapter is the right place — backend dispatcher / smoke harness should not introduce environment-dependent branches.
- Test fixtures can assert exact receipt values when `CI=true`.

**Alternatives considered**:
- *Smoke harness regex-matches the pattern* — already done (FR-015). But determinism in addition to regex match makes diff-based regression detection trivial.

### Decision 7 — Phase 0 + Phase 1 dispatch tree

Per AGENTS.md § Agent Teams Layer 2 (Sonnet teammates), the work splits into 4 dispatch units:

```text
Phase 0a · Backend schema + canonical map + tests          [sonnet-backend]   ≤4 files
Phase 0b · TUI shared dispatcher + 4 primitive call() body [sonnet-tui]       ≤8 files
Phase 1a · Smoke harness + integration tests + fixtures    [sonnet-smoke]     ≤14 files (battery)
Phase 1b · policy-mapping.md + 5 OPAQUE scenario docs      [Lead solo]        6 files (citation accuracy)
```

Phase 0a + Phase 0b run in parallel (no shared files). Phase 1a depends on both Phase 0 teammates. Phase 1b is parallel-safe with Phase 1a.

**Rationale**: matches Constitution § VI accountability (each task has a tracking entry) and AGENTS.md ≤5 task / ≤10 file dispatch unit. Lead reserves citation-accuracy work (Phase 1b) for solo execution.

## Deferred items validation summary

Per `/speckit-plan` Outline § 2 (Constitution Principle VI gate), the spec.md "Deferred to Future Work" table has 7 items:

| Item | Status |
|---|---|
| Multi-turn delegation reuse | NEEDS TRACKING — to be resolved by `/speckit-taskstoissues` |
| Real Live submit adapters | NEEDS TRACKING — to be resolved by `/speckit-taskstoissues` |
| Subscribe primitive E2E demo with real CBS source | NEEDS TRACKING — to be resolved by `/speckit-taskstoissues` |
| OTEL span coverage for TUI dispatcher | NEEDS TRACKING — to be resolved by `/speckit-taskstoissues` |
| `policy-mapping.md` translation to additional languages | NEEDS TRACKING — to be resolved by `/speckit-taskstoissues` |
| Property-based testing of family-map drift detector | Out of scope (no tracking needed) |
| Promote any of η's 5 deferred sub-issues (#2475-#2479) | Tracked at #2475-#2479 (already exist) |

Free-text scan for unregistered deferral patterns: spec.md searched for "separate epic" / "future epic" / "Phase [2+]" / "v2" / "deferred to" / "later release" / "out of scope for v1" — all matches are inside the table or marked "(none)" in the explicit Out-of-Scope section. **No constitution violations.**

## Boot-order checklist

1. ✅ `prompts/system_v1.md` v2 manifest hash `bda67fb…` already on `main` (η commit `1321f77`).
2. ✅ `src/kosmos/tools/mvp_surface.py` already registers 5 core tools (η commit `1321f77`).
3. ✅ Backend `_dispatch_primitive` already routes verify/lookup/submit/subscribe (Spec 1978).
4. ✅ TUI `bridge.ts` + `llmClient.ts` already handle `tool_call` frames (Spec 1978).
5. ✅ TUI `frames.generated.ts` already declares `ToolResultFrame` schema (line 1253).
6. ✅ TUI `services/tools/toolExecution.ts` already invokes `tool.call()` locally (line 1207).
7. ⏳ Need: `_VerifyInputForLLM` pre-validator + canonical map module — **Phase 0a**.
8. ⏳ Need: TUI shared `dispatchPrimitive.ts` + 4 primitive call() bodies + llmClient `tool_result` arm — **Phase 0b**.
9. ⏳ Need: smoke harness + integration tests + 10-fixture battery — **Phase 1a**.
10. ⏳ Need: 6 narrative docs — **Phase 1b**.

## Open risks

1. **K-EXAONE may emit a malformed function_call when the schema changes** — Decision 1's pre-validator accepts BOTH shapes (`{tool_id, params}` AND `{family_hint, session_context}`), so legacy callers are uninfluenced. The smoke captures the actual emit format and the integration test asserts.
2. **Backend self-dispatch race** — the backend's `_dispatch_primitive` and TUI's `tool.call()` both resolve `_pending_calls[call_id]`. Whichever wins the race resolves first; the other's resolution is a no-op (`fut.done()` check at `stdio.py:1639`). If TUI wins for an unusually slow backend dispatch, the LLM continues with the TUI-side result. For mocks this is functionally identical (both call the same primitive). For real adapters this could matter — out of scope for this Epic (mocks only) but tracked for a follow-up.
3. **vhs PNG keyframe rendering on macOS** — charm-vhs ≥ 0.11 has known macOS quirks. Mitigation: capture on Linux CI (existing) and compare against macOS local reference.
4. **`prompts/system_v1.md` parsing fragility** — the `<verify_families>` table parser is regex-based; format changes would break the canonical map. Mitigation: regression test (FR-008b) that asserts ≥10 entries + named families. Out-of-scope hardening (e.g., a markdown AST parser) tracked as future work.

## Phase 0 done — gate transitions to Phase 1

Constitution check passes. Architecture decisions are committed. Phase 1 deliverables (data-model.md, contracts/, quickstart.md, agent context update) are next.
