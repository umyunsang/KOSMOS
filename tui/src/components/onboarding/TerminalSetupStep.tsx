// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — Onboarding step 5: Terminal setup (FR-001 step 5, FR-005, T044).
//
// Renders four independent accessibility toggles (screen_reader / large_font /
// high_contrast / reduced_motion) with a Shift+Tab keybinding hint. Toggle state
// changes are applied immediately (FR-005 / SC-011 ≤500 ms) and persisted via the
// injected writePreference callback (OnboardingFlow wires saveAccessibilityPreference).
//
// Reference: docs/wireframes/ui-a-onboarding.mjs § Step5_Terminal, § A.4 Accessibility
// IME gate: useKoreanIME per vision.md § Keyboard-shortcut migration

import React, { useCallback, useEffect, useState } from 'react'
import { Box, Text, useInput } from 'ink'
import { useTheme } from '../../theme/provider.js'
import { useKoreanIME } from '../../hooks/useKoreanIME.js'
import {
  ACCESSIBILITY_TOGGLE_KEYS,
  type AccessibilityPreferenceT,
  type AccessibilityToggleKey,
  freshAccessibilityPreference,
} from '../../schemas/ui-l2/a11y.js'
import { getUiL2I18n } from '../../i18n/uiL2.js'
import { emitSurfaceActivation } from '../../observability/surface.js'

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

export type TerminalSetupStepProps = {
  onAdvance: (pref: AccessibilityPreferenceT) => void
  onExit: () => void
  /** Initial preference values — used when re-running a single step in isolation. */
  initialPreference?: AccessibilityPreferenceT
  /** Side-effect that persists the preference (injected for testability). */
  writePreference?: (pref: AccessibilityPreferenceT) => Promise<void> | void
  locale?: 'ko' | 'en'
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function TerminalSetupStep({
  onAdvance,
  onExit,
  initialPreference,
  writePreference,
  locale,
}: TerminalSetupStepProps): React.ReactElement {
  const theme = useTheme()
  const { isComposing } = useKoreanIME()
  const i18n = getUiL2I18n(
    locale ?? ((process.env['KOSMOS_TUI_LOCALE'] as 'ko' | 'en') || 'ko'),
  )
  const isEn = (locale ?? process.env['KOSMOS_TUI_LOCALE']) === 'en'

  const [pref, setPref] = useState<AccessibilityPreferenceT>(
    initialPreference ?? freshAccessibilityPreference(),
  )
  const [selectedIdx, setSelectedIdx] = useState(0)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    emitSurfaceActivation('onboarding', { 'onboarding.step': 'terminal-setup' })
  }, [])

  // FR-005: persist immediately on toggle (SC-011 ≤500 ms)
  const toggleKey = useCallback(
    async (key: AccessibilityToggleKey): Promise<void> => {
      const updated: AccessibilityPreferenceT = {
        ...pref,
        [key]: !pref[key],
        updated_at: new Date().toISOString(),
      }
      setPref(updated)
      // Persist without blocking render — SC-011 ≤500 ms target
      if (writePreference !== undefined) {
        setSaving(true)
        try {
          await writePreference(updated)
        } catch (err) {
          const message = err instanceof Error ? err.message : String(err)
          setError(isEn ? `Failed to save: ${message}` : `저장 실패: ${message}`)
        } finally {
          setSaving(false)
        }
      }
    },
    [pref, writePreference, isEn],
  )

  const handleAdvance = useCallback(async (): Promise<void> => {
    // Persist final state on advance
    if (writePreference !== undefined) {
      setSaving(true)
      try {
        await writePreference(pref)
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err)
        setError(isEn ? `Failed to save: ${message}` : `저장 실패: ${message}`)
        setSaving(false)
        return
      }
      setSaving(false)
    }
    onAdvance(pref)
  }, [pref, writePreference, onAdvance, isEn])

  useInput((input, key) => {
    if (isComposing || saving) return
    if (key.ctrl && (input === 'c' || input === 'd')) {
      onExit()
      return
    }
    if (key.escape) {
      onExit()
      return
    }
    if (key.upArrow) {
      setSelectedIdx((i) => (i - 1 + ACCESSIBILITY_TOGGLE_KEYS.length) % ACCESSIBILITY_TOGGLE_KEYS.length)
      return
    }
    if (key.downArrow) {
      setSelectedIdx((i) => (i + 1) % ACCESSIBILITY_TOGGLE_KEYS.length)
      return
    }
    if (input === ' ') {
      const toggleKeyName = ACCESSIBILITY_TOGGLE_KEYS[selectedIdx]
      if (toggleKeyName !== undefined) {
        void toggleKey(toggleKeyName)
      }
      return
    }
    if (key.return) {
      void handleAdvance()
    }
  })

  return (
    <Box flexDirection="column" paddingX={1}>
      <Box flexDirection="column">
        <Text bold color={theme.wordmark}>
          {i18n.terminalSetupTitle}
        </Text>
        <StepProgressDots current={4} total={5} />
      </Box>

      {/* Accessibility toggles (FR-005) */}
      <Box marginTop={1} flexDirection="column">
        <Text color={theme.subtitle}>
          {isEn ? 'Accessibility options:' : '접근성 옵션:'}
        </Text>
        {ACCESSIBILITY_TOGGLE_KEYS.map((toggleKeyName, idx) => {
          const selected = idx === selectedIdx
          const enabled = pref[toggleKeyName]
          const glyph = enabled ? '[✓]' : '[ ]'
          const label = i18n.a11yToggleLabel(toggleKeyName)
          const prefix = selected ? '[선택] ▶ ' : '        '
          return (
            <Box key={toggleKeyName} flexDirection="row">
              <Text color={selected ? theme.kosmosCore : theme.subtle}>
                {prefix}
              </Text>
              <Text color={enabled ? theme.success : theme.subtle}>{glyph} </Text>
              <Text color={theme.text}>{label}</Text>
            </Box>
          )
        })}
      </Box>

      {/* Keybinding hint — Shift+Tab (FR-005, migration tree UI-C.5) */}
      <Box marginTop={1} flexDirection="column">
        <Text color={theme.subtitle}>
          {isEn ? 'Key bindings:' : '주요 키바인딩:'}
        </Text>
        <Box flexDirection="row">
          <Text color={theme.text}>{'  '}</Text>
          <Text color={theme.kosmosCore}>{'Shift+Tab'}</Text>
          <Text color={theme.subtle}>
            {'  '}{isEn ? '— cycle permission modes (default → acceptEdits → bypassPermissions)' : '— 권한 모드 전환 (default → acceptEdits → bypassPermissions)'}
          </Text>
        </Box>
        <Box flexDirection="row">
          <Text color={theme.text}>{'  '}</Text>
          <Text color={theme.kosmosCore}>{'Ctrl+C'}</Text>
          <Text color={theme.subtle}>
            {'  '}{isEn ? '— cancel / auto-deny current modal' : '— 작업 취소 / 현재 모달 자동 거부'}
          </Text>
        </Box>
        <Box flexDirection="row">
          <Text color={theme.text}>{'  '}</Text>
          <Text color={theme.kosmosCore}>{'Ctrl-O'}</Text>
          <Text color={theme.subtle}>
            {'  '}{isEn ? '— expand / collapse long response blocks' : '— 긴 응답 블록 펼치기/접기'}
          </Text>
        </Box>
      </Box>

      <Box marginTop={1}>
        <Text color={theme.subtle} dimColor>
          {isEn
            ? '↑↓ to move · Space to toggle · Enter to complete and start REPL'
            : '↑↓: 이동  ·  Space: 토글  ·  Enter: 완료 후 REPL 시작'}
        </Text>
      </Box>

      {saving && (
        <Box marginTop={1}>
          <Text color={theme.kosmosCore}>
            {isEn ? 'Saving preferences…' : '환경 설정 저장 중…'}
          </Text>
        </Box>
      )}

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
