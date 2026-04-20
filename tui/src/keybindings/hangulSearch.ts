// SPDX-License-Identifier: Apache-2.0
// Spec 288 · 초성 (initial-consonant) matcher for the history-search overlay.
//
// Rationale (research D9 + T037 constraint):
//   - Reuses the Hangul jamo decomposition constants already present in
//     `tui/src/hooks/useKoreanIME.ts` (Korean domain data — jamo literals
//     permitted per AGENTS.md).
//   - Implements pure-stdlib substring + diacritic-insensitive + 초성
//     matching. Zero new runtime dependencies (SC-008).
//   - Spec 022's BM25 + kiwipiepy tokeniser is Python-side; the TUI
//     cannot consume it across the IPC boundary cheaply for an interactive
//     overlay (FR-020 ≤ 300 ms). Instead we reuse the algorithmic shape
//     (lowercase + jamo-decompose + substring-AND) of that tokeniser
//     here in TS — no dependency added, deferred tuning lives in #1311.

// ---------------------------------------------------------------------------
// Hangul tables (Korean domain data — Unicode standard order)
// ---------------------------------------------------------------------------

const CHOSEONG: readonly string[] = [
  'ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ',
  'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ',
]
const CHOSEONG_SET: ReadonlySet<string> = new Set(CHOSEONG)
const HANGUL_BASE = 0xac00
const HANGUL_LAST = 0xd7a3
const JUNGSEONG_COUNT = 21
const JONGSEONG_COUNT = 28

function isHangulSyllable(cp: number): boolean {
  return cp >= HANGUL_BASE && cp <= HANGUL_LAST
}

function isChoseong(ch: string): boolean {
  return CHOSEONG_SET.has(ch)
}

/**
 * Extract the 초성 (leading consonant) of a precomposed Hangul syllable.
 * For non-Hangul characters returns the character lowercased — the matcher
 * treats those as exact-substring contributors.
 */
export function extractChoseong(ch: string): string {
  const cp = ch.codePointAt(0)
  if (cp === undefined) return ''
  if (!isHangulSyllable(cp)) return ch.toLowerCase()
  const syllableIndex = cp - HANGUL_BASE
  const choseongIdx = Math.floor(
    syllableIndex / (JUNGSEONG_COUNT * JONGSEONG_COUNT),
  )
  return CHOSEONG[choseongIdx] ?? ch
}

/**
 * Decompose a string into its 초성 sequence — every Hangul syllable
 * becomes its leading consonant; every non-Hangul character is preserved
 * lowercased. Used to build both the haystack key and the needle.
 */
export function toChoseongString(s: string): string {
  let out = ''
  for (const ch of Array.from(s)) {
    out += extractChoseong(ch)
  }
  return out
}

/**
 * Returns true when every character of `needle` is itself a Hangul jamo
 * 초성. This is the citizen's signal that they are typing a 초성-only
 * search ("ㅂㅅ" → "부산"), and lets the matcher switch from substring
 * mode to 초성 mode.
 */
function isAllChoseong(needle: string): boolean {
  if (needle.length === 0) return false
  for (const ch of Array.from(needle)) {
    if (!isChoseong(ch)) return false
  }
  return true
}

// ---------------------------------------------------------------------------
// Diacritic stripping — covers Latin combining marks; Hangul has no
// combining diacritics in the BMP block we operate on, so NFD + filter
// of the U+0300..U+036F combining range is sufficient.
// ---------------------------------------------------------------------------

function stripDiacritics(s: string): string {
  return s.normalize('NFD').replace(/[\u0300-\u036f]/g, '')
}

function normaliseHaystack(s: string): string {
  return stripDiacritics(s).toLowerCase()
}

/**
 * Returns true if `haystack` matches `needle` under the Spec 288 § FR-020
 * matching rules:
 *   - Substring match on the diacritic-stripped lowercase haystack.
 *   - When `needle` is composed entirely of 초성 jamo, the match is also
 *     attempted against the 초성 decomposition of the haystack.
 * The match is OR-composed — any of the strategies hitting wins.
 */
export function matchesHistoryQuery(
  haystack: string,
  needle: string,
): boolean {
  if (needle.length === 0) return true
  const norm = normaliseHaystack(haystack)
  const n = stripDiacritics(needle).toLowerCase()
  if (norm.includes(n)) return true
  if (isAllChoseong(needle)) {
    const cho = toChoseongString(haystack)
    if (cho.includes(needle)) return true
  }
  return false
}

/**
 * Filter a list of citizen queries against `needle`, preserving order.
 * Pure function — no side effects; safe for use inside a React render
 * (memoise at the call site to keep the overlay under FR-020's 300 ms).
 */
export function filterHistoryEntries<T extends { query_text: string }>(
  entries: ReadonlyArray<T>,
  needle: string,
): ReadonlyArray<T> {
  if (needle.length === 0) return entries
  const out: T[] = []
  for (const e of entries) {
    if (matchesHistoryQuery(e.query_text, needle)) out.push(e)
  }
  return out
}
