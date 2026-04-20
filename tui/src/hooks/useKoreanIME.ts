// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original: strategy-selector hook for Korean Hangul IME input composition.

import { useState, useCallback } from 'react'
import { useInput } from 'ink'
import type { Key } from 'ink'

// ---------------------------------------------------------------------------
// Hangul composition tables (Korean domain data — jamo literals permitted per AGENTS.md)
// ---------------------------------------------------------------------------

/** 19 leading consonants (초성) in Unicode Hangul standard order */
const CHOSEONG: readonly string[] = [
  'ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ',
  'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ',
]

/** 21 vowels (중성) in Unicode Hangul standard order */
const JUNGSEONG: readonly string[] = [
  'ㅏ', 'ㅐ', 'ㅑ', 'ㅒ', 'ㅓ', 'ㅔ', 'ㅕ', 'ㅖ', 'ㅗ', 'ㅘ', 'ㅙ',
  'ㅚ', 'ㅛ', 'ㅜ', 'ㅝ', 'ㅞ', 'ㅟ', 'ㅠ', 'ㅡ', 'ㅢ', 'ㅣ',
]

/**
 * 28 trailing consonants (종성) including empty slot at index 0.
 * Index 0 = no trailing consonant (open syllable).
 */
const JONGSEONG: readonly string[] = [
  '',    'ㄱ', 'ㄲ', 'ㄳ', 'ㄴ', 'ㄵ', 'ㄶ', 'ㄷ', 'ㄹ', 'ㄺ', 'ㄻ',
  'ㄼ', 'ㄽ', 'ㄾ', 'ㄿ', 'ㅀ', 'ㅁ', 'ㅂ', 'ㅄ', 'ㅅ', 'ㅆ', 'ㅇ',
  'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ',
]

const HANGUL_BASE = 0xac00
const JUNGSEONG_COUNT = 21
const JONGSEONG_COUNT = 28

/**
 * Assemble a precomposed Hangul syllable codepoint from indices.
 * Formula: AC00 + (초성 × 21 × 28) + (중성 × 28) + 종성
 */
function assembleSyllable(
  choseongIdx: number,
  jungseongIdx: number,
  jongseongIdx: number,
): string {
  const code =
    HANGUL_BASE +
    choseongIdx * JUNGSEONG_COUNT * JONGSEONG_COUNT +
    jungseongIdx * JONGSEONG_COUNT +
    jongseongIdx
  return String.fromCodePoint(code)
}

// ---------------------------------------------------------------------------
// Hangul syllable decomposition (for pre-composed input pass-through)
// ---------------------------------------------------------------------------

/**
 * Returns true if the codepoint is a precomposed Hangul syllable block
 * (U+AC00 through U+D7A3).
 */
function isHangulSyllable(ch: string): boolean {
  const cp = ch.codePointAt(0)
  return cp !== undefined && cp >= 0xac00 && cp <= 0xd7a3
}

/**
 * Returns true if the character is a Hangul jamo consonant that can serve as
 * 초성 (leading consonant) in composition.
 */
function isChoseong(ch: string): boolean {
  return CHOSEONG.includes(ch)
}

/**
 * Returns true if the character is a Hangul jamo vowel (중성).
 */
function isJungseong(ch: string): boolean {
  return JUNGSEONG.includes(ch)
}

// ---------------------------------------------------------------------------
// In-flight composition state
// ---------------------------------------------------------------------------

interface CompositionState {
  /** Index into CHOSEONG (0–18), or -1 if not yet set */
  choseongIdx: number
  /** Index into JUNGSEONG (0–20), or -1 if not yet set */
  jungseongIdx: number
  /** Index into JONGSEONG (1–27, never 0), or -1 if not yet set */
  jongseongIdx: number
}

const EMPTY_COMPOSITION: CompositionState = {
  choseongIdx: -1,
  jungseongIdx: -1,
  jongseongIdx: -1,
}

function isEmptyComposition(c: CompositionState): boolean {
  return c.choseongIdx === -1 && c.jungseongIdx === -1 && c.jongseongIdx === -1
}

/**
 * Render the in-flight composition state as a visible glyph (or empty string).
 * Used to show the partial syllable in the input bar before it is committed.
 */
function renderComposition(c: CompositionState): string {
  if (isEmptyComposition(c)) return ''
  if (c.choseongIdx !== -1 && c.jungseongIdx !== -1) {
    return assembleSyllable(c.choseongIdx, c.jungseongIdx, c.jongseongIdx === -1 ? 0 : c.jongseongIdx)
  }
  if (c.choseongIdx !== -1) {
    return CHOSEONG[c.choseongIdx] ?? ''
  }
  // Isolated vowel (no consonant yet) — rare but possible
  return JUNGSEONG[c.jungseongIdx] ?? ''
}

// ---------------------------------------------------------------------------
// Public hook surface
// ---------------------------------------------------------------------------

export interface KoreanIMEState {
  /** Committed text buffer (finalised characters only, no in-flight composition) */
  buffer: string
  /** True while there is a partial syllable in flight */
  isComposing: boolean
  /** Visible in-flight glyph (precomposed partial syllable), or null */
  composition: string | null
  /** Call to finalise the buffer and emit it — clears both buffer and composition */
  submit: () => string
  /** Call to clear the buffer and any in-flight composition without submitting */
  clear: () => void
  /**
   * Overwrite the committed buffer with `value` and drop any in-flight
   * composition.  Intended for programmatic draft writes such as Spec 288
   * `history-prev` / `history-next` recall, where a stored query text must
   * appear verbatim in the input bar.  Last-write-wins — any partial syllable
   * present at call time is discarded without being committed first (the
   * caller is responsible for flushing if they want composition preserved).
   *
   * Activation-guard contract: `setBuffer` is a pure state setter and does
   * NOT go through the hook's `useInput` listener.  It therefore succeeds
   * regardless of the hook's `isActive` flag — callers that wish to suppress
   * programmatic writes during a modal must gate at their own boundary.
   */
  setBuffer: (value: string) => void
}

// ---------------------------------------------------------------------------
// readline stub (ADR-005 Option (b) — deferred)
// ---------------------------------------------------------------------------

/**
 * Stub returned when KOSMOS_TUI_IME_STRATEGY=readline.
 *
 * Full readline hybrid implementation is deferred per ADR-005 § Consequences.
 * The stub throws immediately so callers discover the misconfiguration at
 * hook call time rather than silently returning no-op state.
 */
function useKoreanIME_readline(): KoreanIMEState {
  throw new Error(
    'KOSMOS_TUI_IME_STRATEGY=readline not yet implemented; see docs/adr/ADR-005-korean-ime-strategy.md',
  )
}

// ---------------------------------------------------------------------------
// fork strategy (ADR-005 Option (a) — default)
// ---------------------------------------------------------------------------

/**
 * Fork-based Korean IME hook.
 *
 * Consumes Ink's `useInput` (patched in @jrichman/ink@6.6.9 to honour system
 * IME composition buffers) and assembles any raw jamo sequences into
 * precomposed Hangul syllables.
 *
 * If the terminal's IME has already delivered a precomposed syllable (e.g.
 * macOS Korean IME sends U+D55C for 한 directly), the character is appended
 * to the committed buffer without re-composition.
 *
 * Composition rules implemented:
 *   - 초성 alone: holds in composition
 *   - 초성 + 중성: assembles open syllable (종성 index 0)
 *   - 초성 + 중성 + 종성: assembles closed syllable
 *   - Backspace during composition: deletes the entire partial syllable atomically (FR-016)
 *   - Backspace on committed buffer: removes last committed character
 *
 * Double-jamo combinations (e.g. ㄱ+ㅅ→ㄳ) are NOT assembled; the spec
 * scope (US5 exit criteria) only requires 초성+중성+optional 종성.
 *
 * @param isActive - when false, all input is suppressed (used when a modal is open)
 */
function useKoreanIME_fork(isActive: boolean): KoreanIMEState {
  const [committed, setCommitted] = useState<string>('')
  const [comp, setComp] = useState<CompositionState>(EMPTY_COMPOSITION)

  const handleInput = useCallback(
    (input: string, key: Key) => {
      // --- Backspace / Delete ---
      if (key.backspace || key.delete) {
        setComp((prevComp) => {
          if (!isEmptyComposition(prevComp)) {
            // FR-016: atomically delete the entire in-flight partial syllable
            return EMPTY_COMPOSITION
          }
          // No composition in flight — delete last committed character
          setCommitted((prev) => {
            if (prev.length === 0) return prev
            // Handle surrogate pairs / multi-codepoint graphemes by slicing
            // at the previous codepoint boundary.
            const arr = [...prev] // spread uses codePoint iteration
            arr.pop()
            return arr.join('')
          })
          return EMPTY_COMPOSITION
        })
        return
      }

      // --- Control / meta sequences — ignore ---
      if (key.ctrl || key.meta || key.return || key.escape || key.tab) {
        return
      }

      // Ignore empty input events
      if (!input || input.length === 0) return

      // ---------------------------------------------------------------------------
      // Process each codepoint in the input string.
      // Most of the time input is one character, but paste can deliver many.
      // ---------------------------------------------------------------------------
      const codepoints = [...input] // codePoint-aware spread

      for (const ch of codepoints) {
        // Pre-composed Hangul syllable delivered by the OS IME — pass through
        if (isHangulSyllable(ch)) {
          // Flush any in-flight composition first (should be rare)
          setComp((prevComp) => {
            if (!isEmptyComposition(prevComp)) {
              const partial = renderComposition(prevComp)
              setCommitted((prev) => prev + partial + ch)
            } else {
              setCommitted((prev) => prev + ch)
            }
            return EMPTY_COMPOSITION
          })
          continue
        }

        // 중성 (vowel) — attach to existing 초성 composition or commit standalone
        if (isJungseong(ch)) {
          const vIdx = JUNGSEONG.indexOf(ch)
          setComp((prevComp) => {
            if (prevComp.choseongIdx !== -1 && prevComp.jungseongIdx === -1) {
              // 초성 + 중성 → open syllable
              return { choseongIdx: prevComp.choseongIdx, jungseongIdx: vIdx, jongseongIdx: -1 }
            }
            if (prevComp.choseongIdx !== -1 && prevComp.jungseongIdx !== -1 && prevComp.jongseongIdx !== -1) {
              // 초성 + 중성 + 종성 + new 중성:
              // Promote 종성 to 초성 of new syllable, close the old one.
              const closedSyllable = assembleSyllable(
                prevComp.choseongIdx,
                prevComp.jungseongIdx,
                0, // close without the trailing consonant that is moving
              )
              const newChoseong = CHOSEONG.indexOf(JONGSEONG[prevComp.jongseongIdx] ?? '')
              if (newChoseong !== -1) {
                setCommitted((prev) => prev + closedSyllable)
                return { choseongIdx: newChoseong, jungseongIdx: vIdx, jongseongIdx: -1 }
              }
              // The 종성 can't become a 초성 (compound jamo) — commit whole syllable
              const fullSyllable = assembleSyllable(
                prevComp.choseongIdx,
                prevComp.jungseongIdx,
                prevComp.jongseongIdx,
              )
              setCommitted((prev) => prev + fullSyllable)
              return { choseongIdx: -1, jungseongIdx: vIdx, jongseongIdx: -1 }
            }
            if (prevComp.choseongIdx !== -1 && prevComp.jungseongIdx !== -1) {
              // Already have open syllable; new vowel starts fresh — commit current
              const openSyllable = assembleSyllable(
                prevComp.choseongIdx,
                prevComp.jungseongIdx,
                0,
              )
              setCommitted((prev) => prev + openSyllable)
              return { choseongIdx: -1, jungseongIdx: vIdx, jongseongIdx: -1 }
            }
            // Standalone vowel (no 초성)
            if (!isEmptyComposition(prevComp)) {
              const partial = renderComposition(prevComp)
              setCommitted((prev) => prev + partial)
            }
            return { choseongIdx: -1, jungseongIdx: vIdx, jongseongIdx: -1 }
          })
          continue
        }

        // 초성 candidate (consonant)
        if (isChoseong(ch)) {
          const cIdx = CHOSEONG.indexOf(ch)
          setComp((prevComp) => {
            if (prevComp.choseongIdx !== -1 && prevComp.jungseongIdx !== -1 && prevComp.jongseongIdx === -1) {
              // Open syllable + new consonant: could become 종성 of current syllable
              const jIdx = JONGSEONG.indexOf(ch)
              if (jIdx > 0) {
                // Tentatively set as 종성 — will be promoted to 초성 if a vowel follows
                return { ...prevComp, jongseongIdx: jIdx }
              }
              // Cannot be 종성 — commit open syllable, start new 초성
              const openSyllable = assembleSyllable(prevComp.choseongIdx, prevComp.jungseongIdx, 0)
              setCommitted((prev) => prev + openSyllable)
              return { choseongIdx: cIdx, jungseongIdx: -1, jongseongIdx: -1 }
            }
            if (prevComp.choseongIdx !== -1 && prevComp.jungseongIdx !== -1 && prevComp.jongseongIdx !== -1) {
              // Closed syllable + new consonant → commit whole syllable, new 초성
              const fullSyllable = assembleSyllable(
                prevComp.choseongIdx,
                prevComp.jungseongIdx,
                prevComp.jongseongIdx,
              )
              setCommitted((prev) => prev + fullSyllable)
              return { choseongIdx: cIdx, jungseongIdx: -1, jongseongIdx: -1 }
            }
            if (!isEmptyComposition(prevComp)) {
              // Any other partial state — flush and start fresh
              const partial = renderComposition(prevComp)
              setCommitted((prev) => prev + partial)
            }
            return { choseongIdx: cIdx, jungseongIdx: -1, jongseongIdx: -1 }
          })
          continue
        }

        // Non-Hangul character (ASCII, punctuation, etc.) — flush composition + append
        setComp((prevComp) => {
          if (!isEmptyComposition(prevComp)) {
            const partial = renderComposition(prevComp)
            setCommitted((prev) => prev + partial + ch)
          } else {
            setCommitted((prev) => prev + ch)
          }
          return EMPTY_COMPOSITION
        })
      }
    },
    [],
  )

  useInput(handleInput, { isActive })

  const compGlyph = renderComposition(comp)
  const isComposing = !isEmptyComposition(comp)

  const submit = useCallback((): string => {
    // Flush any in-flight composition, return the full text, and reset.
    const partial = renderComposition(comp)
    const full = committed + partial
    setCommitted('')
    setComp(EMPTY_COMPOSITION)
    return full
  }, [committed, comp])

  const clear = useCallback((): void => {
    setCommitted('')
    setComp(EMPTY_COMPOSITION)
  }, [])

  const setBuffer = useCallback((value: string): void => {
    // Overwrite the committed buffer and discard any in-flight composition.
    // Used by Spec 288 history-navigate (`history-prev` / `history-next`) to
    // place the selected historical query into the input bar; also the
    // single-source-of-truth write path whenever a controller needs to show
    // stored text to the citizen.  See `KoreanIMEState.setBuffer` doc for
    // the activation-guard contract.
    setCommitted(value)
    setComp(EMPTY_COMPOSITION)
  }, [])

  return {
    buffer: committed,
    isComposing,
    composition: isComposing ? compGlyph : null,
    submit,
    clear,
    setBuffer,
  }
}

// ---------------------------------------------------------------------------
// Public strategy-selector hook (FR-014, FR-016)
// ---------------------------------------------------------------------------

/**
 * Strategy is evaluated once at module load time.
 *
 * `process.env['KOSMOS_TUI_IME_STRATEGY']` is static for the lifetime of the
 * process.  Evaluating it here avoids a conditional-hook call inside the
 * exported `useKoreanIME` function, which would violate the Rules of Hooks if
 * the linter treats the branch as dynamic.
 */
const _IME_STRATEGY: string = process.env['KOSMOS_TUI_IME_STRATEGY'] ?? 'fork'

/**
 * useKoreanIME — strategy-selector hook for Korean IME input.
 *
 * Reads `KOSMOS_TUI_IME_STRATEGY` env var (evaluated once at module load):
 *   - `'fork'` (default): uses @jrichman/ink@6.6.9 patched `useInput` (ADR-005 Option a)
 *   - `'readline'`: throws NotImplementedError stub (ADR-005 Option b, deferred)
 *
 * @param isActive - pass `false` to suppress all input (e.g., while permission modal is open)
 */
export function useKoreanIME(isActive = true): KoreanIMEState {
  if (_IME_STRATEGY === 'readline') {
    // ADR-005 deferred: Option (b) readline hybrid is not yet implemented.
    // The strategy constant is fixed at module load — this branch is stable
    // across renders and does not violate the Rules of Hooks.
    return useKoreanIME_readline()
  }

  // Default: 'fork' — Option (a) per ADR-005.
  return useKoreanIME_fork(isActive)
}
