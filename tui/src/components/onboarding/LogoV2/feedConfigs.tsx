// Source: .references/claude-code-sourcemap/restored-src/src/components/LogoV2/feedConfigs.tsx (Claude Code 2.1.88, research-use)
// KOSMOS REWRITE per Epic H #1302 (035-onboarding-brand-port) — ADR-006 A-9

// CC's five factories (createRecentActivityFeed, createWhatsNewFeed,
// createProjectOnboardingFeed, createGuestPassesFeed, createOverageCreditFeed)
// are entirely deleted. Two KOSMOS-domain factories replace them.

// ---------------------------------------------------------------------------
// Domain types
// ---------------------------------------------------------------------------

export type KosmosSession = {
  /** UUIDv7 session identifier */
  sessionId: string
  /** First-query short label (already-shortened upstream; treat as display-ready) */
  queryLabel: string
  /** ISO-8601 UTC timestamp */
  timestampIso: string
}

export type MinistryCode = 'KOROAD' | 'KMA' | 'HIRA' | 'NMC'

export type MinistryStatus = {
  ministryCode: MinistryCode
  /** Korean ministry display name, e.g. '한국도로공사' */
  displayName: string
  /** true ⇒ ●  false ⇒ ○ */
  available: boolean
}

// ---------------------------------------------------------------------------
// Feed primitive types (consumed by Feed.tsx / FeedColumn.tsx)
// ---------------------------------------------------------------------------

export type FeedRow = {
  kind: 'session' | 'ministry'
  /** Main label: queryLabel for sessions, displayName for ministries */
  primary: string
  /** Timestamp string for sessions; '●' or '○' for ministries */
  secondary?: string
  /** Ministry binding — set only for ministry rows */
  meta?: MinistryCode
}

export type FeedConfig = {
  /** Korean heading shown above the feed column */
  title: string
  rows: FeedRow[]
  /** Optional per-row accent token name. Omitted for the session feed. */
  accentFor?: (row: FeedRow) => string
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

/**
 * Format an ISO-8601 UTC string as `YYYY-MM-DD HH:mm`.
 * Returns the raw input string unchanged if parsing fails — never throws.
 */
function formatTimestamp(iso: string): string {
  try {
    const d = new Date(iso)
    if (isNaN(d.getTime())) {
      return iso
    }
    const yyyy = d.getUTCFullYear().toString().padStart(4, '0')
    const mm = (d.getUTCMonth() + 1).toString().padStart(2, '0')
    const dd = d.getUTCDate().toString().padStart(2, '0')
    const hh = d.getUTCHours().toString().padStart(2, '0')
    const min = d.getUTCMinutes().toString().padStart(2, '0')
    return `${yyyy}-${mm}-${dd} ${hh}:${min}`
  } catch {
    return iso
  }
}

/** Map a MinistryCode to its agentSatellite token name. */
function ministryToken(code: MinistryCode): string {
  switch (code) {
    case 'KOROAD':
      return 'agentSatelliteKoroad'
    case 'KMA':
      return 'agentSatelliteKma'
    case 'HIRA':
      return 'agentSatelliteHira'
    case 'NMC':
      return 'agentSatelliteNmc'
  }
}

// ---------------------------------------------------------------------------
// Exported factory functions
// ---------------------------------------------------------------------------

/**
 * Build a FeedConfig for the session-history column ("최근 세션").
 *
 * - Title: '최근 세션' (citizen-facing Korean label — AGENTS.md domain-data exception).
 * - Rows: up to 5 most-recent entries. The caller is responsible for ordering;
 *   this factory does NOT re-sort the input array.
 * - No accentFor (session rows use the default `text` token).
 */
export function createKosmosSessionHistoryFeed(
  sessionHistory: KosmosSession[],
): FeedConfig {
  const rows: FeedRow[] = sessionHistory.slice(0, 5).map((sess) => ({
    kind: 'session',
    primary: sess.queryLabel,
    secondary: formatTimestamp(sess.timestampIso),
    meta: undefined,
  }))

  return {
    title: '최근 세션',
    rows,
    // No accentFor — session rows inherit the default text token.
  }
}

/**
 * Build a FeedConfig for the ministry-availability column ("부처 상태").
 *
 * - Title: '부처 상태' (citizen-facing Korean label — AGENTS.md domain-data exception).
 * - Rows: one per MinistryStatus entry; availability shown as ●/○.
 * - accentFor: returns the agentSatellite* token for ministry rows; 'text' otherwise.
 */
export function createMinistryAvailabilityFeed(
  status: MinistryStatus[],
): FeedConfig {
  const rows: FeedRow[] = status.map((ms) => ({
    kind: 'ministry',
    primary: ms.displayName,
    secondary: ms.available ? '●' : '○',
    meta: ms.ministryCode,
  }))

  return {
    title: '부처 상태',
    rows,
    accentFor(row: FeedRow): string {
      if (row.kind === 'ministry' && row.meta !== undefined) {
        return ministryToken(row.meta)
      }
      return 'text'
    },
  }
}
