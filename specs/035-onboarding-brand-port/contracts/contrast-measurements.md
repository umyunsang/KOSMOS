# Contract: Contrast measurements

**Feature**: Epic H #1302
**Phase**: 1 (template; populated by `scripts/compute-contrast.mjs` during implementation)
**Reference**: WCAG 2.1 Success Criterion 1.4.3 (body text ≥ 4.5 : 1, non-text ≥ 3.0 : 1)
**Measurement script**: `scripts/compute-contrast.mjs` (Bun, stdlib only — per research R-3)

This contract defines the pair matrix and the reporting format for contrast measurements. The actual ratios are populated when `scripts/compute-contrast.mjs` runs in CI. This document is the acceptance template — a pair row whose measured ratio falls below threshold fails CI.

---

## § 1 · Measurement methodology

1. Parse `tui/src/theme/dark.ts` for every `rgb(r,g,b)` literal.
2. For each pair `(fg, bg)` in § 2 below, compute the relative luminance:
   ```
   L = 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b)
   linearize(c) = (c/255) <= 0.03928 ? (c/255)/12.92 : ((c/255 + 0.055)/1.055) ** 2.4
   ```
3. Compute the contrast ratio:
   ```
   ratio = (max(Lfg, Lbg) + 0.05) / (min(Lfg, Lbg) + 0.05)
   ```
4. Round to two decimal places.
5. Compare against threshold. Fail CI if any body-text pair < 4.5 or any non-text pair < 3.0.

---

## § 2 · Pair matrix

**Background token**: `background = #0a0e27`.

### Body-text pairs (threshold ≥ 4.5)

| # | Foreground token | Foreground hex | Background hex | Measured ratio | Pass? |
|---|---|---|---|---|---|
| 1 | `wordmark` | `#e0e7ff` | `#0a0e27` | — | — |
| 2 | `subtitle` | `#94a3b8` | `#0a0e27` | — | — |
| 3 | `text` | `rgb(255,255,255)` (→ `#ffffff`) | `#0a0e27` | — | — |
| 4 | `subtle` | `rgb(80,80,80)` (→ `#505050`) | `#0a0e27` | — | — |
| 5 | `success` | `rgb(78,186,101)` | `#0a0e27` | — | — |
| 6 | `error` | `rgb(255,107,128)` | `#0a0e27` | — | — |
| 7 | `warning` | `rgb(255,193,7)` | `#0a0e27` | — | — |
| 8 | `agentSatelliteKoroad` | `#f472b6` | `#0a0e27` | — | — |
| 9 | `agentSatelliteKma` | `#34d399` | `#0a0e27` | — | — |
| 10 | `agentSatelliteHira` | `#93c5fd` | `#0a0e27` | — | — |
| 11 | `agentSatelliteNmc` | `#c4b5fd` | `#0a0e27` | — | — |

### Non-text pairs (threshold ≥ 3.0)

| # | Foreground token | Foreground hex | Background hex | Measured ratio | Pass? |
|---|---|---|---|---|---|
| 12 | `kosmosCore` | `#6366f1` | `#0a0e27` | — | — |
| 13 | `kosmosCoreShimmer` | `#a5b4fc` | `#0a0e27` | — | — |
| 14 | `orbitalRing` | `#60a5fa` | `#0a0e27` | — | — |
| 15 | `orbitalRingShimmer` | `#c7d2fe` | `#0a0e27` | — | — |

### Diff pairs (threshold ≥ 3.0 — non-text UI chrome)

| # | Foreground token | Foreground hex | Background hex | Measured ratio | Pass? |
|---|---|---|---|---|---|
| 16 | `diffAdded` | `rgb(34,92,43)` | `#0a0e27` | — | — |
| 17 | `diffRemoved` | `rgb(122,41,54)` | `#0a0e27` | — | — |

---

## § 3 · Remediation contract

If any row above fails its threshold:

1. The failing token's value is raised (never lowered) in `dark.ts` per spec FR-011.
2. The new value MUST be drawn from the `assets/kosmos-logo.svg` 16-hex palette when the raise affects a brand token; for semantic tokens, the raise may use any hex that meets the threshold.
3. The raise is re-measured; CI passes only when every row meets its threshold.
4. The final measured values are recorded in `docs/design/contrast-measurements.md` (populated at implementation time from this template).

---

## § 4 · Documentation integration

On PR merge, the populated ratios are copied from this template into `docs/design/contrast-measurements.md` (new file created in this PR). The `docs/design/brand-system.md § 4 Palette values` section references `docs/design/contrast-measurements.md` for the authoritative ratios.

---

## § 5 · Traceability

| Clause | Spec FR | Invariant | Test |
|---|---|---|---|
| § 1 methodology | FR-003, SC-001 | I-4 | `scripts/compute-contrast.mjs` CI run |
| § 2 pair matrix | FR-003 | I-4 | matrix exhaustiveness test |
| § 3 remediation | FR-011 | I-4 | re-measurement after raise |
| § 4 integration | SC-010 | — | `docs/design/contrast-measurements.md` exists + referenced from § 4 |
