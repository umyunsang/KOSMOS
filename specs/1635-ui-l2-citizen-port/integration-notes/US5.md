# US5 Integration Notes — Auxiliary Surfaces (T060-T072)

**Author**: Frontend Developer Teammate #5
**Date**: 2026-04-25
**Branch**: `feat/1635-ui-l2-citizen-port`
**Epic**: #1635 P4 UI L2 Citizen Port

---

## Tasks Completed

| Task | Status | Description |
|------|--------|-------------|
| T060 [P] | DONE | `HelpV2Grouped.tsx` — 4-group help rendering consuming `groupCatalog(UI_L2_SLASH_COMMANDS)` |
| T061 | DONE | `commands/help.ts` — `/help` command with `executeHelp(locale)`, emits `surface=help` |
| T062 [P] | DONE | `ConfigOverlay.tsx` — inline overlay for non-secret settings with lock indicator for secrets |
| T063 [P] | DONE | `EnvSecretIsolatedEditor.tsx` — masked secret input, no plaintext echo, isolated confirm/cancel |
| T064 | DONE | `commands/config.ts` — `/config` command with `KOSMOS_CONFIG_CATALOG`, `executeConfig()`, `applyConfigChanges()` |
| T065 [P] | DONE | `PluginBrowser.tsx` — `⏺`/`○` status + Space/i/r/a keybindings |
| T066 | DONE | `commands/plugins.ts` — `/plugins` command, reads `KOSMOS_PLUGIN_REGISTRY` env |
| T067 [P] | DONE | `ExportPdfDialog.tsx` — pdf-lib PDF assembly with `sanitizeForExport()` SC-012 guard |
| T068 | DONE | `commands/export.ts` — `/export` command, writes to `~/Downloads/` |
| T069 [P] | DONE | `HistorySearchDialog.tsx` — 3-filter form with `applyHistoryFilters()` AND composition |
| T070 | DONE | `commands/history.ts` — `/history` command, reads from `~/.kosmos/memdir/user/sessions/` |
| T071 [P] | DONE | All bun:test units — 91 tests, 0 failures, SC-012 assertion passes |
| T072 | DEFERRED to Lead | OTEL surface activation is called inside each command handler (see calls placed below) |

---

## Files Created

### Components
- `/Users/um-yunsang/KOSMOS/tui/src/components/help/HelpV2Grouped.tsx`
- `/Users/um-yunsang/KOSMOS/tui/src/components/config/ConfigOverlay.tsx`
- `/Users/um-yunsang/KOSMOS/tui/src/components/config/EnvSecretIsolatedEditor.tsx`
- `/Users/um-yunsang/KOSMOS/tui/src/components/plugins/PluginBrowser.tsx`
- `/Users/um-yunsang/KOSMOS/tui/src/components/export/ExportPdfDialog.tsx`
- `/Users/um-yunsang/KOSMOS/tui/src/components/history/HistorySearchDialog.tsx`

### Commands
- `/Users/um-yunsang/KOSMOS/tui/src/commands/help.ts`
- `/Users/um-yunsang/KOSMOS/tui/src/commands/config.ts`
- `/Users/um-yunsang/KOSMOS/tui/src/commands/plugins.ts`
- `/Users/um-yunsang/KOSMOS/tui/src/commands/export.ts`
- `/Users/um-yunsang/KOSMOS/tui/src/commands/history.ts`

### Tests
- `/Users/um-yunsang/KOSMOS/tui/tests/components/help/HelpV2Grouped.test.ts`
- `/Users/um-yunsang/KOSMOS/tui/tests/components/config/ConfigOverlay.test.ts`
- `/Users/um-yunsang/KOSMOS/tui/tests/components/plugins/PluginBrowser.test.ts`
- `/Users/um-yunsang/KOSMOS/tui/tests/components/export/ExportPdfDialog.test.ts` (SC-012 gate)
- `/Users/um-yunsang/KOSMOS/tui/tests/components/history/HistorySearchDialog.test.ts`
- `/Users/um-yunsang/KOSMOS/tui/tests/commands/help.test.ts`
- `/Users/um-yunsang/KOSMOS/tui/tests/commands/config.test.ts`
- `/Users/um-yunsang/KOSMOS/tui/tests/commands/plugins.test.ts`
- `/Users/um-yunsang/KOSMOS/tui/tests/commands/export.test.ts`
- `/Users/um-yunsang/KOSMOS/tui/tests/commands/history.test.ts`

---

## emitSurfaceActivation Calls Placed (T072)

Each command handler calls `emitSurfaceActivation()` from `tui/src/observability/surface.ts` at the start of execution:

| Command | Surface Value | Location |
|---------|--------------|----------|
| `/help` | `'help'` | `commands/help.ts:executeHelp()` line 43 |
| `/config` | `'config'` | `commands/config.ts:executeConfig()` line 73 |
| `/plugins` | `'plugins'` | `commands/plugins.ts:executePlugins()` line 32 |
| `/export` | `'export'` | `commands/export.ts:executeExport()` line 65 |
| `/history` | `'history'` | `commands/history.ts:executeHistory()` line 63 |

### What Lead Still Needs to Do for T072

1. **Wire commands into the REPL command dispatcher** (`tui/src/screens/REPL.tsx` or the command routing layer). The command handlers (`executeHelp`, `executeConfig`, `executePlugins`, `executeExport`, `executeHistory`) are pure functions that return data. The REPL dispatcher needs to call them and mount the corresponding components.

2. **Mount components from command results**: Each command returns a result that maps to a React component:
   - `executeHelp()` → mount `<HelpV2Grouped />`
   - `executeConfig()` → mount `<ConfigOverlay />` or `<EnvSecretIsolatedEditor />` depending on `openSecretEditorFor`
   - `executePlugins()` → mount `<PluginBrowser />`
   - `executeExport()` → mount `<ExportPdfDialog />`
   - `executeHistory()` → mount `<HistorySearchDialog />`

3. **Register commands in the command catalog** (`tui/src/commands/catalog.ts` already has the entries; the REPL dispatcher needs to route `/help`, `/config`, `/plugins`, `/export`, `/history` to the handlers).

4. **Verify `emitSurfaceActivation` trace ingestion** via Langfuse — confirm `kosmos.ui.surface=help` (etc.) appears in spans after running `/help` in `bun run tui`.

---

## Test Results

```
bun test v1.3.12 (700fc117)
 91 tests pass, 0 fail
 All US5 test files: 10 files
```

### SC-012 PDF Leakage Assertion

**Status: PASS**

The `sanitizeForExport()` function in `ExportPdfDialog.tsx` strips:
- `traceId=[A-Za-z0-9]+` → `[redacted]`
- `spanId=[A-Za-z0-9]+` → `[redacted]`
- `pluginInternal:[^\s]*` → `[redacted]`

Test coverage: 20 sample sessions simulated in `ExportPdfDialog.test.ts`:
- 10 clean texts → passed unchanged
- 5 texts with embedded OTEL markers → stripped correctly
- 5 edge cases (Korean-only, receipt IDs, empty) → no false-positive redaction

SC-012 grep assertion command (manual verification):
```bash
# After running /export in bun run tui:
grep -E 'traceId=|spanId=|pluginInternal:' ~/Downloads/kosmos-export_*.pdf
# Expected: no output (zero matches)
```

---

## Typecheck Results

Zero typecheck errors in US5 files (verified via `bun x tsc --noEmit --skipLibCheck`).
Pre-existing CC upstream typecheck errors (3240 total) are unrelated and unchanged.

---

## FR Compliance

| FR | Status | Notes |
|----|--------|-------|
| FR-029 | DONE | `/help` 4-group output from catalog SSOT |
| FR-030 | DONE | `/config` overlay + `.env` secret isolation |
| FR-031 | DONE | `/plugins` with `⏺`/`○` + Space/i/r/a keybindings |
| FR-032 | DONE | `/export` PDF via pdf-lib, SC-012 zero-leak guard |
| FR-033 | DONE | `/history` 3-filter AND composition |
| FR-037 | DONE | `emitSurfaceActivation()` placed in all 5 command handlers |

---

## Deferred (T072 is DEFERRED to Lead)

T072 OTEL wiring is considered complete at the command-handler level. The Lead needs to:
1. Wire the command functions into REPL.tsx dispatcher
2. Verify Langfuse surface span ingestion in integration testing
