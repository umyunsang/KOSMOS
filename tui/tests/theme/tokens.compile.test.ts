// Source: KOSMOS Epic H #1302 (035-onboarding-brand-port), task T006
// Contract: specs/035-onboarding-brand-port/contracts/brand-token-surface.md § 1–§ 4, § 7
// Purpose: lock the ThemeToken type surface at compile time.  Any drift from
// the spec (accidental reintroduction of a BAN identifier, missing KOSMOS
// token, preserve-set cardinality change) fails this test.
//
// Strategy: parse `tui/src/theme/tokens.ts` as text (avoids runtime token
// value leakage) and assert identifier-level membership.  Bun's test runner
// executes this file before any TUI component renders.

import { test, expect, describe } from "bun:test"
import { readFileSync } from "node:fs"
import { resolve } from "node:path"

const TOKENS_PATH = resolve(import.meta.dir, "../../src/theme/tokens.ts")
const TOKENS_BODY = readFileSync(TOKENS_PATH, "utf8")

const DELETE_IDENTIFIERS = [
  "claude",
  "claudeShimmer",
  "claudeBlue_FOR_SYSTEM_SPINNER",
  "claudeBlueShimmer_FOR_SYSTEM_SPINNER",
  "clawd_body",
  "clawd_background",
  "briefLabelClaude",
] as const

const ADD_IDENTIFIERS = [
  "kosmosCore",
  "kosmosCoreShimmer",
  "orbitalRing",
  "orbitalRingShimmer",
  "wordmark",
  "subtitle",
  "agentSatelliteKoroad",
  "agentSatelliteKma",
  "agentSatelliteHira",
  "agentSatelliteNmc",
] as const

// Preserve set (62 identifiers per contracts/brand-token-surface.md § 4).
const PRESERVE_IDENTIFIERS = [
  // Harness-state (12)
  "autoAccept",
  "bashBorder",
  "permission",
  "permissionShimmer",
  "planMode",
  "ide",
  "promptBorder",
  "promptBorderShimmer",
  "merged",
  "professionalBlue",
  "chromeYellow",
  "fastMode",
  "fastModeShimmer",
  // Semantic (12)
  "text",
  "inverseText",
  "inactive",
  "inactiveShimmer",
  "subtle",
  "suggestion",
  "remember",
  "success",
  "error",
  "warning",
  "warningShimmer",
  "briefLabelYou",
  // Diff (6)
  "diffAdded",
  "diffRemoved",
  "diffAddedDimmed",
  "diffRemovedDimmed",
  "diffAddedWord",
  "diffRemovedWord",
  // Subagent (8)
  "red_FOR_SUBAGENTS_ONLY",
  "blue_FOR_SUBAGENTS_ONLY",
  "green_FOR_SUBAGENTS_ONLY",
  "yellow_FOR_SUBAGENTS_ONLY",
  "purple_FOR_SUBAGENTS_ONLY",
  "orange_FOR_SUBAGENTS_ONLY",
  "pink_FOR_SUBAGENTS_ONLY",
  "cyan_FOR_SUBAGENTS_ONLY",
  // Message-surface (6)
  "userMessageBackground",
  "userMessageBackgroundHover",
  "messageActionsBackground",
  "selectionBg",
  "bashMessageBackgroundColor",
  "memoryBackgroundColor",
  // Rate-limit (2)
  "rate_limit_fill",
  "rate_limit_empty",
  // Rainbow (14)
  "rainbow_red",
  "rainbow_orange",
  "rainbow_yellow",
  "rainbow_green",
  "rainbow_blue",
  "rainbow_indigo",
  "rainbow_violet",
  "rainbow_red_shimmer",
  "rainbow_orange_shimmer",
  "rainbow_yellow_shimmer",
  "rainbow_green_shimmer",
  "rainbow_blue_shimmer",
  "rainbow_indigo_shimmer",
  "rainbow_violet_shimmer",
  // Background (1)
  "background",
] as const

/**
 * Extracts the identifiers from the `export type ThemeToken = { ... }` block.
 */
function extractTokenTypeKeys(body: string): string[] {
  const typeMatch = body.match(
    /export type ThemeToken = \{([\s\S]*?)\n\}/,
  )
  const block = typeMatch?.[1]
  if (block === undefined) {
    throw new Error(
      "could not locate `export type ThemeToken` block in tokens.ts",
    )
  }
  const keys: string[] = []
  for (const line of block.split("\n")) {
    const m = line.match(/^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:\s*string\s*$/)
    const ident = m?.[1]
    if (ident !== undefined) keys.push(ident)
  }
  return keys
}

describe("brand-token-surface contract (Epic H)", () => {
  const keys = extractTokenTypeKeys(TOKENS_BODY)
  const keySet = new Set(keys)

  test("zero occurrences of DELETE set identifiers", () => {
    for (const ident of DELETE_IDENTIFIERS) {
      expect(keySet.has(ident)).toBe(false)
    }
  })

  test("all 10 ADD set identifiers present", () => {
    for (const ident of ADD_IDENTIFIERS) {
      expect(keySet.has(ident)).toBe(true)
    }
  })

  test("preserve set of 62 identifiers all present", () => {
    expect(PRESERVE_IDENTIFIERS.length).toBe(62)
    for (const ident of PRESERVE_IDENTIFIERS) {
      expect(keySet.has(ident)).toBe(true)
    }
  })

  test("total token count = 10 (add) + 62 (preserve) = 72", () => {
    expect(keys.length).toBe(72)
  })

  test("header comment announces KOSMOS brand rename (ADR-006 A-9)", () => {
    expect(TOKENS_BODY).toContain(
      "// KOSMOS 브랜드 토큰으로 리네이밍됨 (ADR-006 A-9)",
    )
  })

  test("upstream Source: attribution line preserved", () => {
    expect(TOKENS_BODY).toContain(
      "// Source: .references/claude-code-sourcemap/restored-src/src/utils/theme.ts",
    )
  })
})
