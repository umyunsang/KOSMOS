#!/usr/bin/env bun
// Source: KOSMOS Epic H #1302 (035-onboarding-brand-port), tasks T003 + T045
// Reference: specs/035-onboarding-brand-port/contracts/contrast-measurements.md § 1–§ 2
// Dependency policy: Bun + stdlib only (AGENTS.md hard rule, research R-3).
//
// Measures WCAG 2.1 contrast ratios for every (foreground, background) pair
// declared in contracts/contrast-measurements.md § 2 against the dark theme
// palette.  Body-text pairs must meet >= 4.5; non-text >= 3.0.  Exits
// non-zero when any pair fails its threshold so CI can block the PR.

import { readFileSync, writeFileSync, mkdirSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import process from 'node:process'

/**
 * @typedef {"body" | "nontext"} PairKind
 * @typedef {{ foregroundToken: string, backgroundToken: string, kind: PairKind }} Pair
 * @typedef {{ r: number, g: number, b: number }} Rgb
 */

// ---------------------------------------------------------------------------
// Pair matrix (contracts/contrast-measurements.md § 2)
// ---------------------------------------------------------------------------

/** @type {readonly Pair[]} */
export const PAIR_MATRIX = Object.freeze([
  // Body-text pairs (threshold >= 4.5)
  { foregroundToken: 'wordmark', backgroundToken: 'background', kind: 'body' },
  { foregroundToken: 'subtitle', backgroundToken: 'background', kind: 'body' },
  { foregroundToken: 'text', backgroundToken: 'background', kind: 'body' },
  { foregroundToken: 'subtle', backgroundToken: 'background', kind: 'body' },
  { foregroundToken: 'success', backgroundToken: 'background', kind: 'body' },
  { foregroundToken: 'error', backgroundToken: 'background', kind: 'body' },
  { foregroundToken: 'warning', backgroundToken: 'background', kind: 'body' },
  { foregroundToken: 'agentSatelliteKoroad', backgroundToken: 'background', kind: 'body' },
  { foregroundToken: 'agentSatelliteKma', backgroundToken: 'background', kind: 'body' },
  { foregroundToken: 'agentSatelliteHira', backgroundToken: 'background', kind: 'body' },
  { foregroundToken: 'agentSatelliteNmc', backgroundToken: 'background', kind: 'body' },
  // Non-text pairs (threshold >= 3.0)
  { foregroundToken: 'kosmosCore', backgroundToken: 'background', kind: 'nontext' },
  { foregroundToken: 'kosmosCoreShimmer', backgroundToken: 'background', kind: 'nontext' },
  { foregroundToken: 'orbitalRing', backgroundToken: 'background', kind: 'nontext' },
  { foregroundToken: 'orbitalRingShimmer', backgroundToken: 'background', kind: 'nontext' },
  // Diff pairs (threshold >= 3.0 — non-text UI chrome)
  { foregroundToken: 'diffAdded', backgroundToken: 'background', kind: 'nontext' },
  { foregroundToken: 'diffRemoved', backgroundToken: 'background', kind: 'nontext' },
])

/** @type {Readonly<Record<PairKind, number>>} */
export const THRESHOLDS = Object.freeze({
  body: 4.5,
  nontext: 3.0,
})

// ---------------------------------------------------------------------------
// Dark-theme parser — maps token identifier → rgb(r,g,b) literal
// ---------------------------------------------------------------------------

const RGB_LINE_RE = /^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:\s*'rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)'\s*,/

/**
 * @param {string} body
 * @returns {Map<string, Rgb>}
 */
export function parseRgbMap(body) {
  const map = /** @type {Map<string, Rgb>} */ (new Map())
  for (const line of body.split('\n')) {
    const m = line.match(RGB_LINE_RE)
    if (m === null) continue
    const [, token, r, g, b] = m
    if (token === undefined || r === undefined || g === undefined || b === undefined) {
      continue
    }
    map.set(token, {
      r: Number(r),
      g: Number(g),
      b: Number(b),
    })
  }
  return map
}

// ---------------------------------------------------------------------------
// WCAG 2.1 relative luminance + contrast ratio
// ---------------------------------------------------------------------------

/**
 * @param {number} channel8bit
 * @returns {number}
 */
function linearise(channel8bit) {
  const c = channel8bit / 255
  return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4
}

/**
 * @param {Rgb} rgb
 * @returns {number}
 */
export function relativeLuminance(rgb) {
  return (
    0.2126 * linearise(rgb.r) +
    0.7152 * linearise(rgb.g) +
    0.0722 * linearise(rgb.b)
  )
}

/**
 * @param {Rgb} fg
 * @param {Rgb} bg
 * @returns {number}
 */
export function contrastRatio(fg, bg) {
  const lfg = relativeLuminance(fg)
  const lbg = relativeLuminance(bg)
  const lighter = Math.max(lfg, lbg)
  const darker = Math.min(lfg, lbg)
  return (lighter + 0.05) / (darker + 0.05)
}

/**
 * @param {Rgb} rgb
 * @returns {string}
 */
function toHex(rgb) {
  const hex = (/** @type {number} */ n) =>
    n.toString(16).padStart(2, '0')
  return `#${hex(rgb.r)}${hex(rgb.g)}${hex(rgb.b)}`
}

// ---------------------------------------------------------------------------
// Markdown emission
// ---------------------------------------------------------------------------

/**
 * @typedef {{
 *   pair: Pair
 *   fgHex: string
 *   bgHex: string
 *   ratio: number
 *   threshold: number
 *   pass: boolean
 * }} Measurement
 */

/**
 * @param {Measurement[]} results
 * @returns {string}
 */
function renderMarkdown(results) {
  const now = new Date().toISOString()
  const groups = {
    body: results.filter((r) => r.pair.kind === 'body'),
    nontext: results.filter((r) => r.pair.kind === 'nontext'),
  }
  const lines = [
    '# Contrast Measurements — KOSMOS dark theme',
    '',
    `**Generated**: ${now}`,
    '**Source**: `tui/src/theme/dark.ts`',
    '**Methodology**: WCAG 2.1 Success Criterion 1.4.3 (`(L1 + 0.05) / (L2 + 0.05)`)',
    '**Generator**: `scripts/compute-contrast.mjs` (Bun + stdlib, Epic H #1302 T045)',
    '',
    'This document is machine-regenerated — do NOT hand-edit.  Re-run the',
    'generator script after any palette change and commit the output.',
    '',
    '## Body-text pairs (threshold ≥ 4.5)',
    '',
    '| # | Foreground token | Fg hex | Bg hex | Ratio | Threshold | Pass? |',
    '|---|---|---|---|---|---|---|',
  ]
  groups.body.forEach((r, i) => {
    lines.push(
      `| ${i + 1} | ${r.pair.foregroundToken} | ${r.fgHex} | ${r.bgHex} | ${r.ratio.toFixed(2)} | ${r.threshold.toFixed(1)} | ${r.pass ? '✅' : '❌'} |`,
    )
  })
  lines.push('', '## Non-text pairs (threshold ≥ 3.0)', '')
  lines.push('| # | Foreground token | Fg hex | Bg hex | Ratio | Threshold | Pass? |')
  lines.push('|---|---|---|---|---|---|---|')
  groups.nontext.forEach((r, i) => {
    lines.push(
      `| ${i + 1} | ${r.pair.foregroundToken} | ${r.fgHex} | ${r.bgHex} | ${r.ratio.toFixed(2)} | ${r.threshold.toFixed(1)} | ${r.pass ? '✅' : '❌'} |`,
    )
  })
  const passed = results.filter((r) => r.pass).length
  const total = results.length
  lines.push(
    '',
    `## Summary — ${passed}/${total} pairs pass`,
    '',
    passed === total
      ? 'All measured pairs satisfy their WCAG 2.1 threshold.'
      : `**FAILED** — ${total - passed} pair(s) below threshold. Raise the failing token value(s) per contracts/contrast-measurements.md § 3.`,
    '',
  )
  return lines.join('\n')
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

function main() {
  const repoRoot = resolve(import.meta.dir, '..')
  const themePath = resolve(repoRoot, 'tui/src/theme/dark.ts')
  const outPath = resolve(repoRoot, 'docs/design/contrast-measurements.md')

  const body = readFileSync(themePath, 'utf8')
  const rgbMap = parseRgbMap(body)

  /** @type {Measurement[]} */
  const results = []
  for (const pair of PAIR_MATRIX) {
    const fg = rgbMap.get(pair.foregroundToken)
    const bg = rgbMap.get(pair.backgroundToken)
    if (fg === undefined || bg === undefined) {
      console.error(
        `[compute-contrast] missing palette entry: fg=${pair.foregroundToken} bg=${pair.backgroundToken}`,
      )
      return 2
    }
    const ratio = contrastRatio(fg, bg)
    const threshold = THRESHOLDS[pair.kind]
    results.push({
      pair,
      fgHex: toHex(fg),
      bgHex: toHex(bg),
      ratio,
      threshold,
      pass: ratio >= threshold,
    })
  }

  const md = renderMarkdown(results)
  mkdirSync(dirname(outPath), { recursive: true })
  writeFileSync(outPath, md, { encoding: 'utf8' })

  const failures = results.filter((r) => !r.pass)
  if (failures.length > 0) {
    console.error(
      `[compute-contrast] FAIL — ${failures.length} pair(s) below threshold:`,
    )
    for (const f of failures) {
      console.error(
        `  ${f.pair.foregroundToken} / ${f.pair.backgroundToken}: ${f.ratio.toFixed(2)} < ${f.threshold.toFixed(1)}`,
      )
    }
    console.error(`Wrote report to ${outPath}`)
    return 1
  }

  console.log(
    `[compute-contrast] PASS — ${results.length} pairs all meet threshold. Report: ${outPath}`,
  )
  return 0
}

process.exit(main())
