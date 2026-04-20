# Phase 0 Research — Shortcut Tier 1 Port

**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Constitution**: [.specify/memory/constitution.md](../../.specify/memory/constitution.md) · **Vision**: [docs/vision.md](../../docs/vision.md) · **ADR**: [docs/adr/ADR-006-cc-migration-vision-update.md](../../docs/adr/ADR-006-cc-migration-vision-update.md)

## Constitution Principle I — Reference mapping

KOSMOS constitution Principle I mandates that every design decision trace to a concrete reference. The constitution's layer table names "Ink + Gemini CLI (React terminal UI)" as the primary TUI reference and "Claude Code reconstructed (TUI components)" as the secondary reference. This spec is a direct shape-preserving port of the secondary reference; primary reference is consulted only for Ink-idiomatic patterns (hook composition, `useInput` semantics).

### Per-decision reference map

| # | Design decision | Primary reference | Secondary reference | Notes |
|---|---|---|---|---|
| D1 | Adopt CC's `{context, bindings}` block schema | `.references/claude-code-sourcemap/restored-src/src/keybindings/defaultBindings.ts` L32-L60; `schema.ts` L12-L32 (KEYBINDING_CONTEXTS enum) | — | Shape-preserved; KOSMOS uses a narrowed context set (Global, Chat, HistorySearch, Confirmation) covering Tier 1 only. |
| D2 | Use raw-byte detection for ctrl+c/ctrl+d | CC `defaultBindings.ts` L36-L41 comment ("special time-based double-press handling"); Ink `setRawMode` + `use-input.ts` | Ink 3 release notes + GitHub `vadimdemedes/ink` `src/hooks/use-input.ts` | Raw bytes `\x03` / `\x04` guarantee behaviour even on terminals where readline translation is disabled. |
| D3 | Platform-specific `shift+tab` fallback | CC `defaultBindings.ts` L17-L30 (Windows pre-VT fallback to `meta+m`) | — | Inherited verbatim (KOSMOS adopts same check on `process.versions.bun >= 1.2.23`). |
| D4 | IME composition gate centralised in resolver | `tui/src/hooks/useKoreanIME.ts` (existing KOSMOS asset, no CC analog — CC has no IME concept, confirmed in ADR-006 Part B row E) + ADR-005 (Korean IME strategy) | — | Principle I permits KOSMOS-original surfaces when CC has no analog — this is such a case. The escalation is documented here as required by Principle I. |
| D5 | User-override JSON at `~/.kosmos/keybindings.json` | CC `loadUserBindings.ts` (+472 LOC) reads `~/.claude/keybindings.json` | OpenCode keybinds docs (opencode.ai/docs/keybinds) — validates path-based override pattern in agentic TUIs beyond CC | Path only differs (`~/.kosmos/`). Schema shape preserved from CC (chord-string keys → action-string or null values). |
| D6 | Reserved shortcuts list | CC `reservedShortcuts.ts` L1-L127 | — | KOSMOS's reserved set (`agent-interrupt`, `session-exit`) is a strict subset of CC's reserved set. No additions, removals, or semantic divergence. |
| D7 | Resolver precedence (modal → form → context → global) | CC `resolver.ts` L1-L244 | Kiro CLI terminal-UI docs (context-aware binding precedence) — validates the pattern beyond CC | CC's resolver is the canonical reference. Kiro confirms it's an industry pattern, not a CC idiosyncrasy — reduces risk of shape-copying a future dead-end. |
| D8 | Accessibility announcements via live region | KWCAG 2.1 (KS X OT 0003) § 4.1.3 (Status Messages) · WCAG 2.1 § 4.1.3 | — | CC has no equivalent surface (no screen-reader support in CC) — KOSMOS original per Principle I escalation (justified by Korean public-sector accessibility mandate). The new `accessibilityAnnouncer.ts` module emits text to a buffered channel that existing screen-reader integrations on Korean desktops (NVDA, VoiceOver, 센스리더) pick up through standard stdout-based announce pipelines. |
| D9 | History search overlay shape | CC `resolver.ts` uses a `HistorySearch` context; `schema.ts` L20 defines it | — | Overlay rendering will reuse the existing Ink modal pattern under `tui/src/components/onboarding/` (verified against Spec 035 `OnboardingShell.tsx`). |
| D10 | Audit-record emission on reserved actions | Spec 024 — `ToolCallAuditRecord` schema v1; `src/kosmos/tui/audit.py` writer | — | Contract-level reuse of existing writer; this spec only adds two event types (`user-interrupted`, `session-exited`). |
| D11 | Cancellation signal pathway for ctrl+c | Spec 027 — mailbox IPC `.consumed` marker pattern; `src/kosmos/agents/cancellation.py` (existing) | — | ctrl+c action writes a cancellation envelope to the coordinator mailbox; the existing at-least-once delivery guarantees the worker sees it even on retry. |

### Escalations beyond `.references/claude-code-sourcemap/` (documented per Principle I)

Two KOSMOS-original surfaces are introduced where CC has no analog:

1. **IME composition gate in resolver** (D4). Justified by ADR-006 Part B (Epic E, row "CC has no IME notion") and ADR-005. This is a hard mission requirement — KOSMOS cannot be IME-unsafe.
2. **Accessibility announcer module** (D8). Justified by KWCAG 2.1 mandatory compliance for Korean public-sector software. CC does not target screen-reader-first experiences.

Both escalations are strictly additive; they do not modify CC's schema or resolver semantics.

## Deferred Items Validation (Principle VI gate)

All 8 rows from spec.md § Deferred to Future Work table were validated:

| Deferred Item | Tracking Issue | Validation |
|---|---|---|
| Tier 2 bindings | #1588 | Placeholder issue created by `/speckit-taskstoissues` on 2026-04-20; linked as sub-issue of Epic #1303. |
| Tier 3 bindings (ctrl+s stash, ctrl+x ctrl+k killAll) | #1589 | Placeholder issue created by `/speckit-taskstoissues` on 2026-04-20; linked as sub-issue of Epic #1303. |
| GUI remapping editor | #1308 | `gh issue view 1308` confirms: open, size/M, Epic K of ADR-006 Part D-2. Valid tracking target. |
| User-override hot reload | #1590 | Placeholder issue created by `/speckit-taskstoissues` on 2026-04-20; linked as sub-issue of Epic #1303. |
| 초성 search tuning | #1311 | `gh issue view 1311` confirms: open, Sub-Epic N (session history search index). Valid tracking target. |
| Cross-session history via memdir USER | #1299 | `gh issue view 1299` confirms: open, size/M, Epic D (Context Assembly v2). Valid tracking target. |
| Korean IME for Tier 2/3 | #1300 | `gh issue view 1300` confirms: open, size/M, Epic E. Valid tracking target. |
| Full 65-binding port | N/A | Permanently not planned per ADR-006 Part C narrowing — acceptable absence per Principle VI (only "will be done but not now" items require tracking; "will never be done" items do not). |

Unregistered deferral patterns scanned across spec.md text (`separate epic`, `future epic`, `Phase [2+]`, `v2`, `deferred to`, `later release`, `out of scope for v1`): **all matches correspond to Deferred table entries**. No ghost work.

## Decision Log

### D1 · Adopt CC's `{context, bindings}` block schema

**Decision**: Port the `KeybindingBlock` shape from CC verbatim, narrowed to 4 contexts (Global, Chat, HistorySearch, Confirmation).

**Rationale**: SC-009 requires ≥ 80% shape parity with CC to keep Tier 2/3 ports mechanical. The block shape is also the cheapest to preserve — it's a pure data shape with no CC-specific behaviour embedded.

**Alternatives considered**:
- Flat chord-map (single-level `{chord: action}` dict): Rejected — loses context precedence, forces re-implementation of the resolver.
- OpenCode-style per-profile keymap: Rejected — introduces a "profile" concept KOSMOS does not need for Tier 1.

### D2 · Raw-byte detection for ctrl+c/ctrl+d

**Decision**: Handle ctrl+c as `\x03` and ctrl+d as `\x04` at the Ink `useInput` entry point using `setRawMode`, matching the CC comment at `defaultBindings.ts` L36-L41.

**Rationale**: FR-016 explicitly requires raw-byte awareness. Terminals vary in whether they translate these keys through readline; raw byte handling is the only portable path.

**Alternatives considered**:
- Relying on Ink's `key.ctrl && input === 'c'`: Rejected — Ink 3 detects most but not all terminal variants reliably for ctrl+d (ctrl+c is ok).
- Using Node's `readline` `SIGINT` handler: Rejected — fires AFTER React's render pipeline flushes, risking inconsistent audit timing.

### D3 · Platform `shift+tab` fallback

**Decision**: Inherit CC's platform detection verbatim (L17-L30 of `defaultBindings.ts`).

**Rationale**: Windows Terminal without VT mode cannot detect `shift+tab`. CC already engineered the fallback to `meta+m`; adopting it avoids a pit Claude Code already fell into.

### D4 · IME gate centralised in resolver (KOSMOS-original escalation)

**Decision**: Add a single IME-composition check inside `resolver.ts` that short-circuits any buffer-mutating action when `useKoreanIME().isComposing === true`.

**Rationale**: Per FR-007 — centralisation makes Tier 2/3 ports inherit the gate by default. ADR-005 and ADR-006 Part B row E both mandate composition safety. Placing the gate in each action handler (CC-style, since CC has no composition concept to gate) risks inconsistency.

**Alternatives considered**:
- Gate at each action handler: Rejected for inconsistency risk (see above).
- Gate inside `useKoreanIME` itself: Rejected — that hook is a pure state source, and mixing in keybinding logic violates single-responsibility.

### D5 · User-override JSON path

**Decision**: `~/.kosmos/keybindings.json` with CC-shaped schema (chord-key → action-value or `null`).

**Rationale**: Principle I + shape parity with CC's `~/.claude/keybindings.json`. OpenCode's `~/.opencode/keybinds.json` pattern is a secondary validation that the CC pattern is widely adopted in agentic TUIs, reducing risk of schema orphan.

**Alternatives considered**:
- YAML file: Rejected — adds a parse dependency (zero-new-deps rule, SC-008).
- TOML file: Rejected — same dep reason; also no precedent in CC.
- Environment-variable overrides: Rejected — WCAG 2.1.4 requires user-editable config; env vars are operator-editable, not end-user-editable.

### D6 · Reserved shortcut set

**Decision**: Reserve `agent-interrupt` (ctrl+c) and `session-exit` (ctrl+d). All other Tier 1 actions are remappable.

**Rationale**: Safety-critical actions — an unreachable interrupt is a PIPA failure (citizen cannot stop the agent). Every other Tier 1 action has a citizen-visible alternative path (menu, mode dialog), so disability/remapping cannot soft-brick the UX.

**Alternatives considered**:
- Reserve `shift+tab` too: Rejected — WCAG 2.1.4 explicitly mandates remappability; and Spec 033's PermissionMode has a config-file alternative.

### D7 · Resolver precedence

**Decision**: Modal → form/list → context → global. First hit wins; no fall-through.

**Rationale**: Matches CC's `resolver.ts` and matches Ink's `useInput` activation model (multiple `useInput` hooks can be active and each claims input independently — no fall-through).

**Alternatives considered**:
- Fall-through after ignored key: Rejected — subtle bug source; CC explicitly avoided this.

### D8 · Accessibility announcer (KOSMOS-original escalation)

**Decision**: New module `tui/src/keybindings/accessibilityAnnouncer.ts` that buffers text announcements to a reserved stdout/stderr channel. Integrates with screen readers through the standard terminal announce pipe.

**Rationale**: KWCAG 2.1 § 4.1.3 (Status Messages) requires that dynamic state changes reach assistive tech without user action. Korean public-sector mandate under KS X OT 0003 applies. CC has no such module; this is a Principle I escalation documented above.

**Alternatives considered**:
- Skip accessibility announcements, document as known gap: Rejected — FR-030 is a hard requirement; KWCAG 2.1 non-compliance blocks public-sector deployment.
- Use a third-party Node a11y library: Rejected — zero-new-deps (SC-008, AGENTS.md).

### D9 · History-search overlay shape

**Decision**: Reuse the existing Spec 035 onboarding modal shell (`OnboardingShell.tsx` layout pattern) for the ctrl+r overlay.

**Rationale**: Principle I — KOSMOS already has a modal shell with proper focus trap, escape handling, and screen-reader announcement wired in Spec 035. Reuse prevents drift between modal surfaces.

### D10 · Audit-record emission

**Decision**: Reuse Spec 024's `ToolCallAuditRecord` writer with two new event types (`user-interrupted`, `session-exited`).

**Rationale**: Spec 024 is the single authority on audit records; adding event types does not violate the schema contract.

### D11 · Cancellation pathway

**Decision**: ctrl+c writes a cancellation envelope to the coordinator mailbox (Spec 027 pattern), and the coordinator propagates it to active workers.

**Rationale**: Spec 027 mailbox has at-least-once delivery with `.consumed` markers, which handles the race window where ctrl+c fires between a worker ack and a tool-call completion.

**Alternatives considered**:
- Direct `SIGTERM` to worker process: Rejected — not graceful; audit record not guaranteed; Spec 024 compliance at risk.

## Open questions → resolutions

- **Is `~/.kosmos/` the right override location on Windows?** Resolved: yes, Node's `os.homedir()` returns `C:\Users\<user>\` on Windows, so `~/.kosmos/keybindings.json` becomes `C:\Users\<user>\.kosmos\keybindings.json`. Consistent with CC's Windows path handling.
- **Does Ink's `setRawMode` conflict with Bun's TTY handling?** Resolved per CC `defaultBindings.ts` L19-L25 comment — Bun enabled VT mode in 1.2.23; KOSMOS requires Bun >= 1.2.x (Spec 287), so the expected Bun version has the fix.
- **Does the history-search overlay need its own IME gate?** Resolved: yes, and it inherits the gate by construction — it mounts inside the resolver's composition-gated path, so keystrokes are filtered before reaching the overlay's local `useInput`.

## Phase 0 conclusion

All NEEDS CLARIFICATION marks in spec.md were zero before Phase 0 started. Principle VI validation passed. Principle I reference mapping is complete with two documented KOSMOS-original escalations. No unresolved open questions. **Ready for Phase 1.**
