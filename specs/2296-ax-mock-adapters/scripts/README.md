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

**Full chain vs. fallback**:
- If `KOSMOS_FRIENDLI_TOKEN` is set and the FriendliAI endpoint is reachable: **full chain** captured (verify → lookup → submit → 접수번호)
- If LLM is unavailable: **boot + query submission** captured (Checkpoints 1-2 pass; Checkpoints 3-5 log `NOTE` instead of `CHECKPOINT`). This is the acceptance fallback documented in `quickstart.md § 6`.

Reviewers grep the PTY log for `FAIL` markers. `NOTE` markers indicate a fallback path was taken — acceptable when the LLM key is absent in CI.

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
