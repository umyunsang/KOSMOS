# KOSMOS Current TUI Tree Map

**Source**: `find tui/src/components -type f \( -name "*.tsx" -o -name "*.ts" \)` on 2026-04-20 at KOSMOS HEAD `34c48f4`.
**Consumer**: T010–T014 (`KOSMOS target` column for PORT/REWRITE rows).

## 1 · Current tree (26 files across 4 subdirs)

### `tui/src/components/conversation/` (3 files)

- `MessageList.tsx`
- `StreamingMessage.tsx`
- `VirtualizedList.tsx`

### `tui/src/components/coordinator/` (3 files)

- `PermissionGauntletModal.tsx` ← delivered by Epic B #1297 / PR #1441
- `PhaseIndicator.tsx`
- `WorkerStatusRow.tsx`

### `tui/src/components/input/` (1 file)

- `InputBar.tsx`

### `tui/src/components/primitive/` (18 files — Spec 287 citizen-domain primitives, Part D-3 carve-outs per FR-033)

- `AddressBlock.tsx`, `AdmCodeBadge.tsx`, `AuthContextCard.tsx`, `AuthWarningBanner.tsx`, `CollectionList.tsx`, `CoordPill.tsx`, `DetailView.tsx`, `ErrorBanner.tsx`, `EventStream.tsx`, `index.tsx`, `POIMarker.tsx`, `PointCard.tsx`, `StreamClosed.tsx`, `SubmitErrorBanner.tsx`, `SubmitReceipt.tsx`, `TimeseriesTable.tsx`, `types.ts`, `UnrecognizedPayload.tsx`

### Root (1 file)

- `CrashNotice.tsx`

**Total**: 26 files.

## 2 · CC → KOSMOS target-directory mapping (PORT/REWRITE column hint)

| CC family | KOSMOS target parent | Rationale |
|---|---|---|
| `messages/*` (streaming, message row, envelope) | `tui/src/components/conversation/` | existing conversation bucket |
| `PromptInput/*`, `BaseTextInput.tsx`, `TextInput.tsx` | `tui/src/components/input/` | existing input bucket (will expand) |
| `permissions/*`, `TrustDialog/*`, `Passes/*` (permission gauntlet) | `tui/src/components/coordinator/` | existing coordinator bucket hosts `PermissionGauntletModal` |
| `design-system/*`, `ui/*`, `Spinner/*`, `LogoV2/*`, `StructuredDiff/*`, `diff/*`, `HighlightedCode/*` | `tui/src/components/chrome/` ← **new subdir created on first PORT** | low-level visual primitives |
| `CustomSelect/*`, `HelpV2/*`, `root.dialogs/*` (citizen-facing pickers/dialogs) | `tui/src/components/dialogs/` ← **new subdir** | dialog/picker bucket |
| `Settings/*`, `Onboarding.tsx`, `wizard/*`, `root.onboarding` | `tui/src/components/onboarding/` ← **new subdir** (Epic H territory) | Epic H + K convergence point |
| `root.shortcuts/*` | `tui/src/components/shortcuts/` ← **new subdir** (Epic I territory) | Epic I shortcut Tier 1 |
| `tasks/*`, `agents/*` (swarm HUD) | `tui/src/components/coordinator/` | existing coordinator bucket |
| `mcp/*` (harness-level) | `tui/src/components/mcp/` ← **new subdir** (Epic M or TBD) | limited surface; per-verdict case-by-case |
| `memory/*`, `hooks/*` | `tui/src/components/` root or `tui/src/hooks/` | case-by-case; some may be hooks not components |

**Convention** (applied by classifiers):

- When a new top-level subdir is needed (e.g., `chrome/`, `dialogs/`, `onboarding/`, `shortcuts/`, `mcp/`), spell the path in the `KOSMOS target` column and note in rationale: `creates new subdir tui/src/components/<X>/ (first PORT into family)`.
- When a file belongs in an existing subdir, spell the full target path (e.g., `tui/src/components/conversation/MessageRow.tsx`).

## 3 · Closed-Epic reality checks (for T012)

### B #1297 (permission) → already delivered

`PermissionGauntletModal.tsx` at `tui/src/components/coordinator/PermissionGauntletModal.tsx` ships Epic B. Catalog rows for the `permissions/` family must decide per-file:

- **PORT, implementation complete**: the one KOSMOS file that already exists covers CC's core dialog surface. Mark `—` Task sub-issue.
- **REWRITE, re-parent to M**: the 50 other `permissions/*` files (rule store, hooks, preflight menus, settings surfaces) that Epic B did NOT ship → re-parented to M per §R3.

### A #1298 (IPC) → no component files delivered

IPC hardening lives in `src/kosmos/ipc/` (backend) and TUI-side `src/ipc/`. CC has no `components/ipc/*` family; A is not a likely Owning Epic for any `src/components/*` file. If a row nonetheless cites A (e.g., a component rendering connection status), apply §R3 re-parent.

## 4 · Part D-3 carve-out reminder (FR-033)

`tui/src/components/primitive/*` (18 files listed in §1) are KOSMOS-original citizen-domain primitives from Spec 287. They have **no CC analog** and do **not** appear in the catalog. Reverse-check only: no CC component should have `KOSMOS target = tui/src/components/primitive/<X>.tsx`.
