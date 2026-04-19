# Contract — Mode Spectrum + Shift+Tab Cycle + Killswitch

**Feature**: 033-permission-v2-spectrum
**Artifact**: Behavioral contract for `src/kosmos/permissions/modes.py` + TUI `tui/src/permissions/ModeCycle.tsx`
**Date**: 2026-04-20

> References: Claude Code 2.1.88 `PermissionMode.ts` / `getNextPermissionMode.ts` (mirrored with the `dontAsk` KOSMOS addition). Constitution §II (fail-closed, NON-NEGOTIABLE).

## 1. Mode Set

`Literal["default", "plan", "acceptEdits", "bypassPermissions", "dontAsk"]`

Internal modes (`auto`, `bubble`) from Claude Code are EXCLUDED per spec §Out of Scope.

## 2. Shift+Tab Cycle (fast cycle)

Only cycles among low/mid-risk modes:

```
default → plan → acceptEdits → default → ...
```

`bypassPermissions` and `dontAsk` are **excluded from the fast cycle**. They are reachable ONLY via explicit slash commands:

- `/permissions bypass` — activates `bypassPermissions` after confirmation dialog
- `/permissions dontAsk` — activates `dontAsk` after confirmation dialog
- `/permissions default` — resets to `default` from any mode

From `bypassPermissions` or `dontAsk`, pressing Shift+Tab returns directly to `default` (escape hatch — Invariant S1).

## 3. State Machine (adjacency)

| Current | Shift+Tab | `/permissions bypass` | `/permissions dontAsk` | `/permissions default` |
|---------|-----------|----------------------|------------------------|------------------------|
| `default` | `plan` | confirm → `bypassPermissions` | confirm → `dontAsk` | no-op |
| `plan` | `acceptEdits` | confirm → `bypassPermissions` | confirm → `dontAsk` | `default` |
| `acceptEdits` | `default` | confirm → `bypassPermissions` | confirm → `dontAsk` | `default` |
| `bypassPermissions` | `default` (escape) | no-op | confirm → `dontAsk` | `default` |
| `dontAsk` | `default` (escape) | confirm → `bypassPermissions` | no-op | `default` |

## 4. TUI Status Bar Contract

Every mode transition MUST update the status bar with a distinct color + label:

| Mode | Color | Label |
|------|-------|-------|
| `default` | neutral (gray) | `모드: 기본 (매 호출 확인)` |
| `plan` | cyan | `모드: 계획 (실행 없음)` |
| `acceptEdits` | green | `모드: 자동허용 (가역·공용)` |
| `bypassPermissions` | **red/yellow flashing** | `⚠ 모드: 우회 (되돌릴 수 없는 호출 계속 확인)` |
| `dontAsk` | blue | `모드: 사전허용 (목록만 자동)` |

**Invariant UI1 — `bypassPermissions` status bar flashes red/yellow.** Constitutional §II visibility requirement.

## 5. Killswitch Pre-Evaluation Order

**CRITICAL:** For EVERY tool call, the permission pipeline MUST execute in this exact order:

```
1. Killswitch.pre_evaluate(context) -> Decision | None
   - If mode == "bypassPermissions":
     - If context.is_irreversible: return Decision.ASK  (K2)
     - If context.pipa_class == "특수": return Decision.ASK  (K3)
     - If context.auth_level == "AAL3": return Decision.ASK  (K4)
   - Return None (not killswitch-gated)

2. Mode.evaluate(context) -> Decision | None
   - Apply mode-specific auto-allow/auto-deny logic.

3. Rule.resolve(context) -> Decision | None
   - Check session → project → user scope.
   - Apply R1 (deny wins) + R2 (narrower wins).

4. Prompt.ask(context) -> Decision
   - Fall-through: always ask the citizen.
```

**Invariant P1 — Killswitch is step 1. No exception.** Test via mutation: any implementation that runs Mode before Killswitch MUST fail `test_killswitch_priority_order`.

**Invariant P2 — Killswitch returns ASK, not ALLOW/DENY.** It does not make the decision for the user — it forces the prompt to appear. The user still chooses.

**Invariant P3 — Killswitch prompt is not cacheable.** No `allow` rule can be saved from a killswitch-triggered prompt. (K5)

## 6. Confirmation Dialog Contract

`/permissions bypass` and `/permissions dontAsk` MUST show a confirmation dialog before transitioning:

```
⚠ 경고: bypassPermissions 모드로 전환

이 모드에서는 가역 호출이 확인 없이 실행됩니다.
단, 다음은 여전히 매번 확인합니다:
  - 되돌릴 수 없는 호출 (is_irreversible=True)
  - 특수 범주 (pipa_class=특수)
  - AAL3 인증 필요 호출

계속하시겠습니까? [y/N]
Default: N
```

**Invariant UI2 — Default focus is "N" (reject).** Consistent with consent prompt defensive UI.

## 7. Persistence Contract

**Modes are session-scoped.** They DO NOT persist across process restarts.

| State | Persisted? | Storage |
|-------|------------|---------|
| Current mode | ✗ No | In-memory session state. Restart → `default`. |
| Persistent rules | ✓ Yes | `~/.kosmos/permissions.json` |
| Consent ledger | ✓ Yes | `~/.kosmos/consent_ledger.jsonl` |

**Invariant PR1 — `bypassPermissions` cannot be sticky.** Every session starts at `default`, requiring citizen to explicitly re-enable bypass. No "remember" checkbox.

## 8. Test Matrix (required)

| # | Starting mode | Action | Expected ending mode | Expected side effect |
|---|---------------|--------|---------------------|----------------------|
| M01 | `default` | Shift+Tab | `plan` | Status bar: cyan |
| M02 | `plan` | Shift+Tab | `acceptEdits` | Status bar: green |
| M03 | `acceptEdits` | Shift+Tab | `default` | Status bar: neutral |
| M04 | `default` | Shift+Tab (4 times) | `default` | Full cycle completes |
| M05 | `default` | `/permissions bypass` + confirm Y | `bypassPermissions` | Status bar: flashing red/yellow |
| M06 | `default` | `/permissions bypass` + confirm N | `default` | No change |
| M07 | `bypassPermissions` | Shift+Tab | `default` | Escape hatch S1 |
| M08 | `bypassPermissions` | call irreversible tool | **PROMPT appears** | K2 + ledger record |
| M09 | `bypassPermissions` | call public reversible tool | silent allow | No prompt |
| M10 | `bypassPermissions` | call pipa_class="특수" tool | **PROMPT appears** | K3 + ledger record |
| M11 | `bypassPermissions` | call auth_level="AAL3" tool | **PROMPT appears** | K4 + ledger record |
| M12 | `bypassPermissions` | call irreversible tool twice | **2 prompts + 2 ledger records** | K6 (action_digest distinct) |
| M13 | `default` | `/permissions dontAsk` + confirm Y | `dontAsk` | Status bar: blue |
| M14 | `dontAsk` | call tool in allow-list | silent allow | No prompt |
| M15 | `dontAsk` | call tool NOT in allow-list | fall back to `default` prompt | Ledger record |
| M16 | `plan` | call any tool | **NO execution** | Preview string only |
| M17 | Restart process (any mode) | — | `default` | PR1 enforced |

## 9. OTEL Telemetry (Spec 021)

Every mode transition emits:
- `permission.mode.changed` span — attrs: `from_mode`, `to_mode`, `trigger: Literal["shift_tab","slash_command"]`, `confirmed: bool`

Every killswitch gate emits:
- `permission.killswitch.triggered` span — attrs: `reason: Literal["irreversible","pipa_class_특수","aal3"]`, `tool_id`, `mode`

## 10. Exit Criteria

- [ ] All 17 M-matrix scenarios implemented in `tests/permissions/test_mode_transition.py`.
- [ ] Killswitch priority order enforced via `test_killswitch_priority_order.py` mutation test.
- [ ] TUI status bar transitions verified via Ink snapshot tests.
- [ ] No persistence of mode state across process restarts (`test_mode_not_persisted`).
- [ ] Confirmation dialog default focus = N (UI2 enforced).
