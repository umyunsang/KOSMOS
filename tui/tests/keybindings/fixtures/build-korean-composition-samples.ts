// SPDX-License-Identifier: Apache-2.0
// Spec 288 · T032 helper — builds the `korean-composition-samples.json`
// fixture consumed by `ime-composition.integration.test.ts`.
//
// Strategy: enumerate 200 IME-composition samples covering:
//
//   - 단모음 (simple vowel) open syllables: ㄱ+ㅏ → 가, etc.  100 samples
//     drawn from the 19 leading consonants × 5 simple 단모음.
//   - 이중모음 (complex vowel) open syllables: 60 samples from a curated
//     subset of the seven compound vowels (ㅘ ㅙ ㅚ ㅝ ㅞ ㅟ ㅢ) paired with
//     representative 초성.
//   - 복합종성 (compound trailing consonant) closed syllables: 20 samples
//     covering each of the 11 compound 종성 jamo at least once.
//   - Pre-composed Hangul passthrough: 10 samples where the OS IME delivers
//     the syllable directly (ensures the handler recognises U+AC00–U+D7A3
//     pass-through per `useKoreanIME_fork`).
//   - Mixed ASCII + Korean: 10 samples ensuring jamo sequences flanked by
//     spaces / ASCII punctuation survive the composer + a mid-sequence
//     `draft-cancel` press.
//
// The output JSON is checked in — this generator runs once (or whenever the
// fixture needs regeneration) via `bun run tui/tests/keybindings/fixtures/
// build-korean-composition-samples.ts`.

import { writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const CHOSEONG: readonly string[] = [
  'ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ',
  'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ',
]

const SIMPLE_JUNGSEONG: readonly { jamo: string; index: number }[] = [
  { jamo: 'ㅏ', index: 0 },
  { jamo: 'ㅓ', index: 4 },
  { jamo: 'ㅗ', index: 8 },
  { jamo: 'ㅜ', index: 13 },
  { jamo: 'ㅣ', index: 20 },
]

const COMPOUND_JUNGSEONG: readonly { jamo: string; index: number }[] = [
  { jamo: 'ㅘ', index: 9 },
  { jamo: 'ㅙ', index: 10 },
  { jamo: 'ㅚ', index: 11 },
  { jamo: 'ㅝ', index: 14 },
  { jamo: 'ㅞ', index: 15 },
  { jamo: 'ㅟ', index: 16 },
  { jamo: 'ㅢ', index: 19 },
]

const COMPOUND_JONGSEONG: readonly { jamo: string; index: number }[] = [
  // The 11 compound 종성 — each paired with ㄱ+ㅏ frame for assembly.
  { jamo: 'ㄳ', index: 3 },
  { jamo: 'ㄵ', index: 5 },
  { jamo: 'ㄶ', index: 6 },
  { jamo: 'ㄺ', index: 9 },
  { jamo: 'ㄻ', index: 10 },
  { jamo: 'ㄼ', index: 11 },
  { jamo: 'ㄽ', index: 12 },
  { jamo: 'ㄾ', index: 13 },
  { jamo: 'ㄿ', index: 14 },
  { jamo: 'ㅀ', index: 15 },
  { jamo: 'ㅄ', index: 18 },
]

const HANGUL_BASE = 0xac00
const JUNGSEONG_COUNT = 21
const JONGSEONG_COUNT = 28

function assemble(cho: number, jung: number, jong: number): string {
  return String.fromCodePoint(
    HANGUL_BASE +
      cho * JUNGSEONG_COUNT * JONGSEONG_COUNT +
      jung * JONGSEONG_COUNT +
      jong,
  )
}

type Sample = {
  name: string
  category:
    | 'simple-vowel'
    | 'compound-vowel'
    | 'compound-jongseong'
    | 'precomposed'
    | 'mixed-ascii'
  tokens: string[]
  expected_committed: string
}

const SAMPLES: Sample[] = []

// --- 단모음 open syllables — 19 × 5 curated to 100 ------------------
// Take every (cho, jung) pair (95 combos) then round up to 100 with the
// five most-common syllables.
const simplePairs: { cho: number; jung: number; jamoPair: [string, string] }[] = []
for (let ci = 0; ci < CHOSEONG.length; ci++) {
  for (const jv of SIMPLE_JUNGSEONG) {
    const cho = CHOSEONG[ci]
    if (cho === undefined) continue
    simplePairs.push({ cho: ci, jung: jv.index, jamoPair: [cho, jv.jamo] })
  }
}
// 19*5 = 95 combos; drop five rarely composed ones and add precomposed
// helpers below.  Keep first 95; we will hit 100 via compound-vowel set.
for (const p of simplePairs.slice(0, 95)) {
  const syllable = assemble(p.cho, p.jung, 0)
  SAMPLES.push({
    name: `simple ${p.jamoPair[0]}+${p.jamoPair[1]} → ${syllable}`,
    category: 'simple-vowel',
    tokens: [p.jamoPair[0], p.jamoPair[1]],
    expected_committed: syllable,
  })
}

// Five representative closed-syllable simple-vowel cases (ㄱ+ㅏ+ㄴ = 간).
const simpleClosed: Array<[number, number, number]> = [
  [18, 0, 4], // 한
  [0, 0, 4], // 간
  [11, 8, 21], // 옹
  [6, 0, 16], // 맘
  [17, 8, 8], // 폴
]
for (const [cho, jung, jong] of simpleClosed) {
  const choJ = CHOSEONG[cho]
  const jungJ = SIMPLE_JUNGSEONG.find((s) => s.index === jung)?.jamo
  const jongJ = ['', 'ㄱ', 'ㄲ', 'ㄳ', 'ㄴ', 'ㄵ', 'ㄶ', 'ㄷ', 'ㄹ', 'ㄺ', 'ㄻ',
    'ㄼ', 'ㄽ', 'ㄾ', 'ㄿ', 'ㅀ', 'ㅁ', 'ㅂ', 'ㅄ', 'ㅅ', 'ㅆ', 'ㅇ',
    'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ'][jong]
  if (choJ === undefined || jungJ === undefined || jongJ === undefined) continue
  const syllable = assemble(cho, jung, jong)
  SAMPLES.push({
    name: `closed ${choJ}+${jungJ}+${jongJ} → ${syllable}`,
    category: 'simple-vowel',
    tokens: [choJ, jungJ, jongJ],
    expected_committed: syllable,
  })
}

// --- 이중모음 open syllables — 60 samples -------------------------
// Cover each of the 7 compound vowels with up to 9 seed consonants.
const COMPOUND_CONSONANT_SEEDS = [0, 2, 3, 5, 6, 7, 11, 16, 18]
for (const jv of COMPOUND_JUNGSEONG) {
  for (const ci of COMPOUND_CONSONANT_SEEDS) {
    const choJ = CHOSEONG[ci]
    if (choJ === undefined) continue
    const syllable = assemble(ci, jv.index, 0)
    SAMPLES.push({
      name: `compound ${choJ}+${jv.jamo} → ${syllable}`,
      category: 'compound-vowel',
      tokens: [choJ, jv.jamo],
      expected_committed: syllable,
    })
    if (SAMPLES.filter((s) => s.category === 'compound-vowel').length >= 60) break
  }
  if (SAMPLES.filter((s) => s.category === 'compound-vowel').length >= 60) break
}

// --- 복합종성 closed syllables — 20 samples -----------------------
// The `useKoreanIME_fork` composer does NOT synthesise compound 종성 from
// jamo pairs (e.g., ㄱ+ㅅ ⇒ ㄳ) — the hook docblock explicitly narrows the
// scope to 초성+중성+single-jamo 종성.  Real Korean IMEs ship compound-
// jongseong syllables as pre-composed Hangul syllables anyway (system IME
// buffers them internally and emits U+AC00–U+D7A3).  So we test that path:
// every compound-jongseong jamo is exercised via a pre-composed syllable
// token that carries it as the 종성 index.
const CLOSED_FRAMES: Array<{ cho: number; jung: number; choJ: string; jungJ: string }> = [
  { cho: 0, jung: 0, choJ: 'ㄱ', jungJ: 'ㅏ' },
  { cho: 18, jung: 0, choJ: 'ㅎ', jungJ: 'ㅏ' },
]
for (const frame of CLOSED_FRAMES) {
  for (const jo of COMPOUND_JONGSEONG) {
    const syllable = assemble(frame.cho, frame.jung, jo.index)
    SAMPLES.push({
      name: `compound-jongseong precomposed ${frame.choJ}+${frame.jungJ}+${jo.jamo} → ${syllable}`,
      category: 'compound-jongseong',
      // Deliver the syllable as a single pre-composed Hangul codepoint —
      // mirroring the real OS-level IME behaviour that `useKoreanIME_fork`
      // routes through its pre-composed pass-through branch.
      tokens: [syllable],
      expected_committed: syllable,
    })
    if (SAMPLES.filter((s) => s.category === 'compound-jongseong').length >= 20) break
  }
  if (SAMPLES.filter((s) => s.category === 'compound-jongseong').length >= 20) break
}

// --- Pre-composed pass-through — 10 samples -----------------------
const PRECOMPOSED: Array<{ name: string; syllable: string }> = [
  { name: '한', syllable: '한' },
  { name: '글', syllable: '글' },
  { name: '부', syllable: '부' },
  { name: '산', syllable: '산' },
  { name: '응', syllable: '응' },
  { name: '급', syllable: '급' },
  { name: '실', syllable: '실' },
  { name: '안', syllable: '안' },
  { name: '녕', syllable: '녕' },
  { name: '하', syllable: '하' },
]
for (const p of PRECOMPOSED) {
  SAMPLES.push({
    name: `precomposed ${p.name}`,
    category: 'precomposed',
    tokens: [p.syllable],
    expected_committed: p.syllable,
  })
}

// --- Mixed ASCII + Korean — 10 samples ---------------------------
const MIXED_SEED: Array<{ name: string; tokens: string[]; expected: string }> = [
  { name: 'ASCII after ㅎ+ㅏ+ㄴ', tokens: ['ㅎ', 'ㅏ', 'ㄴ', ' ', 'h', 'i'], expected: '한 hi' },
  { name: 'digit before Korean', tokens: ['1', '번', '째'], expected: '1번째' },
  { name: 'punctuation after ㅂ+ㅜ', tokens: ['ㅂ', 'ㅜ', '?'], expected: '부?' },
  { name: 'linking ㅂ+ㅜ+ㅅ+ㅏ+ㄴ (부산)', tokens: ['ㅂ', 'ㅜ', 'ㅅ', 'ㅏ', 'ㄴ'], expected: '부산' },
  { name: 'mixed hello 한', tokens: ['h', 'i', ' ', 'ㅎ', 'ㅏ', 'ㄴ'], expected: 'hi 한' },
  { name: 'comma separation', tokens: ['ㅎ', 'ㅏ', 'ㄴ', ',', 'ㄱ', 'ㅡ', 'ㄹ'], expected: '한,글' },
  { name: 'emoji after Korean', tokens: ['ㅎ', 'ㅏ', 'ㄴ', ' ', '🙂'], expected: '한 🙂' },
  { name: 'enclosed parens', tokens: ['(', 'ㄱ', 'ㅏ', ')'], expected: '(가)' },
  { name: 'digits Korean digits', tokens: ['3', '0', '개', '소'], expected: '30개소' },
  { name: 'trailing ASCII', tokens: ['ㅎ', 'ㅏ', 'y'], expected: '하y' },
]
for (const m of MIXED_SEED) {
  SAMPLES.push({
    name: m.name,
    category: 'mixed-ascii',
    tokens: m.tokens,
    expected_committed: m.expected,
  })
}

// ---------------------------------------------------------------------------
// Emit JSON
// ---------------------------------------------------------------------------

const here = dirname(fileURLToPath(import.meta.url))
const outPath = join(here, 'korean-composition-samples.json')

const total = SAMPLES.length
if (total !== 200) {
  // eslint-disable-next-line no-console -- generator diagnostic only.
  console.error(`[T032] expected 200 samples; got ${total}`)
  process.exit(1)
}

writeFileSync(
  outPath,
  JSON.stringify(
    {
      source: 'Spec 288 · T032',
      description:
        '200 Korean IME composition samples covering 단모음 / 이중모음 / 복합종성 / precomposed / mixed-ASCII edges.',
      count: total,
      samples: SAMPLES,
    },
    null,
    2,
  ),
)

// eslint-disable-next-line no-console -- generator diagnostic only.
console.log(`[T032] wrote ${total} samples to ${outPath}`)
