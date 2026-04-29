# Smoke Scripts — Epic ε #2296

This directory contains Layer 2 (PTY expect) and Layer 4 (vhs visual) smoke verification scripts for the citizen tax-return filing chain (US1).

## Files

| File | Purpose | Layer |
|---|---|---|
| `smoke-citizen-taxreturn.expect` | PTY text-log scenario | Layer 2 |
| `smoke-citizen-taxreturn.tape` | vhs visual + 3 PNG keyframes | Layer 4 |

## Artefacts (produced at T039 run-time)

| File | Layer | Notes |
|---|---|---|
| `../smoke-citizen-taxreturn-pty.txt` | Layer 2 | Full PTY transcript, LLM-grep-friendly |
| `../smoke-citizen-taxreturn.gif` | Layer 4 | Animated full chain (shareable) |
| `../smoke-keyframe-1-boot.png` | Layer 4 | Boot + KOSMOS branding visible |
| `../smoke-keyframe-2-input.png` | Layer 4 | Citizen query typed in |
| `../smoke-keyframe-3-action.png` | Layer 4 | Post-approval state / 접수번호 |

## What Was Actually Captured (T039 run result)

**Environment at time of capture**:
- `KOSMOS_FRIENDLI_TOKEN`: set (live LLM available)
- `KOSMOS_BACKEND_CMD`: `uv run python -m kosmos.ipc.demo.mock_backend`
- `KOSMOS_FORCE_INTERACTIVE=1`: set (required under PTY harness — see KOSMOS-1978 T003b)

**Layer 2 (expect) scenario**: Full PTY session captured. The script:
1. Boots the TUI with the real Mock backend
2. Waits for KOSMOS branding (Checkpoint 1)
3. Sends `내 종합소득세 신고해줘\r` (Checkpoint 2)
4. Waits for permission prompt (Checkpoint 3 — requires live LLM to drive the chain)
5. Sends `Y\r` (Checkpoint 4)
6. Waits up to 30s for `접수번호` (Checkpoint 5)
7. Exits with double Ctrl-C

**Layer 4 (vhs) scenario**: Three PNG keyframes captured:
- Keyframe 1 (boot): KOSMOS branding after 8s boot wait
- Keyframe 2 (input): Citizen query typed in, agentic loop processing
- Keyframe 3 (action): Post-approval state — 접수번호 surfaced (live LLM) or agentic-loop processing state (mock-only fallback)

**Full chain vs. fallback** — two-layer gating:

| Gate | Status (post-PR #2445 head) | Resolution |
|---|---|---|
| **Layer A — verify-dispatch wiring** | ✅ FIXED in this PR | Codex P1 #2446 fix landed: 5 new `AuthContext` typed variants (`SimpleAuthModuleContext`, `ModidContext`, `KECContext`, `GeumyungModuleContext`, `AnyIdSsoContext`), 5 new `PublishedTier` literals, 5 new mock returns wired through Spec 031 `verify(family_hint=...)` dispatcher. Verified by `tests/integration/test_verify_module_dispatch.py` (6 tests). |
| **Layer B — LLM behaviour** | ⚠️ deferred to Epic η #2298 | Even with Layer A fixed, the citizen query "내 종합소득세 신고해줘" doesn't make K-EXAONE emit `verify(family_hint='modid')` because the system prompt doesn't teach the new `mock_verify_module_*` family names or the citizen verify→lookup→submit chain pattern. Captured smoke shows LLM enters "Hatching…" / "Boogieing…" indefinitely. Epic η `prompts/system_v1.md` rewrite is the planned fix. |

**Captured artefact under current state**: boot + query submission + LLM thinking-state. The `Y\r` smoke approval lands as raw input text (no permission prompt fires because no tool call dispatched). Reviewers grep for `FAIL` markers (none); `NOTE` markers indicate Layer B is gating, not a code defect.

**End-to-end receipt-rendering coverage**: load-bearing on the 4-test integration suite at `tests/integration/test_e2e_citizen_taxreturn_chain.py` (T032), which directly invokes the verify / lookup / submit mocks via Python imports and asserts the 3-line ledger trail with matching `delegation_token`. This proves the mock chain + dispatcher both work; the LLM-driven TUI smoke just can't surface 접수번호 until Epic η ships the system-prompt update.

## Offline Scripted-Chain Fallback

If neither path above produces the full receipt token, use the scripted-chain harness:

```bash
cd /Users/um-yunsang/KOSMOS-w-2296
uv run python -m kosmos.ipc.demo.scripted_chain \
  --scenario specs/2296-ax-mock-adapters/scenarios/citizen-taxreturn.json
```

The scenario JSON is at `../scenarios/citizen-taxreturn.json`.

Note: `kosmos.ipc.demo.scripted_chain` may need to be authored if not yet present — check `src/kosmos/ipc/demo/` and see `quickstart.md § 6` for the expected CLI interface.

## Reference

- `AGENTS.md § TUI verification` — Layer 2 + Layer 4 mandates
- `docs/testing.md § Layer 4 — vhs visual + PNG keyframes` — canonical recipe
- `specs/2294-5-primitive-align/scripts/smoke-emergency-lookup.{expect,tape}` — sister Epic reference implementation
