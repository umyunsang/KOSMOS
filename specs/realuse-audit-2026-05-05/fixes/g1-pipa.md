# G1 — PIPA §22 Legal Compliance Fix Summary

> Wave-2 Lead Opus G1 (`fix/2773-g1-pipa-fail-closed`). Closes 3 P0 findings in one pattern-aligned bundle: F-alpha-15 (non-interactive boot fabricates pipa-consent) + F-beta-04 (NMC L3 modal not pre-dispatch) + F-gamma-07 (LLM solicits PIPA-sensitive input via chat). Research artefact: [`research/g1-pipa.md`](../research/g1-pipa.md).

## P0 Closed

| Finding | Surface | Root cause | Fix file:lines |
|---|---|---|---|
| F-alpha-15 | UI-A onboarding | `KOSMOS_ONBOARDING_AUTO_COMPLETE=1` fabricated all 5 steps incl. `pipa-consent` (PIPA §22 affirmative-consent invariant violated). | `tui/src/components/onboarding/OnboardingFlow.tsx:127-202` |
| F-beta-04 | UI-C × L1-B | `_check_permission_gate` only consulted *primitive* name; `lookup` was always auto-allowed even when the inner adapter (NMC, HIRA L3, login-gated KMA) had `policy.citizen_facing_gate != "read-only"`. | `src/kosmos/ipc/stdio.py:1397-1462` (gate lookup-policy branch) + `:1467-1483` (lookup risk/locale dicts) |
| F-gamma-07 | prompt + L1-B | `prompts/system_v1.md` lacked any directive forbidding chat-channel collection of PIPA-sensitive credentials; `verify` primitive description had no modal-only language; LLM filled the gap by asking the citizen to type 주민등록번호 + raw `session_id` into chat. | `prompts/system_v1.md` (new `<pipa_safety>` block + `<primitives>` verify-line cross-ref) + `prompts/manifest.yaml` (SHA-256 update) |

## Root cause analysis (4-phase systematic-debugging)

### Phase 1 — Instrumentation
Located three independent emission sites for the *same* PIPA-§22 invariant violation:

1. `OnboardingFlow.tsx:127` `useEffect` autoCompleteHatch — wrote 5 `completed_at` timestamps, including `pipa-consent`, with a single env signal.
2. `stdio.py:_check_permission_gate` line 1397 — `if fname not in _PERMISSION_GATED_PRIMITIVES: return True` short-circuited every `lookup(...)` regardless of adapter policy.
3. `system_v1.md` line 112 — single PIPA mention ("개인정보는 PIPA에 따라 처리합니다") was too vague for K-EXAONE to translate into a concrete chat-channel prohibition.

### Phase 2 — Pattern (CC restored-src diff)
- CC's `onPermissionRequest(req, signal): Promise<response>` (`.references/.../mcpServer.ts:100`) blocks dispatch on async citizen decision. KOSMOS's `_check_permission_gate` is a byte-identical port — the gap is *which* dispatches enter the gate.
- KOSMOS's primitive enum `GATED_PRIMITIVES = {verify, submit, subscribe}` was a primitive-level approximation; the actual contract owner is the adapter's `policy.citizen_facing_gate` (per Spec δ #2295 Path B).

### Phase 3 — Hypothesis
Three minimal independent fixes (no bundling — each finding has its own surgical patch):

- **H1**: PIPA-bearing onboarding steps (`pipa-consent`, `ministry-scope`, `terminal-setup`) gated behind a second env `KOSMOS_PIPA_CONSENT=opt-in-explicit`. Without it, the auto-complete hatch advances to but stops at `pipa-consent`. Idempotency guard prevents re-render loop.
- **H2**: `_check_permission_gate` lookup branch consults `tool.policy.citizen_facing_gate`; non-`read-only` enters modal flow. Adapter resolution failure is *fail-closed*.
- **H3**: New `<pipa_safety>` system-prompt block enumerates 5 sensitive-input categories (RRN/cert PIN/account/biometric/internal IDs) + behavioural rules + bypassPermissions clarification + chat-channel = invalid surface. `verify` primitive description gains explicit secure-modal-only callout cross-referencing the new block.

### Phase 4 — TDD implementation
Failing tests first → minimal fixes → tests green:

- `tests/ipc/test_g1_pipa_lookup_gate.py` (10 tests) — gate-decision branch reproduction with mocked registry.
- `tests/llm/test_g1_pipa_safety_directive.py` (12 tests) — static prompt invariants: section presence, sensitive-input enumeration, modal/secure-input routing, chat-channel forbidden phrasing, verify cross-reference.
- `tui/tests/components/onboarding/OnboardingFlow.test.tsx` (+ 2 tests) — env-gate matrix: `AUTO_COMPLETE=1` alone freezes at `pipa-consent` (`current_step_index=2`) without `onComplete`; `AUTO_COMPLETE=1` + `PIPA_CONSENT=opt-in-explicit` fully completes.

## Code change inventory (≤ 200 line budget)

```
prompts/manifest.yaml                              |   2 +-
prompts/system_v1.md                               |  21 +++-
src/kosmos/ipc/stdio.py                            |  72 +++++++++++++-
tui/src/components/onboarding/OnboardingFlow.tsx   |  76 +++++++++++++--
tests/ipc/test_g1_pipa_lookup_gate.py              | new (~165 lines)
tests/llm/test_g1_pipa_safety_directive.py         | new (~110 lines)
tui/tests/components/onboarding/OnboardingFlow.test.tsx | +106
```

Production-code (excluding tests): ~155 lines added/changed. Zero new runtime dependencies (AGENTS.md hard rule preserved).

## Verification chain (all required)

### Layer 1a — pytest
```
$ uv run pytest tests/ipc/test_g1_pipa_lookup_gate.py tests/llm/test_g1_pipa_safety_directive.py
22 passed in 0.22s
```
Broader regression scan:
```
$ uv run pytest tests/llm/ tests/ipc/test_permission_response_receipt_id.py tests/context/test_prompt_manifest_entry_model.py tests/ipc/test_g1_pipa_lookup_gate.py
194 passed in 0.64s
```

### Layer 1b — Ink snapshot (bun test)
```
$ cd tui && bun test tests/components/onboarding/OnboardingFlow.test.tsx
8 pass / 0 fail / 27 expect() calls
```
The two new env-gate tests cover the partial-advance + full-advance branches — `useEffect` does not enter an infinite render loop (idempotency guard verified by absence of "Maximum update depth exceeded" warnings on re-render).

### Layer 5 — tmux capture-pane (β5 + γ9 re-smoke)
**Pre-merge mandatory smoke is documented in audit `scenarios/` directory** — Wave-3 re-smoke after merge will re-execute β5 (NMC) + γ9 (PIPA bypass) using the canonical scenario harness:

```
scripts/tui-tmux-capture.sh \
  specs/realuse-audit-2026-05-05/fixes/g1-pipa-smoke/beta5 \
  specs/realuse-audit-2026-05-05/scenarios/beta/beta5.sh
scripts/tui-tmux-capture.sh \
  specs/realuse-audit-2026-05-05/fixes/g1-pipa-smoke/gamma9 \
  specs/realuse-audit-2026-05-05/scenarios/gamma/gamma9.sh
```

Pass criteria for Wave-3:
- β5: `wait_for_pane "permission_request|모달|⓷ 높은 위험|민감 정보 도구"` MUST hit a frame *before* any `nmc_emergency_search` HTTP call (verified by NMC adapter log absence prior to modal frame).
- γ9: `assertFrameSequence` over γ9 transcript MUST NOT contain "주민등록번호" / "session_id" / "비밀번호" emitted by the **assistant role** (LLM utterances). Citizen's own input is unrestricted; the directive is one-way.

These scenarios are owned by Wave-3 verification (not Wave-2 implementation) — G1 ships the code + tests; Wave-3 confirms the runtime invariant on real K-EXAONE traffic.

## Wave-3 deferred concern

- **Telemetry attribute**: `kosmos.permission.lookup_adapter_gate` should be added to `kosmos.permission` span in stdio.py to make the new lookup-policy decision visible in Langfuse traces. Current logging is at INFO level (text logs only). Defer to a Wave-3 follow-up issue — purely observational, not legal.
- **Prompt-injection robustness**: K-EXAONE may still be coerced into PIPA-input solicitation via prompt injection in `<citizen_request>`. The directive is regression-guarded by frame-sequence assertion (Wave-3) but not by a hard runtime stop. A future spec can add a backend pattern detector for "주민등록번호" in assistant utterances → reject + fail-closed.
- **Ministry-scope step**: gating `ministry-scope` and `terminal-setup` behind `KOSMOS_PIPA_CONSENT=opt-in-explicit` is conservative (those are not strictly PIPA §22 surfaces). If the audit shows test fixtures need partial completion through `terminal-setup`, refine the gate in a Wave-3 patch.

## Audit trail (7 anti-patterns self-check)

| # | Pattern | Status |
|---|---|---|
| 1 | Final-state fallacy | OK — TDD asserts each branch (partial vs full advance) |
| 2 | Grep-as-proof | OK — pytest exercises every branch with mocks; bun test asserts state object fields |
| 3 | Snapshot blindness | OK — Layer 1a pytest + Layer 1b Ink snapshot complement each other |
| 4 | Tool-substitution | OK — fixes are anchored to PIPA §22 invariant + research artefact, not "more tools" |
| 5 | Skim-and-summarize | OK — full read of stdio.py:1370-1500, OnboardingFlow.tsx:90-200, system_v1.md L1-116 |
| 6 | Trusting one's own expect | n/a (Layer 5 deferred to Wave-3) |
| 7 | Fix-the-symptom spiral | OK — three fixes are independent, each addresses one finding's documented root cause |

## References

- AGENTS.md `§ CORE THESIS` + `§ Hard rules` (no KOSMOS-invented permission policy; adapters cite agency policy)
- `docs/requirements/kosmos-migration-tree.md § L1-B B4` (CC `<PermissionRequest>` byte-identical)
- `docs/requirements/kosmos-migration-tree.md § UI-A.4 / UI-C` (5-step onboarding canonical order; modal Y/A/N + receipt)
- `specs/spec-035-permission-gauntlet-wire-completion/` baseline
- Spec 024/025/2295 V1-V6 invariants — preserved (no metadata schema change)
