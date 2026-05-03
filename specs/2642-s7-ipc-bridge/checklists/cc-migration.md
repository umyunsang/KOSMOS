# Constitution + Migration compliance · Spec 2642

**Source**: `.specify/memory/constitution.md` (project-wide hard rules) + `AGENTS.md § Hard rules` + `docs/requirements/kosmos-migration-tree.md`.

---

## Hard rules (AGENTS.md)

| Rule | Status | Note |
|---|---|---|
| All source text in English | ✅ | Korean only in domain strings (e.g. `payload` field description) — preserved unchanged |
| Env vars prefixed `KOSMOS_` | ✅ | New env: `KOSMOS_IPC_PARITY_DRIFT_FIXTURE` (test-only) |
| Stdlib `logging` only | ✅ | No new logging surfaces |
| Pydantic v2 for all tool I/O | ✅ | No new Pydantic models; existing `_BaseFrame` / `NotificationPushFrame` unchanged in shape (only docstring extended) |
| Never call live `data.go.kr` from CI | ✅ | Test is pure stdlib regex + Pydantic introspection; no HTTP |
| No new dep outside spec-driven PR | ✅ | Zero new deps |
| Never `--force` push, `--no-verify` | ✅ | Lead enforces |
| Never `requirements.txt`/`setup.py`/`Pipfile` | ✅ | None created |
| Never commit > 1 MB file without ask | ✅ | Largest new artifact: smoke `.gif` (target < 200 KB) |
| Never introduce Go/Rust | ✅ | None introduced |

---

## Spec-driven workflow (AGENTS.md § Spec-driven workflow)

| Step | Status |
|---|---|
| Epic issue created (`epic` label) | ✅ #2642 (parent Initiative #2636) |
| /speckit-specify → spec.md | ✅ |
| /speckit-plan → plan.md (Phase 0 cites docs/vision.md § Reference materials) | ✅ |
| /speckit-tasks → tasks.md | ✅ |
| /speckit-analyze → constitution check | ✅ (this file) |
| /speckit-taskstoissues → Task issues | Pending — Phase 7 |
| /speckit-implement → dispatch tree | ✅ `dispatch-tree.md` authored |
| PR with `Closes #EPIC` only | Pending — Phase 7 |
| Monitor CI → close Task sub-issues | Pending — Phase 7 |

---

## CC-Migration alignment (kosmos-migration-tree.md)

| L-pillar | Touched? | Justification |
|---|---|---|
| L1-A LLM Harness | No | No LLM code path edited |
| L1-B Tool System | No | No tool registry / adapter edits |
| L1-C Main-Verb Abstraction | No | No primitive edits |
| UI L2 | Indirect | REPL.tsx edit is a dead-code removal, not a UX change |

| Phase | Touched? | Justification |
|---|---|---|
| P0 Baseline | No | |
| P1 Dead-code | Yes | TG-A is dead-code removal continuation |
| P2 Anthropic→FriendliAI | Indirect | TG-A removes dead claude.ai surfaces |
| P3 Tool wiring | No | |
| P4 UI L2 | No | |
| P5 Plugin DX | No | |
| P6 Docs+Smoke | Yes | TG-D adds ADR-009 + Layer 5 smoke |

---

## TUI verification mandate (AGENTS.md § TUI verification)

| Layer | Status |
|---|---|
| Layer 1a Python unit | ✅ TG-B + TG-C add new pytest tests |
| Layer 1b Ink snapshot | n/a — REPL.tsx edit is delete-only; existing snapshots cover the kept paths |
| Layer 2 stdio JSONL probe | ✅ existing `tui-ipc-drift.yml` + new `test_codec_envelope_parity.py` |
| Layer 3 PTY text-log | ✅ Phase 7 T017-T018 (tmux capture-pane) |
| Layer 4 vhs PNG keyframes (3+) | ✅ Phase 7 T019-T020 |
| Layer 5 tmux capture | ✅ Phase 7 T017-T018 |

---

## Dispatch unit compliance (AGENTS.md § Agent Teams)

| Teammate | Tasks | File-touch count | Within ≤ 5 tasks AND ≤ 10 files? |
|---|---|---|---|
| sonnet-us1-remote-drop | T003-T007 (5) | ~6 | ✅ |
| sonnet-us2-notif-swap | T008-T010 (3) | 2 | ✅ |
| sonnet-us3-codec-parity | T011-T015 (5) | 4 | ✅ |

All teammate prompts in `dispatch-tree.md` are ≤ 30 lines. ✅

---

## Outcome

PASS — proceed to /speckit-implement.
