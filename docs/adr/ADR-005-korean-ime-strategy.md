# ADR-005: Korean IME Strategy — @jrichman/ink Fork

**Status**: Accepted
**Date**: 2026-04-19
**Epic**: #287 (KOSMOS TUI — Ink + React + Bun)

---

## Context

KOSMOS's primary user demographic is Korean citizens interacting with Korean
public-service APIs (AI Action Plan Principle 8). Korean input via IME
(Hangul composition) is therefore a non-negotiable baseline, not an edge case.

The core problem (R1 in
`specs/287-tui-ink-react-bun/research.md § 2.6`) is that Ink's default
`useInput` hook cannot buffer Hangul composition sequences on macOS and Linux
IMEs. The IME sends multi-step composition events (e.g., jamo keystrokes that
form a single syllable); Ink's raw keypress listener flushes each partial
composition as a committed character, producing garbled input. This is a known
upstream defect tracked by Claude Code issues #3045, #22732, #22853, #27857,
and #29745. None of these issues carry a patch forecast from the Ink maintainer.

Two implementation paths have been identified:

**Option (a) — `@jrichman/ink@6.6.9` fork**

Replace the `ink@^7` pin in `tui/package.json` with
`"ink": "npm:@jrichman/ink@6.6.9"`. This fork patches `useInput` to honour
the system IME composition buffer. It requires React 18 (Ink 6 dependency
tree) rather than React 19.2.

**Option (b) — Node stdlib `readline` hybrid**

Keep `ink@^7` for rendering. Replace Ink's `useInput` with a custom
`tui/src/ipc/readline-bridge.ts` that uses Node's `readline.createInterface`
(available in Bun via its Node-compatibility layer) to capture raw keystrokes
before dispatching them to React state. Option (b) preserves the Ink 7 +
React 19.2 pin but requires KOSMOS-original reimplementation of Ink's input
state machine (arrow keys, backspace, Ctrl-chords, paste detection).

This ADR forces the choice between the two options and closes the debate so
that T103 (package pin update) and T104 (strategy-selector hook) can proceed.
It is gated by SC-1 (`FR-014` + `FR-057`): no IME code may land until this
ADR file exists.

---

## Decision

**Choose Option (a) — `@jrichman/ink@6.6.9` fork.**

The package pin in `tui/package.json` is changed from:

```json
"ink": "^7"
```

to:

```json
"ink": "npm:@jrichman/ink@6.6.9"
```

A strategy-selector environment variable `KOSMOS_TUI_IME_STRATEGY` is
introduced (values: `fork` [default] | `readline`) so that a future spec can
swap strategies without a spec revision. At `fork`, the application uses the
patched `useInput` from the fork. At `readline`, it activates a
`readline-bridge` shim (stub only in v1; full implementation deferred).

### Downstream task impact

- **T103**: Update `tui/package.json` pin to `npm:@jrichman/ink@6.6.9` and
  confirm React 18 peer-dep resolution.
- **T104**: Implement the `KOSMOS_TUI_IME_STRATEGY` selector hook; wire the
  default `fork` path through `useInput`; provide a stub error for the
  `readline` path (deferred full implementation).
- **T102 precondition**: T102 adds a CI test asserting this ADR file
  (`docs/adr/ADR-005-korean-ime-strategy.md`) exists; the build fails if the
  file is absent. This gate must pass before T103/T104 run.

### Specification traceability

| Spec ref | Short description | How this ADR satisfies it |
|----------|-------------------|--------------------------|
| FR-014 | IME strategy must be captured in an ADR before any IME code is written | This ADR is that document |
| FR-015 | Korean Hangul composition must not corrupt the input buffer | Option (a) delivers the patched `useInput` that satisfies this requirement |
| FR-016 | IME strategy must be swappable via env var without code change | `KOSMOS_TUI_IME_STRATEGY` env var provides the swap mechanism |
| FR-057 | ADR gate — SC-1 must pass before IME implementation tasks execute | This file's existence is the gate condition checked by T102 |
| SC-4 | Korean IME headless test must pass in CI | The fork's patched input path is the component that makes a headless composition test tractable |
| R1 | Korean IME upstream defect (research.md risk register) | Option (a) resolves R1 by adopting the fork rather than waiting for upstream |

---

## Consequences

**Positive:**

- Korean Hangul composition works correctly out of the box. Gemini CLI ships
  `@jrichman/ink` in production — this is the single most credible data point
  available (`.references/gemini-cli/package.json`).
- The fork is approximately 20 lines of diff from upstream Ink 6.6.9 — the
  maintenance surface is small and auditable.
- React 18 is a stable, well-understood target; no known regressions for the
  KOSMOS TUI feature set.
- The `KOSMOS_TUI_IME_STRATEGY` env var ensures Option (b) can be activated
  in a future spec without touching this ADR.

**Negative / Trade-offs:**

- **React 18 instead of React 19.2**: We lose React 19.2 Suspense improvements
  and StrictMode hardening. For a terminal REPL with no server components and
  no concurrent-mode rendering, this is an acceptable downgrade. The KOSMOS TUI
  does not use Suspense boundaries; `useSyncExternalStore` (the primary React
  18+ store primitive used in Claude Code's rendering spine) is available in
  React 18.
- **Fork tracking obligation**: When a new upstream Ink 6.x patch releases, the
  fork must be manually checked for divergence. The risk is bounded because Ink
  6 is in maintenance mode; breaking changes are unlikely.
- **Option (b) is deferred, not closed**: The `readline` path is stubbed but
  not implemented. If the fork is ever deprecated or becomes incompatible with
  a future Bun release, Option (b) becomes the fallback. The implementation
  work (replicating Ink's input state machine) remains unquantified.

---

## Alternatives Considered

### Option (b) — Node `readline` hybrid (rejected)

Keep `ink@^7` + React 19.2. Add `tui/src/ipc/readline-bridge.ts` using
`readline.createInterface` to intercept raw keystrokes before Ink's `useInput`
sees them.

**Rejection reasons:**

1. **No production reference**: No open-source project has shipped a
   `readline`-backed Ink input layer for Korean. The cursor-position desync
   risk (R3 in `research.md`) is a known hazard with no prior art to consult.
2. **High KOSMOS-original maintenance**: Ink's `useInput` state machine covers
   arrow keys, backspace, Ctrl-chord sequences, mouse events, and paste
   detection. Reimplementing this in a bridge layer would produce a substantial
   KOSMOS-original code surface that diverges from upstream with every Ink
   patch. The project's guiding principle (harness, not reimplementation) makes
   this unacceptable.
3. **Bun Node-compat surface risk**: `readline.createInterface` is available
   in Bun's Node-compatibility layer, but edge cases in terminal raw-mode
   handling under Bun have not been validated for Korean IME sequences. The
   compatibility gap is an unknown risk.
4. **Benefit does not justify cost**: The sole benefit is staying on Ink 7 +
   React 19.2. KOSMOS v1 does not use any Ink 7-only APIs that would be lost
   on the fork. The upgrade cost is zero in functional terms.

### Wait for upstream Ink Korean IME fix (rejected)

Claude Code issues #3045, #22732, #22853, #27857, and #29745 have been open
without an upstream patch. Blocking the TUI on an unscheduled upstream fix
is not viable for the KSC 2026 delivery target.

---

## References

- `specs/287-tui-ink-react-bun/research.md § 2.6` — Korean IME strategy
  decision rationale and risk register entry R1
- `.references/gemini-cli/package.json` — Gemini CLI production pin of
  `@jrichman/ink` (Apache-2.0 reference implementation)
- Claude Code upstream IME issues: #3045, #22732, #22853, #27857, #29745
- Spec 287 FR-014 (IME ADR gate), FR-015 (composition correctness), FR-016
  (strategy env var), FR-057 (SC-1 ADR-existence gate)
- `docs/adr/ADR-001-geocoding-provider.md` — ADR format reference
- `docs/adr/ADR-002-bm25-retrieval-gate.md` — ADR format reference
