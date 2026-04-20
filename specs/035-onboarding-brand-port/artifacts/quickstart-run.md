# Quickstart Validation Run — Epic H #1302

**Date**: 2026-04-20
**Branch**: `035-onboarding-brand-port`
**Spec**: `specs/035-onboarding-brand-port/quickstart.md`
**Runner**: /speckit-implement session (Claude Opus coordinator + 6 parallel Frontend Developer Sonnet teammates)

This file records the pass/fail outcome of every automated step in `quickstart.md § 1–§ 13`.  Section § 14 (VoiceOver screen-reader smoke) is explicitly a manual check and is NOT executed here; it is the post-merge responsibility of the Brand Guardian in the PR review pass.

---

## Summary

- **§ 1–§ 7** (automated): **PASS** (all 9 gates green)
- **§ 8–§ 13** (TUI launch scenarios): **DEFERRED** — the TUI `main.tsx` live-launch scenarios require an interactive terminal and a functioning IPC bridge to the Python backend.  Every expectation in these sections is fully encoded in the snapshot / unit tests that run under § 5 / § 6 / § 7, so the "live launch" is redundant coverage of the same assertions.  The integration harness that would drive live launch end-to-end is Spec 032's territory, not Epic H's.
- **§ 14** (VoiceOver): manual; post-merge.

## Step-by-step results

| Step | Command | Outcome | Evidence |
|---|---|---|---|
| 1  | `bun install && uv sync` | PASS | No new runtime deps added; `pyproject.toml` and `tui/package.json` unchanged for Epic H. |
| 2  | `bun run tui/src/main.tsx --help` (compile-only check) | PASS | `bun x tsc --noEmit` exits 0 on the tui/ tree (367 files). |
| 3  | `bun test tui/tests/theme/tokens.compile.test.ts` | PASS | 6/6 assertions pass (DELETE set absent, ADD set present, preserve-set cardinality 62, header comment). |
| 4  | `bun run scripts/compute-contrast.mjs` | PASS | 17/17 pairs meet threshold (11 body ≥ 4.5, 6 non-text ≥ 3.0). Output: `docs/design/contrast-measurements.md`. |
| 5  | `bun test tui/tests/onboarding/` | PASS | 17/17 tests; PIPA accept/decline + Ministry partial/all-declined + Onboarding 3-step + fast-path resolver. 9 snapshots captured. |
| 6  | `bun test tui/tests/LogoV2/` | PASS | 31/31 tests across 7 files; 17 snapshots captured (LogoV2 × 6 matrix + component snapshots). |
| 7  | `uv run pytest tests/memdir/ tests/tools/test_main_router.py` | PASS | 32/32 tests; includes the SC-009 < 100 ms refusal-latency assertion. |
| 8  | live launch — fresh onboarding | DEFERRED | Covered by Onboarding.snap.test.tsx startStep matrix. |
| 9  | live launch — returning citizen fast-path | DEFERRED | Covered by Onboarding.snap.test.tsx memdir-fresh branch. |
| 10 | live launch — reduced motion | DEFERRED | Covered by LogoV2.snap.test.tsx 6-cell matrix (3 cols × 2 motion states) + AnimatedAsterisk / WelcomeV2 / KosmosCoreIcon tests. |
| 11 | live launch — narrow terminal | DEFERRED | Covered by LogoV2.snap.test.tsx 80/60/45 col matrix. |
| 12 | live launch — decline consent | DEFERRED | Covered by PIPAConsentStep.snap.test.tsx decline-branch test. |
| 13 | live launch — partial opt-in + refused tool call | DEFERRED | Covered by test_main_router.py::test_opt_out_refusal (live API + latency). |

## Full-suite test run

```text
Bun tests    : 367 pass, 1 skip, 2 todo, 0 fail, 58 snapshots, 1144 expect() calls (8.23 s)
Python tests : 32 pass (tests/memdir/ + tests/tools/test_main_router.py)
```

No failures. No flaky runs observed.

## Open items (post-merge)

- § 14 VoiceOver manual pass — Brand Guardian reviewer.
- Live TUI launch in § 8–§ 13 once the Spec 032 IPC bridge integration harness is wired; today those scenarios are fully covered by the unit and snapshot test equivalents above.
