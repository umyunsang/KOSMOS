# Implementation Plan: Plugin DX TUI integration (Spec 1636 closure)

**Branch**: `feat/1979-plugin-dx-tui-integration` | **Date**: 2026-04-28 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/1979-plugin-dx-tui-integration/spec.md`

## Summary

Close the integration loop between Spec 1636's shipped backend `installer.py:install_plugin()` 8-phase implementation and the citizen-facing TUI. Today, `tui/src/commands/plugin.ts` (singular, KOSMOS-aware) is orphaned — `tui/src/commands.ts:133` registers `tui/src/commands/plugin/index.tsx` (CC marketplace residue with `aliases: ['plugins', 'marketplace']`) under the `/plugin` slash command, hijacking the `/plugins` browser surface as well. The 20th IPC arm `PluginOpFrame` (Spec 1636 + Spec 032) is fully defined with shape validators but has zero backend emit. Epic #1978 closure (verified: `git log` shows `cc4f4a2 / 910b7c5 / 1e295aa / 692d1c3` on main) means `ChatRequestFrame.tools[]` already auto-refreshes from `ToolRegistry.export_core_tools_openai()` on every turn, so plugin tool inventory propagation is automatic once the registry is updated by `register_plugin_adapter`.

**Technical approach**:
1. Replace the `tui/src/commands.ts:133` import to point to KOSMOS `./commands/plugin.js` (singular). The CC marketplace residue (`commands/plugin/`, `services/plugins/`, `utils/plugins/`) becomes unreachable from citizen surface but is **not** deleted in this Epic — defer cleanup to a Spec 1633-style follow-up to preserve `bun test` parity (SC-005). Decision rationale and cleanup boundary documented in `research.md § V1`.
2. Add a `frame.kind == "plugin_op"` arm at `src/kosmos/ipc/stdio.py:1675` if-elif dispatch chain. The handler routes `op="request"` frames to a new `PluginOpDispatcher` that wraps `installer.py:install_plugin()` / uninstall handler / list handler with progress + consent IPC bridges.
3. Replace `installer.py:_default_consent_prompt` (current "deny by default" stub) with an `IPCConsentBridge` callable that emits a `permission_request` frame (Spec 1978 wiring) and awaits the citizen's Y / A / N decision via `asyncio.wait_for(... timeout=60)` (matches the existing permission_response pattern at `stdio.py:814`).
4. Wire `tui/src/commands/plugins.ts` (existing T066 entry point — Spec 1635) to populate `PluginEntry[]` from a `plugin_op_request:list` round-trip rather than the current `KOSMOS_PLUGIN_REGISTRY` env-var stub.
5. Add a `_inactive: set[str]` shadow set to `ToolRegistry` so the ⏺/○ toggle (UI-E.3 mandate) can deactivate without uninstalling. BM25 corpus rebuild + `export_core_tools_openai()` filter on `_inactive`. No manifest schema change.
6. Build a 4-layer PTY-driven E2E scenario (`smoke-1979.tape`, `smoke-1979.expect`, `smoke-1979.stdio.sh`, `tests/`) producing grep-friendly artifacts under `specs/1979-plugin-dx-tui-integration/`.

Zero new runtime dependencies. ToolRegistry change is in-memory only. ~28 tasks projected, well under the ≤90 sub-issue cap.

## Technical Context

**Language/Version**: Python 3.12+ (backend, existing project baseline; no version bump). TypeScript 5.6+ on Bun v1.2.x (TUI, existing Spec 287 + 1635 stack; no version bump).
**Primary Dependencies**: All existing — `pydantic >= 2.13` (frozen models for `PluginManifest`, `PluginOpFrame`; existing); `pydantic-settings >= 2.0` (env catalog including `KOSMOS_PLUGIN_*`; existing); `httpx >= 0.27` (Spec 1636 `_default_catalog_fetcher` / `_default_bundle_fetcher`; existing); `opentelemetry-sdk` + `opentelemetry-semantic-conventions` (Spec 021 spans + `kosmos.plugin.id` attribute; existing); `pytest` + `pytest-asyncio` (existing test stack); `pyyaml` (manifest YAML; existing). TS side: existing `ink`, `react`, `@inkjs/ui`, `string-width`, Bun stdlib + `crypto.randomUUID()`. **Zero new runtime dependencies** (AGENTS.md hard rule + spec FR-023 + SC-006).
**Storage**: N/A at runtime for state added by this Epic. The new ToolRegistry `_inactive: set[str]` is in-memory only, lost on restart (consistent with existing registry boot-time rebuild). Plugin install state continues to live at `~/.kosmos/memdir/user/plugins/<plugin_id>/` (Spec 1636); consent receipts at `~/.kosmos/memdir/user/consent/` (Spec 035 / Spec 1636); audit ledger via Spec 024 unchanged.
**Testing**: `pytest` + `pytest-asyncio` for backend dispatcher + IPCConsentBridge unit tests; `bun test` for TUI command + browser data-binding tests. PTY-driven E2E via `expect` / `script` / `vhs` per `docs/testing.md § TUI verification methodology` 4-layer ladder.
**Target Platform**: Linux + macOS terminals (Bun v1.2.x runtime; existing Spec 287 baseline). No Windows-specific path.
**Project Type**: Conversational multi-agent platform. Backend = Python `kosmos.*` packages over stdio JSONL; TUI = Bun + Ink React.
**Performance Goals**: SC-001 install ≤ 30 s wall-clock (Spec 1636 SC-005 ceiling). SC-002 tool-inventory propagation ≤ 3 s after `plugin_op_complete`. No new perf budgets.
**Constraints**: SC-005 baseline parity `bun test ≥ 984` / `uv run pytest ≥ 3458`. SC-006 zero new runtime deps. SC-007 ≤ 90 sub-issues.
**Scale/Scope**: ~28 tasks across 6 phases (A–F). Affects ~6 files in `src/kosmos/ipc/` + `src/kosmos/plugins/` + ~4 files in `tui/src/commands/` + `tui/src/screens/REPL.tsx` integration.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Status | Evidence |
|---|---|---|
| **§I Reference-Driven Development** | ✅ PASS | 10 references cited in spec.md `Input` field; `research.md § R-1..R-6` maps each design decision to source. CC sourcemap `restored-src/src/services/plugins/*` consulted as residue baseline (V1 verdict). |
| **§II Fail-Closed Security** | ✅ PASS | FR-005 (failed install leaves zero state), FR-013 (revocation fail-closed), edge case "consent_prompt timeout = denial". `IPCConsentBridge` defaults to deny on `asyncio.wait_for` `TimeoutError`. |
| **§III Pydantic v2 Strict Typing** | ✅ PASS | All new entities (`PluginOpDispatcher`, `IPCConsentBridge`) use existing Pydantic v2 frame models (`PluginOpFrame`, `PermissionRequestFrame`). No new schemas; no `Any`. |
| **§IV Government API Compliance** | ✅ PASS | FR-026 forbids live `data.go.kr` in CI. Tests use `file://` catalog + fixture bundles per `installer.py:_default_catalog_fetcher`. No `KOSMOS_*` key handling change. |
| **§V Policy Alignment** | ✅ PASS | PIPA §26 trustee SHA-256 round-trip preserved (FR-012). Public AI Impact Assessment 7-step gauntlet honoured (FR-011). Korea AI Action Plan Principle 8 (single conversational window) — citizen never leaves the TUI to install or invoke a plugin. |
| **§VI Deferred Work Accountability** | ✅ PASS | spec.md § Scope Boundaries lists 8 Permanent OOS + 6 Deferred items. Each deferred item has `Tracking Issue` (`#585`, `#1820`, `#1926`, `#1980`, plus 2 `NEEDS TRACKING` resolved by `/speckit-taskstoissues`). Zero unregistered "future epic" / "v2" / "Phase N" prose patterns. |

**Initial Constitution Check: PASS — proceed to Phase 0.**

## Project Structure

### Documentation (this feature)

```text
specs/1979-plugin-dx-tui-integration/
├── plan.md                       # This file (/speckit-plan output)
├── spec.md                       # /speckit-specify output
├── research.md                   # Phase 0 — V1/V2 verdicts + R-1..R-6
├── data-model.md                 # Phase 1 — PluginOpDispatcher / IPCConsentBridge / shadow set
├── quickstart.md                 # Phase 1 — 5-min citizen walkthrough
├── contracts/                    # Phase 1
│   ├── dispatcher-routing.md     # plugin_op_request → install/uninstall/list contract
│   ├── consent-bridge.md         # _default_consent_prompt → IPC round-trip + 60s timeout
│   ├── citizen-plugin-store.md   # /plugins browser data binding + UI-E.3 keystrokes
│   └── e2e-pty-scenario.md       # 4-layer ladder artifact conventions
├── checklists/
│   └── requirements.md           # /speckit-specify validation checklist
└── tasks.md                      # /speckit-tasks output (NOT created by this command)
```

### Source Code (repository root)

```text
src/kosmos/
├── ipc/
│   ├── stdio.py                  # Add plugin_op arm at line ~1675 if-elif chain
│   ├── frame_schema.py           # No change — PluginOpFrame already defined at 776-936
│   └── plugin_op_dispatcher.py   # NEW — wraps install_plugin / uninstall_plugin / list_plugins
├── plugins/
│   ├── installer.py              # Modify: _default_consent_prompt no-op replaced by IPCConsentBridge wiring (no signature change — same Callable shape)
│   ├── registry.py               # No change to register_plugin_adapter / auto_discover
│   ├── consent_bridge.py         # NEW — IPCConsentBridge class wrapping permission_request frame round-trip
│   └── uninstall.py              # NEW — uninstall_plugin(plugin_id, registry, executor) function
└── tools/
    └── registry.py               # Add _inactive: set[str] + set_active / is_active methods + filter in to_openai_tool / all_tools / BM25 rebuild

tui/src/
├── commands.ts                   # Modify line 133: import KOSMOS plugin from './commands/plugin.js' (singular)
├── commands/
│   ├── plugin.ts                 # No change — already emits sendPluginOp; remove H7 deferred suffix from acknowledgement strings
│   ├── plugins.ts                # Modify: replace KOSMOS_PLUGIN_REGISTRY env-var stub with plugin_op_request:list IPC round-trip
│   └── plugin/                   # CC marketplace residue — unreachable after commands.ts:133 swap; documented for future cleanup Epic
├── components/
│   └── plugins/
│       └── PluginBrowser.tsx     # No change — Spec 1635 T065 already KOSMOS-aligned; receives PluginEntry[] from plugins.ts
├── ipc/
│   └── bridge.ts                 # No change — plugin_op already routes through existing envelope; verify codec.ts handles it
└── screens/
    └── REPL.tsx                  # No change — Spec 1635 already mounts PluginBrowser at line ~3490

tests/
├── ipc/
│   ├── test_plugin_op_dispatch.py        # NEW — frame.kind == "plugin_op" routing
│   └── test_consent_bridge.py            # NEW — 60s timeout = denial; Y/A/N → grant_once / grant_session / deny
├── plugins/
│   ├── test_uninstall.py                 # NEW — uninstall_plugin(): rmtree + deregister + BM25 rebuild + uninstall receipt
│   └── test_registry_inactive_set.py     # NEW — set_active(False) → BM25 + export filter
└── e2e/
    └── test_plugin_install_e2e.py        # NEW — fixture catalog + bundle → install → tool inventory → invoke
```

**Structure Decision**: Single project layout (already established for KOSMOS). Backend additions concentrated in `src/kosmos/ipc/` + `src/kosmos/plugins/` + one method addition to `src/kosmos/tools/registry.py`. TUI additions are minimal: one import swap + one command-handler logic replacement. No new top-level packages.

## Complexity Tracking

> No constitution violations to track. All gates PASS.

The two judgment calls deserving documentation (per FR-018 / Assumption A6):

| Decision | Why kept simple | Simpler alternative rejected because |
|----------|----------------|--------------------------------------|
| V1 — Don't delete CC marketplace residue in this Epic; only swap `commands.ts:133` import | 89 grep matches across 16+ files; deleting risks SC-005 baseline-parity (`bun test ≥ 984`) and triggers a separate-Epic-worthy review surface. | "Delete everything now" rejected because it conflates two scope-distinct concerns (citizen activation vs dead-code cleanup) and would balloon the sub-issue count past 90. Defer to a Spec 1633-style follow-up Epic. |
| V2 — Use existing `PluginBrowser.tsx` (Spec 1635 T065) verbatim; only rewire data source in `commands/plugins.ts` | The existing component is already KOSMOS-aligned with `PluginEntry` shape, ⏺/○ glyphs, Space/i/r/a keystrokes, Korean-primary i18n, and `kosmos.ui.surface=plugins` OTEL emission. | "Build a new `CitizenPluginStore.tsx`" rejected because the existing component matches every UI-E.3 spec line. Authoring a parallel component would duplicate logic and introduce drift risk between the two surfaces. |
