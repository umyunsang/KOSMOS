# Accessibility Checklist

**Spec**: Spec 287 (KOSMOS TUI — Ink + React + Bun)
**Status**: Skeleton — validation happens in T123 (keyboard-only navigation pass) + T124 (screen-reader smoke) under Phase 10 Polish.
**Requirements**: FR-055 (keyboard-only navigation), FR-056 (screen-reader manual smoke test).

All checklist items below are unticked (`- [ ]`). A Teammate completing T123 or T124 marks items as complete (`- [x]`) and adds a date + result to the Audit Log.

---

## 1. Keyboard-only Navigation (FR-055)

FR-055: "Keyboard-only navigation MUST be supported for all interactive components (modal approval, session list selection, 'Load more', etc.)."

No mouse interaction may be required to reach, activate, or dismiss any interactive component in the TUI. All navigation MUST be completable using Tab, arrow keys, Enter, Escape, and Ctrl-key combinations.

### PermissionGauntletModal (User Story 4)

- [ ] The permission modal receives keyboard focus automatically when it appears; no additional keypress required.
- [ ] Tab cycles between "Allow" and "Deny" (or equivalent) action buttons.
- [ ] Enter activates the focused button.
- [ ] Escape dismisses the modal with a "Deny" / cancel result (same behavior as activating "Deny").
- [ ] Focus is returned to the input bar after the modal closes.

### Session list Select component (User Story 2)

- [ ] The session list (`<Select />` from `@inkjs/ui`) is navigable with Up / Down arrow keys.
- [ ] Enter selects the highlighted session and resumes it.
- [ ] Escape exits the session list without selecting.
- [ ] Page Up / Page Down skip 5 items at a time when the list exceeds the terminal height.

### CollectionList "Load more" affordance (User Story 3)

- [ ] The "Load more" button in `<CollectionList />` is reachable by Tab from the last visible row.
- [ ] Enter on the focused "Load more" button emits the follow-up `lookup(mode="fetch", page=...)` IPC frame.
- [ ] After loading, focus moves to the first newly loaded row.

### Slash-command auto-complete

- [ ] The auto-complete suggestion list opens with Tab or the first slash character.
- [ ] Up / Down arrow keys navigate suggestions.
- [ ] Tab or Enter accepts the highlighted suggestion.
- [ ] Escape dismisses the suggestion list and returns focus to the input bar.

### Ctrl-C SIGTERM (FR-009)

- [ ] Ctrl-C sends `SIGTERM` to the backend process within the ≤ 3 s window defined by FR-009.
- [ ] A second Ctrl-C within 3 s escalates to `SIGKILL`.
- [ ] No interactive component blocks Ctrl-C (i.e., no component installs a Ctrl-C intercept without forwarding the signal).

---

## 2. Screen-reader Manual Smoke (FR-056)

FR-056: "Screen-reader accessibility (Ink `aria-*` equivalents) MUST be verified by a manual test checklist committed to `tui/docs/accessibility-checklist.md`."

Ink does not emit ARIA to a DOM — it writes to stdout. "Screen-reader verification" in a TUI context means confirming that a screen reader's line-review mode reads the terminal output in a meaningful order and does not produce garbled text from raw ANSI escape sequences. Test using a real terminal emulator with the screen reader active.

### macOS VoiceOver

**Test environment**: macOS 14+, Terminal.app or iTerm2, VoiceOver (Cmd-F5 to toggle).

Manual steps (skeleton — fill in pass/fail during T124):

1. Launch the TUI via `bun run tui` in Terminal.app with VoiceOver active.
2. Navigate to the first assistant message using VO-Right arrow and verify the message text is read without embedded ANSI codes.
3. Trigger a `tool_result` with `kind: "lookup"` returning an `UnrecognizedPayload` and verify VoiceOver reads the fallback text (`UnrecognizedPayload.tsx`, FR-033).
4. Trigger the permission modal (User Story 4) and verify VoiceOver announces the modal content and focus trap.
5. Trigger a crash notice (`CrashNotice.tsx`) by killing the backend process and verify VoiceOver reads the crash message without leaking `KOSMOS_*` env var values.

Checklist items:

- [ ] Assistant chunk text is read correctly without raw ANSI escape codes by VoiceOver line-review.
- [ ] `UnrecognizedPayload` fallback label is announced by VoiceOver.
- [ ] Permission modal captures VoiceOver focus; background content is not read while the modal is open.
- [ ] Crash notice is read by VoiceOver; no `KOSMOS_*` env var values appear in the spoken output.

### Linux Orca

**Test environment**: Ubuntu 22.04+ (or equivalent), GNOME Terminal, Orca screen reader (`orca` package from distribution repo).

Manual steps (skeleton — fill in pass/fail during T124):

1. Launch the TUI via `bun run tui` in GNOME Terminal with Orca active (Super key → Accessibility → Screen Reader on).
2. Use Orca's flat-review mode (Orca-KP_8 / Orca-KP_2) to navigate rendered rows and verify no ANSI codes appear in spoken output.
3. Trigger a `tool_result` with `kind: "lookup"` returning an `UnrecognizedPayload` and verify Orca speaks the fallback text.
4. Trigger the permission modal and verify Orca announces it and enforces the focus trap.
5. Trigger a crash notice and verify Orca reads the redacted crash message.

Checklist items:

- [ ] Assistant chunk text is read correctly without raw ANSI escape codes by Orca flat-review.
- [ ] `UnrecognizedPayload` fallback label is announced by Orca.
- [ ] Permission modal captures Orca focus; background content is not read while the modal is open.
- [ ] Crash notice is read by Orca; no `KOSMOS_*` env var values appear in the spoken output.

---

## 3. Visual Contrast

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

## 4. Internationalization and RTL

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

## 5. Audit Log

Record each accessibility review pass here. One row per session; add rows chronologically.

| Date | Auditor | Scenario | Result | Notes |
|------|---------|----------|--------|-------|
|      |         |          |        |       |
