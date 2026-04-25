# Phase 0 Research — P4 · UI L2 Citizen Port

**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)
**Generated**: 2026-04-25

This document discharges three Phase 0 obligations defined in `.specify/memory/constitution.md`:

1. **Reference mapping** — every FR points to a concrete construct in the canonical references (`docs/vision.md § Reference materials` + `.references/claude-code-sourcemap/restored-src/src/`).
2. **Deferred items validation** — every "Phase P5", "Phase P6", "follow-up", and "separate epic" mention in spec.md resolves to the `Deferred to Future Work` table.
3. **Dependency justification** — every new package outside the existing AGENTS.md baseline is justified.

There are no open `NEEDS CLARIFICATION` markers in spec.md. The migration tree (`docs/requirements/kosmos-migration-tree.md § UI L2`) is the canonical source for every UI choice and was approved 2026-04-24.

---

## 1 · Reference mapping (Constitution Principle I)

Every FR in spec.md is anchored to a concrete reference. Paths are relative to the repo root. Files lifted under the constitution's lift-rule will carry an upstream-path + `2.1.88` + research-use header.

### UI-A · Onboarding 5-step (FR-001..007)

| Decision | Reference (CC restored-src) | Rationale | Alternatives considered |
|---|---|---|---|
| Five-step driver with persistent step state (FR-001, FR-002) | `.references/claude-code-sourcemap/restored-src/src/components/Onboarding.tsx` | CC ships an exact step registry pattern — `Onboarding.tsx` walks an array of step components and persists completion. Direct port satisfies ≥ 90% fidelity (FR-034). | Reinvent step driver — rejected: violates Principle I and adds ~200 LOC for no gain. |
| `/onboarding [step]` re-entry (FR-003) | `.references/claude-code-sourcemap/restored-src/src/commands/` (CC slash-command pattern) | CC slash-commands take optional positional args; identical surface for our re-entry semantics. | Argparse-style flags — rejected: CC's positional pattern is the canonical port. |
| Korean primary + English fallback (FR-004) | `tui/src/i18n/{ko,en}.ts` (existing KOSMOS infrastructure) | i18n table already in place; this epic only adds onboarding + a11y keys. | New i18n framework — rejected: existing module satisfies the FR. |
| Four accessibility toggles persisted to memdir (FR-005) | Spec 035 memdir path + `vision.md § Layer 5 Memory tiers` (USER tier) | USER-tier memdir is the canonical citizen-preference store; a11y belongs there. | Local-storage TS only — rejected: would not survive `bun run tui` restarts. |
| PIPA §26 trustee notice (FR-006) | `vision.md § TUI experience surface — Citizen onboarding step 2` + `.references/claude-code-sourcemap/restored-src/src/components/Onboarding.tsx` (consent step pattern) | Vision doc names PIPA consent as the canonical second step; CC supplies the consent-acknowledgement layout. | Skip notice text — rejected: violates Principle V and PIPA §26. |
| Right-of-revocation preserves audit + OTEL (FR-007) | Spec 033 ledger semantics + Spec 021 OTEL emission | Ledger is append-only by Spec 033; this epic only ensures the TUI surface respects it. | Delete prior receipts on revoke — rejected: violates §V and the Spec 033 contract. |

### UI-B · REPL Main (FR-008..014)

| Decision | Reference | Rationale | Alternatives considered |
|---|---|---|---|
| ~20-token chunk streaming (FR-008) | `.references/claude-code-sourcemap/restored-src/src/components/Messages.tsx` + `Message.tsx` + `VirtualMessageList.tsx` | CC's `Messages.tsx` chunks renders by token-budget, not per-token; 20-token batches are the migration tree decision (B.1). | Per-token render — rejected: 50–80 % render-frame cost increase, citizens perceive flicker. |
| `Ctrl-O` expand/collapse (FR-009) | `.references/claude-code-sourcemap/restored-src/src/components/CtrlOToExpand.tsx` | Direct 1:1 port. | Custom mod-key combo — rejected: CC parity expected by `feedback_cc_tui_90_fidelity`. |
| Kitty/iTerm2 inline PDF + OS `open` fallback (FR-010) | `vision.md § TUI ↔ backend IPC` (graphics-protocol detection); `pdf-to-img` (Apache-2.0, WASM) | Kitty + iTerm2 graphics protocols are the only two terminals with inline-image support broad enough to matter; `pdf-to-img` is WASM, no native binary, runs inside Bun. | `chafa` / `timg` system binaries — rejected: optional progressive enhancement only, not a baseline (FR-010 needs deterministic behavior). |
| Markdown table parity (FR-011) | `.references/claude-code-sourcemap/restored-src/src/components/MarkdownTable.tsx` | 1:1 port. | Reimplement with `cli-table3` — rejected: CC fidelity. |
| Three error envelope styles (FR-012) | `.references/claude-code-sourcemap/restored-src/src/components/FallbackToolUseErrorMessage.tsx` (Tool path) + Spec 019 LLM 429 / Spec 032 Network HUD patterns | CC's Fallback*Message family supplies the visual primitive; LLM/Tool/Network split follows the migration tree (B.4). | Single generic error component — rejected: B.4 explicitly mandates 3-way visual differentiation. |
| `⎿` quote box (FR-013) | `.references/claude-code-sourcemap/restored-src/src/components/Message.tsx` (CC quote glyph already used) + migration tree B.5 | Glyph already canonical in CC. | Different glyph — rejected: glyph parity is a brand FR (FR-036). |
| Slash autocomplete dropdown (FR-014) | Existing `tui/src/components/PromptInput/PromptInputFooterSuggestions.tsx` + CC's `ContextSuggestions.tsx` | Dropdown infrastructure already exists; this epic extends it for highlighted match + inline preview per B.6. | Inline-only completion — rejected: B.6 mandates the dropdown. |

### UI-C · Permission Gauntlet (FR-015..024)

| Decision | Reference | Rationale | Alternatives considered |
|---|---|---|---|
| Layer 1/2/3 modal (FR-015, FR-016, FR-017) | `.references/claude-code-sourcemap/restored-src/src/components/permissions/PermissionDialog.tsx` + `PermissionRequestTitle.tsx` + `PermissionExplanation.tsx` | CC ships the dialog primitive; KOSMOS adds Layer color + glyph header. | Build modal from `@inkjs/ui` Select — rejected: CC's dialog primitive enforces fail-closed focus rules better. |
| Receipt ID surface (FR-018) | Spec 033 receipt schema + `.references/claude-code-sourcemap/restored-src/src/context/notifications.tsx` (toast surface) | Receipt model is owned by Spec 033; toast UI is the CC notifications context. | Inline-only receipt (no toast) — rejected: poor recovery if citizen scrolls past receipt line. |
| `/consent list` (FR-019) | Spec 033 ledger query API + `.references/claude-code-sourcemap/restored-src/src/components/HistorySearchDialog.tsx` (table layout pattern) | Ledger query is a Spec 033 method; CC's history dialog supplies the table presentation pattern. | Plain text print — rejected: B.3b table parity expected. |
| `/consent revoke rcpt-<id>` (FR-020, FR-021) | Spec 033 revoke method (idempotent semantics) + CC modal | Idempotency contract is Spec 033's; UI just surfaces the result. | Hard-delete on revoke — rejected: violates §V. |
| Shift+Tab mode switch + bypass reinforcement (FR-022) | `.references/claude-code-sourcemap/restored-src/src/components/BypassPermissionsModeDialog.tsx` + `keybindings/defaultBindings.ts` | CC ships the bypass dialog and the Shift+Tab binding. | Single-key toggle — rejected: violates fail-closed Principle II. |
| Ctrl-C auto-deny (FR-023) and 5-min timeout auto-deny (FR-024) | Spec 033 `auto_denied_at_cancel` + `timeout_denied` decision values | Spec 033 already defines the decision enum; the TUI emits the right value. | Treat cancel as "ask again" — rejected: would loop indefinitely on hostile input. |

### UI-D · Ministry Agent visibility (FR-025..028)

| Decision | Reference | Rationale | Alternatives considered |
|---|---|---|---|
| 5-state proposal-iv visibility (FR-025) | `docs/wireframes/proposal-iv.mjs` (state visual) + `.references/claude-code-sourcemap/restored-src/src/components/agents/AgentsList.tsx` + `agents/AgentDetail.tsx` | proposal-iv mjs is the canonical visual; CC's `agents/` dir supplies the list/detail panel composition. | 3-state model (idle/run/done) — rejected: migration tree D.1 mandates 5 states. |
| `/agents` and `/agents --detail` (FR-026) | Migration tree D.1 + `.references/claude-code-sourcemap/restored-src/src/components/CoordinatorAgentStatus.tsx` | CC has the SLA + health surface as a coordinator status pattern. | Single conjoined view — rejected: D.1 mandates two views with explicit `--detail` flag. |
| A+C swarm threshold (FR-027) | Migration tree D.2 + Spec 027 swarm policy | Threshold rule is canonical; this epic only wires the citizen-visible activation. | Always-on swarm — rejected: cost + UX regression. |
| Live-updated panel (FR-028) | `.references/claude-code-sourcemap/restored-src/src/context/notifications.tsx` (event-driven re-render) + Spec 027 mailbox events | Mailbox event stream already feeds the TUI; panel subscribes. | Polling — rejected: 500 ms p95 SLA (SC-007) demands push. |

### UI-E · Auxiliary surfaces (FR-029..033)

| Decision | Reference | Rationale | Alternatives considered |
|---|---|---|---|
| HelpV2 4-group (FR-029) | `.references/claude-code-sourcemap/restored-src/src/components/HelpV2/HelpV2.tsx` + `Commands.tsx` + `General.tsx` | HelpV2 is the canonical grouped help surface; we only relabel groups to Session / Permission / Tool / Storage. | Flat list — rejected: E.1 mandates grouping. |
| Config overlay + .env isolated editor (FR-030) | `.references/claude-code-sourcemap/restored-src/src/components/InvalidConfigDialog.tsx` (overlay primitive) | CC overlay primitive supports inline edit; .env isolation is a KOSMOS-original safeguard. | Edit .env inline — rejected: secret leakage risk in scrollback. |
| Plugin browser ⏺/○ + Space/i/r/a (FR-031) | Migration tree E.3 + `.references/claude-code-sourcemap/restored-src/src/components/CustomSelect/` (key-driven menu primitive) | Migration tree fixes the keystrokes; CC supplies the menu primitive. | Mouse + arrow only — rejected: E.3 mandates the 4-key bindings. |
| Export PDF (FR-032) | `.references/claude-code-sourcemap/restored-src/src/components/ExportDialog.tsx` + `pdf-lib` (MIT) | CC dialog ports 1:1; pdf-lib is the de-facto Bun-compatible PDF assembler. | Headless Chromium HTML→PDF — rejected: ~200 MB extra weight, network egress concern. |
| History 3-filter search (FR-033) | `.references/claude-code-sourcemap/restored-src/src/components/HistorySearchDialog.tsx` | Direct port, KOSMOS adds Layer filter. | New search UI — rejected: CC fidelity. |

### Cross-cutting (FR-034..038)

| Decision | Reference | Rationale | Alternatives considered |
|---|---|---|---|
| ≥ 90 % CC visual + structural fidelity (FR-034) | `.references/claude-code-sourcemap/restored-src/src/{components,screens,keybindings,context}` + `feedback_cc_tui_90_fidelity` | Direct port of CC structures is the canonical strategy. | Greenfield design — rejected: violates Principle I and the user feedback record. |
| UFO 4-pose mascot + purple palette (FR-035) | `docs/wireframes/ufo-mascot-proposal.mjs` + Spec 034 token catalog (already shipped) + `vision.md § Citizen onboarding step 1` | Mascot + palette already in repo; this epic only verifies tokens are wired through. | New mascot — rejected: brand-frozen. |
| `✻` + `⏺` + `⎿` glyphs (FR-036) | CC code base (canonical glyphs) + migration tree brand section | Glyph parity locked. | New glyphs — rejected: brand-frozen. |
| `kosmos.ui.surface` OTEL attribute (FR-037) | Spec 021 GenAI extension + Spec 028 collector pipeline | Adding a span attribute is a Spec 021 extension point; collector ingests by default (FR-038 friendly). | New collector route — rejected: would violate FR-038 (zero new egress). |
| Zero new external network egress (FR-038) | `vision.md § TUI ↔ backend IPC` + Spec 028 local Langfuse stack | All UI surfaces talk to existing Spec 032 stdio + Spec 028 collector — both local. | External feature-flag service — rejected: violates SC-008. |

---

## 2 · Wireframe mapping

| Wireframe (`docs/wireframes/`) | Surface | Used as |
|---|---|---|
| `proposal-iv.mjs` | UI-D agent visibility 5-state + primitive dot color regulation (blue lookup / orange submit / red verify / green subscribe / purple plugin.*) | Visual canonical for UI-D + REPL `ToolUseBlock` |
| `ufo-mascot-proposal.mjs` | UI-A theme step + REPL idle / thinking / success / error poses | Brand canonical for FR-035 |
| `ui-a-onboarding.mjs` | UI-A 5-step layout | Step ordering canonical (FR-001) |
| `ui-b-repl-main.mjs` | UI-B REPL chunk streaming + Ctrl-O + PDF inline + autocomplete | UI-B canonical |
| `ui-c-permission.mjs` | UI-C modal color + receipt + revoke flow | UI-C canonical |
| `ui-d-extensions.mjs` | UI-D agents + plugins surfaces | UI-D + UI-E plugin canonical |
| `ui-e-auxiliary.mjs` | UI-E help / config / export / history | UI-E canonical |

Wireframe mjs files are the visual contract. CC restored-src is the structural contract. The two are complementary: wireframes lock the layout the citizen sees; CC source locks the React component shape that produces it.

---

## 3 · Deferred items validation (Constitution Principle VI)

Spec.md ships an 8-row "Deferred to Future Work" table. Validation walks every prose mention of "Phase Pn" / "follow-up" / "separate epic" / "future" in spec.md and verifies coverage:

| Spec.md prose mention | Resolved by table row | Status |
|---|---|---|
| "P5 — Plugin DX" (5-tier template) | Row 1 (Plugin DX) | OK |
| "Phase P5 — Plugin DX" (marketplace store) | Row 6 (Plugin marketplace store UI) | OK |
| "Phase P6 — Docs + Smoke" (`docs/api`, `docs/plugins`) | Row 2 | OK |
| "Phase P6 follow-up" (Phase 2 auxiliary tools) | Row 3 | OK |
| "Phase P6 follow-up" (`/agents` advanced views) | Row 5 | OK |
| "Post-P6 localization epic" (Japanese) | Row 4 | OK |
| "Spec 035 follow-up" (memdir layout restyling) | Row 7 | OK |
| "Out of scope by canonical decision" (composite tools per migration tree §L1-B6) | Row 8 | OK |

**Result**: Every prose deferral has a row. No CRITICAL constitution-VI violations. All 8 rows carry `NEEDS TRACKING`; `/speckit-taskstoissues` will replace these with concrete issue numbers when it runs.

---

## 4 · Dependency justification

AGENTS.md hard rule: *"Never add a dependency outside a spec-driven PR."* The Python `pyproject.toml` rule (zero new core runtime deps) does not apply to TS — but every new TS dep must still earn its keep. Two are introduced:

### `pdf-to-img` (Apache-2.0)

- **Decision**: add to `tui/package.json` as `dependencies`.
- **Rationale**: FR-010 mandates inline PDF preview on Kitty/iTerm2 graphics protocol. `pdf-to-img` is a WASM-based PDF→PNG converter that runs inside Bun without native binaries (no system dependency). It is Apache-2.0 (license-compatible with KOSMOS). Bundle weight ≈ 1.5 MB pre-minify; zero network calls (purely local conversion).
- **Alternatives considered**:
  - `pdfjs-dist` — heavier (~3 MB), Mozilla-PL not blocker but legacy build pipeline issues with Bun.
  - `chafa` / `timg` system binaries — require system install per developer; FR-010 needs deterministic baseline.
  - Decline FR-010 inline PDF entirely — rejected: migration tree B.3a explicitly fixes it.

### `pdf-lib` (MIT)

- **Decision**: add to `tui/package.json` as `dependencies`.
- **Rationale**: FR-032 mandates `/export` to assemble a PDF containing transcript + tool calls + receipts (excluding OTEL + plugin internals). `pdf-lib` is the standard Bun-compatible PDF document builder, MIT licensed, zero native deps, no network calls. Bundle weight ≈ 600 KB.
- **Alternatives considered**:
  - Headless Chromium HTML→PDF — ~200 MB extra weight; would also require an internal HTTP server, adding network surface that violates FR-038.
  - Markdown→PDF via Pandoc — adds system dep.
  - Decline FR-032 export entirely — rejected: migration tree E.4 mandates it as MVP feature.

Both deps are net **TS-only**; backend Python `pyproject.toml` is not modified, preserving the AGENTS.md hard rule literally and in spirit.

---

## 5 · Open questions and unknowns

None at Phase 0 close. All design decisions trace to either (a) a `.references/claude-code-sourcemap/restored-src/` construct, (b) a `docs/wireframes/*.mjs` visual contract, or (c) an already-shipped KOSMOS spec (Spec 021/027/028/032/033/034/035). Spec.md ships zero `NEEDS CLARIFICATION` markers and the migration tree resolves every category-level question.

---

## 6 · Decisions log

- **D-1**: Five-step onboarding driver is a 1:1 port of `Onboarding.tsx`, with the developer-domain "API key / OAuth / terminal fonts" sub-steps replaced by `pipa-consent`, `ministry-scope`, `terminal-setup`. Decided by migration tree §UI-A.1; ratified here.
- **D-2**: Permission modal is composed from `permissions/PermissionDialog.tsx` + a new `PermissionLayerHeader.tsx` for the green/orange/red glyph header. The glyph itself (⓵/⓶/⓷) is canonical by migration tree §UI-C.1.
- **D-3**: REPL streaming chunk size is fixed at ≈ 20 tokens, configurable via env var `KOSMOS_TUI_STREAM_CHUNK_TOKENS` (default 20) for ops latitude — the spec FR (FR-008) reads "approximately" and the env var stays within "approximately" semantics.
- **D-4**: `pdf-to-img` and `pdf-lib` are the only two new TS dependencies. Both are MIT/Apache-2.0, WASM/JS-only, zero native and zero network. Documented in §4.
- **D-5**: A11y toggles persist to a new memdir path `~/.kosmos/memdir/user/preferences/a11y.json`. This is a Spec 035 follow-up entry in deferred-items §VI but the path itself is owned by this epic (writes only, no schema change to Spec 035 storage).
- **D-6**: Slash command catalog is a new TS module `tui/src/commands/catalog.ts` exporting metadata used by both the autocomplete dropdown (FR-014) and the `/help` 4-group output (FR-029). One source of truth.
- **D-7**: `kosmos.ui.surface` OTEL attribute is emitted from a new helper `tui/src/observability/surface.ts` that wraps the existing Spec 021 emit path. No new collector route; the attribute rides existing spans.
- **D-8**: Integrated PR only. Tasks will be assigned to parallel Teammates at `/speckit-implement`, but the merge target is one PR closing #1635. Per `feedback_integrated_pr_only`.
