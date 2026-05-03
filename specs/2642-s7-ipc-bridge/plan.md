# Plan · Spec 2642 · S7 IPC/Bridge cleanup

**Spec**: `specs/2642-s7-ipc-bridge/spec.md`
**Branch**: `feat/2642-s7-ipc-bridge`
**Lead**: Lead Opus (autonomous)
**Date**: 2026-05-03

---

## Phase 0 — Reference materials consultation (NON-NEGOTIABLE)

Per `AGENTS.md § Spec-driven workflow` "Reference source rule",
each design decision below cites a concrete reference.

| Design decision | Reference cited |
|---|---|
| `remote/` 4 files DROP-FOR-SWAP, formal decision | `docs/vision.md § Reference materials` (Claude Code is the first reference; CC's `remote/` is the claude.ai cloud-session bridge — not in KOSMOS surface) + `specs/cc-migration-audit/decisions.md § S7 IPC Bridge` (decision row) + `specs/cc-migration-audit/scope-S7-ipc-bridge.md § 2.3 + § 5 Finding 2` |
| `directConnectManager.ts` + `useDirectConnect.ts` + `createDirectConnectSession.ts` deletion (kept-stub paths previously alive only because of dead `remote/` references) | `specs/cc-migration-audit/scope-S7-ipc-bridge.md § 2.3` (audit "DROP + cleanup" recommendation) + verified call-graph trace (this plan, § 1.1) |
| `notification_push` arm KOSMOS swap-2 justification (NO CC equivalent) | `.references/claude-code-sourcemap/restored-src/src/ink/useTerminalNotification.ts` (CC notification path = terminal OSC, in-process; no IPC arm) + `specs/031-five-primitive-harness/` (SubscriptionHandle for KMA/CBS/RSS push) + `specs/032-ipc-stdio-hardening/` (envelope arm contract) |
| codec.ts ↔ `_BaseFrame` field-level drift CI gate | `specs/032-ipc-stdio-hardening/` (envelope source-of-truth) + `tests/ipc/test_schema_python_ts_diff.py` (existing JSON-Schema parity gate; codec.ts gap identified by audit § 5 Finding 4) |
| ADR-009 (mcpb-compat lazy shim) | `tui/src/mcpb-compat.ts` (existing implementation) + `specs/2293-ui-residue-cleanup/spec.md § FR-010 + § SC-007` + `specs/cc-migration-audit/scope-S7-ipc-bridge.md § 2.5 + § 5 Finding 5` (ADR registration recommendation) |
| `docs/requirements/kosmos-migration-tree.md § L1-A A6` (Error recovery: simple network retry only) | Confirms `directConnect`/`remote/` retry surface has no role in KOSMOS — DROP justified |

### 0.1 — `notification_push` baseline verification (this plan resolves audit § 5 Finding 3)

Audit Finding 3: "1 arm verification needed — does CC have an IPC notification_push arm?"

**Evidence collected**:

```bash
# CC restored-src has NO ipc/ directory at all:
$ ls .references/claude-code-sourcemap/restored-src/src/ipc/
ls: ... No such file or directory

# CC notification surface is terminal OSC only:
$ grep -rln 'showNotification\|notify\|new Notification' .references/.../src/
.references/.../src/ink/useTerminalNotification.ts  # iTerm2/Kitty/Ghostty/bell

# The Tool.ts notify(notificationType) is an in-process callback:
.references/.../src/Tool.ts:210  /** Send an OS-level notification (iTerm2, Kitty, ...) */

# No grep hits for 'notification_push' in CC sources:
$ grep -rln 'notification_push' .references/.../src/
(no results)
```

**Verdict**: `notification_push` is a KOSMOS swap-2 add-on transporting
Spec 031 SubscriptionHandle pushes (KMA disaster CBS, RSS news,
hospital alerts) over the same stdio plane as the rest of the IPC.
**Orthogonal** to CC's terminal OSC notification path — neither
divergence nor regression.

**Action**: Document the finding *in code* via the
`NotificationPushFrame` docstring + a parity test that asserts the
docstring contains the verification literal `"CC parity: NO equivalent"`.
Ensures future audits do not re-discover it.

### 0.2 — `mcpb-compat.ts` decision posture

Per `AGENTS.md § Hard rules` "Stack changes require an ADR under
`docs/adr/`": `mcpb-compat.ts` introduces a *style of dependency
loading* (lazy import shim) that diverges from CC. Even though the
package itself (`@anthropic-ai/mcpb`) is allowed and was added in
Spec 2293, the shim pattern (one isolated file, all callers go through
it) is a KOSMOS-original architectural decision that future agents
will need rationale for. ADR-009 captures this.

---

## Phase 1 — Implementation strategy

### 1.1 — `remote/` cleanup call-graph trace

Pre-cleanup:
```
tui/src/screens/REPL.tsx
├── import { useDirectConnect } from '../hooks/useDirectConnect.js'         (line 62)
├── import type { DirectConnectConfig } from '../server/directConnectManager.js' (line 63)
├── prop directConnectConfig?: DirectConnectConfig                            (line 650, 680)
└── const directConnect = useDirectConnect({ config: directConnectConfig, ...}) (line 1543)
    └── activeRemote = ... directConnect.isRemoteMode ? directConnect : remoteSession  (line 1563)

tui/src/server/directConnectManager.ts (KOSMOS-stubbed; type-only deps to deleted remote/)
tui/src/server/createDirectConnectSession.ts (depends on directConnectManager.DirectConnectConfig)
tui/src/server/types.ts (only consumed by createDirectConnectSession.ts)
tui/src/hooks/useDirectConnect.ts (KOSMOS-stubbed; no-op hook)
```

Post-cleanup:
```
tui/src/screens/REPL.tsx
└── activeRemote = sshRemote.isRemoteMode ? sshRemote : remoteSession
```

Verification:
```bash
grep -rn 'directConnect\|DirectConnect\|createDirectConnectSession' tui/src/
# expected: zero matches outside of the SWAP comment in REPL.tsx
```

### 1.2 — `notification_push` SWAP docstring + parity test

Edit `src/kosmos/ipc/frame_schema.py:NotificationPushFrame.__doc__`:

```python
"""Push from subscription surfaces (Spec 031 SubscriptionHandle).

CC parity: NO equivalent — Claude Code's notification surface is
terminal OSC sequences (iTerm2, Kitty, Ghostty, bell) emitted
in-process from ``ink/useTerminalNotification.ts``. There is no
push-based IPC notification arm in CC. KOSMOS adds this arm as a
swap-2 addition for Korean civic push channels (KMA disaster CBS,
RSS newsroom, hospital alerts) carried over the same stdio plane to
keep a single correlation plane.

role allow-list: notification.
"""
```

Test `tests/ipc/test_notification_push_swap_parity.py`:
- Asserts `NOTIFICATION_PUSH_ROLE_ALLOWLIST == frozenset({"notification"})`.
- Asserts `"CC parity: NO equivalent"` substring in `NotificationPushFrame.__doc__`.
- Constructs a happy-path frame; asserts validation passes.
- Constructs a frame with `payload=""`; asserts ValidationError raised.
- Asserts all required fields (`subscription_id`, `adapter_id`, `event_guid`, `payload_content_type`, `payload`) are non-optional in the schema.

### 1.3 — codec.ts ↔ Python envelope drift CI gate

`tests/ipc/test_codec_envelope_parity.py` strategy:

1. Read `tui/src/ipc/codec.ts` as text (or `KOSMOS_IPC_PARITY_DRIFT_FIXTURE=1` → fixture path).
2. Regex-extract the envelope zod definition. The codec defines the trailer & frame envelope around lines 55-75 (verified):
   ```ts
   correlation_id: z.string().min(1),
   ...
   transaction_id: z.string().min(1).nullable().optional(),
   ```
3. For each of `correlation_id`, `transaction_id`, `frame_seq`, `version`, `role`, `kind`, `timestamp`:
   - Extract zod kind (`string` / `number` / `literal` / `enum`).
   - Extract constraints (`min(1)` / `nullable()` / `optional()` / `min(N).max(M)`).
4. Cross-reference Pydantic `_BaseFrame` model fields:
   - `correlation_id: str = Field(min_length=1)` → must match `z.string().min(1)`, required.
   - `transaction_id: str | None = Field(default=None, min_length=1)` → must match `z.string().min(1).nullable().optional()`.
   - etc.
5. Failure produces a clear message: `"codec.ts:correlation_id constraint mismatch — expected z.string().min(1) (Python: str, min_length=1), got <actual>"`.

Drift fixture `tests/ipc/fixtures/codec_drift_negative.ts`:
```ts
// FIXTURE — intentional drift for parity-test self-test.
// DO NOT import this file from runtime code.
const _baseFrame = z.object({
  correlation_id: z.string().optional(), // <— DRIFT: was .min(1) required
  transaction_id: z.string().min(1).nullable().optional(),
  ...
})
```

Negative-test `test_drift_negative_fixture_triggers_failure`:
```python
def test_drift_negative_fixture_triggers_failure(monkeypatch):
    monkeypatch.setenv("KOSMOS_IPC_PARITY_DRIFT_FIXTURE", "1")
    with pytest.raises(AssertionError, match="correlation_id"):
        run_codec_envelope_parity_check()
```

`conftest.py` guard ensures `KOSMOS_IPC_PARITY_DRIFT_FIXTURE` defaults
unset:
```python
@pytest.fixture(autouse=True)
def _guard_drift_fixture_env_default_off(monkeypatch):
    if os.environ.get("KOSMOS_IPC_PARITY_DRIFT_FIXTURE") == "1":
        # Test must explicitly opt in via monkeypatch; ambient set is rejected.
        monkeypatch.delenv("KOSMOS_IPC_PARITY_DRIFT_FIXTURE", raising=False)
```

### 1.4 — `tui-ipc-drift.yml` extension

Add a new step "Run codec.ts envelope parity check":
```yaml
      - name: Run codec.ts envelope parity check
        working-directory: .
        run: uv run pytest tests/ipc/test_codec_envelope_parity.py -v
        env:
          PYTHONPATH: ${{ github.workspace }}/src
```

Trigger paths extended to include `tui/src/ipc/codec.ts`.

### 1.5 — ADR-009 author

`docs/adr/ADR-009-mcpb-compat-lazy-shim.md` — follow ADR-007 template
(Status / Date / Epic / Affected / Context / Decision / Rationale /
Consequences / References).

---

## Phase 2 — Verification

### 2.1 — Static checks

```bash
cd tui
bun typecheck
bun test
```

### 2.2 — Backend tests

```bash
uv run pytest tests/ipc/ -v
```

### 2.3 — Layer 5 tmux-capture smoke (TUI mandate)

`specs/2642-s7-ipc-bridge/scripts/smoke-2642.sh` invokes
`scripts/tui-tmux-capture.sh` with a scenario:

1. Spawn `bun run tui`.
2. `wait_for_pane "tool_registry: \\d+ entries verified" 30`.
3. `wait_for_pane "KOSMOS" 5`.
4. `tmux send-keys -t kosmos-2642 "/help" Enter`.
5. `wait_for_pane "Available commands" 10`.
6. `tmux send-keys -t kosmos-2642 "" "C-c"` twice.

Per AGENTS.md TUI verification mandate, capture:
- `snap-001-boot.txt`
- `snap-002-help.txt`
- `final.txt`
- 3+ PNG keyframes via vhs `.tape`:
  - `smoke-2642-keyframe-boot.png`
  - `smoke-2642-keyframe-help.png`
  - `smoke-2642-keyframe-exit.png`

Read the PNGs to verify visual rendering (Layer 4).

### 2.4 — Schema drift self-test

Run the negative fixture path and verify it fails:
```bash
KOSMOS_IPC_PARITY_DRIFT_FIXTURE=1 uv run pytest \
  tests/ipc/test_codec_envelope_parity.py::test_drift_negative_fixture_triggers_failure -v
```

---

## Phase 3 — Risks + dispatch

### 3.1 — 4 task groups identified

| Task group | Files | Lead |
|---|---|---|
| TG-A: `remote/` DROP cleanup | tui/src/server/* (delete), tui/src/hooks/useDirectConnect.ts (delete), tui/src/screens/REPL.tsx (edit) | Sonnet teammate |
| TG-B: `notification_push` SWAP doc + test | src/kosmos/ipc/frame_schema.py (edit), tests/ipc/test_notification_push_swap_parity.py (new) | Sonnet teammate |
| TG-C: codec.ts envelope drift CI | tests/ipc/test_codec_envelope_parity.py (new), tests/ipc/fixtures/codec_drift_negative.ts (new), tests/ipc/conftest.py (edit), .github/workflows/tui-ipc-drift.yml (edit) | Sonnet teammate |
| TG-D: ADR-009 + smoke + final verification | docs/adr/ADR-009-mcpb-compat-lazy-shim.md (new), specs/2642-s7-ipc-bridge/scripts/smoke-2642.sh (new), Layer 5 capture | Lead solo |

Tasks A/B/C are independent (different file trees, no cross-dependencies)
→ parallel Sonnet teammate dispatch.
Task D depends on A+B+C completing first → Lead solo at end.

### 3.2 — Constitution compliance pre-check

| AGENTS.md hard rule | Compliance |
|---|---|
| All source text in English | ✅ Korean only in domain docstrings (e.g. `notification_push` payload description) — preserved |
| No new dependency outside spec-driven PR | ✅ Zero new deps |
| Pydantic v2 for all tool I/O | ✅ Frame schema unchanged |
| Stdlib `logging` only | ✅ No new logging surfaces |
| Never call live data.go.kr from CI | ✅ Test is pure stdlib regex + Pydantic introspection |
| Never `--force` push, `--no-verify` | ✅ Lead verifies |
| TUI verification mandatory | ✅ Phase 2.3 Layer 5 + PNG keyframes |
| ADR for stack changes | ✅ ADR-009 part of deliverables |

---

## Phase 4 — Definition of done

- [ ] All US1-US4 acceptance criteria met (spec § 3).
- [ ] FR-001 through FR-012 satisfied (spec § 4).
- [ ] SC-001 through SC-011 verified (spec § 7).
- [ ] PR opened with `Closes #2642` only.
- [ ] CI green (all 12+ workflow gates).
- [ ] Codex P1 inline reviews resolved.
- [ ] Copilot Gate transitions to `completed`.
- [ ] PR merged.
- [ ] Sub-issues of Epic #2642 closed.

## References

- `specs/2642-s7-ipc-bridge/spec.md` (this spec)
- `specs/cc-migration-audit/scope-S7-ipc-bridge.md` (audit)
- `specs/cc-migration-audit/decisions.md § S7 IPC Bridge` (canonical decisions)
- `docs/vision.md § Reference materials`
- `docs/requirements/kosmos-migration-tree.md`
- `specs/032-ipc-stdio-hardening/` (envelope source-of-truth)
- `tests/ipc/test_schema_python_ts_diff.py` (existing JSON-Schema parity gate)
- `tui/scripts/gen-ipc-types.ts` (existing TS-types codegen)
- `.github/workflows/tui-ipc-drift.yml` (existing drift CI)
- `tui/src/mcpb-compat.ts` (KOSMOS-original lazy shim)
- `.references/claude-code-sourcemap/restored-src/src/ink/useTerminalNotification.ts` (CC notification baseline)
