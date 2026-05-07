# Dispatch tree · Spec 2642 · S7 IPC/Bridge cleanup

**Tasks**: see `specs/2642-s7-ipc-bridge/tasks.md`.
**Dispatch unit**: task-group (≤ 5 tasks AND ≤ 10 file changes per Sonnet teammate, per AGENTS.md § Agent Teams).

---

```
Phase 1 Setup        (T001):       Lead solo (worktree + branch already done before /speckit-implement)
Phase 2 Foundational (T002):       Lead solo (constitution checklist file)
Phase 3 US1 TG-A     (T003-T007):  sonnet-us1-remote-drop      ┐
Phase 4 US2 TG-B     (T008-T010):  sonnet-us2-notif-swap       ├─ parallel
Phase 5 US3 TG-C     (T011-T015):  sonnet-us3-codec-parity     ┘
Phase 6 US4 TG-D     (T016):       Lead solo (ADR-009)
Phase 7 Verification (T017-T027):  Lead solo (smoke + PR + CI + Codex + merge-ready)
```

---

## Sonnet prompts (≤ 30 lines each, per AGENTS.md mandate)

### `sonnet-us1-remote-drop` (TG-A)

> You are a Sonnet teammate for UMMAYA Spec 2642 / Epic #2642 / TG-A.
>
> Worktree: `/Users/um-yunsang/UMMAYA-w-2642`. Branch already checked out.
> Read first: `specs/2642-s7-ipc-bridge/spec.md` § US1 + § FR-001 to FR-004 +
> `specs/2642-s7-ipc-bridge/plan.md` § 1.1.
>
> Tasks T003-T007:
> 1. DELETE `tui/src/server/directConnectManager.ts`,
>    `tui/src/server/createDirectConnectSession.ts`,
>    `tui/src/server/types.ts`, then DELETE the empty `tui/src/server/` directory.
> 2. DELETE `tui/src/hooks/useDirectConnect.ts`.
> 3. Edit `tui/src/screens/REPL.tsx` per spec § FR-002. Verify line numbers
>    against current file content; cite line numbers in commit message.
> 4. Run `grep -rn 'directConnect\|DirectConnect\|createDirectConnectSession' tui/src/`;
>    expect zero non-comment matches. Fix any holdouts.
> 5. Run `cd tui && bun typecheck && bun test`. Fix any breakage.
>
> Mark T003-T007 [x] in `tasks.md`. WIP commit with message:
> `feat(2642): TG-A — remote/ DROP-FOR-SWAP cleanup (claude.ai sync swap-out)`.
> Do NOT push, PR, or watch CI — that's Lead.
> Do NOT touch tasks T008+ — those are other teammates.

### `sonnet-us2-notif-swap` (TG-B)

> You are a Sonnet teammate for UMMAYA Spec 2642 / Epic #2642 / TG-B.
>
> Worktree: `/Users/um-yunsang/UMMAYA-w-2642`. Branch already checked out.
> Read first: `specs/2642-s7-ipc-bridge/spec.md` § US2 + § FR-005 to FR-006 +
> `specs/2642-s7-ipc-bridge/plan.md` § 1.2 +
> existing test pattern in `tests/ipc/test_envelope_roundtrip.py:test_e3_notification_push_requires_notification_role`.
>
> Tasks T008-T010:
> 1. Edit `src/ummaya/ipc/frame_schema.py` — replace
>    `NotificationPushFrame.__doc__` with the extended version from plan § 1.2.
>    Preserve the role allow-list and field definitions byte-identical.
> 2. Create `tests/ipc/test_notification_push_swap_parity.py` per spec § US2.
>    5 tests as listed in tasks.md T009. Use `pydantic.ValidationError` for the
>    rejection test.
> 3. Run `uv run pytest tests/ipc/test_notification_push_swap_parity.py -v`.
>    All 5 must PASS.
>
> Mark T008-T010 [x] in `tasks.md`. WIP commit:
> `feat(2642): TG-B — notification_push CC-parity SWAP docstring + parity test`.
> Do NOT push, PR, or watch CI — that's Lead.

### `sonnet-us3-codec-parity` (TG-C)

> You are a Sonnet teammate for UMMAYA Spec 2642 / Epic #2642 / TG-C.
>
> Worktree: `/Users/um-yunsang/UMMAYA-w-2642`. Branch already checked out.
> Read first: `specs/2642-s7-ipc-bridge/spec.md` § US3 + § FR-007 to FR-009 +
> `specs/2642-s7-ipc-bridge/plan.md` § 1.3 + § 1.4.
> Reference: existing `tests/ipc/test_schema_python_ts_diff.py` for style.
> Read `tui/src/ipc/codec.ts` lines 55-75 to understand envelope shape.
>
> Tasks T011-T015:
> 1. Create `tests/ipc/test_codec_envelope_parity.py` per plan § 1.3.
> 2. Create `tests/ipc/fixtures/codec_drift_negative.ts` (test-only fixture).
> 3. Find/edit appropriate `conftest.py` (likely `tests/conftest.py` or
>    `tests/ipc/conftest.py`) to add the `UMMAYA_IPC_PARITY_DRIFT_FIXTURE`
>    default-OFF guard.
> 4. Edit `.github/workflows/tui-ipc-drift.yml` — add `tui/src/ipc/codec.ts`
>    to triggered paths and add the new pytest step.
> 5. Run `uv run pytest tests/ipc/test_codec_envelope_parity.py -v`. All PASS.
>
> Mark T011-T015 [x] in `tasks.md`. WIP commit:
> `feat(2642): TG-C — codec.ts ↔ Python envelope field-level drift CI gate`.
> Do NOT push, PR, or watch CI — that's Lead.

---

## Risk matrix per teammate

| Teammate | File-touch count | Risk |
|---|---|---|
| sonnet-us1-remote-drop | ~6 (4 deletes + REPL.tsx + tasks.md) | M — REPL.tsx is large; verify line numbers carefully |
| sonnet-us2-notif-swap | 2 (frame_schema.py edit + new test) | L |
| sonnet-us3-codec-parity | 4 (test + fixture + conftest + workflow) | M — regex parser must handle codec.ts whitespace robustly |

---

## Lead solo phases

### Phase 6 — ADR-009

Single-file deliverable; no parallelism needed.

### Phase 7 — Verification + PR

Sequential by nature:
- T017-T020: smoke capture + PNG keyframe Read tool inspection (cannot parallelize Layer 4 visual verification)
- T021: full test suite final pass
- T022-T027: push, PR, CI watch, Codex triage, merge-ready report
