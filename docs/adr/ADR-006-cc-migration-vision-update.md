# ADR-006: CC→KOSMOS Phase 2 Migration — Vision Amendments, Onboarding Brand, and Shortcut Migration

**Status**: Proposed
**Date**: 2026-04-19
**Epic**: TBD (meta-Epic "CC→KOSMOS Phase 2 Migration", sub-issue of Initiative #2)
**Supersedes portions of**: `docs/vision.md` lines 37, 57, 85, 114, 361 (see Amendments A-1..A-4, A-8)
**Extends**: ADR-003 (Bun + Ink + React TUI stack), ADR-004 (Claude Code sourcemap port policy)

---

## Context

PR #1295 merged Spec 287 (TUI port of `claude-code-sourcemap` 2.1.88 into `tui/src/`) on 2026-04-19. With the rendering spine (Ink + React + Bun) and the 5-primitive backend surface (Spec 031, ratified PR #1149) both on `main`, KOSMOS Phase 2 needs:

1. A **vision document that matches what was actually built** — several `docs/vision.md` lines now describe a future state that has already shipped, or describe retired alternatives.
2. An **evidence-grounded plan for the remaining CC migration surface** — six architectural layers with concrete files in `.references/claude-code-sourcemap/restored-src/`, mapped against KOSMOS coverage.
3. A **citizen-facing onboarding and shortcut plan** — currently KOSMOS TUI has 5 keybindings vs. CC's 65, no onboarding screen, and the SVG logo + brand palette in `assets/` has never been ported into a TUI component.
4. A **data-integrity fix** — Initiative #2's `trackedIssues` GraphQL edge is empty despite the body claiming 7 Epics (sub-issue links never created via Sub-Issues API).

This ADR records the consolidated decision so the meta-Epic can be cut with traceable scope.

**Research base** (all file paths verified to exist on `main` as of 2026-04-19):

- `.references/claude-code-sourcemap/restored-src/src/keybindings/defaultBindings.ts` (65 CC bindings, 20 contexts)
- `.references/claude-code-sourcemap/restored-src/src/query.ts` (1 729 lines — the canonical CC query engine)
- `.references/claude-code-sourcemap/restored-src/src/utils/permissions/permissions.ts` (+ `PermissionMode.ts`, `yoloClassifier.ts`, `bypassPermissionsKillswitch.ts`, `dangerousPatterns.ts`, `filesystem.ts`)
- `.references/claude-code-sourcemap/restored-src/src/coordinator/coordinatorMode.ts` (in-process AsyncLocalStorage swarm)
- `.references/claude-code-sourcemap/restored-src/src/services/compact/compact.ts` (+ `microCompact.ts`, `autoCompact.ts`) + `src/memdir/memdir.ts`
- `.references/claude-code-sourcemap/restored-src/src/services/api/withRetry.ts` (+ `errors.ts`, `errorUtils.ts`)
- `.references/claude-code-sourcemap/restored-src/src/components/Onboarding.tsx` (CC onboarding step registry)
- `assets/kosmos-{logo,logo-dark,banner-dark,icon}.{svg,png}` (8 brand assets)
- `specs/031-five-primitive-harness/research.md § 1` (CC primitive-mapping table)
- `specs/027-agent-swarm-core/` (file-based mailbox IPC, shipped)
- `tui/src/hooks/useKoreanIME.ts`, `tui/src/theme/dark.ts`, `tui/src/commands/index.ts`, `tui/src/components/input/InputBar.tsx`, `tui/src/components/coordinator/PermissionGauntletModal.tsx` (current KOSMOS TUI coverage)

---

## Decision

### Part A — Vision.md amendments (apply in the same PR as this ADR)

The following ten amendments bring `docs/vision.md` back in sync with shipped state. Each amendment cites the exact line and the evidence. No amendment adds new scope — every amendment either corrects a retired claim, records a shipped fact, or documents an already-made design decision that was scattered across specs.

#### A-1 · L37 primitive-verb table row — update to 5-primitive

**Current** (L36–37):
> | Primitive verbs | Read, Edit, Bash, Grep, WebFetch | lookup, pay, issue, apply, reserve, subscribe |

**Amended**:
> | Primitive verbs | Read, Edit, Bash, Grep, WebFetch | lookup, resolve_location, submit, subscribe, verify |

**Evidence**: Spec 031 ratified the 5-primitive surface (PR #1149, merged). `specs/031-five-primitive-harness/research.md § 1` lists exactly these five. Vision L93 already references the ratified surface; L37 is the last stale reference.

#### A-2 · L57 "forthcoming Spec 031" — past tense

**Current** (L57, first clause):
> A forthcoming **Spec 031** will execute this method and propose a small set of domain-agnostic harness primitives — currently scoped as five…

**Amended**:
> **Spec 031** executed this method and ratified a small set of domain-agnostic harness primitives — five (`lookup`, `resolve_location`, `submit`, `subscribe`, `verify`)…

**Evidence**: Spec 031 shipped. The "forthcoming" framing contradicts L93 two paragraphs later.

#### A-3 · L85 Mastra reference — retire as TUI reference

**Current** (L85):
> | Mastra (`mastra-ai/mastra`) | Apache-2.0 | TypeScript agent framework — typed tool workflow graphs with loops, branching, human-in-the-loop; Phase 2 TUI layer reference |

**Amended**:
> | Mastra (`mastra-ai/mastra`) | Apache-2.0 | TypeScript agent framework — typed tool workflow graphs with loops, branching, human-in-the-loop (reference only; not used for Phase 2 TUI after ADR-003/004) |

**Evidence**: ADR-003 selected Ink + React + Bun directly; ADR-004 confirmed the CC sourcemap port as the TUI source of truth. Mastra is still a useful cross-reference for typed tool-graph patterns but is no longer the "Phase 2 TUI layer reference" the current text implies.

#### A-4 · L114 Layer 4 pattern family — dual-path

**Current** (L114):
> | 4 | **Agent Swarms** | Ministry-specialist agents coordinated by an orchestrator | Mailbox IPC + coordinator synthesis |

**Amended**:
> | 4 | **Agent Swarms** | Ministry-specialist agents coordinated by an orchestrator | AsyncLocalStorage in-process coordinator (CC parity) + file-based mailbox IPC for crash resilience (KOSMOS Spec 027 extension) |

**Evidence**: `.references/claude-code-sourcemap/restored-src/src/coordinator/coordinatorMode.ts` uses AsyncLocalStorage + `src/tasks/InProcessTeammateTask/`; there is no mailbox-IPC path in CC. KOSMOS Spec 027 adds the file-based mailbox as a KOSMOS-original crash-resilience path (regulated domain, long-running sessions). Both paths coexist — the current phrasing hides the CC parity layer.

#### A-5 · L3 Permission Pipeline — make PermissionMode spectrum explicit

**Add after L115 Layer 3 row** (as a sub-bullet or an inline note inside the Layer 3 prose at L113):

> **PermissionMode spectrum.** Layer 3 inherits CC's four-mode PermissionMode (`default`, `plan`, `acceptEdits`, `bypassPermissions`) as a first-class concept. KOSMOS tightens `bypassPermissions` under a PIPA-specific killswitch (`bypassPermissionsKillswitch` parity) and adds a `citizen-ident-verified` precondition for tools with `auth_level ∈ {AAL2, AAL3}`.

**Evidence**: `.references/claude-code-sourcemap/restored-src/src/utils/permissions/PermissionMode.ts` + `bypassPermissionsKillswitch.ts`. Current vision L179–245 describes the permission gauntlet mechanics but never names the four modes or the killswitch. Every TUI permission dialog MUST honour the active mode; without naming it in vision, the TUI port has no architectural anchor for the mode toggle in `chat:cycleMode` (CC shift+tab).

#### A-6 · L5 Memory tier — declare Phase 1 scope

**Add to the Layer 5 section** (after the existing three-tier description, ~L276):

> **Phase-1 delivered scope.** Of the three context tiers described above, Phase 1 (on `main` as of 2026-04-19) delivers **System prompt assembly** (Spec 026 Prompt Registry) and **Session turn compaction** (`microCompact` + `autoCompact` parity). The **User** and **Project** memory tiers (CC `src/memdir/`) are deferred to Phase 2+; no KOSMOS component currently reads or writes memdir-style files.

**Evidence**: `src/kosmos/prompts/` + `src/kosmos/compact/` exist; no `~/.kosmos/memory/` writer exists. CC `src/memdir/memdir.ts` + `src/memdir/paths.ts` have no KOSMOS counterpart. Declaring this keeps the vision honest about the gap.

#### A-7 · L1 QueryDeps injection boundary

**Add to Layer 1 section** (after L148, the "Query state" block):

> **QueryDeps injection boundary.** The query loop receives its LLM client, tool registry, permission policy, and telemetry emitter via an explicit `QueryDeps` dataclass at loop construction time — never imported from module scope inside the loop. This boundary is how CC keeps the engine test-isolatable (parity with `src/query/deps.ts`) and how KOSMOS keeps Phase-1 `Scenario1` E2E runnable without side effects on live APIs.

**Evidence**: `.references/claude-code-sourcemap/restored-src/src/query/deps.ts` defines `QueryDeps`. KOSMOS Spec 013 (`013-scenario1-e2e-route-safety`) effectively relies on this pattern but it is nowhere in vision.

#### A-8 · L361 Roadmap Phase 2 — partial-complete marker

**Current** (L361, approximate):
> ### Phase 2 — Multi-agent swarm

**Amended**: add a status line directly under the heading:

> Status: **partial** — Spec 027 mailbox IPC shipped (2026-04-14); ministry-specialist agents (출산 보조금, 건강보험, 교통) and the coordinator synthesis pipeline remain open. See Initiative #2 and the CC→KOSMOS Phase 2 Migration meta-Epic (sub-Epics B–F) for the remaining work.

**Evidence**: `gh api graphql` confirms Spec 027 closed; Initiative #2 remains `OPEN`.

#### A-9 · Onboarding screen — KOSMOS brand + PIPA consent

**Add a new sub-section under Layer 5** (Context Assembly) **or** a new Appendix "Onboarding and brand":

> **Citizen onboarding.** First-launch presents a dedicated onboarding sequence derived from CC's step registry (`src/components/Onboarding.tsx`) with the developer-domain steps (API key, OAuth, terminal fonts) replaced by citizen-domain equivalents:
>
> 1. **KOSMOS brand splash** — render the orbital-ring logo (`assets/kosmos-logo-dark.svg` / icon component equivalent) with the wordmark `KOSMOS` and subtitle `KOREAN PUBLIC SERVICE MULTI-AGENT OS`. Palette: background `#0a0e27` → `#1a1040`; ring/core gradient `#60a5fa`/`#a78bfa`/`#818cf8`/`#6366f1`; wordmark `#e0e7ff`; subtitle `#94a3b8`; satellite nodes `#34d399` / `#f472b6` / `#93c5fd` / `#c4b5fd`.
> 2. **PIPA consent** — KOSMOS-original step (no CC analog). Mandatory under PIPA §15 before any tool call can execute; records consent version, timestamp, and AAL gate.
> 3. **Public-API scope acknowledgment** — enumerate the `data.go.kr` ministries the session will query (KOROAD, KMA, HIRA, NMC, …) and their data categories; citizen must acknowledge before Layer-2 adapters go live.
> 4. **Theme picker** — deferred until a light/high-contrast theme ships; the Phase 1 TUI runs the `dark` theme only.

**Evidence**: `assets/` contains 8 brand files; color palette extracted directly from `kosmos-banner-dark.svg` and `kosmos-logo.svg`. The current `tui/src/theme/dark.ts` uses `rgb(0,204,204)` for `background` which has **no basis in the SVG palette** — this is a placeholder inherited from CC that must be replaced with the KOSMOS navy (`#0a0e27`) in the same PR that ports the onboarding splash. Current TUI has no onboarding component; the gap is explicit.

#### A-10 · CC keyboard-shortcut migration — Tier 1/2/3 reference

**Add a new sub-section under Layer 5 (TUI)** or cross-reference into the new Appendix above:

> **Keyboard-shortcut migration.** CC defines 65 bindings across 20 contexts (`src/keybindings/defaultBindings.ts`). KOSMOS currently implements 5 (Enter, y/Y, n/N/Esc, Backspace/Delete, IME passthrough for modifiers). The Tier plan below is the authoritative migration scope for Phase 2:
>
> - **Tier 1 (pre-citizen-launch blocker)**: `ctrl+c` (interrupt active agent), `ctrl+d` (clean exit), `escape` in InputBar (cancel draft, gated on `!ime.isComposing`), `ctrl+r` (history search), `up`/`down` in InputBar (history prev/next, gated on empty buffer).
> - **Tier 2 (post-launch hardening)**: `pageup`/`pagedown`, `ctrl+l` (redraw), `shift+tab` (cycle PermissionMode — binds A-5), `ctrl+_` (undo), `ctrl+shift+c` (copy selection).
> - **Tier 3 (deferred until dependent specs)**: `ctrl+x ctrl+k` (killAll — needs multi-worker), `ctrl+e` (external editor), `meta+p` (modelPicker — KOSMOS uses K-EXAONE only), `ctrl+s` (stash), `ctrl+v` (image paste).
>
> IME safety rule: every binding that mutates the input buffer MUST check `!useKoreanIME().isComposing` before acting (Hangul composition must not be interrupted by a shortcut).

**Evidence**: Full 65-binding catalog in R2 research output (see References). Current KOSMOS 5-binding surface inventoried across `tui/src/components/input/InputBar.tsx`, `tui/src/components/coordinator/PermissionGauntletModal.tsx`, `tui/src/hooks/useKoreanIME.ts`.

---

### Part B — Meta-Epic "CC→KOSMOS Phase 2 Migration" sub-Epic breakdown

The meta-Epic is scoped as **nine sub-Epics**, labelled A–I. Each sub-Epic maps to a concrete CC source region and a concrete KOSMOS gap. The recommended execution order (critical path first) is **G → B → A → H → I → D → C → E → F**.

| ID | Title | CC source | KOSMOS gap | Priority |
|---|---|---|---|---|
| **G** | **Initiative #2 sub-issue re-link** (data-integrity fix) | — | `trackedIssues` edge empty; 7 Epics listed in body but never linked via Sub-Issues API | **P0 — blocker** |
| **B** | Permission v2 — PermissionMode spectrum + persistent rule store | `src/utils/permissions/{permissions,PermissionMode,bypassPermissionsKillswitch,dangerousPatterns,filesystem}.ts` | No mode concept; TUI `PermissionGauntletModal` is per-call only | **P0 — Tier 1 shortcut (shift+tab) + TUI parity + PIPA audit trail** |
| **A** | IPC stdio hardening — structured frames, backpressure, reconnect | `src/services/api/` (REST) vs. KOSMOS `src/kosmos/ipc/stdio.py` | JSONL-over-stdio shipped in 287; no framing spec, no reconnect, no replay | P1 |
| **H** | Onboarding + brand port (binds A-9) | `src/components/Onboarding.tsx` step registry | No onboarding screen; `dark.ts` background token placeholder; logo never rendered in TUI | P1 |
| **I** | Shortcut Tier 1 port (binds A-10) | `src/keybindings/defaultBindings.ts` + `src/hooks/useGlobalKeybindings.tsx` | 5/65 bindings implemented | P1 |
| **D** | Context Assembly v2 — memdir User + Project tiers (binds A-6) | `src/memdir/memdir.ts` + `src/memdir/paths.ts` | System + Session tiers only; no `~/.kosmos/memory/` | P2 |
| **C** | Ministry Specialists — 출산 보조금 / 건강보험 / 교통 workers | `src/coordinator/coordinatorMode.ts` + `src/tasks/InProcessTeammateTask/` | Spec 027 mailbox shipped; no ministry-specific workers yet | P2 |
| **E** | Korean IME — composition-aware shortcut gating, Hangul width | `src/hooks/useKeybindings.ts` (no IME notion in CC) | `useKoreanIME.ts` exists; not integrated with Tier 1 keybindings | P2 |
| **F** | Scenario 2+3 E2E — multi-ministry coordination walk-throughs | — (KOSMOS original; uses `pytest @pytest.mark.live`) | Scenario 1 done (Spec 013); Scenarios 2+3 not specced | P3 |

**Why G is P0**: without a repaired sub-issue graph, `/speckit-taskstoissues` output for the meta-Epic cannot be traced; GraphQL-only issue-tracking (AGENTS.md hard rule) fails at the Initiative level.

**Why B is P0**: PermissionMode is a prerequisite for the Tier 1 `shift+tab` binding in sub-Epic I, for the PIPA audit trail that every tool call downstream of Spec 024 must write, and for TUI feature parity with CC's mode-toggle dialog.

---

### Part C — Execution protocol

1. **This PR** (ADR-006 + vision.md amendments A-1..A-10 + this ADR) is the gate. No sub-Epic branches open until this PR is merged.
2. **Sub-Epic G** runs first as a one-off fix (not a full `/speckit-specify` cycle) because it is a GraphQL mutation sequence, not a code change. Traceable artefact: a GraphQL mutation transcript posted as a comment on Initiative #2 and on each re-linked Epic, plus a post-fix `gh api graphql` query confirming `trackedIssues.nodes` is non-empty and pageInfo exhausted.
3. **Sub-Epics B, A, H, I** run in parallel under Agent Teams (AGENTS.md § Agent Teams: 3+ independent tasks ⇒ parallel Sonnet teammates) once G is done, each following the standard Spec Kit cycle (specify → plan → tasks → analyze → taskstoissues → implement).
4. **Sub-Epics D, C, E, F** stage sequentially after B ships because they depend on the PermissionMode spectrum (D and C must audit-trail through Layer 3; E's keybinding integration requires Tier 1 bindings from I; F's E2E scenarios need B's audit contracts).

---

## Consequences

**Positive:**

- `docs/vision.md` becomes re-readable without contradicting shipped reality: L37/L57/L85/L114/L361 all line up with `main`.
- The meta-Epic has nine named sub-Epics with concrete CC source citations; any reviewer can verify "where does X come from in CC" with a single `grep` under `.references/claude-code-sourcemap/restored-src/`.
- Onboarding brand decisions are ADR-locked: no future PR can change the KOSMOS palette or add a step without citing A-9.
- The 65-binding CC catalog is triaged into Tier 1/2/3 with IME safety rules; no more ad-hoc keybindings.
- The Initiative #2 sub-issue data bug is exposed and scheduled; future `gh api graphql` walks will no longer lie.

**Negative / Trade-offs:**

- Vision.md mutates in the same PR as this ADR. AGENTS.md requires vision changes to sit behind an ADR; this PR satisfies that but also means the PR size is larger than a pure vision edit would be.
- Ten amendments in one PR is a heavy review load. Mitigation: every amendment cites its exact evidence path; reviewer workflow is `grep` + `git show` per amendment, not re-reading vision.md whole.
- The shortcut Tier 1 list depends on the Permission v2 (sub-Epic B) landing before `shift+tab` binds correctly. This ordering is explicit in Part C but adds a cross-Epic dependency.
- The brand palette change in sub-Epic H requires replacing the `dark.ts` `background` token (currently `rgb(0,204,204)`) which is a visible regression for anyone who had memorised the CC-cyan background. Mitigation: the `#0a0e27` navy matches every KOSMOS brand asset and no user has requested the CC-cyan look.

---

## Alternatives Rejected

- **Defer vision amendments to a separate follow-up PR**: Rejected. AGENTS.md rule requires vision + ADR in the same PR. Splitting would introduce a window where vision.md contradicts this ADR.
- **Fold the shortcut plan into sub-Epic I's spec only (no ADR entry)**: Rejected. Shortcut migration crosses Layer 3 (Permission mode toggle) and Layer 5 (TUI); without an ADR cross-reference, the Tier plan drifts once sub-Epic I starts writing specs.
- **Drop sub-Epic G (treat the Initiative #2 empty-edge as a documentation bug, not an issue-graph bug)**: Rejected. AGENTS.md hard rule pins issue tracking to GraphQL `trackedIssues`; the body text is not authoritative. Leaving the edge empty means future tracking claims are wrong.
- **Retire Mastra from the reference table entirely (not just the "Phase 2 TUI layer reference" phrasing)**: Rejected. Mastra remains useful as a typed tool-graph reference; only the "Phase 2 TUI" role is obsolete.

---

## References

- `.references/claude-code-sourcemap/restored-src/src/keybindings/defaultBindings.ts` — 65 binding catalog
- `.references/claude-code-sourcemap/restored-src/src/components/Onboarding.tsx` — CC onboarding step registry
- `.references/claude-code-sourcemap/restored-src/src/coordinator/coordinatorMode.ts` — AsyncLocalStorage swarm
- `.references/claude-code-sourcemap/restored-src/src/utils/permissions/{permissions,PermissionMode,bypassPermissionsKillswitch}.ts`
- `.references/claude-code-sourcemap/restored-src/src/query/deps.ts` — QueryDeps injection boundary
- `.references/claude-code-sourcemap/restored-src/src/memdir/memdir.ts` — memdir tier
- `specs/031-five-primitive-harness/research.md § 1` — CC primitive-mapping table
- `specs/027-agent-swarm-core/` — file-based mailbox IPC
- `specs/287-tui-ink-react-bun/` — TUI port (PR #1295 merged)
- `assets/kosmos-{logo,logo-dark,banner-dark,icon}.{svg,png}` — brand assets
- `docs/vision.md` — target of amendments A-1..A-10
- ADR-003 — Bun + Ink + React TUI stack
- ADR-004 — Claude Code sourcemap port policy
- AGENTS.md — Agent Teams, GraphQL-only issue tracking, vision-change PR rules
- Initiative #2 (Phase 2 — Multi-Agent Swarm) — target parent for the meta-Epic and sub-Epic G
