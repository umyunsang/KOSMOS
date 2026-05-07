// SPDX-License-Identifier: Apache-2.0

type KeyName = 'C-o' | 'C-c' | 'Enter' | 'Down' | 'Tab'
type DecisionPath =
  | 'Enter'
  | 'Down+Enter'
  | 'Down+Down+Enter'
  | 'Tab+Text+Enter'
  | 'Tab+Text+Tab+Enter'
  | 'Down+Down+Tab+Text+Enter'
  | 'Down+Down+Tab+Text+Tab+Enter'

type Harness = {
  waitForPane(pattern: RegExp | string, deadlineSec?: number): Promise<void>
  waitForPaneSince(
    mark: number,
    pattern: RegExp | string,
    deadlineSec?: number,
  ): Promise<void>
  mark(): number
  plainSince(mark: number): string
  snapshot(label: string): string
  sendText(text: string): void
  sendEnter(): void
  sendKey(name: KeyName): void
}

async function sleep(ms: number): Promise<void> {
  await new Promise((resolve) => setTimeout(resolve, ms))
}

function env(name: string, fallback = ''): string {
  return process.env[name] ?? fallback
}

function regexFromEnv(name: string, fallback: RegExp): RegExp {
  const value = env(name)
  if (!value) return fallback
  return new RegExp(value, 'i')
}

function isDecisionPath(value: string): value is DecisionPath {
  return (
    value === 'Enter' ||
    value === 'Down+Enter' ||
    value === 'Down+Down+Enter' ||
    value === 'Tab+Text+Enter' ||
    value === 'Tab+Text+Tab+Enter' ||
    value === 'Down+Down+Tab+Text+Enter' ||
    value === 'Down+Down+Tab+Text+Tab+Enter'
  )
}

async function sendDecisionPath(
  h: Harness,
  value: DecisionPath,
  feedbackText: string,
): Promise<void> {
  if (
    value === 'Down+Enter' ||
    value === 'Down+Down+Enter' ||
    value === 'Down+Down+Tab+Text+Enter' ||
    value === 'Down+Down+Tab+Text+Tab+Enter'
  ) {
    h.sendKey('Down')
    await sleep(150)
  }
  if (
    value === 'Down+Down+Enter' ||
    value === 'Down+Down+Tab+Text+Enter' ||
    value === 'Down+Down+Tab+Text+Tab+Enter'
  ) {
    h.sendKey('Down')
    await sleep(150)
  }
  if (
    value === 'Tab+Text+Enter' ||
    value === 'Tab+Text+Tab+Enter' ||
    value === 'Down+Down+Tab+Text+Enter' ||
    value === 'Down+Down+Tab+Text+Tab+Enter'
  ) {
    h.sendKey('Tab')
    await sleep(300)
    if (feedbackText) {
      h.sendText(feedbackText)
      await sleep(300)
      if (
        value === 'Tab+Text+Tab+Enter' ||
        value === 'Down+Down+Tab+Text+Tab+Enter'
      ) {
        // PermissionPrompt follows the CC Select contract: Tab toggles the
        // feedback input mode. Return focus to the selected option before
        // Enter so the PTY path does not depend on text+CR coalescing.
        h.sendKey('Tab')
        await sleep(200)
      }
    }
  }
  h.sendKey('Enter')
}

export default async function run(h: Harness): Promise<void> {
  const prompt = env('KOSAX_REALUSE_PROMPT')
  if (!prompt) {
    throw new Error('KOSAX_REALUSE_PROMPT is required')
  }

  const ready = regexFromEnv('KOSAX_REALUSE_READY_REGEX', /KOSAX|❯/)
  const observe = regexFromEnv(
    'KOSAX_REALUSE_OBSERVE_REGEX',
    /resolve_location|lookup|verify|submit|subscribe|도구 결과|검색 오류|Error/i,
  )
  const expand = regexFromEnv(
    'KOSAX_REALUSE_EXPAND_REGEX',
    /Showing detailed transcript|outbound_traces|request_url|response_status|status_code|응답 envelope|response envelope|adapter_receipt|receipt_id|transaction_id|delegation_context|Error|검색 오류/i,
  )
  const result = regexFromEnv(
    'KOSAX_REALUSE_RESULT_REGEX',
    /⎿|도구 결과|검색 오류|Error|receipt|영수증|결과|완료/i,
  )
  const observeTimeoutSec = Number(env('KOSAX_REALUSE_OBSERVE_TIMEOUT_SEC', '180'))
  const expandTimeoutSec = Number(env('KOSAX_REALUSE_EXPAND_TIMEOUT_SEC', '30'))
  const resultTimeoutSec = Number(env('KOSAX_REALUSE_RESULT_TIMEOUT_SEC', '180'))
  const afterDecisionTimeoutSec = Number(
    env('KOSAX_REALUSE_AFTER_DECISION_TIMEOUT_SEC', '120'),
  )
  const decisionReadyTimeoutSec = Number(
    env('KOSAX_REALUSE_DECISION_READY_TIMEOUT_SEC', '180'),
  )
  const shouldExpand = env('KOSAX_REALUSE_EXPAND', '1') !== '0'
  const shouldWaitForResult = env(
    'KOSAX_REALUSE_WAIT_FOR_RESULT',
    shouldExpand ? '1' : '0',
  ) !== '0'
  const decisionPath = env('KOSAX_REALUSE_DECISION_PATH')
  const decisionFeedback = env('KOSAX_REALUSE_DECISION_FEEDBACK')
  const decisionReadyRaw = env('KOSAX_REALUSE_DECISION_READY_REGEX')
  const decisionReady = decisionReadyRaw ? new RegExp(decisionReadyRaw, 'i') : null
  const afterDecision = regexFromEnv(
    'KOSAX_REALUSE_AFTER_DECISION_REGEX',
    /receipt|영수증|denied|거부|완료|제출|결과|Error|검색 오류/i,
  )
  const finalRaw = env('KOSAX_REALUSE_FINAL_REGEX')
  const finalRegex = finalRaw ? new RegExp(finalRaw, 'i') : null
  const finalTimeoutSec = Number(env('KOSAX_REALUSE_FINAL_TIMEOUT_SEC', '180'))
  let finalSearchStartMark: number | null = null

  await h.waitForPane(ready, 60)
  h.snapshot('boot')

  h.sendText(prompt)
  const afterInputMark = h.mark()
  h.sendEnter()
  h.snapshot('input-submitted')

  await h.waitForPaneSince(afterInputMark, observe, observeTimeoutSec)
  if (!decisionPath && shouldWaitForResult) {
    const afterObserveMark = h.mark()
    result.lastIndex = 0
    if (!result.test(h.plainSince(afterInputMark))) {
      await h.waitForPaneSince(afterObserveMark, result, resultTimeoutSec)
    }
    finalSearchStartMark = h.mark()
  }
  h.snapshot('post-tool-flow')

  if (decisionPath) {
    if (!isDecisionPath(decisionPath)) {
      throw new Error(
        `Unsupported KOSAX_REALUSE_DECISION_PATH: ${decisionPath}`,
      )
    }
    const decisionGate =
      decisionReady ?? /허용하시겠습니까|권한 요청|Tab to amend|Esc to cancel/i
    if (decisionReady) {
      const decisionReadyMark = h.mark()
      decisionReady.lastIndex = 0
      if (!decisionReady.test(h.plainSince(afterInputMark))) {
        await h.waitForPaneSince(
          decisionReadyMark,
          decisionReady,
          decisionReadyTimeoutSec,
        )
      }
      h.snapshot('decision-ready')
    }
    const afterDecisionMark = h.mark()
    let permissionGateMark = afterDecisionMark
    await sendDecisionPath(h, decisionPath, decisionFeedback)
    h.snapshot(`decision-${decisionPath}`)
    permissionGateMark = h.mark()
    const afterDecisionDeadline = Date.now() + afterDecisionTimeoutSec * 1000
    let followupDecisionOrdinal = 2
    while (Date.now() < afterDecisionDeadline) {
      const resultText = h.plainSince(afterDecisionMark)
      afterDecision.lastIndex = 0
      if (afterDecision.test(resultText)) {
        break
      }
      const permissionText = h.plainSince(permissionGateMark)
      decisionGate.lastIndex = 0
      if (decisionGate.test(permissionText)) {
        h.snapshot(`decision-ready-${followupDecisionOrdinal}`)
        await sendDecisionPath(h, decisionPath, decisionFeedback)
        h.snapshot(`decision-${followupDecisionOrdinal}-${decisionPath}`)
        permissionGateMark = h.mark()
        followupDecisionOrdinal += 1
      }
      await sleep(120)
    }
    afterDecision.lastIndex = 0
    if (!afterDecision.test(h.plainSince(afterDecisionMark))) {
      await h.waitForPaneSince(afterDecisionMark, afterDecision, 0.1)
    }
    finalSearchStartMark = afterDecisionMark
    h.snapshot('after-decision')
  }

  if (finalRegex) {
    const finalMark = finalSearchStartMark ?? h.mark()
    finalRegex.lastIndex = 0
    if (!finalRegex.test(h.plainSince(finalMark))) {
      await h.waitForPaneSince(finalMark, finalRegex, finalTimeoutSec)
    }
    h.snapshot('final-answer-ready')
  }

  if (shouldExpand) {
    const afterExpandMark = h.mark()
    h.sendKey('C-o')
    await h.waitForPaneSince(afterExpandMark, expand, expandTimeoutSec)
    h.snapshot('expanded-tool-detail')
  }

  h.sendKey('C-c')
  h.sendKey('C-c')
}
