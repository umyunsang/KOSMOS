# Tasks · Spec 2642 · S7 IPC/Bridge cleanup

**Spec**: `specs/2642-s7-ipc-bridge/spec.md`
**Plan**: `specs/2642-s7-ipc-bridge/plan.md`
**Branch**: `feat/2642-s7-ipc-bridge`
**Epic**: #2642

---

## Legend

- `[ ]` not started
- `[x]` complete
- `[P]` parallel-safe (independent file tree, no cross-task dependency)

---

## Phase 1 — Setup (Lead solo)

- [x] **T001** — Worktree set up at `/Users/um-yunsang/UMMAYA-w-2642`, branch `feat/2642-s7-ipc-bridge`. (Done before /speckit-implement.)

## Phase 2 — Foundational (Lead solo)

- [x] **T002** — Create `specs/2642-s7-ipc-bridge/checklists/cc-migration.md` (constitution compliance ledger).

## Phase 3 — US1: `remote/` cleanup (TG-A · Sonnet teammate · `[P]`)

- [x] **T003** [P] — DELETE `tui/src/server/directConnectManager.ts`, `tui/src/server/createDirectConnectSession.ts`, `tui/src/server/types.ts`. Verify the directory is empty, then DELETE `tui/src/server/` itself.
- [x] **T004** [P] — DELETE `tui/src/hooks/useDirectConnect.ts`.
- [x] **T005** [P] — Edit `tui/src/screens/REPL.tsx`:
  - Remove imports of `useDirectConnect` (line 62) and `DirectConnectConfig` (line 63).
  - Remove the `directConnectConfig?: DirectConnectConfig;` prop (line 650) and its destructuring (line 680).
  - Remove the `useDirectConnect({ ... })` call block (lines 1542-1549).
  - Replace `activeRemote = sshRemote.isRemoteMode ? sshRemote : directConnect.isRemoteMode ? directConnect : remoteSession` (line 1563) with `activeRemote = sshRemote.isRemoteMode ? sshRemote : remoteSession`.
  - Update the comment on line 1039 to remove the stale `useDirectConnect` mention.
  - Add a header comment at the top of the diff range: `// UMMAYA-2642 / Epic F · S7 — directConnect/server/ DROPPED (claude.ai sync swap-out, Spec 2642 § US1).`
- [x] **T006** [P] — Find and update any remaining call sites passing `directConnectConfig` to REPL or referencing the deleted surfaces. (Search: `grep -rn 'directConnect\|DirectConnect\|createDirectConnectSession' tui/src/`. Expect zero non-comment matches after the cleanup.)
- [x] **T007** [P] — Run `cd tui && bun typecheck` and `bun test`; fix any breakage caused by T003-T006.

## Phase 4 — US2: `notification_push` SWAP doc + parity test (TG-B · Sonnet teammate · `[P]`)

- [x] **T008** [P] — Edit `src/ummaya/ipc/frame_schema.py:NotificationPushFrame.__doc__` to insert the CC-parity verification literal `"CC parity: NO equivalent"` and a 4-line explanation of CC's terminal-OSC notification path (per plan § 1.2).
- [x] **T009** [P] — Create `tests/ipc/test_notification_push_swap_parity.py` per spec § US2 acceptance:
  - Test 1: role allow-list assertion (`_KIND_ROLE_ALLOWLIST["notification_push"] == frozenset({"notification"})`).
  - Test 2: docstring contains `"CC parity: NO equivalent"`.
  - Test 3: required-fields enumeration matches the 5 expected keys.
  - Test 4: happy-path frame validates.
  - Test 5: empty payload rejects with ValidationError.
- [x] **T010** [P] — Run `uv run pytest tests/ipc/test_notification_push_swap_parity.py -v`; ensure all PASS.

## Phase 5 — US3: codec.ts ↔ Python envelope drift CI (TG-C · Sonnet teammate · `[P]`)

- [x] **T011** [P] — Create `tests/ipc/test_codec_envelope_parity.py`. Implementation:
  1. `_extract_codec_envelope_fields(codec_text: str) -> dict[str, FieldSpec]` — regex-based parser anchored on `correlation_id:`, `transaction_id:`, `frame_seq:`, `version:`, `role:`, `kind:`, `timestamp:` lines inside the envelope zod object literal.
  2. `_extract_pydantic_envelope_fields() -> dict[str, FieldSpec]` — uses `_BaseFrame.model_fields` + `FrameTrailer.model_fields`.
  3. `run_codec_envelope_parity_check(codec_path: pathlib.Path | None = None) -> None` — compares the two and raises `AssertionError` with a per-field diagnostic on mismatch.
  4. `test_codec_envelope_parity_passes_on_real_codec()` — calls the check with the real `tui/src/ipc/codec.ts`.
  5. `test_drift_negative_fixture_triggers_failure(monkeypatch)` — sets `UMMAYA_IPC_PARITY_DRIFT_FIXTURE=1`, expects `pytest.raises(AssertionError)` matching `"correlation_id"`.
- [x] **T012** [P] — Create `tests/ipc/fixtures/codec_drift_negative.ts` (a 30-line text file mirroring the codec.ts envelope shape but with `correlation_id` made optional; carries a header comment forbidding runtime import).
- [x] **T013** [P] — Edit `tests/ipc/conftest.py` (or create if absent in that path; check first) to add a guard fixture that ensures `UMMAYA_IPC_PARITY_DRIFT_FIXTURE` is unset by default in every test that does not explicitly opt in. (If a separate `tests/conftest.py` already exists, add the guard there.)
- [x] **T014** [P] — Edit `.github/workflows/tui-ipc-drift.yml`:
  - Add `tui/src/ipc/codec.ts` to `paths:` for both `pull_request` and `push`.
  - Add a new step (after the existing drift check):
    ```yaml
    - name: Run codec.ts envelope parity check
      run: uv run pytest tests/ipc/test_codec_envelope_parity.py -v
      env:
        PYTHONPATH: ${{ github.workspace }}/src
    ```
- [x] **T015** [P] — Run `uv run pytest tests/ipc/test_codec_envelope_parity.py -v`; ensure both happy-path and negative-fixture tests PASS.

## Phase 6 — US4: ADR-009 (TG-D · Lead solo)

- [x] **T016** — Author `docs/adr/ADR-009-mcpb-compat-lazy-shim.md` per spec § US4 acceptance + plan § 1.5.

## Phase 7 — Cross-cutting verification (Lead solo)

- [x] **T017** — Create `specs/2642-s7-ipc-bridge/scripts/smoke-2642.sh` (Layer 5 tmux-capture) per plan § 2.3.
- [x] **T018** — Run the smoke; commit `snap-NNN-*.txt` + `final.txt` artifacts to `specs/2642-s7-ipc-bridge/snapshots/`.
- [x] **T019** — Author the vhs `.tape` (`specs/2642-s7-ipc-bridge/scripts/smoke-2642.tape`) emitting 3 named PNG keyframes (boot / help / exit) + `smoke-2642.gif`.
- [x] **T020** — Read each PNG keyframe via the Read tool to verify visual rendering (Layer 4 mandate).
- [x] **T021** — Run full test suite: `cd tui && bun typecheck && bun test` + `uv run pytest tests/ipc/ -v`.
- [x] **T022** — Commit + push to `feat/2642-s7-ipc-bridge`.
- [x] **T023** — Open PR with `Closes #2642` body. Cite all 4 task-group artifacts in the PR description.
- [x] **T024** — Watch CI (`gh pr checks --watch --interval 10`).
- [x] **T025** — Triage Codex inline reviews; reply or fix each P1.
- [x] **T026** — Verify Copilot Review Gate transitions to `completed`.
- [x] **T027** — Report `MILESTONE: ready to merge` and stop. (User to merge.)

---

## Dispatch grouping (for /speckit-implement)

```
Phase 1-2 Setup + Foundational (T001-T002): Lead solo
Phase 3 US1 (T003-T007): sonnet-us1-remote-drop      ┐
Phase 4 US2 (T008-T010): sonnet-us2-notif-swap       ├─ parallel
Phase 5 US3 (T011-T015): sonnet-us3-codec-parity     ┘
Phase 6 US4 (T016): Lead solo
Phase 7 Verification (T017-T027): Lead solo
```

(Detail: `specs/2642-s7-ipc-bridge/dispatch-tree.md`.)

---

## Constitution compliance checklist (`specs/2642-s7-ipc-bridge/checklists/cc-migration.md`)

- [ ] All source text in English (Korean only in domain docstrings).
- [ ] Zero new runtime dependencies (Python or TS).
- [ ] No `--force` push, `--no-verify`.
- [ ] No direct main commit.
- [ ] No edit to `bridge/`, `upstreamproxy/`, `native-ts/` (PRESERVE-IDENTICAL invariant).
- [ ] No new IPC arm; arm count = 22.
- [ ] PR body cites `Closes #2642` only (not Task sub-issues).
- [ ] Layer 5 tmux smoke + 3 PNG keyframes captured.
