// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — Onboarding step 3: PIPA consent (FR-001 step 3, FR-006, T042).
//
// 5-step flow version. Surfaces the PIPA §26 trustee responsibility notice
// with visual + textual clarity before accepting citizen consent (FR-006).
// On Y/Enter: writes consent record and advances. On N/Esc: exits.
//
// The existing tui/src/components/onboarding/PIPAConsentStep.tsx belongs to
// the Spec 035 3-step flow (splash → pipa-consent → ministry-scope-ack).
// This file is the 5-step flow's step 3 with full FR-006 trustee notice box.
//
// Reference: cc:components/Onboarding.tsx (consent step pattern)
//            docs/wireframes/ui-a-onboarding.mjs § Step3_PIPA
// IME gate: useKoreanIME per vision.md § Keyboard-shortcut migration

import React, { useCallback, useEffect, useState } from 'react'
import { Box, Text, useInput } from 'ink'
import { useTheme } from '../../theme/provider.js'
import { useKoreanIME } from '../../hooks/useKoreanIME.js'
import { getUiL2I18n } from '../../i18n/uiL2.js'
import { emitSurfaceActivation } from '../../observability/surface.js'

// ---------------------------------------------------------------------------
// Data processing categories disclosed under PIPA §26
// ---------------------------------------------------------------------------

const DATA_CATEGORIES: readonly { key: string; descKo: string; descEn: string }[] = [
  {
    key: 'query',
    descKo: '질의 원문 (세션 종료 시 자동 삭제 옵션)',
    descEn: 'Query text (auto-delete on session end option)',
  },
  {
    key: 'location',
    descKo: '위치/주소 (resolve_location 모드 요청 시만)',
    descEn: 'Location/address (only when resolve_location is invoked)',
  },
  {
    key: 'submission',
    descKo: '부처 제출 서식 (submit primitive 호출 시)',
    descEn: 'Ministry submission forms (only when submit primitive is invoked)',
  },
]

const TRUSTEE_MINISTRIES: readonly { code: string; labelKo: string; labelEn: string }[] = [
  { code: 'KOROAD', labelKo: '도로교통공단', labelEn: 'Korea Road Transport Authority' },
  { code: 'KMA', labelKo: '기상청', labelEn: 'Korea Meteorological Administration' },
  { code: 'HIRA', labelKo: '건강보험심사평가원', labelEn: 'Health Insurance Review & Assessment' },
  { code: 'NMC', labelKo: '국립중앙의료원', labelEn: 'National Medical Center' },
]

// ---------------------------------------------------------------------------
// Step header
// ---------------------------------------------------------------------------

function StepProgressDots({ current, total }: { current: number; total: number }) {
  const theme = useTheme()
  const dots = Array.from({ length: total }, (_, i) =>
    i < current ? '●' : i === current ? '◉' : '○',
  ).join(' ')
  return (
    <Text color={theme.subtle}>
      {dots}{'     '}{current + 1} / {total}
    </Text>
  )
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export type PipaConsentStepProps = {
  onAdvance: () => void
  onExit: () => void
  /** Session UUIDv7 stamped on the consent record. Defaults to crypto.randomUUID(). */
  sessionId?: string
  /** Side-effect that persists the consent record (injected for testability). */
  writeRecord?: (sessionId: string, timestamp: string) => Promise<void> | void
  locale?: 'ko' | 'en'
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function PipaConsentStep({
  onAdvance,
  onExit,
  sessionId,
  writeRecord,
  locale,
}: PipaConsentStepProps): React.ReactElement {
  const theme = useTheme()
  const { isComposing } = useKoreanIME()
  const i18n = getUiL2I18n(
    locale ?? ((process.env['KOSMOS_TUI_LOCALE'] as 'ko' | 'en') || 'ko'),
  )
  const isEn = (locale ?? process.env['KOSMOS_TUI_LOCALE']) === 'en'

  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    emitSurfaceActivation('onboarding', { 'onboarding.step': 'pipa-consent' })
  }, [])

  const submit = useCallback(async (): Promise<void> => {
    setError(null)
    setSubmitting(true)
    try {
      const sid = sessionId ?? crypto.randomUUID()
      const ts = new Date().toISOString()
      if (writeRecord !== undefined) {
        await writeRecord(sid, ts)
      }
      onAdvance()
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err)
      setError(
        isEn
          ? `Failed to save consent record: ${message}`
          : `동의 기록을 저장하지 못했습니다: ${message}`,
      )
    } finally {
      setSubmitting(false)
    }
  }, [sessionId, writeRecord, onAdvance, isEn])

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
    if (key.return || input === 'y' || input === 'Y') {
      void submit()
      return
    }
    if (input === 'n' || input === 'N') {
      onExit()
    }
  })

  return (
    <Box flexDirection="column" paddingX={1}>
      <Box flexDirection="column">
        <Text bold color={theme.wordmark}>
          {i18n.pipaConsentTitle}
        </Text>
        <StepProgressDots current={2} total={5} />
      </Box>

      {/* FR-006: clear visual + textual PIPA §26 trustee notice box */}
      <Box marginTop={1} borderStyle="round" borderColor={theme.warning} flexDirection="column" paddingX={1}>
        <Text bold color={theme.warning}>
          ⚠ {isEn ? 'Trustee Responsibility Notice · PIPA §26' : '수탁자 책임 안내 · 개인정보 보호법 §26'}
        </Text>
        <Box marginTop={1} flexDirection="column">
          <Text color={theme.text}>{i18n.pipaTrusteeNotice}</Text>
        </Box>

        <Box marginTop={1} flexDirection="column">
          <Text color={theme.subtitle}>
            {isEn ? 'Data categories processed:' : '처리 정보:'}
          </Text>
          {DATA_CATEGORIES.map((cat) => (
            <Text key={cat.key} color={theme.text}>
              {'  · '}{isEn ? cat.descEn : cat.descKo}
            </Text>
          ))}
        </Box>

        <Box marginTop={1} flexDirection="column">
          <Text color={theme.subtitle}>
            {isEn ? 'Trustee recipients (public APIs only):' : '데이터 수신 부처 (공개 API 전용):'}
          </Text>
          {TRUSTEE_MINISTRIES.map((m) => (
            <Text key={m.code} color={theme.text}>
              {'  · '}{isEn ? m.labelEn : m.labelKo}{' ('}{m.code}{')'}
            </Text>
          ))}
        </Box>

        <Box marginTop={1}>
          <Text color={theme.subtle} dimColor>
            {isEn
              ? 'Audit ledger and OTEL spans are preserved even after consent revocation (FR-007).'
              : '동의 철회 후에도 audit ledger와 OTEL span은 삭제되지 않습니다 (FR-007).'}
          </Text>
        </Box>
      </Box>

      <Box marginTop={1}>
        <Text color={theme.text}>{i18n.pipaConsentBody}</Text>
      </Box>

      <Box marginTop={1}>
        {submitting ? (
          <Text color={theme.kosmosCore}>
            {isEn ? 'Saving consent record…' : '동의 기록 저장 중…'}
          </Text>
        ) : (
          <Text color={theme.kosmosCore}>
            [Y/Enter] {isEn ? 'Agree and continue' : '동의하고 계속'}
            {'  ·  '}
            [N/Esc] {isEn ? 'Decline and exit' : '동의하지 않고 종료'}
          </Text>
        )}
      </Box>

      {/* Error — rendered last for screen-reader accessibility (stream-append) */}
      {error !== null && (
        <Box marginTop={1}>
          <Text color={theme.error}>
            {isEn ? 'Error: ' : '오류: '}{error}
          </Text>
        </Box>
      )}
    </Box>
  )
}

// KOSMOS migration alias: legacy test naming retained for compatibility.
// Refs: Spec 1637 P6 T032 — onboarding test contract preserved.
export const PIPAConsentStep = PipaConsentStep
