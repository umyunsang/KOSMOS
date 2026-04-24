/**
 * Korean-first date/time parser.
 *
 * Strategy:
 *   1. Try regex dictionary of Korean phrases (relative + absolute) → produce a Date.
 *   2. If no Korean pattern matched, attempt ISO-8601 / standard date parse via Date.parse().
 *   3. Return { iso: Date, interpretedText: string } or throw.
 *
 * Design constraints:
 *   - Zero new npm dependencies (AGENTS.md hard rule).
 *   - Uses only Bun/JS stdlib: Date, Intl.DateTimeFormat, regex.
 *   - Timezone handling: Intl.DateTimeFormat(tz) for formatting output;
 *     "now" anchor is always derived from Date.now() in the caller's wall time
 *     then shifted to the target timezone for relative-day resolution.
 */

export interface ParseResult {
  /** The resolved Date object (absolute UTC instant). */
  date: Date
  /** Human-readable interpretation echoed back for LLM confirmation. */
  interpretedText: string
}

// ---------------------------------------------------------------------------
// Day-of-week helpers
// ---------------------------------------------------------------------------

const KO_DAY_NAMES = ['일', '월', '화', '수', '목', '금', '토'] as const
type KoDayName = (typeof KO_DAY_NAMES)[number]

function koDayIndex(name: KoDayName): number {
  return KO_DAY_NAMES.indexOf(name)
}

// ---------------------------------------------------------------------------
// Time-of-day Korean phrases → hour offset
// ---------------------------------------------------------------------------

const KO_TIME_OF_DAY: Record<string, number> = {
  새벽: 3,   // before dawn ~03:00
  아침: 8,   // morning ~08:00
  오전: 9,   // AM (default 09:00 if no hour given)
  낮: 12,    // noon
  점심: 12,  // lunch
  오후: 13,  // PM (default 13:00 if no hour given)
  저녁: 18,  // evening ~18:00
  밤: 21,    // night ~21:00
  자정: 0,   // midnight
}

// ---------------------------------------------------------------------------
// "now" in a given timezone (returns a Date with time-components matching that tz)
// ---------------------------------------------------------------------------

/**
 * Returns a Date object whose UTC value corresponds to midnight (00:00:00) of
 * "today" in the given IANA timezone.  Used to anchor relative phrases.
 */
function midnightInTz(tz: string): Date {
  const now = new Date()
  // Use Intl to get year/month/day in target tz
  const fmt = new Intl.DateTimeFormat('en-CA', {
    timeZone: tz,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour12: false,
  })
  const parts = fmt.formatToParts(now)
  const get = (t: string) => parts.find((p) => p.type === t)?.value ?? '0'
  const year = Number(get('year'))
  const month = Number(get('month')) - 1
  const day = Number(get('day'))

  // Build midnight in that timezone by creating a UTC date that represents
  // midnight local time.  We use the offset trick: format the UTC offset string.
  const offsetFmt = new Intl.DateTimeFormat('en-US', {
    timeZone: tz,
    timeZoneName: 'shortOffset',
  })
  const offsetStr = offsetFmt.formatToParts(now).find((p) => p.type === 'timeZoneName')?.value ?? 'UTC+0'
  const offsetMatch = offsetStr.match(/UTC([+-])(\d{1,2})(?::(\d{2}))?/)
  let offsetMinutes = 0
  if (offsetMatch) {
    const sign = offsetMatch[1] === '+' ? 1 : -1
    offsetMinutes = sign * (Number(offsetMatch[2]) * 60 + Number(offsetMatch[3] ?? 0))
  }

  // Midnight in local tz = UTC midnight - offsetMinutes
  const localMidnightMs =
    Date.UTC(year, month, day, 0, 0, 0, 0) - offsetMinutes * 60_000
  return new Date(localMidnightMs)
}

function addDays(base: Date, days: number): Date {
  return new Date(base.getTime() + days * 86_400_000)
}

function addHours(base: Date, hours: number): Date {
  return new Date(base.getTime() + hours * 3_600_000)
}

// ---------------------------------------------------------------------------
// Main pattern-matching dictionary
// ---------------------------------------------------------------------------

interface PatternEntry {
  pattern: RegExp
  resolve: (match: RegExpMatchArray, midnight: Date, tz: string) => ParseResult
}

const PATTERNS: PatternEntry[] = [
  // ─── Absolute date+time: "2026년 4월 24일 오후 3시 30분" ───────────────
  {
    pattern:
      /(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일(?:\s*(새벽|아침|오전|낮|점심|오후|저녁|밤|자정))?\s*(\d{1,2})시(?:\s*(\d{1,2})분)?/,
    resolve(m, _midnight, tz) {
      const year = Number(m[1])
      const month = Number(m[2]) - 1
      const day = Number(m[3])
      const todPart = m[4] ?? ''
      let hour = Number(m[5])
      const minute = Number(m[6] ?? '0')

      // PM adjustment
      if (todPart === '오후' || todPart === '저녁' || todPart === '밤') {
        if (hour < 12) hour += 12
      } else if (todPart === '오전' || todPart === '아침') {
        if (hour === 12) hour = 0
      }

      const date = buildDateInTz(year, month, day, hour, minute, 0, tz)
      const interpretedText = `${year}년 ${month + 1}월 ${day}일 ${String(hour).padStart(2, '0')}시 ${String(minute).padStart(2, '0')}분 (${tz})`
      return { date, interpretedText }
    },
  },

  // ─── Absolute date only: "2026년 4월 24일" ───────────────────────────────
  {
    pattern: /(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일/,
    resolve(m, _midnight, tz) {
      const year = Number(m[1])
      const month = Number(m[2]) - 1
      const day = Number(m[3])
      const date = buildDateInTz(year, month, day, 0, 0, 0, tz)
      const interpretedText = `${year}년 ${month + 1}월 ${day}일 자정 (${tz})`
      return { date, interpretedText }
    },
  },

  // ─── "어제/오늘/내일 + time-of-day + 시/분" ─────────────────────────────
  {
    pattern:
      /(어제|오늘|내일)(?:\s*(새벽|아침|오전|낮|점심|오후|저녁|밤|자정))?\s*(\d{1,2})시(?:\s*(\d{1,2})분)?/,
    resolve(m, midnight) {
      const dayOffset = m[1] === '어제' ? -1 : m[1] === '내일' ? 1 : 0
      const todPart = m[2] ?? ''
      let hour = Number(m[3])
      const minute = Number(m[4] ?? '0')

      if (todPart === '오후' || todPart === '저녁' || todPart === '밤') {
        if (hour < 12) hour += 12
      } else if (todPart === '오전' || todPart === '아침') {
        if (hour === 12) hour = 0
      } else if (todPart === '새벽') {
        // 새벽 6시 = 06:00, already correct; just ensure AM
        if (hour >= 12) hour -= 12
      }

      const base = addDays(midnight, dayOffset)
      const date = addHours(base, hour + minute / 60)
      const dayLabel = m[1] === '어제' ? '어제' : m[1] === '내일' ? '내일' : '오늘'
      const interpretedText = `${dayLabel} ${todPart} ${String(hour).padStart(2, '0')}시 ${String(minute).padStart(2, '0')}분`
      return { date, interpretedText }
    },
  },

  // ─── "다음 주 X요일" ───────────────────────────────────────────────────
  {
    pattern: /다음\s*주\s*([일월화수목금토])요일/,
    resolve(m, midnight) {
      const targetDay = koDayIndex(m[1] as KoDayName)
      const todayDow = getDayOfWeekFromDate(midnight)
      let diff = targetDay - todayDow
      if (diff <= 0) diff += 7
      diff += 7 // "next week" = always 7+ days ahead
      const date = addDays(midnight, diff)
      const interpretedText = `다음 주 ${m[1]}요일`
      return { date, interpretedText }
    },
  },

  // ─── "지난 주 X요일" / "지난주 X요일" ────────────────────────────────────
  {
    pattern: /지난\s*주\s*([일월화수목금토])요일/,
    resolve(m, midnight) {
      const targetDay = koDayIndex(m[1] as KoDayName)
      const todayDow = getDayOfWeekFromDate(midnight)
      let diff = todayDow - targetDay
      if (diff <= 0) diff += 7
      diff += 7 // "last week" = always 7+ days behind
      const date = addDays(midnight, -diff)
      const interpretedText = `지난 주 ${m[1]}요일`
      return { date, interpretedText }
    },
  },

  // ─── "이번 주 X요일" ───────────────────────────────────────────────────
  {
    pattern: /이번\s*주\s*([일월화수목금토])요일/,
    resolve(m, midnight) {
      const targetDay = koDayIndex(m[1] as KoDayName)
      const todayDow = getDayOfWeekFromDate(midnight)
      let diff = targetDay - todayDow
      // Stay within the current week (can be past or future within the week)
      const date = addDays(midnight, diff)
      const interpretedText = `이번 주 ${m[1]}요일`
      return { date, interpretedText }
    },
  },

  // ─── "X요일" (nearest, defaulting to future) ─────────────────────────
  {
    pattern: /^([일월화수목금토])요일$/,
    resolve(m, midnight) {
      const targetDay = koDayIndex(m[1] as KoDayName)
      const todayDow = getDayOfWeekFromDate(midnight)
      let diff = targetDay - todayDow
      if (diff <= 0) diff += 7 // next occurrence
      const date = addDays(midnight, diff)
      const interpretedText = `이번 ${m[1]}요일 (${diff}일 후)`
      return { date, interpretedText }
    },
  },

  // ─── "N일 후 / N일 뒤" ─────────────────────────────────────────────────
  {
    pattern: /(\d+)일\s*(?:후|뒤)/,
    resolve(m, midnight) {
      const days = Number(m[1])
      const date = addDays(midnight, days)
      const interpretedText = `지금으로부터 ${days}일 후`
      return { date, interpretedText }
    },
  },

  // ─── "N일 전" ─────────────────────────────────────────────────────────
  {
    pattern: /(\d+)일\s*전/,
    resolve(m, midnight) {
      const days = Number(m[1])
      const date = addDays(midnight, -days)
      const interpretedText = `지금으로부터 ${days}일 전`
      return { date, interpretedText }
    },
  },

  // ─── "N시간 후 / N시간 뒤" ────────────────────────────────────────────
  {
    pattern: /(\d+)시간\s*(?:후|뒤)/,
    resolve(m) {
      const hours = Number(m[1])
      const date = new Date(Date.now() + hours * 3_600_000)
      const interpretedText = `지금으로부터 ${hours}시간 후`
      return { date, interpretedText }
    },
  },

  // ─── "어제" / "오늘" / "내일" (no time) ────────────────────────────────
  {
    pattern: /^(어제|오늘|내일)$/,
    resolve(m, midnight) {
      const offset = m[1] === '어제' ? -1 : m[1] === '내일' ? 1 : 0
      const date = addDays(midnight, offset)
      const labelMap: Record<string, string> = { 어제: '어제', 오늘: '오늘', 내일: '내일' }
      const interpretedText = `${labelMap[m[1]!]} 자정 (00:00 기준)`
      return { date, interpretedText }
    },
  },

  // ─── Time-of-day only (relative to today): "오후 3시" ─────────────────
  {
    pattern: /^(새벽|아침|오전|낮|점심|오후|저녁|밤|자정)\s*(\d{1,2})시(?:\s*(\d{1,2})분)?$/,
    resolve(m, midnight) {
      const todPart = m[1]!
      let hour = Number(m[2])
      const minute = Number(m[3] ?? '0')

      if (todPart === '오후' || todPart === '저녁' || todPart === '밤') {
        if (hour < 12) hour += 12
      } else if (todPart === '오전' || todPart === '아침') {
        if (hour === 12) hour = 0
      } else if (todPart === '새벽') {
        if (hour >= 12) hour -= 12
      } else if (todPart === '자정') {
        hour = 0
      }

      const date = addHours(midnight, hour + minute / 60)
      const interpretedText = `오늘 ${todPart} ${String(hour).padStart(2, '0')}시 ${String(minute).padStart(2, '0')}분`
      return { date, interpretedText }
    },
  },
]

// ---------------------------------------------------------------------------
// Timezone-aware date construction
// ---------------------------------------------------------------------------

/**
 * Build a Date whose UTC value corresponds to the given year/month/day hour:min:sec
 * expressed in the `tz` timezone.  Uses Intl offset trick — no external dep.
 */
function buildDateInTz(
  year: number,
  month: number, // 0-indexed
  day: number,
  hour: number,
  minute: number,
  second: number,
  tz: string,
): Date {
  // Construct a UTC date first (treating local params as UTC)
  const naiveUtc = new Date(Date.UTC(year, month, day, hour, minute, second, 0))
  // Get the tz offset at that approximate moment
  const offsetFmt = new Intl.DateTimeFormat('en-US', {
    timeZone: tz,
    timeZoneName: 'shortOffset',
  })
  const offsetStr =
    offsetFmt.formatToParts(naiveUtc).find((p) => p.type === 'timeZoneName')?.value ?? 'UTC+0'
  const offsetMatch = offsetStr.match(/UTC([+-])(\d{1,2})(?::(\d{2}))?/)
  let offsetMinutes = 0
  if (offsetMatch) {
    const sign = offsetMatch[1] === '+' ? 1 : -1
    offsetMinutes = sign * (Number(offsetMatch[2]) * 60 + Number(offsetMatch[3] ?? 0))
  }
  // Subtract the offset so the UTC value represents the correct local time
  return new Date(naiveUtc.getTime() - offsetMinutes * 60_000)
}

/**
 * Returns the 0-based day-of-week (Sun=0 … Sat=6) for the given Date's UTC midnight.
 * Since `midnight` is already the UTC representation of midnight in the target tz,
 * adding 12 hours puts us safely in the middle of that day for DOW calculation.
 */
function getDayOfWeekFromDate(midnight: Date): number {
  const midday = new Date(midnight.getTime() + 12 * 3_600_000)
  return midday.getUTCDay()
}

// ---------------------------------------------------------------------------
// ISO-8601 fallback
// ---------------------------------------------------------------------------

function tryIso(text: string): ParseResult | null {
  // Attempt Date.parse — strict ISO-8601 strings parse reliably across engines.
  const ts = Date.parse(text)
  if (!isNaN(ts)) {
    const date = new Date(ts)
    return {
      date,
      interpretedText: `ISO-8601 입력: ${text}`,
    }
  }
  // Common date-only format without time (YYYY-MM-DD already handled above).
  // Some engines return NaN for "YYYY-MM-DD" without T; normalize manually.
  const dateOnly = /^(\d{4})-(\d{2})-(\d{2})$/.exec(text)
  if (dateOnly) {
    const [, y, mo, d] = dateOnly
    const date = new Date(Date.UTC(Number(y), Number(mo) - 1, Number(d)))
    return {
      date,
      interpretedText: `날짜: ${y}년 ${Number(mo)}월 ${Number(d)}일`,
    }
  }
  return null
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Parse a Korean or ISO-8601 date/time expression.
 *
 * @param text  - Korean natural language phrase or ISO-8601 string.
 * @param tz    - IANA timezone identifier (default "Asia/Seoul").
 * @returns     - { date: Date, interpretedText: string }
 * @throws      - Error when no pattern matches.
 */
export function parseKoreanDate(text: string, tz = 'Asia/Seoul'): ParseResult {
  const normalized = text.trim()
  if (!normalized) {
    throw new Error('Input text must not be empty')
  }

  // Validate timezone early
  try {
    Intl.DateTimeFormat(undefined, { timeZone: tz })
  } catch {
    throw new Error(`Invalid IANA timezone identifier: "${tz}"`)
  }

  const midnight = midnightInTz(tz)

  for (const entry of PATTERNS) {
    const match = normalized.match(entry.pattern)
    if (match) {
      return entry.resolve(match, midnight, tz)
    }
  }

  // ISO-8601 / standard date fallback
  const isoResult = tryIso(normalized)
  if (isoResult) return isoResult

  throw new Error(
    `날짜 표현을 인식할 수 없습니다: "${normalized}". ` +
      `지원 형식: "오늘", "내일", "다음 주 월요일", "2026년 4월 24일", "오후 3시", ISO-8601 등.`,
  )
}

// ---------------------------------------------------------------------------
// ISO-8601 formatter with timezone offset
// ---------------------------------------------------------------------------

/**
 * Format a Date as ISO-8601 with the named timezone offset (not UTC "Z").
 * Example: "2026-04-24T00:00:00+09:00"
 */
export function toIso8601WithTz(date: Date, tz: string): string {
  // Get offset at this specific moment (DST-aware)
  const offsetFmt = new Intl.DateTimeFormat('en-US', {
    timeZone: tz,
    timeZoneName: 'shortOffset',
  })
  const offsetStr =
    offsetFmt.formatToParts(date).find((p) => p.type === 'timeZoneName')?.value ?? 'UTC+0'
  const offsetMatch = offsetStr.match(/UTC([+-])(\d{1,2})(?::(\d{2}))?/)
  let offsetMinutes = 0
  let offsetSign = '+'
  if (offsetMatch) {
    offsetSign = offsetMatch[1] ?? '+'
    offsetMinutes = Number(offsetMatch[2]) * 60 + Number(offsetMatch[3] ?? 0)
  }
  const offsetHours = Math.floor(offsetMinutes / 60)
  const offsetMins = offsetMinutes % 60
  const offsetSuffix = `${offsetSign}${String(offsetHours).padStart(2, '0')}:${String(offsetMins).padStart(2, '0')}`

  // Get local date/time components in the target tz
  const localFmt = new Intl.DateTimeFormat('en-CA', {
    timeZone: tz,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  })
  const parts = localFmt.formatToParts(date)
  const get = (t: string) => parts.find((p) => p.type === t)?.value ?? '00'

  const year = get('year')
  const month = get('month')
  const day = get('day')
  let hour = get('hour')
  const minute = get('minute')
  const second = get('second')

  // Intl hour12:false can return "24" for midnight in some engines — normalize
  if (hour === '24') hour = '00'

  return `${year}-${month}-${day}T${hour}:${minute}:${second}${offsetSuffix}`
}
