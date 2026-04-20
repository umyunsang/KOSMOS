// SPDX-License-Identifier: Apache-2.0
// Source: KOSMOS Epic H #1302 (035-onboarding-brand-port), task T029
// Contract: specs/035-onboarding-brand-port/contracts/onboarding-step-registry.md § 2, § 4
// Contract: specs/035-onboarding-brand-port/contracts/memdir-ministry-scope-schema.md § 3
//
// 4 toggle rows (KOROAD / KMA / HIRA / NMC) with ↑↓ selection, Space to
// toggle, Enter to confirm (builds + validates + writes record via injected
// side-effect), Escape to exit.  All keyboard handlers IME-gated.

import React, { useCallback, useMemo, useState } from 'react'
import { Box, Text, useInput } from 'ink'
import { useTheme } from '../../theme/provider'
import type { ThemeToken } from '../../theme/tokens'
import { useKoreanIME } from '../../hooks/useKoreanIME'
import {
  CURRENT_SCOPE_VERSION,
  MINISTRY_CODES,
  MinistryScopeAcknowledgmentSchema,
  type MinistryCode,
  type MinistryScopeAcknowledgment,
} from '../../memdir/ministry-scope'

// ---------------------------------------------------------------------------
// Ministry table (order fixed; accent-token binding matches brand-token-surface § 2)
// ---------------------------------------------------------------------------

type MinistryRow = {
  code: MinistryCode
  displayName: string
  description: string
  tokenKey: keyof ThemeToken
}

const ROWS: readonly MinistryRow[] = [
  {
    code: 'KOROAD',
    displayName: '한국도로공사',
    description: '교통사고 잦은 곳, 도로 안전 정보',
    tokenKey: 'agentSatelliteKoroad',
  },
  {
    code: 'KMA',
    displayName: '기상청',
    description: '기상 예보, 특보, 실황',
    tokenKey: 'agentSatelliteKma',
  },
  {
    code: 'HIRA',
    displayName: '건강보험심사평가원',
    description: '병원·의원 검색, 진료과목 조회',
    tokenKey: 'agentSatelliteHira',
  },
  {
    code: 'NMC',
    displayName: '국립중앙의료원',
    description: '응급실 실시간 가용 현황',
    tokenKey: 'agentSatelliteNmc',
  },
]

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export type MinistryScopeStepProps = {
  onAdvance: () => void
  onExit: () => void
  sessionId?: string
  /** Defaults to ALL FOUR opted-in (the "all-on" aggregate affordance). */
  initialOptIns?: Partial<Record<MinistryCode, boolean>>
  writeRecord?: (
    record: MinistryScopeAcknowledgment,
  ) => Promise<void> | void
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function MinistryScopeStep({
  onAdvance,
  onExit,
  sessionId,
  initialOptIns,
  writeRecord,
}: MinistryScopeStepProps): React.ReactElement {
  const theme = useTheme()
  const { isComposing } = useKoreanIME()

  const initial = useMemo<Record<MinistryCode, boolean>>(() => {
    const map: Record<MinistryCode, boolean> = {
      KOROAD: true,
      KMA: true,
      HIRA: true,
      NMC: true,
    }
    if (initialOptIns !== undefined) {
      for (const code of MINISTRY_CODES) {
        const override = initialOptIns[code]
        if (override !== undefined) map[code] = override
      }
    }
    return map
  }, [initialOptIns])

  const [optIns, setOptIns] = useState<Record<MinistryCode, boolean>>(initial)
  const [selectedIdx, setSelectedIdx] = useState<number>(0)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState<boolean>(false)

  const submit = useCallback(async (): Promise<void> => {
    setError(null)
    setSubmitting(true)
    try {
      const record = {
        scope_version: CURRENT_SCOPE_VERSION,
        timestamp: new Date().toISOString(),
        session_id: sessionId ?? crypto.randomUUID(),
        ministries: MINISTRY_CODES.map((code) => ({
          ministry_code: code,
          opt_in: optIns[code],
        })),
        schema_version: '1' as const,
      }
      const parsed = MinistryScopeAcknowledgmentSchema.safeParse(record)
      if (!parsed.success) {
        setError(`동의 범위를 저장하지 못했습니다: ${parsed.error.message}`)
        return
      }
      if (writeRecord !== undefined) await writeRecord(parsed.data)
      onAdvance()
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err)
      setError(`동의 범위를 저장하지 못했습니다: ${message}`)
    } finally {
      setSubmitting(false)
    }
  }, [optIns, sessionId, writeRecord, onAdvance])

  useInput((input, key) => {
    if (isComposing || submitting) return
    if (key.ctrl && (input === 'c' || input === 'd')) {
      onExit()
      return
    }
    if (key.escape) {
      onExit()
      return
    }
    if (key.upArrow) {
      setSelectedIdx((i) => (i - 1 + ROWS.length) % ROWS.length)
      return
    }
    if (key.downArrow) {
      setSelectedIdx((i) => (i + 1) % ROWS.length)
      return
    }
    if (input === ' ') {
      const row = ROWS[selectedIdx]
      if (row !== undefined) {
        setOptIns((prev) => ({ ...prev, [row.code]: !prev[row.code] }))
      }
      return
    }
    if (key.return) {
      void submit()
    }
  })

  return (
    <Box flexDirection="column" paddingX={1}>
      <Text bold color={theme.wordmark}>
        부처 API 사용 동의 ({CURRENT_SCOPE_VERSION})
      </Text>
      <Text color={theme.subtitle}>
        KOSMOS가 호출할 수 있는 공개 API 부처를 선택하세요.
      </Text>
      <Box marginTop={1} flexDirection="column">
        {ROWS.map((row, idx) => {
          const selected = idx === selectedIdx
          const optIn = optIns[row.code]
          const glyph = optIn ? '☑' : '☐'
          // Text-prefix "[선택] " carries the focus state in the text
          // stream for screen readers that cannot associate the `▶` glyph
          // with focus semantics.  Visual cue `▶` is retained for sighted
          // users; the two together form a redundant encoding.
          const prefix = selected ? '[선택] ▶ ' : '        '
          const accent = theme[row.tokenKey]
          const accentColor =
            typeof accent === 'string' ? accent : theme.text
          return (
            <Box key={row.code} flexDirection="row">
              <Text color={selected ? theme.kosmosCore : theme.subtle}>
                {prefix}
              </Text>
              <Text color={accentColor}>{glyph} </Text>
              <Text color={theme.text}>
                {row.displayName} ({row.code}) — {row.description}
              </Text>
            </Box>
          )
        })}
      </Box>
      <Box marginTop={1}>
        <Text color={theme.kosmosCore}>
          {submitting
            ? '저장 중...'
            : '↑↓: 이동  ·  Space: 토글  ·  Enter: 확인하고 계속  ·  Esc: 종료'}
        </Text>
      </Box>
      {/* Error region is the last rendered child — same a11y rationale as */}
      {/* PIPAConsentStep: screen readers append on redraw and land on the */}
      {/* last line.  `오류: ` prefix distinguishes from status text.       */}
      {error !== null && (
        <Box marginTop={1}>
          <Text color={theme.error}>오류: {error}</Text>
        </Box>
      )}
    </Box>
  )
}
