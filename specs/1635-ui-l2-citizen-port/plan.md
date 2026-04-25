# Implementation Plan: P4 · UI L2 Citizen Port

**Branch**: `feat/1635-ui-l2-citizen-port` (spec dir slug `1635-ui-l2-citizen-port`)
**Date**: 2026-04-25
**Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/1635-ui-l2-citizen-port/spec.md`

## Summary

Port the nine UI L2 surfaces approved in `docs/requirements/kosmos-migration-tree.md § UI L2 결정사항` to TUI components on top of the P3 (#1634) closed 13-tool surface and 4-primitive wrapper. Five surface families — UI-A onboarding 5-step, UI-B REPL Main, UI-C Permission Gauntlet, UI-D Ministry Agent visibility, UI-E auxiliary — are wired up with ≥ 90% visual + structural fidelity to Claude Code 2.1.88. Backend infrastructure (Spec 027 swarm core, Spec 033 permission v2, Spec 035 brand-port memdir, Spec 021 + Spec 028 OTEL stack) is already in production; this epic adds no new backend services and no new core runtime dependencies. Two TS-only additions are scoped: `pdf-to-img` (Apache-2.0, WASM, PDF inline preview) and `pdf-lib` (MIT, `/export` PDF assembly), explicitly authorized by the Epic body.

## Technical Context

**Language/Version**: TypeScript 5.6+ on Bun v1.2.x runtime (TUI layer, existing Spec 287 stack); Python 3.12+ backend untouched by this epic.
**Primary Dependencies**: `ink` (React for CLIs), `react`, `@inkjs/ui`, `string-width`, existing Bun stdlib + `crypto.randomUUID()` (existing Spec 287/032 stack); **two new TS deps** — `pdf-to-img` (Apache-2.0, WASM PDF→PNG, FR-010), `pdf-lib` (MIT, `/export` assembly, FR-032). Backend Python: no change.
**Storage**: User-tier memdir under `~/.kosmos/memdir/user/` (existing infrastructure from Spec 027 and Spec 035). New paths added by this epic: `~/.kosmos/memdir/user/onboarding/state.json` (resumable step state, FR-002), `~/.kosmos/memdir/user/preferences/a11y.json` (accessibility toggles, FR-005). Permission receipts continue to live in `~/.kosmos/memdir/user/consent/` (Spec 035), append-only.
**Testing**: `bun:test` for unit + behavioral tests on every new component; visual fidelity verified by side-by-side comparison against `.references/claude-code-sourcemap/restored-src/src/` (manual scoring per FR-034 / SC-009).
**Target Platform**: macOS and Linux terminals — Kitty and iTerm2 with graphics protocol detection for inline PDF (FR-010); other terminals fall back to OS `open`.
**Project Type**: Citizen-facing TUI (single project — `tui/`).
**Performance Goals**: Streaming smoothness perceived ≥ 4/5 Likert at 20-token chunk boundary (SC-002); slash-autocomplete ≤ 100 ms after `/` keystroke at p99 (SC-005); agent visibility surface lag ≤ 500 ms p95 (SC-007); accessibility toggles applied ≤ 500 ms (SC-011).
**Constraints**: ≥ 90% visual + structural fidelity to CC 2.1.88 (FR-034 / SC-009); zero new external network egress (FR-038 / SC-008); zero new core runtime dependencies (AGENTS.md hard rule — only `pdf-to-img` and `pdf-lib` admitted, justified in `research.md § Dependency justification`); fail-closed defaults on permission timeouts (FR-024) and Ctrl-C cancel (FR-023).
**Scale/Scope**: 9 surfaces, ~30–40 new/modified TS components under `tui/src/`, 38 functional requirements, 12 measurable success criteria, ~3 000 LOC TS estimated, 1 integrated PR closing #1635 (per `feedback_integrated_pr_only`).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Verdict | Evidence |
|---|---|---|
| **I. Reference-Driven Development** | PASS | Every UI L2 surface ports a concrete construct from `.references/claude-code-sourcemap/restored-src/src/` (`Onboarding.tsx`, `permissions/`, `HelpV2/`, `Markdown.tsx`, `MarkdownTable.tsx`, `CtrlOToExpand.tsx`, `ExportDialog.tsx`, `HistorySearchDialog.tsx`, `BypassPermissionsModeDialog.tsx`, `agents/`, `keybindings/`, `context/modalContext.tsx`). Phase 0 research.md tabulates the per-FR mapping. Files lifted from restored-src will carry the upstream-path + `2.1.88` + research-use header per the constitution's lift-rule. |
| **II. Fail-Closed Security (NON-NEGOTIABLE)** | PASS | UI L2 introduces no new tool adapters and no new auth paths — Layer 1/2/3 backend (Spec 033) already enforces fail-closed. The TUI surface upholds the discipline: Ctrl-C in a permission modal records `auto_denied_at_cancel` (FR-023); 5-minute idle on Layer 3 records `timeout_denied` (FR-024); `bypassPermissions` mode requires reinforcement confirmation (FR-022). |
| **III. Pydantic v2 Strict Typing (NON-NEGOTIABLE)** | PASS | Backend untouched — no new Pydantic models. TS side uses Zod for IPC envelope additions (none in this epic; Spec 032 envelope is reused as-is) and for slash-command catalog typing. No `any` in shipped TS code. |
| **IV. Government API Compliance** | N/A | No new tool adapters; no `data.go.kr` calls added or modified. CI live tests gated by `@pytest.mark.live` remain out of scope. |
| **V. Policy Alignment** | PASS | Implements PIPA §15 consent step (FR-006), PIPA §26 trustee notice (FR-006 visual + textual), PIPA right-of-revocation with audit preservation (FR-007); Korea AI Action Plan principle 8 (single conversational window + cross-ministry swarm UI: FR-025–028) and principle 9 (Open API surfaced via `/plugins` browser entry: FR-031). |
| **VI. Deferred Work Accountability** | PASS | spec.md ships an 8-row "Deferred to Future Work" table; every "Phase P5" / "Phase P6" / "separate epic" / "follow-up" mention in the spec body resolves to a row. `/speckit-taskstoissues` will resolve `NEEDS TRACKING` markers. |

**Gate result**: All six principles cleared. No Complexity Tracking entries required.

**Post-design re-check (after Phase 1)**: data-model.md, contracts/, and quickstart.md introduce no new violations. Specifically: (a) every new TS schema lives under `tui/src/schemas/ui-l2/` and uses Zod with strict types — no `any`; (b) the keybinding contract preserves the IME safety rule from `vision.md § Keyboard-shortcut migration` (every input-mutating binding declares `ime_safe: false`); (c) the memdir-paths contract documents zero new network egress and routes all consent / agent / session writes through existing Spec 027 / 033 / 035 IPC; (d) the slash-commands schema mandates Korean-primary descriptions with English fallback (Principle V + FR-004). All six principles still PASS post-design.

## Project Structure

### Documentation (this feature)

```text
specs/1635-ui-l2-citizen-port/
├── plan.md              # this file
├── research.md          # Phase 0 — reference mapping + deferred items validation + dep justification
├── data-model.md        # Phase 1 — TS-side entities (Zod schemas)
├── quickstart.md        # Phase 1 — citizen golden path walk-through
├── contracts/           # Phase 1 — slash-command catalog + keybinding contract + memdir paths
│   ├── slash-commands.schema.json
│   ├── keybindings.schema.json
│   └── memdir-paths.md
├── checklists/
│   └── requirements.md  # already produced by /speckit-specify
└── tasks.md             # produced by /speckit-tasks (NOT this command)
```

### Source Code (repository root)

The TUI is the only modified surface. Backend Python is unchanged.

```text
tui/
├── src/
│   ├── components/
│   │   ├── onboarding/                                      # UI-A · 5-step sequence (FR-001..007)
│   │   │   ├── PreflightStep.tsx                            # NEW
│   │   │   ├── ThemeStep.tsx                                # PORT — restored-src ThemePicker
│   │   │   ├── PipaConsentStep.tsx                          # PORT — Onboarding.tsx PIPA section
│   │   │   ├── MinistryScopeStep.tsx                        # NEW (Spec 035 memdir tie-in)
│   │   │   ├── TerminalSetupStep.tsx                        # NEW (a11y + Shift+Tab hint)
│   │   │   └── OnboardingFlow.tsx                           # PORT — Onboarding.tsx step driver
│   │   ├── messages/                                        # UI-B · REPL Main (FR-008..014)
│   │   │   ├── StreamingChunk.tsx                           # PORT — restored-src streaming primitive
│   │   │   ├── PdfInlineViewer.tsx                          # NEW — Kitty/iTerm2 detect → pdf-to-img
│   │   │   ├── MarkdownRenderer.tsx                         # PORT — Markdown.tsx
│   │   │   ├── MarkdownTable.tsx                            # PORT — MarkdownTable.tsx (1:1)
│   │   │   ├── ErrorEnvelope.tsx                            # NEW — LLM/Tool/Network 3-type
│   │   │   └── ContextQuoteBlock.tsx                        # NEW — ⎿ + single-border
│   │   ├── PromptInput/
│   │   │   ├── PromptInputFooterSuggestions.tsx             # PORT — autocomplete dropdown (FR-014)
│   │   │   └── CtrlOToExpand.tsx                            # PORT — restored-src CtrlOToExpand.tsx
│   │   ├── permissions/                                     # UI-C · Permission Gauntlet (FR-015..024)
│   │   │   ├── PermissionGauntletModal.tsx                  # PORT — restored-src permissions/
│   │   │   ├── BypassReinforcementModal.tsx                 # PORT — BypassPermissionsModeDialog.tsx
│   │   │   ├── PermissionLayerHeader.tsx                    # NEW — green ⓵ / orange ⓶ / red ⓷
│   │   │   └── ReceiptToast.tsx                             # NEW — rcpt-<id> surface
│   │   ├── agents/                                          # UI-D · Ministry Agent (FR-025..028)
│   │   │   ├── AgentVisibilityPanel.tsx                     # PORT — proposal-iv 5-state
│   │   │   └── AgentDetailRow.tsx                           # NEW — SLA / health / avg-resp
│   │   ├── help/                                            # UI-E · HelpV2 (FR-029)
│   │   │   └── HelpV2Grouped.tsx                            # PORT — restored-src HelpV2/
│   │   ├── config/                                          # UI-E · Config overlay (FR-030)
│   │   │   ├── ConfigOverlay.tsx                            # NEW
│   │   │   └── EnvSecretIsolatedEditor.tsx                  # NEW
│   │   ├── plugins/                                         # UI-E · Plugin browser (FR-031)
│   │   │   └── PluginBrowser.tsx                            # NEW — ⏺/○ + Space/i/r/a
│   │   ├── export/                                          # UI-E · Export PDF (FR-032)
│   │   │   └── ExportPdfDialog.tsx                          # PORT — ExportDialog.tsx + pdf-lib
│   │   └── history/                                         # UI-E · History search (FR-033)
│   │       └── HistorySearchDialog.tsx                      # PORT — restored-src HistorySearchDialog.tsx
│   ├── screens/
│   │   └── REPL.tsx                                         # MODIFY — wire all surfaces
│   ├── keybindings/
│   │   ├── defaultBindings.ts                               # MODIFY — Ctrl-O, Shift+Tab, /-trigger
│   │   ├── KeybindingContext.tsx                            # PORT — restored-src KeybindingContext
│   │   └── useKeybinding.ts                                 # PORT — restored-src useKeybinding
│   ├── context/
│   │   ├── modalContext.tsx                                 # PORT — modal stack
│   │   ├── overlayContext.tsx                               # PORT — overlay stack
│   │   ├── notifications.tsx                                # PORT — toast surface
│   │   └── PermissionReceiptContext.tsx                     # NEW — receipt + revoke surface
│   ├── commands/
│   │   ├── onboarding.ts                                    # NEW — /onboarding [step] (FR-003)
│   │   ├── consent.ts                                       # NEW — /consent list | revoke (FR-019, 020)
│   │   ├── agents.ts                                        # MODIFY — /agents [--detail] (FR-026)
│   │   ├── help.ts                                          # MODIFY — 4-group output (FR-029)
│   │   ├── config.ts                                        # NEW — /config overlay entry (FR-030)
│   │   ├── plugins.ts                                       # MODIFY — browser entry (FR-031)
│   │   ├── export.ts                                        # NEW — /export PDF (FR-032)
│   │   ├── history.ts                                       # NEW — /history filters (FR-033)
│   │   └── lang.ts                                          # NEW — /lang ko|en (FR-004)
│   ├── i18n/
│   │   ├── ko.ts                                            # MODIFY — onboarding + error + a11y keys
│   │   └── en.ts                                            # MODIFY — fallback strings
│   └── theme/
│       └── tokens.ts                                        # MODIFY — UFO purple verified (Spec 034 already shipped this)
└── tests/
    ├── components/
    │   ├── onboarding/                                       # FR-001..007 unit tests
    │   ├── messages/                                         # FR-008..014 unit tests
    │   ├── permissions/                                      # FR-015..024 unit tests
    │   ├── agents/                                           # FR-025..028 unit tests
    │   └── (help, config, plugins, export, history)/         # FR-029..033 unit tests
    ├── commands/                                             # /onboarding · /consent · /agents · /help · /config · /plugins · /export · /history · /lang
    ├── keybindings/                                          # Ctrl-O, Shift+Tab, /-trigger
    └── i18n/                                                 # ko/en parity
```

**Structure Decision**: Single TUI project. All net-new artifacts land under `tui/src/components/` + `tui/src/screens/` + `tui/src/keybindings/` + `tui/src/context/` + `tui/src/commands/` + `tui/src/i18n/` + `tui/tests/`. No backend changes — backend Python files are not modified by this epic. The PR is integrated (one PR closing #1635) per `feedback_integrated_pr_only`; per-task PRs are forbidden.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No constitution violations. Two new TS dependencies (`pdf-to-img`, `pdf-lib`) are not violations because the AGENTS.md hard rule scopes "zero new core runtime dependencies" to backend Python (the rule is repeated under every `pyproject.toml` + Python spec); the Epic body explicitly authorizes both TS-only additions. Justification documented in `research.md § Dependency justification`.
