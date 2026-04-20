# Contract: Onboarding step registry

**Feature**: Epic H #1302
**Phase**: 1
**Owner of authoritative source**: `tui/src/components/onboarding/Onboarding.tsx`
**CC reference**: `.references/claude-code-sourcemap/restored-src/src/components/Onboarding.tsx` (CC 2.1.88, a8a678c)

This contract specifies the 3-step linear citizen onboarding state machine. It binds FR-012 / FR-014 and backs User Stories 1 / 2 / 3.

---

## § 1 · Step registry

Fixed ordering, no branching:

```typescript
type StepId = "splash" | "pipa-consent" | "ministry-scope-ack" | "done"

interface OnboardingStep {
  stepId: StepId
  component: React.FC<{ onAdvance: () => void; onExit: () => void }>
  advanceCondition: () => boolean
  skipCondition: (memdir: MemdirUserState) => boolean
  exitSideEffect: "write-consent-record" | "write-scope-record" | "none"
}

const STEPS: readonly OnboardingStep[] = [
  {
    stepId: "splash",
    component: SplashStep,
    advanceCondition: () => true,  // any keypress advances
    skipCondition: () => false,    // splash always renders
    exitSideEffect: "none",
  },
  {
    stepId: "pipa-consent",
    component: PIPAConsentStep,
    advanceCondition: () => true,  // Enter advances on acceptance
    skipCondition: (memdir) => memdir.consentRecord?.consent_version === CURRENT_CONSENT_VERSION,
    exitSideEffect: "write-consent-record",
  },
  {
    stepId: "ministry-scope-ack",
    component: MinistryScopeStep,
    advanceCondition: () => true,  // Enter advances after selection
    skipCondition: (memdir) => memdir.scopeRecord?.scope_version === CURRENT_SCOPE_VERSION,
    exitSideEffect: "write-scope-record",
  },
  {
    stepId: "done",
    component: () => null,  // passthrough; returns the citizen to the main TUI
    advanceCondition: () => true,
    skipCondition: () => false,
    exitSideEffect: "none",
  },
]
```

Version constants:

```typescript
const CURRENT_CONSENT_VERSION = "v1"
const CURRENT_SCOPE_VERSION = "v1"
```

Bumping either constant invalidates all prior records by design (research R-6).

---

## § 2 · State transition

```
                       Enter             Enter                    Enter
   [ splash ]  ──────▶  [ pipa-consent ] ──────▶  [ ministry-scope-ack ] ──────▶  [ done ]
        │                     │                           │
        │ Escape              │ Escape                    │ Escape
        └─────────────────────┴───────────────────────────┘
                                    ▼
                        useApp().exit() — no record written
```

**Keybinding surface** (per step):

| Step | Enter | Escape | ↑ / ↓ | Space | Ctrl+C / Ctrl+D |
|---|---|---|---|---|---|
| splash | advance | exit | — | — | exit |
| pipa-consent | accept + write record + advance | exit | — | — | exit |
| ministry-scope-ack | confirm current selection + write record + advance | exit | move selection | toggle current ministry | exit |
| done | passthrough | passthrough | — | — | exit |

**IME safety**: every keyboard handler at step level is gated on `!useKoreanIME().isComposing` per accessibility-gate.md AG-04. This applies even though onboarding has no free-text input — the Enter key during a Hangul composition must commit the composition, not advance the step.

---

## § 3 · Session-start decision

Executed once per session (at `main.tsx` bootstrap), before `Onboarding` renders:

```typescript
async function resolveStartStep(memdir: MemdirUserState): Promise<StepId> {
  const consentFresh = memdir.consentRecord?.consent_version === CURRENT_CONSENT_VERSION
  const scopeFresh = memdir.scopeRecord?.scope_version === CURRENT_SCOPE_VERSION

  if (consentFresh && scopeFresh) return "splash"        // fast-path: splash-only, 3 s budget
  if (consentFresh && !scopeFresh) return "ministry-scope-ack"  // skip PIPA
  return "splash"                                        // full flow
}
```

**Fast-path contract (SC-012)**: when `resolveStartStep` returns `"splash"` AND both records are fresh, the splash auto-advances after 3 s OR on the first keypress, whichever comes first. Total budget: 3 s from launch to main TUI.

---

## § 4 · Side-effect contracts

### `write-consent-record`

Triggered by `pipa-consent.advanceCondition()` returning `true`. Sequence:

1. Construct `PIPAConsentRecord` (per `contracts/memdir-consent-schema.md`) with current `CURRENT_CONSENT_VERSION`, `datetime.now(UTC)`, active session UUIDv7, `aal_gate = AAL1` default.
2. Write synchronously to `~/.kosmos/memdir/user/consent/<timestamp>-<session_id>.json.tmp`.
3. `fsync` the tmp file.
4. `os.rename` to the final path.
5. Advance only after step 4 completes; on any error, render a citizen-visible Korean error message and do NOT advance.

### `write-scope-record`

Triggered by `ministry-scope-ack.advanceCondition()` returning `true`. Same sequence, with `MinistryScopeAcknowledgment` (per `contracts/memdir-ministry-scope-schema.md`) to `~/.kosmos/memdir/user/ministry-scope/<timestamp>-<session_id>.json`.

---

## § 5 · Accessibility contract

**Splash step** (row 165 `[ag-onboarding]`):

- WCAG 1.4.3 contrast — every foreground token renders against the `background` token at ≥ 4.5 : 1 (text) or ≥ 3.0 : 1 (non-text).
- WCAG 2.1.1 keyboard — Enter advances, Escape exits; no mouse dependency.
- WCAG 2.4.7 focus visible — first interactive affordance is the splash itself; focus indicator is inverse-video on the "Press Enter to continue" hint line.
- WCAG 4.1.2 role — the splash is announced as "KOSMOS onboarding — splash screen" on first render via the text stream.
- KWCAG — 은하계 스플래시 대체 텍스트 ("KOSMOS 은하계 스플래시 — 한국도로공사 · 기상청 · 건강보험심사평가원 · 국립중앙의료원"); screen-reader narration enumerates all 4 ministries.

**PIPA consent step** (no existing catalog row — new component):

- WCAG 1.4.3, 2.1.1, 2.4.7, 4.1.2 + KWCAG consent-flow narration.
- Consent version string is announced; timestamp is computed at accept time and is not announced.
- AAL gate is announced in citizen-readable Korean (`AAL1` → "기본 인증 단계").

**Ministry scope step** (no existing catalog row — new component):

- Same WCAG + KWCAG set.
- Each ministry's toggle state is announced on selection change.
- Korean ministry names + English adapter codes per research R-9 (`한국도로공사 (KOROAD)`, etc.).

---

## § 6 · Traceability

| Clause | Spec FR | Invariant | Test |
|---|---|---|---|
| § 1 step registry | FR-012 | I-6 | `Onboarding.snap.test.tsx` asserts 4 steps |
| § 2 state transition | FR-014 | I-7 | escape-exit branch test |
| § 3 session-start decision | FR-016, SC-012 | I-7, X-1 | `resolveStartStep.test.ts` |
| § 4 side effects | FR-013, FR-016 | I-8, I-10, I-13, I-15 | `write-consent-record` + `write-scope-record` integration test |
| § 5 accessibility | FR-024, FR-025 | I-23 | `[ag-onboarding]` manual screen-reader smoke |
