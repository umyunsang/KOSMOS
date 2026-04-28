# Feature Specification: Plugin DX TUI integration (Spec 1636 closure)

**Feature Branch**: `feat/1979-plugin-dx-tui-integration`
**Created**: 2026-04-28
**Status**: Draft
**Input**: User description: Epic #1979 closure of Spec 1636 (Plugin DX 5-tier). Spec 1636 shipped backend infrastructure (`installer.py` 8-phase, `register_plugin_adapter`, `auto_discover`, `slsa.py`, `canonical_acknowledgment.py`, manifest schema, 4 example plugins, 50-item validation matrix, plugin store catalog). Two TUI activation gaps remain: (1) `plugin_op` IPC frame is defined as the 20th IPC arm with role allow-list `tui:request / backend:progress+complete` but emit count is zero — `tui/src/commands/plugin.ts:18-24` H7 review-eval comment explicitly defers the backend dispatcher wiring; (2) TUI `tui/src/services/plugins/*` and `tui/src/commands/plugin/*` are CC marketplace plugin port residue (`tengu_plugin_*` analytics + `_PROTO_plugin_name` PII tagging + claude.ai marketplace concepts), not the kosmos-migration-tree.md UI-E.3 citizen plugin store browser (⏺/○ Space i r a key bindings). Hard dep Epic #1978 (ChatRequestFrame + permission bridge) closed. This Epic closes Initiative #1631 alongside Epic #1980 (Agent Swarm TUI integration). Citation: `docs/vision.md`, `docs/requirements/kosmos-migration-tree.md § L1-B B8 + § UI-E.3 + § P5/P6`, `specs/1636-plugin-dx-5tier/{spec.md, plan.md, contracts/plugin-install.cli.md, contracts/manifest.schema.json}`, `src/kosmos/ipc/frame_schema.py:776-936` PluginOpFrame + `_v_plugin_op_shape` + `KIND_ROLE_ALLOWLIST` + `KIND_TERMINAL`, `src/kosmos/plugins/installer.py:install_plugin()`, `src/kosmos/plugins/registry.py:register_plugin_adapter` + `auto_discover`, `tui/src/commands/plugin.ts:18-24,90-167`, `docs/testing.md § TUI verification methodology`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Citizen completes a plugin install end-to-end inside the TUI (Priority: P1)

A citizen using KOSMOS wants the Seoul subway arrival capability that a community contributor published to `kosmos-plugin-store`. They type `/plugin install seoul-subway` in the REPL. The TUI shows a real-time progress overlay walking through the seven install phases (📡 catalog → 📦 bundle → 🔐 SLSA → 🧪 manifest → 📝 consent → 🔄 register + BM25 → 📜 receipt). When the overlay clears with a success banner, the citizen can use the new capability immediately — no shell exit, no restart, no copy-pasted command outside the TUI.

**Why this priority**: Without this story, the entire Spec 1636 5-tier infrastructure is unreachable from the citizen's primary surface. Today the slash command emits a `plugin_op_request` IPC frame that the backend dispatcher ignores, and the TUI shows the literal apology "(backend dispatcher not yet wired — use `kosmos plugin install` shell entry-point)". That apology shipped in `tui/src/commands/plugin.ts:90-167`. Closing this gap converts a documented dead-end into a working primary path. Every other story in this Epic depends on this loop being closed.

**Independent Test**: Run `/plugin install <fixture-name>` against a `file://` catalog + fixture bundle (matches the `_default_catalog_fetcher` + `_default_bundle_fetcher` `file://` branches in `installer.py`). Capture the run via the L3 expect/script text-log layer. Assert: a `plugin_op_request` frame leaves the TUI; seven `plugin_op_progress` frames arrive in order with bilingual Korean + English messages; a `plugin_op_complete` frame arrives with `result="success"`, valid `receipt_id` (`rcpt-` prefix), `exit_code=0`; the receipt JSON is appended under `~/.kosmos/memdir/user/consent/`; the install root contains `~/.kosmos/memdir/user/plugins/<plugin_id>/`; the wall-clock duration is ≤ 30 s (Spec 1636 SC-005).

**Acceptance Scenarios**:

1. **Given** the citizen runs `/plugin install seoul-subway` against a fixture catalog with a valid bundle and SLSA provenance, **When** the install proceeds, **Then** seven `plugin_op_progress` frames arrive in phase order (1 → 7), the consent prompt round-trips through the TUI, and a `plugin_op_complete` frame arrives with `result="success"`, `exit_code=0`, and a non-empty `receipt_id` within 30 seconds.
2. **Given** the citizen presses **N** at the consent prompt, **When** the backend receives the rejection, **Then** the backend emits `plugin_op_complete` with `result="failure"`, `exit_code=5`, no `receipt_id`, and no on-disk state is written under either `~/.kosmos/memdir/user/plugins/` or `~/.kosmos/memdir/user/consent/`.
3. **Given** a citizen runs `/plugin install <name-not-in-catalog>`, **When** the backend dispatcher resolves the catalog, **Then** the backend emits `plugin_op_complete` with `result="failure"`, `exit_code=1`, `error_kind="catalog_miss"`, and the TUI overlay closes with a Korean error message that names the catalog URL the citizen can inspect.
4. **Given** a citizen runs `/plugin install <name>` with `KOSMOS_PLUGIN_SLSA_SKIP=true` and `KOSMOS_ENV=development`, **When** the backend reaches the SLSA phase, **Then** the install proceeds with `slsa_verification="skipped"` recorded in the consent receipt and the TUI overlay displays a red banner ("⚠️ 서명 검증 우회됨 (개발 모드)") that the citizen sees before consent.
5. **Given** a citizen runs `/plugin uninstall <name>` for a previously installed plugin, **When** the backend processes the request, **Then** the backend emits the same progress + complete envelope shape (with operation-appropriate phase messages), removes the install directory, appends a `plugin_uninstall` consent receipt, and the next conversational turn no longer offers the plugin's `tool_id` in the model's tool inventory.

---

### User Story 2 — Citizen asks a question and the model invokes the freshly installed plugin tool (Priority: P1)

A citizen has just installed `seoul-subway`. They type "지금 강남역 다음 열차 언제?" into the REPL. Without any system-prompt edit or restart, the model selects the new plugin's adapter through the standard 5-primitive surface (`lookup` / `submit` / `verify` / `subscribe`). The 3-layer permission gauntlet renders the consent modal with the layer color matching the plugin's manifest `permission_layer`. The citizen approves; the plugin returns a result; the model integrates that result into the response.

**Why this priority**: This story is the entire reason the 5-primitive abstraction (migration tree § L1-C) exists — adapters surfaced through dynamic discovery rather than system-prompt edits. Without it the citizen sees an installed plugin that the model never uses, which is the worst possible UX outcome. Story 1 closes the install path; this story proves the install actually delivered value.

**Independent Test**: Pre-install a fixture plugin via Story 1's path (or via direct backend call to `register_plugin_adapter` if Story 1 is not yet shippable). Send a citizen turn whose intent matches the plugin's `search_hint_ko`. Capture the IPC frame stream via the L2 stdio JSONL probe. Assert: the next `ChatRequestFrame` includes the plugin's `tool_id` in `tools[]` (Epic #1978 wiring); the model emits a `tool_use` for that `tool_id` through one of the 4 root primitives; the permission gauntlet emits a `permission_request` frame with the manifest's `permission_layer`; the citizen's "Y" decision (or session-auto "A") is honoured; the plugin returns a structured result; the assistant response cites the plugin output.

**Acceptance Scenarios**:

1. **Given** a citizen has just installed a Layer-1 plugin (low-risk public-data lookup, e.g., subway arrivals), **When** they ask a question matching the plugin's `search_hint_ko`, **Then** the next `ChatRequestFrame` carries the plugin's `tool_id` in `tools[]`, the model invokes it through the appropriate primitive, the gauntlet renders a green "⓵" Layer-1 modal, and the citizen's "Y" approves a single invocation.
2. **Given** a citizen has just installed a Layer-2 plugin with `processes_pii: true` (e.g., personal benefits lookup), **When** they ask a matching question, **Then** the gauntlet modal displays the orange "⓶" Layer-2 indicator, the trustee org name and PIPA §26 acknowledgment SHA-256 hash sourced from the manifest, and the citizen sees who is responsible for their data before granting access.
3. **Given** a citizen has installed a Layer-3 plugin (irreversible action, e.g., complaint submission), **When** they ask a matching question, **Then** the gauntlet modal displays the red "⓷" Layer-3 indicator with the additional confirmation step required at this layer per Spec 033, and the citizen's choice between [Y 한번만 / A 세션 자동 / N 거부] is recorded with a receipt id.
4. **Given** a citizen previously revoked permission for a plugin via `/consent revoke <receipt_id>`, **When** the model later attempts to invoke that plugin, **Then** the invocation fails-closed at the gauntlet without the plugin needing any plugin-side integration code, and the model receives a structured error indicating revoked consent.
5. **Given** the citizen has installed a plugin and uninstalled it in the same session, **When** they ask a question that previously matched, **Then** the next `ChatRequestFrame.tools[]` no longer includes that plugin's `tool_id` and the model does not attempt to invoke it.

---

### User Story 3 — Citizen browses installed plugins via the TUI plugin surface (Priority: P2)

A citizen wants to see what plugins they have installed, what tier each is at, what data each plugin handles, and revoke or remove ones they no longer trust. They open the citizen plugin browser. They see one row per installed plugin showing: the plugin's display name, tier badge ([Live] / [Mock]), permission layer color (1=green / 2=orange / 3=red), trustee org name (if PII-handling), and an enable/disable indicator. They use arrow keys to navigate, Space to select, `i` to view details, `r` to remove.

**Why this priority**: P2 because Stories 1 + 2 already deliver the core install + invoke loop. Story 3 is the citizen's audit and lifecycle-management surface — important for trust but not blocking the primary capability. Without this story the citizen's only way to enumerate installed plugins is `ls ~/.kosmos/memdir/user/plugins/` from a shell, which violates the "TUI as primary surface" principle from migration tree § UI design.

**Independent Test**: Pre-install three fixture plugins of distinct tiers/layers. Open the citizen plugin browser surface. Capture the rendered output via the L3 expect/script text-log layer. Assert: three rows render in deterministic (manifest-name) order; each row carries the correct tier badge + layer color glyph + trustee org (or "—" if not PII-handling); pressing `r` on a selected row triggers a confirmation modal; the modal accept path emits a `plugin_op_request` with `request_op="uninstall"`. The `a` keystroke (marketplace catalog) renders a deferred-to-#1820 message rather than a no-op.

**Acceptance Scenarios**:

1. **Given** three plugins of mixed tier (Live + Mock) and layer (1 / 2 / 3) are installed, **When** the citizen opens the plugin browser, **Then** all three rows render in deterministic order with correct tier badge, layer color glyph, and trustee org metadata sourced from the manifest.
2. **Given** the citizen selects an installed plugin and presses `i`, **When** the detail view renders, **Then** it shows the plugin's full manifest summary (description in Korean, search hints, permission layer rationale, PIPA acknowledgment SHA-256 if applicable, install timestamp, last-used timestamp).
3. **Given** the citizen selects an installed plugin and presses `r`, **When** the confirmation modal renders, **Then** accepting emits a `plugin_op_request` with `request_op="uninstall"`, the install root subtree is removed, a `plugin_uninstall` consent receipt is appended, and the row disappears from the browser.
4. **Given** the citizen presses `a` (marketplace catalog) in the browser, **When** the action is dispatched, **Then** the surface displays a clear Korean message that this view is deferred to #1820 with no error and no empty no-op.
5. **Given** an install is in progress in the background, **When** the citizen opens the browser, **Then** an "(설치 중…)" placeholder row renders for the in-flight plugin and converts to a normal row when the terminal `plugin_op_complete` frame arrives.

---

### User Story 4 — Verification engineer captures the integration loop via the 4-layer PTY ladder (Priority: P2)

A verification engineer (or Codex review automation) needs grep-friendly proof that the install + invoke loop actually works end-to-end. They run a single E2E scenario script that exercises Story 1 + Story 2 under PTY, capturing artifacts at all four verification layers (L1 unit / L2 stdio JSONL probe / L3 expect/script text-log / L4 vhs visual). The script produces deterministic, grep-able text output that automated review tooling can verify, plus a binary recording for human visual review.

**Why this priority**: P2 because verification produces evidence, not citizen-visible value. But without it the Epic cannot exit Codex review per memory `feedback_codex_reviewer` + `feedback_runtime_verification` + `feedback_vhs_tui_smoke` — Codex needs grep-able proof, and humans need visual proof. The 4-layer ladder is the canonical methodology established post-#2152 (per `docs/testing.md § TUI verification methodology`).

**Independent Test**: Run the E2E scenario script against a fixture catalog. Assert: L1 (`bun test` + `uv run pytest`) returns ≥ baseline parity (984 / 3458). L2 (stdio JSONL probe with no TUI) shows the full frame stream with all 7 plugin_op phases + ChatRequestFrame.tools[] post-install + tool_use post-question. L3 (expect/script text-log) is grep-able with phase markers, primitive markers, and permission gauntlet markers. L4 (vhs visual gif/mp4) renders without manual intervention from script start to citizen response. All four artifacts under `specs/1979-plugin-dx-tui-integration/`.

**Acceptance Scenarios**:

1. **Given** the E2E scenario script runs against a fresh fixture catalog, **When** it completes, **Then** four verification artifacts exist under `specs/1979-plugin-dx-tui-integration/` (one per layer) and the artifact filenames + content layout match the conventions documented in `docs/testing.md § TUI verification methodology`.
2. **Given** the L3 text-log artifact, **When** an automated reviewer greps for the phase markers (`plugin_op_progress.*phase=1` through `phase=7`, `plugin_op_complete.*result="success"`, `tool_use.*tool_id="plugin\.`, `permission_response.*decision`), **Then** all expected markers appear in expected order.
3. **Given** the `bun test` + `uv run pytest` baselines (984 / 3458 from post-#2152 main), **When** the L1 layer runs against this Epic's branch, **Then** test counts meet or exceed baseline parity with zero new failures.

---

### Edge Cases

- **TUI killed mid-install**: Citizen presses Ctrl+C between bundle download and registry registration. Backend receives no further frames. Backend MUST NOT leave a half-installed plugin under `~/.kosmos/memdir/user/plugins/<plugin_id>/`. The on-shutdown cleanup path removes any partially extracted bundle directory before the process exits.
- **Concurrent installs from two TUI sessions**: Two distinct citizen sessions simultaneously fire `plugin_op_request` for different plugins. The fcntl-flocked consent ledger position assignment in `installer.py:_allocate_consent_position` already serialises receipt position; both installs MUST complete with monotonically increasing `consent_ledger_position` values.
- **Concurrent install of the same plugin twice**: Two `plugin_op_request` frames target the same plugin name. The second MUST observe the first's install root and either no-op (already installed at same version) or fail with a clear "plugin already installed" message — never overwrite half-written state.
- **`consent_prompt` IPC round-trip times out**: The TUI receives a consent request but never replies (e.g., user walks away). The backend MUST treat the timeout as denial after a bounded interval and emit `plugin_op_complete` with `exit_code=5`. The fail-closed default protects citizens from accidentally granting access through inaction.
- **Plugin install succeeds but BM25 index rebuild fails**: Registry rolls back the partially registered tool. The complete frame reports `exit_code=6` (I/O error). The install directory is removed so a retry starts clean.
- **Manifest `permission_layer=3` with `slsa_state="skipped"`**: Already enforced in `installer.py:Phase 4.5` — install rejected with `error_kind="slsa_skip_layer_3_forbidden"`. Surface this Korean error verbatim in the TUI overlay so the citizen understands why the install was refused.
- **Bilingual progress message missing**: `_v_plugin_op_shape` rejects a `plugin_op_progress` frame missing either `progress_message_ko` or `progress_message_en`. Backend code paths MUST emit both for every phase.
- **TUI plugin browser opened during a concurrent install**: The browser shows an "(설치 중…)" placeholder row for the in-flight plugin and converts to a normal row when the terminal frame arrives. The browser does not block on the install; it just reflects state.
- **Plugin `tool_id` namespace collision**: Two plugins both claim `plugin.foo.lookup`. The registry rejects the second per existing Spec 022 invariant. Surface the collision error in the TUI overlay with both plugin_ids named.
- **Citizen revokes consent then re-asks the same question**: The gauntlet must fail-closed without re-prompting (Spec 033 invariant). The model receives a structured error and adapts its response.
- **CC marketplace residue surface accidentally invoked**: A citizen who learned the CC `/plugins` slash command from documentation tries it. Per the Phase E verdict, the surface either redirects to the citizen browser OR is hidden behind a dev-mode flag — never silently shows CC marketplace UI to a citizen.
- **Plugin uninstalled while a tool_use is in flight**: The currently in-flight tool call completes against the still-loaded module; subsequent invocations fail at the gauntlet because the registry no longer carries the tool. No corruption of in-flight state.

## Requirements *(mandatory)*

### Functional Requirements

#### Backend dispatcher + IPC envelope (Phase B)

- **FR-001**: Backend stdio dispatcher MUST route incoming `plugin_op_request` frames to the appropriate backend handler (install / uninstall / list) based on the frame's `request_op` field, mirroring the role allow-list in `frame_schema.py` (`tui:request / backend:progress+complete`).
- **FR-002**: Backend MUST emit one `plugin_op_progress` frame per install phase (1 through 7) carrying both `progress_message_ko` and `progress_message_en`. The Korean and English messages MUST follow the canonical phrasing in `specs/1636-plugin-dx-5tier/contracts/plugin-install.cli.md`.
- **FR-003**: Backend MUST emit exactly one `plugin_op_complete` frame per `plugin_op_request`. The frame MUST carry `result` ∈ {`success`, `failure`}, `exit_code` from the contract's 8-code table, and `receipt_id` if and only if `result=="success"`.
- **FR-004**: The `consent_prompt` callback in `installer.py:_default_consent_prompt` MUST be replaced (in the IPC-bound code path) with a round-trip that emits a consent prompt to the TUI and awaits the citizen's Y / A / N decision. Timeout treats as denial.
- **FR-005**: Failed installs MUST NOT leave any state under `~/.kosmos/memdir/user/plugins/<plugin_id>/` or `~/.kosmos/memdir/user/consent/`. On any post-extraction failure, the install directory MUST be removed and the failure MUST be reflected in the complete frame.
- **FR-006**: Uninstall flow MUST emit the same progress + complete envelope shape as install (operation-appropriate phase messages), remove the install directory, deregister the tool from `ToolRegistry`, rebuild the BM25 index, and append a `plugin_uninstall` consent receipt.
- **FR-007**: The list operation MUST emit a single `plugin_op_complete` frame whose body carries the enumerated installed plugins (deterministic order by `plugin_id` lexicographic sort). Progress frames are not required for list because there are no phases.

#### Tool inventory propagation (Phase C)

- **FR-008**: After a successful install `plugin_op_complete`, the next `ChatRequestFrame` MUST include the new plugin's `tool_id` in `tools[]`. No TUI restart, no system-prompt edit. (Rides on Epic #1978's tool-inventory wiring; this Epic verifies and does not extend.)
- **FR-009**: After a successful uninstall `plugin_op_complete`, the next `ChatRequestFrame` MUST exclude the removed plugin's `tool_id` from `tools[]`.
- **FR-010**: Plugin tool invocations through any of the 4 root primitives (`lookup` / `submit` / `verify` / `subscribe`) MUST emit OTEL spans carrying the `kosmos.plugin.id` attribute (Spec 021 + Spec 1636 FR-021 invariant). This Epic does not extend the OTEL schema; it only verifies emission.

#### Permission gauntlet (Phase D)

- **FR-011**: Plugin tool invocations MUST traverse the Spec 033 permission gauntlet. The layer (1 / 2 / 3) MUST be sourced from the manifest's `permission_layer` field with no per-invocation override.
- **FR-012**: For plugins with `processes_pii: true` in the manifest, the gauntlet's consent modal MUST display: the trustee org name, the PIPA §26 trustee acknowledgment SHA-256 hash sourced from the manifest, and a deep-link reference to `docs/plugins/security-review.md`. The citizen MUST see this metadata before granting access.
- **FR-013**: Citizen revocation via `/consent revoke <receipt_id>` MUST cause subsequent invocations of the affected plugin to fail-closed at the gauntlet without plugin-side integration code. The model MUST receive a structured error indicating revoked consent so it can adapt its response.
- **FR-014**: Permission gauntlet decisions for plugin tools MUST surface the layer-color glyph documented in migration tree § UI-C.1 (1=green ⓵ / 2=orange ⓶ / 3=red ⓷) so the citizen has uniform visual cues across in-tree adapters and plugins.

#### Citizen plugin browser (Phase E)

- **FR-015**: The TUI MUST provide a citizen-facing plugin browser surface listing installed plugins with: display name, tier badge ([Live] / [Mock]), permission layer color glyph, trustee org name (or "—" if not PII-handling), enable/disable indicator (⏺ enabled / ○ disabled), and last-install timestamp.
- **FR-016**: The plugin browser MUST honour the migration tree § UI-E.3 key bindings: arrow keys (navigate), Space (select), `i` (detail view), `r` (remove with confirmation), ⏺/○ toggle (enable/disable). The `a` keystroke MUST render a clear "marketplace browser deferred to #1820" message, never an empty no-op.
- **FR-017**: The remove (`r`) flow MUST emit a `plugin_op_request` with `request_op="uninstall"` and reflect the operation outcome in the browser when the terminal frame arrives.
- **FR-018**: The CC marketplace plugin port residue (`tui/src/services/plugins/*`, `tui/src/commands/plugin/*`) MUST be verdict-resolved. Acceptable verdicts: (a) removed entirely, or (b) isolated under a `KOSMOS_PLUGIN_DEV_MODE` flag that does not surface to citizens by default. The verdict + rationale MUST be documented in `plan.md` Phase 0 with a citation to `feedback_kosmos_scope_cc_plus_two_swaps`.
- **FR-019**: While a `plugin_op_progress` flow is in flight for an install, the browser MUST render an "(설치 중…)" placeholder row for the target plugin and replace it with a real row when the terminal frame arrives.

#### E2E verification (Phase F)

- **FR-020**: A PTY-driven E2E scenario script MUST exist under `specs/1979-plugin-dx-tui-integration/` and produce four verification artifacts (one per layer) when run against a fixture catalog. The script MUST run without manual keypresses except where the test harness simulates citizen consent decisions.
- **FR-021**: The L3 expect/script text-log artifact MUST contain grep-able phase markers (`plugin_op_progress.*phase=1` through `phase=7`), primitive markers (`tool_use.*tool_id="plugin\.`), and permission gauntlet markers (`permission_response.*decision`). Memory `feedback_vhs_tui_smoke` requires this for Codex review.
- **FR-022**: The L1 layer (`bun test` + `uv run pytest`) MUST meet or exceed post-#2152 baseline parity (984 / 3458) with zero new test failures attributable to this Epic.

#### Cross-cutting governance

- **FR-023**: This Epic MUST add zero new runtime dependencies. `pyproject.toml` and `tui/package.json` MUST remain unchanged in their dependency declarations.
- **FR-024**: All source-text identifiers and comments MUST be English. Citizen-facing display strings (slash-command acknowledgements, progress messages, browser labels, error messages) follow the bilingual pattern (Korean primary + English fallback).
- **FR-025**: Backend lifecycle events (frame emit, install phase transitions, register / deregister tool, BM25 rebuild) MUST use stdlib `logging`. No `print()` outside the CLI output layer.
- **FR-026**: This Epic MUST NOT introduce calls to live `data.go.kr` APIs from CI. All E2E tests use `file://` catalog + fixture bundles per the existing seam in `installer.py:_default_catalog_fetcher`.
- **FR-027**: Sub-issue count MUST stay ≤ 90 per memory `feedback_subissue_100_cap`.

### Key Entities

- **`PluginOpRequest` frame**: TUI-to-backend frame triggering an install / uninstall / list operation. Already defined in `frame_schema.py:780-936` as part of `PluginOpFrame` with `op="request"`.
- **`PluginOpProgress` frame**: Backend-to-TUI frame announcing one of 7 install phases with bilingual messages. Already defined as part of `PluginOpFrame` with `op="progress"`.
- **`PluginOpComplete` frame**: Backend-to-TUI terminal frame with `result`, `exit_code`, optional `receipt_id`. Already defined as part of `PluginOpFrame` with `op="complete"`. Listed in `KIND_TERMINAL`.
- **`ChatRequestFrame.tools[]` extension**: The per-turn tool inventory now carries plugin tool entries after auto-discover. This Epic verifies the propagation; the underlying frame change shipped in Epic #1978.
- **`CitizenPluginBrowserEntry`**: TUI display row per installed plugin. Renders display name, tier badge, layer color glyph, trustee org name, enable/disable indicator, install timestamp. Sourced from the in-process `ToolRegistry` + manifest cache.
- **Backend dispatcher**: A new function under `src/kosmos/ipc/` (or extension to `stdio.py`) that pattern-matches incoming `plugin_op_request` frames and dispatches to install / uninstall / list handlers. Emits `plugin_op_progress` and `plugin_op_complete` frames through the existing IPC envelope.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A citizen executing `/plugin install <fixture-name>` from a fresh TUI session sees the install complete with `plugin_op_complete.result="success"` within **30 seconds** wall-clock (Spec 1636 SC-005 ceiling). All seven `plugin_op_progress` frames emit in phase order with bilingual messages. A consent receipt JSON appears under `~/.kosmos/memdir/user/consent/` carrying the manifest's `acknowledgment_sha256`. Captured under L3 text-log smoke.
- **SC-002**: Within **3 seconds** of a successful install `plugin_op_complete`, the next `ChatRequestFrame` carries the new plugin's `tool_id` in `tools[]`. Verified via L2 stdio JSONL probe inspecting the frame stream (no TUI in the loop).
- **SC-003**: When a citizen asks a question whose intent matches the freshly installed plugin's `search_hint_ko`, the model invokes the plugin tool through one of the 4 root primitives, the permission gauntlet renders the layer-color modal sourced from the manifest, and the citizen's Y / A / N decision is honoured per Spec 033 in **100 %** of test cases (verified via at least 5 deterministic scenarios across 3 layer values).
- **SC-004**: The 4-layer PTY-driven E2E scenario completes without manual intervention. All four verification artifacts (L1 unit / L2 stdio JSONL / L3 text-log / L4 vhs) are produced under `specs/1979-plugin-dx-tui-integration/` and L3 is grep-friendly per memory `feedback_vhs_tui_smoke` so Codex review can verify automatically.
- **SC-005**: `bun test` count ≥ **984** and `uv run pytest` count ≥ **3458** (post-#2152 baseline parity). Zero new test failures attributable to this Epic.
- **SC-006**: `pyproject.toml` and `tui/package.json` show **zero** new runtime dependencies after the Epic merges (AGENTS.md hard rule).
- **SC-007**: GitHub Sub-Issues API v2 reports **≤ 90** open sub-issues parented to Epic #1979 at `/speckit-taskstoissues` time (memory `feedback_subissue_100_cap`).
- **SC-008**: Permission revocation via `/consent revoke <receipt_id>` causes subsequent invocations of the affected plugin to fail-closed at the gauntlet in **100 %** of test cases (verified via at least 3 negative-test scenarios). The fail mode produces a structured error visible to the model.
- **SC-009**: Concurrent installs from two TUI sessions assign monotonically increasing `consent_ledger_position` values in **100 %** of test cases (verified via at least 5 concurrent-install simulations using fcntl-flocked position assignment already in `installer.py:_allocate_consent_position`).
- **SC-010**: A citizen who presses **N** at the consent prompt sees the install abort with `plugin_op_complete.exit_code=5`, no on-disk plugin state under `~/.kosmos/memdir/user/plugins/`, and no consent receipt under `~/.kosmos/memdir/user/consent/`. **Zero** partial-state leaks across 5 negative-test runs.

## Assumptions

- **Assumption A1**: Epic #1978 (ChatRequestFrame + permission bridge) is closed and merged on `main`. Verified via memory `feedback_graphql_issue_tracking` lineage + git log `cc4f4a2 / 910b7c5 / 1e295aa / 692d1c3`. Plugin tools propagate into `ChatRequestFrame.tools[]` via the same auto-refresh path Epic #1978 wired for in-tree adapters.
- **Assumption A2**: Spec 1636's `installer.py:install_plugin()` 8-phase implementation is correct (6 integration tests + 4 SC tests already pass). This Epic does not modify the install logic — only the IPC dispatch path that invokes it. The `consent_prompt` parameter is a pre-existing seam designed for IPC binding.
- **Assumption A3**: Spec 033 permission gauntlet routes by tool's `permission_layer` attribute. Plugin manifest `permission_layer` already maps directly through `register_plugin_adapter`'s `GovAPITool` invariants; no new gauntlet surface needed.
- **Assumption A4**: `kosmos-plugin-store` example plugins (`seoul-subway`, `post-office`, `nts-homtax`, `nhis-check`) are accessible at the URLs declared in their respective catalog entries OR a fixture catalog with equivalent shape can be used. The `_default_catalog_fetcher` already supports `file://` for tests; this Epic uses fixture bundles in CI per FR-026.
- **Assumption A5**: The 4-layer TUI verification ladder is canonical post-#2152 (per `docs/testing.md § TUI verification methodology`). This Epic uses the existing infrastructure and does not extend the methodology.
- **Assumption A6**: `tui/src/components/plugins/PluginBrowser.tsx` may be either KOSMOS-aligned (kept and extended) or CC residue (replaced). The verdict is established in `plan.md` Phase 0 with code citation.
- **Assumption A7**: `tui/src/services/plugins/*` and `tui/src/commands/plugin/*` are CC marketplace plugin port residue. The verdict on whether to remove or isolate behind a dev-mode flag is established in `plan.md` Phase 0 per FR-018. Both options preserve the SC-005 baseline-parity invariant; the choice depends on whether the residue affects user-visible TUI surfaces today.
- **Assumption A8**: All plugin tool invocations are dispatched through the existing 5-primitive surface (migration tree § L1-C). This Epic neither extends the primitive set nor introduces a plugin-specific primitive — `plugin.<id>.<verb>` namespace already routes through the standard primitive surface.
- **Assumption A9**: The `plugin_op` frame's role allow-list (`tui:request / backend:progress+complete`) is a hard contract. This Epic does not add new roles; the backend dispatcher implements the existing allow-list.
- **Assumption A10**: Codex review is the primary inline review channel post-#2076. After every push the engineer queries `chatgpt-codex-connector[bot]` PR comments and addresses each (memory `feedback_codex_reviewer`).

## Scope Boundaries & Deferred Items *(mandatory)*

### Out of Scope (Permanent)

- **Plugin manifest schema changes**: Spec 1636 ships the canonical schema (`src/kosmos/plugins/manifest_schema.py`) with five cross-field validators and PIPA §26 acknowledgment hash gate. This Epic only wires the existing schema through TUI; any field addition is a separate spec-driven change.
- **SLSA verification logic**: Spec 1636 + `slsa.py` ship the `slsa-verifier` shell-out path including the production-`slsa_skip` refusal and Layer-3 hard refusal. This Epic only consumes the verification outcome; `slsa.py` is treated as a black box.
- **50-item validation matrix**: Spec 1636 Tier 4 ships the workflow + 50 check modules. This Epic only consumes the workflow outcome ("plugin is valid") at install time; the matrix itself is invariant.
- **`canonical_acknowledgment.py` SHA-256 generation logic**: Spec 1636 ships the canonical text + hash extraction. This Epic uses `CANONICAL_ACKNOWLEDGMENT_SHA256` as a constant.
- **Plugin marketplace catalog browser (`a` keystroke destination)**: Explicitly deferred to #1820 per Spec 1636 Assumption A5. The `a` keystroke in the citizen browser MUST render a deferred-to-#1820 message.
- **Hot-reload of an installed plugin's source code**: Permanent OOS per Spec 1636 § Out of Scope. Restart is the contract.
- **Cross-language plugin authoring**: The 4-primitive envelope and Pydantic v2 manifest are Python-canonical. Cross-language plugins require a separate IPC contract (permanent OOS per Spec 1636).
- **Reserved root primitive override**: Plugins cannot override `lookup` / `submit` / `verify` / `subscribe` even with justification flags. Constitutional per migration tree § L1-C C1 + Spec 1636 § Out of Scope.

### Deferred to Future Work

| Item | Reason for Deferral | Target Epic/Phase | Tracking Issue |
|------|---------------------|-------------------|----------------|
| Plugin tool dense-embedding discovery | This Epic uses the existing BM25 retrieval (`auto_discover` rebuilds the BM25 index per Spec 1636 FR-020). Dense embeddings are an orthogonal retrieval improvement spec'd separately. | feat/585-retrieval-dense | #585 |
| External plugin contributor onboarding UX | This Epic is the consume-side activation. Improvements to the contribute-side flow (template repo polish, `kosmos plugin init` UX iteration) live in the `kosmos-plugin-template` repo workstream. | Plugin contributor experience workstream | NEEDS TRACKING |
| Plugin store catalog index sync mechanism | This Epic consumes the catalog index. The publish path / catalog refresh / index sync mechanism (how the store gets new plugins) is a registry-side concern. | Spec 1636 follow-up — registry-side | NEEDS TRACKING |
| Spec 027 Agent Swarm worker invoking plugin tools | Citizen-facing invocation closes here; swarm workers reaching plugin tools through the same primitive surface is the parallel Epic that closes Initiative #1631 alongside this one. | Epic #1980 — Agent Swarm TUI integration | #1980 |
| Plugin marketplace catalog browser (`a` keystroke target) | Browsing the published catalog from inside the TUI is a distinct UX problem from managing installed plugins. | Post-P5 marketplace Epic | #1820 |
| Acknowledgment-text drift audit workflow | The canonical PIPA acknowledgment text is expected stable. Building a drift audit before any drift event has happened is premature. | Post-P5 first acknowledgment-text update | #1926 |
| CC marketplace residue cleanup (`commands/plugin/*`, `services/plugins/*`, `utils/plugins/*`) | This Epic swaps `commands.ts:133` to KOSMOS singular `plugin.ts`, making the CC residue (~16 files, 89 grep matches) unreachable. Bulk deletion deferred to preserve SC-005 baseline parity. | Spec 1633-style dead-code-elimination follow-up | #2242 |
| Plugin runtime enable/disable IPC (`plugin_op_request:activate/deactivate`) | This Epic adds `_inactive` shadow set + treats ⏺/○ Space as visual-only. Runtime toggle requires Spec 032 envelope schema bump — out of scope. | Post-P5 plugin-lifecycle Epic | #2243 |
| SC-001 live environment validation against `kosmos-plugin-store` | This Epic measures SC-001 against `file://` fixture catalog; live network latency variance not quantified. | Post-P5 fixture→live calibration | #2244 |
| Plugin list payload reassembly stress test (>50 plugins) | This Epic targets MVP3 (1-4 plugins). Reassembly at scale (50/100/200/500 plugins) not stress-tested. | Post-P5 catalog scale Epic | #2245 |
