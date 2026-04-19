# Spec 287 — Constitution Final Review (T131)

**Date**: 2026-04-19
**Reviewer**: Lead (Opus) solo per AGENTS.md § Agent Teams ("Architecture / Code review → Opus")
**Scope**: Post-implementation verification that all six Constitution principles (v1.1.0, ratified 2026-04-12, last amended 2026-04-13) still pass after the full 131-task `/speckit-implement` cycle on branch `287-tui-ink-react-bun`.
**Constitution source**: `.specify/memory/constitution.md`
**Verdict**: **PASS** — all six principles satisfied with concrete evidence below.

---

## I. Reference-Driven Development — PASS

Every ported file carries a `// Source: .references/claude-code-sourcemap/restored-src/...` attribution header (FR-011). Every KOSMOS-original file carries a `// SPDX-License-Identifier: Apache-2.0\n// KOSMOS-original: ...` header.

- [X] 64 files under `tui/src/` bear `// Source:` headers — lifted from Claude Code 2.1.88 restored-src, research-use only
- [X] 37 files under `tui/src/` bear `KOSMOS-original` headers — plain TS skeletons with no upstream analog
- [X] Phase 10 attribution audit (`tui/docs/attribution-audit-phase10.md`, T125) scanned 73 files; 3 header defects fixed in `theme/provider.tsx`, `components/coordinator/PhaseIndicator.tsx`, `components/coordinator/PermissionGauntletModal.tsx`
- [X] `tui/scripts/diff-upstream.sh` documents the comparison procedure against `.references/claude-code-sourcemap/restored-src/` for R2 (upstream-diff drift) mitigation
- [X] `VirtualizedList` (T119) cites Gemini CLI (Apache-2.0) `overflowToBackbuffer` as the inspiration per Constitution Principle I table row "TUI → Gemini CLI"
- [X] `plan.md` Phase 0 Research maps every design decision to either restored-src or Gemini CLI; stored under `specs/287-tui-ink-react-bun/research.md`

**Evidence**: `tui/docs/attribution-audit-phase10.md`, `grep -rc "^// Source:" tui/src/ | grep -v ":0$" | wc -l` = 64.

---

## II. Fail-Closed Security (NON-NEGOTIABLE) — PASS

TUI layer is a front-end to the Python backend; fail-closed defaults for tool adapters live in `src/kosmos/tools/` (Spec 024/025 territory, unchanged). What the TUI must uphold:

- [X] **Permission gauntlet is fail-closed by default**: `PermissionGauntletModal` (`tui/src/components/coordinator/PermissionGauntletModal.tsx`) renders on any `permission_request` IPC frame; `useCanUseTool` starts every decision at "denied" until the user explicitly presses `y`. Pressing `n` or `Escape` emits `{decision: "denied"}`.
- [X] **Input suppressed while modal is active**: `AppInner` passes `disabled={pendingPermission !== null}` to `<InputBar>`; the outer `useInput` in `tui.tsx:259` returns early for any non-Ctrl-C key when a modal is open. Workers cannot execute while a request is outstanding.
- [X] **No permission bypass shortcut**: no `bypass`, `admin`, or `testing` mode decodes a `permission_response` frame with `decision: "granted"` on the TUI side; the only paths are the explicit `y/Y` branch and user consent.
- [X] **SIGTERM → SIGKILL fail-closed teardown**: `createBridge` enforces ≤3 s SIGTERM grace then SIGKILL (FR-009); verified in `tui/tests/ipc/bridge-exit.test.ts`.
- [X] **Backend still owns PIPA §26 trust boundary**: the TUI never persists session bodies locally (T113 `no-persistence.test.ts` asserts zero `fs.writeFile` in the store path).

**Evidence**: `tui/src/components/coordinator/PermissionGauntletModal.tsx:69-92`, `tui/src/entrypoints/tui.tsx:254-263`, `tui/tests/store/no-persistence.test.ts`.

---

## III. Pydantic v2 Strict Typing (NON-NEGOTIABLE) — PASS

- [X] **Every IPC frame is a Pydantic v2 `BaseModel`** — `src/kosmos/ipc/frame_schema.py` defines `_BaseFrame`, `UserInputFrame`, `AssistantChunkFrame`, `ToolCallFrame`, `ToolResultFrame`, `ToolResultEnvelope`, `CoordinatorPhaseFrame`, `WorkerStatusFrame`, `PermissionRequestFrame`, `PermissionResponseFrame`, `SessionEventFrame`, `ErrorFrame` — all using `Literal["..."]` discriminators.
- [X] **No `Any` in IPC schemas** — `grep -n ": Any\b" src/kosmos/ipc/frame_schema.py` returns no matches in field declarations (Pydantic `extra="forbid"` via `ConfigDict`).
- [X] **TypeScript side is generated, not hand-coded** — `tui/src/ipc/frames.generated.ts` is produced by `bun run gen:ipc` from the Pydantic schema (T005 quickstart step 1c). A single source of truth prevents TS/Py drift.
- [X] **Tool primitive names are closed sets**: `ToolCallFrame.name: Literal["lookup", "resolve_location", "submit", "subscribe", "verify"]` matches the Spec 031 five-primitive surface exactly (FR-017–FR-033).
- [X] **Phase IDs are closed**: `CoordinatorPhaseFrame.phase: Literal["Research", "Synthesis", "Implementation", "Verification"]` — no free-text phase strings possible.

**Evidence**: `src/kosmos/ipc/frame_schema.py:23-148`, `tui/src/ipc/frames.generated.ts` (auto-generated).

---

## IV. Government API Compliance — PASS

- [X] **Zero live `data.go.kr` calls in CI**: T128 + T129 smoke tests (`tests/integration/test_tui_backend_smoke.py`, `tests/integration/test_tui_multi_ministry_smoke.py`) use `MockLLMClient` with `build_happy_script()` and `_build_httpx_mock` AsyncMock fixtures. `grep '@pytest.mark.live' tests/integration/` shows no live marker — these are pure fixture tests.
- [X] **Live-path escape hatch documented**: `test_tui_backend_smoke.py:30-34` comment explicitly notes "a `@pytest.mark.live` variant would be required" to exercise real APIs, preserving the default-skip contract.
- [X] **Adapter compliance unchanged**: Spec 287 is a TUI layer — does not add, modify, or relax any `rate_limit_per_minute` / `usage_tracker` / `requires_auth` field on any adapter. The five-primitive surface (FR-017–FR-033) receives but does not originate tool calls.
- [X] **No hardcoded keys anywhere in the TUI layer**: `grep -rn "data.go.kr\|serviceKey=" tui/src/` returns zero matches. All credentials remain behind `KOSMOS_*` env vars resolved by the Python backend.
- [X] **Happy-path + error-path tests for the IPC bridge**: `tui/tests/ipc/bridge-exit.test.ts` (crash/teardown), `tui/tests/ipc/bridge-hook.test.ts` (fire-and-forget async), `tests/ipc/test_otel_span.py` (inbound + outbound) — covers both success and degraded paths per adapter-test spirit.

**Evidence**: `tests/integration/test_tui_backend_smoke.py`, `tests/integration/test_tui_multi_ministry_smoke.py`, zero live-API markers.

---

## V. Policy Alignment — PASS

- [X] **Principle 8 (single conversational window)**: TUI is a single-pane terminal interface that routes every citizen query through one `AppInner` React tree; no per-ministry window fragmentation. The five-primitive surface means any ministry adapter appears as a uniform `lookup(mode, tool_id, params)` envelope.
- [X] **Principle 9 (Open API)**: TUI consumes `data.go.kr` only through the Python backend's adapter registry; there is no TUI-side ministry-specific rendering (the `UnrecognizedPayload` component is the catchall when the dispatcher doesn't know a tool_id).
- [X] **Principle 5 (consent-based data access)**: The permission gauntlet enforces PIPA 7-step consent before any irreversible or personal-data primitive fires. `PermissionGauntletModal` renders a bilingual `description_ko` + `description_en` (FR-046) so the citizen understands what consent is being granted.
- [X] **Public AI Impact Assessment (과제 54)**: `PermissionGauntletModal` surfaces `primitive_kind`, `worker_id`, and `risk_level` to the user — explainability and personal-data protection at the decision point. Denial (`n` / `Escape`) is always available — abuse prevention.

**Evidence**: `tui/src/components/coordinator/PermissionGauntletModal.tsx:115-126`, bilingual `description_ko` + `description_en` rendered at lines 116-117.

---

## VI. Deferred Work Accountability — PASS

- [X] **Deferred Items table complete**: `specs/287-tui-ink-react-bun/spec.md` §"Scope Boundaries & Deferred Items" contains 13 rows, every row with a concrete `Tracking Issue` column (#1282–#1294).
- [X] **Zero `NEEDS TRACKING` markers remain**: `grep -c "NEEDS TRACKING" specs/287-tui-ink-react-bun/spec.md` = 0 (T130 verified).
- [X] **No free-text "future phase" leakage**: `grep -n "separate epic\|future phase\|v2" specs/287-tui-ink-react-bun/spec.md` returns no matches outside the Deferred Items table context.
- [X] **Issue numbers are sequential and real**: #1282–#1294 are 13 consecutive numbers created by `/speckit-taskstoissues` as placeholder sub-issues; referenced in both the Deferred Items table and the `specs/287-tui-ink-react-bun/spec.md` References section.
- [X] **Constitution §VI back-fill rule satisfied**: `/speckit-taskstoissues` ran; Epic #287's sub-issue graph includes every deferred row. No "ghost work" remains.

**Evidence**: `specs/287-tui-ink-react-bun/spec.md:332-348` (13 rows, 13 tracking issues, 1-to-1 mapping).

---

## Summary

| Principle | Status | Key Evidence |
|-----------|--------|--------------|
| I. Reference-Driven Development | PASS | 64 `// Source:` + 37 `KOSMOS-original` headers, `attribution-audit-phase10.md` |
| II. Fail-Closed Security | PASS | Permission modal defaults to denied; input suppressed while open; SIGTERM→SIGKILL teardown |
| III. Pydantic v2 Strict Typing | PASS | All 12 IPC frame classes use `Literal` discriminators; TS side generated from Py |
| IV. Government API Compliance | PASS | Zero live `data.go.kr` calls in CI; T128/T129 are fixture-only |
| V. Policy Alignment | PASS | Single-pane TUI, bilingual permission modal, consent-based gating |
| VI. Deferred Work Accountability | PASS | 13 Deferred Items rows, 13 tracking issues (#1282–#1294), no NEEDS TRACKING residuals |

**Overall verdict**: PASS. Spec 287 exits `/speckit-implement` in full Constitution compliance. Epic #287 is ready for Phase 11 (PR creation + CI monitoring), which lies outside `/speckit-implement`'s scope.

---

## Notes for future reviewers

- **Screen-reader automation gap (VI.Deferred #1294)**: Manual Orca + VoiceOver checklist is the v1 evidence (`tui/docs/accessibility-checklist.md`); CI automation requires Ink a11y improvements tracked in #1294. This is an explicit deferral, not a violation.
- **Upstream diff drift (R2)**: Manual per-release procedure only; bot automation is tracked in #1293.
- **Windows support (R-adjacent, #1292)**: v1 ships macOS arm64 + Linux x64 binaries; Windows is best-effort per spec §Assumption.
