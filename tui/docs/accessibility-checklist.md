# Accessibility Checklist

**Spec**: Spec 287 (KOSMOS TUI — Ink + React + Bun)
**Status**: T123 keyboard-only navigation pass completed 2026-04-19. T124 screen-reader smoke plan appended 2026-04-19. Items remain unchecked until manual execution.
**Requirements**: FR-055 (keyboard-only navigation), FR-056 (screen-reader manual smoke test).

---

## Keyboard-only Navigation Audit Table (FR-055, T123)

Audited 2026-04-19. For each component, actual behavior is derived from reading the source file. No speculation. Components that do not yet have a keyboard-interactive surface are marked "Not applicable" or listed under "Deferred surfaces".

| Component | File | Interactions | Keyboard-reachable? | Escape to cancel? | Notes |
|-----------|------|-------------|---------------------|-------------------|-------|
| `PermissionGauntletModal` | `tui/src/components/coordinator/PermissionGauntletModal.tsx` | `y`/`Y` to grant, `n`/`N` or `Escape` to deny | Yes — `useInput` installs on mount, receives all keystrokes while modal is visible | Yes — `key.escape` triggers `deny()` and emits `permission_response: denied` | No Tab cycle between buttons; modal surface is single-decision (y/n/Escape), not a two-button focus cycle. The skeleton checklist expected Tab-cycling; ACTUAL code has none. Followup: add Tab focus ring if FR-055 requires explicit button tabbing. Color-only risk indicator (`riskBorderColor`) has no non-visual signal — see Known Issues. |
| `InputBar` | `tui/src/components/input/InputBar.tsx` | Enter to submit (guarded by `!ime.isComposing`); Backspace delegated to `useKoreanIME`; all input suppressed when `disabled=true` | Yes — active by default, suppressed only when the permission modal is open | Not applicable (not a modal; no cancel action) | Korean IME mid-composition Enter is correctly blocked by `ime.isComposing` guard. `disabled` prop is the mechanism for the permission-modal gate (FR-046). No Escape handler in `InputBar` itself — Escape is not a meaningful action on a single-line text input in this TUI. |
| `CollectionList` "Load more" | `tui/src/components/primitive/CollectionList.tsx` | Renders up to 50 items then a truncation notice | No keyboard-reachable "Load more" affordance — truncation is displayed as static text (`… N more items`), not an interactive button | Not applicable (no button exists) | FR-019 specifies a "Load more" button that emits a follow-up `lookup(mode="fetch", page=...)` IPC frame. The current implementation truncates at `MAX_ITEMS = 50` with a static count text and no interactive affordance. This is a gap vs FR-019 and FR-055. Followup: implement a keyboard-focusable "Load more" control. |
| Session list `<Select />` | `tui/src/commands/sessions.ts` + `tui/src/components/` | `sessions.ts` emits a `session_event: "list"` IPC frame only; no UI component renders the returned list | Not wired to any UI yet | Not applicable | The `/sessions` command sends the list request via IPC but there is no `<Select />` or other rendering component for the returned session list in `tui/src/components/`. This surface is deferred (see below). |
| Slash-command auto-complete | `tui/src/commands/dispatcher.ts` + `tui/src/components/input/InputBar.tsx` | Dispatcher handles slash-prefixed input; no auto-complete suggestion list in source | Not applicable (feature not implemented) | Not applicable | No auto-complete UI component exists. Skeleton checklist item is aspirational/deferred. |
| Ctrl-C SIGTERM | `tui/src/entrypoints/tui.tsx` | Process-level signal; not a component interaction | Yes — Ctrl-C is handled at process level, not blocked by any component | Not applicable | FR-009 compliance depends on `tui.tsx` wiring; confirmed `PermissionGauntletModal` does not intercept Ctrl-C (it only consumes y/n/Escape via `useInput`). |

### Deferred surfaces

The following interactive surfaces appear in the skeleton checklist or spec but are not yet implemented as keyboard-navigable UI components in `tui/src/`. Do not mark these as passing until the code ships.

- **Session list `<Select />` (US2 / FR-038)**: The `/sessions` command emits an IPC request but the returned list has no rendered interactive component. Once a `<Select />` (from `@inkjs/ui`) is wired, audit Tab/arrow/Enter/Escape per the checklist template.
- **CollectionList "Load more" button (US3 / FR-019)**: Static truncation text only. Once an interactive affordance is added, audit Tab-reachability and Enter activation.
- **Slash-command auto-complete**: Not implemented. Audit when shipped.

---

## Keyboard-only Navigation Checklist (FR-055)

Items below reflect the state of the actual source code as of 2026-04-19. Ticking an item requires a human tester to manually verify the behavior matches the description.

### PermissionGauntletModal

- [ ] The permission modal receives all keyboard input automatically when it mounts (no extra keypress required) — `useInput` activates on mount.
- [x] `y` / `Y` grants the request and emits `permission_response: granted`. (Verified in source: line 68-77, `PermissionGauntletModal.tsx`.)
- [x] `n` / `N` denies the request and emits `permission_response: denied`. (Verified in source: line 78-88.)
- [x] Escape denies the request — `key.escape` branch is identical to `n`. (Verified in source: line 78.)
- [ ] All other keystrokes are blocked while the modal is open — `useInput` callback comment on line 89 says "All other keys are consumed (blocked) intentionally." Manual confirmation required.
- [ ] Focus returns to `InputBar` after modal closes — requires `InputBar.disabled` to transition `false`; wiring is in `tui.tsx`, not yet manually verified.
- [ ] **GAP**: No Tab cycle between "Allow" and "Deny" buttons — the modal is y/n/Escape only. If FR-055 requires explicit button tabbing, this needs a followup implementation task.

### InputBar (Korean IME + Enter + Backspace)

- [ ] Korean IME Enter (mid-composition) does NOT submit — guarded by `!ime.isComposing`. Manual verification required on macOS Korean IME and Linux fcitx5/ibus.
- [ ] Backspace deletes partial syllable atomically (delegated to `useKoreanIME`). Manual IME hardware test required.
- [ ] Enter submits only non-empty committed text (`text.trim().length > 0`). Manual test required.
- [ ] Input is suppressed when `disabled=true` (modal open). Manual test with permission fixture required.

### CollectionList "Load more"

- [ ] **GAP — NOT IMPLEMENTED**: No keyboard-reachable "Load more" affordance exists. The component renders static truncation text. Follow-up task required to implement an interactive affordance per FR-019.

### Session list Select

- [ ] **DEFERRED — NOT WIRED**: Session list rendering UI does not yet exist. Keyboard-navigation audit blocked until UI component is implemented.

### Ctrl-C SIGTERM

- [ ] Ctrl-C sends SIGTERM to the backend process within ≤ 3 s (FR-009). Manual test with `kill -0` verification required.
- [ ] No interactive component intercepts Ctrl-C without forwarding — confirmed `PermissionGauntletModal` only intercepts y/n/Escape.

---

## Screen reader smoke — macOS VoiceOver + Linux Orca

**Status**: Manual smoke plan only. This plan has NOT been executed. Execution is required to satisfy FR-056.

> This section is a documented manual test plan, not a CI-automated check. Automated screen-reader CI for Ink-based TUIs requires upstream Ink accessibility improvements (see Deferred Items in spec.md `#1294`). All items below remain unchecked until a human tester executes the steps on the specified hardware/OS.

### Known issues (pre-execution, from static code analysis)

1. **ANSI escape code degradation**: Ink writes raw ANSI escape sequences to stdout. Screen readers in line-review mode may speak or display raw escape codes (e.g., `\e[1m`, `\e[32m`) interleaved with text content. This is a fundamental limitation of Ink's output model and applies to all TUI output including streaming assistant chunks, the permission modal border, and risk-level color codes.

2. **Color-only risk indicator on `PermissionGauntletModal`**: `PermissionGauntletModal.tsx` line 92 and 108-109 express `risk_level` (`low`/`medium`/`high`) exclusively via `riskBorderColor` (a theme token mapping to `theme.success` / `theme.warning` / `theme.error`). The risk level text (`HIGH`, `MEDIUM`, `LOW`) is rendered via `pendingRequest.risk_level.toUpperCase()` on line 109. The text representation exists, so VoiceOver/Orca will read the level string — but the border color alone would be inaccessible without it. Confirmed: the text label is present.

3. **No `aria-*` equivalents in Ink**: Ink's component model does not emit ARIA roles, live regions, or focus management signals to an assistive technology bridge. Screen readers operating in line-review mode (not application mode) are the only usable interaction model. Modal "focus trap" behavior that a DOM-based UI provides via `aria-modal` does not exist — the `PermissionGauntletModal` blocks input via Ink's `useInput` activation model but does not signal to VoiceOver/Orca that a modal is active.

---

### macOS VoiceOver

**Test environment**: macOS 14+ (Sonoma) or later, Terminal.app or iTerm2, VoiceOver enabled via Cmd+F5.

**Prerequisites**:
- Bun installed (`~/.bun/bin/bun` — note: `bun` may not be on `$PATH` in all shells; use the full path `~/.bun/bin/bun run tui` if `bun: command not found` is reported).
- Python backend running or fixture mode configured.
- VoiceOver cursor interaction mode set to "Text selection" for terminal windows.

**Steps**:

1. Enable VoiceOver: press Cmd+F5 (or open System Settings > Accessibility > VoiceOver).
2. Open Terminal.app. Start the TUI in fixture mode:
   ```
   ~/.bun/bin/bun scripts/fixture-runner.ts tests/fixtures/smoke/route-safety.jsonl
   ```
   (Note: `scripts/fixture-runner.ts` does not exist yet — see T127 delta log. Use `tui/src/entrypoints/tui.tsx` against a stub backend, or wait for fixture-runner.ts to be implemented.)
3. With VoiceOver active, use VO+Right arrow to move through the terminal output line by line. Confirm the assistant message text is spoken without embedded ANSI escape codes (`\e[` sequences).
4. Trigger a `tool_result` with `kind: "lookup"` returning a `LookupCollection`. Confirm VoiceOver reads the `CollectionList` row text and the truncation notice.
5. Trigger the permission modal by replaying `tests/fixtures/coordinator/permission-gauntlet.jsonl` (if the file exists) or injecting a `permission_request` frame manually. Confirm VoiceOver reads: (a) the modal title, (b) the `description_ko` and `description_en` text, (c) the `[y]` / `[n]` prompt. Confirm VoiceOver does NOT continue reading background content while the modal is open (Ink's `useInput` activation blocks other input but does not enforce an ARIA modal — known limitation).
6. Kill the backend process (`kill -9 <pid>`) and confirm VoiceOver reads the `CrashNotice` text. Confirm no `KOSMOS_*` env var values appear in the spoken output.

**Checklist items** (tick when manually verified by a human tester):

- [ ] Assistant chunk text is spoken without raw ANSI codes in line-review mode.
- [ ] `CollectionList` row text and truncation notice are spoken.
- [ ] Permission modal title, bilingual description, and y/n prompt are spoken.
- [ ] `CrashNotice` text is spoken; no `KOSMOS_*` values in spoken output.
- [ ] **Known issue acknowledged**: VoiceOver does not receive an ARIA-modal signal; background content may be navigable with VO cursor — this is a known Ink limitation.
- [ ] **Known issue acknowledged**: ANSI escape codes may appear in spoken output for colored or styled text — logged as a known issue, not a blocker for v1.

---

### Linux Orca

**Test environment**: Ubuntu 24.04 LTS, GNOME Terminal, Orca screen reader (`sudo apt install orca`).

**Prerequisites**:
- Bun installed via `curl -fsSL https://bun.sh/install | bash`; `~/.bun/bin/bun` is available.
- Orca active: GNOME Settings > Accessibility > Screen Reader toggle, or run `orca` from a terminal in a separate session.
- Python 3.12+ with `uv` installed.

**Steps**:

1. Enable Orca: toggle from GNOME Settings > Accessibility > Screen Reader, or run `orca &` in a background terminal.
2. Open GNOME Terminal. Start the TUI:
   ```
   ~/.bun/bin/bun scripts/fixture-runner.ts tests/fixtures/smoke/route-safety.jsonl
   ```
   (Same caveat as macOS: `fixture-runner.ts` is not yet implemented. See T127 delta log.)
3. Use Orca's flat-review mode: Orca+KP_8 to read the line above, Orca+KP_2 to read the line below. Navigate rendered rows and confirm the assistant message text is spoken without `\e[` sequences.
4. Trigger a `tool_result` with `kind: "lookup"` returning a `LookupCollection`. Confirm Orca reads the row text and truncation notice.
5. Trigger the permission modal. Confirm Orca announces the modal content. Note: Orca does not receive an ARIA-modal signal from Ink; flat-review may still navigate to background content (known limitation).
6. Kill the backend and confirm Orca reads the `CrashNotice` text without leaking `KOSMOS_*` values.

**Checklist items** (tick when manually verified by a human tester):

- [ ] Assistant chunk text is spoken without raw ANSI codes in Orca flat-review mode.
- [ ] `CollectionList` row text and truncation notice are spoken.
- [ ] Permission modal title, bilingual description, and y/n prompt are spoken.
- [ ] `CrashNotice` text is spoken; no `KOSMOS_*` values in spoken output.
- [ ] **Known issue acknowledged**: Orca does not receive an ARIA-modal signal — known Ink limitation.
- [ ] **Known issue acknowledged**: ANSI escape codes may appear in spoken output — known limitation.

---

## Visual Contrast

ThemeToken sets (`default`, `dark`, `light` — FR-039) MUST pass WCAG AA minimum contrast ratio (4.5:1 for normal body text, 3:1 for large text) between foreground and background color values as declared in `tui/src/theme/*.ts`.

Verification method: extract hex color pairs from theme token files and test with a WCAG contrast checker (e.g., [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/) or the `wcag-contrast` npm package).

### Default theme

- [ ] Body text foreground / background passes WCAG AA (4.5:1).
- [ ] Dim text (timestamps, secondary labels) / background passes WCAG AA.
- [ ] Error banner foreground / background passes WCAG AA.
- [ ] Permission modal text / modal background passes WCAG AA.

### Dark theme

- [ ] Body text foreground / background passes WCAG AA (4.5:1).
- [ ] Dim text / background passes WCAG AA.
- [ ] Error banner foreground / background passes WCAG AA.
- [ ] Permission modal text / modal background passes WCAG AA.

### Light theme

- [ ] Body text foreground / background passes WCAG AA (4.5:1).
- [ ] Dim text / background passes WCAG AA.
- [ ] Error banner foreground / background passes WCAG AA.
- [ ] Permission modal text / modal background passes WCAG AA.

---

## Internationalization and RTL

### Bilingual support (FR-037)

FR-037: "User-visible command text MUST be localized to Korean + English; internal command identifiers MUST remain in English."

All user-visible strings live in `tui/i18n/en.ts` (English source) and `tui/i18n/ko.ts` (Korean translation). Internal command identifiers (e.g., `/save`, `/sessions`) are English-only.

- [ ] All strings in `tui/i18n/ko.ts` have a corresponding key in `tui/i18n/en.ts`; no orphaned keys.
- [ ] `KOSMOS_TUI_LANG=ko` renders Korean strings for all user-visible surfaces.
- [ ] `KOSMOS_TUI_LANG=en` (or unset) renders English strings.
- [ ] Internal slash-command identifiers (`/save`, `/sessions`, `/resume`, `/new`) are not translated.

### RTL support

RTL (right-to-left) layout is not in scope for v1. Ink's layout model does not provide RTL support, and no KOSMOS v1 data sources require Arabic or Hebrew rendering.

**Deferral note**: RTL support is deferred to a future ADR and tracking issue per Spec 287 § Scope Boundaries & Deferred Items. If RTL is required in a future release, a dedicated Spec and ADR must be opened before any RTL layout changes are made.

- [ ] (Deferred) RTL layout — tracked in future ADR/issue.

---

## Audit Log

Record each accessibility review pass here. One row per session; add rows chronologically.

| Date | Auditor | Scenario | Result | Notes |
|------|---------|----------|--------|-------|
| 2026-04-19 | Technical Writer (T123) | Keyboard-only navigation pass — static code analysis of all interactive components | See table above | Gaps: CollectionList "Load more" not implemented; session list Select not wired to UI; PermissionGauntletModal has no Tab cycle between buttons. |
| 2026-04-19 | Technical Writer (T124) | Screen-reader smoke plan authored | Plan documented; NOT executed | Execution required on macOS VoiceOver + Ubuntu 24.04 Orca by a human tester. |
