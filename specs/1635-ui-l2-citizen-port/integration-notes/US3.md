# US3 Integration Notes — Onboarding 5-step

**Author**: Teammate #3 (Frontend Developer)
**Date**: 2026-04-25
**Spec**: specs/1635-ui-l2-citizen-port/spec.md (FR-001..007)
**Tasks completed**: T040, T041, T042, T043 (existing), T044, T045, T046, T047, T048, T050, T051
**Tasks deferred to Lead**: T049, T052

---

## Files Delivered

### Step components (T040–T044)

| File | Task | Description |
|------|------|-------------|
| `tui/src/components/onboarding/PreflightStep.tsx` | T040 | Bun version + graphics protocol + KOSMOS_* env-var ✓/✗ checks |
| `tui/src/components/onboarding/ThemeStep.tsx` | T041 | UFO mascot idle pose (violet palette) + theme selector |
| `tui/src/components/onboarding/PipaConsentStep.tsx` | T042 | PIPA §26 trustee notice box + Y/N consent (FR-006) |
| `tui/src/components/onboarding/MinistryScopeStep.tsx` | T043 | Existing Spec 035 component; suitable as-is for 5-step flow |
| `tui/src/components/onboarding/TerminalSetupStep.tsx` | T044 | 4 a11y toggles + Shift+Tab / Ctrl-O keybinding hints |

### Flow driver and commands (T045–T048)

| File | Task | Description |
|------|------|-------------|
| `tui/src/components/onboarding/OnboardingFlow.tsx` | T045 | 5-step driver; loads/saves `OnboardingState`; supports isolation mode |
| `tui/src/commands/onboarding.ts` | T046 | `/onboarding [step-name]` parser + help metadata |
| `tui/src/commands/lang.ts` | T047 | `/lang ko|en` parser + `getCurrentLocale()` |
| `TerminalSetupStep.tsx` + `OnboardingFlow.tsx` | T048 | a11y toggle persistence wired to `saveAccessibilityPreference()` |

### Tests (T050–T051)

| File | Covers |
|------|--------|
| `tui/tests/components/onboarding/PreflightStep.test.tsx` | T040 — 7 tests |
| `tui/tests/components/onboarding/ThemeStep.test.tsx` | T041 — 6 tests |
| `tui/tests/components/onboarding/PipaConsentStep.test.tsx` | T042 — 6 tests |
| `tui/tests/components/onboarding/TerminalSetupStep.test.tsx` | T044 — 8 tests |
| `tui/tests/components/onboarding/OnboardingFlow.test.tsx` | T045 — 6 tests |
| `tui/tests/commands/onboarding.test.ts` | T046 — 12 tests |
| `tui/tests/commands/lang.test.ts` | T047 — 12 tests |

**Total: 57 tests, all passing.**

---

## T049 — main.tsx Entry Gate

**What Lead needs to add** (do NOT touch `tui/src/main.tsx` before this integration):

### Import path

```ts
import { OnboardingFlow, resetOnboardingState } from './components/onboarding/OnboardingFlow.js'
import { isOnboardingComplete } from './schemas/ui-l2/onboarding.js'
import { loadOnboardingState } from './utils/uiL2Memdir.js'
import { parseOnboardingCommand } from './commands/onboarding.js'
```

### Gate predicate

```ts
// In main.tsx, before mounting AppInner/REPL:
const state = await loadOnboardingState()
const needsOnboarding = !isOnboardingComplete(state)
```

### Rendering

```tsx
// Replace the Onboarding component from Spec 035 with:
{needsOnboarding ? (
  <OnboardingFlow
    sessionId={resolvedSessionId}
    onComplete={() => setNeedsOnboarding(false)}
    locale={getCurrentLocale()}
  />
) : (
  <AppInner /* existing REPL entry */ />
)}
```

### /onboarding command dispatch

When the REPL dispatcher receives `/onboarding [arg]`:

```ts
import { parseOnboardingCommand } from '../commands/onboarding.js'
import { resetOnboardingState } from '../components/onboarding/OnboardingFlow.js'
import { loadOnboardingState } from '../utils/uiL2Memdir.js'

const result = parseOnboardingCommand(arg)
if (result.mode === 'full') {
  const current = await loadOnboardingState()
  await resetOnboardingState(current)
  // Mount OnboardingFlow with isolatedStep=undefined (full sequence)
  setOnboardingMode({ active: true, isolatedStep: undefined })
} else if (result.mode === 'isolated') {
  // Mount OnboardingFlow with isolatedStep=result.step
  setOnboardingMode({ active: true, isolatedStep: result.step })
} else {
  // Show error toast with result.message
}
```

---

## T052 — OTEL kosmos.ui.surface=onboarding emission

**What Lead needs to add**: `emitSurfaceActivation('onboarding', ...)` is already called
inside each step component via a `useEffect` at mount time. The Lead should additionally
emit the surface activation at `OnboardingFlow` mount in `main.tsx`:

```ts
import { emitSurfaceActivation } from './observability/surface.js'

// In the gate predicate block, before mounting OnboardingFlow:
if (needsOnboarding) {
  emitSurfaceActivation('onboarding', { 'onboarding.mode': 'initial' })
}
```

This ensures the OTEL collector receives a surface activation span even if a step is
skipped (e.g., the user presses Esc during preflight before any step-level span fires).

---

## Architecture notes

### State persistence

- `OnboardingState` lives at `~/.kosmos/memdir/user/onboarding/state.json`
  (atomic-rename writes via `uiL2Memdir.ts`).
- `AccessibilityPreference` lives at `~/.kosmos/memdir/user/preferences/a11y.json`
  (same atomic-rename path). Written on every toggle AND on Enter (advance).
- PIPA consent records continue to use the Spec 035 `memdir/io.ts` writers
  (`writeConsentRecord`).
- Ministry scope records continue to use `writeScopeRecord` from the same module.

### Isolation mode contract

`/onboarding <step-name>` sets `isolatedStep` on `OnboardingFlow`. In this mode:
- `current_step_index` in persisted state is **not** reset.
- Only the named step renders.
- On advance, `onComplete()` is called immediately (no index increment).
- The `completed_at` for the replayed step IS updated.

### Resume-after-SIGINT

If the process exits mid-onboarding (SIGINT, kill), the next launch reads `current_step_index`
from the persisted state and starts from that index. Steps with `completed_at !== null` at
a lower index are not re-run (they stay in `steps[]` for audit purposes).

### /lang command integration

`parseLangCommand` mutates `process.env['KOSMOS_TUI_LOCALE']`. Components that call
`getUiL2I18n(getCurrentLocale())` will pick up the new locale on the next render.
Components using the module-level `uiL2I18n` constant will NOT hot-swap; they need
to be unmounted/remounted or refactored to call `getUiL2I18n()` instead.

The Lead should verify the REPL's modal and toast components call `getUiL2I18n(getCurrentLocale())`
rather than the module-level constant, or implement a React context for the locale.

---

## Test coverage summary

| FR | Test file | Test count |
|----|-----------|------------|
| FR-001 (5-step sequence) | OnboardingFlow.test.tsx | 6 |
| FR-001 step 1 (preflight) | PreflightStep.test.tsx | 7 |
| FR-001 step 2 (theme/FR-035) | ThemeStep.test.tsx | 6 |
| FR-001 step 3 (pipa/FR-006) | PipaConsentStep.test.tsx | 6 |
| FR-001 step 5 (terminal/FR-005) | TerminalSetupStep.test.tsx | 8 |
| FR-003 (/onboarding command) | onboarding.test.ts | 12 |
| FR-004 (/lang command) | lang.test.ts | 12 |

**57 tests total. All pass.**
