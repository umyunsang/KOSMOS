# Implementation Plan: Shortcut Tier 1 Port — Citizen-Safe Keybinding Layer

**Branch**: `288-shortcut-tier1-port` | **Date**: 2026-04-20 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/288-shortcut-tier1-port/spec.md`

## Summary

Port Claude Code 2.1.88's central keybinding system (14 files under `.references/claude-code-sourcemap/restored-src/src/keybindings/`) into `tui/src/keybindings/` as a shape-compatible registry, then wire exactly the Tier 1 six actions (`agent-interrupt`, `session-exit`, `draft-cancel`, `history-search`, `history-prev`, `history-next`, `permission-mode-cycle`) across Global / Chat / HistorySearch / Confirmation contexts. The IME-composition gate (`useKoreanIME().isComposing`) is centralised at the resolver, making Tier 1 Hangul-safe and leaving a correct inheritance path for the Tier 2/3 ports that Epic E (#1300) and the post-launch Tier 2 work will do next.

Technical approach: (a) mechanical port of CC's 14-file keybinding module minus the 58 bindings KOSMOS does not adopt; (b) a KOSMOS-specific override wrapper that enforces the reserved-binding list (`agent-interrupt`, `session-exit`) and the IME gate at resolution time; (c) integration with Spec 033 `ModeCycle` for `shift+tab`, Spec 027 mailbox for `ctrl+c` cancellation, and Spec 024 audit writer for reserved-action records; (d) accessibility announcements through the existing `useLiveRegion` screen-reader channel (if absent, added as KOSMOS-original per Principle I escalation, justified in research.md).

## Technical Context

**Language/Version**: TypeScript 5.6+ (strict, `noUncheckedIndexedAccess`); Python 3.12+ only touched via existing Spec 024 audit writer and Spec 027 cancellation mailbox.
**Primary Dependencies**: `ink` (existing), `react` (existing), `zod` v4 (already present in `tui/` from Spec 287 — used in existing schemas; no new dep). No new runtime dependencies — see SC-008 and AGENTS.md hard rule.
**Storage**: Registry is in-memory, rebuilt at TUI launch. User-override JSON at `~/.kosmos/keybindings.json` (read-only; never written by this spec). Consumed-but-not-produced by this spec: memdir USER tier (Epic D #1299) for cross-session history; degrades to in-memory session history when absent.
**Testing**: Existing `bun test` harness (Spec 287) for unit + integration tests against Ink test-renderer. New test fixtures for (a) Korean IME composition sequences (reused from `useKoreanIME` existing tests), (b) raw-byte chord tables, (c) accessibility-announcement assertions.
**Target Platform**: Bun v1.2.x runtime; terminals xterm-256color, Windows Terminal (with VT mode), macOS Terminal.app, iTerm2. Per CC `defaultBindings.ts` L16-L30, Windows pre-VT fallback maps `shift+tab` → `meta+m`; KOSMOS inherits this.
**Project Type**: Frontend (TUI) feature port, backed by Python audit/cancellation services via existing stdio JSONL channel.
**Performance Goals**: ctrl+c interrupt ≤ 500 ms (SC-001); mode-indicator update ≤ 200 ms (FR-010); history-search overlay open ≤ 300 ms (AS-6.1); accessibility announcement ≤ 1 s (FR-030).
**Constraints**: Zero new runtime deps (SC-008). IME-safe: 100% zero-jamo-drop over 200-sample test suite (SC-002). KWCAG 2.1 / WCAG 2.1.4 compliance (FR-029..FR-032, FR-023..FR-028).
**Scale/Scope**: 6 Tier 1 action handlers, 7 user stories, 34 FR, 9 SC. Port surface = 14 CC files (shape-preserved), minus 58 bindings not adopted. Affected KOSMOS surfaces: `tui/src/keybindings/` (new), `tui/src/components/input/InputBar.tsx` (refactor), `tui/src/permissions/ModeCycle.tsx` (integration point, no change), `tui/src/hooks/useKoreanIME.ts` (consumer, no change). ~2,600 LOC of CC reference, estimated ~900 LOC of KOSMOS port after removing unused bindings and Korean/accessibility additions.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status | Evidence |
|---|---|---|---|
| **I · Reference-Driven Development** | Every design decision traces to a concrete reference. `/speckit-plan` Phase 0 consults `docs/vision.md § Reference materials`. | ✅ PASS | research.md §0 maps all 11 design decisions to CC sourcemap paths, ADR-005, ADR-006, Spec 033, Spec 287 stack, KWCAG 2.1, and WCAG 2.1.4. TUI row in constitution table requires Ink + CC reconstructed → matched. |
| **II · Fail-Closed Security** | Reserved bindings un-remappable; PermissionMode block on irreversible-action flag; no `bypassPermissions` shortcut. | ✅ PASS | FR-027 (reserved), FR-009 (irreversible-action block), FR-011 (ModeCycle is sole authority). |
| **III · Pydantic v2 Strict Typing** | Applies to Python tool I/O. | N/A | This spec is TypeScript-only on the TUI layer. No new Python tool adapters are introduced; Python touch points (audit writer, cancellation mailbox) already follow Principle III via Specs 024 and 027. |
| **IV · Government API Compliance** | CI live-API ban; fixture-only tests. | ✅ PASS | This spec introduces no new adapters. All tests against `data.go.kr` remain skipped via `@pytest.mark.live`. |
| **V · Policy Alignment** | Korea AI Action Plan Principle 8 (single conversational window), Principle 9 (open API/MCP), Principle 5 (consent-based). | ✅ PASS | Principle 8 is strengthened — ctrl+c keeps a single conversation alive where ministry portals force re-authentication. Principle 5 — history search respects memdir USER consent (FR-019, FR-021). |
| **VI · Deferred Work Accountability** | Every deferral tracked in spec table + GitHub issue. | ✅ PASS | Deferred table has 8 rows; 7 link to tracking issues (existing: #1299, #1300, #1308, #1311 · placeholders created 2026-04-20: #1588 Tier 2, #1589 Tier 3, #1590 user-override hot reload — all linked as sub-issues of Epic #1303); 1 marked `N/A` (full-65-port permanently out of mission scope). Zero `NEEDS TRACKING` remaining. |

**Gate outcome**: All applicable principles pass. No violations; Complexity Tracking table below is empty.

## Project Structure

### Documentation (this feature)

```text
specs/288-shortcut-tier1-port/
├── plan.md              # This file (/speckit-plan output)
├── spec.md              # Spec (/speckit-specify output)
├── research.md          # Phase 0 output (this cycle)
├── data-model.md        # Phase 1 output (this cycle)
├── quickstart.md        # Phase 1 output (this cycle)
├── contracts/           # Phase 1 output (this cycle)
│   ├── keybinding-schema.ts    # Zod + TS type surface for registry entries
│   └── user-override.schema.json   # JSON Schema for ~/.kosmos/keybindings.json
├── checklists/
│   └── requirements.md  # Quality checklist from /speckit-specify
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
tui/src/
├── keybindings/                             # NEW — port of CC src/keybindings/
│   ├── defaultBindings.ts                   # Tier 1 seed (KOSMOS subset, 6 actions)
│   ├── schema.ts                            # Context enum + Zod schema (KOSMOS subset)
│   ├── reservedShortcuts.ts                 # agent-interrupt + session-exit guards
│   ├── parser.ts                            # chord string → normalised tuple
│   ├── match.ts                             # chord matcher (ctrl+c, shift+tab, etc.)
│   ├── resolver.ts                          # modal→form→context→global precedence + IME gate
│   ├── loadUserBindings.ts                  # read ~/.kosmos/keybindings.json, validate, merge
│   ├── validate.ts                          # schema + reserved guard checks
│   ├── template.ts                          # catalogue template for help/discovery
│   ├── shortcutFormat.ts                    # chord → display string ("ctrl+c" → "Ctrl+C")
│   ├── useKeybinding.ts                     # per-context hook
│   ├── useShortcutDisplay.ts                # formatter hook
│   ├── KeybindingContext.tsx                # React context
│   ├── KeybindingProviderSetup.tsx          # provider wiring
│   └── accessibilityAnnouncer.ts            # KOSMOS-original: live-region text channel
├── components/input/InputBar.tsx            # refactor: replace ad-hoc useInput with useKeybinding
├── hooks/
│   ├── useGlobalKeybindings.tsx             # NEW — port of CC hook
│   └── useKoreanIME.ts                      # existing, consumed by resolver
├── permissions/ModeCycle.tsx                # existing, called by permission-mode-cycle action
└── main.tsx                                 # wrap root in KeybindingProvider

tui/tests/keybindings/                       # NEW
├── parser.test.ts
├── match.test.ts
├── resolver.test.ts                         # incl. IME gate + modal precedence
├── reservedShortcuts.test.ts
├── loadUserBindings.test.ts
├── ime-composition.integration.test.ts      # 200-sample Korean composition suite
├── accessibility.test.ts                    # screen-reader channel assertions
└── fixtures/
    ├── korean-composition-samples.json
    └── override-files/{disable-ctrl-r,remap-ctrl-r,invalid}.json

src/kosmos/tui/audit.py                      # existing (Spec 024) — consumed
src/kosmos/agents/cancellation.py            # existing (Spec 027) — consumed
```

**Structure Decision**: Port placement under `tui/src/keybindings/` mirrors CC's `src/keybindings/` one-to-one to keep the shape parity called for in SC-009. Hooks colocate with CC under `tui/src/hooks/`. Tests live at `tui/tests/keybindings/` per Spec 287 convention. Zero new top-level directories, zero new dependencies.

## Complexity Tracking

> No constitution violations — table intentionally empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| *(none)* | *(n/a)* | *(n/a)* |
