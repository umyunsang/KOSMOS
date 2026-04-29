#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""One-shot script to materialize Epic #1979's 38 tasks + 4 deferred placeholders
as GitHub issues + link them as sub-issues of Epic #1979.

Usage: uv run python specs/1979-plugin-dx-tui-integration/scripts/create_issues.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from dataclasses import dataclass

REPO = "umyunsang/KOSMOS"
EPIC_NUM = 1979


@dataclass(frozen=True)
class Task:
    task_id: str
    title: str
    phase: int  # 1..7
    story: str  # "" / "US1" / "US2" / "US3" / "US4"
    parallel: bool
    size: str  # S / M / L
    body: str


# fmt: off
TASKS: list[Task] = [
    # ── Phase 1: Setup ──
    Task(
        "T001", "Capture today's broken /plugin install UX as L3 text-log + L2 JSONL",
        1, "", True, "S",
        "Use existing 4-layer ladder (`expect` + `script` + raw stdio probe) against `main` branch baseline. Output: `specs/1979-plugin-dx-tui-integration/notes-baseline.txt` + `notes-baseline.jsonl`.\n\n"
        "Reference: docs/testing.md § TUI verification methodology, memory `feedback_runtime_verification`.\n\n"
        "**Acceptance**: artifact files exist; observably show `tui/src/commands/plugin/index.tsx` (CC marketplace) being invoked under `/plugin install` rather than KOSMOS path."
    ),
    Task(
        "T002", "Document gap analysis to notes-baseline.md",
        1, "", True, "S",
        "Document: (a) `tui/src/commands.ts:133` mis-routing to CC `commands/plugin/index.tsx`, (b) `plugin_op` IPC frame emit count = 0 (verified via `grep -rn 'plugin_op' src/ tui/src/`), (c) orphaned `tui/src/commands/plugin.ts` (singular).\n\n"
        "Reference: research.md § V1.\n\n"
        "**Acceptance**: `specs/1979-plugin-dx-tui-integration/notes-baseline.md` enumerates the 3 gaps with code citations."
    ),
    # ── Phase 2: Foundational ──
    Task(
        "T003", "Add plugin_op arm to stdio.py:1675 if-elif dispatch chain",
        2, "", False, "S",
        "Add `frame.kind == \"plugin_op\"` branch after `session_event` arm in `src/kosmos/ipc/stdio.py`. Wrap handler call in try/except → ErrorFrame fanout matching the existing `chat_request` / `tool_result` / `permission_response` arms.\n\n"
        "Reference: contracts/dispatcher-routing.md § Dispatch logic.\n\n"
        "**Blocks**: T004, T013\n\n"
        "**Acceptance**: dispatch arm exists; malformed plugin_op frames produce ErrorFrame; well-formed pass through to handler module."
    ),
    Task(
        "T004", "[P] Create plugin_op_dispatcher.py module skeleton",
        2, "", True, "M",
        "Create `src/kosmos/ipc/plugin_op_dispatcher.py` (NEW) with `handle_plugin_op_request(frame, *, registry, executor, write_frame, consent_bridge, session_id)` entry point + `handle_install` / `handle_uninstall` / `handle_list` private routers (signatures only; bodies stub `NotImplementedError`).\n\n"
        "Reference: data-model.md § E1 + contracts/dispatcher-routing.md.\n\n"
        "**Blocked by**: T003\n\n"
        "**Acceptance**: module imports without error; type signatures match data-model.md § E1."
    ),
    Task(
        "T005", "[P] Extend ToolRegistry with _inactive set + lifecycle methods",
        2, "", True, "M",
        "Extend `src/kosmos/tools/registry.py:ToolRegistry` with: `_inactive: set[str]` field + `set_active(tool_id, active: bool) -> None` + `is_active(tool_id) -> bool` + `deregister(tool_id) -> None` methods. Filter `_inactive` from `core_tools` / `all_tools` / `to_openai_tool` / BM25 corpus rebuild.\n\n"
        "Reference: data-model.md § E4.\n\n"
        "**Blocks**: T011 (uninstall calls deregister)\n\n"
        "**Acceptance**: 4 new test methods in T015 pass; existing registry tests still pass."
    ),
    Task(
        "T006", "[P] Create IPCConsentBridge module (consent_bridge.py)",
        2, "", True, "M",
        "Create `src/kosmos/plugins/consent_bridge.py` (NEW) with `IPCConsentBridge` class — sync `__call__(entry, version, manifest) -> bool` matching `installer.ConsentPrompt` signature; emits `PermissionRequestFrame` + awaits `_pending_perms[request_id]` future via `asyncio.wait_for(timeout=60.0)`; returns `False` on TimeoutError (fail-closed).\n\n"
        "Reference: data-model.md § E2 + contracts/consent-bridge.md.\n\n"
        "**Blocks**: T009, T013\n\n"
        "**Acceptance**: 6 unit tests in T016 pass."
    ),
    # ── Phase 3: User Story 1 ──
    Task(
        "T007", "[US1] Add progress_emitter param to install_plugin()",
        3, "US1", False, "M",
        "Modify `src/kosmos/plugins/installer.py:install_plugin()` to accept optional `progress_emitter: Callable[[int, str, str], Awaitable[None]] | None = None` parameter. Call `await progress_emitter(phase_num, message_ko, message_en)` between each of the 7 phases using canonical text from `specs/1636-plugin-dx-5tier/contracts/plugin-install.cli.md § Phases`. Backwards compatible (None → no emit).\n\n"
        "Reference: contracts/dispatcher-routing.md § Outbound frame sequence.\n\n"
        "**Blocks**: T008, T010\n\n"
        "**Acceptance**: existing 6 integration tests + 4 SC tests still pass; new test asserts 7 emitter calls in phase order."
    ),
    Task(
        "T008", "[US1] Implement handle_install in plugin_op_dispatcher.py",
        3, "US1", False, "M",
        "Implement `handle_install` in `src/kosmos/ipc/plugin_op_dispatcher.py`: build progress_emitter closure that wraps each phase tick into a `PluginOpFrame(op=\"progress\", progress_phase=N, progress_message_ko=..., progress_message_en=...)` + `write_frame(...)`. On `install_plugin` return, emit terminal `plugin_op_complete` with `result` + `exit_code` + `receipt_id`.\n\n"
        "Reference: contracts/dispatcher-routing.md § install sequence.\n\n"
        "**Blocked by**: T007\n\n"
        "**Acceptance**: install request → 7 progress frames + 1 complete frame observed; exit_code matches installer return."
    ),
    Task(
        "T009", "[US1] Inject IPCConsentBridge into installer's consent_prompt seam",
        3, "US1", False, "S",
        "Inject `IPCConsentBridge` into `installer.py:install_plugin()` `consent_prompt` parameter at the dispatcher boundary (T008). The default `_default_consent_prompt` (lines 219-229) stays as the test/in-process fallback; the IPC code path uses the bridge.\n\n"
        "Reference: contracts/consent-bridge.md § Signature compatibility.\n\n"
        "**Blocked by**: T006, T008\n\n"
        "**Acceptance**: dispatcher-injected install propagates citizen Y/A/N decision through to install_plugin's phase-5 branch."
    ),
    Task(
        "T010", "[P] [US1] Create uninstall_plugin module",
        3, "US1", True, "M",
        "Create `src/kosmos/plugins/uninstall.py` (NEW) with `uninstall_plugin(plugin_id, *, registry, executor, progress_emitter=None) -> UninstallResult` 3-phase flow: deregister → rmtree → write `PluginConsentReceipt(action_type=\"plugin_uninstall\")`. Idempotent on already-removed plugin.\n\n"
        "Reference: data-model.md § E3 + contracts/dispatcher-routing.md § Outbound (uninstall).\n\n"
        "**Blocks**: T011\n\n"
        "**Acceptance**: 4 new tests in T015's sister file pass (rmtree + deregister + receipt + idempotent)."
    ),
    Task(
        "T011", "[US1] Implement handle_uninstall mirroring handle_install pattern",
        3, "US1", False, "S",
        "Implement `handle_uninstall` in `src/kosmos/ipc/plugin_op_dispatcher.py` mirroring T008 with the 3-phase progress emitter from T010. Reuse the same `_allocate_consent_position` flock for receipt position assignment.\n\n"
        "Reference: contracts/dispatcher-routing.md § uninstall sequence.\n\n"
        "**Blocked by**: T005, T010\n\n"
        "**Acceptance**: uninstall request → 3 progress frames + 1 complete frame; receipt position monotonic."
    ),
    Task(
        "T012", "[US1] Implement handle_list with payload_delta enumeration",
        3, "US1", False, "M",
        "Implement `handle_list` in `src/kosmos/ipc/plugin_op_dispatcher.py`: enumerate `registry._tools` (filtered through `is_active`) + load each plugin's manifest snapshot from install root → emit `payload_start` + `payload_delta` + `payload_end` triplet carrying `PluginListEntry[]` JSON, then a single `plugin_op_complete` with `correlation_id` matching.\n\n"
        "Reference: contracts/dispatcher-routing.md § list payload.\n\n"
        "**Blocked by**: T005\n\n"
        "**Acceptance**: list request → 0 progress frames + payload triplet + complete frame; payload JSON parses to PluginListEntry[]."
    ),
    Task(
        "T013", "[US1] Wire dispatcher boot params into stdio.py",
        3, "US1", False, "S",
        "In `src/kosmos/ipc/stdio.py`, pass `_ensure_tool_registry()` + `_ensure_tool_executor()` + `write_frame` + freshly-constructed `IPCConsentBridge(write_frame=write_frame, pending_perms=_pending_perms, session_id=frame.session_id)` into the T003 if-elif arm's `handle_plugin_op_request` call.\n\n"
        "Reference: contracts/dispatcher-routing.md § Dispatch logic.\n\n"
        "**Blocked by**: T003, T006, T008, T011, T012\n\n"
        "**Acceptance**: end-to-end fixture test (T014) passes."
    ),
    Task(
        "T014", "[P] [US1] Author unit tests test_plugin_op_dispatch.py",
        3, "US1", True, "M",
        "Author `tests/ipc/test_plugin_op_dispatch.py`: 5 cases — install_request_dispatches, uninstall_request_dispatches, list_request_emits_payload_only, unknown_request_op_returns_error_frame, consent_timeout_emits_complete_exit5. Add SC-009 sub-test (analysis.md C2): `test_concurrent_installs_assign_monotonic_positions`. Add FR-010 sub-test (analysis.md C1): `test_install_emits_kosmos_plugin_id_otel_attribute`.\n\n"
        "Reference: contracts/e2e-pty-scenario.md § L1 + analysis.md C1/C2.\n\n"
        "**Acceptance**: all 7 tests pass."
    ),
    Task(
        "T015", "[P] [US1] Author unit tests test_consent_bridge.py",
        3, "US1", True, "M",
        "Author `tests/ipc/test_consent_bridge.py`: 6 cases — allow_once / allow_session / deny / timeout / pii_includes_acknowledgment_sha256 / layer_3_secondary_confirm.\n\n"
        "Reference: contracts/consent-bridge.md § Test seams + data-model.md § E2.\n\n"
        "**Acceptance**: all 6 tests pass."
    ),
    # ── Phase 4: User Story 2 ──
    Task(
        "T016", "[US2] Add pluginsModifiedThisSession session-scoped flag in TUI",
        4, "US2", False, "S",
        "In `tui/src/ipc/bridgeSingleton.ts` (or equivalent), add `pluginsModifiedThisSession: boolean` flag. Set `true` on every `plugin_op_complete:result=\"success\"` for `request_op ∈ {install, uninstall}`. Reset to `false` after consumed once on next ChatRequestFrame build.\n\n"
        "Reference: research.md § R-6 + contracts/dispatcher-routing.md § Tools[] propagation.\n\n"
        "**Blocks**: T017\n\n"
        "**Acceptance**: bun test verifies flag transitions on terminal frame."
    ),
    Task(
        "T017", "[US2] Empty frame.tools when pluginsModifiedThisSession is true",
        4, "US2", False, "S",
        "In TUI ChatRequestFrame builder (likely `tui/src/services/api/` or `tui/src/ipc/bridge.ts` outbound path), if `pluginsModifiedThisSession === true`, set `frame.tools = []` to defer to backend's `registry.export_core_tools_openai()` fallback at `src/kosmos/ipc/stdio.py:1192-1195`. Reset flag after emit.\n\n"
        "Reference: research.md § R-6.\n\n"
        "**Blocked by**: T016\n\n"
        "**Acceptance**: T018 integration test passes."
    ),
    Task(
        "T018", "[P] [US2] Author test_plugin_install_to_invoke.py integration test",
        4, "US2", True, "M",
        "Author `tests/e2e/test_plugin_install_to_invoke.py:test_install_and_invoke_fixture_plugin`: install fixture plugin via dispatcher → send chat_request matching plugin's search_hint_ko (with `frame.tools=[]`) → assert next outbound `tool_use` frame has `tool_id=\"plugin.<id>.<verb>\"`.\n\n"
        "Reference: contracts/e2e-pty-scenario.md § L1 + spec.md US2 acceptance scenarios.\n\n"
        "**Acceptance**: test passes within 3s post-install (SC-002)."
    ),
    Task(
        "T019", "[P] [US2] Author test_plugin_layer_routing.py 3-layer test",
        4, "US2", True, "M",
        "Author `tests/e2e/test_plugin_layer_routing.py`: install 3 fixture plugins with `permission_layer ∈ {1, 2, 3}` → invoke each → assert each `permission_request` carries the correct `layer` field; assert layer-3 plugin triggers Spec 033 layer-3 secondary confirm path.\n\n"
        "Reference: spec.md § FR-011, FR-014, SC-003.\n\n"
        "**Acceptance**: 3 layer scenarios + revocation negative scenario all pass."
    ),
    Task(
        "T020", "[P] [US2] Author test_plugin_pii_acknowledgment.py PIPA round-trip test",
        4, "US2", True, "S",
        "Author `tests/e2e/test_plugin_pii_acknowledgment.py`: install a fixture plugin with `processes_pii: true` + valid PIPA acknowledgment → invoke → assert `permission_request` carries `acknowledgment_sha256` + `trustee_org_name` from the manifest.\n\n"
        "Reference: spec.md § FR-012 + contracts/consent-bridge.md § PIPA §26.\n\n"
        "**Acceptance**: PII fields present in PermissionRequestFrame; layer 2/3 test cases included."
    ),
    # ── Phase 5: User Story 3 ──
    Task(
        "T021", "[US3] CRITICAL: Swap commands.ts:133 import to KOSMOS plugin.ts",
        5, "US3", False, "S",
        "**CRITICAL wire-up**: In `tui/src/commands.ts`, change line 133 from `import plugin from './commands/plugin/index.js'` to `import plugin from './commands/plugin.js'`. This is the single line that activates the entire KOSMOS citizen plugin path; all subsequent US3 tasks depend on it.\n\n"
        "Reference: research.md § V1 verdict.\n\n"
        "**Blocks**: T022, T023..T030\n\n"
        "**Acceptance**: bun test passes; `/plugin install <name>` reaches backend dispatcher (verified via L2 stdio probe at T032)."
    ),
    Task(
        "T022", "[P] [US3] Remove H7 deferred suffix from plugin.ts acknowledgements",
        5, "US3", True, "S",
        "In `tui/src/commands/plugin.ts`, remove the H7 review-eval deferred suffix from acknowledgement strings at lines 111-112, 135-136, 164-166 (`\"(backend dispatcher not yet wired — use ...)\"`). Backend is now wired.\n\n"
        "Reference: spec.md § Background Gap 1.\n\n"
        "**Blocked by**: T021\n\n"
        "**Acceptance**: grep for the deferred suffix returns 0; bun test still passes."
    ),
    Task(
        "T023", "[US3] Replace KOSMOS_PLUGIN_REGISTRY env-var stub with IPC round-trip",
        5, "US3", False, "M",
        "In `tui/src/commands/plugins.ts`, replace the `KOSMOS_PLUGIN_REGISTRY` env-var stub (lines 32-51) with: emit `plugin_op_request:list` with fresh correlation_id → await matching `plugin_op_complete` + reassembled payload → parse `PluginListEntry[]` → return as `PluginEntry[]`.\n\n"
        "Reference: data-model.md § E5 + contracts/citizen-plugin-store.md § /plugins browser data flow.\n\n"
        "**Blocked by**: T021\n\n"
        "**Acceptance**: T030 bun test pass; manual `/plugins` open shows real backend state."
    ),
    Task(
        "T024", "[P] [US3] Extend PluginEntry shape with 6 additive fields",
        5, "US3", True, "S",
        "Extend `PluginEntry` type in `tui/src/components/plugins/PluginBrowser.tsx:26-33` with 6 additive optional fields: `tier`, `layer`, `trustee_org_name`, `install_timestamp_iso`, `search_hint_ko`, `search_hint_en`. Backwards compatible with existing Spec 1635 T065 tests.\n\n"
        "Reference: contracts/citizen-plugin-store.md § PluginEntry shape.\n\n"
        "**Blocked by**: T021\n\n"
        "**Acceptance**: T025 layout renders new columns; existing Spec 1635 T065 tests still pass."
    ),
    Task(
        "T025", "[US3] Render 6 new columns in PluginBrowser layout",
        5, "US3", False, "M",
        "Render the 6 new columns in `tui/src/components/plugins/PluginBrowser.tsx` layout (status glyph + name + version + tier badge + layer color glyph + description + active hint). Preserve ≥90% Spec 1635 T065 visual fidelity.\n\n"
        "Reference: contracts/citizen-plugin-store.md § Visual layout.\n\n"
        "**Blocked by**: T024\n\n"
        "**Acceptance**: bun test snapshot for 3 mixed-tier/layer entries passes."
    ),
    Task(
        "T026", "[P] [US3] Implement detail modal sub-component (i keystroke)",
        5, "US3", True, "M",
        "Implement detail modal sub-component (or extend existing `onDetail` callback's render path) in `tui/src/components/plugins/PluginDetail.tsx` (NEW) — renders manifest summary including PIPA acknowledgment SHA-256 for `processes_pii=true` plugins.\n\n"
        "Reference: contracts/citizen-plugin-store.md § Detail view.\n\n"
        "**Blocked by**: T021\n\n"
        "**Acceptance**: bun test verifies PII fields render for processes_pii=true; absent for processes_pii=false."
    ),
    Task(
        "T027", "[P] [US3] Implement remove confirmation modal (r keystroke)",
        5, "US3", True, "M",
        "Implement remove confirmation modal in `tui/src/components/plugins/PluginRemoveConfirm.tsx` (NEW) — Y emits `plugin_op_request:uninstall`.\n\n"
        "Reference: contracts/citizen-plugin-store.md § Remove confirmation.\n\n"
        "**Blocked by**: T021\n\n"
        "**Acceptance**: bun test verifies Y-press emits frame; N-press dismisses without emit."
    ),
    Task(
        "T028", "[P] [US3] Wire `a` keystroke deferred message",
        5, "US3", True, "S",
        "Wire `onMarketplace` callback in `tui/src/components/plugins/PluginBrowser.tsx:73,105` to render the deferred Korean message: `\"스토어 브라우저는 #1820 에서 작업 중입니다 (deferred)\"`.\n\n"
        "Reference: contracts/citizen-plugin-store.md § Keystroke contract `a`.\n\n"
        "**Blocked by**: T021\n\n"
        "**Acceptance**: bun test verifies a-press shows deferred message; never an empty no-op."
    ),
    Task(
        "T029", "[P] [US3] Implement in-flight install placeholder row",
        5, "US3", True, "M",
        "Implement in-flight install placeholder row in `tui/src/components/plugins/PluginBrowser.tsx`: when a `plugin_op_progress` frame arrives for a plugin not yet in the list, render `⏳ <name> ... (설치 중… 단계 N/7)`. Replace with real row when terminal `plugin_op_complete` arrives.\n\n"
        "Reference: contracts/citizen-plugin-store.md § In-flight install indicator.\n\n"
        "**Blocked by**: T021, T024\n\n"
        "**Acceptance**: bun test simulates progress frame stream; placeholder renders + converts to real row."
    ),
    Task(
        "T030", "[P] [US3] Author bun tests for PluginBrowser + plugins commands",
        5, "US3", True, "M",
        "Author bun tests `tui/src/components/plugins/PluginBrowser.test.tsx` + `tui/src/commands/plugins.test.ts`: 6 cases — renders 3 entries with mixed tier/layer + Space toggles isActive visually + r emits uninstall + a renders deferred message + i opens detail with PII fields + executePlugins round-trips list.\n\n"
        "Reference: contracts/citizen-plugin-store.md § Test seams.\n\n"
        "**Acceptance**: all 6 tests pass."
    ),
    # ── Phase 6: User Story 4 ──
    Task(
        "T031", "[P] [US4] Author fixture catalog + bundle + provenance under scripts/fixtures/",
        6, "US4", True, "M",
        "Author fixture catalog + bundle under `specs/1979-plugin-dx-tui-integration/scripts/fixtures/`: `catalog.json` (CatalogIndex schema with 1 entry pointing at file:// URLs), `seoul-subway.tar.gz` (containing `manifest.yaml` + `adapter.py` + minimal Pydantic v2 input/output schemas), `seoul-subway.intoto.jsonl` (SLSA provenance compatible with `KOSMOS_PLUGIN_SLSA_SKIP=true` test path).\n\n"
        "Reference: contracts/e2e-pty-scenario.md § L2 + spec/1636 contracts/manifest.schema.json.\n\n"
        "**Acceptance**: T032 stdio probe runs to completion against the fixture; install succeeds + receipt written."
    ),
    Task(
        "T032", "[P] [US4] L2 stdio JSONL probe script smoke-stdio.sh",
        6, "US4", True, "S",
        "Author L2 stdio JSONL probe `specs/1979-plugin-dx-tui-integration/scripts/smoke-stdio.sh` (executable shell script) that pipes raw `plugin_op_request` frames into backend stdio mode + captures the JSONL response stream → outputs `specs/1979-plugin-dx-tui-integration/smoke-stdio.jsonl`. Includes 4 inbound frames: list-before / install / permission-response / list-after / chat_request.\n\n"
        "Reference: contracts/e2e-pty-scenario.md § L2.\n\n"
        "**Acceptance**: jq filter `select(.kind == \"plugin_op\" and .op == \"complete\")` returns 2 frames (list-before + install)."
    ),
    Task(
        "T033", "[P] [US4] L3 expect script smoke-1979.expect + 3 negatives",
        6, "US4", True, "M",
        "Author L3 expect script `specs/1979-plugin-dx-tui-integration/scripts/smoke-1979.expect` driving the TUI under PTY (via `script(1)`) → outputs `smoke-1979.txt`. Covers happy path + 3 negative paths in sibling scripts: `smoke-1979-deny.expect` (consent N → exit_code=5), `smoke-1979-bad-name.expect` (catalog miss → exit_code=1), `smoke-1979-revoke.expect` (install + revoke + re-invoke fail-closed).\n\n"
        "Reference: contracts/e2e-pty-scenario.md § L3.\n\n"
        "**Acceptance**: grep for canonical phase markers (📡/📦/🔐/🧪/📝/🔄/📜/✓ 설치 완료/plugin\\.seoul_subway/⓵) returns ≥ 1 match each."
    ),
    Task(
        "T034", "[P] [US4] L4 vhs .tape script for visual demonstration",
        6, "US4", True, "S",
        "Author L4 vhs `.tape` script `specs/1979-plugin-dx-tui-integration/scripts/smoke-1979.tape` driving the citizen scenario for visual review. Output: `specs/1979-plugin-dx-tui-integration/smoke-1979.gif` (gitignored).\n\n"
        "Reference: contracts/e2e-pty-scenario.md § L4 + memory `feedback_vhs_tui_smoke`.\n\n"
        "**Acceptance**: `bun run vhs scripts/smoke-1979.tape` produces playable gif."
    ),
    Task(
        "T035", "[US4] Master orchestrator run-e2e.sh runs L1+L2+L3",
        6, "US4", False, "M",
        "Author master orchestrator `specs/1979-plugin-dx-tui-integration/scripts/run-e2e.sh`: runs L1 (`uv run pytest tests/ipc/ tests/plugins/ tests/e2e/` + `bun test --cwd tui`) + L2 (T032) + L3 (T033 happy path + 3 negatives) sequentially; reports SC-1..SC-4 evidence map. L4 is manual-only (`bun run vhs ...`).\n\n"
        "Reference: contracts/e2e-pty-scenario.md § Run conditions + § Acceptance evidence.\n\n"
        "**Blocked by**: T031, T032, T033\n\n"
        "**Acceptance**: full run completes ≤ 10min; outputs SC evidence map."
    ),
    # ── Phase 7: Polish ──
    Task(
        "T036", "[P] Update spec.md Deferred table with 4 new entries",
        7, "", True, "S",
        "Update `specs/1979-plugin-dx-tui-integration/spec.md` § \"Deferred to Future Work\" table with 4 new rows surfaced by research.md V1 + R-3/R-4 verdicts and analysis.md Risk C/D: (1) CC marketplace residue cleanup → Spec 1633-style follow-up Epic, (2) Plugin runtime enable/disable IPC → Post-P5 plugin-lifecycle Epic, (3) SC-001 live environment validation → Post-P5 fixture→live calibration, (4) Plugin list payload reassembly stress test (>50 plugins) → Post-P5 catalog scale Epic.\n\n"
        "Reference: research.md § Deferred Items Validation + analysis.md Risk inventory.\n\n"
        "**Acceptance**: 4 new rows present; each has tracking issue # filled in (post-/speckit-taskstoissues)."
    ),
    Task(
        "T037", "[P] Add .gitignore entry for smoke-1979.gif",
        7, "", True, "S",
        "Add `.gitignore` entry for `specs/1979-plugin-dx-tui-integration/smoke-1979.gif` (binary, > 1 MB risk per AGENTS.md hard rule).\n\n"
        "**Acceptance**: gif is not tracked; `git status` clean after vhs run."
    ),
    Task(
        "T038", "Run final quickstart.md validation",
        7, "", False, "S",
        "Run final `quickstart.md` validation manually: walk through the 5-step citizen scenario; confirm each step's expected output matches the prose mock-up; capture any discrepancies as bug fixes before PR.\n\n"
        "Reference: quickstart.md.\n\n"
        "**Acceptance**: 5 main steps + 3 branches all pass; PR ready."
    ),
]
# fmt: on


@dataclass(frozen=True)
class Deferred:
    title: str
    body: str


DEFERRED: list[Deferred] = [
    Deferred(
        "[Deferred] CC marketplace residue cleanup (commands/plugin/* + services/plugins/* + utils/plugins/*)",
        "## Originating Epic\n\n#1979 (Plugin DX TUI integration)\n\n"
        "## Deferral reason\n\n"
        "Epic #1979 swaps the `commands.ts:133` import to point at the KOSMOS singular `plugin.ts`, making the CC marketplace residue (`tui/src/commands/plugin/*`, `tui/src/services/plugins/*`, `tui/src/utils/plugins/*` — ~16 files, 89 grep matches) unreachable from citizen surface. Deleting the residue in Epic #1979 was rejected because:\n"
        "1. SC-005 baseline-parity (`bun test ≥ 984`) risk — ~89 grep matches across multiple files might cascade into test failures.\n"
        "2. Sub-issue budget — adding cleanup tasks would balloon the count past 90.\n\n"
        "## Target\n\n"
        "Spec 1633-style dead-code-elimination follow-up Epic. Verify all 89 matches removed; bun test parity preserved; CHANGELOG documents the residue removal.\n\n"
        "## Reference\n\n"
        "- specs/1979-plugin-dx-tui-integration/research.md § V1\n"
        "- memory `feedback_kosmos_scope_cc_plus_two_swaps`\n"
        "- Spec 1633 dead-code-elimination pattern"
    ),
    Deferred(
        "[Deferred] Plugin runtime enable/disable IPC (plugin_op_request:activate/deactivate)",
        "## Originating Epic\n\n#1979 (Plugin DX TUI integration)\n\n"
        "## Deferral reason\n\n"
        "Epic #1979 adds `_inactive: set[str]` shadow set to `ToolRegistry` (Phase 2 T005) but does NOT expose it via IPC. The PluginBrowser's ⏺/○ Space toggle is implemented as visual-only because adding a 4th `PluginOpFrame.request_op` value (`activate` / `deactivate`) would trigger:\n"
        "1. Spec 032 envelope schema bump\n"
        "2. New SHA-256 hash for the `kosmos.ipc.schema.hash` OTEL attribute\n"
        "3. Sub-issue budget overrun\n\n"
        "## Target\n\n"
        "Post-P5 plugin-lifecycle Epic. Adds `request_op ∈ {activate, deactivate}` to the discriminated union; updates Spec 032 envelope hash; wires PluginBrowser Space keystroke to backend IPC.\n\n"
        "## Reference\n\n"
        "- specs/1979-plugin-dx-tui-integration/research.md § R-3+R-4\n"
        "- specs/1979-plugin-dx-tui-integration/data-model.md § E4\n"
        "- docs/requirements/kosmos-migration-tree.md § UI-E.3"
    ),
    Deferred(
        "[Deferred] SC-001 live environment validation against kosmos-plugin-store",
        "## Originating Epic\n\n#1979 (Plugin DX TUI integration)\n\n"
        "## Deferral reason\n\n"
        "Epic #1979 SC-001 (≤30s install) is measured against fixture catalog under `file://` URLs only. Live network latency variance from the `kosmos-plugin-store` GitHub catalog + bundle download is not quantified. The fixture path is known to be ≤ 13s (analysis.md quickstart measurement); live network adds variance.\n\n"
        "## Target\n\n"
        "Post-P5 fixture→live calibration Epic. Measures SC-001 against actual `kosmos-plugin-store/seoul-subway` catalog + bundle URLs; calibrates the 30s ceiling against real network conditions.\n\n"
        "## Reference\n\n"
        "- specs/1979-plugin-dx-tui-integration/analysis.md Risk C\n"
        "- specs/1979-plugin-dx-tui-integration/spec.md SC-001"
    ),
    Deferred(
        "[Deferred] Plugin list payload reassembly stress test (>50 plugins)",
        "## Originating Epic\n\n#1979 (Plugin DX TUI integration)\n\n"
        "## Deferral reason\n\n"
        "Epic #1979 T020 / T023 implements `plugin_op_request:list` payload reassembly via Spec 032 `payload_start` / `payload_delta` / `payload_end` triplet. The MVP3 use case is 1-4 installed plugins. Spec 1636 SC-010 (200ms boot per plugin) implies catalogs may grow large; payload reassembly at >50 plugins is not stress-tested in this Epic.\n\n"
        "## Target\n\n"
        "Post-P5 catalog scale Epic. Stress-tests payload reassembly at 50/100/200/500 installed plugins; measures TTI for `/plugins` browser; potentially introduces pagination if needed.\n\n"
        "## Reference\n\n"
        "- specs/1979-plugin-dx-tui-integration/analysis.md Risk D\n"
        "- specs/1636-plugin-dx-5tier/spec.md SC-010"
    ),
]


def gh(*args: str, capture: bool = True) -> str:
    """Run gh CLI; return stdout."""
    cmd = ["gh", *args]
    result = subprocess.run(cmd, capture_output=capture, text=True, check=False)
    if result.returncode != 0:
        print(f"gh failed: {' '.join(cmd)}\nstderr: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    return result.stdout.strip()


def issue_body(t: Task) -> str:
    p_marker = "[P] (parallel-safe)" if t.parallel else "Sequential"
    story = t.story or "(none — Setup/Foundational/Polish)"
    return (
        f"## Task\n\n{t.body}\n\n"
        f"## Phase\n\nPhase {t.phase} ({phase_label(t.phase)})\n\n"
        f"## Story\n\n{story}\n\n"
        f"## Parallel-safe\n\n{p_marker}\n\n"
        f"## Size\n\n{t.size}\n\n"
        f"## Epic\n\nSub-issue of Epic #1979 (Plugin DX TUI integration)\n"
    )


def phase_label(n: int) -> str:
    return {
        1: "Setup",
        2: "Foundational",
        3: "User Story 1 — citizen install",
        4: "User Story 2 — citizen invokes plugin",
        5: "User Story 3 — citizen plugin browser",
        6: "User Story 4 — E2E PTY verification",
        7: "Polish",
    }[n]


def labels_for(t: Task) -> list[str]:
    labels = ["agent-ready", "epic-1979", f"phase-{t.phase}", f"size/{t.size}"]
    if t.story:
        labels.append("P1" if t.story in {"US1", "US2"} else "P2")
    if t.parallel:
        labels.append("parallel-safe")
    return labels


def ensure_labels(label_set: set[str]) -> None:
    """Create labels that don't exist yet (idempotent)."""
    existing_raw = gh("label", "list", "--repo", REPO, "--limit", "200", "--json", "name")
    existing = {row["name"] for row in json.loads(existing_raw)}
    needed = label_set - existing
    for label in sorted(needed):
        # Pick a reasonable default color
        color = {
            "agent-ready": "0E8A16",
            "epic-1979": "5319E7",
            "P1": "B60205",
            "P2": "FBCA04",
            "parallel-safe": "0075CA",
        }.get(label, "C5DEF5")
        try:
            gh("label", "create", label, "--repo", REPO, "--color", color, "--force")
            print(f"  Created label: {label}", file=sys.stderr)
        except SystemExit:
            pass


def create_issue(title: str, body: str, labels: list[str]) -> int:
    """Create issue + return issue number."""
    label_str = ",".join(labels) if labels else ""
    args = [
        "issue", "create",
        "--repo", REPO,
        "--title", title,
        "--body", body,
    ]
    if label_str:
        args.extend(["--label", label_str])
    url = gh(*args)
    # URL format: https://github.com/umyunsang/KOSMOS/issues/2208
    return int(url.rsplit("/", 1)[-1])


def get_issue_node_id(num: int) -> str:
    """Convert issue number to GraphQL node ID via REST."""
    return gh("api", f"repos/{REPO}/issues/{num}", "--jq", ".node_id")


def link_subissue(epic_id: str, sub_id: str) -> None:
    """Link sub_id as sub-issue of epic_id via GraphQL Sub-Issues API v2."""
    query = (
        "mutation($eid: ID!, $sid: ID!) { "
        "addSubIssue(input: {issueId: $eid, subIssueId: $sid}) { "
        "issue { number } subIssue { number } } }"
    )
    gh("api", "graphql", "-f", f"query={query}", "-F", f"eid={epic_id}", "-F", f"sid={sub_id}")


def main() -> None:
    print(f"Phase 1: Resolving Epic #{EPIC_NUM} GraphQL ID...", file=sys.stderr)
    epic_id = gh(
        "api", "graphql", "-f",
        f'query=query {{ repository(owner: "umyunsang", name: "KOSMOS") {{ issue(number: {EPIC_NUM}) {{ id }} }} }}',
        "--jq", ".data.repository.issue.id",
    )
    print(f"  Epic GraphQL ID: {epic_id}", file=sys.stderr)

    print("\nPhase 2: Ensuring labels exist...", file=sys.stderr)
    all_labels: set[str] = set()
    for t in TASKS:
        all_labels.update(labels_for(t))
    all_labels.update({"deferred", "deferred-from-1979", "needs-spec", "epic"})
    ensure_labels(all_labels)

    print("\nPhase 3: Creating 38 task issues + linking as sub-issues...", file=sys.stderr)
    task_results: list[tuple[Task, int, str]] = []  # (task, num, node_id)
    for t in TASKS:
        title = f"{t.task_id}: {t.title}"
        print(f"  Creating {t.task_id}...", file=sys.stderr, end=" ", flush=True)
        num = create_issue(title, issue_body(t), labels_for(t))
        node_id = get_issue_node_id(num)
        link_subissue(epic_id, node_id)
        print(f"#{num} → linked", file=sys.stderr)
        task_results.append((t, num, node_id))
        time.sleep(0.4)  # Mild rate-limit cushion

    print("\nPhase 4: Creating 4 deferred placeholder issues + linking as sub-issues...", file=sys.stderr)
    deferred_results: list[tuple[Deferred, int, str]] = []
    for d in DEFERRED:
        print("  Creating placeholder...", file=sys.stderr, end=" ", flush=True)
        num = create_issue(d.title, d.body, ["deferred", "deferred-from-1979", "needs-spec"])
        node_id = get_issue_node_id(num)
        link_subissue(epic_id, node_id)
        print(f"#{num} → linked", file=sys.stderr)
        deferred_results.append((d, num, node_id))
        time.sleep(0.4)

    print("\nPhase 5: Verifying sub-issue count...", file=sys.stderr)
    final_count = gh(
        "api", "graphql", "-f",
        f'query=query {{ repository(owner: "umyunsang", name: "KOSMOS") {{ issue(number: {EPIC_NUM}) {{ subIssues {{ totalCount }} }} }} }}',
        "--jq", ".data.repository.issue.subIssues.totalCount",
    )
    print(f"  Epic #{EPIC_NUM} now has {final_count} sub-issues (expected 42).", file=sys.stderr)

    # Emit machine-readable summary to stdout
    summary = {
        "epic_num": EPIC_NUM,
        "epic_id": epic_id,
        "tasks": [
            {"task_id": t.task_id, "issue_num": num, "title": t.title, "phase": t.phase, "story": t.story}
            for t, num, _nid in task_results
        ],
        "deferred": [
            {"issue_num": num, "title": d.title}
            for d, num, _nid in deferred_results
        ],
        "final_subissue_count": int(final_count),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
