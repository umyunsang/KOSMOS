# Feature Specification: Shortcut Tier 1 Port — Citizen-Safe Keybinding Layer

**Feature Branch**: `288-shortcut-tier1-port`
**Created**: 2026-04-20
**Status**: Draft
**Input**: User description: "Epic #1303 — Shortcut Tier 1 port (ADR-006 sub-Epic I, binds amendment A-10). Port Claude Code's central keybinding system into `tui/src/` as a registry, with scope narrowed to the Tier 1 six bindings: ctrl+c (interrupt), ctrl+d (clean exit), escape (draft cancel), ctrl+r (history search), up/down (history prev/next), shift+tab (PermissionMode cycle). Every buffer-mutating binding gated on `!useKoreanIME().isComposing`. Every Tier 1 binding invokable under an active screen reader (KWCAG 2.1). Every binding disableable/remappable per WCAG 2.1.4."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Mid-query interrupt without losing the session (Priority: P1)

A citizen typing a natural-language question realises partway through the agent's tool-loop execution that they asked the wrong thing ("아, 내가 잘못 말했네"). Today on ministry portals this requires closing the browser tab and re-authenticating with a public certificate (공동인증서). In KOSMOS the citizen presses `ctrl+c` once; the active agent loop aborts, any in-flight tool call is cancelled, the session and authentication state persist, and the citizen can re-ask immediately in the same session.

**Why this priority**: Without a reliable interrupt, every mistaken query forces the citizen back through PIPA re-consent and AAL authentication. This is a pre-launch blocker — a conversational AX surface without one-key interrupt is functionally worse than the very DX portal flows KOSMOS claims to replace.

**Independent Test**: Start a long-running agent loop (e.g., a multi-step ministry lookup chain), press `ctrl+c` mid-execution, verify the loop exits within 500 ms, the session remains logged in, and the next typed message is accepted normally.

**Acceptance Scenarios**:

1. **Given** an agent loop is executing a tool call, **When** the citizen presses `ctrl+c`, **Then** the loop exits within 500 ms, an audit record captures "user-interrupted" with session ID, and the citizen can type a new message without re-authentication.
2. **Given** no agent loop is active, **When** the citizen presses `ctrl+c`, **Then** the TUI surfaces a confirmation (press-again-to-exit) rather than terminating, matching Claude Code's double-press exit pattern.
3. **Given** a screen reader is active, **When** `ctrl+c` is pressed, **Then** the interrupt announcement is emitted through the accessibility text channel within 1 second.

---

### User Story 2 — Clean exit with audit flush (Priority: P1)

A citizen finishes their session and wants to exit. Ministry portals auto-logout silently after 10 minutes; the explicit logout button's location differs per portal. In KOSMOS the citizen presses `ctrl+d` once; the session closes cleanly, all pending audit records are flushed to durable storage, any held consent tokens are marked as session-complete, and the TUI exits with status code 0.

**Why this priority**: Regulatory — Spec 024 requires every tool call to produce an immutable audit record. An unclean exit that drops in-memory audit buffers is a PIPA §26 compliance failure. Also UX-critical: citizens must have a single, discoverable exit that is impossible to confuse with "cancel this query".

**Independent Test**: Execute several tool calls producing audit records, press `ctrl+d`, verify the process exits cleanly (exit code 0), every audit record is present in persistent storage, and no orphaned consent receipts remain.

**Acceptance Scenarios**:

1. **Given** the citizen has executed tool calls in the current session, **When** they press `ctrl+d`, **Then** audit records flush to storage before the process exits, and the exit is reported in the session-end telemetry span.
2. **Given** an agent loop is active, **When** `ctrl+d` is pressed, **Then** the TUI asks for confirmation first rather than killing the loop mid-tool-call.
3. **Given** the input buffer is non-empty, **When** `ctrl+d` is pressed, **Then** the keystroke is ignored and the binding fires only on an empty input buffer (citizen-safety rule to prevent accidental exit during typing).

---

### User Story 3 — Cancel draft without breaking Hangul composition (Priority: P1)

A citizen is composing a Korean query. Hangul input builds characters through IME composition ("ㄱ" → "가" → "간" → "간다"). Today on web forms, pressing `escape` mid-composition can commit or drop partial jamo unpredictably, corrupting the message. In KOSMOS, pressing `escape` while the IME is actively composing does nothing (the keystroke is consumed by the IME). Pressing `escape` when the IME is idle clears the input draft.

**Why this priority**: Korean composition safety is the single most-likely source of user-visible regression in a keybinding port. Any Tier 1 binding that mutates the buffer without IME gating will produce intermittent, irreproducible character-loss bugs that destroy citizen trust. ADR-005 mandates this rule.

**Independent Test**: Begin typing a Korean sentence, press `escape` mid-composition and verify the draft is preserved and the IME state is intact; then finish the composition, press `escape` again and verify the buffer clears.

**Acceptance Scenarios**:

1. **Given** the IME `isComposing` flag is true, **When** the citizen presses `escape`, **Then** the draft is preserved and the composition continues.
2. **Given** the IME is idle and the input buffer has text, **When** `escape` is pressed, **Then** the buffer clears and the cursor resets to column 0.
3. **Given** the input buffer is empty, **When** `escape` is pressed, **Then** no action fires and no audit record is written.

---

### User Story 4 — Permission mode cycle without leaving the conversation (Priority: P1)

A citizen is asking read-only questions and wants to escalate to an actual action (e.g., submit a form via an adapter). Ministry portals force a redirect to a separate identity-verification page, breaking the conversation. In KOSMOS the citizen presses `shift+tab` to cycle through Permission Modes (Spec 033: `plan` → `default` → `acceptEdits` → `bypassPermissions`); the Permission Mode indicator updates in the status bar, and tool-call gating tightens or loosens per Spec 033's spectrum. Cycling into `bypassPermissions` is blocked when the session has an active irreversible-action flag (e.g., pending 정부24 submission).

**Why this priority**: `shift+tab` is the citizen-visible handle on the entire Permission Pipeline v2 (Spec 033). Without it, Permission Modes exist only in config files and CLI flags — inaccessible to the citizen mid-conversation.

**Independent Test**: Start in `plan` mode, press `shift+tab`, verify the mode advances to `default` and the status bar updates; continue cycling to confirm all permitted transitions; attempt to enter `bypassPermissions` with an irreversible action pending and verify the transition is blocked with a visible explanation.

**Acceptance Scenarios**:

1. **Given** the current mode is `plan`, **When** `shift+tab` is pressed, **Then** the mode advances to `default` and the Permission Mode status indicator updates within 200 ms.
2. **Given** the current mode is the last in the cycle, **When** `shift+tab` is pressed, **Then** the mode wraps to the first (same semantics as `ModeCycle.tsx`).
3. **Given** an irreversible civic action is pending, **When** `shift+tab` would advance to `bypassPermissions`, **Then** the transition is blocked, the mode stays at the previous step, and a citizen-readable notice explains why.
4. **Given** the IME is composing, **When** `shift+tab` is pressed, **Then** the binding does NOT fire (composition-safety rule).

---

### User Story 5 — History prev/next for past queries (Priority: P2)

A citizen wants to re-ask or modify a question they asked earlier in the session (or in a previous session, if the memdir USER tier consent covers persistence). Ministry portals bury "recent inquiries" in different menus per ministry. In KOSMOS, when the input buffer is empty, pressing `up` loads the previous citizen query into the draft; `down` loads the next. When the buffer is non-empty, `up` and `down` pass through to the default buffer behaviour (cursor movement) so typed text is never clobbered.

**Why this priority**: Material UX improvement but not a safety-critical blocker — the session can ship without it (citizens can retype). Priority P2 reflects this.

**Independent Test**: Send several queries, then with an empty buffer press `up` repeatedly to confirm descent into history; verify `down` returns toward the present; verify pressing `up` with a non-empty buffer does NOT overwrite the draft.

**Acceptance Scenarios**:

1. **Given** the input buffer is empty and the citizen has sent ≥ 1 prior query in the session, **When** `up` is pressed, **Then** the most-recent query loads into the buffer.
2. **Given** the input buffer contains typed (but unsent) text, **When** `up` is pressed, **Then** the binding does NOT fire (buffer is preserved).
3. **Given** memdir USER tier consent was declined, **When** a new session starts and `up` is pressed with an empty buffer, **Then** the binding sees only the current-session history (not prior sessions) and the absence of prior-session history is not an error.

---

### User Story 6 — History search by substring (Priority: P2)

A citizen remembers they asked something about "부산 응급실" last week but cannot recall the exact phrasing. With memdir USER tier consent granted, pressing `ctrl+r` opens a history-search overlay where typing "부산" filters prior queries containing that substring; pressing `enter` loads the selected query into the draft; pressing `escape` closes the overlay without modifying the buffer.

**Why this priority**: Amplifies the value of User Story 5 and is the primary citizen-facing surface for the memdir USER tier. But like Story 5 it is not safety-critical — the session works without it.

**Independent Test**: Populate history with several queries, open the overlay with `ctrl+r`, type a substring, verify matching entries filter in real time, select one with `enter`, and confirm the draft loads correctly.

**Acceptance Scenarios**:

1. **Given** memdir USER consent is granted and prior queries exist, **When** `ctrl+r` is pressed, **Then** a search overlay opens within 300 ms.
2. **Given** the overlay is open, **When** the citizen types a Korean substring, **Then** matching entries filter with diacritic-aware and initial-consonant (초성) matching.
3. **Given** memdir USER consent is declined, **When** `ctrl+r` is pressed, **Then** the overlay opens scoped to current-session history only and displays a notice that cross-session history requires consent.
4. **Given** the overlay is open, **When** `escape` is pressed, **Then** the overlay closes and the pre-overlay input draft is restored byte-for-byte.

---

### User Story 7 — Disabling or remapping a binding (Priority: P2)

A citizen uses an assistive device that claims `ctrl+r` for screen-reader reload, or an external keyboard where `shift+tab` is a hardware shortcut. WCAG 2.1.4 (Character Key Shortcuts) requires the citizen be able to turn off or remap any keyboard shortcut. KOSMOS reads a user-override file from `~/.kosmos/keybindings.json` (schema only shipped in this spec; graphical editor deferred). A disabled binding is a no-op; a remapped binding fires on the new key.

**Why this priority**: Regulatory (WCAG 2.1.4) + accessibility inclusivity. Mandatory to ship, but the inline GUI editor is deferred to a later spec; config-file-only remapping is sufficient for this release.

**Independent Test**: Write a user override disabling `ctrl+r`; start TUI; press `ctrl+r`; verify no action fires and the binding is absent from the keybinding catalogue displayed in any help surface.

**Acceptance Scenarios**:

1. **Given** `~/.kosmos/keybindings.json` contains `{"ctrl+r": null}`, **When** `ctrl+r` is pressed, **Then** no action fires.
2. **Given** the override file remaps `history-search` from `ctrl+r` to `ctrl+f`, **When** `ctrl+f` is pressed, **Then** the history-search overlay opens.
3. **Given** an override attempts to remap a reserved binding (e.g., `ctrl+c` interrupt — per ADR-006 treated as safety-critical), **When** the TUI loads, **Then** the remap is rejected with a logged warning and the default binding remains active.

---

### Edge Cases

- **Ctrl+c while in a modal** (Consent, PermissionGauntlet, Onboarding): modal's local `useInput` currently claims the binding. Expected behaviour: modal-local handler wins (modal closes, agent loop continues); only when no modal is mounted does the global interrupt fire.
- **Shift+tab in a form focus chain** (e.g., Onboarding step back-navigation): local form handler wins. Global PermissionMode cycle only fires when no focus chain claims `shift+tab`.
- **Up/down inside a list overlay** (e.g., ministry scope picker): local overlay handler wins. History prev/next only fires inside InputBar with an empty buffer.
- **Ctrl+r while offline** (no cached memdir USER data): overlay opens against current-session history only; no network fallback is attempted.
- **Rapid key sequences** (e.g., ctrl+c ctrl+c within 250 ms, or chord stubs for future Tier 2): the resolver MUST NOT drop keystrokes; the first ctrl+c interrupts the loop, the second (if within confirmation window) is the double-press exit that parallels user-story 1 scenario 2.
- **Screen-reader activation mid-session**: Tier 1 announcements must be idempotent — if a screen reader attaches mid-session, pressing ctrl+c immediately works and announces correctly.
- **Terminal emulator that swallows ctrl+d** (rare legacy emulators): degrade gracefully — the TUI must still honour the menu-driven exit path; no crash.
- **Corrupted user-override file**: fall back to defaults silently; log the parse error; do not block startup.

## Requirements *(mandatory)*

### Functional Requirements

#### Central registry and resolution

- **FR-001**: The TUI MUST expose a single central keybinding registry that records every binding as an `{action, default_chord, context, description, remappable, reserved}` entry. Exactly one registry instance exists per TUI process.
- **FR-002**: The registry MUST ship with six Tier 1 actions mapped to their default chords: `agent-interrupt`→`ctrl+c`, `session-exit`→`ctrl+d`, `draft-cancel`→`escape`, `history-search`→`ctrl+r`, `history-prev`→`up`, `history-next`→`down`, `permission-mode-cycle`→`shift+tab`.
- **FR-003**: The resolver MUST consult, in order: (a) the currently focused modal/overlay's local handler, (b) the currently focused form/list's local handler, (c) the input-buffer context's local handler, (d) the global handler. The first handler that claims the chord wins; downstream handlers are not invoked for that keystroke.
- **FR-004**: The TUI MUST eliminate ad-hoc `useInput` chord handling for Tier 1 actions from any component outside the registry. Existing per-modal `useInput` calls for modal-local actions (y/n/enter) remain in place.

#### Korean IME safety

- **FR-005**: Every binding whose action mutates, clears, replaces, or submits the input buffer MUST check `useKoreanIME().isComposing` and NOT fire while composition is active. Specifically: `draft-cancel`, `history-prev`, `history-next`, `history-search`, and any Tier 1 binding that commits a history entry into the draft.
- **FR-006**: Bindings whose action does not touch the buffer (e.g., `agent-interrupt`, `permission-mode-cycle`) are exempt from the IME gate BUT MUST still not disrupt the IME composition pipeline (they must not trigger a commit of the in-progress syllable).
- **FR-007**: The IME gate check MUST be centralised inside the resolver (not duplicated in per-action handlers), so that future Tier 2/3 bindings inherit the gate without rediscovering the rule.

#### Permission mode cycle (shift+tab)

- **FR-008**: `shift+tab` MUST cycle through the Permission Modes defined by Spec 033's PermissionMode spectrum in the order `plan` → `default` → `acceptEdits` → `bypassPermissions` → `plan` (wrap).
- **FR-009**: Cycling into `bypassPermissions` MUST be blocked whenever the session has an outstanding irreversible-action flag (e.g., a pending 정부24 submission or any ConsentRecord with `is_irreversible=true` that has not yet been executed). When blocked, the cycle holds at the previous mode and surfaces a citizen-readable notice.
- **FR-010**: The Permission Mode status indicator in the TUI MUST update within 200 ms of a successful cycle and emit an OTel span attribute `kosmos.permission.mode` on the change.
- **FR-011**: The backend `ModeCycle.tsx` handler from Spec 033 MUST be the sole authority on permitted transitions; the keybinding layer only forwards the cycle request and renders the result.

#### Session control (ctrl+c, ctrl+d)

- **FR-012**: `ctrl+c` MUST abort the active agent loop within 500 ms and emit an audit record with event type `user-interrupted`, session ID, and the interrupted tool-call ID (if any).
- **FR-013**: `ctrl+c` with no active loop MUST arm a double-press exit: a second `ctrl+c` within 2 seconds closes the TUI (symmetric with Claude Code's behaviour); otherwise the arm times out.
- **FR-014**: `ctrl+d` MUST only fire on an empty input buffer; on a non-empty buffer it MUST be ignored (citizen-safety rule).
- **FR-015**: `ctrl+d` on empty buffer MUST trigger clean exit: flush all pending audit records to durable storage, complete any in-flight OTel spans, release consent tokens, and exit the process with status 0. If an agent loop is active, confirmation MUST be requested before exiting.
- **FR-016**: Ctrl+c/ctrl+d MUST be handled using Ink's `setRawMode` + `useInput` with raw-byte awareness (`\x03` for ctrl+c, `\x04` for ctrl+d) so the TUI behaves correctly on terminals that do not translate these keys through Node's `readline` layer.

#### History (up/down, ctrl+r)

- **FR-017**: `up` in InputBar MUST load the previous citizen query into the draft only when the buffer is empty. On a non-empty buffer, it MUST pass through to the default cursor-movement behaviour.
- **FR-018**: `down` in InputBar MUST load the next citizen query (toward the present) only when the buffer is empty. On a non-empty buffer, it MUST pass through.
- **FR-019**: Both `up` and `down` MUST respect memdir USER tier consent scoping: with consent, they traverse cross-session history; without consent, they traverse current-session history only. The scope boundary MUST be visible to the citizen (e.g., a separator line or status indicator when crossing from current-session into prior-session entries).
- **FR-020**: `ctrl+r` MUST open a history-search overlay that displays matching entries as the citizen types; matching MUST support Korean substring, diacritic-insensitive, and 초성 (initial-consonant) matching.
- **FR-021**: The history-search overlay MUST show only entries the citizen has consent to see: current-session entries always, prior-session entries only when memdir USER consent is granted.
- **FR-022**: Selecting an entry from the overlay via `enter` MUST load it into the draft; `escape` MUST close the overlay without modifying the draft.

#### User override schema (WCAG 2.1.4 compliance)

- **FR-023**: The TUI MUST read an optional user-override file at `~/.kosmos/keybindings.json` at startup. Missing or unreadable file MUST degrade silently to defaults.
- **FR-024**: A corrupted or schema-invalid override file MUST NOT block startup; the parse error MUST be logged and defaults MUST apply.
- **FR-025**: An override of `{"<chord>": null}` MUST disable the binding entirely (the chord becomes a no-op).
- **FR-026**: An override of `{"<new-chord>": "<action-name>"}` MUST remap the action from its default chord to the new one.
- **FR-027**: Bindings marked `reserved=true` in the registry (at minimum `agent-interrupt` on `ctrl+c`) MUST NOT be remappable. An override attempting to remap a reserved binding MUST be rejected with a logged warning; the default binding remains active.
- **FR-028**: Every Tier 1 binding except reserved bindings (`agent-interrupt`, `session-exit`) MUST be disableable via override. Reserved bindings are neither remappable nor disableable (safety-critical per D6).

#### Accessibility (KWCAG 2.1 / KS X OT 0003)

- **FR-029**: Every Tier 1 action MUST be invokable when a screen reader is attached (no reliance on visual-only cues for the binding to fire).
- **FR-030**: Every Tier 1 action outcome MUST emit an accessibility announcement to the appropriate text channel (e.g., modal open/close, mode change, draft-cleared, interrupt-confirmed) within 1 second.
- **FR-031**: No Tier 1 binding MAY rely on a hover or visual focus state that is absent from screen-reader flow.
- **FR-032**: The full Tier 1 binding catalogue MUST be discoverable without pressing any key (e.g., via a menu item in the existing help surface or an environment-variable-triggered dump), so a blind citizen can learn the keymap.

#### Observability and audit

- **FR-033**: Every successful Tier 1 activation MUST emit an OTel span with attribute `kosmos.tui.binding=<action-name>`; reserved bindings (`agent-interrupt`, `session-exit`) MUST additionally emit an audit record per Spec 024.
- **FR-034**: Blocked activations (IME gate, Permission Mode block, consent scope) MUST emit a span with `kosmos.tui.binding.blocked.reason=<reason>` for post-hoc analysis; no audit record is emitted for benign blocks (IME still composing is not an audit event).

### Key Entities *(include if feature involves data)*

- **Keybinding Registry Entry**: `{ action_name, default_chord, context, description, remappable, reserved }`. The registry holds these as an immutable in-memory map, rebuilt at TUI startup from `defaultBindings.ts` seed + user override.
- **User Override File** (`~/.kosmos/keybindings.json`): JSON object mapping chord strings to either `null` (disable) or action names (remap). Schema frozen in this spec; editor UI deferred.
- **Citizen Query History Entry**: `{ query_text, timestamp, session_id, consent_scope }`. Source of truth is memdir USER tier (when consent granted) or in-memory session state (always). Read-only from this spec's perspective.
- **Permission Mode State** (Spec 033): `{ current_mode, allowed_transitions, pending_irreversible_action_flags }`. Read-only from this spec; the keybinding layer only forwards cycle requests.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A citizen can interrupt an active agent loop with `ctrl+c` and have the loop stop within 500 ms on at least 99% of attempts, measured on a reference terminal (xterm-256color, Bun v1.2).
- **SC-002**: 100% of Korean-composition sessions show zero dropped or corrupted jamo characters when Tier 1 bindings are pressed mid-composition across a 200-sample automated IME-composition test suite.
- **SC-003**: Every Tier 1 binding passes a KWCAG 2.1 keyboard-accessibility audit administered by an independent accessibility auditor against a reference screen reader configuration.
- **SC-004**: A citizen who disables `ctrl+r` via the user-override file and restarts the TUI sees zero history-search overlays on 10 consecutive `ctrl+r` presses.
- **SC-005**: PermissionMode cycling via `shift+tab` is correctly blocked on at least 100% of test-suite attempts that inject an outstanding irreversible-action flag.
- **SC-006**: After clean exit via `ctrl+d`, 100% of audit records produced during the session are present in durable storage (verified by a post-exit inspection of the audit store).
- **SC-007**: The Tier 1 binding catalogue is discoverable to a citizen using only a screen reader in under 30 seconds from TUI launch (measured by a usability test with a blind participant).
- **SC-008**: Zero new runtime dependencies are introduced by this spec (AGENTS.md hard rule — the registry, resolver, and IME gate are built with existing `ink` + `react` + Bun stdlib primitives only).
- **SC-009**: At least 80% of the CC `defaultBindings.ts` binding schema shape (chord string format, action naming convention, context labels) is preserved in the KOSMOS registry to keep future Tier 2/3 ports mechanical.

## Assumptions

- Spec 033 (Permission Mode Spectrum, #1297) has shipped and exposes a stable `ModeCycle` transition API. Verified against `tui/src/permissions/ModeCycle.tsx` on commit `104e2eb`.
- Spec 027 (Agent Swarm Core mailbox IPC) provides a cancellation pathway that the `agent-interrupt` action can signal. Verified on `main`.
- Spec 024 (Tool Template Security) provides the audit-record writer that `ctrl+c`/`ctrl+d` will invoke.
- `tui/src/hooks/useKoreanIME.ts` exposes `isComposing` as a stable boolean and is the authoritative source for IME state.
- The TUI runs under Ink v3+ with `setRawMode` available and Bun v1.2.x as the runtime (Spec 287 stack).
- memdir USER tier (Epic D #1299) is NOT required to ship this spec. The history bindings (Stories 5 and 6) degrade gracefully to current-session-only history when memdir USER is absent.
- Screen readers on Korean desktops commonly tested against: NVDA (Windows), VoiceOver (macOS), 센스리더 (SenseReader, Korean commercial). Accessibility audit targets these three at minimum.
- WCAG 2.1.4 (Character Key Shortcuts) compliance is achieved via FR-023 to FR-028 (disableable/remappable). No additional "turn off all single-key shortcuts" master switch is required — the only single-key Tier 1 bindings (`escape`, `up`, `down`) are all context-gated (InputBar + empty-buffer / idle-IME).

## Scope Boundaries & Deferred Items *(mandatory)*

### Out of Scope (Permanent)

- **Image paste binding** — KOSMOS is a Korean-public-API harness; citizen queries are text-only. No image-input flow exists in the product vision (`docs/vision.md`).
- **External editor binding** (`ctrl+e` in CC) — citizens do not edit source files; this is a DX-only affordance.
- **Model picker binding** (`meta+p` in CC) — KOSMOS uses EXAONE via FriendliAI as a single model; no picker surface exists.
- **Tier 3 killAll binding** (`ctrl+x ctrl+k`) — requires multi-worker supervision surface that the coordinator does not yet expose; and citizens do not multi-task across workers in the current TUI.

### Deferred to Future Work

| Item | Reason for Deferral | Target Epic/Phase | Tracking Issue |
|------|---------------------|-------------------|----------------|
| Tier 2 bindings (pageup/pagedown scroll, ctrl+l redraw, ctrl+_ undo, ctrl+shift+c copy) | Post-launch hardening per ADR-006 Part C; Tier 2 is "after Tier 1 proves stable" | Phase 2 post-launch | #1588 |
| Tier 3 bindings (ctrl+s stash; ctrl+x ctrl+k killAll requires multi-worker supervision surface) | Depends on multi-worker supervision surface not yet designed | Phase 3 Production Ready | #1589 |
| GUI remapping editor | `/settings` TUI dialog shell is a separate Epic K (#1308); keymap editor will live inside that shell | Epic K #1308 Settings TUI dialog | #1308 |
| User-override schema hot reload (without TUI restart) | Requires file-watcher integration not yet scoped | Phase 2 post-launch | #1590 |
| 초성 (initial-consonant) search algorithm tuning for `ctrl+r` overlay | BM25 + 초성-aware tokeniser lives in Spec 022 retrieval stack; this spec reuses it via existing tokeniser — but tuning for short-query (1-2 character) 초성 search is out of scope | Epic N #1311 Session history search index | #1311 |
| Cross-session history persistence beyond memdir USER tier | memdir USER tier itself is a separate Epic D #1299; this spec consumes it when available and degrades otherwise | Epic D #1299 Context Assembly v2 | #1299 |
| Korean IME integration for future Tier 2/3 bindings | Epic E #1300 integrates IME across the full keybinding surface; this spec integrates only the Tier 1 subset | Epic E #1300 Korean IME integration | #1300 |
| Full 65-binding port from CC | ADR-006 Part C explicitly narrows to Tier 1; full port would require citizen-UX justification for each binding | Not planned (out of mission scope) | N/A |
