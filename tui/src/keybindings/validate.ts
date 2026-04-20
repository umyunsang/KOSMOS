// SPDX-License-Identifier: Apache-2.0
// Source: .references/claude-code-sourcemap/restored-src/src/keybindings/validate.ts (CC 2.1.88, research-use)
// Spec 288 · T011 — registry-build-time invariants (data-model.md § 3).
//
// Enforces four invariants that MUST hold over every `KeybindingEntry` the
// registry accepts:
//
//   I1. reserved === true  ⟹  remappable === false
//   I2. reserved === true  ⟹  effective_chord === default_chord  (FR-028)
//   I3. default_chord parses under the chord grammar (i.e., `tryParseChord`
//       round-trips to the same canonical string)
//   I4. No non-reserved entry's effective_chord collides with a reserved
//       entry's slot in the registry's chord map (Codex P1, PR #1591).
//       Enforced at registry-assembly time in `buildRegistry`, not here —
//       `assertI4` is exposed below for registry use.
//
// Violations throw — they cannot reach runtime. The registry assembler (T012)
// wraps `validateEntries` around every merge so user-override damage cannot
// silently corrupt the default set. I4 is the defense-in-depth backstop
// behind the loader-layer `reserved-chord-collision` rejection (per the
// Spec 025 V6 two-layer pattern).

import { tryParseChord } from './parser'
import { type KeybindingEntry } from './types'

export class RegistryInvariantError extends Error {
  readonly invariant: 'I1' | 'I2' | 'I3' | 'I4'
  readonly entry: KeybindingEntry

  constructor(
    invariant: 'I1' | 'I2' | 'I3' | 'I4',
    entry: KeybindingEntry,
    message: string,
  ) {
    super(`registry invariant ${invariant} violated: ${message}`)
    this.name = 'RegistryInvariantError'
    this.invariant = invariant
    this.entry = entry
  }
}

function assertI1(entry: KeybindingEntry): void {
  if (entry.reserved && entry.remappable) {
    throw new RegistryInvariantError(
      'I1',
      entry,
      `reserved action ${entry.action} cannot be remappable`,
    )
  }
}

function assertI2(entry: KeybindingEntry): void {
  if (
    entry.reserved &&
    entry.effective_chord !== entry.default_chord
  ) {
    throw new RegistryInvariantError(
      'I2',
      entry,
      `reserved action ${entry.action} effective_chord diverges from default`,
    )
  }
}

function assertI3(entry: KeybindingEntry): void {
  const round = tryParseChord(entry.default_chord)
  if (round === null || round !== entry.default_chord) {
    throw new RegistryInvariantError(
      'I3',
      entry,
      `default_chord ${entry.default_chord} does not round-trip the chord grammar`,
    )
  }
}

/**
 * Validate a registry-candidate set. Throws `RegistryInvariantError` on the
 * first violation encountered; callers can attach the error's `invariant`
 * tag to telemetry.
 */
export function validateEntries(
  entries: Iterable<KeybindingEntry>,
): void {
  for (const e of entries) {
    assertI1(e)
    assertI2(e)
    assertI3(e)
  }
}
