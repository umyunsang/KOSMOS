// SPDX-License-Identifier: Apache-2.0
// Epic 1 finish — FR-012: UMMAYA bypass detection backstop.
//
// The CC `bypassPermissions` flag gates the dangerous-mode UX.  In UMMAYA
// the gauntlet must NEVER be silently skipped for credentialed or side-
// effecting primitives (verify / submit) regardless of bypassPermissions or
// auto-mode state.
//
// This module exposes two guards:
//   - isUmmayaBypassAllowed(primitive, toolPermissionContext)
//     Returns true only when bypass is safe (lookup).
//     Returns false for verify / submit.
//
//   - assertUmmayaGauntletRequired(primitive, toolPermissionContext)
//     Throws if a blocked primitive is called in bypass mode (test helper).
//
// CC reference: utils/permissions/bypassPermissionsKillswitch.ts (CC 2.1.88)
// UMMAYA adaptation: stateless pure-function guard, no React hooks, no module
// singleton. Safe to call from any context (hooks, test fixtures, tool call).

import type { ToolPermissionContext } from '../../Tool.js'
import type { UmmayaPrimitive } from './aalToLayer.js'

// ---------------------------------------------------------------------------
// Primitives that MUST always go through the gauntlet (fail-closed).
// ---------------------------------------------------------------------------

/**
 * Primitives that are NEVER allowed to bypass the permission gauntlet,
 * even when `bypassPermissions` is true or the session is in auto-mode.
 *
 * Rationale (FR-012):
 *   - verify: delegates real credentials to external auth vendor (Layer 1).
 *   - submit: side-effecting, potentially irreversible (Layer 2/3).
 *   - lookup: read-only; intentionally excluded — bypass is safe here.
 */
export const BYPASS_BLOCKED_PRIMITIVES: ReadonlySet<UmmayaPrimitive> = new Set<UmmayaPrimitive>([
  'verify',
  'submit',
])

// ---------------------------------------------------------------------------
// isUmmayaBypassAllowed — fail-closed predicate
// ---------------------------------------------------------------------------

/**
 * Returns `true` if the primitive MAY proceed without the permission gauntlet
 * (i.e., in bypass / auto-mode without a human approval prompt).
 *
 * Always returns `false` for primitives in BYPASS_BLOCKED_PRIMITIVES
 * regardless of `toolPermissionContext.bypassPermissions`.
 *
 * Always returns `true` for `lookup` — it is read-only and side-effect-free.
 */
export function isUmmayaBypassAllowed(
  primitive: UmmayaPrimitive,
  _toolPermissionContext?: Pick<ToolPermissionContext, 'bypassPermissions'>,
): boolean {
  if (primitive === 'lookup') {
    // lookup: read-only, bypass is always safe.
    return true
  }
  if (BYPASS_BLOCKED_PRIMITIVES.has(primitive)) {
    // FR-012: blocked regardless of bypass flag.
    return false
  }
  // Default: honour the bypassPermissions flag.
  return _toolPermissionContext?.bypassPermissions ?? false
}

// ---------------------------------------------------------------------------
// assertUmmayaGauntletRequired — defensive check for tests / call-sites
// ---------------------------------------------------------------------------

/**
 * Throws a descriptive error if `primitive` is in BYPASS_BLOCKED_PRIMITIVES
 * and `toolPermissionContext.bypassPermissions` is true.
 *
 * Intended usage: call from `checkPermissions` implementations in each
 * primitive tool BEFORE delegating to the CC `{ behavior: 'ask' }` path.
 * In production, the CC pipeline never bypasses `{ behavior: 'ask' }` for
 * blocked primitives because UMMAYA does not wire `bypassPermissions: true`
 * for citizen sessions.  This assert is a belt-and-suspenders guard for
 * future configuration drift.
 *
 * @throws Error if bypass is attempted on a blocked primitive.
 */
export function assertUmmayaGauntletRequired(
  primitive: UmmayaPrimitive,
  toolPermissionContext?: Pick<ToolPermissionContext, 'bypassPermissions'>,
): void {
  if (
    BYPASS_BLOCKED_PRIMITIVES.has(primitive) &&
    toolPermissionContext?.bypassPermissions === true
  ) {
    throw new Error(
      `[UMMAYA FR-012] Bypass attempted on gauntlet-required primitive '${primitive}'. ` +
        `bypassPermissions must not be set for citizen-facing primitives.`,
    )
  }
}
