// SPDX-License-Identifier: Apache-2.0
// Source: KOSMOS Epic H #1302 (035-onboarding-brand-port), task T021
// Contract: specs/035-onboarding-brand-port/contracts/onboarding-step-registry.md § 2, § 4 (write-consent-record)
// Contract: specs/035-onboarding-brand-port/contracts/memdir-consent-schema.md § 3 (Zod mirror)
//
// Citizen-facing PIPA § 26 수탁자 consent surface.
//
// On Enter: builds a PIPAConsentRecord, validates it via Zod, invokes the
// injected `writeRecord` side-effect, then calls `onAdvance()`.  On Escape:
// calls `onExit()` with no side-effect (FR-014 decline semantics).
//
// All keyboard handlers are IME-gated via `useKoreanIME()` per AG-04.

import React, { useCallback, useState } from 'react'
import { Box, Text, useInput } from 'ink'
import { useTheme } from '../../theme/provider'
import { useKoreanIME } from '../../hooks/useKoreanIME'
import {
  CURRENT_CONSENT_VERSION,
  PIPAConsentRecordSchema,
  type PIPAConsentRecord,
} from '../../memdir/consent'

// ---------------------------------------------------------------------------
// AAL gate → citizen-readable Korean label
// ---------------------------------------------------------------------------

const AAL_LABEL: Record<'AAL1' | 'AAL2' | 'AAL3', string> = {
  AAL1: '기본 인증 단계',
  AAL2: '표준 인증 단계',
  AAL3: '상위 인증 단계',
}

// ---------------------------------------------------------------------------
// Ministry recipient enumeration (citizen-visible list — FR-012)
// ---------------------------------------------------------------------------

const RECIPIENTS: readonly { code: string; label: string }[] = [
  { code: 'KOROAD', label: '한국도로공사' },
  { code: 'KMA', label: '기상청' },
  { code: 'HIRA', label: '건강보험심사평가원' },
  { code: 'NMC', label: '국립중앙의료원' },
]

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export type PIPAConsentStepProps = {
  onAdvance: () => void
  onExit: () => void
  /**
   * Session UUIDv7 stamped on the consent record.  When omitted a UUIDv4 is
   * synthesised via `crypto.randomUUID()` — acceptable for the test harness;
   * the integration path passes the session's real UUIDv7 from Spec 032.
   */
  sessionId?: string
  /** AAL gate at consent time; defaults to AAL1 (pre-identity-verification). */
  aalGate?: 'AAL1' | 'AAL2' | 'AAL3'
  /**
   * Side-effect that persists the validated record.  Default is a no-op so
   * the component compiles against the placeholder; `Onboarding.tsx` supplies
   * the real stdio-IPC-backed writer in T022.
   */
  writeRecord?: (record: PIPAConsentRecord) => Promise<void> | void
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function PIPAConsentStep({
  onAdvance,
  onExit,
  sessionId,
  aalGate = 'AAL1',
  writeRecord,
}: PIPAConsentStepProps): React.ReactElement {
  const theme = useTheme()
  const { isComposing } = useKoreanIME()
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState<boolean>(false)

  const submit = useCallback(async (): Promise<void> => {
    setError(null)
    setSubmitting(true)
    try {
      const record = {
        consent_version: CURRENT_CONSENT_VERSION,
        timestamp: new Date().toISOString(),
        aal_gate: aalGate,
        session_id: sessionId ?? crypto.randomUUID(),
        citizen_confirmed: true as const,
        schema_version: '1' as const,
      }
      const parsed = PIPAConsentRecordSchema.safeParse(record)
      if (!parsed.success) {
        setError(`동의 기록을 저장하지 못했습니다: ${parsed.error.message}`)
        return
      }
      if (writeRecord !== undefined) await writeRecord(parsed.data)
      onAdvance()
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err)
      setError(`동의 기록을 저장하지 못했습니다: ${message}`)
    } finally {
      setSubmitting(false)
    }
  }, [aalGate, sessionId, writeRecord, onAdvance])

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
    if (key.return) {
      void submit()
    }
  })

  return (
    <Box flexDirection="column" paddingX={1}>
      <Text bold color={theme.wordmark}>
        개인정보 활용 동의 ({CURRENT_CONSENT_VERSION})
      </Text>
      <Text color={theme.subtitle}>개인정보 보호법 § 26 수탁자 고지</Text>
      <Box marginTop={1} flexDirection="column">
        <Text color={theme.text}>
          KOSMOS는 아래 부처 공개 API를 호출해 답변을 돕는 수탁자입니다.
        </Text>
        <Text color={theme.text}>
          요청 내용과 응답 메타데이터는 세션 중에만 메모리에서 처리됩니다.
        </Text>
      </Box>
      <Box marginTop={1} flexDirection="column">
        <Text color={theme.subtitle}>데이터 수신 부처:</Text>
        {RECIPIENTS.map((r) => (
          <Text key={r.code} color={theme.text}>
            {'  • '}
            {r.label} ({r.code})
          </Text>
        ))}
      </Box>
      <Box marginTop={1}>
        <Text color={theme.subtitle}>
          현재 인증 단계: {AAL_LABEL[aalGate]} ({aalGate})
        </Text>
      </Box>
      {error !== null && (
        <Box marginTop={1}>
          <Text color={theme.error}>{error}</Text>
        </Box>
      )}
      <Box marginTop={1} flexDirection="column">
        <Text color={theme.kosmosCore}>
          {submitting
            ? '저장 중...'
            : 'Enter: 동의하고 계속  ·  Esc: 동의하지 않고 종료'}
        </Text>
      </Box>
    </Box>
  )
}
