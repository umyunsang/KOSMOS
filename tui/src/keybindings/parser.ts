// SPDX-License-Identifier: Apache-2.0
// Source: .references/claude-code-sourcemap/restored-src/src/keybindings/parser.ts (CC 2.1.88, research-use)
// Spec 288 · T004 — chord parser + canonicaliser.
//
// KOSMOS narrows CC's Chord[] (multi-keystroke chord array) to a single
// canonicalised `ChordString` brand, because Tier 1 has no multi-step chords.
// The full grammar (EBNF) lives in `data-model.md § ChordString`.
//
// Re-exports `parseChord` / `tryParseChord` from `./chord` (Team C landed
// the implementation first — this module is the tasks.md-referenced entry).

export { parseChord, tryParseChord } from './chord'
