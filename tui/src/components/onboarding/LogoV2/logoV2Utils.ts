// Source: .references/claude-code-sourcemap/restored-src/src/utils/logoV2Utils.ts (Claude Code 2.1.88, research-use)
// KOSMOS PORT + REWRITE per Epic H #1302 (035-onboarding-brand-port) — ADR-006 A-9
//
// PORT (generic terminal-size math, content-agnostic):
//   - getLayoutMode(cols): selects 'full' | 'condensed' | 'fallback'
//   - calculateLayoutDimensions(cols): column geometry for the splash
//   - calculateOptimalLeftWidth(cols): left-column width under 'full'
//   - formatWelcomeMessage(version): builds the Korean welcome string
//
// REWRITE (KOSMOS-specific data sources):
//   - getKosmosSessionHistorySync(): reads memdir Session tier
//   - getMinistryAvailabilitySync(): reads Spec 022 adapter registry
//
// DISCARDED (CC-only, Anthropic-branded):
//   - getLogoDisplayData — superseded by KOSMOS_BANNER_ASSET selection.
//
// Reference: specs/035-onboarding-brand-port/plan.md § Phase 0 R-7

import type { KosmosSession, MinistryStatus } from './feedConfigs'

// ---------------------------------------------------------------------------
// PORT — layout-mode math (no CC content, only generic terminal geometry)
// ---------------------------------------------------------------------------

export type LayoutMode = 'full' | 'condensed' | 'fallback'

const FULL_MIN_COLS = 80
const CONDENSED_MIN_COLS = 50

export function getLayoutMode(cols: number): LayoutMode {
  if (cols >= FULL_MIN_COLS) return 'full'
  if (cols >= CONDENSED_MIN_COLS) return 'condensed'
  return 'fallback'
}

export type LayoutDimensions = {
  mode: LayoutMode
  totalWidth: number
  leftWidth: number
  rightWidth: number
  gap: number
}

/**
 * Derives the column geometry for the splash given a terminal width.  The
 * splash is only rendered at `mode === 'full'`; condensed and fallback modes
 * bypass column math (rendered by `CondensedLogo.tsx` or a single-line).
 */
export function calculateLayoutDimensions(cols: number): LayoutDimensions {
  const mode = getLayoutMode(cols)
  if (mode !== 'full') {
    return {
      mode,
      totalWidth: cols,
      leftWidth: cols,
      rightWidth: 0,
      gap: 0,
    }
  }
  const gap = 2
  const leftWidth = calculateOptimalLeftWidth(cols)
  const rightWidth = Math.max(0, cols - leftWidth - gap)
  return { mode, totalWidth: cols, leftWidth, rightWidth, gap }
}

/**
 * Left-column width under 'full' mode: 60% of total, clamped to [28, 48].
 */
export function calculateOptimalLeftWidth(cols: number): number {
  const target = Math.floor(cols * 0.6)
  if (target < 28) return 28
  if (target > 48) return 48
  return target
}

/**
 * Builds the Korean welcome string used by `WelcomeV2.tsx`.  Kept pure so
 * tests can assert the exact shape without rendering Ink.
 */
export function formatWelcomeMessage(version: string): string {
  return `KOSMOS에 오신 것을 환영합니다  v${version}`
}

// ---------------------------------------------------------------------------
// REWRITE — KOSMOS data sources (sync wrappers over session + registry reads)
// ---------------------------------------------------------------------------

/**
 * Returns the most recent KOSMOS session entries (bounded by `limit`) read
 * from the memdir Session tier.  Implementation is a thin sync wrapper
 * consumed by `LogoV2.tsx`; the IO is delegated to the injected `reader`
 * so tests can substitute fixtures without touching the filesystem.
 *
 * Default reader returns an empty array — the real filesystem-backed reader
 * lands with the memdir wiring in Spec 027 integration.
 */
export type SessionHistoryReader = () => KosmosSession[]

const EMPTY_SESSIONS: SessionHistoryReader = () => []

export function getKosmosSessionHistorySync(
  limit = 5,
  reader: SessionHistoryReader = EMPTY_SESSIONS,
): KosmosSession[] {
  const sessions = reader()
  if (sessions.length <= limit) return sessions
  return sessions.slice(0, limit)
}

/**
 * Returns the current availability status for each Phase 1 ministry.  Reads
 * from the Spec 022 adapter registry via the injected `reader` so tests can
 * substitute a deterministic snapshot.
 *
 * Default reader returns all four ministries marked available = false
 * (fail-closed — the registry has not yet reported in).
 */
export type MinistryStatusReader = () => MinistryStatus[]

const FAIL_CLOSED_MINISTRIES: MinistryStatusReader = () => [
  { ministryCode: 'KOROAD', displayName: '한국도로공사', available: false },
  { ministryCode: 'KMA', displayName: '기상청', available: false },
  { ministryCode: 'HIRA', displayName: '건강보험심사평가원', available: false },
  { ministryCode: 'NMC', displayName: '국립중앙의료원', available: false },
]

export function getMinistryAvailabilitySync(
  reader: MinistryStatusReader = FAIL_CLOSED_MINISTRIES,
): MinistryStatus[] {
  return reader()
}
