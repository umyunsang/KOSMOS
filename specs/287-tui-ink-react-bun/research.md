# Phase 0 Research: Full TUI (Ink + React + Bun)

**Branch**: `287-tui-ink-react-bun` | **Date**: 2026-04-19
**Feeds**: `plan.md` § Technical Context, `data-model.md`, `contracts/`, `tasks.md`

This document (a) resolves every `NEEDS CLARIFICATION` from `plan.md` § Technical Context (none open at exit), (b) validates the spec's Deferred Items table per Constitution Principle VI, and (c) maps every design decision to a concrete reference. Decisions are presented in the format `Decision / Rationale / Alternatives considered`.

---

## 1. Constitution Principle VI: Deferred Items Validation

**Spec deferred table** (`spec.md` § Scope Boundaries & Deferred Items → Deferred to Future Work): 13 rows; all 13 carry `NEEDS TRACKING` in the Tracking Issue column.

**Body scan** for unregistered deferral phrases (patterns: `separate epic`, `future epic`, `Phase [2+]`, `v2`, `deferred to`, `later release`, `out of scope for v1`): all matches lie inside the deferred-items table. Zero orphan deferrals in spec body.

**Verdict**: Principle VI is satisfied **at plan time**. `NEEDS TRACKING` entries are the expected pre-taskstoissues state; `/speckit-taskstoissues` will create 13 placeholder issues and back-fill the spec per constitution text (§ Principle VI: "creates placeholder issues for any 'NEEDS TRACKING' markers and back-fills the spec with the issue number"). No blocker raised.

| Deferred row | Reason | Target | Resolution by |
|---|---|---|---|
| Web UI / mobile UI | Out of scope for terminal platform | Phase 3+ | `/speckit-taskstoissues` placeholder |
| Voice I/O | Skipped for MVP | Phase 3+ | `/speckit-taskstoissues` placeholder |
| Plugin/skill system, Buddy, KAIROS, Remote, Vim | Claude Code upstream modules not mapped | Phase 3+ / Future Initiative | `/speckit-taskstoissues` placeholder |
| Custom theme DSL, Multi-window, Windows-native, diff bot, a11y CI | Not required for MVP | Phase 3+ | `/speckit-taskstoissues` placeholder |

---

## 2. Reference Ledger (Constitution Principle I)

Every design decision in `plan.md` maps here to a concrete reference source. This ledger satisfies the "Reference source rule" in AGENTS.md and Principle I's mandatory reference mapping.

### 2.1 TUI framework stack (Bun + Ink 7 + React 19.2)

**Decision**: TypeScript 5.6+, Ink v7.0.0, React 19.2, Bun v1.2.x, `@inkjs/ui` v2.
**Rationale**:

- Ink is Claude Code's production TUI framework — confirmed by `restored-src/src/ink/` (29 files reconstructed from Claude Code 2.1.88). Lifting Ink's reconciler + layout intact preserves rendering behavior.
- Ink v7 requires React 19.2 + Node 22 compatibility per the Ink releases changelog. Bun v1.2.x provides Node-22-compatible runtime + package manager + test runner in one binary, reducing build surface vs Node + pnpm + vitest.
- Gemini CLI (`.references/gemini-cli/packages/cli/`) runs Ink on Node (not Bun) but provides the second reference for structure: hooks, theme system, `overflowToBackbuffer`.
- `@inkjs/ui` v2 is the official Ink component library — ships TextInput / Spinner / Select / Select-all that Claude Code uses in permission prompts.

**Alternatives considered**:

- **Raw Blessed / neo-blessed**: No React model; rejected — diverges from Claude Code's architecture; loses upstream diff traceability.
- **Node + tsx/vitest instead of Bun**: Functional, but doubles the tool count for no win. Bun's `Bun.spawn` + built-in test runner collapses the TUI infra into one runtime.
- **Deno**: Supports JSX but not Ink 7 out of the box; `useSyncExternalStore` pattern interactions unproven in Deno; rejected.

**References**:

- `.references/claude-code-sourcemap/restored-src/src/ink/` — 29 files (reconciler.ts, layout/, renderer.ts, root.ts, etc.)
- `.references/gemini-cli/packages/cli/` — Apache-2.0 Ink TUI structure
- Ink changelog — https://github.com/vadimdemedes/ink/releases (Node 22 + React 19.2 requirement per v7.0.0 notes)
- Bun docs — https://bun.sh/docs/api/spawn (extra-fd limitation, oven-sh/bun#4670)

### 2.2 IPC mechanism: `Bun.spawn` JSONL over stdin/stdout/stderr

**Decision**: `Bun.spawn` with newline-delimited JSON (JSONL) over stdio. No extra fds.
**Rationale**:

- FR-001 mandates `Bun.spawn`. oven-sh/bun#4670 confirms Bun's `spawn` does not pass extra fds — protocols relying on socket-handle passing fail silently. Protocol must fit on stdin (requests in) + stdout (events out) + stderr (log + crash trace).
- JSONL matches Claude Code's `restored-src/src/services/api/client.ts` streaming-chunk format (newline-delimited JSON over HTTP SSE) — the TUI rendering pipeline is already shaped around line-framed JSON. Using the same framing on stdio keeps the rendering spine upstream-identical; only the source fd changes.
- Python's `asyncio.StreamReader` + `sys.stdout.buffer.write(...)` + `.flush()` gives natural backpressure handling for the 100 ev/s soak.

**Alternatives considered**:

- **Unix domain socket**: Would allow extra fds and bidirectional handles, but requires parent-spawn-socket dance; rejected because `Bun.spawn` handles stdio natively and platform portability (Windows best-effort) is better over stdio.
- **HTTP localhost + SSE**: Keeps Claude Code's wire format identical, but adds a TCP listener + port management + security surface. Rejected — stdio avoids all of that.
- **MessagePack over stdio**: Denser, but loses debuggability (plain `cat` cannot inspect frames). Rejected for citizen-scale operator ergonomics.

**References**:

- `.references/claude-code-sourcemap/restored-src/src/services/api/client.ts` — SSE streaming chunk decoder (model for the TUI receiver path)
- Bun spawn docs + oven-sh/bun#4670 issue
- Python `asyncio.StreamReader.readuntil(b"\n")` — stdlib pattern

### 2.3 IPC frame types: generated from Pydantic v2

**Decision**: TypeScript IPC frame types are emitted from Python Pydantic v2 models by `tui/scripts/gen-ipc-types.ts`. Generated output at `tui/src/ipc/frames.generated.ts` is committed and never hand-edited. Runtime `zod` schemas are a parallel belt-and-braces check on the TS side.
**Rationale**:

- Constitution Principle III (Pydantic v2 strict typing) forbids `Any`; Spec 031's SC-008 hard rule forbids duplicating Python schemas in TypeScript. Code-gen from Pydantic is the only path that satisfies both.
- Pydantic 2 exposes `model.model_json_schema()` → JSON Schema Draft 2020-12. Two Python tools consume it cleanly: `datamodel-code-generator` (JSON Schema → TS via json-schema-to-typescript) and `pydantic-to-typescript` (direct). Both are devtools, not runtime deps; neither ships in the compiled TUI binary.
- Claude Code's upstream types are hand-written TS (no code-gen) because the upstream backend is Anthropic's API, which publishes an OpenAPI schema. KOSMOS inverts this — the backend is our own Python, so Pydantic is the source of truth.

**Alternatives considered**:

- **Hand-duplicated TS types**: Rejected by FR-003 ("no hand-duplicated schemas"). Drift between Python and TS is a known failure mode.
- **tRPC**: Elegant but HTTP-first; over-specified for stdio JSONL; adds a runtime dependency. Rejected.
- **Protocol Buffers / Cap'n Proto**: Heavier, requires `.proto` as a third source of truth. Rejected — Pydantic already is the source of truth.
- **io-ts / valibot instead of zod**: Functional, but zod has wider community + better ergonomics with discriminated unions (`z.discriminatedUnion("kind", [...])`). Acceptable swap in future; zod chosen for v1.

**References**:

- Spec 031 contracts (`specs/031-five-primitive-harness/contracts/*.schema.json`) — already Pydantic-generated JSON Schema
- `datamodel-code-generator` docs — https://github.com/koxudaxi/datamodel-code-generator
- `pydantic-to-typescript` — https://github.com/phillipdupuis/pydantic-to-typescript
- zod discriminated unions — https://zod.dev/?id=discriminated-unions

### 2.4 Five-primitive renderers

**Decision**: 14 dedicated Ink components (`tui/src/components/primitive/`), keyed by the discriminated union `kind` + subtype fields emitted by Spec 031 envelopes. Unknown variants fall through to `<UnrecognizedPayload />`.
**Rationale**:

- FR-008 forbids string sniffing. Pydantic's `Literal[...]` discriminator + Zod's `z.discriminatedUnion` force exhaustive `switch` coverage at compile time.
- Claude Code's tool-result rendering in `restored-src/src/tools/*` follows the same pattern: one component per tool schema. The lift inverts subject but preserves structure.
- Semantic naming (FR-018: `temperature_c` not `TMP`) is enforced by Spec 022's tool facade — the TUI renders what the backend delivers; it never re-maps provider codes.

**Alternatives considered**:

- **Single generic renderer with schema-driven layout**: Rejected — opaque; breaks the 1:1 variant-to-component traceability Spec 031 requires.
- **Markdown-rendering only**: Rejected — loses the collapsible raw-JSON expander (FR-017), the `[MOCK: <reason>]` chip (FR-026), and the streaming event banner (FR-028). Ink components are the only path.

**References**:

- Spec 031 `plan.md` + `data-model.md` — 5-primitive envelope union
- Spec 022 `spec.md` — `lookup(mode, tool_id, params)` + `resolve_location` return variants
- `.references/claude-code-sourcemap/restored-src/src/tools/` — 30+ tool result renderers (structural analog)
- `restored-src/src/components/design-system/` — Box / Text / spinner primitives lifted to style the renderers

### 2.5 Command dispatcher + theme engine (User Story 2)

**Decision**: Lift `restored-src/src/commands/dispatcher.ts` + registry shape verbatim; subset the command set to `/save`, `/sessions`, `/resume`, `/new` + a future-proof registry slot for Phase 2 commands. Theme engine lifted from `restored-src/src/theme.ts` (and related); three built-in themes (`default`, `dark`, `light`) via `KOSMOS_TUI_THEME` env var.
**Rationale**:

- FR-036: registry shape MUST stay upstream-compatible for future diff tracking. Renaming or restructuring blocks `diff-upstream.sh` from locating the canonical file.
- Claude Code's `commands/` directory has 50+ entries (observed via `ls`); KOSMOS's v1 command set is 4. The registry can hold either — upstream shape is preserved even with a smaller enabled set.
- Theme tokens (`ThemeToken` named set, FR-040) forbid inline hex colors — this is Claude Code's existing pattern; lifting it avoids recreating a less-rigorous equivalent.

**Alternatives considered**:

- **Hand-roll a minimal dispatcher**: Rejected — violates FR-036 + sabotages upstream diff tracking (SC-9 spirit).
- **Full command-set lift (50+)**: Rejected for v1 — most Claude Code commands (`/debug-tool-call`, `/autofix-pr`, `/break-cache`) have no KOSMOS analog. Deferred items table is the correct place for extending the set.

**References**:

- `.references/claude-code-sourcemap/restored-src/src/commands/` (50+ commands, preserve registry shape)
- `restored-src/src/components/design-system/` + theme tokens
- `#468` env registry (FR-041 `KOSMOS_TUI_THEME` registration)

### 2.6 Korean IME strategy (R1 blocker)

**Decision**: Forced choice between (a) `@jrichman/ink@6.6.9` fork adoption and (b) Node `readline` hybrid. Decision codified in `docs/adr/NNN-korean-ime-strategy.md` **before** any IME code lands (FR-014, FR-057, SC-1 gate).
**Recommendation (pending ADR approval)**: Option (a) — `@jrichman/ink@6.6.9` fork.
**Rationale for recommendation**:

- Gemini CLI ships Option (a) in production — community-confirmed working for Korean (`.references/gemini-cli/package.json` pins `@jrichman/ink`). This is the single most proven data point.
- Option (b) (readline hybrid) has no public production reference; the cursor-position desync risk (R3) is concrete and debugging would fall to our two-person team.
- Option (a) pins us to Ink 6.6.9 (fork) vs Ink 7.0.0 (upstream). Ink 7 upgrades require fork tracking — acceptable cost vs the alternative's unknowns.

**Alternatives considered**:

- **Option (b) readline hybrid**: Lower lock-in (stays on upstream Ink 7) but higher integration risk. Retained as ADR option for authoring-phase reconsideration.
- **Wait for upstream Ink Hangul support**: Rejected — Claude Code issues #3045/#22732/#22853/#27857/#29745 are open; no upstream patch forecast.

**References**:

- `.references/gemini-cli/package.json` (pins `@jrichman/ink`)
- Claude Code issues #3045, #22732, #22853, #27857, #29745 (all referenced in spec R1)
- `specs/011-cli-tui-interface/spec.md` — historical IME risk discussion

### 2.7 Virtualization + double-buffered redraws

**Decision**: Lift `VirtualizedList` from `restored-src/`, add Gemini CLI's `overflowToBackbuffer` pattern on top. Message state via `useSyncExternalStore` store pattern (≈35-line store lifted from `restored-src/`).
**Rationale**:

- FR-048/049/050/051 are prescriptive on lifts. No structural decision to make; this section documents the source paths.
- `useSyncExternalStore` (React 18+ primitive) is the pattern Claude Code uses to avoid re-rendering the full message list on every chunk. Only the affected `<StreamingMessage />` re-renders. Gemini CLI uses the same pattern.
- `overflowToBackbuffer` (Gemini CLI terminology) writes scrollback to the terminal's alt-screen history without re-rendering historical messages — essential for multi-hundred-message conversations.

**Alternatives considered**:

- **react-window / react-virtualized**: Designed for DOM; Ink is a different reconciler. Rejected.
- **Hand-roll virtualization**: Rejected by FR-048 (must lift).

**References**:

- `restored-src/src/components/` (search `VirtualizedList` / `virtualization`)
- `.references/gemini-cli/packages/cli/src/` (`overflowToBackbuffer` pattern)
- React `useSyncExternalStore` — https://react.dev/reference/react/useSyncExternalStore

### 2.8 Permission-gauntlet modal (User Story 4)

**Decision**: Lift `restored-src/src/components/ToolPermission*.tsx` and related permission-flow components wholesale. TUI's role: render the modal, collect citizen decision, relay `permission_response` IPC frame.
**Rationale**:

- Claude Code's permission-gauntlet UX is the authoritative interaction for "sensitive action requires user approval". FR-045 mandates the lift. The Spec 027 coordinator mailbox emits `permission_request` messages; the TUI is the visible endpoint.
- Component list (scanned via `ls restored-src/src/components/`): `ToolPermission/`, `BypassPermissionsModeDialog.tsx`, `ApproveApiKey.tsx`, `useCanUseTool.tsx` — all lift candidates. A mapping table lives in `data-model.md § Upstream Component Map`.

**Alternatives considered**:

- **Hand-roll modal**: Rejected by FR-045.
- **Separate OS-level dialog**: Rejected — the TUI is terminal-only; citizens in remote-shell contexts need in-terminal flow.

**References**:

- `restored-src/src/components/ToolPermission*.tsx`
- `restored-src/src/hooks/useCanUseTool.tsx`
- Spec 027 `data-model.md` — `permission_request` mailbox schema
- `docs/vision.md § Layer 6` — human interface permission-delegation flow

### 2.9 Backend: `kosmos-backend --ipc stdio` entrypoint

**Decision**: Add one module `src/kosmos/ipc/stdio.py` implementing an `asyncio` reader+writer loop that dispatches JSONL IPC frames to existing Spec 031 primitive handlers + Spec 027 coordinator mailbox. Add one CLI flag `--ipc stdio` to `src/kosmos/cli/__main__.py`. No new Python runtime deps (AGENTS.md hard rule).
**Rationale**:

- Existing Phase 1 CLI (`src/kosmos/cli/`) is retained unchanged per spec Assumptions. The `--ipc stdio` mode is an additional dispatch target — it reuses the same primitive registry, session store, observability span emission.
- Pure-stdlib implementation: `asyncio.StreamReader` bound to `sys.stdin.buffer`, `sys.stdout.buffer.write` + `.flush()` for output. Pydantic v2 `model_validate_json` + `model_dump_json` handle framing. Zero new imports beyond stdlib.
- Observability: every IPC frame emits a `kosmos.ipc.frame` span child of the session span (Spec 021), so frame-level latency is visible in the same OTEL pipeline (#501).

**Alternatives considered**:

- **Standalone Python binary**: Rejected — duplicates entrypoint infrastructure for no isolation gain.
- **Rewrite CLI as IPC-first**: Rejected — keeps the Phase 1 CLI as a fallback per spec Assumption.

**References**:

- `src/kosmos/cli/__main__.py` (existing entrypoint)
- `src/kosmos/primitives/` (existing primitive registry)
- Spec 027 `data-model.md § Coordinator` (mailbox contract)
- Spec 021 `plan.md` (OTEL span emission pattern)

### 2.10 Source attribution (FR-011/012/013, SC-9)

**Decision**: Every file lifted from `restored-src/` carries the exact header:

```ts
// Source: .references/claude-code-sourcemap/restored-src/<original-path> (Claude Code 2.1.88, research-use)
```

`tui/NOTICE` declares research-use reconstruction and attributes Anthropic. `tui/scripts/diff-upstream.sh` compares each lifted file to its source and reports divergence.
**Rationale**:

- Licensing: the reconstructed source is research-use only. Without attribution, any lift is a legal risk. The header + NOTICE + diff script form the three-layer compliance surface.
- Traceability: SC-9 "upstream diffs remain traceable". A grep for the header pinpoints every ported file. CI can assert the header exists on every `.tsx` / `.ts` in `tui/src/components/`, `tui/src/ink/`, `tui/src/commands/`, `tui/src/coordinator/`, `tui/src/hooks/`.
- ADR: `docs/adr/NNN-claude-code-sourcemap-port.md` is the single approval point for this approach (FR-057).

**Alternatives considered**:

- **Separate lift-manifest file**: Rejected — splits the attribution from the code, making header-less files possible by mistake.
- **No attribution, treat lift as clean-room**: Rejected — legally unsafe + violates SC-9.

**References**:

- `restored-src/README.md` — research-use disclaimer
- `tui/NOTICE` (to be created) — Anthropic attribution

---

## 3. Outstanding NEEDS CLARIFICATION

None. All technical context fields in `plan.md` are resolved at plan-time.

---

## 4. Decision Summary Table

| # | Decision | Reference |
|---|---|---|
| 1 | Bun + Ink 7 + React 19.2 + TypeScript 5.6 stack | `restored-src/src/ink/`, Ink changelog, Gemini CLI |
| 2 | `Bun.spawn` JSONL over stdio (no extra fds) | oven-sh/bun#4670, `restored-src/src/services/api/client.ts` |
| 3 | IPC types code-gen from Pydantic v2 | Constitution III, Spec 031 contracts, `datamodel-code-generator` |
| 4 | 14 dedicated Ink renderers, `<UnrecognizedPayload />` fallback | Spec 031 envelopes, `restored-src/src/tools/` structural analog |
| 5 | Lift command dispatcher + theme engine verbatim | `restored-src/src/commands/`, `restored-src/src/theme.ts` |
| 6 | Korean IME: forced ADR choice; recommend `@jrichman/ink@6.6.9` fork | Gemini CLI `package.json`, Claude Code IME issues |
| 7 | Lift VirtualizedList + `useSyncExternalStore` + `overflowToBackbuffer` | `restored-src/src/components/`, Gemini CLI, React docs |
| 8 | Lift permission-gauntlet modal wholesale | `restored-src/src/components/ToolPermission*`, Spec 027 |
| 9 | Python `src/kosmos/ipc/stdio.py` + `--ipc stdio` CLI flag; no new deps | AGENTS.md hard rule, existing CLI |
| 10 | Header + NOTICE + diff script for every lifted file | `restored-src/README.md`, FR-011/012/013 |

**Phase 0 exit**: All NEEDS CLARIFICATION resolved; all deferred items validated; all design decisions traced to concrete references. Ready for Phase 1.
