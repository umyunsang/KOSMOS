// Source: .references/claude-code-sourcemap/restored-src/src/utils/theme.ts (Claude Code 2.1.88, research-use)
// KOSMOS 브랜드 토큰으로 리네이밍됨 (ADR-006 A-9)
import type { ThemeToken } from './tokens'

/**
 * Default KOSMOS theme — maps to the KOSMOS dark palette (ADR-006 A-9).
 * Uses explicit RGB values to avoid inconsistencies from users'
 * custom terminal ANSI color definitions.
 */
const defaultTheme: ThemeToken = {
  autoAccept: 'rgb(175,135,255)', // Electric violet
  bashBorder: 'rgb(253,93,177)', // Bright pink
  // KOSMOS metaphor — orbital core
  kosmosCore: 'rgb(99,102,241)', // #6366f1
  kosmosCoreShimmer: 'rgb(165,180,252)', // #a5b4fc
  // KOSMOS metaphor — orbital ring
  orbitalRing: 'rgb(96,165,250)', // #60a5fa
  orbitalRingShimmer: 'rgb(199,210,254)', // #c7d2fe
  // KOSMOS wordmark + subtitle
  wordmark: 'rgb(224,231,255)', // #e0e7ff
  subtitle: 'rgb(148,163,184)', // #94a3b8
  // KOSMOS ministry satellites
  agentSatelliteKoroad: 'rgb(244,114,182)', // #f472b6 (한국도로공사)
  agentSatelliteKma: 'rgb(52,211,153)', // #34d399 (기상청)
  agentSatelliteHira: 'rgb(147,197,253)', // #93c5fd (건강보험심사평가원)
  agentSatelliteNmc: 'rgb(196,181,253)', // #c4b5fd (국립중앙의료원)
  permission: 'rgb(177,185,249)', // Light blue-purple
  permissionShimmer: 'rgb(207,215,255)', // Lighter blue-purple for shimmer
  planMode: 'rgb(72,150,140)', // Muted sage green
  ide: 'rgb(71,130,200)', // Muted blue
  promptBorder: 'rgb(136,136,136)', // Medium gray
  promptBorderShimmer: 'rgb(166,166,166)', // Lighter gray for shimmer
  text: 'rgb(255,255,255)', // White
  inverseText: 'rgb(0,0,0)', // Black
  inactive: 'rgb(153,153,153)', // Light gray
  inactiveShimmer: 'rgb(193,193,193)', // Lighter gray for shimmer effect
  subtle: 'rgb(80,80,80)', // Dark gray
  suggestion: 'rgb(177,185,249)', // Light blue-purple
  remember: 'rgb(177,185,249)', // Light blue-purple
  background: 'rgb(10,14,39)', // #0a0e27 — KOSMOS navy
  success: 'rgb(78,186,101)', // Bright green
  error: 'rgb(255,107,128)', // Bright red
  warning: 'rgb(255,193,7)', // Bright amber
  merged: 'rgb(175,135,255)', // Electric violet (matches autoAccept)
  warningShimmer: 'rgb(255,223,57)', // Lighter amber for shimmer
  diffAdded: 'rgb(34,92,43)', // Dark green
  diffRemoved: 'rgb(122,41,54)', // Dark red
  diffAddedDimmed: 'rgb(71,88,74)', // Very dark green
  diffRemovedDimmed: 'rgb(105,72,77)', // Very dark red
  diffAddedWord: 'rgb(56,166,96)', // Medium green
  diffRemovedWord: 'rgb(179,89,107)', // Softer red
  red_FOR_SUBAGENTS_ONLY: 'rgb(220,38,38)', // Red 600
  blue_FOR_SUBAGENTS_ONLY: 'rgb(37,99,235)', // Blue 600
  green_FOR_SUBAGENTS_ONLY: 'rgb(22,163,74)', // Green 600
  yellow_FOR_SUBAGENTS_ONLY: 'rgb(202,138,4)', // Yellow 600
  purple_FOR_SUBAGENTS_ONLY: 'rgb(147,51,234)', // Purple 600
  orange_FOR_SUBAGENTS_ONLY: 'rgb(234,88,12)', // Orange 600
  pink_FOR_SUBAGENTS_ONLY: 'rgb(219,39,119)', // Pink 600
  cyan_FOR_SUBAGENTS_ONLY: 'rgb(8,145,178)', // Cyan 600
  professionalBlue: 'rgb(106,155,204)',
  chromeYellow: 'rgb(251,188,4)',
  userMessageBackground: 'rgb(55, 55, 55)',
  userMessageBackgroundHover: 'rgb(70, 70, 70)',
  messageActionsBackground: 'rgb(44, 50, 62)',
  selectionBg: 'rgb(38, 79, 120)',
  bashMessageBackgroundColor: 'rgb(65, 60, 65)',
  memoryBackgroundColor: 'rgb(55, 65, 70)',
  rate_limit_fill: 'rgb(177,185,249)',
  rate_limit_empty: 'rgb(80,83,112)',
  fastMode: 'rgb(255,120,20)',
  fastModeShimmer: 'rgb(255,165,70)',
  briefLabelYou: 'rgb(122,180,232)',
  rainbow_red: 'rgb(235,95,87)',
  rainbow_orange: 'rgb(245,139,87)',
  rainbow_yellow: 'rgb(250,195,95)',
  rainbow_green: 'rgb(145,200,130)',
  rainbow_blue: 'rgb(130,170,220)',
  rainbow_indigo: 'rgb(155,130,200)',
  rainbow_violet: 'rgb(200,130,180)',
  rainbow_red_shimmer: 'rgb(250,155,147)',
  rainbow_orange_shimmer: 'rgb(255,185,137)',
  rainbow_yellow_shimmer: 'rgb(255,225,155)',
  rainbow_green_shimmer: 'rgb(185,230,180)',
  rainbow_blue_shimmer: 'rgb(180,205,240)',
  rainbow_indigo_shimmer: 'rgb(195,180,230)',
  rainbow_violet_shimmer: 'rgb(230,180,210)',
}

export default defaultTheme
