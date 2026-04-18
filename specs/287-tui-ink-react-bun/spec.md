# Feature Specification: Full TUI (Ink + React + Bun)

**Feature Branch**: `287-tui-ink-react-bun`
**Created**: 2026-04-19
**Status**: Draft
**Input**: Epic #287 — Full TUI (Ink + React + Bun)

## Overview

This spec governs the port of Claude Code 2.1.88's Ink + React terminal UI onto the KOSMOS Python backend. The migration thesis (per `project_tui_architecture.md` memory and Epic #287): keep Claude Code's Ink + React + `useSyncExternalStore` rendering spine, its IPC/streaming chunk protocol, its virtualized list, its permission-gauntlet UX, its theme + session commands — **replace only the backend boundary**. Claude Code's Anthropic API client (`services/api/`) becomes KOSMOS's Python backend over stdio JSONL; Claude Code's `tools/*` developer-domain implementations become thin Ink renderers over KOSMOS's 5-primitive surface (Spec 031 / #1052).

**Primary migration source**: `.references/claude-code-sourcemap/restored-src/src/` — 1,884 `.ts`/`.tsx` files reconstructed from Claude Code 2.1.88's published source map (research-use only). Every file lifted from this source MUST carry a header comment:

```
// Source: .references/claude-code-sourcemap/restored-src/<original-path> (Claude Code 2.1.88, research-use)
```

**Stack**: TypeScript + Ink v7.0.0 + React 19.2 + Bun v1.2.x. Backend stays Python; only `tui/` is TypeScript (per AGENTS.md Hard Rule).

**Co-develops lockstep with**: Spec 031 / #1052 (five-primitive harness). Contract sync cadence: every 2 merged PRs on either side, run a joint smoke.

**Depends on**: #507 (Spec 022 rendering contract), #1052 (Spec 031 five-primitive), #13 (agent swarm coordinator), #14 (specialist role labels), #468 (KOSMOS_TUI_* env registry), #501 (observability span emission).

---

## User Scenarios & Testing

### User Story 1 — IPC Bridge + Streaming Chunk Renderer Swap (Priority: P1)

A citizen launches the KOSMOS TUI via `bun run tui`. The TypeScript process spawns the KOSMOS Python backend as a child process (`uv run kosmos-backend --ipc stdio`) and communicates via newline-delimited JSON (JSONL) over stdin/stdout. Streaming assistant text renders chunk-by-chunk in real time.

**Why P1**: The entire TUI is inert until the IPC bridge is live. This is the foundational sub-epic A deliverable.

**Independent Test**: Can be tested by running `bun run tui` against a Python backend stub that emits pre-scripted JSONL. No live `data.go.kr` calls required.

**Acceptance Scenarios**:

1. **Given** `bun run tui` is invoked, **When** the TypeScript process starts, **Then** it spawns `uv run kosmos-backend --ipc stdio` via `Bun.spawn` (stdin/stdout/stderr only — no extra fds per oven-sh/bun#4670) within 2 seconds.
2. **Given** the backend emits `assistant_chunk` JSONL frames, **When** the TUI receives them in order, **Then** each chunk is appended to the streaming message component within 50 ms of receipt.
3. **Given** a 10-minute soak test at 100+ IPC events/sec using a fixture stream, **When** the test completes, **Then** zero frames are dropped and the process exits cleanly.
4. **Given** the backend process exits with a non-zero code or emits to stderr, **When** the exit is detected, **Then** the TUI surfaces a crash notice (with redacted env secrets per #468 guard patterns) within 5 s.
5. **Given** `assistant_chunk` frames arrive, **When** the user has not pressed Enter, **Then** chunks appear in FIFO order — the TUI never reorders streaming output.

---

### User Story 2 — Command Dispatcher + Theme Engine + Session Commands (Priority: P1)

A citizen types slash commands (`/save`, `/sessions`, `/resume`, `/new`) and uses the themed terminal interface. The command dispatcher and theme engine are lifted from Claude Code's `commands/` directory with Korean + English localization of user-visible text while keeping the internal registry shape identical to the upstream source.

**Why P1**: Session management and theming are required for Phase 1 CLI feature parity (SC-6). The command shape must stay upstream-compatible for future diff tracking.

**Independent Test**: Can be tested with `ink-testing-library` by injecting `/save` into the input stream and asserting a `session_event` IPC frame is emitted.

**Acceptance Scenarios**:

1. **Given** a user types `/sessions` at the prompt, **When** Enter is pressed, **Then** the TUI sends a `session_event` IPC request and renders the session list returned by the backend.
2. **Given** a user types `/save`, **When** Enter is pressed, **Then** the current session is persisted via the backend IPC and a confirmation message is rendered.
3. **Given** `KOSMOS_TUI_THEME` is set to `dark` | `light` | `default`, **When** the TUI starts, **Then** the theme token set matching the env var is applied to all Box/Text components.
4. **Given** an unknown slash command is entered, **When** Enter is pressed, **Then** the dispatcher renders a help snippet listing valid commands; it does not crash.
5. **Given** the command registry is loaded, **When** inspected programmatically, **Then** its shape is structurally identical to the `commands/` registry shape in `.references/claude-code-sourcemap/restored-src/src/commands/` so upstream diffs apply cleanly.

---

### User Story 3 — Five-Primitive Renderers (Priority: P1)

Every return variant of the 5-primitive surface (Spec 031 / #507) has a dedicated Ink component. No string sniffing — all discrimination happens on the Pydantic-generated `kind` field in the JSONL `tool_result` frame. Unknown `kind` falls through to `<UnrecognizedPayload />`.

**Why P1**: Without renderers, tool results are invisible in the TUI. This is the core UX value proposition of the platform.

**Independent Test**: Each component variant can be tested in isolation with `ink-testing-library` using a single fixture JSON file per discriminator arm. No IPC, no backend process required.

**Acceptance Scenarios**:

1. **Given** a `tool_result` frame with `kind: "lookup"` and subtype `LookupPoint`, **When** rendered, **Then** `<PointCard />` shows key-value pairs and a collapsible raw-JSON expander.
2. **Given** a `tool_result` frame with `kind: "lookup"` and subtype `LookupTimeseries`, **When** rendered, **Then** `<TimeseriesTable />` uses semantic column headers (`temperature_c`, `precipitation_mm`) — never raw provider codes (TMP/PCP/REH).
3. **Given** a `tool_result` frame with `kind: "lookup"` and subtype `LookupList` or `LookupCollection`, **When** rendered, **Then** `<CollectionList />` shows paginated rows and a "Load more" affordance that triggers a follow-up `lookup(mode="fetch", page=...)` IPC frame.
4. **Given** a `tool_result` frame with `kind: "lookup"` and subtype `LookupError`, **When** `reason` is `auth_required`, **Then** `<ErrorBanner />` renders the permission-consent dialog; for other `reason` values it renders the appropriate icon + retry affordance.
5. **Given** a `tool_result` frame with `kind: "resolve_location"`, **When** rendered, **Then** all populated slots (`coords`, `adm_cd`, `address`, `poi`) are shown via their respective components (`<CoordPill />`, `<AdmCodeBadge />`, `<AddressBlock />`, `<POIMarker />`).
6. **Given** a `tool_result` frame with `kind: "submit"` and family `pay`, **When** rendered, **Then** `<SubmitReceipt />` shows the family-specific payload; if `mock_reason` is present, a `[MOCK: <reason>]` chip is displayed.
7. **Given** a `tool_result` frame with `kind: "subscribe"` yielding `AsyncIterator` frames, **When** the stream is open, **Then** `<EventStream />` shows the modality banner (CBS broadcast / REST pull / RSS 2.0) and updates live; on terminal event, `<StreamClosed />` shows the `close_reason`.
8. **Given** a `tool_result` frame with `kind: "verify"` and family `gongdong_injeungseo`, **When** rendered, **Then** `<AuthContextCard />` displays the Korea-published tier (one of 18 values) as the **primary label** and NIST AAL as an advisory-only secondary hint; the primary label is never omitted when the hint is absent.
9. **Given** a `tool_result` frame with an unrecognized `kind` value, **When** rendered, **Then** `<UnrecognizedPayload />` is displayed; a warning is logged; no crash occurs; structure is never guessed.

---

### User Story 4 — Coordinator Phase + Per-Worker Status + Permission-Gauntlet Modal (Priority: P2)

Multi-agent activity from #13 is visible in the TUI. Coordinator phase transitions and per-worker status rows surface in the conversation view. When a worker raises a `permission_request`, the TUI blocks further input until the citizen approves or denies, then delivers the response back via IPC.

**Why P2**: Required for multi-ministry scenarios (SC-7) but can be deferred until the IPC bridge and basic renderers are stable.

**Independent Test**: Can be tested with `ink-testing-library` by injecting scripted `coordinator_phase` and `permission_request` IPC frames and asserting the expected modal and status row renders.

**Acceptance Scenarios**:

1. **Given** a `coordinator_phase` IPC frame with `phase: "Research"`, **When** received, **Then** the phase indicator updates to `Research` without disrupting the active streaming message.
2. **Given** a `worker_status` IPC frame for worker `transport-specialist`, **When** received, **Then** a status row appears showing the specialist's `role_id` label and current primitive iteration.
3. **Given** a `worker_status` frame where `status` includes a `permission_request`, **When** received, **Then** the TUI renders the permission-gauntlet modal (lifted from Claude Code's permission-gauntlet UX in `restored-src/`), blocks all user input, and awaits a `permission_response` from the citizen.
4. **Given** a citizen approves the permission request, **When** the modal is confirmed, **Then** a `permission_response: "granted"` IPC frame is sent and input is unblocked.
5. **Given** a scripted 3-specialist scenario (Transport + Health + Emergency from #14), **When** executed end-to-end, **Then** all three worker status rows are visible concurrently and update independently.

---

### User Story 5 — Korean IME Input Module (Priority: P2)

Korean character composition (Hangul 초성/중성/종성) works correctly in the conversation input area. The spec forces a decision between two proven approaches: (a) adopt the `@jrichman/ink` fork (Gemini CLI's strategy), or (b) readline hybrid (Node readline handles input, Ink renders only). The chosen approach is codified in an ADR.

**Why P2**: Upstream Ink's `useInput` cannot buffer Hangul composition. Claude Code issues #3045, #22732, #22853, #27857, #29745 confirm this is a hard blocker for Korean users. An ADR must exist before implementation (SC-4).

**Independent Test**: Can be tested by injecting Hangul composition sequences via `stdin` in a headless terminal process and asserting the composed character (e.g., `ㅎ` + `ㅏ` + `ㄴ` → `한`) is emitted as a single composed glyph.

**Decision Required (forced choice — no silent adoption)**:

| Option | Description | Trade-off |
|--------|-------------|-----------|
| (a) `@jrichman/ink@6.6.9` fork | Gemini CLI's path; community-confirmed working for Korean; pins `ink: npm:@jrichman/ink@6.6.9` in `tui/package.json` | Ties us to fork; Ink 7 upgrades require fork tracking |
| (b) readline hybrid | Node readline handles raw input; Ink renders; composition events fire correctly | More integration complexity; possible cursor/position desync |

**ADR requirement**: The decision MUST be documented in `docs/adr/NNN-korean-ime-strategy.md` and approved before any IME code lands.

**Acceptance Scenarios**:

1. **Given** the chosen IME strategy is implemented, **When** a user types `한글` on macOS (Korean IME) and on Linux (fcitx5 or ibus), **Then** the composed text appears correctly in the input area.
2. **Given** the user is mid-composition (e.g., partial syllable block), **When** they press Backspace, **Then** the partial syllable is deleted atomically (not character by character in jamo form).
3. **Given** an ADR exists in `docs/adr/` choosing option (a) or (b), **When** a PR implementing IME lands, **Then** CI verifies the ADR exists as a precondition.

---

### User Story 6 — Session Persistence via IPC (Priority: P3)

The TUI reuses the existing Phase 1 Python JSONL session store. No duplicate TUI-side state. The TUI reads and writes sessions exclusively through backend IPC calls.

**Why P3**: Session persistence is critical for production use but can be implemented after the rendering pipeline is stable.

**Independent Test**: Can be tested by starting a session, sending `/save`, restarting the TUI with `/resume <id>`, and asserting the conversation history is restored.

**Acceptance Scenarios**:

1. **Given** a user sends `/save`, **When** the IPC response arrives, **Then** the session ID is displayed and the JSONL store is written by the backend (not the TUI process).
2. **Given** a user sends `/sessions`, **When** the list arrives, **Then** each session entry shows its ID, creation timestamp, and turn count.
3. **Given** a user resumes a session via `/resume <id>`, **When** the backend sends the conversation history, **Then** prior turns are rendered in the message list without re-streaming.
4. **Given** the TUI holds zero session state locally, **When** the TUI process is killed and restarted, **Then** the JSONL store is intact and the session can be resumed from the backend.

---

### User Story 7 — Performance: Virtualization + Double-Buffered Redraws (Priority: P3)

The TUI handles long conversations and high event rates without visual degradation. Virtual scrolling, double-buffered rendering, and the `useSyncExternalStore` pattern are lifted directly from Claude Code's restored source.

**Why P3**: Required for the 100+ events/sec soak test (SC-2) but only visible at scale.

**Independent Test**: Can be tested by replaying a 1,000-message fixture at 100 events/sec via `stdin` injection and asserting no dropped frames and ≤ 50 ms per redraw.

**Acceptance Scenarios**:

1. **Given** a conversation with 100+ messages, **When** new messages arrive, **Then** only the visible viewport is re-rendered (virtualized via `VirtualizedList` from `restored-src/`).
2. **Given** 100+ IPC events/sec are received, **When** redraws occur, **Then** no frames are dropped and the event queue does not grow unbounded.
3. **Given** the `useSyncExternalStore` store pattern is used for message state, **When** a new chunk arrives, **Then** only the affected message component re-renders (not the full list).
4. **Given** the `overflowToBackbuffer` pattern from Gemini CLI is applied, **When** the conversation exceeds terminal height, **Then** scrollback is available without re-rendering historical messages.

---

### Edge Cases

- What happens when the backend emits a malformed JSONL frame (not valid JSON)? → The TUI logs a parse error and renders `<UnrecognizedPayload />` for that frame; it does not crash.
- What happens when the `kind` field is absent from a `tool_result` frame? → Treated as unknown `kind`; falls through to `<UnrecognizedPayload />`.
- What happens when a `subscribe` stream never sends a terminal event? → The TUI times out after `KOSMOS_TUI_SUBSCRIBE_TIMEOUT_S` seconds (default: 120) and renders `<StreamClosed reason="timeout" />`.
- What happens when the verify renderer receives an unknown tier value (not in the 18-value enum)? → Displays the raw tier string with a warning chip; NIST AAL hint shown if available.
- What happens when CJK character width calculation is wrong (ink#688, ink#759 edge cases)? → The TUI logs a width-calc warning; text may wrap at a non-ideal point but must never panic.
- What happens on Windows? → Best-effort only; Linux + macOS are primary targets per Epic #287 scope.

---

## Requirements

### Functional Requirements

#### IPC Bridge (FR-001 – FR-010)

- **FR-001**: The TUI MUST spawn the Python backend as `uv run kosmos-backend --ipc stdio` via `Bun.spawn`, using only stdin/stdout/stderr (no extra fds — oven-sh/bun#4670 limitation).
- **FR-002**: The IPC protocol MUST be newline-delimited JSON (JSONL). Each frame MUST have a `kind` discriminator field. The full frame type union is:
  `user_input` | `assistant_chunk` | `tool_call` | `tool_result` | `coordinator_phase` | `worker_status` | `permission_request` | `permission_response` | `session_event` | `error`
- **FR-003**: TypeScript IPC frame types MUST be generated from the Python Pydantic v2 models — no hand-duplicated schemas. A code-gen step in `tui/scripts/gen-ipc-types.ts` MUST run before any type is hand-written.
- **FR-004**: The TUI MUST detect backend process crash (non-zero exit or stderr flush) within ≤ 5 s and surface a crash notice in the terminal. Crash notices MUST redact all `KOSMOS_`-prefixed environment variable values (per #468 guard patterns).
- **FR-005**: IPC frames MUST be delivered to the renderer in FIFO order per session. The TUI MUST NOT reorder frames.
- **FR-006**: `assistant_chunk` frames MUST be appended to the streaming message component within ≤ 50 ms of receipt.
- **FR-007**: The IPC bridge MUST sustain ≥ 100 events/sec for ≥ 10 minutes with zero dropped frames (soak test evidence required for SC-2).
- **FR-008**: `tool_result` frames MUST be dispatched to the correct renderer via a discriminated `kind` field — no string sniffing of payload body content.
- **FR-009**: On clean `session_event: "exit"` IPC frame or `Ctrl-C`, the TUI MUST send `SIGTERM` to the backend process and wait ≤ 3 s before `SIGKILL`.
- **FR-010**: The IPC bridge MUST log every frame receive/send at `DEBUG` level using the `KOSMOS_TUI_LOG_LEVEL` env var; default is `WARN`.

#### Source Attribution (FR-011 – FR-013)

- **FR-011**: Every file lifted from `.references/claude-code-sourcemap/restored-src/` MUST carry a header comment:
  ```
  // Source: .references/claude-code-sourcemap/restored-src/<original-path> (Claude Code 2.1.88, research-use)
  ```
- **FR-012**: `tui/NOTICE` MUST declare the research-use reconstruction and attribute Anthropic.
- **FR-013**: An upstream-diff procedure MUST be documented: a script `tui/scripts/diff-upstream.sh` compares each lifted file against its source in `.references/claude-code-sourcemap/restored-src/` and reports divergence.

#### Korean IME (FR-014 – FR-016)

- **FR-014**: The spec MUST force a decision between (a) `@jrichman/ink@6.6.9` fork adoption and (b) readline hybrid before any IME code lands. The decision MUST be documented in an ADR under `docs/adr/`.
- **FR-015**: The chosen IME strategy MUST produce correctly composed Hangul characters on macOS (Korean IME) and Linux (fcitx5 / ibus).
- **FR-016**: Mid-composition Backspace MUST delete the partial syllable block atomically, not character by character in jamo form.

#### Five-Primitive Renderers (FR-017 – FR-035)

- **FR-017**: `lookup` → `LookupPoint` or `LookupRecord` MUST render via `<PointCard />`: key-value table, collapsible raw-JSON expander.
- **FR-018**: `lookup` → `LookupTimeseries` MUST render via `<TimeseriesTable />` using semantic column headers only — raw provider codes (TMP/PCP/REH) MUST NOT appear.
- **FR-019**: `lookup` → `LookupList` / `LookupCollection` MUST render via `<CollectionList />` with paginated rows and a "Load more" affordance that emits a follow-up `lookup(mode="fetch", page=...)` IPC frame.
- **FR-020**: `lookup` → `LookupDetail` MUST render via `<DetailView />` for nested detail on a selected list row.
- **FR-021**: `lookup` → `LookupError` MUST render via `<ErrorBanner />`. When `reason == "auth_required"`, the permission-consent dialog (wired to #13 coordinator permission chain) MUST be shown. All other `reason` values MUST map to distinct icon + color + retry affordance.
- **FR-022**: `resolve_location` → `coords` slot MUST render via `<CoordPill />` (WGS84 lat/lon + confidence).
- **FR-023**: `resolve_location` → `adm_cd` slot MUST render via `<AdmCodeBadge />` (10-digit code + Korean name).
- **FR-024**: `resolve_location` → `address` slot MUST render via `<AddressBlock />` (road + jibun + zipcode).
- **FR-025**: `resolve_location` → `poi` slot MUST render via `<POIMarker />` (POI id + canonical name).
- **FR-026**: `submit` → family payload MUST render via `<SubmitReceipt />`. All five family arms MUST be handled: `pay`, `issue_certificate`, `submit_application`, `reserve_slot`, `check_eligibility`. When `mock_reason` is present, a `[MOCK: <reason>]` chip MUST be displayed (values: `tee_bound`, `payment_rail`, `pii_gate`, `delegation_absent`).
- **FR-027**: `submit` → error MUST render via `<SubmitErrorBanner />` with revocation/rollback hint.
- **FR-028**: `subscribe` → streaming `AsyncIterator` frames MUST render via `<EventStream />`. A modality banner (CBS broadcast / REST pull / RSS 2.0) MUST be shown at stream open. RSS `guid` dedup status and CBS storm throttle indicator MUST be surfaced.
- **FR-029**: `subscribe` → terminal event MUST render via `<StreamClosed />` showing `close_reason` (`exhausted` / `revoked` / `timeout`).
- **FR-030**: `verify` → 6-family result MUST render via `<AuthContextCard />`. The **primary label** MUST be one of the 18 Korea-published tier values. NIST AAL MUST be shown as an advisory-only secondary hint. The primary label MUST NOT be omitted when the NIST hint is absent.
- **FR-031**: `verify` → 6-family discriminator chip MUST show one of: `gongdong_injeungseo` / `geumyung_injeungseo` / `ganpyeon_injeung` / `digital_onepass` / `mobile_id` / `mydata`.
- **FR-032**: `verify` → downgrade / expiry MUST render via `<AuthWarningBanner />` with tier downgrade notice. NIST AAL hint drift MUST be logged but MUST NOT block the UI.
- **FR-033**: Any `tool_result` frame with an unrecognized `kind` MUST render via `<UnrecognizedPayload />`. A warning MUST be logged. The TUI MUST NOT crash or attempt to infer payload structure.
- **FR-034**: Every renderer variant MUST have a fixture-driven `ink-testing-library` component test exercising each discriminated-union arm. No live `data.go.kr` calls in renderer tests.
- **FR-035**: All renderer fixtures MUST be sourced from recorded responses in #507 (Spec 022) and #1052 (Spec 031); no hand-crafted fictional data.

#### Command Dispatcher + Theme + Session (FR-036 – FR-042)

- **FR-036**: The command dispatcher MUST be lifted from `restored-src/src/commands/` with its internal registry shape preserved so upstream diffs apply cleanly.
- **FR-037**: User-visible command text MUST be localized to Korean + English; internal command identifiers MUST remain in English.
- **FR-038**: `/save`, `/sessions`, `/resume`, `/new` MUST be supported as first-class session commands, backed by backend IPC `session_event` frames.
- **FR-039**: The theme engine MUST support three built-in themes: `default`, `dark`, `light`. Theme MUST be selected via `KOSMOS_TUI_THEME` env var and documented in `docs/configuration.md`.
- **FR-040**: Theme tokens MUST be a named set (`ThemeToken`) consumed by all Box/Text components — no inline hex colors.
- **FR-041**: `KOSMOS_TUI_THEME` MUST be registered in the #468 env var registry.
- **FR-042**: An unknown slash command MUST render a help snippet listing valid commands; the dispatcher MUST NOT crash.

#### Multi-Agent Surface (FR-043 – FR-047)

- **FR-043**: `coordinator_phase` IPC frames MUST update the phase indicator component (`Research | Synthesis | Implementation | Verification`) without disrupting any active streaming message.
- **FR-044**: `worker_status` IPC frames MUST render a per-worker status row showing `role_id` label (from #14) and current primitive iteration.
- **FR-045**: When `worker_status` surfaces a `permission_request`, the TUI MUST render the permission-gauntlet modal (lifted from Claude Code's permission-gauntlet UX), block all user input, and await citizen approval or denial.
- **FR-046**: The citizen's approval/denial MUST be returned via a `permission_response` IPC frame within the same session. Input is unblocked only after the response is sent.
- **FR-047**: The coordinator surface MUST be lifted from `restored-src/src/coordinator/` with the same attribution header requirement (FR-011).

#### Performance + Virtualization (FR-048 – FR-052)

- **FR-048**: `VirtualizedList` MUST be lifted from `restored-src/` with only the IPC-boundary adapter changed; the `overflowToBackbuffer` pattern from Gemini CLI fills any ambiguity.
- **FR-049**: Double-buffered rendering on conversation redraws MUST be used (Claude Code's existing pattern from `restored-src/`).
- **FR-050**: Message state MUST use the `useSyncExternalStore` store pattern lifted from Claude Code (≈35-line store). Only the affected message component should re-render on new chunk arrival.
- **FR-051**: The TUI MUST sustain ≥ 100 IPC events/sec with no dropped frames on a MacBook Air M1 (soak test target).
- **FR-052**: Scrollback MUST be available via `overflowToBackbuffer` for conversations exceeding terminal height, without re-rendering historical messages.

#### Observability (FR-053 – FR-054)

- **FR-053**: The TUI MUST emit `gen_ai.tool_loop.iteration` spans with `kosmos.session.id` correctly attributed, routed through the #501 OTEL collector.
- **FR-054**: Span emission MUST NOT be synchronous on the render thread; it MUST be fire-and-forget via an async queue.

#### Accessibility (FR-055 – FR-056)

- **FR-055**: Keyboard-only navigation MUST be supported for all interactive components (modal approval, session list selection, "Load more", etc.).
- **FR-056**: Screen-reader accessibility (Ink `aria-*` equivalents) MUST be verified by a manual test checklist committed to `tui/docs/accessibility-checklist.md`.

#### ADR Requirement (FR-057)

- **FR-057**: An ADR MUST exist in `docs/adr/` approving the Bun + TypeScript + Ink stack, the Claude Code sourcemap port approach (licensing + attribution + research-use declaration), and the Korean IME strategy before any TUI code lands (SC-1 gate).

### Key Entities

- **`IPCFrame`**: Discriminated union on `kind` field (`user_input` | `assistant_chunk` | `tool_call` | `tool_result` | `coordinator_phase` | `worker_status` | `permission_request` | `permission_response` | `session_event` | `error`). Generated from Python Pydantic v2 models via code-gen.
- **`PrimitiveEnvelope`**: 5-arm discriminated union mirroring Spec 031 — `LookupEnvelope` | `ResolveLocationEnvelope` | `SubmitEnvelope` | `SubscribeEnvelope` | `VerifyEnvelope`. Nested within `tool_result` IPC frames.
- **`CoordinatorPhase`**: Enum `Research | Synthesis | Implementation | Verification`. Carried in `coordinator_phase` IPC frames from #13.
- **`WorkerStatus`**: Per-worker status record: `worker_id`, `role_id` (from #14), `current_primitive`, `status` (`idle | running | waiting_permission | error`).
- **`PermissionRequest`**: Citizen-facing permission prompt: `request_id`, `worker_id`, `primitive_kind`, `description_ko`, `description_en`, `risk_level`.
- **`SessionEvent`**: Session lifecycle events: `save` | `load` | `list` | `resume` | `new` | `exit`. Backed by the Phase 1 Python JSONL store — no TUI-side duplicate state.
- **`ThemeToken`**: Named token set consumed by all Box/Text components: `primary`, `secondary`, `error`, `warning`, `success`, `muted`, `background`, `border`.

---

## Success Criteria

Copied verbatim from Epic #287:

- **SC-1**: ADR in `docs/adr/` approves the Bun + TypeScript + Ink stack + the Claude Code sourcemap port approach (licensing + attribution + research-use declaration) before any TUI code lands (per `AGENTS.md`).
- **SC-2**: IPC bridge handles 100+ events/sec without dropped messages over a 10-minute soak test.
- **SC-3**: Every #507 / #1052 primitive return variant and every `ResolveBundle` slot has a dedicated renderer; a fixture-driven component test exercises each discriminated-union arm (5 primitives × all variants).
- **SC-4**: Korean IME input produces correctly composed characters in the conversation view.
- **SC-5**: Backend crash is detected and surfaced in the TUI within 5 s.
- **SC-6**: Phase 1 Python CLI feature parity — session persistence, `/save`, `/sessions`, `/resume`, streaming markdown, 3 themes — all round-trip through the TUI.
- **SC-7**: Multi-agent coordinator phase + per-worker status render correctly for a scripted 3-specialist scenario (Transport + Health + Emergency from #14).
- **SC-8**: Manual smoke test of Scenario 1 (route safety) and a Phase 2 multi-ministry scenario both complete through the Ink TUI.
- **SC-9**: Every file lifted from `.references/claude-code-sourcemap/restored-src/` carries a header comment citing its source path + Claude Code version (`2.1.88`) + the research-use notice — so upstream diffs remain traceable.

---

## Assumptions

- `Bun.spawn` is the IPC mechanism; extra fds beyond stdin/stdout/stderr are NOT used (oven-sh/bun#4670 constraint). The entire protocol fits on stdin/stdout/stderr.
- Ink v7.0.0 requires Node 22 + React 19.2. The `tui/package.json` pins these exactly.
- CJK character width is handled by `string-width`; known edge cases (ink#688, ink#759) are documented in `tui/docs/cjk-width-known-issues.md`.
- The Phase 1 Python CLI (`src/kosmos/cli/`) is retained unchanged as a fallback + CI smoke target. This Epic delivers an additional front-end.
- `.references/claude-code-sourcemap/restored-src/` is read-only; KOSMOS-local adaptations live only in `tui/`.
- TypeScript strict mode is enabled in `tui/tsconfig.json`.
- No new Python runtime dependencies are introduced by this spec (AGENTS.md hard rule).
- `bun build --compile` is used for single-binary distribution; cross-OS builds are best-effort.

---

## Scope Boundaries & Deferred Items

### Out of Scope (Permanent)

- **Web UI / mobile UI**: KOSMOS is a terminal-based platform; a web front-end would require a fundamentally different rendering stack.
- **Replacing the Phase 1 Python CLI**: The CLI remains for CI smoke and low-capability terminals. This Epic ships an additional front-end.
- **Rendering of per-adapter raw provider codes** (e.g., KMA TMP/PCP/REH): The TUI consumes only semantic names the tool facade specifies.
- **Any renderer for the deleted 8-verb Mock Facade** (closed #994): Superseded by the 5-primitive surface of #1052; `check_eligibility`, `reserve_slot`, `subscribe_alert`, `pay`, `issue_certificate`, `submit_application` as standalone top-level tools are retired.
- **Go or Rust TUI components**: AGENTS.md hard rule prohibits Go and Rust.

### In Scope for v1

| Sub-Epic | Key Deliverables |
|----------|-----------------|
| A — IPC Bridge | `Bun.spawn` JSONL bridge, JSONL frame types from Pydantic code-gen, crash detection ≤5s, soak test ≥100 ev/s / 10 min |
| B — Dispatcher + Theme + Session | Command dispatcher lifted from `commands/`, Korean+English localization, `/save` `/sessions` `/resume` `/new`, 3 built-in themes, `KOSMOS_TUI_THEME` env var |
| C — Five-Primitive Renderers | All 14 renderer components (FR-017–FR-033), `<UnrecognizedPayload />`, fixture-driven `ink-testing-library` tests per arm |
| C — Coordinator Surface | Phase indicator, per-worker status rows, permission-gauntlet modal lifted from `restored-src/src/coordinator/` |
| D — IME + ADR | ADR choosing (a) fork or (b) readline hybrid; Hangul composition verified macOS + Linux |
| D — Virtualization + Perf | `VirtualizedList`, double-buffered redraws, `useSyncExternalStore`, `overflowToBackbuffer` |
| D — Session + Persistence | Session read/write via IPC only; no TUI-side JSONL store |

### Deferred to Future Work

| Item | Reason for Deferral | Target Epic/Phase | Tracking Issue |
|------|---------------------|-------------------|----------------|
| Web UI / browser-based interface | Requires different rendering stack; out of scope for terminal platform | Phase 3+ | NEEDS TRACKING |
| Mobile UI | Out of scope for terminal platform | Phase 3+ | NEEDS TRACKING |
| Voice input and voice output | Claude Code `voice/` module exists but skipped for MVP; requires speech pipeline | Phase 3+ | NEEDS TRACKING |
| Plugin / skill system (`plugins/`, `skills/` from Claude Code) | Complex extension lifecycle; not required for MVP primitives | Phase 3+ | NEEDS TRACKING |
| Buddy mode (`buddy/` from Claude Code) | Not mapped to any KOSMOS role; no equivalent backend | Phase 3+ | NEEDS TRACKING |
| KAIROS assistant mode (`assistant/` from Claude Code) | No equivalent backend; design TBD | Phase 3+ | NEEDS TRACKING |
| Remote sessions (`remote/` from Claude Code) | KOSMOS runs local; remote orchestration is a separate initiative | Future Initiative | NEEDS TRACKING |
| Vim mode (`vim/` from Claude Code) | Low priority for citizen users | Phase 3+ | NEEDS TRACKING |
| Custom theme DSL beyond 3 built-in themes | Not required for MVP; design TBD | Phase 3+ | NEEDS TRACKING |
| Multi-window / tiled layouts | Complex layout engine; not required for MVP | Phase 3+ | NEEDS TRACKING |
| Windows-native full support | Linux + macOS are primary; Windows is best-effort in v1 | Phase 3+ | NEEDS TRACKING |
| Upstream-diff auto-sync bot | Manual diff script sufficient for v1; bot automation deferred | Phase 3+ | NEEDS TRACKING |
| Accessibility: screen-reader automated CI | Manual checklist sufficient for v1; automated CI requires Ink a11y improvements | Phase 3+ | NEEDS TRACKING |

---

## Risks

| ID | Risk | Likelihood | Impact | Mitigation |
|----|------|-----------|--------|------------|
| R1 | **Korean IME (blocker)**: Upstream Ink's `useInput` cannot buffer Hangul composition. Claude Code issues #3045, #22732, #22853, #27857, #29745 confirm this. | High | High | Spec forces a decision: (a) `@jrichman/ink@6.6.9` fork (Gemini CLI's proven path) or (b) readline hybrid. Decision codified in ADR before any IME code. |
| R2 | **Claude Code upstream diff drift**: If Anthropic publishes a new Claude Code version, ported files may diverge from the updated upstream. | Medium | Medium | Every ported file carries an attribution header (FR-011). A `tui/scripts/diff-upstream.sh` script documents the comparison procedure. Manual review per release. |
| R3 | **Ink 7 vs. fork version skew**: If option (a) fork is chosen, Ink 7 upgrades require fork tracking. If option (b) is chosen, readline hybrid may desync cursor positions. | Medium | Medium | Mitigated by ADR (FR-014, FR-057). Version pinned in `tui/package.json`. Fork tracking cadence documented in ADR. |
| R4 | **Bun extra-fd limitation**: `Bun.spawn` does not support extra fds beyond stdin/stdout/stderr (oven-sh/bun#4670). Any IPC design relying on socket handle passing will fail. | High (confirmed) | High | Protocol is constrained to stdin/stdout/stderr from the start (FR-001). No workaround required if the constraint is respected. |
| R5 | **CJK width calculation edge cases**: `string-width` has known issues with some Hangul sequences (ink#688, ink#759). Text may wrap at non-ideal points. | Medium | Low | Documented in `tui/docs/cjk-width-known-issues.md`. Log a warning on overflow but do not crash. |

---

## References

- **Epic #287**: `gh issue view 287 --repo umyunsang/KOSMOS` — primary scope source; SC-1..SC-9 copied verbatim
- **Spec 031 / #1052**: Five-Primitive Harness Redesign — `specs/031-five-primitive-harness/spec.md` — defines `submit` / `subscribe` / `verify` envelopes the TUI must render
- **Spec 022 / #507**: MVP Main Tool — `specs/022-mvp-main-tool/spec.md` — defines `lookup` return variants and `resolve_location` bundle slots
- **Spec 027 / #13**: Agent Swarm Core — `specs/027-agent-swarm-core/spec.md` — coordinator phase + worker status IPC contract
- **`.references/claude-code-sourcemap/restored-src/`**: Claude Code 2.1.88 reconstructed TypeScript source (1,884 files); research-use only
- **`.references/gemini-cli/`**: Gemini CLI (Apache-2.0) — `overflowToBackbuffer` virtualization pattern
- **Spec 011**: `specs/011-cli-tui-interface/spec.md` — Korean IME Risk R1 historical context
- **Constitution v1.3.0 Principle VI**: Deferred Work Accountability — mandates Deferred Items table with tracking issues
- **`docs/vision.md § Layer 6`**: KOSMOS Layer 6 human interface boundary; permission-delegation flow
- **`AGENTS.md § Hard rules`**: TypeScript allowed only for the TUI layer; no Go/Rust; no new runtime dependencies without a spec-driven PR
- **Ink v7 changelog**: https://github.com/vadimdemedes/ink/releases — Node 22 + React 19.2 requirement
- **Bun spawn docs**: https://bun.sh/docs/api/spawn — extra-fd limitation (oven-sh/bun#4670)
- **`@jrichman/ink` fork**: https://www.npmjs.com/package/@jrichman/ink — Gemini CLI pins `6.6.9`
- **Claude Code IME issues**: #3045, #22732, #22853, #27857, #29745 — Hangul composition not buffered by upstream `useInput`
