// SPDX-License-Identifier: Apache-2.0
// KOSAX-original: no upstream CC analog (CC has no reduced-motion gate).
// Pattern mirror: tui/src/hooks/useKoreanIME.ts (Spec 287).
// Reference: specs/035-onboarding-brand-port/plan.md § Phase 0 R-8.
//
// Centralises the reduced-motion decision so AnimatedAsterisk, LogoV2, and
// any future shimmer consumer reads a single source of truth.  The hook is
// deliberately synchronous — NO_COLOR and KOSAX_REDUCED_MOTION are read once
// per render; env-var mutations at runtime are out of scope (AGENTS.md forbids
// runtime env mutation, and Ink re-renders on input/resize only).

export type ReducedMotionState = {
  prefersReducedMotion: boolean
}

/**
 * Returns `{ prefersReducedMotion: true }` when EITHER of the following is set:
 *   - `NO_COLOR` (any non-empty value; https://no-color.org/ convention)
 *   - `KOSAX_REDUCED_MOTION` (any non-empty value, per KOSAX env prefix rule)
 *
 * Consumers:
 *   - `AnimatedAsterisk.tsx` — gates the shimmer-cycle render loop.
 *   - `LogoV2.tsx` — skips per-frame re-render of the orbital-ring shimmer.
 *   - `KosaxCoreIcon.tsx` — gates the `shimmering` prop effect.
 */
export function useReducedMotion(): ReducedMotionState {
  const noColor = process.env.NO_COLOR
  const kosaxFlag = process.env.KOSAX_REDUCED_MOTION
  const prefersReducedMotion =
    (noColor !== undefined && noColor.length > 0) ||
    (kosaxFlag !== undefined && kosaxFlag.length > 0)
  return { prefersReducedMotion }
}
