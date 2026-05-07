# Spec 2642 · S7 IPC/Bridge cleanup

**Initiative**: #2636 — CC Migration Audit-Driven Realignment
**Epic**: #2642 — Epic F · IPC/Bridge 정리
**Status**: Draft (autonomous Lead Opus authoring, 2026-05-03)
**Author**: Lead Opus (UMMAYA Epic F · S7 slice)
**Feature branch**: `feat/2642-s7-ipc-bridge`

---

## 1. Why this exists

The S7 audit (`specs/cc-migration-audit/scope-S7-ipc-bridge.md`) and the
canonical decision row (`specs/cc-migration-audit/decisions.md § S7 IPC
Bridge`) identified four concrete cleanup actions required to land the
IPC/Bridge slice of the CC-migration-audit-driven realignment:

1. **`remote/` 4-file DROP + `directConnectManager` dead type-stub cleanup.**
   CC's `remote/` (4 files: `RemoteSessionManager.ts`,
   `SessionsWebSocket.ts`, `sdkMessageAdapter.ts`,
   `remotePermissionBridge.ts`) is the claude.ai-backed cloud-session
   WebSocket bridge. UMMAYA swap-1 (LLM = K-EXAONE on FriendliAI) and
   swap-2 (Tool = GovAPITool) replace claude.ai entirely; the cloud
   session surface has no UMMAYA use-case. The 4 files were never ported
   (audit § 2.3) but `tui/src/server/directConnectManager.ts` still
   ships a dead `DirectConnectSessionManager` class with
   `unknown`-typed stubs for `RemotePermissionResponse` /
   `RemoteMessageContent`. `screens/REPL.tsx`,
   `hooks/useDirectConnect.ts`, `server/createDirectConnectSession.ts`
   transitively re-export the dead type. **This cleanup formally
   classifies the cluster as DROP-FOR-SWAP, deletes the dead runtime,
   and lands a `// SWAP:` header on every kept file that references the
   deleted surface.**

2. **`notification_push` IPC arm — CC baseline verification + SWAP
   docstring.** Audit § 5 Finding 3 flagged "1 arm verification needed".
   Investigation (this spec, § 4.2) confirms CC has **no** push-based
   notification IPC arm — CC emits OS notifications via terminal OSC
   sequences from `ink/useTerminalNotification.ts` (iTerm2 / Kitty /
   Ghostty / bell), all in-process. UMMAYA's `notification_push` arm
   (`src/ummaya/ipc/frame_schema.py:768`) is a **swap-2 add-on**
   carrying Spec 031 SubscriptionHandle pushes (Korean disaster-alert
   CBS, RSS news subscribe) over the same stdio plane — orthogonal to
   CC terminal OSC notifications. **This cleanup adds an explicit
   SWAP-justification docstring + a parity test that asserts the arm's
   role allow-list (`{notification}`) and adapter_id pattern
   (`*_push|*_subscribe`).**

3. **TS↔Python frame-schema field-level drift CI gate (NEW).** The
   existing `tui-ipc-drift.yml` + `test_schema_python_ts_diff.py` cover
   the **JSON Schema** (`tui/src/ipc/schema/frame.schema.json`) and the
   **generated TS types** (`tui/src/ipc/frames.generated.ts`). They do
   **not** cover `tui/src/ipc/codec.ts` — a hand-written zod schema
   layer used for runtime validation on the TUI side. The audit § 5
   Finding 4 calls this gap out. **This cleanup adds a new pytest
   gate** (`tests/ipc/test_codec_envelope_parity.py`) **that parses
   codec.ts's envelope zod schema (regex-based extraction of
   `correlation_id` / `transaction_id` / `frame_seq` / `version` /
   `role` / `kind` / `timestamp` field constraints) and asserts they
   match the Pydantic envelope.** A negative-fixture (`drift_fixture`)
   proves the gate fails when an intentional drift is injected.

4. **`mcpb-compat.ts` ADR-009 (UMMAYA-original innovation).**
   `tui/src/mcpb-compat.ts` (Epic #2293 FR-010) is a 26-line lazy-load
   shim around `@anthropic-ai/mcpb` that defers the package's
   ~700 KB heap cost (~300 zod-v3 `.bind(this)` schema instances) until
   a session actually processes a `.dxt` file. CC has no equivalent —
   this is a UMMAYA-original optimization. Audit § 2.5 + § 5 Finding 5
   recommend ADR registration. **This cleanup writes
   `docs/adr/ADR-009-mcpb-compat-lazy-shim.md` documenting the
   decision, rationale, consequences, and the FR-010 / SC-007 grep gate
   that keeps the package literal isolated to one shim file.**

---

## 2. CORE THESIS alignment

UMMAYA = CC-original harness + 2 swaps. Every action above is justified
under that thesis:

| Action | Swap class | Justification |
|---|---|---|
| 1. `remote/` DROP + `directConnectManager` cleanup | swap-2 (claude.ai sync removed) | claude.ai backed remote sessions are not part of UMMAYA surface |
| 2. `notification_push` SWAP docstring | swap-2 (Korean civic push channels) | Spec 031 SubscriptionHandle for CBS/RSS — orthogonal CC addition |
| 3. codec.ts ↔ Python envelope drift CI | swap-implementation transport | stdio JSONL is UMMAYA's swap-implementation; field-level parity guards swap correctness |
| 4. mcpb-compat.ts ADR | UMMAYA-original innovation (perf optimization) | byte-identical CC default does not apply — CC has no equivalent; ADR captures the deviation |

No PRESERVE-IDENTICAL CC bridge file is touched (audit § 2.1 confirms
24/24 bridge files + 2/3 server + 2/2 upstreamproxy + 4/4 native-ts are
already byte-identical and stay that way).

---

## 3. User stories

### US1 — Remote DROP cleanup (claude.ai sync surface removal)

**As a** UMMAYA maintainer auditing the TUI for swap-2 leftovers,
**I want** the `remote/` cluster — including `directConnectManager.ts`,
the dead `useDirectConnect.ts` hook, the dead `createDirectConnectSession.ts`,
and the dead REPL.tsx wiring — formally deleted with `// SWAP:` headers
on the kept stub paths,
**so that** future audits do not re-flag the cluster and the TUI
compiles + boots without claude.ai-backed remote-session dead code.

**Acceptance**:
- `tui/src/server/directConnectManager.ts` deleted.
- `tui/src/server/createDirectConnectSession.ts` deleted.
- `tui/src/server/types.ts` deleted (only consumed by the deleted siblings).
- `tui/src/hooks/useDirectConnect.ts` deleted.
- `tui/src/hooks/useRemoteSession.ts` retained but documented in audit § 2.3 NEVER-PORT roster (no runtime change).
- `tui/src/screens/REPL.tsx` strips imports/usage of the deleted surface, replacing `directConnect.isRemoteMode ? directConnect : remoteSession` with `remoteSession`. The `directConnectConfig?` prop is removed; callers that pass it are updated.
- `tui/src/screens/REPL.tsx` retains a comment: `// UMMAYA-2642 / Epic F · S7 — directConnect/remote/ DROPPED (claude.ai sync swap-out).`
- `bun typecheck` (UMMAYA narrow) PASS.
- `bun test` for `tui/` PASS.
- No call site in `tui/src/**` references `DirectConnectConfig`, `useDirectConnect`, `DirectConnectSessionManager`, `createDirectConnectSession`.

### US2 — `notification_push` SWAP justification + role parity test

**As a** Codex/Copilot reviewer reading the IPC schema,
**I want** the `notification_push` arm to declare *in-source* why it
exists (Spec 031 SubscriptionHandle for KMA/CBS/RSS push, swap-2 surface,
**not** an OS-notification IPC equivalent of CC's terminal OSC),
**so that** future drift audits can compare UMMAYA's IPC surface to
CC's call signatures without re-discovering this finding.

**Acceptance**:
- `src/ummaya/ipc/frame_schema.py:NotificationPushFrame` docstring extended with explicit "CC parity: NO equivalent — CC uses terminal OSC via `ink/useTerminalNotification.ts` (iTerm2/Kitty/Ghostty/bell), in-process. This arm is UMMAYA swap-2 (Spec 031 SubscriptionHandle for Korean civic push channels)."
- New test `tests/ipc/test_notification_push_swap_parity.py` asserts:
  - role allow-list equals `frozenset({"notification"})`,
  - `subscription_id` / `adapter_id` / `event_guid` / `payload_content_type` / `payload` are required,
  - the docstring contains the literal substring `"CC parity: NO equivalent"`,
  - a happy-path frame validates,
  - an empty payload rejects.

### US3 — codec.ts ↔ Python envelope field-level drift CI gate

**As a** future contributor editing `correlation_id` semantics,
**I want** CI to fail fast when `tui/src/ipc/codec.ts`'s envelope zod
schema diverges from `src/ummaya/ipc/frame_schema.py`'s `_BaseFrame`
field constraints,
**so that** TS-side runtime validation never silently accepts a frame
the Python backend would reject (or vice versa).

**Acceptance**:
- New test `tests/ipc/test_codec_envelope_parity.py`:
  - Reads `tui/src/ipc/codec.ts` as text.
  - Extracts the `frameTrailerSchema()` and `_BaseFrameSchema()` (or whatever the codec's envelope-defining zod constants are named) field-by-field via narrow regex anchors.
  - Compares each of `correlation_id`, `transaction_id`, `frame_seq`, `version`, `role`, `kind`, `timestamp` to the Python `_BaseFrame` field metadata (required-ness, nullability, min_length on string fields).
  - Asserts an exact match.
- A negative fixture `tests/ipc/fixtures/codec_drift_negative.ts` — a 30-line text file that re-declares the envelope with `correlation_id` made optional — proves the test fails when fed the negative fixture (toggled by a `UMMAYA_IPC_PARITY_DRIFT_FIXTURE=1` env var that swaps the codec.ts path before parsing; default off, so production CI uses the real codec.ts).
- A second test `test_drift_negative_fixture_triggers_failure` uses `pytest.raises(AssertionError)` against the parity check called with the fixture path → proves CI fail-mode works.
- No new runtime dependency. Pure stdlib regex + Pydantic introspection.

### US4 — `mcpb-compat.ts` ADR-009

**As a** future agent reading `docs/adr/`,
**I want** ADR-009 to capture the UMMAYA-original lazy-load shim
decision (700 KB heap deferral, FR-010 / SC-007 grep-gate invariant),
**so that** if CC adopts the same pattern upstream we can either drop
the shim or document why we keep ours.

**Acceptance**:
- `docs/adr/ADR-009-mcpb-compat-lazy-shim.md` with sections **Status**, **Date**, **Epic**, **Affected**, **Context**, **Decision**, **Rationale**, **Consequences**, **References**.
- References include: `tui/src/mcpb-compat.ts`, `specs/2293-ui-residue-cleanup/spec.md § FR-010 / SC-007`, `specs/cc-migration-audit/scope-S7-ipc-bridge.md § 2.5 + § 5 Finding 5`.
- Status: **Accepted**.

---

## 4. Functional requirements

### FR-001 (US1)
DELETE `tui/src/server/directConnectManager.ts`,
`tui/src/server/createDirectConnectSession.ts`,
`tui/src/server/types.ts`, `tui/src/hooks/useDirectConnect.ts`.

### FR-002 (US1)
Update `tui/src/screens/REPL.tsx`:
- Remove import of `useDirectConnect`, `DirectConnectConfig`.
- Remove `directConnectConfig?` prop and its usage.
- Replace `sshRemote.isRemoteMode ? sshRemote : directConnect.isRemoteMode ? directConnect : remoteSession` with `sshRemote.isRemoteMode ? sshRemote : remoteSession`.
- Add comment `// UMMAYA-2642 / Epic F · S7 — directConnect/server/ DROPPED (claude.ai sync swap-out).`

### FR-003 (US1)
Update any callers of the deleted REPL.tsx prop or of `createDirectConnectSession` / `DirectConnectSessionManager` / `DirectConnectConfig`. Verify via `grep -rn "directConnect\|DirectConnect" tui/src/` returning zero matches in non-deleted files (after the cleanup).

### FR-004 (US1)
`tui/src/server/` directory is **emptied** by FR-001. Delete the empty directory.

### FR-005 (US2)
Extend `NotificationPushFrame.__doc__` with the literal substring
`"CC parity: NO equivalent"` and a 4-line explanation of CC's terminal
OSC alternative.

### FR-006 (US2)
Add `tests/ipc/test_notification_push_swap_parity.py` per US2 acceptance.

### FR-007 (US3)
Add `tests/ipc/test_codec_envelope_parity.py` per US3 acceptance.

### FR-008 (US3)
Add `tests/ipc/fixtures/codec_drift_negative.ts` (test-only, not imported by TUI runtime).

### FR-009 (US3)
Extend `.github/workflows/tui-ipc-drift.yml` to also run
`uv run pytest tests/ipc/test_codec_envelope_parity.py` (the existing
job already runs other ipc tests, but explicit inclusion ensures the
new gate runs even on TS-only PRs that touch `codec.ts`).

### FR-010 (US4)
Author `docs/adr/ADR-009-mcpb-compat-lazy-shim.md`.

### FR-011 (cross-cutting)
Zero new runtime dependencies (Python or TS).

### FR-012 (cross-cutting)
The IPC envelope arm count remains **22**
(`test_schema_python_ts_diff.py:_EXPECTED_KIND_COUNT`).

---

## 5. Non-functional requirements

### NFR-001 — Source-text English
All source-text English; comments referencing Korean civic surfaces
may use Korean for domain data only.

### NFR-002 — No CC byte-identical surface touched
`bridge/`, `upstreamproxy/`, `native-ts/`, and the 2 PRESERVE-IDENTICAL
`server/` files (`createDirectConnectSession.ts`, `types.ts`) are
**deleted** (FR-001) — but they were 2/3 byte-identical because they
have no swap-justified divergence; their deletion is justified by the
parent surface (`remote/`) being dropped, not by editing the CC-mirror
content. After deletion, `bridge/` 24-file byte-identical invariant is
unchanged.

### NFR-003 — IPC arm count invariant preserved
22 arms — none added, none removed by this spec.

### NFR-004 — Test parity with existing schema-drift tests
The new `test_codec_envelope_parity.py` follows the
`test_schema_python_ts_diff.py` style (regex-based, fail-loud,
explicit error message pointing at the fix command).

---

## 6. Out of scope

- Re-porting `remote/` 4 files. (Permanently NEVER-PORT.)
- Editing `tui/src/hooks/useRemoteSession.ts` (separate stub, retained for `RemoteAgent` future).
- Editing `tui/src/upstreamproxy/` (PRESERVE-IDENTICAL, no S7 finding).
- Migration of any ipc/ TS file beyond codec.ts test coverage (`bridge.ts`, `mcp.ts`, `llmClient.ts` etc. all unchanged).
- Splitting `notification_push` arm into multiple arms (orthogonal future work if needed).
- Onboarding mcpb-compat to the codec.ts parity gate (mcpb-compat is not an IPC envelope).

---

## 7. Success criteria

| ID | Criterion | Verification |
|---|---|---|
| SC-001 | `tui/src/server/` deleted | `ls tui/src/server/` returns ENOENT |
| SC-002 | `tui/src/hooks/useDirectConnect.ts` deleted | `ls tui/src/hooks/useDirectConnect.ts` returns ENOENT |
| SC-003 | `bun typecheck` PASS in `tui/` | CI green |
| SC-004 | `bun test` PASS in `tui/` | CI green |
| SC-005 | `uv run pytest tests/ipc/` PASS | CI green |
| SC-006 | `notification_push` SWAP docstring contains `"CC parity: NO equivalent"` | `test_notification_push_swap_parity.py` PASS |
| SC-007 | codec.ts envelope drift CI fails on injected drift | `test_codec_envelope_parity.py::test_drift_negative_fixture_triggers_failure` PASS |
| SC-008 | ADR-009 file present and referenced from `docs/adr/` | `ls docs/adr/ADR-009-mcpb-compat-lazy-shim.md` returns 0 |
| SC-009 | IPC arm count = 22 | `test_schema_python_ts_diff.py` PASS |
| SC-010 | Zero new runtime deps in `pyproject.toml` and `tui/package.json` | `git diff pyproject.toml tui/package.json` shows no `[dependencies]` change |
| SC-011 | TUI Layer 5 tmux-capture smoke shows healthy chat boot | `specs/2642-s7-ipc-bridge/scripts/smoke-2642.sh` runs and `snap-NNN-*.txt` includes `UMMAYA` branding + `tool_registry: 24 entries verified` (or current count) |

---

## 8. References (canonical)

- `docs/vision.md § Reference materials` — Claude Code is the first reference for any unclear design decision.
- `docs/requirements/ummaya-migration-tree.md` — L1-A § A6 (Error recovery) + L1-B § B1 (Tool wrapping = work unit).
- `specs/cc-migration-audit/scope-S7-ipc-bridge.md` — full S7 audit
  (44 CC files vs 74 UMMAYA files mapping).
- `specs/cc-migration-audit/decisions.md § S7 IPC Bridge` — the 4 decisions this spec implements.
- `specs/287-tui-ink-react-bun/contracts/` — IPC envelope contract surface.
- `specs/032-ipc-stdio-hardening/` — Spec 032 envelope source-of-truth (correlation_id / transaction_id / payload_chunk arms / heartbeat / resume).
- `.references/claude-code-sourcemap/restored-src/src/ink/useTerminalNotification.ts` — CC terminal OSC notification path (proves CC has no IPC notification arm).
- `.references/claude-code-sourcemap/restored-src/src/remote/` — CC's claude.ai backed remote-session WebSocket cluster (formally NEVER-PORT under DROP-FOR-SWAP).
- `tui/src/mcpb-compat.ts` — UMMAYA-original lazy shim (FR-010 of Spec 2293).

---

## 9. Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| REPL.tsx removal breaks remoteSession path | M | Layer 5 tmux-capture smoke + manual verification of `useRemoteSession` stub still wired |
| codec.ts regex parser misses a field rename | L | Test asserts each field independently with a clear failure message; regex anchored on `/^\s*<field>:/m` |
| Negative fixture not isolated → real CI uses it | L | env-var gate `UMMAYA_IPC_PARITY_DRIFT_FIXTURE=1`; tests/ipc/conftest.py asserts default OFF |
| ADR-009 number collision | L | Confirmed `docs/adr/` has ADR-001 through ADR-008; ADR-009 is the next free slot |
| 22-arm count regression | L | NFR-003 + SC-009 + existing `test_schema_python_ts_diff.py` |
