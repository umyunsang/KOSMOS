// [P0 reconstructed · Pass 3 · Services API error helpers]
// Reference: consumer callsites in query.ts (line 43, 804, 1073) +
//            services/api/claude.ts + services/api/withRetry.ts.
// Original CC 2.1.88 source for this module was not captured in the
// sourcemap reconstruction; all exports below are reconstructed from
// consumer import patterns and the well-known Claude API error taxonomy.
/* eslint-disable @typescript-eslint/no-explicit-any */

// ───── Error message string constants ─────────────────────────────────────
// Matching exact Anthropic API error prefixes so classifier heuristics work.
export const API_ERROR_MESSAGE_PREFIX = 'API Error:'
export const API_TIMEOUT_ERROR_MESSAGE = 'API request timed out'
export const CREDIT_BALANCE_TOO_LOW_ERROR_MESSAGE = 'Credit balance is too low'
export const CUSTOM_OFF_SWITCH_MESSAGE = 'Custom off switch active'
export const INVALID_API_KEY_ERROR_MESSAGE = 'Invalid API key'
export const INVALID_API_KEY_ERROR_MESSAGE_EXTERNAL =
  'Invalid API key · please set ANTHROPIC_API_KEY or run `claude login`'
export const ORG_DISABLED_ERROR_MESSAGE_ENV_KEY =
  'Organization disabled for this API key'
export const ORG_DISABLED_ERROR_MESSAGE_ENV_KEY_WITH_OAUTH =
  'Organization disabled — run `claude login` to refresh credentials'
export const PROMPT_TOO_LONG_ERROR_MESSAGE =
  'prompt is too long: '
export const REPEATED_529_ERROR_MESSAGE =
  'API returned 529 Overloaded repeatedly'
export const TOKEN_REVOKED_ERROR_MESSAGE = 'Token has been revoked'

// ───── Classifier helpers ─────────────────────────────────────────────────

/** Coarse categorisation used by the retry matrix. */
export function categorizeRetryableAPIError(
  err: unknown,
): 'retryable' | 'non_retryable' | 'unknown' {
  const msg = extractErrorMessage(err)
  if (!msg) return 'unknown'
  if (msg.includes('529') || msg.includes('Overloaded')) return 'retryable'
  if (msg.includes('503') || msg.includes('timeout')) return 'retryable'
  if (msg.includes(INVALID_API_KEY_ERROR_MESSAGE)) return 'non_retryable'
  if (msg.includes(TOKEN_REVOKED_ERROR_MESSAGE)) return 'non_retryable'
  if (msg.includes(CREDIT_BALANCE_TOO_LOW_ERROR_MESSAGE)) return 'non_retryable'
  return 'unknown'
}

/** Fine-grained classification used for telemetry + UI dialogs. */
export function classifyAPIError(
  err: unknown,
):
  | 'invalid_api_key'
  | 'token_revoked'
  | 'credit_balance_too_low'
  | 'org_disabled'
  | 'prompt_too_long'
  | 'timeout'
  | 'overloaded'
  | 'refusal'
  | 'unknown' {
  const msg = extractErrorMessage(err)
  if (!msg) return 'unknown'
  if (msg.includes(INVALID_API_KEY_ERROR_MESSAGE)) return 'invalid_api_key'
  if (msg.includes(TOKEN_REVOKED_ERROR_MESSAGE)) return 'token_revoked'
  if (msg.includes(CREDIT_BALANCE_TOO_LOW_ERROR_MESSAGE))
    return 'credit_balance_too_low'
  if (
    msg.includes(ORG_DISABLED_ERROR_MESSAGE_ENV_KEY) ||
    msg.includes(ORG_DISABLED_ERROR_MESSAGE_ENV_KEY_WITH_OAUTH)
  )
    return 'org_disabled'
  if (msg.includes('prompt is too long')) return 'prompt_too_long'
  if (msg.includes('timed out') || msg.includes('timeout')) return 'timeout'
  if (msg.includes('Overloaded') || msg.includes('529')) return 'overloaded'
  return 'unknown'
}

export function startsWithApiErrorPrefix(msg: unknown): boolean {
  return typeof msg === 'string' && msg.startsWith(API_ERROR_MESSAGE_PREFIX)
}

export function isPromptTooLongMessage(msg: unknown): boolean {
  return typeof msg === 'string' && msg.includes('prompt is too long')
}

/**
 * Parse `prompt is too long: N tokens > M` into {current, max}.
 * Returns empty object if parse fails.
 */
export function parsePromptTooLongTokenCounts(
  msg: unknown,
): { current?: number; max?: number } {
  if (typeof msg !== 'string') return {}
  const match = msg.match(/(\d+)\s*tokens?\s*>\s*(\d+)/)
  if (!match) return {}
  return {
    current: Number(match[1]),
    max: Number(match[2]),
  }
}

export function getPromptTooLongTokenGap(msg: unknown): number | null {
  const { current, max } = parsePromptTooLongTokenCounts(msg)
  if (current == null || max == null) return null
  return current - max
}

export function getErrorMessageIfRefusal(err: unknown): string | null {
  const msg = extractErrorMessage(err)
  if (!msg) return null
  if (msg.toLowerCase().includes('refusal') || msg.toLowerCase().includes('refused'))
    return msg
  return null
}

export function getAssistantMessageFromError(err: unknown): string {
  const msg = extractErrorMessage(err)
  return msg ? `${API_ERROR_MESSAGE_PREFIX} ${msg}` : `${API_ERROR_MESSAGE_PREFIX} unknown error`
}

export function getImageTooLargeErrorMessage(limit?: number): string {
  return `Image exceeds size limit${limit ? ` (${limit} bytes)` : ''}`
}

export function getPdfInvalidErrorMessage(): string {
  return 'PDF is invalid or unreadable'
}

export function getPdfPasswordProtectedErrorMessage(): string {
  return 'PDF is password-protected; decrypt before attaching'
}

export function getPdfTooLargeErrorMessage(limit?: number): string {
  return `PDF exceeds size limit${limit ? ` (${limit} bytes)` : ''}`
}

export function getRequestTooLargeErrorMessage(): string {
  return 'Request payload too large'
}

function extractErrorMessage(err: unknown): string | null {
  if (typeof err === 'string') return err
  if (err instanceof Error) return err.message
  if (typeof err === 'object' && err !== null && 'message' in err) {
    const m = (err as { message: unknown }).message
    if (typeof m === 'string') return m
  }
  return null
}

export default undefined as any
