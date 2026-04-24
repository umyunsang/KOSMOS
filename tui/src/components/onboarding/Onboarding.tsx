// Source: .references/claude-code-sourcemap/restored-src/src/components/Onboarding.tsx (Claude Code 2.1.88, research-use)
// KOSMOS REWRITE per Epic H #1302 (035-onboarding-brand-port) — ADR-006 A-9
//
// Three-step linear citizen onboarding state machine:
//   splash → pipa-consent → ministry-scope-ack → done
//
// PIPA consent step and ministry-scope step mount as placeholder `<Text>`
// components; T022 and T030 replace them with real step implementations
// (PIPAConsentStep / MinistryScopeStep) that trigger memdir writes via
// stdio IPC.
//
// Contract: specs/035-onboarding-brand-port/contracts/onboarding-step-registry.md § 1–§ 3
// IME gate:  specs/035-onboarding-brand-port/contracts/onboarding-step-registry.md § 2

import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { Box, Text, useApp, useInput } from 'ink'
import { useTheme } from '../../theme/provider'
import { useKoreanIME } from '../../hooks/useKoreanIME'
import { LogoV2 } from '../LogoV2/LogoV2'
import { PIPAConsentStep } from './PIPAConsentStep'
import { MinistryScopeStep } from './MinistryScopeStep'
import { writeConsentRecord, writeScopeRecord } from '../../memdir/io'
import type { PIPAConsentRecord } from '../../memdir/consent'
import type { MinistryScopeAcknowledgment } from '../../memdir/ministry-scope'

// Fast-path auto-advance budget (SC-012: returning citizen ≤ 3 s launch-to-main).
const FAST_PATH_AUTO_ADVANCE_MS = 3000

// ---------------------------------------------------------------------------
// Version constants (bumping either invalidates all prior memdir records).
// ---------------------------------------------------------------------------

export const CURRENT_CONSENT_VERSION = 'v1'
export const CURRENT_SCOPE_VERSION = 'v1'

// ---------------------------------------------------------------------------
// Step registry
// ---------------------------------------------------------------------------

export type StepId = 'splash' | 'pipa-consent' | 'ministry-scope-ack' | 'done'

export type MemdirUserState = {
  consentRecord?: { consent_version: string }
  scopeRecord?: { scope_version: string }
}

export type StepComponentProps = {
  onAdvance: () => void
  onExit: () => void
  sessionId: string
  writeConsentRecord: (record: PIPAConsentRecord) => Promise<void> | void
  writeScopeRecord: (
    record: MinistryScopeAcknowledgment,
  ) => Promise<void> | void
}

export type OnboardingStep = {
  stepId: StepId
  component: React.FC<StepComponentProps>
  advanceCondition: () => boolean
  skipCondition: (memdir: MemdirUserState) => boolean
  exitSideEffect: 'write-consent-record' | 'write-scope-record' | 'none'
}

/**
 * Splash step wrapper — renders `<LogoV2 />` then a citizen-visible
 * instruction hint below.  The hint satisfies WCAG 3.3.2 (labels /
 * instructions) and is the terminal-stream equivalent of a "visible focus"
 * cue for keyboard-only + screen-reader users.
 */
const SplashStep: React.FC<StepComponentProps> = () => {
  const theme = useTheme()
  return (
    <Box flexDirection="column" alignItems="center">
      <LogoV2 />
      <Box marginTop={1}>
        <Text color={theme.kosmosCore}>
          계속하려면 Enter  ·  종료하려면 Esc
        </Text>
      </Box>
    </Box>
  )
}

const PIPAStepBound: React.FC<StepComponentProps> = ({
  onAdvance,
  onExit,
  sessionId,
  writeConsentRecord,
}) => {
  return (
    <PIPAConsentStep
      onAdvance={onAdvance}
      onExit={onExit}
      sessionId={sessionId}
      writeRecord={writeConsentRecord}
    />
  )
}

const MinistryScopeStepBound: React.FC<StepComponentProps> = ({
  onAdvance,
  onExit,
  sessionId,
  writeScopeRecord,
}) => {
  return (
    <MinistryScopeStep
      onAdvance={onAdvance}
      onExit={onExit}
      sessionId={sessionId}
      writeRecord={writeScopeRecord}
    />
  )
}

const DoneStep: React.FC<StepComponentProps> = () => {
  return null
}

export const STEPS: readonly OnboardingStep[] = [
  {
    stepId: 'splash',
    component: SplashStep,
    advanceCondition: () => true,
    skipCondition: () => false,
    exitSideEffect: 'none',
  },
  {
    stepId: 'pipa-consent',
    component: PIPAStepBound,
    advanceCondition: () => true,
    skipCondition: (memdir) =>
      memdir.consentRecord?.consent_version === CURRENT_CONSENT_VERSION,
    exitSideEffect: 'write-consent-record',
  },
  {
    stepId: 'ministry-scope-ack',
    component: MinistryScopeStepBound,
    advanceCondition: () => true,
    // Skip ONLY when BOTH records are fresh.  Stale consent forces the
    // scope step to render regardless of its own freshness — ministry
    // opt-ins from a superseded consent version must be re-acknowledged
    // (research R-6, Codex review 2026-04-20).
    skipCondition: (memdir) =>
      memdir.consentRecord?.consent_version === CURRENT_CONSENT_VERSION &&
      memdir.scopeRecord?.scope_version === CURRENT_SCOPE_VERSION,
    exitSideEffect: 'write-scope-record',
  },
  {
    stepId: 'done',
    component: DoneStep,
    advanceCondition: () => true,
    skipCondition: () => false,
    exitSideEffect: 'none',
  },
]

// ---------------------------------------------------------------------------
// Default consent-write side-effect — direct-filesystem atomic write.
//
// Writes the record to `~/.kosmos/memdir/user/{consent,ministry-scope}/`
// via `tui/src/memdir/io.ts` using the tmp + fsync + rename pattern.  The
// Python backend reads the same directory through `latest_consent()` /
// `latest_scope()`; both producers share POSIX fsync ordering for
// durability.  A best-effort diagnostic envelope is also emitted on
// stderr so log aggregators see the event trail — actionable state lives
// on disk, not on stderr.  Tests override by passing `onWriteConsentRecord`.
// ---------------------------------------------------------------------------

function defaultWriteConsentRecord(record: PIPAConsentRecord): void {
  writeConsentRecord(record)
  const envelope = {
    event: 'onboarding.write_consent_record',
    session_id: record.session_id,
    ts: new Date().toISOString(),
  }
  process.stderr.write(`${JSON.stringify(envelope)}\n`)
}

function defaultWriteScopeRecord(
  record: MinistryScopeAcknowledgment,
): void {
  writeScopeRecord(record)
  const envelope = {
    event: 'onboarding.write_scope_record',
    session_id: record.session_id,
    ts: new Date().toISOString(),
  }
  process.stderr.write(`${JSON.stringify(envelope)}\n`)
}

// ---------------------------------------------------------------------------
// Session-start resolver (per contract § 3)
//
// Return values:
//   - both records fresh                            → 'splash' (3 s fast-path)
//   - consent fresh, scope stale                    → 'ministry-scope-ack'
//   - consent stale (or absent)                     → 'splash' (full flow; the
//     step machine enters splash → pipa-consent → ministry-scope-ack → done)
// ---------------------------------------------------------------------------

export function resolveStartStep(memdir: MemdirUserState): StepId {
  const consentFresh =
    memdir.consentRecord?.consent_version === CURRENT_CONSENT_VERSION
  const scopeFresh =
    memdir.scopeRecord?.scope_version === CURRENT_SCOPE_VERSION
  if (consentFresh && scopeFresh) return 'splash'
  if (consentFresh && !scopeFresh) return 'ministry-scope-ack'
  return 'splash'
}

// ---------------------------------------------------------------------------
// OTEL span emission (Spec 021)
//
// The Python backend owns the OTEL SDK; the TUI emits a structured JSONL
// event on stderr that the Python-side span exporter picks up.  Keeping
// the emission shape stable here ensures T022 / T030 can layer in
// consent / scope record details without disturbing the event schema.
// ---------------------------------------------------------------------------

type OnboardingSpanKind = 'enter' | 'advance' | 'exit'

export function emitOnboardingSpan(
  stepId: StepId,
  kind: OnboardingSpanKind,
): void {
  const envelope = {
    span: 'kosmos.onboarding.step',
    step: stepId,
    kind,
    ts: new Date().toISOString(),
  }
  process.stderr.write(`${JSON.stringify(envelope)}\n`)
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export type OnboardingProps = {
  memdir?: MemdirUserState
  startStep?: StepId
  onComplete?: () => void
  /** Session UUIDv7 stamped on every written record.  Defaults to a fresh UUIDv4. */
  sessionId?: string
  /** Test override for the consent-write side effect. */
  onWriteConsentRecord?: (record: PIPAConsentRecord) => Promise<void> | void
  /** Test override for the ministry-scope-write side effect. */
  onWriteScopeRecord?: (
    record: MinistryScopeAcknowledgment,
  ) => Promise<void> | void
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function Onboarding({
  memdir = {},
  startStep,
  onComplete,
  sessionId,
  onWriteConsentRecord,
  onWriteScopeRecord,
}: OnboardingProps): React.ReactElement | null {
  const { exit } = useApp()
  const { isComposing } = useKoreanIME()
  const initial: StepId = startStep ?? resolveStartStep(memdir)
  const initialIndex = STEPS.findIndex((s) => s.stepId === initial)
  const [currentIndex, setCurrentIndex] = useState<number>(
    initialIndex >= 0 ? initialIndex : 0,
  )

  const current = STEPS[currentIndex]
  const resolvedSessionId = useMemo<string>(
    () => sessionId ?? crypto.randomUUID(),
    [sessionId],
  )
  const writeConsentRecord = onWriteConsentRecord ?? defaultWriteConsentRecord
  const writeScopeRecord = onWriteScopeRecord ?? defaultWriteScopeRecord

  useEffect(() => {
    if (current !== undefined) emitOnboardingSpan(current.stepId, 'enter')
  }, [current])

  // Reaching `done` is the terminal signal.
  //
  // When the caller wires `onComplete` (embedded-gate mode — the TUI
  // entrypoint swaps <Onboarding> for <AppInner> via its own state flag),
  // we MUST NOT call Ink `exit()` — that would tear down the whole render
  // tree before the parent can mount the main UI.
  //
  // When no `onComplete` is provided (standalone mode — e.g. demo or
  // isolated test harness), falling back to `exit()` is the sensible
  // default so the process doesn't sit on the blank `DoneStep`.
  useEffect(() => {
    if (current?.stepId !== 'done') return
    if (onComplete !== undefined) {
      onComplete()
      return
    }
    exit()
  }, [current, exit, onComplete])

  const advance = useCallback((): void => {
    if (current === undefined) return
    emitOnboardingSpan(current.stepId, 'advance')
    // Walk forward honouring `skipCondition(memdir)` so returning citizens
    // skip steps whose records are already fresh (fast-path contract § 3).
    let nextIndex = currentIndex + 1
    while (
      nextIndex < STEPS.length &&
      STEPS[nextIndex]?.skipCondition(memdir) === true
    ) {
      nextIndex += 1
    }
    if (nextIndex >= STEPS.length) {
      // Same embedded-vs-standalone rule as the done-step effect above:
      // the embedded-gate flow relies on the parent to swap components
      // via `onComplete`, so `exit()` must only fire in standalone mode.
      if (onComplete !== undefined) onComplete()
      else exit()
      return
    }
    setCurrentIndex(nextIndex)
  }, [currentIndex, current, exit, memdir, onComplete])

  // Fast-path auto-advance (SC-012): when the returning-citizen resolver
  // lands directly on the splash step AND both memdir records are fresh,
  // auto-advance after FAST_PATH_AUTO_ADVANCE_MS.  This closes the keyboard
  // loop for citizens who are not watching the screen when they relaunch.
  const consentFresh =
    memdir.consentRecord?.consent_version === CURRENT_CONSENT_VERSION
  const scopeFresh =
    memdir.scopeRecord?.scope_version === CURRENT_SCOPE_VERSION
  const fastPath =
    current?.stepId === 'splash' && consentFresh && scopeFresh
  useEffect(() => {
    if (!fastPath) return
    const handle = setTimeout(() => {
      if (current?.advanceCondition() === true) advance()
    }, FAST_PATH_AUTO_ADVANCE_MS)
    return () => clearTimeout(handle)
  }, [fastPath, current, advance])

  const exitSession = useCallback((): void => {
    if (current !== undefined) emitOnboardingSpan(current.stepId, 'exit')
    exit()
  }, [current, exit])

  // Step-level keybinding only for the splash screen (step 0) which has no
  // internal `useInput` — every other step owns its own input handling so
  // we must not double-register or we'd steal IME-safe Enter handling.
  const isSplash = current?.stepId === 'splash'
  useInput(
    (input, key) => {
      if (isComposing) return
      if (key.ctrl && (input === 'c' || input === 'd')) {
        exitSession()
        return
      }
      if (key.escape) {
        exitSession()
        return
      }
      if (key.return) {
        if (current?.advanceCondition() === true) advance()
      }
    },
    { isActive: isSplash },
  )

  if (current === undefined) return null

  const StepComponent = current.component
  return (
    <Box flexDirection="column">
      <StepComponent
        onAdvance={advance}
        onExit={exitSession}
        sessionId={resolvedSessionId}
        writeConsentRecord={writeConsentRecord}
        writeScopeRecord={writeScopeRecord}
      />
    </Box>
  )
}
