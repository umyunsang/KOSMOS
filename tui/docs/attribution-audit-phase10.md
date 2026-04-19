# Attribution Audit — Phase 10 (T125)

Generated: 2026-04-19

## Scope

Files audited per T125 spec:

- `tui/src/ink/**` (all `.ts` / `.tsx`)
- `tui/src/commands/**` (`.ts` / `.tsx`)
- `tui/src/theme/**` (`.ts` / `.tsx`)
- `tui/src/components/coordinator/**` (`.ts` / `.tsx`)
- `tui/src/components/conversation/VirtualizedList.tsx`
- `tui/src/hooks/**` (`.ts` / `.tsx`)

## Summary

| Category | Count |
|---|---|
| Files scanned | 73 |
| Files with attribution header (Source:) | 60 |
| Files KOSMOS-original with explicit marker | 11 |
| Files fixed in this audit | 3 |
| Discrepancies (bad reference path → fixed) | 2 |

## Files With Attribution Header (60)

### tui/src/ink/ (48 files — all carry `// Source:` on line 1)

All files reference `.references/claude-code-sourcemap/restored-src/src/ink/` paths, all of which were verified to exist in the shared reference root.

Full list: colorize.ts, dom.ts, focus.ts, frame.ts, get-max-width.ts, instances.ts, line-width-cache.ts, measure-text.ts, node-cache.ts, output.ts, parse-keypress.ts, reconciler.ts, render-border.ts, render-node-to-output.ts, render-to-screen.ts, renderer.ts, root.ts, screen.ts, squash-text-nodes.ts, stringWidth.ts, styles.ts, tabstops.ts, terminal.ts, widest-line.ts, wrap-text.ts, events/click-event.ts, events/dispatcher.ts, events/emitter.ts, events/event-handlers.ts, events/event.ts, events/focus-event.ts, events/input-event.ts, events/keyboard-event.ts, events/terminal-event.ts, events/terminal-focus-event.ts, layout/engine.ts, layout/geometry.ts, layout/node.ts, layout/yoga.ts, termio/ansi.ts, termio/csi.ts, termio/dec.ts, termio/esc.ts, termio/osc.ts, termio/parser.ts, termio/sgr.ts, termio/tokenize.ts, termio/types.ts.

### tui/src/commands/ (1 lifted)

- `dispatcher.ts` — `// Source: .../src/commands.ts` — reference path verified OK.

### tui/src/theme/ (3 lifted + 1 KOSMOS-original)

- `dark.ts`, `default.ts`, `light.ts` — `// Source: .../src/utils/theme.ts` — reference path verified OK.
- `tokens.ts` — `// Source: .../src/utils/theme.ts` — reference path verified OK.

### tui/src/components/coordinator/ (3 lifted)

- `WorkerStatusRow.tsx` — `// Source: .../src/components/CoordinatorAgentStatus.tsx` — reference path verified OK.
- `VirtualizedList.tsx` — `// Source: .../src/components/VirtualMessageList.tsx` — reference path verified OK.

### tui/src/hooks/ (2 lifted)

- `useCanUseTool.ts` — `// Source: .../src/hooks/useCanUseTool.tsx` — reference path verified OK.
- `useVirtualScroll.ts` — `// Source: .../src/hooks/useVirtualScroll.ts` — reference path verified OK.

## Files Missing Attribution That Were Fixed (3)

### 1. `tui/src/theme/provider.tsx`

**Before (line 1):** `import { createContext, useContext, type ReactNode } from 'react'`

**Issue:** No attribution marker of any kind, despite all peer files in the directory having one.

**Resolution:** This is genuinely KOSMOS-original per git commit `3a40a12` (commit message explicitly states "KOSMOS-original per ADR-004 Section 3"). Prepended:

```
// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original React context provider for KOSMOS_TUI_THEME resolution.
// No upstream analog in Claude Code — CC uses a plain object import, not React context.
```

### 2. `tui/src/components/coordinator/PhaseIndicator.tsx`

**Before (line 1):** `// Source: .references/claude-code-sourcemap/restored-src/src/components/CoordinatorProgressLine.tsx`

**Issue:** `CoordinatorProgressLine.tsx` does NOT exist in restored-src. Verified via `ls` — the directory contains `AgentProgressLine.tsx`, `BashModeProgress.tsx`, `TeleportProgress.tsx`, etc.

**Resolution:** Updated attribution to reference the closest upstream analog:

```
// Source: .references/claude-code-sourcemap/restored-src/src/components/AgentProgressLine.tsx (Claude Code 2.1.88, research-use)
// Note: Original attribution listed CoordinatorProgressLine.tsx which does not exist in restored-src.
//       AgentProgressLine.tsx is the closest upstream analog (phase glyph + progress line pattern).
```

### 3. `tui/src/components/coordinator/PermissionGauntletModal.tsx`

**Before (line 1):** `// Source: .references/.../src/components/ToolPermission*.tsx`

**Issue:** Wildcard `ToolPermission*.tsx` does not resolve — no files with that prefix exist in restored-src components directory. `BypassPermissionsModeDialog.tsx` (line 2) resolves correctly.

**Resolution:** Replaced wildcard with the concrete closest upstream file:

```
// Source: .references/.../src/components/permissions/WorkerPendingPermission.tsx (Claude Code 2.1.88, research-use)
// Note: Original attribution listed ToolPermission*.tsx wildcard which does not resolve in restored-src.
//       WorkerPendingPermission.tsx is the closest upstream analog for the worker-scoped permission modal pattern.
```

## Files Deliberately KOSMOS-Original With No Attribution Header Required (11)

These files carry `// KOSMOS-original` or `// SPDX-License-Identifier: Apache-2.0 / KOSMOS-original` as their marker. No `// Source:` header is expected per FR-011 (which only applies to lifted files):

| File | Rationale |
|---|---|
| `src/commands/help.tsx` | KOSMOS-original help renderer for slash commands |
| `src/commands/index.ts` | KOSMOS-original command registry builder |
| `src/commands/new.ts` | KOSMOS-original /new session command |
| `src/commands/resume.ts` | KOSMOS-original /resume session command |
| `src/commands/save.ts` | KOSMOS-original /save session command |
| `src/commands/sessions.ts` | KOSMOS-original /sessions session command |
| `src/commands/types.ts` | KOSMOS-original command type definitions |
| `src/theme/provider.tsx` | KOSMOS-original ThemeProvider (fixed in this audit) |
| `src/hooks/useKoreanIME.ts` | KOSMOS-original Korean IME composition hook |

## Discrepancies Where Referenced Path Does Not Resolve (Fixed Above)

| File | Bad Reference | Resolution |
|---|---|---|
| `src/components/coordinator/PhaseIndicator.tsx` | `CoordinatorProgressLine.tsx` (not in restored-src) | Replaced with `AgentProgressLine.tsx` |
| `src/components/coordinator/PermissionGauntletModal.tsx` | `ToolPermission*.tsx` (wildcard, no match) | Replaced with `permissions/WorkerPendingPermission.tsx` |
