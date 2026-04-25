// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — /lang ko|en command (FR-004, T047).
//
// Flips the i18n locale binding at runtime without restart. The command
// updates the process.env['KOSMOS_TUI_LOCALE'] key (visible to all getUiL2I18n
// callers) and returns the new locale so the REPL dispatcher can trigger a
// re-render.
//
// Design: locale is process-level state, not a React context, because
// tui/src/i18n/uiL2.ts evaluates KOSMOS_TUI_LOCALE at module-load time via
// the `uiL2I18n` constant. Callers that need reactive locale changes should
// call getUiL2I18n(locale) directly with the locale returned by this command.
//
// Valid codes: ko | en   (Japanese: 日本語 deferred to post-P6 per spec.md)
//
// Reference: specs/1635-ui-l2-citizen-port/contracts/slash-commands.schema.json

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type SupportedLocale = 'ko' | 'en'

export type LangCommandResult =
  | { ok: true; locale: SupportedLocale }
  | { ok: false; message: string }

// ---------------------------------------------------------------------------
// Parser
// ---------------------------------------------------------------------------

const SUPPORTED_LOCALES = new Set<string>(['ko', 'en'])

/**
 * Parse the argument string from `/lang <code>`.
 *
 * Side-effect: sets `process.env['KOSMOS_TUI_LOCALE']` to the new locale so
 * that subsequent `getUiL2I18n()` calls pick it up. This is intentionally a
 * process-level mutation — locale is a singleton per TUI session.
 */
export function parseLangCommand(argStr: string): LangCommandResult {
  const arg = argStr.trim().toLowerCase()

  if (arg === '') {
    return {
      ok: false,
      message: 'Usage: /lang ko|en',
    }
  }

  if (!SUPPORTED_LOCALES.has(arg)) {
    return {
      ok: false,
      message: `Unsupported locale: "${arg}". Supported: ${[...SUPPORTED_LOCALES].join(' | ')}`,
    }
  }

  const locale = arg as SupportedLocale

  // Mutate process environment so module-level i18n lookups pick up the change
  process.env['KOSMOS_TUI_LOCALE'] = locale

  return { ok: true, locale }
}

/**
 * Return the currently active locale from the environment.
 * Falls back to 'ko' (Korean primary per FR-004).
 */
export function getCurrentLocale(): SupportedLocale {
  const env = process.env['KOSMOS_TUI_LOCALE']
  return env === 'en' ? 'en' : 'ko'
}

// ---------------------------------------------------------------------------
// Human-readable help text (consumed by /help catalog, FR-029)
// ---------------------------------------------------------------------------

export const LANG_COMMAND_HELP = {
  name: '/lang',
  group: 'session',
  description_ko: '언어를 한국어/영어로 전환합니다 (즉시 적용, 재시작 불필요)',
  description_en: 'Switch language between Korean and English (applied immediately, no restart required)',
  arg_signature: 'ko|en',
} as const
