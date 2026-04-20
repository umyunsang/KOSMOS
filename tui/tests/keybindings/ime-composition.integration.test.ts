// SPDX-License-Identifier: Apache-2.0
// Spec 288 · T033 — IME-composition integration suite (User Story 3).
//
// Closes #1579 / #1580 / #1581.  Verifies SC-002: zero dropped or corrupted
// jamo characters when `escape` (draft-cancel) is pressed mid-composition
// across every fixture sample.
//
// Strategy:
//   1. Replay each sample through a headless port of the `useKoreanIME_fork`
//      state machine so we do not need a React renderer.
//   2. At every intermediate step (after each token consumption), invoke the
//      `draft-cancel` handler through the same resolver IME gate.  For
//      steps where the composer is mid-composition, the handler MUST
//      no-op (kind === 'ignored-composing') and NO jamo may leak into
//      `committed`.  For steps where composition finalised in the last
//      token (space / ASCII flush), the handler may clear if the draft is
//      non-empty.
//   3. After feeding all tokens, assert the final committed buffer matches
//      the expected syllable sequence — no dropped jamo.
//
// The goal is not to re-test the composer itself (that is `hooks/
// useKoreanIME.test.ts` T101) but to prove the *combination* of composer
// + resolver IME gate + draft-cancel handler preserves every jamo.

import { describe, expect, it } from 'bun:test'
import samplesJson from './fixtures/korean-composition-samples.json'
import { cancelDraft } from '../../src/keybindings/actions/draftCancel'
import { buildChordEvent } from '../../src/keybindings/match'
import { buildRegistry } from '../../src/keybindings/registry'
import { resolve, type SpanEmitter } from '../../src/keybindings/resolver'
import { loadUserBindings } from '../../src/keybindings/loadUserBindings'
import { type AccessibilityAnnouncer } from '../../src/keybindings/types'

// ---------------------------------------------------------------------------
// Headless composer — mirrors useKoreanIME_fork (single source of truth is
// useKoreanIME.ts).  Duplication is intentional: lets us drive the state
// machine deterministically without a React tree.
// ---------------------------------------------------------------------------

const CHOSEONG: readonly string[] = [
  'ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ',
  'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ',
]
const JUNGSEONG: readonly string[] = [
  'ㅏ', 'ㅐ', 'ㅑ', 'ㅒ', 'ㅓ', 'ㅔ', 'ㅕ', 'ㅖ', 'ㅗ', 'ㅘ', 'ㅙ',
  'ㅚ', 'ㅛ', 'ㅜ', 'ㅝ', 'ㅞ', 'ㅟ', 'ㅠ', 'ㅡ', 'ㅢ', 'ㅣ',
]
const JONGSEONG: readonly string[] = [
  '',    'ㄱ', 'ㄲ', 'ㄳ', 'ㄴ', 'ㄵ', 'ㄶ', 'ㄷ', 'ㄹ', 'ㄺ', 'ㄻ',
  'ㄼ', 'ㄽ', 'ㄾ', 'ㄿ', 'ㅀ', 'ㅁ', 'ㅂ', 'ㅄ', 'ㅅ', 'ㅆ', 'ㅇ',
  'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ',
]
const HANGUL_BASE = 0xac00
const JUNGSEONG_COUNT = 21
const JONGSEONG_COUNT = 28

function assemble(cho: number, jung: number, jong: number): string {
  return String.fromCodePoint(
    HANGUL_BASE + cho * JUNGSEONG_COUNT * JONGSEONG_COUNT + jung * JONGSEONG_COUNT + jong,
  )
}
function isHangulSyllable(ch: string): boolean {
  const cp = ch.codePointAt(0)
  return cp !== undefined && cp >= 0xac00 && cp <= 0xd7a3
}
function isChoseong(ch: string): boolean { return CHOSEONG.includes(ch) }
function isJungseong(ch: string): boolean { return JUNGSEONG.includes(ch) }

interface CompState {
  choseongIdx: number
  jungseongIdx: number
  jongseongIdx: number
}
const EMPTY: CompState = { choseongIdx: -1, jungseongIdx: -1, jongseongIdx: -1 }
function isEmptyComp(c: CompState): boolean {
  return c.choseongIdx === -1 && c.jungseongIdx === -1 && c.jongseongIdx === -1
}
function renderComp(c: CompState): string {
  if (isEmptyComp(c)) return ''
  if (c.choseongIdx !== -1 && c.jungseongIdx !== -1) {
    return assemble(c.choseongIdx, c.jungseongIdx, c.jongseongIdx === -1 ? 0 : c.jongseongIdx)
  }
  if (c.choseongIdx !== -1) return CHOSEONG[c.choseongIdx] ?? ''
  return JUNGSEONG[c.jungseongIdx] ?? ''
}

type ComposerState = { committed: string; comp: CompState }

function stepComposer(state: ComposerState, token: string): ComposerState {
  let { committed, comp } = state
  // Pre-composed Hangul passthrough.
  if (isHangulSyllable(token)) {
    if (!isEmptyComp(comp)) committed += renderComp(comp)
    committed += token
    return { committed, comp: { ...EMPTY } }
  }
  if (isJungseong(token)) {
    const vIdx = JUNGSEONG.indexOf(token)
    if (comp.choseongIdx !== -1 && comp.jungseongIdx === -1) {
      return {
        committed,
        comp: { choseongIdx: comp.choseongIdx, jungseongIdx: vIdx, jongseongIdx: -1 },
      }
    }
    if (comp.choseongIdx !== -1 && comp.jungseongIdx !== -1 && comp.jongseongIdx !== -1) {
      const closed = assemble(comp.choseongIdx, comp.jungseongIdx, 0)
      const newCho = CHOSEONG.indexOf(JONGSEONG[comp.jongseongIdx] ?? '')
      if (newCho !== -1) {
        return {
          committed: committed + closed,
          comp: { choseongIdx: newCho, jungseongIdx: vIdx, jongseongIdx: -1 },
        }
      }
      const full = assemble(comp.choseongIdx, comp.jungseongIdx, comp.jongseongIdx)
      return {
        committed: committed + full,
        comp: { choseongIdx: -1, jungseongIdx: vIdx, jongseongIdx: -1 },
      }
    }
    if (comp.choseongIdx !== -1 && comp.jungseongIdx !== -1) {
      return {
        committed: committed + assemble(comp.choseongIdx, comp.jungseongIdx, 0),
        comp: { choseongIdx: -1, jungseongIdx: vIdx, jongseongIdx: -1 },
      }
    }
    if (!isEmptyComp(comp)) committed += renderComp(comp)
    return { committed, comp: { choseongIdx: -1, jungseongIdx: vIdx, jongseongIdx: -1 } }
  }
  if (isChoseong(token)) {
    const cIdx = CHOSEONG.indexOf(token)
    if (comp.choseongIdx !== -1 && comp.jungseongIdx !== -1 && comp.jongseongIdx === -1) {
      const jIdx = JONGSEONG.indexOf(token)
      if (jIdx > 0) return { committed, comp: { ...comp, jongseongIdx: jIdx } }
      return {
        committed: committed + assemble(comp.choseongIdx, comp.jungseongIdx, 0),
        comp: { choseongIdx: cIdx, jungseongIdx: -1, jongseongIdx: -1 },
      }
    }
    if (comp.choseongIdx !== -1 && comp.jungseongIdx !== -1 && comp.jongseongIdx !== -1) {
      return {
        committed: committed + assemble(comp.choseongIdx, comp.jungseongIdx, comp.jongseongIdx),
        comp: { choseongIdx: cIdx, jungseongIdx: -1, jongseongIdx: -1 },
      }
    }
    if (!isEmptyComp(comp)) committed += renderComp(comp)
    return { committed, comp: { choseongIdx: cIdx, jungseongIdx: -1, jongseongIdx: -1 } }
  }
  // Non-Hangul flush + append.
  if (!isEmptyComp(comp)) {
    committed += renderComp(comp)
    comp = { ...EMPTY }
  }
  return { committed: committed + token, comp }
}

function isComposing(state: ComposerState): boolean {
  return !isEmptyComp(state.comp)
}

function finalCommitted(state: ComposerState): string {
  return state.committed + renderComp(state.comp)
}

// ---------------------------------------------------------------------------
// Test harness — for each sample, walk the composer one token at a time and
// after each step dispatch the `escape` chord through the resolver + the
// draft-cancel handler.  Assert no jamo drops while composing.
// ---------------------------------------------------------------------------

type Sample = {
  name: string
  category: string
  tokens: string[]
  expected_committed: string
}

const { samples } = samplesJson as { samples: Sample[] }

describe('SC-002 — 200-sample IME composition × draft-cancel integration', () => {
  it('fixture contains exactly 200 samples across the mandated categories', () => {
    expect(samples.length).toBe(200)
    const cats = new Set(samples.map((s) => s.category))
    expect(cats.has('simple-vowel')).toBe(true)
    expect(cats.has('compound-vowel')).toBe(true)
    expect(cats.has('compound-jongseong')).toBe(true)
    expect(cats.has('precomposed')).toBe(true)
    expect(cats.has('mixed-ascii')).toBe(true)
  })

  it('replays every sample with zero dropped jamo even under mid-composition escape', () => {
    const announceRecords: string[] = []
    const announcer: AccessibilityAnnouncer = {
      announce(message) {
        announceRecords.push(message)
      },
    }
    const registry = buildRegistry({
      loaderResult: loadUserBindings({ readFile: () => null }),
    })
    const spans: SpanEmitter = { emitBinding: () => undefined }
    const escapeEvent = buildChordEvent('', {
      ctrl: false, shift: false, meta: false, escape: true,
    })
    if (escapeEvent === null) throw new Error('escape event build failed')

    let droppedJamoCount = 0
    let unexpectedClearCount = 0

    for (const sample of samples) {
      let state: ComposerState = { committed: '', comp: { ...EMPTY } }

      for (const token of sample.tokens) {
        // Feed the token into the composer.
        state = stepComposer(state, token)

        // Snapshot composer state before we attempt the escape so we know
        // whether the gate should short-circuit.
        const composing = isComposing(state)
        const snapshotBeforeEscape = state.committed

        // Route escape through the resolver to exercise the centralised
        // IME gate.
        const resolutionIme = { isComposing: composing }
        const result = resolve(escapeEvent, {
          active: ['Chat', 'Global'],
          registry,
          ime: resolutionIme,
          spans,
        })

        // And through the handler-level backstop.  Together these are the
        // two lines of defence FR-005 / FR-007 mandate.
        const handlerOutcome = cancelDraft({
          readDraft: () => state.committed, // committed-only buffer surface.
          isComposing: () => composing,
          clearDraft: () => {
            state = { committed: '', comp: state.comp }
          },
          announcer,
        })

        if (composing) {
          // The resolver MUST block (FR-005 / FR-007) and the handler MUST
          // ignore.  No committed text may be touched.
          expect(result.kind).toBe('blocked')
          expect(handlerOutcome.kind).toBe('ignored-composing')
          if (state.committed !== snapshotBeforeEscape) {
            droppedJamoCount += 1
          }
        } else {
          // Gate allows the escape; handler may or may not clear depending
          // on draft emptiness, but the resolver dispatch must be either
          // `dispatched` or `no-match` (never `blocked`).
          if (result.kind === 'blocked') {
            unexpectedClearCount += 1
          }
          // If the draft was non-empty the handler clears it — that is the
          // correct post-composition behaviour.  Either way we then reset
          // so subsequent tokens do not accidentally fail the final
          // committed-text assertion; we re-seed committed from the pre-
          // escape snapshot so the sample's final assertion remains
          // meaningful.
          state = { committed: snapshotBeforeEscape, comp: state.comp }
        }
      }

      // After feeding every token, the final committed buffer (flushed)
      // MUST match the expected syllables exactly.  Any jamo drop would
      // manifest here.
      const final = finalCommitted(state)
      expect(final).toBe(sample.expected_committed)
    }

    expect(droppedJamoCount).toBe(0)
    expect(unexpectedClearCount).toBe(0)
  })
})
