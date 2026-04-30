# Contract — PTY Smoke Protocol (FR-011 / 013 / 014 / 015)

**Date**: 2026-04-30
**Owner**: `specs/2297-zeta-e2e-smoke/scripts/smoke-citizen-taxreturn.expect`

## I-P1 — Driver script structure

**Given** a clean working tree with η commit `1321f77` on `main` and `KOSMOS_FRIENDLI_TOKEN` set.

**Then** `smoke-citizen-taxreturn.expect` MUST:
1. `set timeout 90` (90s total budget).
2. `spawn bash -c "cd $env(HOME)/KOSMOS-w-2297/tui && bun run tui"`.
3. `expect "KOSMOS"` (boot+branding render).
4. `send "종합소득세 신고해줘\r"`.
5. `expect -re "접수번호: hometax-2026-\\d\\d-\\d\\d-RX-\[A-Z0-9\]\{5\}"` — strict regex on receipt id.
6. Capture full PTY session via `log_file specs/2297-zeta-e2e-smoke/smoke-citizen-taxreturn-pty.txt`.
7. Send `\003\003` to terminate.
8. `expect eof`.

## I-P2 — Synthetic checkpoint marker

**Given** the smoke harness observes the receipt arm in a `tool_result` frame.

**Then** the harness MUST emit `CHECKPOINTreceipt token observed` to stdout exactly once. This is a literal string the harness inserts when its `tool_result` parser sees `envelope.kind === 'submit'` AND `envelope.transaction_id` matches the receipt regex. The `expect` script MUST also `expect "CHECKPOINTreceipt token observed"` to assert convergence.

The marker is implemented in the TUI side (e.g. in `dispatchPrimitive.ts` when `KOSMOS_SMOKE_CHECKPOINTS=true` env is set) — fire-and-forget `process.stderr.write` so it lands in PTY capture but does not pollute production output.

## I-P3 — Captured log MUST contain three tool_call markers (FR-014)

**Given** the captured `specs/2297-zeta-e2e-smoke/smoke-citizen-taxreturn-pty.txt`.

**Then** `grep -c 'tool_call' smoke-citizen-taxreturn-pty.txt` MUST return ≥3, and `grep -c 'tool_result' MUST return ≥3.

The TUI renders `tool_call`/`tool_result` markers in its existing tool-execution output style (via `renderToolUseMessage` / `renderToolResultMessage`). These are LLM-grep-friendly substrings.

## I-P4 — Receipt id regex (FR-015)

**Given** the captured log.

**Then** `grep -oE '접수번호: hometax-2026-[0-9]{2}-[0-9]{2}-RX-[A-Z0-9]{5}' smoke-citizen-taxreturn-pty.txt` MUST return exactly one match.

## I-P5 — CI-friendly determinism

**Given** `CI=true` env var set.

**Then** the mock submit adapter `mock_submit_module_hometax_taxreturn` MUST use a deterministic seed for the random suffix. The expected suffix value under CI is documented in the integration test fixture `tests/fixtures/citizen_chains/modid.json` `expected_receipt_id_ci_only` field (resolved during /speckit-implement).

## I-P6 — No flaky behavior

**Given** the smoke is run 3 times back-to-back on CI HEAD.

**Then** each run MUST PASS (FR-021 SC-001). If any run fails, the smoke is flaky and the change is BLOCKED until root-cause is found.

## I-P7 — Lead Opus push-gate

**Given** AGENTS.md § TUI verification methodology Layers 0–4 mandatory.

**Then** before `git push`, Lead Opus MUST verify presence of:
- `specs/2297-zeta-e2e-smoke/scripts/smoke-citizen-taxreturn.expect`
- `specs/2297-zeta-e2e-smoke/smoke-citizen-taxreturn-pty.txt`
- `specs/2297-zeta-e2e-smoke/scripts/smoke-citizen-taxreturn.tape`
- `specs/2297-zeta-e2e-smoke/scripts/smoke-keyframe-1-boot.png`
- `specs/2297-zeta-e2e-smoke/scripts/smoke-keyframe-2-dispatch.png`
- `specs/2297-zeta-e2e-smoke/scripts/smoke-keyframe-3-receipt.png`

The PR description MUST list all 6 artefacts.
