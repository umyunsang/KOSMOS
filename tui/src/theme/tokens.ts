// Source: .references/claude-code-sourcemap/restored-src/src/utils/theme.ts (Claude Code 2.1.88, research-use)
// KOSMOS 브랜드 토큰으로 리네이밍됨 (ADR-006 A-9)

/**
 * ThemeToken is the canonical set of named color slots used throughout the
 * KOSMOS TUI.  It binds to the KOSMOS brand metaphor (orbital core, orbital
 * ring, wordmark, subtitle, ministry satellites) per ADR-006 A-9; keys that
 * are tied to harness semantics (subagent palette, diff colours, rainbow
 * shimmer) are retained verbatim from the upstream source so that lifted
 * components continue to compile.
 *
 * Contract: specs/035-onboarding-brand-port/contracts/brand-token-surface.md
 * Grep gate: specs/034-tui-component-catalog/contracts/grep-gate-rules.md § 4
 *
 * The "default" KOSMOS theme maps to the upstream "dark" palette.
 */
export type ThemeToken = {
  autoAccept: string
  bashBorder: string
  // KOSMOS metaphor — orbital core (asterisk glyph)
  kosmosCore: string
  kosmosCoreShimmer: string
  // KOSMOS metaphor — orbital ring (ADR-006 A-9 composition)
  orbitalRing: string
  orbitalRingShimmer: string
  // KOSMOS wordmark + subtitle
  wordmark: string
  subtitle: string
  // KOSMOS ministry satellites (Phase 1 ministries)
  agentSatelliteKoroad: string
  agentSatelliteKma: string
  agentSatelliteHira: string
  agentSatelliteNmc: string
  permission: string
  permissionShimmer: string
  planMode: string
  ide: string
  promptBorder: string
  promptBorderShimmer: string
  text: string
  inverseText: string
  inactive: string
  inactiveShimmer: string
  subtle: string
  suggestion: string
  remember: string
  background: string
  success: string
  error: string
  warning: string
  merged: string
  warningShimmer: string
  diffAdded: string
  diffRemoved: string
  diffAddedDimmed: string
  diffRemovedDimmed: string
  diffAddedWord: string
  diffRemovedWord: string
  red_FOR_SUBAGENTS_ONLY: string
  blue_FOR_SUBAGENTS_ONLY: string
  green_FOR_SUBAGENTS_ONLY: string
  yellow_FOR_SUBAGENTS_ONLY: string
  purple_FOR_SUBAGENTS_ONLY: string
  orange_FOR_SUBAGENTS_ONLY: string
  pink_FOR_SUBAGENTS_ONLY: string
  cyan_FOR_SUBAGENTS_ONLY: string
  professionalBlue: string
  chromeYellow: string
  userMessageBackground: string
  userMessageBackgroundHover: string
  messageActionsBackground: string
  selectionBg: string
  bashMessageBackgroundColor: string
  memoryBackgroundColor: string
  rate_limit_fill: string
  rate_limit_empty: string
  fastMode: string
  fastModeShimmer: string
  briefLabelYou: string
  rainbow_red: string
  rainbow_orange: string
  rainbow_yellow: string
  rainbow_green: string
  rainbow_blue: string
  rainbow_indigo: string
  rainbow_violet: string
  rainbow_red_shimmer: string
  rainbow_orange_shimmer: string
  rainbow_yellow_shimmer: string
  rainbow_green_shimmer: string
  rainbow_blue_shimmer: string
  rainbow_indigo_shimmer: string
  rainbow_violet_shimmer: string
}
