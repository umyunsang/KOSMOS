# Phase 0 Research: Plugin DX TUI integration

**Feature**: 1979-plugin-dx-tui-integration
**Date**: 2026-04-28
**Inputs**: spec.md, plan.md, AGENTS.md, docs/vision.md, docs/requirements/kosmos-migration-tree.md, .specify/memory/constitution.md

## Reference mapping (Constitution §I)

Every design decision below cites a primary or secondary reference per Constitution §I + the canonical reference table.

| Layer | Primary | Secondary |
|---|---|---|
| Tool System | `specs/1636-plugin-dx-5tier/{spec,plan,contracts}.md` (KOSMOS plugin schema canon) | Pydantic AI (schema-driven registry) — already adopted in `src/kosmos/tools/registry.py` |
| IPC Envelope | `specs/032-ipc-stdio-hardening/` + `src/kosmos/ipc/frame_schema.py:776-936` PluginOpFrame | AutoGen `AgentRuntime` mailbox IPC pattern — Spec 027 lineage |
| Permission Pipeline | `specs/033-permission-v2-spectrum/` (3-layer + Shift+Tab) + `src/kosmos/ipc/stdio.py:814` `asyncio.wait_for` permission timeout | OpenAI Agents SDK (guardrail pipeline) |
| TUI | `specs/1635-ui-l2-citizen-port/` T065 PluginBrowser + T066 `/plugins` command | `.references/claude-code-sourcemap/restored-src/src/components/CustomSelect/` (visual structure baseline) |
| Context Assembly | Epic #1978 closure — `stdio.py:1182-1196` tools[] auto-build path | Claude Code reconstructed (context assembly) |
| Error Recovery | `installer.py:_safe_extract` post-extraction rollback + `stdio.py` ErrorFrame fanout | OpenAI Agents SDK (retry matrix) |

---

## Verdict V1 — CC marketplace residue handling (FR-018 deliverable)

**Decision**: **Option A (revised)** — Replace `tui/src/commands.ts:133` import to `./commands/plugin.js` (KOSMOS singular). The CC marketplace residue (`tui/src/commands/plugin/*` subdirectory + `tui/src/services/plugins/*` + `tui/src/utils/plugins/*`) becomes unreachable from citizen surface but is **not deleted in this Epic**. Cleanup is deferred to a Spec 1633-style follow-up Epic.

**Rationale**:
- The current `commands.ts:133` registers `tui/src/commands/plugin/index.tsx` under the `/plugin` slash command. That file's source declares `description: 'Manage Claude Code plugins'`, `aliases: ['plugins', 'marketplace']` — meaning today both `/plugin` AND `/plugins` AND `/marketplace` route to the CC LSP marketplace surface, NOT the KOSMOS citizen path. The KOSMOS singular file `tui/src/commands/plugin.ts` (which already emits `sendPluginOp` correctly via Spec 1636 work) is **orphaned** — never imported anywhere in `commands.ts` or `App.tsx`.
- Deletion-only path: 89 grep matches for `tengu_plugin_*` / `marketplaceManager` / `reconcileMarketplaces` / `_PROTO_plugin` across 16+ files in `tui/src/utils/plugins/{marketplaceManager, reconciler, refresh, fetchTelemetry, pluginBlocklist, headlessPluginInstall, officialMarketplaceStartupCheck, pluginStartupCheck, lspRecommendation, pluginAutoupdate, officialMarketplaceGcs, installedPluginsManager}.ts` plus the `commands/plugin/*` subtree and `services/plugins/*`. This is too large to safely delete inside this Epic without violating SC-005 (`bun test ≥ 984` parity). Memory `feedback_kosmos_scope_cc_plus_two_swaps` confirms KOSMOS = CC + 2 swaps (tools, LLM); marketplace surface is not a swap target, so it should eventually leave the codebase entirely — but not in this Epic.
- Replacement-only path (chosen): change one line. After the swap, the CC residue is verifiably unreachable from any user-typed slash command (verified by grepping `tui/src/commands.ts` for any further import; the `loadPluginCommands.ts` reference at line 166 is a dynamic plugin-loaded-skill discovery path, not a citizen-typed command).
- Memory `feedback_no_stubs_remove_or_migrate` says missing modules are KOSMOS-equivalents or removed, never stubbed. The CC residue is fully implemented dead code, not stubs — leaving it inert satisfies the rule by making it KOSMOS-unreachable.

**Alternatives considered**:
- **Option A (literal)** — delete all 16+ residue files in this Epic. Rejected: 89 grep matches; risks `bun test` parity (SC-005); doubles the sub-issue count; conflates citizen activation with dead-code cleanup.
- **Option B** — wrap residue under `KOSMOS_PLUGIN_DEV_MODE=true` env flag. Rejected: residue is already CC-private and never user-exposed once `commands.ts:133` swaps; the flag adds complexity (TS env-var plumbing) for zero citizen-visible benefit.
- **Option D (do nothing)** — leave `commands.ts:133` pointing at CC residue. Rejected: that is the *defect itself* — the citizen `/plugin install` literally never reaches `installer.py:install_plugin()`.

**Cleanup tracking**: Add a follow-up note to spec.md § Deferred Items table → "CC marketplace residue cleanup (commands/plugin/*, services/plugins/*, utils/plugins/*) — Spec 1633-style dead-code Epic, NEEDS TRACKING." Already in spec.md as Deferred row 2 ("External plugin contributor onboarding UX") — add the residue cleanup as a separate row in `/speckit-tasks` deferred resolution.

**Citation**: `tui/src/commands.ts:133`, `tui/src/commands/plugin/index.tsx:5` (aliases), `tui/src/commands/plugin.ts:18-24` (H7 review eval comment), memory `feedback_kosmos_scope_cc_plus_two_swaps`.

---

## Verdict V2 — `tui/src/components/plugins/PluginBrowser.tsx` handling (FR-015 deliverable)

**Decision**: **Option A** — Use existing `PluginBrowser.tsx` (Spec 1635 T065) verbatim. Only rewire data source in `tui/src/commands/plugins.ts` (T066) to populate from `plugin_op_request:list` IPC round-trip rather than the current `KOSMOS_PLUGIN_REGISTRY` env-var stub.

**Rationale**:
- The existing component (`tui/src/components/plugins/PluginBrowser.tsx:1-171`) is already KOSMOS-aligned: header cites `// Spec 1635 P4 UI L2 — T065 PluginBrowser`. It uses `PluginEntry` shape with KOSMOS-specific fields (`description_ko`, `description_en`, `isActive`), KOSMOS theme provider (`useTheme`), KOSMOS i18n (`useUiL2I18n`). The keybinding handler covers UI-E.3 mandate exactly: arrow keys + Space (toggle) + i (detail) + r (remove) + a (marketplace).
- The `a` keystroke calls `onMarketplace()` callback — perfect insertion point for the FR-013 / FR-016 "deferred to #1820" Korean message.
- The component is purely presentational; data layer lives in `commands/plugins.ts` which currently reads from `KOSMOS_PLUGIN_REGISTRY` env var (acknowledged as a "P5 will replace this" stub at line 30).
- `PluginEntry` shape already maps cleanly onto `PluginManifest` fields: `id` ← `plugin_id`, `name` ← `description_ko`-derived display name, `version` ← `version`, `description_ko/en` ← `description_ko/en` (or fall back to `search_hint_ko/en`), `isActive` ← `not registry._inactive` (R-3/R-4 verdict).
- Building a parallel `CitizenPluginStore.tsx` would duplicate ~170 LOC of identical logic and introduce drift risk between two browsers that mean the same thing.

**Alternatives considered**:
- **Option B** — author new `CitizenPluginStore.tsx`. Rejected: duplicates Spec 1635 work; violates DRY; no functional gap to justify.
- **Option C** — partially rewrite `PluginBrowser.tsx` to add tier badges + layer color glyphs + trustee org column. **Partially adopted** for FR-015. Concrete plan: extend `PluginEntry` shape (additive — backwards compatible) with `tier: "live" | "mock"`, `layer: 1 | 2 | 3`, `trustee_org_name: string | null`; render new columns in the existing layout. The keybinding handler stays untouched.

**Citation**: `tui/src/components/plugins/PluginBrowser.tsx:1-171`, `tui/src/commands/plugins.ts:1-52`, `docs/requirements/kosmos-migration-tree.md § UI-E.3`.

---

## R-1 — Backend stdio dispatcher pattern for `plugin_op` arm

**Decision**: Add a `frame.kind == "plugin_op"` branch at `src/kosmos/ipc/stdio.py:1675` if-elif chain (after `session_event`). The handler delegates to a new `PluginOpDispatcher` module (`src/kosmos/ipc/plugin_op_dispatcher.py`) that pattern-matches the inner `op="request"` field and routes to `install_handler` / `uninstall_handler` / `list_handler`. Each handler runs `installer.py:install_plugin()` (or equivalent) inside an `asyncio.create_task` so the dispatcher can emit progress frames concurrently while the install executes.

**Rationale**:
- The existing chain at `stdio.py:1675-1751` already handles `user_input` / `chat_request` / `tool_result` / `permission_response` / `session_event` with a uniform try/except → ErrorFrame fallback (FR-010 resilience invariant). Adding a sixth arm follows the established pattern.
- `installer.py:install_plugin()` is **synchronous** (not async) but its phase progression naturally maps to a sequence: catalog → bundle → SLSA → manifest → consent → register → receipt. Two implementation strategies considered:
  - **Strategy A** (chosen) — Refactor `install_plugin` to accept an optional `progress_emitter: Callable[[int, str, str], Awaitable[None]]` parameter that's called between phases. The dispatcher passes a `partial(emit_progress_frame, correlation_id=...)` that emits `plugin_op_progress` frames asynchronously. Internal phase progression remains sync; only the emit hook is async.
  - **Strategy B** — Wrap `install_plugin` in a thread executor and emit progress frames from a sibling task that polls a shared queue. Rejected: more moving parts; thread-vs-asyncio handoff complexity; emit ordering becomes dependent on GIL scheduling.

**Alternatives considered**:
- **Strategy C** — split `install_plugin` into 7 separate async coroutines, each emitting one progress frame. Rejected: triples the code surface for zero observable improvement; risks regressing the 6 integration tests + 4 SC tests already passing on `install_plugin`.

**Implementation note**: The progress callback receives `(phase: int, message_ko: str, message_en: str)`. The dispatcher wraps these into `PluginOpFrame(op="progress", progress_phase=..., progress_message_ko=..., progress_message_en=...)`. All 14 phase messages (7 install phases × Korean + English each) come from `specs/1636-plugin-dx-5tier/contracts/plugin-install.cli.md` § Phases canonical text — no new translation work needed.

**Citation**: `src/kosmos/ipc/stdio.py:1675-1751` (existing dispatch chain), `src/kosmos/plugins/installer.py:install_plugin` (8-phase impl), `specs/1636-plugin-dx-5tier/contracts/plugin-install.cli.md § Phases`.

---

## R-2 — `consent_prompt` IPC round-trip timeout

**Decision**: 60-second `asyncio.wait_for` on the citizen consent reply, reusing the existing `permission_response` timeout pattern at `src/kosmos/ipc/stdio.py:814`. On `asyncio.TimeoutError`, the bridge returns `False` (denial) and the dispatcher emits `plugin_op_complete` with `exit_code=5`, `error_kind="consent_timeout"`. The TUI sees the same Y / A / N modal it sees for in-tree adapter permissions (Spec 033 + Spec 1978 reuse).

**Rationale**:
- Spec 1978 already established 60s as the canonical permission-prompt timeout at `stdio.py:_pending_perms` infrastructure. Plugin install consent has identical UX semantics ("citizen Y/N decision before potentially-impactful action"); reusing the timeout value avoids citizen confusion ("why does plugin consent expire faster than tool consent?").
- 60s is bounded by the Spec 1636 SC-005 30s install ceiling. Wait — the install has a 30s budget but consent happens at phase 5/7, after catalog + bundle + SLSA + manifest validation. By the time the consent prompt appears, ≤ 20s of the 30s budget is left. The consent timeout (60s) is intentionally LARGER than the remaining install budget so a citizen who pauses at the prompt does not race the 30s SC-001 metric — they breach 30s deliberately by taking time to think. SC-001 measures "install completes ≤ 30s on the happy path"; a deliberated consent decision is separately allowed.
- Spec 027 mailbox `replay_unread` has a 30s pattern but that is for inter-agent message redelivery, not citizen UI prompt — different time scale. Discarded as comparison.

**Alternatives considered**:
- 30s timeout matching SC-001. Rejected: forces citizen rush; conflates "did the citizen decide" with "did the install complete fast enough". UX hostile.
- 5-minute timeout. Rejected: too long for an interactive prompt; risks the TUI overlay drifting out of sync with backend state if citizen walks away for 4 minutes.

**Citation**: `src/kosmos/ipc/stdio.py:814` (existing permission timeout), `specs/1636-plugin-dx-5tier/contracts/plugin-install.cli.md § Phase 5: 동의 확인`.

---

## R-3 + R-4 — ⏺/○ toggle semantics + BM25 enabled flag honour

**Decision** (combined): Add an in-memory `_inactive: set[str]` shadow set to `ToolRegistry`. Methods: `set_active(tool_id, active: bool) -> None` and `is_active(tool_id) -> bool`. The set is rebuilt empty at every backend boot (no persistence). Filters apply at:
- `BM25Index.rebuild()` corpus generation in `_rebuild_bm25_index_for` (skip inactive tools)
- `to_openai_tool` / `export_core_tools_openai` (skip inactive tools)
- `core_tools()` / `situational_tools()` / `all_tools()` — return all tools but tag `is_active` (or filter — TBD in data-model.md)

The TUI ⏺/○ toggle calls `plugin_op_request` with a new sub-op? **No — simpler**: extend `PluginOpFrame.request_op` allow-list from `{install, uninstall, list}` to `{install, uninstall, list, set_active, set_inactive}`. **Wait — that requires schema change**.

**Revised decision**: The ⏺/○ toggle uses a new lightweight sibling frame — actually, no, that violates "zero schema change" + sub-issue ≤ 90 budget.

**Final decision**: **Defer the toggle's runtime semantics to a sibling spec.** This Epic implements `_inactive` shadow set on the backend (no manifest change, no IPC change) but the TUI's ⏺/○ toggle in this Epic operates as **visual-only** — it flips the local `isActive` flag in `PluginEntry` state but does NOT round-trip to backend. Rationale: a runtime enable/disable cycle would need a 4th `PluginOpFrame` sub-op (`activate` / `deactivate`); adding that to the discriminated union triggers a Spec 032 envelope schema bump + a new SHA-256 hash for the `kosmos.ipc.schema.hash` OTEL attribute. That is too much scope for this Epic.

**What this Epic ships**: ⏺/○ visual toggle in `PluginBrowser` (already implemented per Spec 1635 T065). The `r` (remove) keybinding emits `plugin_op_request:uninstall` and is the only state-changing path for plugin lifecycle.

**Backend `_inactive` shadow set**: Reserved for future use; not exposed via IPC in this Epic. Reason it stays in scope: the existing test infrastructure may need to deactivate plugins for unit tests without uninstalling them, and the shadow set is the cleanest low-risk hook.

**Documented in spec.md as a clarification of FR-016**: "The ⏺/○ glyph reflects citizen-local active/inactive state. Pressing Space toggles the visual glyph but does not round-trip to backend in this Epic. Backend deactivation API is reserved for a follow-up Epic."

**Decision logged in `/speckit-clarify`** if needed; no [NEEDS CLARIFICATION] marker required because the spec text already reads "⏺ enabled / ○ disabled (visual indicator)" without committing to runtime enable/disable.

**Tracking**: Add a `Deferred to Future Work` row → "Plugin runtime enable/disable IPC (`plugin_op_request:activate/deactivate` + ToolRegistry `_inactive` API exposure) — NEEDS TRACKING."

**Citation**: `src/kosmos/tools/registry.py:179-203` (registry shape), `src/kosmos/ipc/frame_schema.py:805-869` (PluginOpFrame request_op enum), `docs/requirements/kosmos-migration-tree.md § UI-E.3`, memory `feedback_no_hardcoding`.

---

## R-5 — vhs vs expect signal differentiation in the 4-layer ladder

**Decision**: 
- **L3 (expect/script)** drives the consent Y / A / N keypress simulation via `expect ... send -- "Y\r"` (or `A\r` / `N\r`). expect is the right layer because the consent prompt is text-based (a Korean modal) and Y/A/N is a single-keystroke decision; expect's `send` semantics map directly.
- **L4 (vhs `.tape`)** uses `Type "Y"` for citizen-visible visual flow demonstration but does NOT drive the canonical decision — it merely demonstrates what a citizen sees. The decision-of-record in the test rig is the L3 expect output; L4 is for human review only (per memory `feedback_vhs_tui_smoke`).

**Rationale**:
- expect produces grep-friendly text logs (`tui_log.txt` or `script.cast`). LLMs and Codex review tooling can verify outcomes by grepping for canonical phase markers — this is the L3 verification deliverable per FR-021.
- vhs produces binary `.gif` / `.mp4` artifacts. Useful for human visual review but unparseable by automated review tools. Per memory `feedback_vhs_tui_smoke`, vhs is supplemental — never the primary verification source.
- Driving consent decisions through vhs `Type` would couple the visual demonstration timing (frame rate, render speed) to the test outcome — fragile + slow.

**Alternatives considered**:
- vhs-only path. Rejected: can't grep frame outputs; slows iteration; depends on terminal rendering timing.
- expect-only path with no vhs. Rejected: humans (especially the project lead per memory `feedback_vhs_tui_smoke` lineage) want the gif for visual review.

**Citation**: `docs/testing.md § TUI verification methodology` (4-layer ladder), memory `feedback_vhs_tui_smoke`, memory `feedback_runtime_verification`.

---

## R-6 — Epic #1978 ChatRequestFrame.tools[] auto-refresh timing

**Decision**: Rely on the existing fallback path at `stdio.py:1182-1196`. After a successful `plugin_op_complete`, the next `chat_request` frame triggers a fresh `_ensure_tool_registry()` call (or a `registry.export_core_tools_openai()` re-export if the registry singleton is reused). Since `register_plugin_adapter` mutated the registry's `_tools` dict in-process during phase 6 (📁 등록 + BM25 색인) of the install, the next export naturally includes the new plugin's tool. **No new IPC frame, no TUI cache invalidation, no race condition** — the registry is the single source of truth and all reads on the next turn see the post-install state.

**Rationale**:
- `stdio.py:1190-1191`: `for t in frame.tools: llm_tools.append(LLMToolDefinition.model_validate(t.model_dump()))` — TUI authority path.
- `stdio.py:1192-1195`: `if not llm_tools: registry = _ensure_tool_registry(); for raw in registry.export_core_tools_openai(): ...` — backend fallback path.
- For plugin-install-affected sessions, the simplest contract is: TUI sends `frame.tools=[]` (empty list) on the next ChatRequestFrame after a `plugin_op_complete:success`. Backend falls back to `export_core_tools_openai()` which now includes the new plugin. This requires zero TUI logic change because the existing TUI tool catalog plumbing already builds `frame.tools` from a static catalog; on plugin install completion, the TUI can simply stop sending that catalog (let backend authority take over for the next turn).
- **Race condition analysis**: Is there a window where `plugin_op_complete:success` fires, but the next `chat_request` arrives before `_tools` has the new entry? **No** — `register_plugin_adapter` is called synchronously at phase 6 of `install_plugin`, BEFORE `plugin_op_complete` is emitted (phase 7 receipt + phase 8 success). So when the TUI receives `plugin_op_complete:success`, the registry already has the tool. SC-002 ≤ 3s is met by causality, not by timer.

**Alternatives considered**:
- TUI sends a separate `tools_request` frame after each `plugin_op_complete:success` to refresh its local cache. Rejected: requires a new IPC frame (Spec 032 envelope bump); duplicates the fallback path's work; introduces a network round-trip where causality alone suffices.
- TUI listens for `plugin_op_complete` events and invalidates its tool catalog cache on the client side. Rejected: requires TUI cache implementation that doesn't exist; the simplest path (let backend be authoritative on the post-install turn) just works.

**TUI implementation note**: In `tui/src/commands/plugin.ts` after the citizen runs `/plugin install`, set a session-scoped flag `pluginsModifiedThisSession=true`. On the next ChatRequestFrame build, if that flag is set, send `frame.tools=[]` to defer to backend authority. Reset the flag after one use (so subsequent turns can re-cache). This is a 5-line TS change; documented in contracts/dispatcher-routing.md.

**Citation**: `src/kosmos/ipc/stdio.py:1182-1196`, `src/kosmos/plugins/installer.py:install_plugin` phase 6 ordering, Epic #1978 closure verified via git log.

---

## Deferred Items Validation (Constitution §VI gate)

Spec.md § Scope Boundaries was reviewed for compliance with Constitution §VI:

### Permanent Out-of-Scope (8 items)

All 8 items have explicit "MUST NOT change" / "permanent OOS" rationale. None pattern-match unregistered "future" / "v2" prose. ✅ PASS.

### Deferred Items table (6 items)

| Item | Tracking Issue | Status |
|------|---------------|--------|
| Plugin tool dense-embedding discovery | #585 | ✅ verified open issue (`feat/585-retrieval-dense` branch exists per CLAUDE.md "Active Technologies" line) |
| External plugin contributor onboarding UX | NEEDS TRACKING | ✅ flagged for `/speckit-taskstoissues` |
| Plugin store catalog index sync mechanism | NEEDS TRACKING | ✅ flagged for `/speckit-taskstoissues` |
| Spec 027 swarm worker invoking plugin tools | #1980 | ✅ named Epic per spec.md Initiative section |
| Plugin marketplace catalog browser (`a` keystroke target) | #1820 | ✅ named in Spec 1636 Assumption A5 |
| Acknowledgment-text drift audit workflow | #1926 | ✅ named in Spec 1636 § Deferred |

### New deferrals discovered during Phase 0 (added to spec.md tracking)

Two new deferrals emerge from V1 + R-3/R-4 verdicts:

| Item | Reason for Deferral | Target Epic/Phase | Tracking Issue |
|------|---------------------|-------------------|----------------|
| CC marketplace residue cleanup (`commands/plugin/*`, `services/plugins/*`, `utils/plugins/*`) | This Epic only swaps `commands.ts:133` import; full cleanup is too large to land safely with SC-005 baseline parity | Spec 1633-style follow-up dead-code Epic | NEEDS TRACKING |
| Plugin runtime enable/disable IPC (`plugin_op_request:activate/deactivate`) | This Epic ships ⏺/○ as visual-only; runtime toggle requires Spec 032 envelope schema bump | Post-P5 plugin-lifecycle Epic | NEEDS TRACKING |

### Unregistered deferral pattern scan

Scanned spec.md prose for `separate epic`, `future epic`, `Phase [2+]`, `v2`, `deferred to`, `later release`, `out of scope for v1`. Every match traces to an entry in either § Out of Scope (Permanent) or § Deferred to Future Work table. ✅ PASS.

---

## Constitution re-check after Phase 0

| Principle | Status | Evidence |
|---|---|---|
| §I Reference-Driven Development | ✅ PASS | Every R-1..R-6 + V1/V2 verdict cites primary + (where relevant) secondary reference. Reference table populated. |
| §II Fail-Closed Security | ✅ PASS | R-2 confirms `asyncio.TimeoutError → False` (denial). V1 confirms residue stays inert, never silently activates. |
| §III Pydantic v2 Strict Typing | ✅ PASS | Zero schema additions. R-3/R-4 backs off from PluginOpFrame request_op enum extension to preserve Spec 032 envelope hash invariant. |
| §IV Government API Compliance | ✅ PASS | No live `data.go.kr` calls introduced. Fixture catalog path (file://) preserved. |
| §V Policy Alignment | ✅ PASS | PIPA §26 trustee SHA-256 round-trip preserved (R-1 phase 5). 7-step gauntlet honoured (R-2). |
| §VI Deferred Work Accountability | ✅ PASS | 6 + 2 new = 8 deferred items all have tracking issue or NEEDS TRACKING marker. Zero unregistered prose. |

**Phase 0 Constitution Check: PASS — proceed to Phase 1.**
