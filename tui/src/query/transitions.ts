// [P0 reconstructed · Pass 3 v2 · agent-verified query state machine]
// Source of truth: literal grep of every `transition: { reason: ...` and
// `return { reason: ...` in tui/src/query.ts. Agent verification (Software
// Architect) found the first reconstruction had wrong Terminal names and
// missing Continue payloads — this v2 matches the consumer exactly.

/**
 * Why the previous iteration of the query loop continued.
 * Undefined on the first iteration. Exactly 7 variants — enumerate each
 * `transition: { reason:` site in query.ts.
 */
export type Continue =
  /** Archived old messages locally; carries whether the drain was committed. */
  | { reason: 'collapse_drain_retry'; committed: boolean }
  /** Ran reactive compact (fast-model summarisation of history). */
  | { reason: 'reactive_compact_retry' }
  /** Hit max_output_tokens; retrying with a higher ceiling. */
  | { reason: 'max_output_tokens_escalate' }
  /** Injected a "resume without recap" user message after max_output_tokens.
   *  `attempt` is 1-indexed: 1 on first recovery, 2 on second, etc. */
  | { reason: 'max_output_tokens_recovery'; attempt: number }
  /** A post-turn stop hook returned blocking errors; message injected. */
  | { reason: 'stop_hook_blocking' }
  /** Warned the model it is approaching the token budget. */
  | { reason: 'token_budget_continuation' }
  /** Happy path — tools ran, results appended, proceeding. */
  | { reason: 'next_turn' }

/**
 * Why the query loop terminated. Returned from the async generator.
 * Exactly the set of literal `return { reason:` values in query.ts.
 */
export type Terminal =
  /** Normal completion — model returned end_turn and no tool calls. */
  | { reason: 'completed' }
  /** Session exceeded a blocking limit (rate limit, org policy). */
  | { reason: 'blocking_limit' }
  /** Image attachment validation failed or was too large. */
  | { reason: 'image_error' }
  /** Model call failed non-retryably. */
  | { reason: 'model_error'; error: unknown }
  /** Stream was aborted mid-response (user abort or network). */
  | { reason: 'aborted_streaming' }
  /** Aborted while tools were running. */
  | { reason: 'aborted_tools' }
  /** Prompt (incl. context) exceeded the model's token limit with no recovery. */
  | { reason: 'prompt_too_long' }
  /** A stop hook returned a hard stop without allowing injection. */
  | { reason: 'hook_stopped' }
  /** Post-turn stop hook explicitly blocked further iteration. */
  | { reason: 'stop_hook_prevented' }
  /** Hit the per-session max-turn cap. Carries the final turn count. */
  | { reason: 'max_turns'; turnCount: number }

// ───── Constructors ─────────────────────────────────────────────────────

export const Continue = {
  collapse_drain_retry: (committed: boolean): Continue => ({
    reason: 'collapse_drain_retry',
    committed,
  }),
  reactive_compact_retry: (): Continue => ({ reason: 'reactive_compact_retry' }),
  max_output_tokens_escalate: (): Continue => ({
    reason: 'max_output_tokens_escalate',
  }),
  max_output_tokens_recovery: (attempt: number): Continue => ({
    reason: 'max_output_tokens_recovery',
    attempt,
  }),
  stop_hook_blocking: (): Continue => ({ reason: 'stop_hook_blocking' }),
  token_budget_continuation: (): Continue => ({
    reason: 'token_budget_continuation',
  }),
  next_turn: (): Continue => ({ reason: 'next_turn' }),
} as const

export const Terminal = {
  completed: (): Terminal => ({ reason: 'completed' }),
  blocking_limit: (): Terminal => ({ reason: 'blocking_limit' }),
  image_error: (): Terminal => ({ reason: 'image_error' }),
  model_error: (error: unknown): Terminal => ({ reason: 'model_error', error }),
  aborted_streaming: (): Terminal => ({ reason: 'aborted_streaming' }),
  aborted_tools: (): Terminal => ({ reason: 'aborted_tools' }),
  prompt_too_long: (): Terminal => ({ reason: 'prompt_too_long' }),
  hook_stopped: (): Terminal => ({ reason: 'hook_stopped' }),
  stop_hook_prevented: (): Terminal => ({ reason: 'stop_hook_prevented' }),
  max_turns: (turnCount: number): Terminal => ({ reason: 'max_turns', turnCount }),
} as const

// ───── Type guards ──────────────────────────────────────────────────────

const CONTINUE_REASONS = [
  'collapse_drain_retry',
  'reactive_compact_retry',
  'max_output_tokens_escalate',
  'max_output_tokens_recovery',
  'stop_hook_blocking',
  'token_budget_continuation',
  'next_turn',
] as const

const TERMINAL_REASONS = [
  'completed',
  'blocking_limit',
  'image_error',
  'model_error',
  'aborted_streaming',
  'aborted_tools',
  'prompt_too_long',
  'hook_stopped',
  'stop_hook_prevented',
  'max_turns',
] as const

export function isContinue(value: unknown): value is Continue {
  return (
    typeof value === 'object' &&
    value !== null &&
    'reason' in value &&
    typeof (value as { reason: unknown }).reason === 'string' &&
    (CONTINUE_REASONS as readonly string[]).includes(
      (value as { reason: string }).reason,
    )
  )
}

export function isTerminal(value: unknown): value is Terminal {
  return (
    typeof value === 'object' &&
    value !== null &&
    'reason' in value &&
    typeof (value as { reason: unknown }).reason === 'string' &&
    (TERMINAL_REASONS as readonly string[]).includes(
      (value as { reason: string }).reason,
    )
  )
}
